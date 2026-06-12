#!/bin/bash
# telegram-reset.sh — 远程重置 Telegram channel 会话（清空上下文）
# detached 延迟执行：给当前回合 5 秒把回复发回 Telegram，然后杀会话立即重建。
# 新会话由 telegram-channel.sh 拉起，其 takeover 逻辑会夺回轮询。

set -u

nohup bash -c '
  sleep 5
  /opt/homebrew/bin/tmux kill-session -t claude-telegram 2>/dev/null
  sleep 1
  /Users/USERNAME/life-os/.tools/telegram-channel.sh
' >/dev/null 2>&1 &

echo "已调度：5 秒后 channel 会话重建，上下文清空"
