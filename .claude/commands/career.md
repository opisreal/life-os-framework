---
description: 职业成长模块操作（log / jd / review / roadmap / interview）
---

根据用户意图路由到对应的 career skill：

用户输入：$ARGUMENTS

路由规则：
- `log` 或 "记一下/今天工作/收到反馈/周报" → @.claude/skills/career-log/SKILL.md
- `jd` 或 "新 JD/分析 JD/目标岗位" → @.claude/skills/career-jd/SKILL.md
- `review week|month|quarter` 或 "周复盘/月度复盘/季度复盘" → @.claude/skills/career-review/SKILL.md
- `roadmap` 或 "学习路线/差距分析/怎么补" → @.claude/skills/career-roadmap/SKILL.md
- `interview` 或 "面试题/今天的面试/复盘面试" → @.claude/skills/career-interview/SKILL.md
- 无参数或不明确 → 列出五个子命令的简短说明，问用户想做什么
