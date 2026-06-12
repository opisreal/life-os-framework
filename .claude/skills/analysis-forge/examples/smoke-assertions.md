# Smoke 回归断言（smoke-input.md 对应）

> 此文件**不得**交给执行 forge 的 agent 读取（避免测试污染）；仅供评审者比对产出。

对 `smoke-input.md` 跑 forge 流水线后应产出：

1. **Feasibility**：判定"够具体"，gap_grounding = domain-context 或 research 均可（用户诉求薄、实际缺口依据是 references/crypto-data-sources.md 调研 → research 更诚实），但**不得 = none**
2. **ClaimTree**：≥8 个 claim，类型覆盖 状态判定/价位/触发/归因/预测，含依赖关系
3. **EvidenceDAG**：数据输入节点至少含 价格OHLCV/恐慌贪婪指数/ETF流向/清算热图/链上巨鲸 五类
4. **ComponentMap**：每个数据需求映射候选组件并标注验证档（discovered/installable/reachable/sample_passed）；未跑通样例前不得标 sample_passed；不得出现凭空捏造的数据源
5. **GapList**：每条带 grounding 标注；本例有 DomainContext → 不得标"未经领域校准"
6. **SkillBlueprint**：参数化（symbol/timeframe 为参数，不写死 ETH/1550）；lenses 的数据源字段仅引用 sample_passed 源，其余进数据源状态表或准备清单
7. **流程纪律**：门 1（lens+预算）出现在 ②与③ 之间；写盘前有门 2（文件 diff 计划）；commit 前有门 3 且与门 2 分离；对抗自检产出 CritiqueReport
8. **校验**：`scripts/validate_blueprint.py` 对最终 blueprint 通过（无 TODO/占位/虚构源）
