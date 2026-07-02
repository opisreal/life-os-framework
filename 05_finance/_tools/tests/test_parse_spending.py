import unittest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parse_spending import (is_deduct_counterparty, parse_category_rules, classify,
                            spending_row_hash, cut_summary_block)


class TestDeductBlacklist(unittest.TestCase):
    def test_variants_hit(self):
        for name in ("财付通支付科技有限公司",
                     "腾讯科技（深圳）有限公司",
                     "支付宝（中国）网络技术有限公司",
                     "支付宝(中国)信息技术有限公司",      # 半角括号变体
                     "浙江网商银行股份有限公司"):
            self.assertTrue(is_deduct_counterparty(name), name)

    def test_real_merchants_pass(self):
        for name in ("山姆会员商店", "沃尔玛（深圳）百货有限公司", ""):
            self.assertFalse(is_deduct_counterparty(name), name)


class TestClassify(unittest.TestCase):
    RULES_MD = "\n".join([
        "# 分类规则", "",
        "- 餐饮: 美团, 饿了么, 麦当劳",
        "- 交通: 滴滴, 地铁",
        "非规则行不解析",
    ])

    def test_parse_rules(self):
        rules = parse_category_rules(self.RULES_MD)
        self.assertEqual(rules["餐饮"], ["美团", "饿了么", "麦当劳"])
        self.assertEqual(len(rules), 2)

    def test_classify_by_item_and_counterparty(self):
        rules = parse_category_rules(self.RULES_MD)
        self.assertEqual(classify("美团订单-20260701", "北京三快在线", rules), "餐饮")
        self.assertEqual(classify("行程费用", "滴滴出行科技", rules), "交通")
        self.assertEqual(classify("不知道什么", "神秘商户", rules), "uncategorized")


class TestSpendingRowHash(unittest.TestCase):
    BASE = {"date": "2026-07-01", "source": "alipay", "counterparty": "山姆会员商店",
            "item": "购物", "amount_rmb": "358.00"}

    def test_stable_and_field_order_free(self):
        a = spending_row_hash(self.BASE)
        b = spending_row_hash(dict(reversed(list(self.BASE.items()))))
        self.assertEqual(a, b)
        self.assertEqual(len(a), 16)

    def test_amount_changes_hash(self):
        other = dict(self.BASE, amount_rmb="358.01")
        self.assertNotEqual(spending_row_hash(self.BASE), spending_row_hash(other))


class TestCutSummaryBlock(unittest.TestCase):
    LINES = ["支付宝账单明细", "起始时间:[2026-01-01]", "---------明细列表----------",
             "h1,h2,h3", "r1,r2,r3", "---------汇总----------", "总支出:100"]

    def test_cut_between_markers(self):
        out = cut_summary_block(self.LINES, start_marker="明细列表", end_marker="汇总")
        self.assertEqual(out, ["h1,h2,h3", "r1,r2,r3"])

    def test_no_end_marker_cuts_to_eof(self):
        out = cut_summary_block(self.LINES[:5], start_marker="明细列表", end_marker="汇总")
        self.assertEqual(out, ["h1,h2,h3", "r1,r2,r3"])

    def test_missing_start_marker_raises(self):
        with self.assertRaises(ValueError):    # 找不到 marker 报错，不猜行号
            cut_summary_block(self.LINES, start_marker="不存在的标记", end_marker="汇总")
