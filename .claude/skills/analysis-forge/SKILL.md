---
name: analysis-forge
description: 结论逆向编译器。当用户给出一份成品制品（分析结论/报告/演讲/带论证的文章）并希望"逆向出它的分析过程""复盘这个人的思维""推出证据链""做一个能产出这种分析的 agent/skill"，或输入 /forge 时使用。输入制品 → 逆向出能力与过程 → 编译成可复用的多 agent 分析 skill 蓝图。
---

把一个**成品制品**（分析结论 / 演讲 / 报告）逆向编译成一个**可复用的多 agent 分析 skill 蓝图**。
框架/结构逆向领域无关；领域缺口诊断需 grounding（见铁律 7）。v0.1 只做分析/评估型输出（生成型/文风模仿不在范围）。

## 前置读取

执行前必读：
1. `archetypes/analysis-evaluation.md` — 制品类型 / claim 类型 / 默认 lens 模式 / 禁止事项
2. `references/blueprint-schema.md` — 各阶段结构化产物的字段契约
3. `references/workflow.md` — 生成 skill 的编排骨架规格
4. 若制品属 crypto 领域：`references/crypto-data-sources.md`（已验证的组件分层清单）

## 输入

- `/forge <制品文本或文件路径>`，可附 **DomainContext**（领域 / 任务类型 / 允许数据源 / 已有参考材料 / 禁止假设）
- 制品也可在对话中直接粘贴

## 编译流水线

结构化产物的字段契约一律以 `references/blueprint-schema.md` 为准。

### ⓪ 可行性门（前置失败出口）

产出 `Feasibility`。判定：制品够不够具体、产出等级（可运行 skill | 仅分析模板）、`gap_grounding`（domain-context | research | none）。
- 制品太薄（无可拆 claim / 无证据痕迹）→ **停**，列需用户补充的材料，不硬编。
- 无 DomainContext 时问一次用户是否提供；用户不提供且不批准 web 调研 → `gap_grounding = none`。

### ① 解构（inline）

制品 → `ClaimTree`：拆原子 claim（类型：状态判定 | 价位/阈值 | 触发 | 归因 | 预测 | 知识前提），每条带证据原文引用 + 依赖关系。

### ② 并行逆向扇出

用 Workflow 工具并行四路（不可用时退化为 inline 串行，顺序同下）：
1. **链路逆推** → `EvidenceDAG`（数据输入 / 中间推理 / 思维框架 / 结论 四类节点）
2. **框架识别** → `FrameworkList`（每个框架标命中哪些 claim）
3. **组件复用扫描** → `ComponentMap`：每个数据需求列候选组件，**官方 > 高星开源 > 第三方 > 自建兜底**；每个候选标验证档 `discovered | installable | reachable | sample_passed`。仅凭文档/印象 = discovered，**不许直接标更高档**。crypto 领域先查 `references/crypto-data-sources.md` 再补网络调研。
4. **缺口诊断** → `GapList`：对照领域最佳实践找原版缺失维度，P0-P3 排序。每条标 grounding 来源；`gap_grounding = none` 时整个 GapList 标注"未经领域校准"。

### ┃ 门 1：lens 与预算

向用户呈现：EvidenceDAG 摘要 + GapList + 数据预算（免费/注册/付费分层）。用户勾定：纳入哪些 lens、是否启用付费源。**不许替用户默认勾选付费源。**

### ②b 选定源分级验证

对用户勾定的数据源逐个跑**最小样例调用**（curl / 一行脚本），跑通 → 升 `sample_passed`；跑不通 → 退回 GapList 或"用户准备清单"（key 注册 / 审批申请）。
**只有 sample_passed 的源可进生成 skill 的 lens 定义。**

### ③ 综合

全部产物 → `SkillBlueprint`：名称、输入参数（**参数化，抽掉实例值**）、lenses（每个 lens = 数据源[仅 sample_passed] + 框架 + 产出）、综合逻辑、对抗证伪算法、数据源状态表、输出格式、smoke fixture。

### ④ 对抗自检

派一个 critic agent 攻击 blueprint + 跑 `scripts/validate_blueprint.py` → `CritiqueReport`。
检查：lens 是否漏维度 / 置信度如何校准 / 有无虚构数据源 / 参数化是否彻底 / smoke 能否过。
有 blocking 项 → 退回 ③ 修，不许带病进门 2。

### ┃ 门 2：写盘确认

呈现最终 blueprint + **文件 diff 计划**（每个将写入的路径；覆盖已有文件必须单独列"被覆盖清单"）。用户确认后才写盘。

### ④b Smoke test

写盘后跑 5 项检查：① frontmatter 合法 ② description 能准确触发 ③ 无 TODO/占位 API ④ 用 `examples/smoke-input.md` 跑一遍能产出结构化报告 ⑤ 数据源状态表无虚构项。
不过 → 修到过，**不进门 3**。

### ┃ 门 3：commit 确认

列 commit 文件清单 + commit message → 用户确认 → commit。
生成的领域 skill 按目标领域前缀（如 crypto → `feat(market)`）；forge 本体改动 `chore(os)`。

### ⑤ 沉淀（可选）

本次逆向若暴露 archetype 缺陷/新模式，追加一笔到 `archetypes/analysis-evaluation.md` 的"案例记录"节。

## 产出落点

- 单技能级 → `.claude/skills/<生成名>/{SKILL.md, references/workflow.md, examples/smoke-input.md}`（+ 可选 thin command）
- 模块级（如 crypto）→ 只产「分析核心」蓝图落进指定模块目录，其余基建（回测/定时/日志）后续手工搭，不属 forge 产物

## 铁律

1. **不编数据源/能力**——生成 skill 只默认使用 `sample_passed` 源；其余进缺口或准备清单。"文档看起来支持"不等于验证。
2. **复用优先**——先组件扫描再考虑自建；官方 > 高星开源 > 第三方 > 自建兜底。
3. **参数化优先**——blueprint 不写死实例值（币种 / 价位 / 日期都是参数）。
4. **对抗证伪必出校准置信度**——生成 skill 不许吐裸叙事结论；置信度只用 高/中/低 + 三因子理由（lens 一致性 + skeptic 反驳强度 + 数据完整度），不编数字分。
5. **写盘与 commit 分两道门**——门 2 列 diff 计划，门 3 单独确认 commit；中间必须夹 smoke。
6. **三道门都不许跳**——用户说"快点/直接弄好"也只能合并呈现，不能省略确认本身。
7. **领域诊断要诚实**——`gap_grounding = none` 时只做内部结构逆向，产物显式标注"仅内部结构逆向，未做领域最佳实践补全"，绝不冒充。
8. **逆向方法领域无关**——不把任何领域词写进引擎步骤；领域差异只进 archetype 和 DomainContext。

## 红线自查（出现这些念头就停下）

| 念头 | 现实 |
|---|---|
| "这个 API 文档很全，直接标可用" | 文档 ≠ 跑通。没跑最小样例就是 discovered。 |
| "用户赶时间，门 1/2 合并跳过" | 门可以合并呈现，确认不能省。 |
| "这个领域我懂，缺口我直接列" | 你的印象不是 grounding。标注来源或标"未经领域校准"。 |
| "先写成 ETH 专用，以后再参数化" | 以后不会再参数化。现在就抽参数。 |
| "critic 大概率没意见，跳过自检" | 自检是流水线的一级，不是可选项。 |

## 输出

每次 `/forge` 结束后汇报：生成了哪个 skill（路径）、lens 清单、数据源状态表（sample_passed / 待准备）、GapList 残留项、smoke 结果、commit hash。
