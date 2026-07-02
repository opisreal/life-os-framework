import unittest, sys, os
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fetch_bitget import normalize_history_position, normalize_fill, fetch_fills

# 真实 API 返回小写 utime/ctime（2026-06-13 实测，与官方文档 cTime/uTime 不符）
SAMPLE = {"positionId": "123", "symbol": "ETHUSDT", "holdSide": "long",
          "openAvgPrice": "1500", "closeAvgPrice": "1550", "closeTotalPos": "1.0",
          "pnl": "50", "netProfit": "48.5", "totalFunding": "0.1",
          "openFee": "-0.5", "closeFee": "-0.6", "ctime": "1749000000000", "utime": "1749100000000"}

class TestNormalize(unittest.TestCase):
    def test_fields(self):
        rec = normalize_history_position(SAMPLE)
        self.assertEqual(rec["source_id"], "123")
        self.assertEqual(rec["symbol"], "ETHUSDT")
        self.assertEqual(rec["direction"], "long")
        self.assertEqual(rec["exchange"], "bitget")
        # utime(ms) → 'YYYY-MM-DD HH:MM:SS'（UTC+8，与 CSV 同口径）
        self.assertRegex(rec["close_time"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
        # 映射已锁定（2026-06-13 真实 9/9 对账）：realized_pnl=pnl（毛），两候选仍保留供审计
        self.assertEqual(rec["pnl_raw"], "50")
        self.assertEqual(rec["net_profit_raw"], "48.5")
        self.assertEqual(rec["source_file"], "api:history-position")

    def test_fee_folding_time_and_hash(self):
        import parse_trades
        rec = normalize_history_position(SAMPLE)
        # fee = −(totalFunding+openFee+closeFee) = −(0.1−0.5−0.6) = 1
        self.assertEqual(rec["fee"], "1")
        self.assertEqual(rec["realized_pnl"], "50")    # = pnl（毛），2026-06-13 对账锁定
        # 固定 UTC+8 偏移（非本机时区）：1749100000000 ms → 2025-06-05 13:06:40
        self.assertEqual(rec["close_time"], "2025-06-05 13:06:40")
        self.assertEqual(rec["market_type"], "futures")
        self.assertEqual(rec["open_avg"], "1500")
        self.assertEqual(rec["close_avg"], "1550")
        self.assertEqual(rec["qty"], "1.0")
        self.assertEqual(rec["row_hash"], parse_trades.closed_row_hash(rec))
        self.assertNotIn("setup", rec)                 # setup 由 CLI 层 setdefault

    def test_legacy_capitalized_utime_fallback(self):
        # 兜底：若 Bitget 改回文档写法 uTime/cTime（大小写变体），归一化仍可工作
        legacy = {k: v for k, v in SAMPLE.items() if k not in ("utime", "ctime")}
        legacy["uTime"] = SAMPLE["utime"]
        legacy["cTime"] = SAMPLE["ctime"]
        rec = normalize_history_position(legacy)
        self.assertEqual(rec["close_time"], "2025-06-05 13:06:40")
        self.assertEqual(rec["source_id"], "123")

    def test_loaders_registered_and_dispatchable(self):
        # LOADERS 新键经 parse_trades 转发 stub 分发（与 CLI getattr(parse_trades,…) 契约一致）
        import parse_trades
        name = parse_trades.LOADERS[("bitget", "closed_pnl_api")]
        self.assertEqual(name, "load_api_closed_pnl")
        self.assertTrue(callable(getattr(parse_trades, name)))


# ---------- fills（成交明细）归一化：2026-07-03 真实 API 样本校准 ----------
# 真实返回大写 cTime（与 history-position 的小写 utime/ctime 相反，两处大小写互异均兼容）
FILL = {"tradeId": "t1", "symbol": "BTCUSDT", "orderId": "o1", "price": "59689.1",
        "baseVolume": "0.0684", "quoteVolume": "4082.7344",
        "feeDetail": [{"deduction": "no", "feeCoin": "USDT",
                       "totalDeductionFee": None, "totalFee": "-2.44964066"}],
        "side": "sell", "profit": "21.99744", "enterPointSource": "web",
        "tradeSide": "close", "posMode": "hedge_mode", "tradeScope": "taker",
        "cTime": "1749100000500"}


class TestNormalizeFill(unittest.TestCase):
    def test_fields(self):
        import parse_trades
        rec = normalize_fill(FILL)
        self.assertEqual(rec["source_id"], "t1")
        self.assertEqual(rec["symbol"], "BTCUSDT")
        self.assertEqual(rec["side"], "sell")
        self.assertEqual(rec["position_side"], "close_long")   # hedge_mode：close+sell=平多
        self.assertEqual(rec["price"], "59689.1")
        self.assertEqual(rec["base_qty"], "0.0684")
        self.assertEqual(rec["quote_qty"], "4082.7344")
        self.assertEqual(rec["fee_amount"], "2.44964066")      # −ΣtotalFee，正=成本（同 closed-pnl 折叠口径）
        self.assertEqual(rec["fee_asset"], "USDT")
        # cTime(ms) → UTC+8 含毫秒（schema §1：同秒同价同量的合法重复靠毫秒区分）
        self.assertEqual(rec["time"], "2025-06-05 13:06:40.500")
        self.assertEqual(rec["exchange"], "bitget")
        self.assertEqual(rec["market_type"], "futures")
        self.assertEqual(rec["source_file"], "api:fills")
        self.assertEqual(rec["row_hash"], parse_trades.row_hash(rec))

    def test_position_side_matrix(self):
        cases = {("open", "buy"): "open_long", ("open", "sell"): "open_short",
                 ("close", "sell"): "close_long", ("close", "buy"): "close_short"}
        for (ts, side), want in cases.items():
            rec = normalize_fill(dict(FILL, tradeSide=ts, side=side))
            self.assertEqual(rec["position_side"], want, (ts, side))

    def test_non_hedge_mode_rejected(self):
        # 单向持仓推导规则未实测，不猜——校准门：非 hedge_mode 整行拒绝出 warning
        with self.assertRaises(ValueError):
            normalize_fill(dict(FILL, posMode="one_way_mode"))

    def test_mixed_fee_coin_rejected(self):
        f = dict(FILL, feeDetail=[{"feeCoin": "USDT", "totalFee": "-1"},
                                  {"feeCoin": "BGB", "totalFee": "-0.1"}])
        with self.assertRaises(ValueError):
            normalize_fill(f)

    def test_multi_fee_same_coin_summed(self):
        f = dict(FILL, feeDetail=[{"feeCoin": "USDT", "totalFee": "-1.5"},
                                  {"feeCoin": "USDT", "totalFee": "-0.5"}])
        self.assertEqual(normalize_fill(f)["fee_amount"], "2")

    def test_lowercase_ctime_fallback(self):
        f = {k: v for k, v in FILL.items() if k != "cTime"}
        f["ctime"] = FILL["cTime"]
        self.assertEqual(normalize_fill(f)["time"], "2025-06-05 13:06:40.500")

    def test_fills_loader_registered(self):
        import parse_trades
        name = parse_trades.LOADERS[("bitget", "fills_api")]
        self.assertEqual(name, "load_api_fills")
        self.assertTrue(callable(getattr(parse_trades, name)))


class TestFetchFillsPagination(unittest.TestCase):
    def test_two_pages_cursor_and_bad_row_warning(self):
        page1 = {"fillList": [dict(FILL, tradeId=f"t{i}") for i in range(100)], "endId": "cur1"}
        bad = dict(FILL, tradeId="tbad", posMode="one_way_mode")
        page2 = {"fillList": [dict(FILL, tradeId="t100"), bad], "endId": "cur2"}
        calls = []

        def fake(*a, **kw):
            calls.append(kw.get("id_less_than"))
            return page1 if kw.get("id_less_than") is None else page2

        with mock.patch("fetch_bitget.bitget_api.fills", side_effect=fake):
            rows, warnings = fetch_fills(1, 2)
        self.assertEqual(calls, [None, "cur1"])        # 第二页带游标；第二页不足 100 停
        self.assertEqual(len(rows), 101)               # 坏行不入 rows
        self.assertEqual(len(warnings), 1)             # 坏行出 warning（含 tradeId 可溯源）
        self.assertIn("tbad", warnings[0])


if __name__ == "__main__":
    unittest.main()
