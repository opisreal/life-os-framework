#!/usr/bin/env bash
# finance monthly reminder — 由 launchd 触发
# 每月 3 日 09:00 提醒做上月月度复盘

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LIFEOS_ROOT="$(cd "$MODULE_ROOT/.." && pwd)"
MANIFEST="$MODULE_ROOT/.manifest.json"
NOTIFY="$LIFEOS_ROOT/.tools/notify.sh"

# 计算上月（如今天 2026-06-03，则上月 = 2026-05）
LAST_MONTH=$(date -v-1m +%Y-%m 2>/dev/null || date -d "last month" +%Y-%m)
NOW_ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# 读 manifest
SKIP_COUNT=$(jq -r '.cron["monthly-reminder"]["skip-count"] // 0' "$MANIFEST")
LAST_RUN=$(jq -r '.cron["monthly-reminder"]["last-run"] // "never"' "$MANIFEST")

# 判断上月复盘是否已生成
REVIEW_FILE="$MODULE_ROOT/reviews/monthly/${LAST_MONTH}-review.md"
if [[ -f "$REVIEW_FILE" ]]; then
  NEW_SKIP=0
else
  NEW_SKIP=$((SKIP_COUNT + 1))
fi

# 统计数据预检
SNAP_COUNT=$(find "$MODULE_ROOT/snapshots" -name "${LAST_MONTH}.md" 2>/dev/null | wc -l | tr -d ' ')
SPEND_COUNT=$(find "$MODULE_ROOT/spending" -name "${LAST_MONTH}.md" 2>/dev/null | wc -l | tr -d ' ')
GOAL_ACTIVE_COUNT=$(jq -r '.goals.active | length' "$MANIFEST")

# 状态预警（只读 pyramid.md 里的状态符号，不读具体金额）
PYRAMID="$MODULE_ROOT/goals/pyramid.md"
WARN_LINES=""
if [[ -f "$PYRAMID" ]]; then
  WARN_LINES=$(grep -E "(⚠️|❌)" "$PYRAMID" | sed -E 's/[0-9]+(万|元|%|RMB)//g; s/  +/ /g' | head -5)
fi

# 组装文案
TITLE="📅 [Life OS · finance] 上月（${LAST_MONTH}）复盘窗口已开"

PREFIX=""
if [[ "$NEW_SKIP" -ge 2 ]]; then
  PREFIX="⚠️ 已跳过 ${NEW_SKIP} 次月度复盘，是否调整节奏？

"
fi

BODY="${PREFIX}距上次触发: ${LAST_RUN}
期间数据: ${SNAP_COUNT} 份 snapshot · ${SPEND_COUNT} 份 spending · ${GOAL_ACTIVE_COUNT} 个 active goal

状态预警:
${WARN_LINES:-（无明显预警）}

→ 打开 Claude Code 执行: /finance review month

—— 05_finance/_tools/monthly-reminder.sh @ $(date '+%Y-%m-%d %H:%M:%S')"

# 推送
"$NOTIFY" "$TITLE" "$BODY"
NOTIFY_EXIT=$?

# 更新 manifest（无论推送成功否，last-run 都更新）
TMP=$(mktemp)
jq --arg now "$NOW_ISO" --argjson skip "$NEW_SKIP" \
  '.cron["monthly-reminder"]["last-run"] = $now | .cron["monthly-reminder"]["skip-count"] = $skip' \
  "$MANIFEST" > "$TMP" && mv "$TMP" "$MANIFEST"

# git commit
cd "$LIFEOS_ROOT"
git add 05_finance/.manifest.json
git commit -m "chore(finance): monthly reminder fired $(date '+%Y-%m-%d')" --quiet || true

exit $NOTIFY_EXIT
