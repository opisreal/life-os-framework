---
name: wiki-query
description: 基于 wiki 知识库回答问题。当用户问"X 是什么""X 和 Y 有什么区别""总结一下 X 相关的知识"或输入 /wiki query 时使用。先查索引定位相关页面，综合已有知识回答，有价值的回答可存为新页面。
---

# Wiki Query

## 执行步骤

### Step 1: 读取索引
读取 `01_wiki/index.md`，定位与问题相关的页面。

### Step 2: 读取相关页面
根据索引找到的页面，逐个读取。沿着 `[[wikilinks]]` 追踪关联页面。

### Step 3: 综合回答
基于已有 wiki 知识回答用户问题。回答中引用具体页面：
```
根据 [[concepts/rag-pipeline]]，RAG 的核心流程是...
另见 [[entities/qdrant]] 中关于向量检索的说明。
```

### Step 4: 判断是否值得存档
如果回答是一次有价值的综合分析（对比、决策、新发现），询问用户：
"这个回答要存到 wiki 吗？建议放在 `synthesis/` 下。"

如果用户同意：
- 创建新页面（按 schema.md 格式）
- 更新 index.md
- 追加 log.md

### Step 5: 识别知识缺口
如果 wiki 中信息不足以回答问题：
- 明确告知"wiki 中目前没有关于 X 的页面"
- 建议：基于用户已有知识创建 stub 页，或等学到相关内容后 ingest

## 反模式
- 不要绕过 wiki 直接从自身知识回答——wiki 是真相源
- 如果 wiki 内容和 LLM 知识冲突，以 wiki 为准，但提醒用户可能需要更新
- 不要在回答中编造 wiki 里没有的内容
