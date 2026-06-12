#!/usr/bin/env bash
# finance yearly reminder
# 每年 1 月 8 日 09:00

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LIFEOS_ROOT="$(cd "$MODULE_ROOT/.." && pwd)"
MANIFEST="$MODULE_ROOT/.manifest.json"
NOTIFY="$LIFEOS_ROOT/.tools/notify.sh"

LAST_YEAR=$(( $(date +%Y) - 1 ))
NOW_ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)

SKIP_COUNT=$(jq -r '.cron["yearly-reminder"]["skip-count"] // 0' "$MANIFEST")
LAST_RUN=$(jq -r '.cron["yearly-reminder"]["last-run"] // "never"' "$MANIFEST")

REVIEW_FILE="$MODULE_ROOT/reviews/yearly/${LAST_YEAR}-review.md"
if [[ -f "$REVIEW_FILE" ]]; then
  NEW_SKIP=0
else
  NEW_SKIP=$((SKIP_COUNT + 1))
fi

# 统计去年 snapshot 月份数
SNAP_MONTHS=$(find "$MODULE_ROOT/snapshots/${LAST_YEAR}" -name "${LAST_YEAR}-*.md" 2>/dev/null | wc -l | tr -d ' ')

TITLE="📅 [Life OS · finance] ${LAST_YEAR} 年度财报窗口已开"

PREFIX=""
if [[ "$NEW_SKIP" -ge 2 ]]; then
  PREFIX="⚠️ 已跳过 ${NEW_SKIP} 次年度财报，是否调整节奏？

"
fi

BODY="${PREFIX}距上次触发: ${LAST_RUN}
去年 snapshot 完整度: ${SNAP_MONTHS}/12 月

→ 打开 Claude Code 执行: /finance review year

提示: 年度复盘会主动询问 budget 是否需重定（偏离 >20% 时）+ 与 career 联动提示

—— 05_finance/_tools/yearly-reminder.sh @ $(date '+%Y-%m-%d %H:%M:%S')"

"$NOTIFY" "$TITLE" "$BODY"
NOTIFY_EXIT=$?

TMP=$(mktemp)
jq --arg now "$NOW_ISO" --argjson skip "$NEW_SKIP" \
  '.cron["yearly-reminder"]["last-run"] = $now | .cron["yearly-reminder"]["skip-count"] = $skip' \
  "$MANIFEST" > "$TMP" && mv "$TMP" "$MANIFEST"

cd "$LIFEOS_ROOT"
git add 05_finance/.manifest.json
git commit -m "chore(finance): yearly reminder fired $(date '+%Y-%m-%d')" --quiet || true

exit $NOTIFY_EXIT
