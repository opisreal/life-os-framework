import unittest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fetch_bitget import normalize_history_position

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


if __name__ == "__main__":
    unittest.main()
