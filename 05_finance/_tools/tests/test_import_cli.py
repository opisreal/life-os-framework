import unittest, sys, os, csv, shutil, tempfile, json, subprocess
from datetime import datetime, timedelta, timezone
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
FIX = os.path.join(HERE, "fixtures", "bitget_closedpnl_sample.csv")

sys.path.insert(0, TOOLS)
import import_closed_pnl
import fetch_bitget
import bitget_api

_TZ_UTC8 = timezone(timedelta(hours=8))

def run_cli(args):
    return subprocess.run([sys.executable, os.path.join(TOOLS, "import_closed_pnl.py")] + args,
                          capture_output=True, text=True)

class TestImportCli(unittest.TestCase):
    def setUp(self):
        self.store = tempfile.NamedTemporaryFile('w', suffix='.csv', delete=False); self.store.close()
        os.unlink(self.store.name)          # CLI 需自建含表头的文件
        self.addCleanup(lambda: os.path.exists(self.store.name) and os.unlink(self.store.name))

    def test_first_import_appends_all(self):
        r = run_cli([FIX, "--store", self.store.name])
        rep = json.loads(r.stdout)
        self.assertEqual(rep["added"], 4); self.assertEqual(rep["skipped"], 0)
        rows = list(csv.DictReader(open(self.store.name)))
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(r2["setup"] == "unlabeled" for r2 in rows))

    def test_replay_same_file_skips_silently(self):
        run_cli([FIX, "--store", self.store.name])
        rep = json.loads(run_cli([FIX, "--store", self.store.name]).stdout)
        self.assertEqual(rep["added"], 0); self.assertEqual(rep["skipped"], 4)
        self.assertEqual(rep["suspected"], 0)   # 同 source_file 重放豁免

    def test_same_hash_other_file_suspected(self):
        run_cli([FIX, "--store", self.store.name])
        import shutil; dup = FIX.replace("sample", "sample_copy"); shutil.copy(FIX, dup)
        self.addCleanup(os.unlink, dup)
        rep = json.loads(run_cli([dup, "--store", self.store.name]).stdout)
        self.assertEqual(rep["added"], 0); self.assertEqual(rep["suspected"], 4)   # 不静默删、不入库，待人工确认

    def test_zero_byte_store_gets_header(self):
        # 存量文件存在但 0 字节：append 必须先补表头，否则首行数据被当表头 → 账本损坏
        open(self.store.name, "w").close()
        rep = json.loads(run_cli([FIX, "--store", self.store.name]).stdout)
        self.assertEqual(rep["added"], 4)
        with open(self.store.name, encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            self.assertIn("close_time", reader.fieldnames)
            self.assertIn("setup", reader.fieldnames)
            rows = list(reader)
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(r["row_hash"] for r in rows))


# ---------- --source api（Task O）：进程内直调 run_import，网络边界全部 mock ----------

CSV_SOURCE_FILE = "导出 U 本位合约历史仓位-2026-06-08 05_28_26.035.csv"

def _api_item(pid, pnl="50", utime_ms="1749100000000"):
    """history-position 单条真实形态样本（小写 utime，见 exchange-schemas.md API 段）。"""
    return {"positionId": pid, "symbol": "ETHUSDT", "holdSide": "long",
            "openAvgPrice": "1500", "closeAvgPrice": "1550", "closeTotalPos": "1.0",
            "pnl": pnl, "netProfit": "48.5", "totalFunding": "0.1",
            "openFee": "-0.5", "closeFee": "-0.6", "utime": utime_ms}

def _api_row(pid, **kw):
    """归一化后的 API 行（schema 与生产路径同源，不手抄字段）。"""
    return fetch_bitget.normalize_history_position(_api_item(pid, **kw))

def _args(argv):
    return import_closed_pnl.build_parser().parse_args(argv)


class TestImportApiSource(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.store = os.path.join(self.tmp, "closed-pnl.csv")

    def _seed_store(self, rows):
        """造存量 store：API 同字段行改挂 CSV source_file（模拟 Task N 回填后的存量形态）。"""
        with open(self.store, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=import_closed_pnl.STORE_FIELDS)
            w.writeheader()
            for r in rows:
                full = dict(r); full.setdefault("setup", "unlabeled")
                w.writerow({k: full.get(k, "") for k in import_closed_pnl.STORE_FIELDS})

    def test_api_source_id_hit_definitive_skip_plus_new_row(self):
        # ① 2 行 mock：一行 positionId 与存量重复（CSV 来源、source_file 不同）、一行全新
        seed = dict(_api_row("111")); seed["source_file"] = CSV_SOURCE_FILE
        self._seed_store([seed])
        fetched = [_api_row("111"), _api_row("222", pnl="60")]
        with mock.patch.object(fetch_bitget, "fetch_closed_pnl", return_value=fetched):
            rep = import_closed_pnl.run_import(_args(["--source", "api", "--store", self.store]))
        self.assertEqual(rep["added"], 1)
        self.assertEqual(rep["skipped"], 1)        # id 命中 = 确定重复，绝不 suspected
        self.assertEqual(rep["suspected"], 0)
        self.assertEqual(rep["source"], "api")
        self.assertEqual(len(rep["window"]), 2)    # [since, until]
        rows = list(csv.DictReader(open(self.store, encoding="utf-8")))
        self.assertEqual(len(rows), 2)
        new = [r for r in rows if r["source_id"] == "222"][0]
        self.assertEqual(new["source_file"], "api:history-position")
        self.assertEqual(new["setup"], "unlabeled")

    def test_dedup_fix_id_hit_cross_source_file_skipped_not_suspected(self):
        # ④ 修正回归测试：CSV 入库行（source_id 已回填）+ API 重拉同 positionId
        #    旧逻辑会因 source_file 不同标 suspected——positionId 命中是确定重复，必须 skipped
        seed = dict(_api_row("111")); seed["source_file"] = CSV_SOURCE_FILE
        self._seed_store([seed])
        with mock.patch.object(fetch_bitget, "fetch_closed_pnl", return_value=[_api_row("111")]):
            rep = import_closed_pnl.run_import(_args(["--source", "api", "--store", self.store]))
        self.assertEqual(rep["added"], 0)
        self.assertEqual(rep["skipped"], 1)
        self.assertEqual(rep["suspected"], 0)
        self.assertEqual(len(list(csv.DictReader(open(self.store, encoding="utf-8")))), 1)

    def test_csv_replay_after_id_backfill_still_skipped(self):
        # 存量互盲回归：store 行 source_id 回填后，重放原 CSV（行无 id）必须 hash 命中 skipped，
        # 不得因「存量只按 id 登记」而重复入库
        rep1 = import_closed_pnl.run_import(_args([FIX, "--store", self.store]))
        self.assertEqual(rep1["added"], 4)
        rows = list(csv.DictReader(open(self.store, encoding="utf-8")))
        for i, r in enumerate(rows):
            r["source_id"] = f"9000{i}"
        self._seed_store(rows)
        rep2 = import_closed_pnl.run_import(_args([FIX, "--store", self.store]))
        self.assertEqual(rep2["added"], 0)
        self.assertEqual(rep2["skipped"], 4)
        self.assertEqual(rep2["suspected"], 0)


class TestEquityAuto(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.store = os.path.join(self.tmp, "closed-pnl.csv")
        now = datetime.now(_TZ_UTC8)
        self.week = now.strftime("%G-W%V")
        self.today = now.strftime("%Y-%m-%d")
        self.eq_path = os.path.join(self.tmp, "equity", now.strftime("%G") + ".csv")

    BALANCE = [{"accountType": "spot", "usdtBalance": "1.5"},
               {"accountType": "futures", "usdtBalance": "100.25"}]

    def test_equity_written_when_week_missing(self):
        # ② 当周无行 → 写自动行：sum(usdtBalance) 两位小数、note=auto、rate/rmb 空、net_flow 0
        with mock.patch.object(fetch_bitget, "fetch_closed_pnl", return_value=[]), \
             mock.patch.object(bitget_api, "all_account_balance", return_value=self.BALANCE):
            rep = import_closed_pnl.run_import(
                _args(["--source", "api", "--equity", "--store", self.store]))
        self.assertEqual(rep["equity"]["status"], "written")
        self.assertEqual(rep["equity"]["value"], "101.75")
        self.assertEqual(rep["equity"]["week"], self.week)
        rows = list(csv.DictReader(open(self.eq_path, encoding="utf-8")))
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r["week"], self.week)
        self.assertEqual(r["as_of"], self.today)
        self.assertEqual(r["equity_usdt"], "101.75")
        self.assertEqual(r["usdt_cny_rate"], "")
        self.assertEqual(r["equity_rmb"], "")
        self.assertEqual(r["net_flow_usdt"], "0")
        self.assertEqual(r["note"], "auto")

    def test_equity_exists_no_write_no_fetch(self):
        # ③ 当周已有行 → 不写不拉（覆盖问询是 skill 层的事），报告 exists + 现值
        os.makedirs(os.path.dirname(self.eq_path))
        with open(self.eq_path, "w", newline="", encoding="utf-8") as fh:
            fh.write("week,as_of,equity_usdt,usdt_cny_rate,equity_rmb,net_flow_usdt,note\n")
            fh.write(f"{self.week},{self.today},4255.36,,,0,manual\n")
        before = open(self.eq_path, encoding="utf-8").read()
        with mock.patch.object(fetch_bitget, "fetch_closed_pnl", return_value=[]), \
             mock.patch.object(bitget_api, "all_account_balance",
                               side_effect=AssertionError("不得调用：当周行已存在")):
            rep = import_closed_pnl.run_import(
                _args(["--source", "api", "--equity", "--store", self.store]))
        self.assertEqual(rep["equity"]["status"], "exists")
        self.assertEqual(rep["equity"]["value"], "4255.36")
        self.assertEqual(open(self.eq_path, encoding="utf-8").read(), before)


# ---------- --kind fills（步骤② fills 轨道）：trades.csv 落盘 ----------

def _fill_item(tid, price="59689.1"):
    """fills 单条真实形态样本（大写 cTime，2026-07-03 实测）。"""
    return {"tradeId": tid, "symbol": "BTCUSDT", "orderId": "o1", "price": price,
            "baseVolume": "0.0684", "quoteVolume": "4082.7344",
            "feeDetail": [{"feeCoin": "USDT", "totalFee": "-2.44964066"}],
            "side": "sell", "tradeSide": "close", "posMode": "hedge_mode",
            "cTime": "1749100000500"}


def _fill_row(tid, **kw):
    return fetch_bitget.normalize_fill(_fill_item(tid, **kw))


class TestImportFillsKind(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.store = os.path.join(self.tmp, "trades.csv")

    def test_first_import_writes_trades_schema(self):
        fetched = ([_fill_row("t1"), _fill_row("t2", price="59000")], [])
        with mock.patch.object(fetch_bitget, "fetch_fills", return_value=fetched):
            rep = import_closed_pnl.run_import(
                _args(["--source", "api", "--kind", "fills", "--store", self.store]))
        self.assertEqual(rep["added"], 2)
        self.assertEqual(rep["skipped"], 0)
        with open(self.store, encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            self.assertEqual(reader.fieldnames, import_closed_pnl.TRADES_FIELDS)   # 14 列，无 setup
            rows = list(reader)
        self.assertEqual(len(rows), 2)
        self.assertNotIn("setup", rows[0])
        self.assertTrue(all(r["row_hash"] for r in rows))
        # date_range 用 time 字段（fills 无 close_time）；首末两元素口径同 closed_pnl
        self.assertEqual(rep["date_range"], ["2025-06-05", "2025-06-05"])

    def test_replay_idempotent_by_trade_id(self):
        fetched = ([_fill_row("t1")], [])
        with mock.patch.object(fetch_bitget, "fetch_fills", return_value=fetched):
            import_closed_pnl.run_import(
                _args(["--source", "api", "--kind", "fills", "--store", self.store]))
            rep = import_closed_pnl.run_import(
                _args(["--source", "api", "--kind", "fills", "--store", self.store]))
        self.assertEqual(rep["added"], 0)
        self.assertEqual(rep["skipped"], 1)        # tradeId 命中 = 确定重复
        self.assertEqual(rep["suspected"], 0)

    def test_fills_csv_source_not_calibrated(self):
        # fills 的 CSV 映射未校准（exchange-schemas.md fills 段），csv 路径必须显式拒绝
        with self.assertRaises(SystemExit):
            import_closed_pnl.run_import(
                _args(["--source", "csv", "--kind", "fills", FIX, "--store", self.store]))

    def test_fills_warnings_surface_in_report(self):
        fetched = ([_fill_row("t1")], ["fill tbad: posMode=one_way_mode 未校准，跳行"])
        with mock.patch.object(fetch_bitget, "fetch_fills", return_value=fetched):
            rep = import_closed_pnl.run_import(
                _args(["--source", "api", "--kind", "fills", "--store", self.store]))
        self.assertEqual(rep["added"], 1)
        self.assertEqual(len(rep["warnings"]), 1)
