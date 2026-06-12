---
title: forge 流水线数据契约
type: reference
created: 2026-06-11
---

# 各阶段结构化产物字段契约

> 所有产物以 JSON 代码块呈现给用户（嵌在 markdown 汇报里）。字段名用下方英文键；缺字段 = validate_blueprint.py 报错。

## Feasibility（⓪）

```json
{
  "specific_enough": true,
  "missing_from_user": ["..."],
  "output_grade": "runnable-skill | analysis-template",
  "allow_component_scan": true,
  "gap_grounding": "domain-context | research | none",
  "artifact_type": "分析结论 | 演讲 | 带论证文章",
  "reject_reason": null
}
```

## ClaimTree（①）

```json
{
  "conclusion_summary": "一句话总结制品的元结论",
  "claims": [
    {
      "id": "C1",
      "statement": "...",
      "type": "状态判定 | 价位阈值 | 触发 | 归因 | 预测 | 知识前提",
      "evidence_quotes": ["制品原文摘录..."],
      "depends_on": ["C2", "C3"]
    }
  ]
}
```

## EvidenceDAG（②-1）

```json
{
  "nodes": [
    { "id": "D1", "kind": "数据输入 | 中间推理 | 思维框架 | 结论",
      "label": "...", "upstream": ["D2"] }
  ]
}
```

约束：结论节点必须可达至少一个数据输入节点；孤立节点 = 逆向不完整。

## FrameworkList（②-2）

```json
[ { "framework": "...", "role": "...", "claims_hit": ["C1"] } ]
```

## ComponentMap（②-3）

```json
[
  {
    "data_need": "价位级清算分布",
    "candidates": [
      {
        "name": "CoinAnk",
        "trust": "官方 | 高星开源 | 第三方 | 自建兜底",
        "provides": "...",
        "access": "api | mcp | lib | scrape",
        "verification": "discovered | installable | reachable | sample_passed",
        "needs_prep": "注册 key / 审批 / 无",
        "cost": "免费 | 免费需注册 | $X/mo"
      }
    ]
  }
]
```

验证档语义（只能逐级升，凭证必须真实发生过）：
- `discovered`：仅文档/口碑层面知道它存在
- `installable`：本机装上了 / 依赖满足
- `reachable`：端点连通（HTTP 200 / 握手成功）
- `sample_passed`：**最小样例调用返回了真实数据**——唯一可进 SkillBlueprint.lenses 的档

## GapList（②-4）

```json
[
  {
    "missing_dimension": "...",
    "why_matters": "...",
    "suggested_source": "...",
    "priority": "P0 | P1 | P2 | P3",
    "grounding": "domain-context | research | uncalibrated"
  }
]
```

`gap_grounding = none` 时所有条目 grounding 必须 = `uncalibrated`，且报告标注"未经领域校准"。

## SkillBlueprint（③）

```json
{
  "name": "kebab-case-skill-name",
  "params": [ { "name": "symbol", "required": true, "default": null, "desc": "..." } ],
  "lenses": [
    { "key": "...", "data_sources": ["仅 sample_passed 的组件名"],
      "frameworks": ["..."], "produces": "..." }
  ],
  "synthesis_logic": "各 lens 产物如何融合成判断",
  "adversarial_check": "skeptic 攻击什么 + 置信度三因子如何计算",
  "data_source_status": [ { "name": "...", "verification": "...", "in_use": true } ],
  "output_format": "报告结构（对齐 archetype 输出契约五要素）",
  "smoke_fixture": "examples/smoke-input.md 的相对路径"
}
```

## CritiqueReport（④）

```json
[ { "issue": "...", "severity": "blocking | major | minor", "fix": "..." } ]
```

blocking 定义：虚构数据源 / lens 引用非 sample_passed 源 / 实例值未参数化 / 输出契约五要素缺项。
