#!/usr/bin/env python3
"""risk 层数据一致性检查（只读，wiki-lint 范式）：
①两表表头与 KINDS 列集一致 ②row_hash 可复现 ③source_id 表内唯一
④setup 受控词表 ⑤equity 守卫（load_equity）+ 折算契约 equity_rmb=round(usdt×rate,2)。
独立 CLI 输出 JSON；weekly_pull 每周自动跑一次，异常进通知（不阻塞不降级）。"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_trades
from import_closed_pnl import STORE_FIELDS, TRADES_FIELDS

SETUP_VOCAB = {"trend", "reversal", "news", "scalp", "unplanned", "unlabeled"}

DEFAULT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "risk")

def _check_table(path, fields, hash_fn, hash_col, issues, setup_vocab=None):
    if not os.path.exists(path):
        return                                     # 表未建（空仓账户）合法
    with open(path, encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != fields:
            issues.append(f"{os.path.basename(path)}: 表头与 KINDS 列集不一致: {reader.fieldnames}")
            return
        rows = list(reader)
    seen_ids = set()
    for i, r in enumerate(rows, start=2):          # 行号含表头，报错可定位
        if hash_fn(r) != r.get(hash_col, ""):
            issues.append(f"{os.path.basename(path)}:{i}: row_hash 不可复现（字段被手改过？）")
        sid = r.get("source_id") or ""
        if sid:
            if sid in seen_ids:
                issues.append(f"{os.path.basename(path)}:{i}: source_id 重复 {sid}")
            seen_ids.add(sid)
        if setup_vocab is not None and r.get("setup") not in setup_vocab:
            issues.append(f"{os.path.basename(path)}:{i}: setup 非受控词表值 {r.get('setup')!r}")

def lint(root=DEFAULT_ROOT):
    """返回 issue 字符串列表（空 = 全部通过）。只读不修。"""
    issues = []
    _check_table(os.path.join(root, "closed-pnl.csv"), STORE_FIELDS,
                 parse_trades.closed_row_hash, "row_hash", issues, setup_vocab=SETUP_VOCAB)
    _check_table(os.path.join(root, "trades.csv"), TRADES_FIELDS,
                 parse_trades.row_hash, "row_hash", issues)
    eq_dir = os.path.join(root, "equity")
    if os.path.isdir(eq_dir):
        for fn in sorted(os.listdir(eq_dir)):
            if not fn.endswith(".csv"):
                continue
            path = os.path.join(eq_dir, fn)
            try:
                rows = parse_trades.load_equity(path)
            except ValueError as e:
                issues.append(f"equity/{fn}: {e}")
                continue
            for r in rows:
                rate, rmb = r.get("usdt_cny_rate", ""), r.get("equity_rmb", "")
                if rate and rmb:
                    want = round(float(r["equity_usdt"]) * float(rate), 2)
                    if abs(float(rmb) - want) > 0.005:
                        issues.append(f"equity/{fn} {r['week']}: equity_rmb={rmb} 违反契约"
                                      f"（应为 round({r['equity_usdt']}×{rate},2)={want}）")
    return issues

def main():
    issues = lint()
    print(json.dumps({"ok": not issues, "issues": issues}, ensure_ascii=False))
    return 0 if not issues else 1

if __name__ == "__main__":
    sys.exit(main())
