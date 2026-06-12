---
description: Wiki 知识库操作（ingest / query / lint / status / crosslink / tags）
---

根据用户意图路由到对应的 wiki skill：

用户输入：$ARGUMENTS

路由规则：
- `ingest` 或 "整理/沉淀/加到wiki" → @.claude/skills/wiki-ingest/SKILL.md
- `query` 或 "X是什么/对比/总结" → @.claude/skills/wiki-query/SKILL.md
- `lint` 或 "检查/健康/问题" → @.claude/skills/wiki-lint/SKILL.md
- `status` 或 "状态/多少页/概览" → @.claude/skills/wiki-status/SKILL.md
- `crosslink` 或 "补充链接/交叉引用" → @.claude/skills/cross-linker/SKILL.md
- `tags` 或 "标签/整理标签" → @.claude/skills/tag-taxonomy/SKILL.md
- 无参数 → 执行 wiki-status skill 显示概览
