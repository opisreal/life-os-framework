#!/usr/bin/env bash
# career weekly reminder
# 每周一 09:00

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LIFEOS_ROOT="$(cd "$MODULE_ROOT/.." && pwd)"
MANIFEST="$MODULE_ROOT/.manifest.json"
NOTIFY="$LIFEOS_ROOT/.tools/notify.sh"

# 上一周 ISO week
LAST_WEEK=$(date -v-1w +%Y-W%V 2>/dev/null || date -d "last week" +%Y-W%V)
NOW_ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)

SKIP_COUNT=$(jq -r '.cron["weekly-reminder"]["skip-count"] // 0' "$MANIFEST")
LAST_RUN=$(jq -r '.cron["weekly-reminder"]["last-run"] // "never"' "$MANIFEST")

REVIEW_FILE="$MODULE_ROOT/reviews/weekly/${LAST_WEEK}-review.md"
if [[ -f "$REVIEW_FILE" ]]; then
  NEW_SKIP=0
else
  NEW_SKIP=$((SKIP_COUNT + 1))
fi

# 统计上周 log 条目数（粗略 — 上一周文件存在视为有数据）
LOG_FILE="$MODULE_ROOT/log/$(date +%Y)/${LAST_WEEK}.md"
LOG_COUNT=0
[[ -f "$LOG_FILE" ]] && LOG_COUNT=$(grep -cE "^- \[" "$LOG_FILE" || echo 0)

TITLE="📅 [Life OS · career] 上周（${LAST_WEEK}）复盘窗口已开"

PREFIX=""
if [[ "$NEW_SKIP" -ge 2 ]]; then
  PREFIX="⚠️ 已跳过 ${NEW_SKIP} 次周复盘，是否调整节奏？

"
fi

BODY="${PREFIX}距上次触发: ${LAST_RUN}
上周 log 条目: ${LOG_COUNT}

→ 打开 Claude Code 执行: /career review week

—— 04_career/_tools/weekly-reminder.sh @ $(date '+%Y-%m-%d %H:%M:%S')"

"$NOTIFY" "$TITLE" "$BODY"
NOTIFY_EXIT=$?

TMP=$(mktemp)
jq --arg now "$NOW_ISO" --argjson skip "$NEW_SKIP" \
  '.cron["weekly-reminder"]["last-run"] = $now | .cron["weekly-reminder"]["skip-count"] = $skip' \
  "$MANIFEST" > "$TMP" && mv "$TMP" "$MANIFEST"

cd "$LIFEOS_ROOT"
git add 04_career/.manifest.json
git commit -m "chore(career): weekly reminder fired $(date '+%Y-%m-%d')" --quiet || true

exit $NOTIFY_EXIT
