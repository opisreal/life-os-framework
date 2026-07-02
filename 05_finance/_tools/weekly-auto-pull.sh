#!/usr/bin/env bash
# 步骤② 全自动周拉取（MVP-1.6 终态）：API 拉已平仓+权益+成交明细 → 写表 → commit → 通知。
# 任何一步失败 → 降级执行 weekly-submit-reminder.sh 催促真值表（人肉 CSV 路径永远可用）。
# 对账/文案组装/lint 一致性检查在 weekly_pull.py（TDD 覆盖），本脚本只做编排。
# launchd 双槽（周日 20:00 + 21:30 重试）：同周已通知且无新增无异常 → 静默退出（marker 防重复通知）。
# 测试缝：PULL_CMD 环境变量可替换拉取命令（如 PULL_CMD=false 模拟失败分支，此时跳过 fills）。
set -uo pipefail
ROOT="/Users/USERNAME/life-os"
TOOLS="$ROOT/05_finance/_tools"
NOTIFY="$ROOT/.tools/notify.sh"
MARKER="$ROOT/.tools/logs/finance-auto-pull.notified"
cd "$ROOT"
WEEK="$(date +%G-W%V)"

degrade() {
  "$NOTIFY" "⚠️ [Life OS · finance] 自动拉取失败：$1" "已降级为催促模式。手动兜底：python3 05_finance/_tools/import_closed_pnl.py --source api --equity（或导 CSV 走 finance-import）" finance || true
  exec /bin/bash "$TOOLS/weekly-submit-reminder.sh"
}

# 1) 拉取（已平仓+权益自动行；成交明细单独一拉，任一失败都降级）
if [ -n "${PULL_CMD:-}" ]; then
  REPORT="$($PULL_CMD)" || degrade "拉取命令退出非零"
  FILLS_REPORT='{"added":0,"skipped":0,"suspected":0,"warnings":[]}'
else
  REPORT="$(python3 "$TOOLS/import_closed_pnl.py" --source api --equity)" || degrade "import 脚本退出非零"
  FILLS_REPORT="$(python3 "$TOOLS/import_closed_pnl.py" --source api --kind fills)" || degrade "fills 拉取退出非零"
fi

# 2) 对账 + lint + 组装（weekly_pull.py，纯逻辑已测）
OUT="$(REPORT="$REPORT" FILLS_REPORT="$FILLS_REPORT" python3 "$TOOLS/weekly_pull.py")" || degrade "报告解析失败"
COMMIT="$(printf '%s\n' "$OUT" | sed -n 's/^COMMIT=//p')"
FLAGGED="$(printf '%s\n' "$OUT" | sed -n 's/^FLAGGED=//p')"
TITLE="$(printf '%s\n' "$OUT" | sed -n 's/^TITLE=//p')"
BODY="$(printf '%s\n' "$OUT" | sed -n 's/^BODY=//p')"

# 3) 有新数据才 commit（沿用 reminder 自动 commit 先例；无新增不产生空提交）
if [ "$COMMIT" = "yes" ]; then
  ISOYEAR="$(date +%G)"
  git add 05_finance/risk/closed-pnl.csv 05_finance/risk/trades.csv "05_finance/risk/equity/${ISOYEAR}.csv" || degrade "git add 失败"
  git commit -m "feat(finance): weekly auto-pull ${WEEK}（自动入账+权益行+成交明细，weekly-auto-pull.sh）" || degrade "git commit 失败"
fi

# 4) 通知（重试槽防重复：同周已通知且无新增无异常 → 静默）
if [ "$COMMIT" = "no" ] && [ "$FLAGGED" = "no" ] && [ -f "$MARKER" ] && [ "$(cat "$MARKER")" = "$WEEK" ]; then
  exit 0
fi
"$NOTIFY" "$TITLE" "$BODY" finance && echo "$WEEK" > "$MARKER"
