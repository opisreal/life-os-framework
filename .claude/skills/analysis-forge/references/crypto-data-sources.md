---
title: crypto 数据层选型（forge 首个验证案例素材）
type: reference
created: 2026-06-08
note: 待 06_market 模块建成后迁入 06_market/_design/
---

# crypto 数据层选型

> forge 首次产出（加密趋势分析 agent）的数据层选型素材。2026-06 调研，按"准备成本"分层。
> 这是 forge 组件复用扫描（§4 ②）在 crypto 领域的一次实例输出，也是 ComponentMap 的真实样例。

## Tier 0 — 零准备直接用（免费 / 无 key）

| 组件 | 类型 | 提供 | 信任度 |
|---|---|---|---|
| CCXT + CCXT MCP (doggybee) | lib / mcp | K线/资金费率/OI/盘口，三大所统一 | 高星开源(MIT) |
| CoinGecko MCP（keyless 端点） | mcp | 市场总览/历史价/链上 DEX | 官方 |
| alternative.me 恐慌贪婪指数 | api | F&G 指数，已实测 HTTP 200 | 官方，永久免费 |
| DefiLlama (free) | api | TVL / 赛道 | 官方 |
| TA-Lib（需装 C 库）/ pandas-ta-classic | lib | 技术指标（150 / 252） | 高星开源 |
| Freqtrade(GPL,独立进程) / Jesse(MIT) | lib | 回测引擎 / 历史数据 | 高星开源 |

## Tier 1 — 免费但需注册 key / 申请

| 组件 | 提供 | 需准备 |
|---|---|---|
| Coinalyze（免费 key, 40/min） | 清算**时序**总量 + 多空比 + 资金费率（⚠️无价位级热力图） | 注册拿免费 key |
| SoSoValue（免费 Demo key） | ETF 每日净流主源（官方 JSON） | 注册 + 申请 key（**要审批，早提**） |
| CoinGecko Demo key（10k/月） | 小币基本面（supply/赛道/白皮书） | 注册拿 Demo key |
| DropsTab Builders Program | 小币解锁 + 融资 + VC | 申请 Builders（**要审批，免费 3 个月**） |
| Dune（免费 key + 2500 credits/月 + 官方 MCP） | 自建任意链上指标 | 注册拿 key |

## Tier 2 — 付费按需

- 🔴 **价位级清算热力图**（ETH 报告最值钱的信号源：1555 清算价 / 6.27 亿空单强度）：
  - **CoinAnk $30/mo**（最便宜，含热力图 + MCP + CLI + **7 天试用**）
  - ≫ Coinglass 价位级 $699/mo ≫ Hyblock $499/mo（avoid）
  - ⚠️ 免费世界拿不到价位级（Coinalyze 只有时序聚合）
- 交易所净流 / Whale Ratio：CryptoQuant ~$99/mo
- 链上高分辨率：Glassnode ~$79/mo

## 架构蓝图（非数据源）

**TradingAgents（83k⭐, Apache-2.0）**——多 agent"交易公司"：分析师团队（基本面/情绪/新闻/技术）+ 研究员多空辩论 + trader + 风控。几乎就是 forge 设计的"扇出 lens → 对抗证伪"。**借架构，换加密数据层**（它原本为股票设计、数据靠 Yahoo Finance）。

## 用户需提前准备（最小集，全免费）

1. 注册 CoinGecko → Demo key
2. 注册 Coinalyze → 免费 key
3. 注册 SoSoValue → 申请 ETF key（要审批，早提）
4. 申请 DropsTab Builders（要审批，早提）
5. 注册 Dune → key
6.（可选）`brew install ta-lib`

零 key 即用的（CCXT / CoinGecko MCP / F&G / DefiLlama）不用准备。

## 预算决策（待用户拍板）

价位级清算热力图：建议先用全免费栈起步、清算先用 Coinalyze 时序版，价位级热力图用 CoinAnk 7 天试用验证价值，觉得值再 $30/mo。
