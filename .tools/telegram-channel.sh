#!/bin/bash
# telegram-channel.sh — 常驻 Telegram channel 会话看门狗（launchd 触发，每 300s）
# 1) tmux 会话不存在时拉起 claude --channels
# 2) 会话存在时做健康检查：bot.pid 的轮询进程必须是本会话的后代。
#    同项目开任何新 claude 会话都会自动加载 telegram 插件并触发其 takeover
#    逻辑（SIGTERM 旧 poller 抢走轮询），channel 会话从此收不到消息。
#    检测到劫持或 poller 已死时重启会话，新实例的 takeover 会夺回轮询。
# 人工查看：tmux attach -t claude-telegram （退出查看用 Ctrl-b d，不要 Ctrl-c）

set -u

SESSION="claude-telegram"
REPO="/Users/USERNAME/life-os"
TMUX="/opt/homebrew/bin/tmux"
CLAUDE="/opt/homebrew/bin/claude"
LOG_DIR="$REPO/.tools/logs"
LOG="$LOG_DIR/telegram-channel.log"
PID_FILE="$HOME/.claude/channels/telegram/bot.pid"

mkdir -p "$LOG_DIR"

log() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

launch() {
  log "$1，拉起 claude --channels"
  "$TMUX" new-session -d -s "$SESSION" -c "$REPO" \
    "$CLAUDE --channels plugin:telegram@claude-plugins-official" >> "$LOG" 2>&1
}

if ! "$TMUX" has-session -t "$SESSION" 2>/dev/null; then
  launch "session 不存在"
  exit 0
fi

# --- 健康检查：轮询权是否还在本会话手里 ---

# 刚启动的会话给 60s 缓冲，server 可能还没写 bot.pid
created=$("$TMUX" display-message -p -t "$SESSION" '#{session_created}' 2>/dev/null || echo 0)
if [ $(($(date +%s) - created)) -lt 60 ]; then
  exit 0
fi

pane_pid=$("$TMUX" list-panes -t "$SESSION" -F '#{pane_pid}' 2>/dev/null | head -1)

restart() {
  log "$1，重启 channel 会话夺回轮询"
  "$TMUX" kill-session -t "$SESSION" 2>/dev/null
  launch "重启"
  exit 0
}

bot_pid=$(cat "$PID_FILE" 2>/dev/null || echo "")
if [ -z "$bot_pid" ] || ! kill -0 "$bot_pid" 2>/dev/null; then
  restart "poller 不存在（bot.pid 缺失或进程已死）"
fi

# 从 bot_pid 沿 ppid 链上溯，必须能到达本会话的 pane 进程
pid=$bot_pid
while [ -n "$pid" ] && [ "$pid" -gt 1 ]; do
  if [ "$pid" = "$pane_pid" ]; then
    exit 0  # 轮询权归属正确
  fi
  pid=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')
done

restart "轮询被劫持（bot.pid=$bot_pid 非本会话后代）"
