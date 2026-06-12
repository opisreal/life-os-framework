#!/bin/bash
# tg-notify.sh — 发送通知到 Telegram 通知专用群
# 用法: tg-notify.sh "消息内容" [chat_id]
# token 复用 channel 插件的配置（~/.claude/channels/telegram/.env）
# 默认群组从 .tools/.env.private 读取（TG_NOTIFY_CHAT_ID，模板见 .env.example）

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$SCRIPT_DIR/.env.private" ] && source "$SCRIPT_DIR/.env.private"

ENV_FILE="$HOME/.claude/channels/telegram/.env"
TOKEN=$(grep -m1 '^TELEGRAM_BOT_TOKEN=' "$ENV_FILE" | cut -d= -f2-)
TEXT="${1:?用法: tg-notify.sh \"消息\" [chat_id]}"
CHAT_ID="${2:-${TG_NOTIFY_CHAT_ID:?未配置 TG_NOTIFY_CHAT_ID（见 .tools/.env.example）}}"

curl -sS --max-time 30 "https://api.telegram.org/bot${TOKEN}/sendMessage" \
  -d chat_id="${CHAT_ID}" \
  --data-urlencode text="${TEXT}"
