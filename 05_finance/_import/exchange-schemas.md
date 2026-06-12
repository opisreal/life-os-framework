---
type: import-schema
updated: 2026-06-12
---
# 交易所导出文件 → 内部字段映射

首次导入校准产物。内部字段定义见 `../risk/_schema.md`。新增交易所/新报表类型时在此追加段落。

## Bitget

### 已平仓盈亏（U 本位合约历史仓位导出）

校准来源：2026-06-08 真实导出文件（`导出 U 本位合约历史仓位-*.csv`）。

**文件格式**：
- 编码：`utf-8-sig`（带 BOM）；解析失败兜底 `gb18030`
- 表头行号：0（首行即表头）。解析器不硬编码行号，按内容定位（首个含 `已实现盈亏` 的行）
- 日期格式：`YYYY-MM-DD HH:MM:SS`，按 UTC+8 处理
- **无任何唯一交易/仓位 ID** → `source_id` 置空串，去重靠 `closed_row_hash`（见下）

**表头（逐字）**：
`合约,开仓时间,开仓均价,平仓均价,平仓量,平仓价值,仓位盈亏,已实现盈亏,资金费用,开仓手续费,平仓手续费,全部平仓时间`

**列映射**（内部 9 字段 schema 见 `../risk/_schema.md` §2）：

| 原始列 | 内部字段 | 解析规则 |
|---|---|---|
| 合约 | symbol + direction + margin_mode | 格式 `<SYMBOL> <Long\|Short>·<Cross\|Isolated>`，如 `ETHUSDT Long·Cross`。direction 转小写 `long`/`short`；格式不符 → 记 warning 并跳过该行（不崩溃） |
| 全部平仓时间 | close_time | 原样保留 |
| 开仓均价 | open_avg | 原样保留 |
| 平仓均价 | close_avg | 原样保留 |
| 平仓量 | qty | 优先按 symbol 推导的基础资产做**精确后缀剥离**（symbol 去掉 `USDT` 报价后缀即基础资产：`1000PEPEUSDT`→`1000PEPE`，故 `3501000PEPE`→`350`、`0.9ETH`→`0.9`）；单元格不以基础资产结尾时才回退「剥尾部非数字字符」正则并记 warning。数字前缀资产（1000PEPE/10000SATS 类合约）若直接用正则会把资产名前缀吞进数量 |
| 已实现盈亏 | realized_pnl | 剥 `USDT` 后缀。口径=**毛价格盈亏**（不含费用） |
| 资金费用 + 开仓手续费 + 平仓手续费 | fee | **折叠公式：`fee = −(资金费用 + 开仓手续费 + 平仓手续费)`**。fee 为正=净成本；资金费收入超手续费时可为负。资金费用可为正（收入）或负；两项手续费恒为负 |
| 仓位盈亏 | （校验和，不存储） | 净盈亏。**逐行校验：`\|已实现盈亏 + 资金费用 + 开仓手续费 + 平仓手续费 − 仓位盈亏\| < 1e-6`**，不满足 → 该行收入 warnings（保留行、不静默丢） |
| 开仓时间 / 平仓价值 | （不存储） | 开仓时间不入 9 字段 schema；平仓价值 = 平仓均价×平仓量，冗余 |
| — | source_id | 空串（导出无 ID） |

口径关系：`realized_pnl − fee == 仓位盈亏（净）`。

> margin_mode（Cross/Isolated）当前解析后不落盘——仅 symbol+direction 进记录，如需区分全仓/逐仓再加列。

容错行为：数值单元格为空/`--`/无法解析 → 记 warning（标明行与列）并跳过该行，其余行正常导入；表头缺任一必需列 → 整个文件不导入，返回空行集 + warning（不抛 KeyError）。

**附加字段**（导入时补齐）：`exchange="bitget"`、`market_type="futures"`、`source_file=导入文件名（basename）`、`row_hash=closed_row_hash(rec)`。

**closed_row_hash（无 ID 时的去重指纹）**：
对以下 8 个字段的**规范化字符串值**（剥后缀之后、转 float 之前，即写入 `risk/closed-pnl.csv` 的原样字符串）取 `sha256[:16]`：
`("close_time", "exchange", "symbol", "direction", "open_avg", "close_avg", "qty", "realized_pnl")`

> 注意：不能复用 fills 的 `row_hash`（其字段为 time/side/price/base_qty 等成交向字段，closed-pnl 记录里大多缺失，会导致同 symbol 所有回合哈希碰撞）。
> 字符串稳定性契约：哈希输入是落盘的规范字符串本身，因此重新读回自家 CSV 必产生相同哈希。
> 已知局限：跨导出去重依赖 Bitget 数值字符串形态稳定（`"1.5"` 与 `"1.50"` 视为不同），契约仅保证重读自家落盘文件哈希一致。
> 已知局限：数值解析的千分位仅接受合法分组（`1,234,567.89`），非法分组（`1,2,9`）与欧式小数逗号（`5.062,5`）整体拒绝出 warning，不静默截断。

### API（history-position）

来源：`GET /api/v2/mix/position/history-position`（MVP-1.6 API 轨道，归一化在 `_tools/fetch_bitget.py`）。

**字段映射**：

| API 字段 | 内部字段 | 规则 |
|---|---|---|
| positionId | source_id | 唯一主键，去重优先用（CSV 路径无 ID，此处激活） |
| symbol | symbol | 原样保留（如 `ETHUSDT`） |
| holdSide | direction | 转小写 `long`/`short` |
| openAvgPrice | open_avg | 原样保留字符串 |
| closeAvgPrice | close_avg | 原样保留字符串 |
| closeTotalPos | qty | 原样保留字符串（API 无单位后缀，无需剥离） |
| totalFunding + openFee + closeFee | fee | 折叠公式同 CSV：`fee = −(totalFunding+openFee+closeFee)`，经 `_fmt_num` 规范化 |
| uTime | close_time | 毫秒时间戳 → `YYYY-MM-DD HH:MM:SS`，**固定 UTC+8**（与 CSV 同口径，不依赖本机时区） |
| pnl | realized_pnl（**暂定**） | 见下方警告 |
| — | exchange / market_type / source_file | `bitget` / `futures` / `api:history-position` |
| — | row_hash | `closed_row_hash(rec)` 仍计算（与 CSV 兜底路径互见，dedup 互盲修复已落地） |

> ⚠️ **pnl 映射未锁定，待 Task N 对账**：API 返回 `pnl` 与 `netProfit` 两个候选，与 CSV 列「仓位盈亏（净）/已实现盈亏（毛）」的精确对应**尚未实测验证**。当前 `realized_pnl` 暂取 `pnl`（毛口径候选）；归一化记录额外保留 `pnl_raw` / `net_profit_raw` 两候选（不落盘，writer 按 STORE_FIELDS 过滤）。须用 W23 已落盘 9 行与 API 同窗口拉取**逐行对账**锁定映射后修订本表与 `fetch_bitget.py`（铁律 4：不编数据）。

**窗口约束**：私有查询类接口统一 **~3 个月回溯窗口**——更早历史只能靠 CSV 存档，形态必须是"定期增量拉 + 本地落库"。分页为游标式（`endId` + `idLessThan`，每页 ≤100），`fetch_closed_pnl` 已实现循环。

### 成交明细（fills）

**待校准——需用户导出成交明细 CSV**。不预先猜测列名；拿到真实导出后在此补映射表。
