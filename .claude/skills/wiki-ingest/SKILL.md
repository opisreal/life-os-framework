---
name: wiki-ingest
description: 摄入新资料到 wiki 知识库。当用户说"整理一下 X""把这个加到 wiki""沉淀这个概念"或输入 /wiki ingest 时使用。读取原始资料，用提取框架蒸馏知识，创建/更新 wiki 页面，维护索引、日志和 manifest。
---

# Wiki Ingest

## 前置读取
1. `01_wiki/_meta/schema.md`（页面格式和分类规范）
2. `01_wiki/_meta/taxonomy.md`（标签受控词表）
3. `01_wiki/_meta/extraction-frames.md`（按类型选择提取框架）
4. `01_wiki/index.md`（已有页面，避免重复）
5. `01_wiki/.manifest.json`（已摄入来源，避免重复处理）

## 输入方式
用户可能通过以下方式提供资料：
- 直接在对话中贴文本/链接
- 指定 `01_wiki/raw/` 下的文件路径
- 让 LLM 基于用户描述生成知识页
- 批量指定目录（如 `01_wiki/raw/*.pdf`）

## 执行步骤

### Step 0: 增量检查
如果来源是文件路径，先检查 `.manifest.json`：
- 已摄入且未修改 → 告知用户"已处理过，跳过"
- 已摄入但文件已修改 → 告知用户"来源有更新，需要重新摄入"
- 未摄入 → 继续

### Step 1: 理解资料 + 选择提取框架
- 读取原始资料
- 根据内容性质选择提取框架（见 `extraction-frames.md`）：
  - 偏概念/理论 → Concept Frame
  - 偏工具/框架 → Entity Frame
  - 偏操作步骤 → Howto Frame
  - 偏论文/文章 → Reference Frame
  - 混合内容 → 拆分后分别用对应框架
- 与用户讨论关键要点：这份资料的核心是什么？哪些概念值得独立建页？
- **不要跳过讨论直接开写**——用户的判断决定什么值得沉淀

### Step 2: 规划页面
列出计划创建/更新的页面清单，说明：
- 新建还是更新已有页面
- 放在哪个分类（concepts/entities/howtos/references/synthesis）
- 使用哪个提取框架
- 预计会涉及哪些交叉引用
- 让用户确认后再动手

### Step 3: 创建/更新页面
按 schema.md 的页面格式 + 选中的提取框架写入：
- 必须包含完整 YAML frontmatter（title/category/tags/sources/created/updated/status）
- 每页至少 2-3 个 `[[wikilinks]]` 指向已有页面
- 标签从 taxonomy.md 中选取
- 如需新标签，先更新 taxonomy.md
- 新建页面 status 设为 `draft`

### Step 4: 更新已有页面的交叉引用
扫描新页面提到的已有概念，在已有页面中补充反向链接。
具体做法：
- 读取新页面中所有 `[[wikilinks]]` 的目标页
- 在目标页的"与其他概念的关系"或合适位置，补充指向新页面的链接
- 一次 ingest 可能触及 5-15 个页面

### Step 5: 更新 index.md
在对应分类下追加新页面条目：
```markdown
- [[concepts/xxx]] — 一句话摘要
```
更新 frontmatter 中的 `page_count` 和 `updated`。

### Step 6: 更新 .manifest.json
在 `sources` 中追加记录：
```json
{
  "sources": {
    "raw/xxx.pdf": {
      "ingested_at": "2026-04-07T20:30:00+08:00",
      "size_bytes": 12345,
      "modified_at": "2026-04-07T10:00:00+08:00",
      "source_type": "pdf",
      "pages_created": ["concepts/a.md", "entities/b.md"],
      "pages_updated": ["concepts/c.md"]
    }
  }
}
```
对于用户直接贴的文本，source key 用 `chat:YYYY-MM-DD-简述`。
更新 `stats` 中的计数。

### Step 7: 追加 log.md
```markdown
## [YYYY-MM-DD] ingest | 资料标题
- 来源：raw/xxx 或 chat:直接输入
- 提取框架：concept + entity
- 新建页面：concepts/a.md, entities/b.md
- 更新页面：concepts/c.md（补充交叉引用）
- 新增标签：无 / xxx
```

### Step 8: git commit
```
feat(wiki): ingest — 资料标题简述
```

### Step 9: 输出摘要
```
📚 已摄入：资料标题
   提取框架：Concept Frame + Entity Frame
   新建 3 页：concepts/a, entities/b, references/c
   更新 2 页：concepts/d（+反向链接）, entities/e（+反向链接）
   当前 wiki 共 X 页 | 已摄入 Y 个来源
```

## 判断规则
- 概念定义 → `concepts/`
- 工具/框架/人物 → `entities/`
- 操作步骤/教程 → `howtos/`
- 论文/文章/课程章节摘要 → `references/`
- 跨概念的对比或综合分析 → `synthesis/`
- 如果一份资料同时涉及多个分类，分别建页
- 一个概念如果在多个来源中被提到，**合并到同一页面**而非创建多个

## 反模式
- 不要把原始资料原封不动复制到 wiki——wiki 是**蒸馏后的知识**
- 不要跳过讨论直接批量建页
- 不要创建没有交叉引用的孤页
- 不要使用 taxonomy 中不存在的标签
- 不要修改 `raw/` 下的文件
- 不要遗漏 manifest 更新——这是增量追踪的基础
