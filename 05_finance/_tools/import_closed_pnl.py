#!/usr/bin/env python3
"""导入 Bitget 已平仓盈亏：load（CSV / API）→ 去重 → append → JSON 报告。

去重规则（risk/_schema.md §2）：
- source_id 命中存量 = **确定重复**，直接 skipped（positionId 相同即同一回合，不看 source_file——
  API 重拉、CSV 回填 id 后跨源重见皆属此类）；
- 仅无 id 行的 hash 命中才走重放豁免：source_file 相同 → skipped；不同 → suspected（不入库，人工确认）。
存量行 id 与 hash **分别登记**（互盲修复的存量侧）：id 回填后重放原 CSV（行无 id）仍按 hash 命中跳过。

--source api：fetch_bitget.fetch_closed_pnl 直拉（默认窗口近 90 天 = 回溯上限），同一管道落盘；
--equity（api 限定）：导入后拉全账户权益，当周 equity 行缺失才写自动行（note=auto），已存在报 exists。"""
import argparse, csv, json, os, sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_trades

_TZ_UTC8 = timezone(timedelta(hours=8))   # 固定 UTC+8，与 close_time / 探针同口径

STORE_FIELDS = ["close_time", "exchange", "market_type", "symbol", "direction", "open_avg",
                "close_avg", "qty", "realized_pnl", "fee", "source_id", "source_file", "row_hash", "setup"]

EQUITY_FIELDS = ["week", "as_of", "equity_usdt", "usdt_cny_rate", "equity_rmb", "net_flow_usdt", "note"]

def build_parser():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source_csv", nargs="?", help="源 CSV 路径（--source csv 必填；api 路径忽略）")
    ap.add_argument("--store", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "risk", "closed-pnl.csv"))
    ap.add_argument("--exchange", default="bitget")
    ap.add_argument("--kind", default="closed_pnl")
    ap.add_argument("--source", choices=("csv", "api"), default="csv")
    ap.add_argument("--since", help="api 限定：拉取窗口起点 YYYY-MM-DD（UTC+8 零点）；默认 90 天前（回溯上限）")
    ap.add_argument("--equity", action="store_true",
                    help="api 限定：导入后拉 all-account-balance 写当周 equity 自动行（已有行则报 exists 不写）")
    return ap

def _api_window(since):
    """--since → [start_ms, end_ms]（UTC+8 语义）；默认 90 天回溯（窗口上限）。"""
    now = datetime.now(_TZ_UTC8)
    if since:
        try:
            start = datetime.strptime(since, "%Y-%m-%d").replace(tzinfo=_TZ_UTC8)
        except ValueError:
            raise SystemExit(f"--since 格式非法（需 YYYY-MM-DD）: {since!r}")
    else:
        start = now - timedelta(days=90)
    return (int(start.timestamp() * 1000), int(now.timestamp() * 1000),
            start.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d"))

def _equity_auto(store_path):
    """当周 equity 自动行：缺则拉权益求和写入（note=auto），已存在 → exists 不写不拉
    （覆盖问询是 skill 层的事）。文件 = <store 同级>/equity/<ISO 年 %G>.csv。"""
    import bitget_api
    now = datetime.now(_TZ_UTC8)
    week = now.strftime("%G-W%V")
    eq_path = os.path.join(os.path.dirname(os.path.abspath(store_path)), "equity", now.strftime("%G") + ".csv")
    if os.path.exists(eq_path):
        for r in parse_trades.load_equity(eq_path):
            if r["week"] == week:
                return {"status": "exists", "week": week, "value": r.get("equity_usdt", "")}
    total = sum(float(it["usdtBalance"]) for it in bitget_api.all_account_balance())
    value = f"{total:.2f}"
    write_header = not os.path.exists(eq_path) or os.path.getsize(eq_path) == 0
    os.makedirs(os.path.dirname(eq_path), exist_ok=True)
    with open(eq_path, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=EQUITY_FIELDS)
        if write_header:
            w.writeheader()
        w.writerow({"week": week, "as_of": now.strftime("%Y-%m-%d"), "equity_usdt": value,
                    "usdt_cny_rate": "", "equity_rmb": "", "net_flow_usdt": "0", "note": "auto"})
    return {"status": "written", "week": week, "value": value}

def run_import(args):
    """主逻辑（main() 的薄包装对象）：返回 JSON 报告 dict，不打印。测试直调此函数 mock 网络边界。"""
    window = None
    if args.source == "api":
        import fetch_bitget
        start_ms, end_ms, since_s, until_s = _api_window(args.since)
        new_rows, warnings = fetch_bitget.fetch_closed_pnl(start_ms, end_ms), []
        window = [since_s, until_s]
    else:
        if not args.source_csv:
            raise SystemExit("source_csv 必填（--source csv 路径）")
        if args.equity:
            raise SystemExit("--equity 仅在 --source api 下可用")
        loader = getattr(parse_trades, parse_trades.LOADERS[(args.exchange, args.kind)])
        new_rows, warnings = loader(args.source_csv, kind=args.kind)

    existing = []
    if os.path.exists(args.store):
        with open(args.store, encoding="utf-8") as fh:
            existing = list(csv.DictReader(fh))
    seen_ids = set()      # id 命中 = 确定重复
    seen_hashes = {}      # hash → source_file（无 id 行的重放豁免判据）
    for r in existing:    # id 与 hash 分别登记（存量侧互盲修复）
        if r.get("source_id"):
            seen_ids.add(r["source_id"])
        if r.get("row_hash"):
            seen_hashes[r["row_hash"]] = r.get("source_file", "")

    added, skipped, suspected = [], 0, []
    for r in new_rows:
        sid = r.get("source_id") or ""
        if sid and sid in seen_ids:
            skipped += 1                          # id 命中：确定重复，不看 source_file
            continue
        h = r.get("row_hash") or ""
        if h and h in seen_hashes:
            if seen_hashes[h] == r.get("source_file", ""):
                skipped += 1                      # 同文件重放豁免
            else:
                suspected.append(r)               # 无 id 的跨文件 hash 命中 → 人工确认
            continue
        r.setdefault("setup", "unlabeled")
        added.append(r)
        if sid:
            seen_ids.add(sid)
        if h:
            seen_hashes[h] = r.get("source_file", "")

    if added:
        # 文件不存在或 0 字节（空文件 append 不补表头会让首行数据被当表头）都要写表头
        write_header = not os.path.exists(args.store) or os.path.getsize(args.store) == 0
        with open(args.store, "a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=STORE_FIELDS)
            if write_header:
                w.writeheader()
            w.writerows({k: r.get(k, "") for k in STORE_FIELDS} for r in added)

    weeks = sorted({r["close_time"][:10] for r in added})
    report = {"source": args.source,
              "added": len(added), "skipped": skipped, "suspected": len(suspected),
              "warnings": warnings, "date_range": weeks[:1] + weeks[-1:],
              "suspected_rows": [{k: r.get(k) for k in ("close_time", "symbol", "realized_pnl")} for r in suspected]}
    if window:
        report["window"] = window
    if args.equity:
        report["equity"] = _equity_auto(args.store)
    return report

def main(argv=None):
    args = build_parser().parse_args(argv)
    print(json.dumps(run_import(args), ensure_ascii=False))

if __name__ == "__main__":
    main()
