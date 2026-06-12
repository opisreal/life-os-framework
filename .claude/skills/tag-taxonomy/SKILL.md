---
name: tag-taxonomy
description: 管理 wiki 标签分类体系。当用户说"整理标签""有哪些标签""加个新标签""标签太乱了"或输入 /wiki tags 时使用。审计标签使用情况，清理/合并/新增标签，维护受控词表。
---

# Tag Taxonomy

## 前置读取
1. `01_wiki/_meta/taxonomy.md`（当前标签体系）
2. 所有 wiki 页面的 frontmatter tags

## 支持的操作

### 1. 审计（默认）
扫描所有页面的 tags，生成报告：
```markdown
## 🏷️ 标签审计报告

### 使用频率
| 标签 | 使用次数 | 示例页面 |
|---|---|---|
| rag | 12 | concepts/rag-pipeline, entities/qdrant, ... |
| langchain | 8 | entities/langchain, howtos/lcel-chain, ... |
| ...

### 问题
- **未定义标签**（taxonomy 中没有）：`xxx` 用于 3 个页面
- **僵尸标签**（定义了但没人用）：`yyy`
- **近义标签**（可能需要合并）：`deep-learning` vs `dl`
- **超限页面**（> 5 个标签）：concepts/aaa.md (7 个标签)
```

### 2. 新增标签
用户要求新增标签时：
1. 检查是否已有近义词
2. 确定放在哪个层级（Domain / Type / Status）
3. 更新 `taxonomy.md`
4. git commit: `chore(wiki): add tag — xxx`

### 3. 合并标签
用户要求合并标签时（如 `deep-learning` → `dl`）：
1. 列出受影响的页面
2. 用户确认后批量替换所有页面的 frontmatter
3. 更新 `taxonomy.md`（删除旧标签，保留新标签）
4. git commit: `chore(wiki): merge tag xxx → yyy`

### 4. 清理僵尸标签
从 `taxonomy.md` 中移除从未使用的标签（用户确认后）。

## 反模式
- 不要自动合并标签——必须用户确认
- 新增标签前必须检查近义词
- 不要在正文中修改标签——只改 frontmatter
