#!/usr/bin/env bash
# 步骤② 全自动周拉取（MVP-1.6 终态）：API 拉已平仓+权益 → 写表 → commit → 通知。
# 任何一步失败 → 降级执行 weekly-submit-reminder.sh 催促真值表（人肉 CSV 路径永远可用）。
# fills（成交明细）未校准，本版不拉——exchange-schemas.md fills 段补全后接入。
# 测试缝：PULL_CMD 环境变量可替换拉取命令（如 PULL_CMD=false 模拟失败分支），launchd 正常运行不设。
set -uo pipefail
ROOT="/Users/USERNAME/life-os"
TOOLS="$ROOT/05_finance/_tools"
NOTIFY="$ROOT/.tools/notify.sh"
cd "$ROOT"
WEEK="$(date +%G-W%V)"

degrade() {
  "$NOTIFY" "⚠️ [Life OS · finance] 自动拉取失败：$1" "已降级为催促模式。手动兜底：python3 05_finance/_tools/import_closed_pnl.py --source api --equity（或导 CSV 走 finance-import）" finance || true
  exec /bin/bash "$TOOLS/weekly-submit-reminder.sh"
}

# 1) 拉取（API 直拉 + 权益自动行）
if [ -n "${PULL_CMD:-}" ]; then
  REPORT="$($PULL_CMD)" || degrade "拉取命令退出非零"
else
  REPORT="$(python3 "$TOOLS/import_closed_pnl.py" --source api --equity)" || degrade "import 脚本退出非零"
fi

# 2) 解析报告 + 出入金对账（|ΔE − net_pnl|/prev > 5% 才追问）+ 组装通知
OUT="$(REPORT="$REPORT" python3 - <<'PY'
import csv, datetime, json, os, sys
sys.path.insert(0, "05_finance/_tools")
from parse_trades import load_equity, compute_pnl_stats

rep = json.loads(os.environ["REPORT"])
added, skipped, suspected = rep["added"], rep["skipped"], rep["suspected"]
warnings = rep.get("warnings", [])
eq_info = rep.get("equity") or {}
need_commit = added > 0 or eq_info.get("status") == "written"

recon = ""
isoyear = datetime.date.today().isocalendar()[0]
eq_path = f"05_finance/risk/equity/{isoyear}.csv"
try:
    eq = load_equity(eq_path)
    if len(eq) >= 2:
        prev, curr = eq[-2], eq[-1]
        # 期间口径：上期快照日之后的回合（同日快照前成交会混入，5% 阈值下可容忍）
        rows = [r for r in csv.DictReader(open("05_finance/risk/closed-pnl.csv"))
                if r["close_time"] > prev["as_of"]]
        net = compute_pnl_stats(rows)["net_pnl"]
        p = float(prev["equity_usdt"])
        if p > 0:
            gap = abs(float(curr["equity_usdt"]) - p - net) / p
            if gap > 0.05:
                recon = f"⚠️ 出入金对账：权益变动与期间净盈亏缺口 {gap:.1%}（>5%）——本周有出入金吗？回「出入金 <±USDT数>」登记"
except FileNotFoundError:
    pass  # 年初新文件未建等情况，不阻塞通知

if eq_info.get("status") == "written":
    eq_line = f"权益 {eq_info['week']} = {eq_info['value']} USDT（自动行）"
elif eq_info.get("status") == "exists":
    eq_line = "权益本周已有行（未覆盖，如需改用「记权益 <数>」）"
else:
    eq_line = "⚠️ 权益行无状态（检查 --equity 分支）"

parts = [f"已自动入账 {added} 回合（防重跳过 {skipped}）", eq_line]
if suspected:
    parts.append(f"⚠️ {suspected} 行疑似重复未入库，回「导入交易」逐条确认")
if warnings:
    parts.append(f"⚠️ 解析 warnings {len(warnings)} 条（映射漂移嫌疑，看 launchd 日志）")
if recon:
    parts.append(recon)
parts.append("回 setup 标签即出周报；无补充可直接说「周复盘」")

flagged = bool(suspected or warnings or recon)
print("COMMIT=" + ("yes" if need_commit else "no"))
print("TITLE=" + ("⚠️ [Life OS · finance] 周材料已拉取（有待确认项）" if flagged else "✅ [Life OS · finance] 周报材料已备好"))
print("BODY=" + "；".join(parts))
PY
)" || degrade "报告解析失败"

COMMIT="$(printf '%s\n' "$OUT" | sed -n 's/^COMMIT=//p')"
TITLE="$(printf '%s\n' "$OUT" | sed -n 's/^TITLE=//p')"
BODY="$(printf '%s\n' "$OUT" | sed -n 's/^BODY=//p')"

# 3) 有新数据才 commit（沿用 reminder 自动 commit 先例；无新增不产生空提交）
if [ "$COMMIT" = "yes" ]; then
  ISOYEAR="$(date +%G)"
  git add 05_finance/risk/closed-pnl.csv "05_finance/risk/equity/${ISOYEAR}.csv" || degrade "git add 失败"
  git commit -m "feat(finance): weekly auto-pull ${WEEK}（自动入账+权益行，weekly-auto-pull.sh）" || degrade "git commit 失败"
fi

# 4) 通知（周报材料就绪 / 待确认项）
"$NOTIFY" "$TITLE" "$BODY" finance
