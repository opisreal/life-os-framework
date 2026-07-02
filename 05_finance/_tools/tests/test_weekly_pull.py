import unittest, sys, os, csv, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from weekly_pull import compose, load_equity_series

EQ_HDR = "week,as_of,equity_usdt,usdt_cny_rate,equity_rmb,net_flow_usdt,note\n"

def _rep(added=0, skipped=0, suspected=0, warnings=None, equity=None):
    r = {"added": added, "skipped": skipped, "suspected": suspected,
         "warnings": warnings or []}
    if equity is not None:
        r["equity"] = equity
    return r

def _eqrow(week, as_of, usdt):
    return {"week": week, "as_of": as_of, "equity_usdt": usdt}

def _closed(t, pnl, fee="0"):
    return {"close_time": t, "realized_pnl": pnl, "fee": fee}


class TestCompose(unittest.TestCase):
    def test_normal_written_no_flags(self):
        out = compose(_rep(added=3, skipped=5, equity={"status": "written", "week": "2026-W27", "value": "4307.94"}),
                      _rep(added=10), [], [])
        self.assertTrue(out["commit"])
        self.assertFalse(out["flagged"])
        self.assertIn("✅", out["title"])
        self.assertIn("3 回合", out["body"])
        self.assertIn("成交明细 +10", out["body"])
        self.assertIn("4307.94", out["body"])

    def test_nothing_new_no_commit(self):
        out = compose(_rep(equity={"status": "exists", "week": "2026-W27", "value": "4307.94"}),
                      _rep(), [], [])
        self.assertFalse(out["commit"])
        self.assertFalse(out["flagged"])

    def test_suspected_and_warnings_flag(self):
        out = compose(_rep(suspected=2, equity={"status": "exists"}),
                      _rep(warnings=["fill x: posMode 未校准"]), [], [])
        self.assertTrue(out["flagged"])
        self.assertIn("⚠️", out["title"])
        self.assertIn("疑似重复", out["body"])
        self.assertIn("warnings 1 条", out["body"])

    def test_reconciliation_gap_triggers(self):
        eq = [_eqrow("2026-W26", "2026-06-28", "100"), _eqrow("2026-W27", "2026-07-03", "200")]
        closed = [_closed("2026-06-30 10:00:00", "10")]   # net=10, ΔE=100 → gap 90%
        out = compose(_rep(equity={"status": "written", "week": "2026-W27", "value": "200"}),
                      _rep(), eq, closed)
        self.assertTrue(out["flagged"])
        self.assertIn("出入金对账", out["body"])

    def test_reconciliation_clean_silent(self):
        eq = [_eqrow("2026-W26", "2026-06-28", "100"), _eqrow("2026-W27", "2026-07-03", "103")]
        closed = [_closed("2026-06-30 10:00:00", "3")]
        out = compose(_rep(equity={"status": "written", "week": "2026-W27", "value": "103"}),
                      _rep(), eq, closed)
        self.assertNotIn("出入金对账", out["body"])


class TestLoadEquitySeriesCrossYear(unittest.TestCase):
    def test_merge_two_year_files(self):
        tmp = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, tmp)
        with open(os.path.join(tmp, "2026.csv"), "w") as fh:
            fh.write(EQ_HDR + "2026-W53,2026-12-31,100,,,0,\n")
        with open(os.path.join(tmp, "2027.csv"), "w") as fh:
            fh.write(EQ_HDR + "2027-W01,2027-01-04,110,,,0,\n")
        rows = load_equity_series(tmp)
        self.assertEqual([r["week"] for r in rows], ["2026-W53", "2027-W01"])
