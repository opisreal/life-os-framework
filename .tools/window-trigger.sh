#!/bin/bash
# window-trigger.sh — 每日定时推送（launchd 触发，claude headless 执行，模型锁定 sonnet）
# 用法: window-trigger.sh morning|noon|evening|midnight
#   morning  07:58 苏州+德州天气 + Claude Code/Codex 近24h版本更新 → Lark 群
#   noon     13:02 静默（仅回复 ok，验证调度窗口）
#   evening  18:05 国产大模型当日动态 → Lark 群
#   midnight 00:00 静默（仅回复 ok，验证调度窗口）

set -u

TASK="${1:?用法: window-trigger.sh morning|noon|evening|midnight}"
REPO="/Users/USERNAME/life-os"
LOG_DIR="$REPO/.tools/logs"
LOG="$LOG_DIR/window-trigger.log"
CLAUDE_BIN="/opt/homebrew/bin/claude"
NOTIFY="$REPO/.tools/tg-notify.sh"
TODAY=$(date +%F)
YESTERDAY=$(date -v-1d +%F)

mkdir -p "$LOG_DIR"

TOOLS="WebSearch,WebFetch,Bash($NOTIFY:*),Bash(.tools/tg-notify.sh:*)"
MAX_TURNS=50

case "$TASK" in
  morning)
    read -r -d '' PROMPT <<EOF
今天是 ${TODAY}。执行以下任务：

1. 搜索苏州市和山东省德州市今天的全天天气预报（白天/夜间天气、最高最低气温、风力、降水概率，如有恶劣天气预警需包含）。推荐数据源：中国气象局 weather.cma.cn（苏州站 58349，德州站 54714）。
2. 查询 Claude Code 和 OpenAI Codex CLI 在 ${YESTERDAY} 08:00 到今天 08:00 之间的版本功能更新：
   - Claude Code：抓取 https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md 的最新条目
   - Codex CLI：releases 网页为动态加载、直接抓取效果差，用 Atom feed https://github.com/openai/codex/releases.atom 获取最新 release，必要时对比相邻 tag 的 git diff 页面提取变更内容
   - 更新内容翻译为中文；该时间窗内无新版本则写「过去24小时无更新，当前最新版 vX.X.X」
3. 整理为一条简洁的中文消息，格式：
【今日早报 ${TODAY}】
■ 天气
苏州：…
德州：…
■ 版本更新
Claude Code vX.X.X：…
Codex vX.X.X：…
4. 用以下命令发送到 Telegram 通知群（已验证可用，纯文本，不要用 markdown 语法）：
   ${NOTIFY} "<消息内容>"
5. 发送失败时重试一次，仍失败则在输出中说明错误原因。发送成功即任务完成。
EOF
    ;;
  evening)
    read -r -d '' PROMPT <<EOF
今天是 ${TODAY}。执行以下任务：

1. 用 WebSearch 搜索今日国产大模型更新动态，覆盖国内主流厂商/模型：DeepSeek、通义千问 Qwen（阿里）、Kimi（月之暗面）、豆包（字节跳动）、智谱 GLM、MiniMax、阶跃星辰、百度文心、讯飞星火、腾讯混元等。关注：新模型发布、版本升级、能力更新、开源动作、价格调整、重要合作等。
2. 只收录今天（过去24小时内）的动态，每条注明厂商和要点；没有动态的厂商不要编造；整体无重要动态则写「今日无重要更新」。
3. 整理为一条简洁的中文消息，格式：
【国产大模型动态 ${TODAY}】
• 厂商/模型：动态摘要
• …
4. 用以下命令发送到 Telegram 通知群（已验证可用，纯文本，不要用 markdown 语法）：
   ${NOTIFY} "<消息内容>"
5. 发送失败时重试一次，仍失败则在输出中说明错误原因。发送成功即任务完成。
EOF
    ;;
  noon|midnight)
    PROMPT='仅回复"ok"。不要调用任何工具，不要搜索，不要发送任何消息。'
    TOOLS=""
    MAX_TURNS=3
    ;;
  *)
    echo "unknown task: $TASK" >&2
    exit 1
    ;;
esac

{
  echo "[$(date '+%F %T')] window-trigger:$TASK start"
  cd "$REPO" || exit 1
  if [ -n "$TOOLS" ]; then
    "$CLAUDE_BIN" -p "$PROMPT" --model sonnet --allowedTools "$TOOLS" --max-turns "$MAX_TURNS"
  else
    "$CLAUDE_BIN" -p "$PROMPT" --model sonnet --max-turns "$MAX_TURNS"
  fi
  rc=$?
  echo "[$(date '+%F %T')] window-trigger:$TASK exit=$rc"
} >> "$LOG" 2>&1
