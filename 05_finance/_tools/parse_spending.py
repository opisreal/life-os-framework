#!/usr/bin/env python3
"""MVP-2 稳健层支出解析纯函数（内部 schema 见 stable/_schema.md §1）。
本文件只含**源无关**的纯函数；三源（支付宝/微信/银行）loader 待真实样本校准后
补入（spending-schemas.md 三段定版前不猜列名——铁律「列名不确定先校准」）。"""
import hashlib

# 代扣黑名单（stable/_schema.md §2）：银行流水对方户名命中 → 剔除银行侧条目。
# 模糊包含匹配；括号统一半角后比对（工商全称有全/半角变体）。
DEDUCT_BLACKLIST = ("财付通支付科技", "腾讯科技(深圳)", "支付宝(中国)网络技术",
                    "支付宝(中国)信息技术", "网商银行")

SPENDING_HASH_FIELDS = ("date", "source", "counterparty", "item", "amount_rmb")

def _norm_parens(s):
    return (s or "").replace("（", "(").replace("）", ")")

def is_deduct_counterparty(name):
    """银行流水对方户名是否为第三方支付代扣（命中 → 该条目剔除，明细侧为准）。"""
    n = _norm_parens(name)
    return any(b in n for b in DEDUCT_BLACKLIST)

def parse_category_rules(md_text):
    """解析 category-rules.md 的规则行「- 分类: 关键词, 关键词」→ {分类: [关键词]}。
    非规则行忽略；规则数据驱动，改分类只改 md 不改代码。"""
    rules = {}
    for line in md_text.splitlines():
        line = line.strip()
        if not line.startswith("- ") or ":" not in line:
            continue
        cat, _, kws = line[2:].partition(":")
        kws = [k.strip() for k in kws.split(",") if k.strip()]
        if cat.strip() and kws:
            rules[cat.strip()] = kws
    return rules

def classify(item, counterparty, rules):
    """关键词归类：item 或 counterparty 包含关键词即命中；未命中 → 'uncategorized'
    （交 LLM 批量列给用户审，不猜）。多分类命中取规则文件先定义者。"""
    text = f"{item or ''}|{counterparty or ''}"
    for cat, kws in rules.items():
        if any(k in text for k in kws):
            return cat
    return "uncategorized"

def spending_row_hash(rec):
    """支出行去重指纹（无 source_id 时兜底），sha256[:16]。
    字段集与 trades 的 row_hash / closed-pnl 的 closed_row_hash 不混用。"""
    key = "|".join(str(rec.get(f, "")) for f in SPENDING_HASH_FIELDS)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

def cut_summary_block(lines, start_marker, end_marker):
    """按**内容**裁掉账单头尾汇总块（标准库 csv 无 skiprows，先裁行再喂 reader）：
    返回 start_marker 行之后、end_marker 行之前的数据行（含表头行）。
    end_marker 缺席 → 裁到文件尾；start_marker 找不到 → ValueError（报错不猜行号）。
    marker 实测值由 spending-schemas.md 各源段登记（校准产物）。"""
    start = None
    for i, line in enumerate(lines):
        if start_marker in line:
            start = i + 1
            break
    if start is None:
        raise ValueError(f"裁切 marker 未命中: {start_marker!r}（账单格式变化？先重校准再导入）")
    out = []
    for line in lines[start:]:
        if end_marker and end_marker in line:
            break
        out.append(line)
    return out
