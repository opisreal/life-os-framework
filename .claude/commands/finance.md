---
description: 理财模块操作（import / review）
---

根据用户意图路由到对应的 finance skill：

用户输入：$ARGUMENTS

路由规则：
- `import` 或 "导入成交/导入流水/上传交易/贴账单/记一下消费" → @.claude/skills/finance-import/SKILL.md
- `review week` 或 "周复盘/本周交易/本周总结" → @.claude/skills/finance-review/SKILL.md （week 分支，MVP-1）
- `review month|quarter|year` → @.claude/skills/finance-review/SKILL.md （MVP-2 起启用）
- ~~`record`~~ → 已并入 finance-import（旧 finance-record 待删）
- ~~`plan`~~ → later（MVP-3 起，暂寄生在 review 的"下期 Action"段）
- 无参数或不明确 → 列出 import / review week 两个当前可用入口，问用户想做什么
