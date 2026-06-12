#!/bin/bash
# export-framework.sh — 将 life-os 公共框架白名单导出到公共仓库 life-os-framework
# 机制：git ls-files ∩ 白名单前缀 − 排除规则 → 复制 → 路径脱敏 → 敏感扫描门 → commit+push
# 触发：手动运行，或主仓库 post-commit hook 自动触发（见 .tools/git-hooks/post-commit）
# 安全设计：白名单显式枚举（默认拒绝）；扫描门命中即中止并通知 TG 群

set -u

SRC="/Users/USERNAME/life-os"
DEST="$HOME/life-os-framework"
LOG="$SRC/.tools/logs/export-framework.log"
NOTIFY="$SRC/.tools/tg-notify.sh"

# 字面量黑名单从私有配置读取（LEAK_LITERALS），脚本本体不出现真实标识符
[ -f "$SRC/.tools/.env.private" ] && source "$SRC/.tools/.env.private"

mkdir -p "$(dirname "$LOG")"
exec >> "$LOG" 2>&1
echo "[$(date '+%F %T')] export 开始"

cd "$SRC" || exit 1

# ---------- 白名单（前缀匹配，显式枚举） ----------
INCLUDE_PREFIXES=(
  "CLAUDE.md"
  "README.md"
  "AGENTS.md"
  ".gitignore"
  ".claude/commands/"
  ".claude/skills/"
  ".claude/settings.json"
  ".tools/"
  "01_wiki/_meta/"
  "04_career/README.md"
  "04_career/_tools/"
  "05_finance/README.md"
  "05_finance/_tools/"
  "05_finance/_import/exchange-schemas.md"
)
# 骨架：各模块的 .gitkeep 保留目录结构
SKELETON_PATTERN='\.gitkeep$'

# ---------- 排除规则（在白名单内仍要剔除的） ----------
EXCLUDE_REGEX='(_design/|\.manifest\.json|notify\.config\.private|\.env\.private|settings\.local\.json|^\.tools/logs/)'

# ---------- 生成导出文件清单 ----------
FILELIST=$(mktemp)
{
  for p in "${INCLUDE_PREFIXES[@]}"; do
    git ls-files -- "$p"
  done
  git ls-files | grep -E "$SKELETON_PATTERN"
} | grep -vE "$EXCLUDE_REGEX" | sort -u > "$FILELIST"

COUNT=$(wc -l < "$FILELIST" | tr -d ' ')
echo "导出清单：$COUNT 个文件"

# ---------- 复制到导出仓库（保留 .git，清掉其余旧内容） ----------
if [ ! -d "$DEST/.git" ]; then
  echo "❌ $DEST 不是 git 仓库，先初始化（见脚本头部注释）"
  exit 1
fi
find "$DEST" -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +
rsync -a --files-from="$FILELIST" "$SRC/" "$DEST/"
rm -f "$FILELIST"

# ---------- 路径脱敏：机器相关绝对路径 → 占位符 ----------
grep -rlF '/Users/USERNAME' "$DEST" --exclude-dir=.git 2>/dev/null | while read -r f; do
  sed -i '' 's|/Users/USERNAME|/Users/USERNAME|g' "$f"
done

# ---------- 敏感扫描门（命中即中止） ----------
LITERAL_ARGS=()
[ -n "${LEAK_LITERALS:-}" ] && LITERAL_ARGS=(-e "$LEAK_LITERALS")
LEAK=$(grep -rnEI \
  -e '[0-9]{8,10}:[A-Za-z0-9_-]{35}' \
  -e 'oc_[a-z0-9]{16,}' \
  -e '(^|[^0-9.])-[0-9]{9,13}([^0-9.]|$)' \
  -e 'aaron\.zhao|lbk\.one' \
  -e '(api[_-]?key|secret|passphrase)["'"'"' ]*[:=]["'"'"' ]*[A-Za-z0-9+/]{16,}' \
  ${LITERAL_ARGS[@]+"${LITERAL_ARGS[@]}"} \
  "$DEST" --exclude-dir=.git 2>/dev/null | head -20)

if [ -n "$LEAK" ]; then
  echo "🚨 敏感扫描命中，中止导出："
  echo "$LEAK"
  "$NOTIFY" "🚨 life-os-framework 导出中止：敏感扫描命中，详见 .tools/logs/export-framework.log" >/dev/null
  exit 1
fi
echo "敏感扫描通过"

# ---------- 提交并推送（导出仓库独立署名，避免泄露工作邮箱） ----------
cd "$DEST" || exit 1
git config user.name "opisreal"
git config user.email "opisreal@users.noreply.github.com"
git add -A
if git diff --cached --quiet; then
  echo "无变更，跳过提交"
else
  SRC_SHA=$(git -C "$SRC" rev-parse --short HEAD 2>/dev/null || echo "worktree")
  git commit -m "chore(sync): export framework from life-os @${SRC_SHA}" --quiet
  if git push --quiet 2>&1; then
    echo "✅ 已推送 $(git rev-parse --short HEAD)"
  else
    echo "❌ push 失败"
    "$NOTIFY" "❌ life-os-framework push 失败，详见 .tools/logs/export-framework.log" >/dev/null
    exit 1
  fi
fi
echo "[$(date '+%F %T')] export 完成"
