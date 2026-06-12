#!/usr/bin/env bash
# 每周提交探针：只认 git 提交（铁律 1）。真值表三态，完整态不发通知。
# 权益半 = HEAD 中本 ISO 周 equity 行存在；数据半 = 本周一以来 closed-pnl.csv 有提交。
set -euo pipefail
ROOT="/Users/USERNAME/life-os"
NOTIFY="$ROOT/.tools/notify.sh"
cd "$ROOT"
WEEK="$(date +%G-W%V)"; ISOYEAR="$(date +%G)"
EQUITY_REL="05_finance/risk/equity/${ISOYEAR}.csv"
DOW=$(date +%u)                                  # 1=周一 … 7=周日
MONDAY=$(date -v -$((DOW-1))d +%Y-%m-%d)
equity_ok="no"
if git show "HEAD:${EQUITY_REL}" 2>/dev/null | grep -q "^${WEEK},"; then equity_ok="yes"; fi
data_ok="no"
if git log --since="${MONDAY} 00:00" --oneline -- 05_finance/risk/closed-pnl.csv | grep -q .; then data_ok="yes"; fi
if [ "$equity_ok" = "yes" ]; then
  exit 0   # 完整态（含空仓周仅权益）：不发通知
elif [ "$data_ok" = "yes" ]; then
  TITLE="⚠️ [Life OS · finance] 还差本周权益"
  BODY="已收到交易数据。回复：记权益 <USDT数>（30 秒完成 ${WEEK}）"
else
  TITLE="⚠️ [Life OS · finance] 本周还没交数据"
  BODY="导一下 Bitget 本周已平仓报表，并回复：记权益 <USDT数>（${WEEK}）"
fi
"$NOTIFY" "$TITLE" "$BODY" finance
