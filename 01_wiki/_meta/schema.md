---
type: wiki-schema
---

# Wiki Schema（规范文档）

> 本文件定义 wiki 的结构约定、页面格式、工作流规范。
> 基于 Karpathy LLM Wiki 模式，适配 Life OS 上下文。

## 三层架构

| 层 | 路径 | 职责 | 谁写 |
|---|---|---|---|
| Raw Sources | `01_wiki/raw/` | 原始资料，不可变 | 用户放入 |
| Wiki | `01_wiki/{concepts,entities,howtos,references,synthesis}/` | 结构化知识页面 | LLM 维护 |
| Schema | 本文件 + CLAUDE.md | 规范和约定 | 用户 + LLM 共同演进 |

## 目录分类

| 目录 | 用途 | 示例 |
|---|---|---|
| `concepts/` | 概念、理论、心智模型 | `transformer.md`、`rag-pipeline.md` |
| `entities/` | 工具、框架、人物、组织 | `langchain.md`、`qdrant.md` |
| `howtos/` | 操作方法、最佳实践 | `deploy-ollama-local.md` |
| `references/` | 来源文献摘要（论文/文章/课程章节） | `attention-is-all-you-need.md` |
| `synthesis/` | 跨领域综合分析、对比、决策 | `vector-db-comparison.md` |
| `raw/` | 原始资料（PDF/文章/剪藏），LLM 只读不改 | 用户自行放入 |
| `raw/assets/` | 图片等附件 | Obsidian 下载的图片 |
| `_meta/` | taxonomy.md + schema.md | 规范文档 |

## 页面格式

每个 wiki 页面必须包含 YAML frontmatter：

```yaml
---
title: 页面标题
category: concepts        # concepts/entities/howtos/references/synthesis
tags: [rag, langchain]    # 从 taxonomy.md 选取，最多 5 个
aliases: [别名]           # 可选
sources:                  # 来源溯源
  - raw/xxx.pdf
  - https://...
created: 2026-04-07
updated: 2026-04-07
status: draft             # stub/draft/mature/stale
---
```

### 页面正文结构

**Concept 页**：
```markdown
# 概念名

一句话定义。

## 核心要点
- ...

## 工作原理
...

## 与其他概念的关系
- [[相关概念A]] — 关系说明
- [[相关概念B]] — 关系说明

## 实践要点
...

## 来源
- [[references/来源页]]
```

**Entity 页**（工具/框架）：
```markdown
# 工具名

一句话定位。

## 解决什么问题
...

## 核心特性
- ...

## 使用场景
...

## 与其他工具的对比
- vs [[entities/竞品]] — 差异点

## 来源
- 官网：
- 文档：
```

**Reference 页**（来源摘要）：
```markdown
# 来源标题

## 元信息
- 类型：论文 / 文章 / 课程章节 / 视频
- 作者：
- 日期：

## 核心观点
1. ...
2. ...

## 关联知识
- [[concepts/相关概念]]
- [[entities/相关工具]]

## 原始笔记
> 直接引用或摘录
```

## 命名约定

- 有自然英文名的概念 → 英文小写连字符（`transformer.md`、`rag-pipeline.md`）
- 本身是中文概念 → 直接用中文文件名（`道法术器.md`、`庄家思维.md`）
- 每个页面至少 2-3 个 `[[wikilinks]]` 指向现有页面

## 操作规范

### Ingest（摄入）
1. 检查 `.manifest.json` 判断是否已处理（增量）
2. 用户将资料放入 `raw/` 或直接贴内容
3. 选择提取框架（见 `extraction-frames.md`）
4. LLM 读取资料，与用户讨论关键要点
5. 创建/更新 wiki 页面（可能触及多个分类）
6. 更新已有页面的交叉引用
7. 更新 `index.md`
8. 更新 `.manifest.json`（追踪记录）
9. 追加 `log.md` 记录
10. git commit

### Query（查询）
1. LLM 先读 `index.md` 定位相关页面
2. 读取相关页面，沿 `[[wikilinks]]` 追踪关联页
3. 综合回答，引用具体页面
4. 如果回答有价值，可存为新的 `synthesis/` 页面
5. 追加 `log.md`

### Lint（健康审计）
6 项检查：
1. 断链（`[[wikilinks]]` 目标不存在）🔴
2. 孤页（无入链）🟡
3. Frontmatter 完整性 🟡
4. 过时检测（长期未更新 + manifest 中来源已变更）🟢
5. 索引一致性（index.md vs 实际文件）🔴
6. 标签健康（未定义标签 / 僵尸标签 / 超限）🟡

### Status（状态）
快速统计：页面数、分类分布、质量分布、待摄入来源、最近操作。

### Cross-link（交叉引用）
扫描所有页面，找出正文提到了某个页面标题/别名但没有 `[[链接]]` 的地方，批量建议补充。

### Tag Management（标签管理）
审计标签使用频率、发现未定义标签、清理僵尸标签、合并近义标签。

## 增量追踪（.manifest.json）

`.manifest.json` 是 wiki 的摄入账本，记录每个已处理来源的：
- `ingested_at` — 摄入时间
- `size_bytes` — 文件大小
- `modified_at` — 来源文件最后修改时间
- `source_type` — 来源类型（pdf/md/url/chat）
- `pages_created` — 本次新建的页面路径
- `pages_updated` — 本次更新的页面路径

用于：
- 避免重复摄入已处理的来源
- 检测来源文件变更（delta 计算）
- 统计页面来源溯源

## 提取框架（Extraction Frames）

摄入资料时，根据内容类型选择对应的结构化提取框架。
详见 `_meta/extraction-frames.md`。

5 种框架：
- **Concept Frame** — 概念定义、核心机制、关系、常见误解
- **Entity Frame** — 工具定位、特性、使用场景、优劣势
- **Howto Frame** — 目标、前置条件、步骤、常见坑、验证
- **Reference Frame** — 元信息、核心论点、关键发现、局限性
- **Synthesis Frame** — 问题、各方观点、共识、分歧、判断

## 备注

- wiki 页面之间通过 `[[wikilinks]]` 互相链接，构成知识网络
- `.manifest.json` 纳入版本控制，便于追踪摄入历史
