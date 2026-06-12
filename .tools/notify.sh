#!/usr/bin/env bash
# notify.sh — Life OS 通用消息发送器
# 用法: notify.sh "标题" "正文(支持多行)" [route-key]
#   route-key 可选；若提供且配置里 routes.<key> 存在则用该接收方，否则 fallback 到 default
# 配置: .tools/notify.config.private.json (gitignore)
# 退出码: 0 = 至少一个通道成功; 1 = 全部失败 / 配置缺失

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$SCRIPT_DIR/notify.config.private.json"

if [[ ! -f "$CONFIG" ]]; then
  echo "ERROR: $CONFIG not found. Copy notify.config.example.json and fill values." >&2
  exit 1
fi

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 \"title\" \"body\" [route-key]" >&2
  exit 1
fi

TITLE="$1"
BODY="$2"
ROUTE="${3:-}"
FULL_MSG="$TITLE

$BODY"

CHANNELS=$(jq -r '.enabled_channels[]' "$CONFIG")
SUCCESS=0
FAIL=0

# 按通道 + route key 解析实际接收方；找不到 routes.<key> 时回退到 default
resolve_receive_id() {
  local channel="$1"
  local route="$2"
  local field="$3"   # default_receive_id (lark) / default_chat_id (telegram)
  local rid
  if [[ -n "$route" ]]; then
    rid=$(jq -r --arg r "$route" ".${channel}.routes[\$r]? // empty" "$CONFIG")
    if [[ -n "$rid" ]]; then
      echo "$rid"
      return
    fi
  fi
  jq -r ".${channel}.${field}? // empty" "$CONFIG"
}

for CH in $CHANNELS; do
  case "$CH" in
    lark)
      RECEIVE_ID=$(resolve_receive_id lark "$ROUTE" default_receive_id)
      RECEIVE_ID_TYPE=$(jq -r '.lark.receive_id_type? // "chat_id"' "$CONFIG")
      if [[ -z "$RECEIVE_ID" ]]; then
        echo "WARN: lark.default_receive_id not set, skipping" >&2
        continue
      fi

      # lark-cli 用 --chat-id 或 --user-id；按 receive_id_type 选
      case "$RECEIVE_ID_TYPE" in
        chat_id)  ID_FLAG="--chat-id" ;;
        open_id)  ID_FLAG="--user-id" ;;
        *)
          echo "ERROR lark: unsupported receive_id_type '$RECEIVE_ID_TYPE' (use chat_id or open_id)" >&2
          FAIL=$((FAIL+1))
          continue
          ;;
      esac

      LARK_ERR=$(mktemp)
      RESP=$(lark-cli im +messages-send "$ID_FLAG" "$RECEIVE_ID" --text "$FULL_MSG" 2>"$LARK_ERR") || {
        echo "ERROR lark: lark-cli exit $? — $(cat "$LARK_ERR")" >&2
        rm -f "$LARK_ERR"
        FAIL=$((FAIL+1))
        continue
      }
      rm -f "$LARK_ERR"
      OK=$(echo "$RESP" | jq -r '.ok? // false' 2>/dev/null || echo "false")
      if [[ "$OK" == "true" ]]; then
        SUCCESS=$((SUCCESS+1))
      else
        echo "ERROR lark: $RESP" >&2
        FAIL=$((FAIL+1))
      fi
      ;;
    telegram)
      TOKEN=$(jq -r '.telegram.bot_token? // empty' "$CONFIG")
      CHAT_ID=$(resolve_receive_id telegram "$ROUTE" default_chat_id)
      if [[ -z "$TOKEN" || -z "$CHAT_ID" ]]; then
        echo "INFO: telegram not configured (missing bot_token or chat_id), skipping" >&2
        continue
      fi
      RESP=$(curl -sf -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
        --data-urlencode "chat_id=${CHAT_ID}" \
        --data-urlencode "text=${FULL_MSG}") || {
        echo "ERROR telegram: HTTP request failed (curl exit $?)" >&2
        FAIL=$((FAIL+1))
        continue
      }
      OK=$(echo "$RESP" | jq -r '.ok // false')
      if [[ "$OK" == "true" ]]; then
        SUCCESS=$((SUCCESS+1))
      else
        echo "ERROR telegram: $RESP" >&2
        FAIL=$((FAIL+1))
      fi
      ;;
    *)
      echo "WARN: unknown channel '$CH', skipping" >&2
      ;;
  esac
done

if [[ "$SUCCESS" -gt 0 ]]; then
  exit 0
else
  echo "ERROR: all channels failed or skipped" >&2
  exit 1
fi
