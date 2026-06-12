#!/usr/bin/env bash
# finance quarterly reminder
# 每季度首月 5 日 09:30

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LIFEOS_ROOT="$(cd "$MODULE_ROOT/.." && pwd)"
MANIFEST="$MODULE_ROOT/.manifest.json"
NOTIFY="$LIFEOS_ROOT/.tools/notify.sh"

# 计算上季度
YEAR=$(date +%Y)
MONTH=$(date +%m)
case "$MONTH" in
  01|02|03) LAST_Q="$((YEAR-1))-Q4" ;;
  04|05|06) LAST_Q="${YEAR}-Q1" ;;
  07|08|09) LAST_Q="${YEAR}-Q2" ;;
  10|11|12) LAST_Q="${YEAR}-Q3" ;;
esac

NOW_ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)

SKIP_COUNT=$(jq -r '.cron["quarterly-reminder"]["skip-count"] // 0' "$MANIFEST")
LAST_RUN=$(jq -r '.cron["quarterly-reminder"]["last-run"] // "never"' "$MANIFEST")

REVIEW_FILE="$MODULE_ROOT/reviews/quarterly/${LAST_Q}-review.md"
if [[ -f "$REVIEW_FILE" ]]; then
  NEW_SKIP=0
else
  NEW_SKIP=$((SKIP_COUNT + 1))
fi

# 状态预警 — 统计连续 ⚠️/❌ 目标
PYRAMID="$MODULE_ROOT/goals/pyramid.md"
WARN_COUNT=0
if [[ -f "$PYRAMID" ]]; then
  WARN_COUNT=$(grep -cE "(⚠️|❌)" "$PYRAMID")
fi

TITLE="📅 [Life OS · finance] 上季度（${LAST_Q}）复盘窗口已开"

PREFIX=""
if [[ "$NEW_SKIP" -ge 2 ]]; then
  PREFIX="⚠️ 已跳过 ${NEW_SKIP} 次季度复盘，是否调整节奏？

"
fi

PLAN_HINT=""
if [[ "$WARN_COUNT" -ge 2 ]]; then
  PLAN_HINT="
💡 检测到 ${WARN_COUNT} 个目标处于 ⚠️/❌ 状态，复盘后建议跟 /finance plan"
fi

BODY="${PREFIX}距上次触发: ${LAST_RUN}
预警目标数（⚠️ + ❌）: ${WARN_COUNT}

→ 打开 Claude Code 执行: /finance review quarter${PLAN_HINT}

—— 05_finance/_tools/quarterly-reminder.sh @ $(date '+%Y-%m-%d %H:%M:%S')"

"$NOTIFY" "$TITLE" "$BODY"
NOTIFY_EXIT=$?

TMP=$(mktemp)
jq --arg now "$NOW_ISO" --argjson skip "$NEW_SKIP" \
  '.cron["quarterly-reminder"]["last-run"] = $now | .cron["quarterly-reminder"]["skip-count"] = $skip' \
  "$MANIFEST" > "$TMP" && mv "$TMP" "$MANIFEST"

cd "$LIFEOS_ROOT"
git add 05_finance/.manifest.json
git commit -m "chore(finance): quarterly reminder fired $(date '+%Y-%m-%d')" --quiet || true

exit $NOTIFY_EXIT
