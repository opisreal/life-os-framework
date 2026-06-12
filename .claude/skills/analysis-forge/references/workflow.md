---
title: 生成 skill 的多 agent 编排骨架规格
type: reference
created: 2026-06-11
---

# 编排骨架规格（forge 产物的运行时形状）

> forge 生成的每个分析/评估 skill，其 `references/workflow.md` 按本规格写。
> v0.1 是**过程描述驱动**：SKILL.md 用文字描述编排，宿主（Claude Code）在运行时用 Agent/Workflow 工具拉起；不绑定 standalone runtime（强执行版留 v0.2）。

## 四段骨架

```
扇出   N 个 lens agent 并行 —— 每个 = 一个分析维度
       输入：参数实例（如 symbol/timeframe）+ 该 lens 的 sample_passed 数据源 + 指定框架
       输出：该维度的结构化发现（数据带时间戳与来源；拉取失败显式标"缺失"）

综合   synthesizer 融合各 lens → 候选判断
       规则：lens 间冲突必须显式列出，不许静默取多数

对抗   skeptic agent 攻击候选判断 —— 找反例、查数据时效、挑因果跳步
       输出：最强反驳清单 + 每条是否改变结论

输出   结构化报告（archetype 输出契约五要素）+ 校准置信度
```

## 校准置信度（三因子，不编数字）

| 因子 | 高 | 低 |
|---|---|---|
| lens 一致性 | 各维度指向同一判断 | 关键维度互相矛盾 |
| skeptic 反驳强度 | 反驳均被数据回应 | 存在未回应的实质反驳 |
| 数据完整度 | 核心源全部拉到 | 有 P0/P1 源缺失 |

三因子 → 高/中/低：任一因子"低"则整体不得高于"中"；两个及以上"低"则整体"低"。报告必须写出三因子各自的判定理由。

## 生成 skill 时需写死进其 workflow.md 的内容

1. lens 清单（key / 数据源 / 框架 / 产出）——来自 SkillBlueprint.lenses
2. 综合逻辑——来自 SkillBlueprint.synthesis_logic
3. skeptic 的攻击面——来自 SkillBlueprint.adversarial_check
4. 降级路径——某 lens 数据源失效时：跳过该 lens 并降置信度，还是中止（按 lens 的 P 级写明）
5. 宿主能力假设——本骨架假设宿主有 Agent/Workflow 工具；无则按 lens 顺序 inline 串行执行，结果等价、耗时变长
