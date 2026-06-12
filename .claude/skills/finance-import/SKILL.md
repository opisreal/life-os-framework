---
name: finance-import
description: 理财模块导入型唯一写入口。当用户说"导入成交""上传交易""贴 Bitget CSV""发截图记交易""导入流水""记一下消费"或输入 /finance import 时使用；输入只含权益数（"记权益""报权益"）走仅权益轻路径。MVP-1.5 实现交易分支（Bitget 已平仓盈亏 + 周权益快照；成交明细 fills 待校准）；支出分支 MVP-2 起启用。
---

# Finance Import — 导入型唯一写入口

`05_finance/` 数据层的**唯一写入口**。原则：**脏活给脚本、归类/确认给 LLM**——行级写盘一律走 `_tools/import_closed_pnl.py`，LLM 只做归类、确认与合并问答。
当前（MVP-1.5）主路径为**已平仓盈亏 + 周权益**；支出分支（支付宝/微信/银行流水）MVP-2 起启用，收到支出类输入（"记一下消费"等）→ 告知"MVP-2 启用"，不处理。

> **与 MVP-1.6 API 轨道的关系**：Bitget 只读 API 自动拉取（`fetch_bitget.py`，经 `LOADERS` 注册表新键如 `("bitget","closed_pnl_api")`）上线后，本 skill 的手动 CSV 路径**降级为兜底**（API 失败降级 / 超 3 个月回溯窗口的历史补录），但流程不变——两条路径共用 `import_closed_pnl.py` 同一去重/落盘管道。本文件不得写死"仅 CSV"假设。

## 前置读取
1. `05_finance/risk/_schema.md` — 表字段定义（closed-pnl 14 列含 setup / equity v2 七列）+ 重放豁免与 suspected 语义（§2）+ setup 受控词表
2. `05_finance/_import/exchange-schemas.md` — Bitget 原始列名 → 内部字段映射（已校准）
3. `05_finance/risk/accounts.md` — 账户登记
4. `05_finance/_tools/import_closed_pnl.py` + `parse_trades.py` — 写盘 CLI 与纯函数

## 列映射状态
- **Bitget 已平仓盈亏：已校准**（基于 2026-06-08 真实导出，见 `_import/exchange-schemas.md` Bitget 段）。**若 Bitget 改版导致解析 warnings 激增**（表头变化、数值格式变化）→ 停止写库，先重新校准映射表，再导入。
- **Bitget 成交明细（fills）：待校准**——拿到真实导出前不猜列名、不解析写库（`exchange-schemas.md` fills 段补全后启用，届时批内去重走 `dedup_fills`；closed-pnl 走 `closed_row_hash` 指纹，两表去重函数不混用）。
- 新交易所/新报表类型同理：先用真实样本补 `exchange-schemas.md` 段落，再导入。

## 行为（交易分支）

### ① 接收输入
- CSV 文件路径（用户给本地路径）→ 直接进 ②
- 粘贴的 CSV 文本 → 原样落临时文件（保留原始列头与字符串形态）再进 ②
- 截图（Bitget 已平仓页面）→ 走"截图路径"（见 ③ 末）

### ② 行级写盘（一律走脚本）

```bash
python3 05_finance/_tools/import_closed_pnl.py <源CSV路径> \
  [--store 05_finance/risk/closed-pnl.csv] [--exchange bitget] [--kind closed_pnl]
```

默认参数即 Bitget 已平仓盈亏，通常只给源文件路径。脚本内部：`LOADERS` 注册表分发 loader → 解析归一化 → 跨导入去重（含重放豁免）→ 仅 append 新行（`setup` 默认 `unlabeled`）→ stdout 输出 JSON 报告：

| 字段 | 含义 |
|---|---|
| `added` | 本次新增写入的行数 |
| `skipped` | 重放豁免静默跳过数（hash/id 命中存量且 `source_file` 相同 = 同文件重放） |
| `suspected` | hash 命中但 `source_file` **不同**的行数（**未写库**，待人工确认） |
| `warnings` | 解析警告列表（跳行原因 / 恒等式校验不平等）；激增 → 触发重新校准 |
| `date_range` | 新增行的首末日期 |
| `suspected_rows` | suspected 行摘要（close_time / symbol / realized_pnl） |

重放豁免与 suspected 语义以 `risk/_schema.md` §2 为准。**禁止 LLM 绕过脚本手抄行进 CSV。**

### ③ suspected 处理（不静默）
`suspected_rows` **批量列给用户**逐条或批量确认：
- 确认**是重复** → 丢弃，完成输出里注明。
- 确认**不是重复**（合法的同参数回合）→ 由 LLM 显式追加：先列出将写入的整行（14 列，`row_hash` 调 `parse_trades.closed_row_hash` 计算，不手算），用户确认后 append——**确认追加也要显式记录，绝不静默写入**。

**截图路径**：LLM 读图提取为内部字段，逐行列给用户核对（看不清的字段问，不编数据）；核对通过后按上面"显式追加"方式写入（`source_id` 留空、`source_file=screenshot-<date>`、`row_hash` 调脚本函数算）。

### ④ 合并问答（导入末尾一条消息问完，不分多轮）
脚本报告转述后，**一条消息**问三件事，然后解析用户的单条回复：
1. **setup 标签**：本次新增回合标什么（受控词表：`trend` / `reversal` / `news` / `scalp` / `unplanned`；可整批一个标签或按行指定；答"跳过"或不答 → 保持 `unlabeled`，不阻塞）。用户给标后 LLM 显式回填 `setup` 列（setup 不进 `closed_row_hash`，事后补标/改标不破坏去重）。
2. **当前权益**："当前权益多少 USDT？"——只问当下值。
3. **出入金**：被动提一句"本周有出入金才说，默认按 0 记"；**仅当对账触发**——`|本周权益 − 上周权益 − 本周 net_pnl| / 上周权益 > 5%`（net_pnl 调 `compute_pnl_stats` 算，不心算）——才主动追问"本周有出入金吗"，平时零追问。

### ⑤ 权益写入（当下值语义）
写 `05_finance/risk/equity/<ISO年>.csv` 一行（schema v2 七列，字段规则见 `_schema.md` §3）：
- **当下值**：`as_of` = 今天（周内任意日均可），`week` = `as_of` 所在 ISO 周；**文件年份 = week 的 ISO 年（`date +%G` 语义）**，跨自然年的 ISO 周按 ISO 年归档。
- **绝不问历史权益回忆题**（"上周日收盘权益多少"属违规）。上周缺行 → 本周行 note 诚实标注断点（如 `"W23 缺采样"`），不补造；仅当用户**主动**提供 Bitget 资产历史截图时可选补录历史行。
- **同 week 复报 → 覆盖问询**：该周已有行 → 问"覆盖还是跳过"，覆盖即重写该行，**文件内同 week 不留双行**。
- 用户暂不给权益数 → 提醒"回撤计算依赖此数"后跳过，不编数。
- 写后调 `parse_trades.load_equity(path)` 自检（week 格式 / 同 week 重复 / 排序守卫）。

**汇率惰性**：`usdt_cny_rate` / `equity_rmb` 可空，平时留空（MVP-1 无消费者）。需要折算时（MVP-2 净值汇总或用户要求）**自动查**当月月初 USD/CNY（WebSearch，铁律 7，不问用户），按契约 `equity_rmb = round(equity_usdt × usdt_cny_rate, 2)` 填入并同步 `05_finance/rates.md`；**rates.md 缺行不阻塞导入**。

### 完成输出
- JSON 报告转述：added / skipped / suspected（及处理结果）/ warnings
- setup 标注结果（标了什么 / 几行保持 unlabeled）
- equity 本周行状态（写入 / 覆盖 / 跳过）
- git commit：`feat(finance): import closed-pnl + equity <YYYY-Wnn>`（add 仅本次改动的 risk/ 文件，及 rates.md 如有）

## 仅权益轻路径
输入只含权益数——触发词"记权益 <USDT数>""报权益"——**跳过 ①-④**，直接执行 ⑤ 写 equity + commit（`feat(finance): equity <YYYY-Wnn>`）。空仓周只走这条即满足周探针的"完整态"（探针真值表：权益半 ✓ 即不催，交易数据有无不裁决）。

## 铁律
- **脏活给脚本**——解析、哈希、去重、统计、写盘走 `import_closed_pnl.py` 与 `parse_trades.py`，LLM 不心算、不手抄数字。
- **不编数据**——读图看不清、字段缺失、权益数未给 → 问或留缺口 note，不猜。
- **写入前 schema 一致**——落盘列集与 `risk/_schema.md` 现行版一致（closed-pnl 14 列 / equity v2 七列）；setup 新词先改 schema 再落盘。
- **疑似重复不静默**——suspected 批量列给用户确认；确认追加也要显式记录。
- **不问回忆题、不问可查的数**——权益只记当下值，汇率自动查。
- **列名不确定先校准**——映射表缺段（如 fills）就停在校准步，不猜列名硬解析。
- 原始 CSV 文件本身不入库（raw 不可变原则同 wiki）；只写归一化后的表。

## 验收
以 `import_closed_pnl.py` 的 JSON 报告为准：
- 全新文件：`added` = 文件有效行数，`closed-pnl.csv` 增同数行（`setup=unlabeled`），`warnings` 为空或已逐条向用户解释。
- 同文件重放：`added=0`、`skipped=N`、`suspected=0`（重放豁免规则生效）。
- equity 本周行已写（或用户显式跳过且输出注明），`load_equity` 自检通过。
- 合并问答只发了一条消息（setup / 当前权益 / 出入金被动项）。
