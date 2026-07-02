import unittest, sys, os, csv, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import parse_trades
from import_closed_pnl import STORE_FIELDS, TRADES_FIELDS
from lint_finance import lint

EQ_HDR = "week,as_of,equity_usdt,usdt_cny_rate,equity_rmb,net_flow_usdt,note\n"

def _closed_rec(sid="p1", pnl="50"):
    rec = {"close_time": "2026-07-01 10:00:00", "exchange": "bitget", "market_type": "futures",
           "symbol": "BTCUSDT", "direction": "long", "open_avg": "100", "close_avg": "110",
           "qty": "1", "realized_pnl": pnl, "fee": "1", "source_id": sid,
           "source_file": "api:history-position", "setup": "unlabeled"}
    rec["row_hash"] = parse_trades.closed_row_hash(rec)
    return rec

class TestLint(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, self.root)
        os.makedirs(os.path.join(self.root, "equity"))

    def _write_closed(self, recs):
        with open(os.path.join(self.root, "closed-pnl.csv"), "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=STORE_FIELDS); w.writeheader()
            w.writerows({k: r.get(k, "") for k in STORE_FIELDS} for r in recs)

    def _write_equity(self, body):
        with open(os.path.join(self.root, "equity", "2026.csv"), "w") as fh:
            fh.write(EQ_HDR + body)

    def test_all_good_empty_issues(self):
        self._write_closed([_closed_rec()])
        self._write_equity("2026-W27,2026-07-03,100,6.7939,679.39,0,\n")
        self.assertEqual(lint(self.root), [])

    def test_hash_mismatch_detected(self):
        rec = _closed_rec(); rec["row_hash"] = "deadbeefdeadbeef"
        self._write_closed([rec]); self._write_equity("")
        issues = lint(self.root)
        self.assertTrue(any("row_hash" in i for i in issues), issues)

    def test_duplicate_source_id_detected(self):
        self._write_closed([_closed_rec("p1"), _closed_rec("p1")]); self._write_equity("")
        self.assertTrue(any("source_id 重复" in i for i in lint(self.root)))

    def test_bad_setup_vocab_detected(self):
        rec = _closed_rec(); rec["setup"] = "yolo"
        self._write_closed([rec]); self._write_equity("")
        self.assertTrue(any("setup" in i for i in lint(self.root)))

    def test_equity_contract_violation_detected(self):
        self._write_closed([_closed_rec()])
        self._write_equity("2026-W27,2026-07-03,100,6.7939,999.99,0,\n")   # ≠ round(100×6.7939,2)
        self.assertTrue(any("equity_rmb" in i for i in lint(self.root)))

    def test_missing_tables_ok(self):
        self._write_equity("")     # closed-pnl/trades 不存在 → 不报错（空仓账户合法）
        self.assertEqual(lint(self.root), [])
