---
name: finance-record
description: 已废弃（2026-06）：录入走 finance-import，规划等 MVP-3。本 skill 不再触发。
---

> ⚠️ **已废弃（2026-06-12）**：录入已并入 finance-import（导入型唯一写入口）。本文件不再触发，保留至 W26 复盘裁决删除。

是 Life OS `05_finance/` 模块的**录入入口**。
按输入内容判断分流，是这个模块所有"写入数据"的唯一入口。

## 前置读取
执行前必读：
1. `05_finance/_design/2026-05-24-finance-module-design.md` §3.1（你的铁律）
2. `05_finance/.manifest.json` 检查已录入历史
3. `05_finance/rates.md` 当前汇率表
4. `05_finance/budget.md` 当前预算基线（spending 归类时对照超额项）
5. 若是目标变更：`05_finance/goals/pyramid.md` + `goals/active/`

## 输入识别
判断输入类型（按关键词组合 + 数据形态）：

| 类型 | 触发信号 | 路径 |
|---|---|---|
| **A · 月度快照** | "快照"/"资产"/"月初"/"X 账户余额"，或粘贴的是"账户名: 金额"列表 | `snapshots/<year>/<period>.md` |
| **B · 月度消费** | "消费"/"账单"/"流水"/"支付宝"/"微信"/"信用卡"，或粘贴的是账单原始数据 | `spending/<year>/<period>.md` |
| **C · 目标变更** | "新目标"/"改目标"/"调整目标"/"目标达成"/"放弃目标" | `goals/active/<name>.md` 或 `goals/archive/` |

**模糊时不要猜——反问用户**。

## 执行步骤

### 类型 A · 月度快照
1. 确认月份（默认上月或本月初）
2. 检查 `snapshots/<year>/<period>.md` 是否已存在
   - 存在 → 更新而非新建
   - 不存在 → 新建
3. 解析输入的账户清单，按 9 类分组（现金/投资/加密/房产/公积金养老金/保险/负债/+ 其他用户提供的）
4. **加密资产**：必须先检查 `rates.md` 该月汇率
   - 已录入 → 直接折算 `数量 × rate = 折算 RMB`
   - 未录入 → **必须先问用户当月汇率**（CoinGecko / CMC / 用户偏好来源），写入 rates.md 再算
5. **房产估值**：
   - 是 6 月或 12 月 → 主动询问要不要更新估值（不强制）
   - 其他月份 → carry forward 上月值（若上月也无 → 问用户）
   - 更新时必须留 source 字段（如"中介报价"/"链家挂牌"/"评估机构"），不允许凭感觉拍
6. **金额单位**：写入前必须确认是"元"为单位。模糊时反问（特别是 6 位数以上的大额，"是 50 万还是 5 万"）
7. 算 frontmatter 三个字段：
   - `total_rmb` = 所有非负债资产之和（含折算后的加密资产）
   - `total_liability` = 负债类之和
   - `net_worth` = total_rmb - total_liability
8. 追加一行到 `net-worth.md`，含月环比（与上月对比百分比）
9. 更新 `.manifest.json` 的 `snapshots` 数组
10. git commit: `feat(finance): snapshot YYYY-MM`

### 类型 B · 月度消费
1. 确认月份（默认上月）
2. 检查 `spending/<year>/<period>.md` 是否已存在
3. 把原始账单粘到 `<details>` 折叠块
4. 自动按 5 大类归类：
   - **刚性支出**：房贷月供 / 物业水电网 / 通勤 / 基础食材 / 保险月缴
   - **柔性消费**：外卖 / 餐饮社交 / 咖啡奶茶 / 订阅服务 / 网购日用
   - **品质消费**：旅行 / 衣服美妆 / 学习付费 / 健身
   - **大额一次性**：装修 / 医疗大额 / 车辆维修 / 礼金红包 / 父母医疗
   - **金融性支出**：房贷利息 / 信用卡分期手续费 / 投资亏损实现
5. **疑似分错列出来让用户确认**（不要静默归类）：
   - 列出所有"边界模糊"项（如"和客户吃饭"在柔性还是刚性？）
   - 用户确认后写入
   - 如果用户对某类有稳定判定（如"和客户吃饭算工作=刚性"），追加到 `budget.md` 的"分类规则备注"段
6. 二级 tag 选填：询问"是否要加 #自己 / #社交 / #家庭 / #工作 标签"
   - 跳过即不标
7. 算 frontmatter：
   - `total` = 5 大类之和
   - `income` = 收入段之和
   - `saving_rate` = (income - total) / income，保留 3 位小数
8. 对照 `budget.md` 检查超额项，在文件末尾写"对照 budget 标记"段
9. 更新 `.manifest.json` 的 `spending` 数组
10. git commit: `feat(finance): spending YYYY-MM`

### 类型 C · 目标变更
1. 判断动作：新增 / 修改 / 达成 / 放弃
2. 新增：
   - 询问 layer (bottom/middle/top)、name、target_amount、target_date、priority
   - 写入 `goals/active/<period>-<slug>.md`（slug 用拼音或英文，避免文件名特殊字符）
   - 追加到 `goals/pyramid.md` 对应层
3. 修改：
   - 更新 `goals/active/<name>.md` 对应字段
   - 在文件末尾"调整历史"段追加一行：`<date> · 改了什么 · 原因`
4. 达成：
   - 在文件 frontmatter 改 status: achieved
   - 移动到 `goals/archive/`
   - 从 `goals/pyramid.md` 对应层移除
5. 放弃：
   - 同达成，但 status: abandoned
6. **重算 pyramid 进度数字**（不重算状态判定 ✅/⚠️/❌——那是 review 的事）：
   - 进度% = current_amount / target_amount（current_amount 从用户输入获取，或保留原值）
7. 更新 `.manifest.json` 的 `goals` 段
8. git commit: `feat(finance): goal <action> <name>`

## 铁律
- ❌ 不编数据：金额模糊（如"大概一两万"）必须问清楚，不四舍五入猜
- ❌ 不主动复盘：只归档，不评判。月度复盘是 `finance-review` 的事
- ❌ 不动 `plans/`、不动 `reviews/`
- ❌ 自动归类时**不静默**——疑似分错必须列出让用户确认
- ❌ 重复月份的录入 → 更新原文件，不新建（一个月一份 snapshot/spending）
- ❌ 加密资产汇率未录入 → 必须先问当月汇率，不用上月汇率凑数
- ❌ 金额单位（万/千/元）模糊 → 必须确认，不允许猜
- ❌ 房产估值不允许凭感觉拍 → 必须有 source
- ✅ pyramid 的状态判定字段（✅/⚠️/❌）由 review 写，record 只写进度数字
- ✅ git commit 信息按设计文档约定（`feat(finance): ...`）

## 输出
执行完毕后简要汇报：
- 写了哪个文件 / 几条数据
- 算出的 net_worth / saving_rate
- 是否有需要用户后续确认的事项
- git commit hash
