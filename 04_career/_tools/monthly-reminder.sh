#!/usr/bin/env bash
# career monthly reminder — 每月 1 日 09:00

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LIFEOS_ROOT="$(cd "$MODULE_ROOT/.." && pwd)"
MANIFEST="$MODULE_ROOT/.manifest.json"
NOTIFY="$LIFEOS_ROOT/.tools/notify.sh"

LAST_MONTH=$(date -v-1m +%Y-%m 2>/dev/null || date -d "last month" +%Y-%m)
NOW_ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)

SKIP_COUNT=$(jq -r '.cron["monthly-reminder"]["skip-count"] // 0' "$MANIFEST")
LAST_RUN=$(jq -r '.cron["monthly-reminder"]["last-run"] // "never"' "$MANIFEST")

REVIEW_FILE="$MODULE_ROOT/reviews/monthly/${LAST_MONTH}-review.md"
if [[ -f "$REVIEW_FILE" ]]; then
  NEW_SKIP=0
else
  NEW_SKIP=$((SKIP_COUNT + 1))
fi

# 统计上月新增事件（粗略：log + feedback + jd + interview）
LOG_YEAR=$(echo "$LAST_MONTH" | cut -c1-4)
LOG_COUNT=$(find "$MODULE_ROOT/log/$LOG_YEAR" -name "*.md" -newer "$MODULE_ROOT/.manifest.json" 2>/dev/null | wc -l | tr -d ' ' || echo 0)

# 识别 roadmap 中的潜在过期项（保守：只算 P0/P1 段下 unchecked todos）
ROADMAP_OVERDUE=0
if [[ -f "$MODULE_ROOT/roadmap.md" ]]; then
  ROADMAP_OVERDUE=$(awk '/^## 优先级 P[01]/,/^## 优先级 P[23]/' "$MODULE_ROOT/roadmap.md" 2>/dev/null | grep -cE "^- \[ \]" | tr -d ' \n' || echo 0)
fi

TITLE="📅 [Life OS · career] 上月（${LAST_MONTH}）复盘窗口已开"

PREFIX=""
if [[ "$NEW_SKIP" -ge 2 ]]; then
  PREFIX="⚠️ 已跳过 ${NEW_SKIP} 次月复盘，是否调整节奏？

"
fi

OVERDUE_HINT=""
if [[ "$ROADMAP_OVERDUE" -gt 0 ]]; then
  OVERDUE_HINT="
⏰ roadmap P0/P1 段有 ${ROADMAP_OVERDUE} 项未完成"
fi

BODY="${PREFIX}距上次触发: ${LAST_RUN}
本月新增数据约: ${LOG_COUNT} 条${OVERDUE_HINT}

→ 打开 Claude Code 执行: /career review month

—— 04_career/_tools/monthly-reminder.sh @ $(date '+%Y-%m-%d %H:%M:%S')"

"$NOTIFY" "$TITLE" "$BODY"
NOTIFY_EXIT=$?

TMP=$(mktemp)
jq --arg now "$NOW_ISO" --argjson skip "$NEW_SKIP" \
  '.cron["monthly-reminder"]["last-run"] = $now | .cron["monthly-reminder"]["skip-count"] = $skip' \
  "$MANIFEST" > "$TMP" && mv "$TMP" "$MANIFEST"

cd "$LIFEOS_ROOT"
git add 04_career/.manifest.json
git commit -m "chore(career): monthly reminder fired $(date '+%Y-%m-%d')" --quiet || true

exit $NOTIFY_EXIT
