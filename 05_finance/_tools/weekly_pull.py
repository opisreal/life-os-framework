#!/usr/bin/env python3
"""weekly-auto-pull 的对账/文案组装逻辑（自 shell heredoc 抽出，TDD 覆盖）。
shell（weekly-auto-pull.sh）只负责：调 import CLI、调本模块、git commit、notify。
compose() 为纯函数；main() 做 IO（环境变量进、KEY=VALUE 行出）。"""
import csv
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_trades

def load_equity_series(equity_dir):
    """跨年读全部 equity/<year>.csv（每个文件经 load_equity 守卫）→ 按 week 升序合并。
    单年读取会让跨年周（W01 的上一行在旧年文件）的对账静默失效，故一律走此函数。"""
    rows = []
    for fn in sorted(os.listdir(equity_dir)):
        if fn.endswith(".csv"):
            rows.extend(parse_trades.load_equity(os.path.join(equity_dir, fn)))
    return sorted(rows, key=lambda r: r["week"])

def compose(report, fills_report, equity_rows, closed_rows, lint_issues=None):
    """组装通知与提交决策：返回 {commit, flagged, title, body}。
    出入金对账：|ΔE − 期间净盈亏| / 上期权益 > 5% 才追问（期间=上期快照日之后的回合，
    同日快照前成交会混入——5% 阈值下可容忍的启发式）。"""
    added, skipped, suspected = report["added"], report["skipped"], report["suspected"]
    fills_added = fills_report.get("added", 0)
    warnings = report.get("warnings", []) + fills_report.get("warnings", [])
    eq_info = report.get("equity") or {}
    need_commit = added > 0 or fills_added > 0 or eq_info.get("status") == "written"

    recon = ""
    if len(equity_rows) >= 2:
        prev, curr = equity_rows[-2], equity_rows[-1]
        window = [r for r in closed_rows if r["close_time"] > prev["as_of"]]
        net = parse_trades.compute_pnl_stats(window)["net_pnl"]
        p = float(prev["equity_usdt"])
        if p > 0:
            gap = abs(float(curr["equity_usdt"]) - p - net) / p
            if gap > 0.05:
                recon = (f"⚠️ 出入金对账：权益变动与期间净盈亏缺口 {gap:.1%}（>5%）"
                         f"——本周有出入金吗？回「出入金 <±USDT数>」登记")

    if eq_info.get("status") == "written":
        eq_line = f"权益 {eq_info.get('week', '')} = {eq_info.get('value', '')} USDT（自动行）"
    elif eq_info.get("status") == "exists":
        eq_line = "权益本周已有行（未覆盖，如需改用「记权益 <数>」）"
    else:
        eq_line = "⚠️ 权益行无状态（检查 --equity 分支）"

    parts = [f"已自动入账 {added} 回合（防重跳过 {skipped}）、成交明细 +{fills_added} 条", eq_line]
    if suspected:
        parts.append(f"⚠️ {suspected} 行疑似重复未入库，回「导入交易」逐条确认")
    if warnings:
        parts.append(f"⚠️ 解析 warnings {len(warnings)} 条（映射漂移嫌疑，看 launchd 日志）")
    if recon:
        parts.append(recon)
    if lint_issues:
        parts.append(f"⚠️ 数据一致性 {len(lint_issues)} 处异常（跑 lint_finance.py 看明细）")
    parts.append("回 setup 标签即出周报；无补充可直接说「周复盘」")

    flagged = bool(suspected or warnings or recon or lint_issues)
    title = ("⚠️ [Life OS · finance] 周材料已拉取（有待确认项）" if flagged
             else "✅ [Life OS · finance] 周报材料已备好")
    return {"commit": need_commit, "flagged": flagged, "title": title, "body": "；".join(parts)}

def main():
    report = json.loads(os.environ["REPORT"])
    fills_report = json.loads(os.environ["FILLS_REPORT"])
    equity_rows = load_equity_series(os.path.join("05_finance", "risk", "equity"))
    with open(os.path.join("05_finance", "risk", "closed-pnl.csv"), encoding="utf-8") as fh:
        closed_rows = list(csv.DictReader(fh))
    try:
        import lint_finance
        lint_issues = lint_finance.lint()
    except Exception as e:                       # lint 自身故障不阻塞周报
        lint_issues = [f"lint 未能运行: {e}"]
    out = compose(report, fills_report, equity_rows, closed_rows, lint_issues)
    print("COMMIT=" + ("yes" if out["commit"] else "no"))
    print("FLAGGED=" + ("yes" if out["flagged"] else "no"))
    print("TITLE=" + out["title"])
    print("BODY=" + out["body"])

if __name__ == "__main__":
    main()
