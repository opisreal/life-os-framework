#!/usr/bin/env python3
"""导入 Bitget 已平仓盈亏：load → 去重（含重放豁免）→ append → JSON 报告。
重放豁免：新行 hash 命中存量且 source_file 相同 → skipped；source_file 不同 → suspected（不入库，人工确认）。"""
import argparse, csv, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_trades

STORE_FIELDS = ["close_time", "exchange", "market_type", "symbol", "direction", "open_avg",
                "close_avg", "qty", "realized_pnl", "fee", "source_id", "source_file", "row_hash", "setup"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source_csv")
    ap.add_argument("--store", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "risk", "closed-pnl.csv"))
    ap.add_argument("--exchange", default="bitget")
    ap.add_argument("--kind", default="closed_pnl")
    args = ap.parse_args()

    loader = getattr(parse_trades, parse_trades.LOADERS[(args.exchange, args.kind)])
    new_rows, warnings = loader(args.source_csv, kind=args.kind)

    existing = []
    if os.path.exists(args.store):
        with open(args.store, encoding="utf-8") as fh:
            existing = list(csv.DictReader(fh))
    seen = {}   # key → source_file（id 优先，hash 兜底）
    for r in existing:
        key = r.get("source_id") or r.get("row_hash")
        if key:
            seen[key] = r.get("source_file", "")

    added, skipped, suspected = [], 0, []
    for r in new_rows:
        key = r.get("source_id") or r.get("row_hash")
        if key in seen:
            if seen[key] == r.get("source_file", ""):
                skipped += 1                      # 同文件重放豁免
            else:
                suspected.append(r)               # 跨文件命中 → 人工确认
            continue
        r.setdefault("setup", "unlabeled")
        added.append(r); seen[key] = r.get("source_file", "")

    if added:
        # 文件不存在或 0 字节（空文件 append 不补表头会让首行数据被当表头）都要写表头
        write_header = not os.path.exists(args.store) or os.path.getsize(args.store) == 0
        with open(args.store, "a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=STORE_FIELDS)
            if write_header:
                w.writeheader()
            w.writerows({k: r.get(k, "") for k in STORE_FIELDS} for r in added)

    weeks = sorted({r["close_time"][:10] for r in added})
    print(json.dumps({"added": len(added), "skipped": skipped, "suspected": len(suspected),
                      "warnings": warnings, "date_range": weeks[:1] + weeks[-1:],
                      "suspected_rows": [{k: r.get(k) for k in ("close_time", "symbol", "realized_pnl")} for r in suspected]},
                     ensure_ascii=False))

if __name__ == "__main__":
    main()
