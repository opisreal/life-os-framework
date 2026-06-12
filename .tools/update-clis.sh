#!/bin/bash
# update-clis.sh — 定时升级 claude-code / codex（launchd 触发，纯 bash，无 LLM 参与）
# 两者均为 Homebrew cask 安装；失败时通过 tg-notify.sh 通知 Telegram 通知群

set -u

LOG_DIR="/Users/USERNAME/life-os/.tools/logs"
LOG="$LOG_DIR/cli-update.log"
BREW="/opt/homebrew/bin/brew"
NOTIFY="/Users/USERNAME/life-os/.tools/tg-notify.sh"
CASKS="claude-code@latest codex"

mkdir -p "$LOG_DIR"

ver() { "/opt/homebrew/bin/$1" --version 2>/dev/null | head -1; }

{
  echo "[$(date '+%F %T')] cli-update start"
  before_claude=$(ver claude)
  before_codex=$(ver codex)

  "$BREW" update 2>&1 | tail -2
  if "$BREW" upgrade --cask $CASKS 2>&1; then
    after_claude=$(ver claude)
    after_codex=$(ver codex)
    echo "claude: $before_claude -> $after_claude"
    echo "codex:  $before_codex -> $after_codex"
    echo "[$(date '+%F %T')] cli-update done"
  else
    echo "[$(date '+%F %T')] cli-update FAILED (exit=$?)"
    "$NOTIFY" "⚠️ CLI 自动升级失败（claude-code/codex），详见 .tools/logs/cli-update.log" \
      || echo "tg 通知也失败了"
  fi
} >> "$LOG" 2>&1
