---
name: finance-review
description: 理财模块周期复盘。当用户说"周复盘""本周交易"或输入 /finance review week 时使用（MVP-1 当前分支）。month/quarter/year 分支 MVP-2 起启用。聚合 risk 三张表 + 北极星目标，生成交易周报：胜率/盈亏比/净盈亏/回撤诊断 + 教练评述。
---

# Finance Review — 周期复盘

**只读 + 生成报告**，从不动原始数据（trades / closed-pnl / equity 由 finance-import 写）。
复用 career-review 范式：三档 ✅/⚠️/❌、教练评述非套话、**素材稀薄不强行编报告**。

## 分支状态
- **week（当前激活，MVP-1）**：交易周复盘，本文件主体。
- **month / quarter / year（MVP-2 起启用，停用占位）**：净值快照 + 消费结构 + 储蓄率 + 环比 + 防御性预测（month）；资产配置漂移 + 再平衡（quarter）；跨年对比 + budget 重定（year）。概念保留于 v1 设计与 `2026-06-03-finance-refactor-design.md` §A5，MVP-2 落地前用户触发这些分支 → 告知"MVP-2 起启用"，不生成报告。

## week 分支

### 触发
`/finance review week`、"周复盘""本周交易""本周总结"。

### 输入
1. `05_finance/risk/trades.csv` — 成交明细
2. `05_finance/risk/closed-pnl.csv` — 已平仓盈亏（合约胜率/盈亏比**主源**，取 realized_pnl，不靠 FIFO 重算）
3. `05_finance/risk/equity/<year>.csv` — 周权益序列（当下值采样；回撤唯一依据；**一律经 `parse_trades.load_equity()` 读取**）
4. `00_north-star/goals.md` — `drawdown_cap_from_peak`（当前 0.20）等北极星参数

### Step 1: 计算时间窗
默认上一个完整 ISO 周（`YYYY-Wnn`）；用户可指定本周（窗口=本周一~今天）或其他周。输出窗口给用户确认。

### Step 2: 数据完整性检查（素材稀薄分支）
窗口内筛选 trades / closed-pnl 行数，并检查 equity 是否有本周行：
- **窗口内无任何成交且无平仓记录** → 不强行编报告。输出诊断（各表窗口内行数、equity 有无本周行），给选项：① 先 `/finance import` 补数据再重跑（推荐）；② 本周确实没交易 → 生成"空仓周"极简记录（仅摘要 + equity 回撤一行 + 教练评述聚焦"为什么没交易/空仓纪律"）；③ 跳过本期。
- **equity 缺本周行** → 回撤算不了，提示先补权益数（finance-import 仅权益轻路径：回复"记权益 <USDT数>"），可先出无回撤段的报告但必须标注 ⚠️ 缺口。

### Step 3: 核对上期 Action 完成度
读上一期周报（若存在）的 `## 五、下期 Action` checkbox，逐条核对完成情况（优先用本期数据核对，数据判不了的问用户，不猜）：
- 结果写入本期 `## 一、摘要`（一句"上期 Action 完成 x/y"+ 未完成项点名）。
- frontmatter 写 `actions_done: x/y` —— **自由记录字段，不进任何校验和验收**。
- 上期无 Action 段（W23 及更早不回补）→ 省略该字段，摘要不提。

### Step 4: 计算（一律调脚本，禁止 LLM 心算）
所有数字必须来自 `05_finance/_tools/parse_trades.py` 的函数——写一段一次性 Python（import parse_trades）跑出结果，**不允许 LLM 看着 CSV 心算/手抄统计**：
- **成交数**：窗口内 trades.csv 行数（按 market_type 分 spot/futures 计数）。
- **胜率/盈亏比/净盈亏**：`compute_pnl_stats(窗口内 closed-pnl 行)` → rounds / wins / losses / **breakeven** / win_rate / profit_factor / net_pnl / gross_profit / gross_loss。
- **setup 归因**：窗口内 closed-pnl 行按 `setup` 列分组，各组分别跑 `compute_pnl_stats` → rounds / win_rate / profit_factor / net_pnl；同时计算 `unplanned` 与 `unlabeled` 的回合数占比。
- **手续费合计**：窗口内 trades.csv `fee_amount` 求和（按 fee_asset 分币种）+ closed-pnl `fee` 合计。
- **峰值回撤**：equity 序列**一律经 `load_equity(path)` 取**（week 格式/同 week 重复/排序守卫，**禁止现写 CSV 读取**），`drawdown_from_peak(equity 序列)` 对照 `goals.md` 的 `drawdown_cap_from_peak=0.20`：`drawdown_breaches(...)` 为 True → **⚠️ 破上限**，报告醒目标出。
- **单周权益变化**：`weekly_change(equity 序列)`（最近一期环比，仅展示观察、无 cap；序列不足 2 点返回 None → 报告该行填 "—"）。
- **现货低置信**：`pair_spot_rounds(窗口内现货成交)` 的 low_conf 条数 → 报告注明"剔除 N 条缺底仓回合，现货统计仅基于可配对回合"。

### Step 5: 生成报告
写 `05_finance/reviews/weekly/<year>-W<nn>.md`，**固定五段 + 条件性 setup 归因小表，不含支出段**（MVP-1 无支出数据）：

````markdown
---
type: finance-review
period: 2026-W24
window-start: 2026-06-08
window-end: 2026-06-14
created: 2026-06-15
net_pnl: -120.5
win_rate: 0.44
profit_factor: 2.10        # 无亏损回合时写字符串 "inf"；无数据才是 null
drawdown: 0.08
drawdown_breached: false
actions_done: 1/3          # 上期 Action 完成度，自由记录，不进校验；上期无 Action 段则省略
---

# 交易周复盘 · 2026-W24

## 一、摘要
（3-5 句：本周交易了什么、净结果、最大的一个问题；含"上期 Action 完成 x/y"。基于真实数据，不套模板。）

## 二、交易数据
| 指标 | 值 | 状态 |
|---|---|---|
| 成交数（spot / futures） | N / M | — |
| 已平仓回合 | X | — |
| 胜率 | XX%（X 胜 Y 负 Z 平，平计入分母） | ✅/⚠️/❌ |
| 盈亏比 (profit_factor) | X.XX | ✅/⚠️/❌ |
| 净盈亏 (net_pnl) | ±XXX USDT | ✅/⚠️/❌ |
| 手续费合计 | XXX USDT | — |
| 峰值回撤 (drawdown_from_peak) | X.X% / cap 20% | ✅/⚠️/❌ |
| 单周权益变化 (weekly_change) | ±X.X% | 观察，无 cap |
| 现货低置信剔除 | N 条 | （注明口径） |

## setup 归因
（条件段：**仅当窗口内存在非 unlabeled 标签才包含本段**，全 unlabeled 则整段省略。）
| setup | rounds | 胜率 | profit_factor | net_pnl |
|---|---|---|---|---|

- unplanned 占比 X% 、unlabeled 占比 Y%（两者并列展示，躲标可见）
- unplanned 占比 > 1/3 → 本段标 ⚠️，教练评述按下述防激励倒挂规则展开

## 三、风险诊断
逐项检查，每项给 ✅/⚠️/❌ + 一句证据：
- **扛单**：是否有持仓亏损远超平均仍不止损的回合（看 closed-pnl 单笔最大亏 vs 平均亏）
- **亏损加仓**：同向连续开仓且均价恶化（看 trades 序列）
- **单所/单标的集中**：单一 symbol 占成交额比例是否过高
- **回撤是否破 20%**：drawdown_from_peak vs drawdown_cap_from_peak，破则 ❌ + 触发"下周减仓/停手"建议

## 四、教练评述（200-400 字）
（针对**本周交易行为**的实质评论：节奏、纪律、仓位、情绪痕迹。
 必须引用本周真实数据点，禁止"继续保持""注意风险"类套话。
 若 setup 段触发 unplanned ⚠️：**必须先肯定诚实打标是加分项、问题在开单行为不在标签**，再谈如何收敛无计划单——防激励倒挂。）

## 五、下期 Action
（≤3 条 checkbox，每条**可执行、可核对**：动词 + 对象 + 可验证的完成条件，从本期诊断推出。禁"注意风险"类空话。下期 Step 3 逐条核对。）
- [ ] （示例）单标的成交额占比降到 60% 以下——下期"单所/单标的集中"项核对
````

呈现约定：
- **胜率行**用 `compute_pnl_stats` 的 wins/losses/breakeven 写"X 胜 Y 负 Z 平（平计入分母）"。
- **profit_factor 无亏损**（rounds>0 且 gross_loss=0，函数返回 None）→ 正文写 **"∞（无亏损回合）"**、frontmatter 写字符串 **`"inf"`**；窗口无数据（rounds=0）才写 `null`——两者不得混用。
- 若该周 `|net_flow_usdt| > 0`，回撤行旁标注"含出入金扰动，读数不可直接对照 cap"（一行文案，不算 TWR）。

### Step 6: 副作用与提示
- 若 `05_finance/.manifest.json` 已有 `reviews.weekly` 节点 → push 本期 period；没有则跳过（manifest 重置是独立迁移任务，本 skill 不自行扩 schema）。
- 回撤破 cap 或连续 2 周净亏 → 报告末尾提示具体动作建议（降杠杆/减频/停手一周），**只提示不强制**。
- git commit：`chore(finance): review <year>-W<nn>`（add 报告文件 + manifest 如有改动）。

### 重复检测
目标周报文件已存在 → 问用户：覆盖（推荐，git 史保留旧版）/ 取消 / 另存 v2。

## 铁律
- **数字一律来自 parse_trades.py 脚本输出**——LLM 不心算、不手抄统计；报告数字必须能被同输入下的函数复算。
- 不打分到具体数字（如"交易健康度 78 分"），状态只用 ✅/⚠️/❌ 三档。
- 教练评述 200-400 字、针对本周真实交易行为，套话算违规。
- 素材稀薄（窗口内无成交无平仓）→ 不强行编报告，走 Step 2 分支。
- 合约盈亏只认 closed-pnl.csv 的 realized_pnl；现货 FIFO 缺底仓回合剔除并注明，不拿低置信数据充数。
- 回撤只认 equity 周权益序列（**一律 `load_equity()` 读取**，排序/同 week 唯一性守卫，禁止现写 CSV 读取），不从成交流水推。
- 不动 trades / closed-pnl / equity / goals 原始数据（只读）。
- 不含支出段（MVP-1 无支出数据，MVP-2 month 分支再加）。

## 输出确认
- 写了哪个周报文件、各项核心数字（成交数/胜率/净盈亏/回撤）
- 上期 Action 完成度（actions_done，如适用）与本期下期 Action 条数
- 回撤是否破 cap
- git commit hash

---

**kill 判据**：4 周内主动跑不满 3 次（import + review week 算一次完整 loop）→ 砍掉 finance loop，不换形式硬撑。
