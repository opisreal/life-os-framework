import os
import tempfile
import unittest
from parse_trades import row_hash
from parse_trades import dedup_fills
from parse_trades import compute_pnl_stats
from parse_trades import drawdown_from_peak
from parse_trades import pair_spot_rounds
from parse_trades import load_bitget_csv
from parse_trades import closed_row_hash
from parse_trades import dedup_closed_rounds
from parse_trades import weekly_change
from parse_trades import load_equity

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures",
                       "bitget_closedpnl_sample.csv")

HEADER = ("合约,开仓时间,开仓均价,平仓均价,平仓量,平仓价值,仓位盈亏,"
          "已实现盈亏,资金费用,开仓手续费,平仓手续费,全部平仓时间")

class TestRowHash(unittest.TestCase):
    def test_stable_and_order_independent_of_irrelevant_fields(self):
        fill = {"time": "2026-06-01T10:00:00+08:00", "exchange": "bitget",
                "market_type": "futures", "symbol": "BTC/USDT", "side": "buy",
                "position_side": "open_long", "price": "60000", "base_qty": "0.1",
                "quote_qty": "6000", "fee_amount": "1.2", "fee_asset": "USDT"}
        h1 = row_hash(fill)
        h2 = row_hash(dict(fill))
        fill2 = dict(fill); fill2["price"] = "60001"
        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, row_hash(fill2))
        self.assertEqual(len(h1), 16)

class TestDedup(unittest.TestCase):
    def _f(self, sid, price, qty):
        return {"source_id": sid, "time": "t", "exchange": "bitget",
                "market_type": "futures", "symbol": "BTC/USDT", "side": "buy",
                "position_side": "open_long", "price": price, "base_qty": qty,
                "fee_amount": "0"}

    def test_dedup_by_source_id(self):
        kept, suspected = dedup_fills([self._f("A", "1", "1"), self._f("A", "1", "1")])
        self.assertEqual(len(kept), 1)
        self.assertEqual(suspected, [])

    def test_same_hash_no_source_id_is_suspected_not_dropped(self):
        a = self._f("", "1", "1"); b = self._f("", "1", "1")
        kept, suspected = dedup_fills([a, b])
        self.assertEqual(len(kept), 2)
        self.assertEqual(len(suspected), 1)

    def test_distinct_fills_all_kept(self):
        kept, suspected = dedup_fills([self._f("A", "1", "1"), self._f("B", "2", "1")])
        self.assertEqual(len(kept), 2)
        self.assertEqual(suspected, [])

class TestPnlStats(unittest.TestCase):
    def _r(self, pnl, fee="0"):
        return {"realized_pnl": pnl, "fee": fee}

    def test_win_rate_profit_factor_net(self):
        rounds = [self._r("100", "2"), self._r("-50", "1"), self._r("30", "1"), self._r("-20", "1")]
        s = compute_pnl_stats(rounds)
        self.assertEqual(s["rounds"], 4)
        self.assertEqual(s["wins"], 2)
        self.assertEqual(s["losses"], 2)
        self.assertAlmostEqual(s["win_rate"], 0.5)
        self.assertAlmostEqual(s["profit_factor"], 130/70)
        self.assertAlmostEqual(s["net_pnl"], 100-50+30-20-5)

    def test_empty_rounds(self):
        s = compute_pnl_stats([])
        self.assertEqual(s["rounds"], 0)
        self.assertIsNone(s["win_rate"])
        self.assertIsNone(s["profit_factor"])
        self.assertEqual(s["net_pnl"], 0.0)

    def test_no_losses_profit_factor_is_none(self):
        s = compute_pnl_stats([self._r("10"), self._r("5")])
        self.assertIsNone(s["profit_factor"])

class TestDrawdown(unittest.TestCase):
    def test_peak_to_current(self):
        eq = [100.0, 120.0, 90.0]
        self.assertAlmostEqual(drawdown_from_peak(eq), 0.25)

    def test_new_high_zero_drawdown(self):
        self.assertAlmostEqual(drawdown_from_peak([100.0, 110.0, 130.0]), 0.0)

    def test_single_or_empty(self):
        self.assertEqual(drawdown_from_peak([100.0]), 0.0)
        self.assertEqual(drawdown_from_peak([]), 0.0)

    def test_breach_flag_against_cap(self):
        from parse_trades import drawdown_breaches
        self.assertTrue(drawdown_breaches([100.0, 70.0], cap=0.20))
        self.assertFalse(drawdown_breaches([100.0, 90.0], cap=0.20))

class TestSpotFifo(unittest.TestCase):
    def _t(self, side, price, qty):
        return {"side": side, "price": price, "base_qty": qty}

    def test_full_cost_round_included(self):
        fills = [self._t("buy", "100", "1"), self._t("sell", "120", "1")]
        rounds, low_conf = pair_spot_rounds(fills)
        self.assertEqual(len(rounds), 1)
        self.assertEqual(low_conf, 0)
        self.assertAlmostEqual(rounds[0]["realized_pnl"], 20.0)

    def test_sell_without_basis_marked_low_conf_and_excluded(self):
        fills = [self._t("sell", "120", "1")]
        rounds, low_conf = pair_spot_rounds(fills)
        self.assertEqual(rounds, [])
        self.assertEqual(low_conf, 1)

    # --- Fix 1: 输入守卫 ---

    def test_sell_zero_qty_is_low_conf_no_round(self):
        fills = [self._t("buy", "100", "1"), self._t("sell", "100", "0")]
        rounds, low_conf = pair_spot_rounds(fills)
        self.assertEqual(rounds, [])
        self.assertEqual(low_conf, 1)

    def test_sell_negative_qty_is_low_conf_no_round(self):
        fills = [self._t("buy", "100", "1"), self._t("sell", "100", "-1")]
        rounds, low_conf = pair_spot_rounds(fills)
        self.assertEqual(rounds, [])
        self.assertEqual(low_conf, 1)

    def test_buy_nonpositive_qty_is_low_conf_skipped(self):
        # buy qty<=0 不入栈，后续卖出无底仓 → 也 low_conf
        fills = [self._t("buy", "100", "0"), self._t("buy", "100", "-2"),
                 self._t("sell", "120", "1")]
        rounds, low_conf = pair_spot_rounds(fills)
        self.assertEqual(rounds, [])
        self.assertEqual(low_conf, 3)

    def test_side_case_insensitive(self):
        fills = [self._t("BUY", "100", "1"), self._t("Sell", "120", "1")]
        rounds, low_conf = pair_spot_rounds(fills)
        self.assertEqual(len(rounds), 1)
        self.assertEqual(low_conf, 0)
        self.assertAlmostEqual(rounds[0]["realized_pnl"], 20.0)

    def test_unknown_side_is_low_conf_skipped(self):
        fills = [self._t("buy", "100", "1"), self._t("hold", "120", "1"),
                 self._t("sell", "120", "1")]
        rounds, low_conf = pair_spot_rounds(fills)
        self.assertEqual(len(rounds), 1)
        self.assertEqual(low_conf, 1)
        self.assertAlmostEqual(rounds[0]["realized_pnl"], 20.0)

    # --- Fix 2: FIFO 多 lot 覆盖 ---

    def test_multi_lot_weighted_cost_and_remaining_tail(self):
        # buy 1@100, buy 1@200, sell 1.5@150 → pnl = 1.5*150 - (1*100 + 0.5*200) = 25
        # 剩余 lot 0.5@200，再 sell 0.5@200 → pnl = 0
        fills = [self._t("buy", "100", "1"), self._t("buy", "200", "1"),
                 self._t("sell", "150", "1.5"), self._t("sell", "200", "0.5")]
        rounds, low_conf = pair_spot_rounds(fills)
        self.assertEqual(len(rounds), 2)
        self.assertEqual(low_conf, 0)
        self.assertAlmostEqual(rounds[0]["realized_pnl"], 25.0)
        self.assertAlmostEqual(rounds[1]["realized_pnl"], 0.0)

    def test_partial_lot_sell_leaves_tail(self):
        fills = [self._t("buy", "100", "1"), self._t("sell", "110", "0.4"),
                 self._t("sell", "90", "0.6")]
        rounds, low_conf = pair_spot_rounds(fills)
        self.assertEqual(len(rounds), 2)
        self.assertEqual(low_conf, 0)
        self.assertAlmostEqual(rounds[0]["realized_pnl"], 4.0)
        self.assertAlmostEqual(rounds[1]["realized_pnl"], -6.0)

    def test_low_conf_oversized_sell_consumes_lots(self):
        # 钉住现有保守行为：超量卖单虽被丢弃（low_conf），但已破坏性消耗了现有 lots，
        # 故后续本可配对的卖单也变为 low_conf。
        fills = [self._t("buy", "100", "1"), self._t("sell", "120", "2"),
                 self._t("sell", "120", "1")]
        rounds, low_conf = pair_spot_rounds(fills)
        self.assertEqual(rounds, [])
        self.assertEqual(low_conf, 2)

class TestLoadBitgetClosedPnl(unittest.TestCase):
    def _load_fixture(self):
        return load_bitget_csv(FIXTURE, kind="closed_pnl")

    def _write_tmp(self, text, encoding="utf-8-sig"):
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        self.addCleanup(os.remove, path)
        with open(path, "w", encoding=encoding, newline="") as f:
            f.write(text)
        return path

    def test_fixture_loads_all_rows_no_warnings(self):
        rows, warnings = self._load_fixture()
        self.assertEqual(len(rows), 4)
        self.assertEqual(warnings, [])

    def test_first_row_normalized_fields(self):
        rows, _ = self._load_fixture()
        r = rows[0]
        self.assertEqual(r["close_time"], "2026-06-01 12:00:00")
        self.assertEqual(r["symbol"], "AAAUSDT")
        self.assertEqual(r["direction"], "long")
        self.assertEqual(r["open_avg"], "1.5")
        self.assertEqual(r["close_avg"], "1.6")
        self.assertEqual(r["qty"], "100")        # 后缀 AAA 已剥离
        self.assertEqual(r["realized_pnl"], "10")  # USDT 已剥离
        self.assertEqual(r["source_id"], "")
        self.assertEqual(r["exchange"], "bitget")
        self.assertEqual(r["market_type"], "futures")
        self.assertEqual(r["source_file"], "bitget_closedpnl_sample.csv")
        self.assertEqual(r["row_hash"], closed_row_hash(r))

    def test_fee_folding_realized_minus_fee_equals_position_pnl(self):
        rows, _ = self._load_fixture()
        # 行1：资金费用为正（收入）：fee = -(0.05 - 0.06 - 0.064) = 0.074
        self.assertAlmostEqual(float(rows[0]["fee"]), 0.074)
        self.assertAlmostEqual(
            float(rows[0]["realized_pnl"]) - float(rows[0]["fee"]), 9.926)
        # 行3：资金费用为负：fee = -(-0.02 - 0.048 - 0.044) = 0.112
        self.assertAlmostEqual(float(rows[2]["fee"]), 0.112)
        self.assertAlmostEqual(
            float(rows[2]["realized_pnl"]) - float(rows[2]["fee"]), 9.888)

    def test_short_direction_parsed(self):
        rows, _ = self._load_fixture()
        self.assertEqual(rows[2]["symbol"], "BBBUSDT")
        self.assertEqual(rows[2]["direction"], "short")

    def test_synthetic_short_isolated(self):
        path = self._write_tmp(HEADER + "\n" +
            "XUSDT Short·Isolated,2026-06-01 10:00:00,2,1.9,50X,95USDT,"
            "4.9USDT,5USDT,0USDT,-0.05USDT,-0.05USDT,2026-06-01 11:00:00\n")
        rows, warnings = load_bitget_csv(path, kind="closed_pnl")
        self.assertEqual(warnings, [])
        self.assertEqual(rows[0]["symbol"], "XUSDT")
        self.assertEqual(rows[0]["direction"], "short")

    def test_header_located_by_content_not_line_zero(self):
        path = self._write_tmp("导出说明,,,,,,,,,,,\n" + HEADER + "\n" +
            "XUSDT Long·Cross,2026-06-01 10:00:00,2,2.1,50X,105USDT,"
            "4.9USDT,5USDT,0USDT,-0.05USDT,-0.05USDT,2026-06-01 11:00:00\n")
        rows, warnings = load_bitget_csv(path, kind="closed_pnl")
        self.assertEqual(len(rows), 1)
        self.assertEqual(warnings, [])

    def test_gb18030_fallback(self):
        path = self._write_tmp(HEADER + "\n" +
            "XUSDT Long·Cross,2026-06-01 10:00:00,2,2.1,50X,105USDT,"
            "4.9USDT,5USDT,0USDT,-0.05USDT,-0.05USDT,2026-06-01 11:00:00\n",
            encoding="gb18030")
        rows, warnings = load_bitget_csv(path, kind="closed_pnl")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["symbol"], "XUSDT")

    def test_unknown_contract_format_warns_and_skips(self):
        path = self._write_tmp(HEADER + "\n" +
            "WEIRDFORMAT,2026-06-01 10:00:00,2,2.1,50X,105USDT,"
            "4.9USDT,5USDT,0USDT,-0.05USDT,-0.05USDT,2026-06-01 11:00:00\n")
        rows, warnings = load_bitget_csv(path, kind="closed_pnl")
        self.assertEqual(rows, [])
        self.assertEqual(len(warnings), 1)

    def test_checksum_mismatch_warns_but_keeps_row(self):
        # 仓位盈亏故意写错：应=4.9，写成 4.0
        path = self._write_tmp(HEADER + "\n" +
            "XUSDT Long·Cross,2026-06-01 10:00:00,2,2.1,50X,105USDT,"
            "4.0USDT,5USDT,0USDT,-0.05USDT,-0.05USDT,2026-06-01 11:00:00\n")
        rows, warnings = load_bitget_csv(path, kind="closed_pnl")
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(warnings), 1)

    def test_unsupported_kind_raises(self):
        with self.assertRaises(ValueError):
            load_bitget_csv(FIXTURE, kind="fills")

    # --- Fix 1: 数字前缀资产（1000PEPE / 10000SATS）精确剥离，不再吞平仓量 ---

    def test_digit_prefixed_asset_qty_exact_strip(self):
        # 旧正则会把 "3501000PEPE" 误剥成 "3501000"；应按基础资产精确剥离 → "350"
        path = self._write_tmp(HEADER + "\n" +
            "1000PEPEUSDT Long·Cross,2026-06-01 10:00:00,0.002,0.0021,3501000PEPE,0.735USDT,"
            "4.9USDT,5USDT,0USDT,-0.05USDT,-0.05USDT,2026-06-01 11:00:00\n")
        rows, warnings = load_bitget_csv(path, kind="closed_pnl")
        self.assertEqual(warnings, [])
        self.assertEqual(rows[0]["symbol"], "1000PEPEUSDT")
        self.assertEqual(rows[0]["qty"], "350")

    def test_digit_prefixed_asset_decimal_qty_exact_strip(self):
        # 旧正则会把 "0.510000SATS" 误剥成 "0.510000"；应 → "0.5"
        path = self._write_tmp(HEADER + "\n" +
            "10000SATSUSDT Short·Cross,2026-06-01 10:00:00,2,1.9,0.510000SATS,0.95USDT,"
            "4.9USDT,5USDT,0USDT,-0.05USDT,-0.05USDT,2026-06-01 11:00:00\n")
        rows, warnings = load_bitget_csv(path, kind="closed_pnl")
        self.assertEqual(warnings, [])
        self.assertEqual(rows[0]["symbol"], "10000SATSUSDT")
        self.assertEqual(rows[0]["qty"], "0.5")

    # --- Fix 2: 空/垃圾单元格跳行不崩，缺列返回 warning 不 KeyError ---

    def test_empty_money_cell_skips_row_with_warning_others_loaded(self):
        path = self._write_tmp(HEADER + "\n" +
            "XUSDT Long·Cross,2026-06-01 10:00:00,2,2.1,50X,105USDT,"
            "4.9USDT,5USDT,,-0.05USDT,-0.05USDT,2026-06-01 11:00:00\n" +
            "YUSDT Long·Cross,2026-06-02 10:00:00,2,2.1,50Y,105USDT,"
            "4.9USDT,5USDT,0USDT,-0.05USDT,-0.05USDT,2026-06-02 11:00:00\n")
        rows, warnings = load_bitget_csv(path, kind="closed_pnl")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["symbol"], "YUSDT")
        self.assertEqual(len(warnings), 1)
        self.assertIn("第2行", warnings[0])
        self.assertIn("资金费用", warnings[0])

    def test_missing_required_column_returns_warning_not_keyerror(self):
        truncated = HEADER.replace("平仓量,", "")
        path = self._write_tmp(truncated + "\n" +
            "XUSDT Long·Cross,2026-06-01 10:00:00,2,2.1,105USDT,"
            "4.9USDT,5USDT,0USDT,-0.05USDT,-0.05USDT,2026-06-01 11:00:00\n")
        rows, warnings = load_bitget_csv(path, kind="closed_pnl")
        self.assertEqual(rows, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("平仓量", warnings[0])


class TestClosedRowHash(unittest.TestCase):
    def test_stable_across_reloads(self):
        rows1, _ = load_bitget_csv(FIXTURE, kind="closed_pnl")
        rows2, _ = load_bitget_csv(FIXTURE, kind="closed_pnl")
        self.assertEqual([r["row_hash"] for r in rows1],
                         [r["row_hash"] for r in rows2])
        self.assertEqual(len(rows1[0]["row_hash"]), 16)

    def test_qty_change_changes_hash(self):
        rows, _ = load_bitget_csv(FIXTURE, kind="closed_pnl")
        r2 = dict(rows[0]); r2["qty"] = "101"
        self.assertNotEqual(closed_row_hash(rows[0]), closed_row_hash(r2))

    def test_same_symbol_different_rounds_no_collision(self):
        # fills 向 row_hash 的坑：closed-pnl 记录里 time/side/price 等全缺失，
        # 同 symbol 所有回合会碰撞。closed_row_hash 必须区分。
        rows, _ = load_bitget_csv(FIXTURE, kind="closed_pnl")
        hashes = {r["row_hash"] for r in rows}
        self.assertEqual(len(hashes), len(rows))


class TestDedupClosedRounds(unittest.TestCase):
    def test_same_hash_no_source_id_suspected_not_dropped(self):
        rows, _ = load_bitget_csv(FIXTURE, kind="closed_pnl")
        kept, suspected = dedup_closed_rounds(rows + [dict(rows[0])])
        self.assertEqual(len(kept), 5)       # 不静默删
        self.assertEqual(len(suspected), 1)

    def test_distinct_rounds_all_kept(self):
        rows, _ = load_bitget_csv(FIXTURE, kind="closed_pnl")
        kept, suspected = dedup_closed_rounds(rows)
        self.assertEqual(len(kept), 4)
        self.assertEqual(suspected, [])

    def test_source_id_dedup_direct(self):
        a = {"source_id": "ID1", "close_time": "t", "exchange": "bitget",
             "symbol": "X", "direction": "long", "open_avg": "1",
             "close_avg": "2", "qty": "1", "realized_pnl": "1"}
        kept, suspected = dedup_closed_rounds([a, dict(a)])
        self.assertEqual(len(kept), 1)
        self.assertEqual(suspected, [])


class TestDedupCrossSource(unittest.TestCase):
    def _r(self, sid, **kw):
        base = {"close_time": "2026-06-05 10:00:00", "exchange": "bitget", "symbol": "ETHUSDT",
                "direction": "long", "open_avg": "1500", "close_avg": "1550", "qty": "1",
                "realized_pnl": "50", "fee": "1", "source_id": sid}
        base.update(kw); return base

    def test_id_row_then_idless_same_round_is_suspected(self):
        with_id = self._r("pos123")          # API 来源
        no_id = self._r("")                  # CSV 兜底来源，同一回合
        kept, suspected = dedup_closed_rounds([with_id, no_id])
        self.assertEqual(len(kept), 2)       # 不静默删
        self.assertEqual(len(suspected), 1)  # 但要标出来


class TestLoadedRowsFeedPnlStats(unittest.TestCase):
    def test_fixture_stats(self):
        rows, _ = load_bitget_csv(FIXTURE, kind="closed_pnl")
        s = compute_pnl_stats(rows)
        self.assertEqual(s["rounds"], 4)
        self.assertEqual(s["wins"], 2)
        self.assertEqual(s["losses"], 2)
        # net_pnl = Σ仓位盈亏 = 9.926 - 25.59 + 9.888 - 2.0632
        self.assertAlmostEqual(s["net_pnl"], -7.8392, delta=1e-6)


class TestWeeklyChange(unittest.TestCase):
    def test_change(self):
        self.assertAlmostEqual(weekly_change([100.0, 90.0]), -0.10)
        self.assertAlmostEqual(weekly_change([100.0, 90.0, 99.0]), 0.10)

    def test_short_series(self):
        self.assertIsNone(weekly_change([100.0]))
        self.assertIsNone(weekly_change([]))

    def test_zero_prev(self):
        self.assertIsNone(weekly_change([0.0, 50.0]))


class TestThousandsSeparator(unittest.TestCase):
    def test_comma_number_parses_fully(self):
        from parse_trades import _strip_suffix
        self.assertEqual(_strip_suffix("5,062.5USDT"), "5062.5")
        self.assertEqual(_strip_suffix("1,298USELESS"), "1298")
    def test_garbage_remainder_rejected(self):
        from parse_trades import _strip_suffix
        self.assertIsNone(_strip_suffix("5.062.5USDT"))   # 异常格式整体拒绝

    def test_invalid_grouping_rejected(self):
        # 逗号仅在合法千分位分组（\d{1,3}(,\d{3})+）时剔除；其余逗号用法整体拒绝
        from parse_trades import _strip_suffix
        self.assertIsNone(_strip_suffix("1,2,9USDT"))     # 非法分组，旧实现静默成 "129"
        self.assertIsNone(_strip_suffix("5.062,5USDT"))   # 欧式小数逗号，旧实现静默成 "5.0625"


class TestBreakeven(unittest.TestCase):
    def test_breakeven_counted(self):
        s = compute_pnl_stats([{"realized_pnl": "0", "fee": "0"},
                               {"realized_pnl": "10", "fee": "0"}])
        self.assertEqual(s["breakeven"], 1)
        self.assertEqual(s["wins"], 1)
        self.assertEqual(s["rounds"], 2)
    def test_empty_has_breakeven_zero(self):
        self.assertEqual(compute_pnl_stats([])["breakeven"], 0)


class TestFxNoiseIsolation(unittest.TestCase):
    """v1.1 设计验收 #4：汇率噪声隔离。USDT 权益走平时，汇率下行会让
    RMB 折算序列出现纯汇率假回撤——这就是回撤主序列必须用 USDT 的原因。"""

    USDT = [1000.0, 1000.0, 1000.0]
    RATES = [7.2, 7.0, 6.8]

    def test_flat_usdt_equity_zero_drawdown(self):
        self.assertEqual(drawdown_from_peak(self.USDT), 0.0)

    def test_rmb_series_shows_fx_only_drawdown(self):
        rmb = [e * r for e, r in zip(self.USDT, self.RATES)]
        self.assertEqual(rmb, [7200.0, 7000.0, 6800.0])
        dd = drawdown_from_peak(rmb)
        self.assertGreater(dd, 0.0)
        self.assertAlmostEqual(dd, (7.2 - 6.8) / 7.2)   # ≈0.0556，全是汇率噪声


class TestSetupGrouping(unittest.TestCase):
    """v1.1 设计验收 #5：setup 分组聚合。钉住 review SKILL 规定的分组配方——
    按 setup 标签做朴素 dict groupby，每组独立喂 compute_pnl_stats。"""

    def test_groupby_setup_then_stats_per_group(self):
        rounds = [
            {"setup": "trend",     "realized_pnl": "100", "fee": "0"},
            {"setup": "trend",     "realized_pnl": "50",  "fee": "0"},
            {"setup": "reversal",  "realized_pnl": "-30", "fee": "0"},
            {"setup": "unplanned", "realized_pnl": "-10", "fee": "0"},
            {"setup": "",          "realized_pnl": "5",   "fee": "0"},  # 未标注
        ]
        groups = {}
        for r in rounds:
            groups.setdefault(r.get("setup", ""), []).append(r)
        stats = {k: compute_pnl_stats(v) for k, v in groups.items()}

        self.assertEqual(stats["trend"]["rounds"], 2)
        self.assertAlmostEqual(stats["trend"]["win_rate"], 1.0)
        self.assertAlmostEqual(stats["trend"]["net_pnl"], 150.0)

        self.assertEqual(stats["reversal"]["rounds"], 1)
        self.assertAlmostEqual(stats["reversal"]["win_rate"], 0.0)
        self.assertAlmostEqual(stats["reversal"]["net_pnl"], -30.0)

        self.assertEqual(stats["unplanned"]["rounds"], 1)
        self.assertAlmostEqual(stats["unplanned"]["win_rate"], 0.0)
        self.assertAlmostEqual(stats["unplanned"]["net_pnl"], -10.0)

        self.assertEqual(stats[""]["rounds"], 1)
        self.assertAlmostEqual(stats[""]["win_rate"], 1.0)
        self.assertAlmostEqual(stats[""]["net_pnl"], 5.0)

        # 分组无遗漏：各组回合数之和 = 总回合数
        self.assertEqual(sum(s["rounds"] for s in stats.values()), len(rounds))


class TestLoadEquity(unittest.TestCase):
    def _write(self, body):
        f = tempfile.NamedTemporaryFile('w', suffix='.csv', delete=False, encoding='utf-8')
        f.write("week,as_of,equity_usdt,usdt_cny_rate,equity_rmb,net_flow_usdt,note\n" + body)
        f.close(); self.addCleanup(os.unlink, f.name); return f.name

    def test_sorted_by_week(self):
        p = self._write("2026-W25,2026-06-19,4300,,,0,\n2026-W24,2026-06-12,4255.36,,,0,\n")
        rows = load_equity(p)
        self.assertEqual([r["week"] for r in rows], ["2026-W24", "2026-W25"])
        self.assertEqual(rows[0]["equity_usdt"], "4255.36")

    def test_duplicate_week_raises(self):
        p = self._write("2026-W24,2026-06-12,1,,,0,\n2026-W24,2026-06-13,2,,,0,\n")
        with self.assertRaises(ValueError):
            load_equity(p)

    def test_bad_week_format_raises(self):
        p = self._write("2026-W7,2026-02-15,1,,,0,\n")   # 必须两位零填充
        with self.assertRaises(ValueError):
            load_equity(p)


if __name__ == "__main__":
    unittest.main()
