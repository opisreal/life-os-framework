# 05_finance — 个人理财模块

> v2.1「稳健 + 风险」两层架构。导入型输入替代手填快照，先用交易 loop 验证习惯，再扩稳健层。目标锚点在 `00_north-star/goals.md`（年储蓄目标 + `drawdown_cap_from_peak`）。

## 两层架构
- **风险层**（当前主战场）：交易账户（Bitget U 本位合约）。周节奏 loop：导入已平仓盈亏 + 报当周权益 → 周报诊断。数据落 `risk/` 三张表。
- **稳健层**（MVP-2 启用）：银行 / 基金 / 公积金等低频资产，月度导入对账单 + 净值汇总。当前未启用。

## 两个入口
- **`/finance import`** — 模块**唯一写入口**。贴 Bitget 已平仓盈亏 CSV（截图兜底）→ 脚本去重落盘 → 末尾一条合并问答（setup 标签可跳过 / 当前权益 / 出入金默认无）。
  - **"记权益"轻路径**：输入只含权益数（"记权益 / 报权益 <USDT数>"）→ 跳过导入步骤，直接写 equity 行 + commit，30 秒完成（空仓周即此路径）。
  - 行级写盘一律走 `_tools/import_closed_pnl.py`（LOADERS 分发 / 跨导入去重 / 重放豁免 / JSON 报告），LLM 只做归类确认与问答。
- **`/finance review week`** — 周复盘。聚合 risk 三张表 + 北极星目标，产出 `reviews/weekly/<period>.md`：胜率 / 盈亏比 / 净盈亏 / 峰值回撤诊断 + setup 归因小表 + 教练评述 + 下期 Action。month/quarter/year 分支 MVP-2 起启用。
- 旧 `/finance record`（已并入 import）与 `/finance plan`（推迟至 MVP-3）已废弃，skill 文件保留至 W26 裁决删除。

## risk/ 三张表

| 表 | 状态 | 说明 |
|---|---|---|
| `risk/trades.csv` | 待启用 | 成交明细（fills）。CSV 列映射待校准；MVP-1.6 API 轨道接入后启用，解锁"亏损加仓"诊断 |
| `risk/closed-pnl.csv` | 在用 | 已平仓盈亏，**14 列**（9 字段 schema + exchange/market_type/source_file/row_hash + setup 归因列）。胜率/盈亏比/净盈亏主源 |
| `risk/equity/<year>.csv` | 在用 | 周权益快照 **schema v2，7 列**（week/as_of/equity_usdt/usdt_cny_rate/equity_rmb/net_flow_usdt/note）。`equity_usdt` 唯一必填，回撤计算唯一主序列；汇率/RMB 惰性回填 |

字段定义与去重/重放豁免规则见 `risk/_schema.md`；交易所原始列映射见 `_import/exchange-schemas.md`。

## kill 判据
4 周内主动跑不满 3 次完整 loop（import + review week 算一次）→ 砍掉 finance loop，不换形式硬撑。W23 起算，**W26 复盘统一裁决**：loop 存废、setup 列存废、废弃 skill 文件删除。加固/基建工作不计为"跑 loop"。

## trys/ 定位
**交易实验沙箱，不入账本不进统计。** 套利脚本、刷量实验、策略草稿放这里；其产生的真实成交仍以交易所导出为准走 import 入账。

## MVP 分期现状
- **MVP-1 ✅**：交易 loop 第一圈跑通（W23 周报）。
- **MVP-1.5（完成中）**：加固包——探针 git 真值表三态、equity schema v2、setup 归因列、回撤口径定版（`drawdown_cap_from_peak`）、导入固化（import CLI）、文档对齐。
- **MVP-1.6（API 轨道，两步走）**：①半自动验证期——签名客户端 + fetch 归一化骨架先行，烟雾测试与字段对账等只读 key 建好；②全自动——launchd 周日自动拉取 + 写表 + commit + 通知，任何失败降级回催促探针，CSV 路径永远保留为兜底。
- **MVP-2（later）**：稳健层（月度对账单导入 + 净值汇总 + month/quarter/year 复盘）。
- **MVP-3（later）**：plan 路径规划重启。

## 目录
- `risk/` — 风险层三张表 + `_schema.md` + `accounts.md`
- `reviews/weekly/<period>.md` — 交易周报（monthly/quarterly/yearly 待 MVP-2）
- `_tools/` — `parse_trades.py`（纯函数）/ `import_closed_pnl.py`（导入 CLI）/ `bitget_api.py` + `fetch_bitget.py`（API 轨道）/ `weekly-submit-reminder.sh`（探针）/ tests
- `_import/exchange-schemas.md` — 交易所导出列映射（首次导入校准产物）
- `_design/` — 设计与实施计划文档
- `trys/` — 交易实验沙箱（不入账本）
- `rates.md` — 汇率表（惰性回填来源）
- `budget.md` / `plans/` / `snapshots/` / `spending/` / `goals/` / `net-worth.md` — v1 遗留，goals 已标废弃，其余待 MVP-2 重启或清理

## 提醒
weekly 一档：launchd 周日 20:00 触发 `_tools/weekly-submit-reminder.sh` → `.tools/notify.sh` → 飞书。探针只认 git 提交（真值表三态：权益已提交则静默；缺权益/缺数据才催，文案内嵌最低成本响应口令）。月/季/年三档已停。配置见 `~/life-os/.tools/README.md`。

## 隐私声明
**当前采用明文存储**。所有金额直接写在 markdown / CSV 里。

**适用前提**：
- 本仓库无 git remote（仅本地）
- 不通过 iCloud / Dropbox 等云盘同步
- 电脑不与他人共用

**何时需要升级**：
- 准备 push 到 GitHub / Gitee 等远程
- 启用云盘同步
- 共用电脑或工作场景频繁屏幕共享

## 隐私升级路径
未来要把仓库 push 到云端时，按以下步骤迁移到"双文件分层"。**迁移清单必须覆盖全部含绝对金额的文件**：

| 需迁移 | 内容 |
|---|---|
| `snapshots/` | 月度资产快照（v1 遗留） |
| `spending/` | 消费流水（v1 遗留） |
| `net-worth.md` | 净资产序列（v1 遗留） |
| `risk/closed-pnl.csv` | 逐笔盈亏（绝对金额） |
| `risk/equity/` | 权益序列（绝对金额） |
| `reviews/weekly/` | 周报 frontmatter 含 net_pnl 绝对额，正文含权益数 |

```bash
cd /Users/USERNAME/life-os/05_finance
mv snapshots       snapshots.private
mv spending        spending.private
mv net-worth.md    net-worth.private.md
mv risk/closed-pnl.csv  risk/closed-pnl.private.csv
mv risk/equity     risk/equity.private
mv reviews/weekly  reviews/weekly.private
# .gitignore 追加：
#   05_finance/snapshots.private/
#   05_finance/spending.private/
#   05_finance/**/*.private.md
#   05_finance/risk/*.private.csv
#   05_finance/risk/equity.private/
#   05_finance/reviews/weekly.private/
git rm --cached -r snapshots spending net-worth.md risk/closed-pnl.csv risk/equity reviews/weekly
git add 05_finance/
git commit -m "chore(finance): migrate to private-file layered storage"
# (必做) 用 git-filter-repo 清洗历史——上述文件的绝对金额已进过 git 历史
```

迁移后：
- `plans/`、`goals/pyramid.md`、`risk/_schema.md`、`_design/`、`_tools/` 等不含绝对金额的文件可继续进 git
- **注意：`reviews/` 含绝对金额（周报 frontmatter `net_pnl`、正文权益数），不能整目录留在 git**——周报需随权益/盈亏数据一起迁入 private，或改造为脱敏版后再留
- 模块仍能完整运行，分析能力不受影响
