---
name: cross-linker
description: 自动发现并插入缺失的 wikilinks。当用户说"补充链接""检查交叉引用""wiki 链接不全"或输入 /wiki crosslink 时使用。扫描所有页面，找出应该互相链接但没有链接的地方，批量补充。
---

# Cross Linker

## 核心逻辑
扫描 wiki 中所有页面，如果页面 A 的正文中**提到了**页面 B 的标题或别名（aliases），但没有用 `[[wikilinks]]` 链接到 B，则建议插入链接。

## 执行步骤

### Step 1: 构建词表
读取所有 wiki 页面，提取：
- 文件名（去掉 `.md` 后缀和路径前缀）
- frontmatter 中的 `title`
- frontmatter 中的 `aliases`（如有）

构建一个查找表：`{名称/别名 → 文件路径}`

### Step 2: 扫描正文
遍历每个页面的正文（不含 frontmatter），对每个词表条目做匹配：
- 匹配规则：完整词匹配，不匹配已在 `[[]]` 中的文本
- 排除自引用（页面不链接到自己）
- 中文概念用包含匹配（如正文提到"Transformer"且存在 `concepts/transformer.md`）

### Step 3: 生成建议清单
```markdown
## 🔗 Cross-link 建议

### concepts/rag-pipeline.md
- 第 15 行提到 "Qdrant" → 建议链接到 [[entities/qdrant]]
- 第 23 行提到 "向量检索" → 建议链接到 [[concepts/vector-search]]

### entities/langchain.md
- 第 8 行提到 "LCEL" → 建议链接到 [[concepts/lcel]]

共 N 处建议，涉及 M 个页面
```

### Step 4: 用户确认
- 展示完整建议清单
- 用户可以逐条确认或批量确认
- 对于不确定的匹配（如"模型"→ 是否指 `concepts/llm`？），标记为可选

### Step 5: 执行链接插入
将正文中的纯文本替换为 `[[wikilinks]]`：
- `Qdrant` → `[[entities/qdrant|Qdrant]]`
- 如果文件名和显示文本相同，用简写 `[[entities/qdrant]]`
- 每个页面中同一个目标只链接第一次出现

### Step 6: 更新 log.md
```markdown
## [YYYY-MM-DD] crosslink | 交叉引用补充
- 扫描页面数：X
- 发现缺失链接：Y 处
- 已插入链接：Z 处（用户确认后）
- 跳过：W 处
```

### Step 7: git commit
```
feat(wiki): crosslink — 补充 Z 处交叉引用
```

## 判断规则
- 只在正文中第一次出现时插入链接，避免满屏蓝链
- frontmatter 中不插入链接
- 代码块中不插入链接
- 如果一个词同时匹配多个目标（歧义），标记为可选，让用户决定

## 反模式
- 不要在用户未确认时批量修改文件
- 不要创建新页面——只链接已有页面
- 不要链接 index.md 或 log.md
