# Life OS — Wiki

LLM 驱动的个人知识库。基于 Karpathy LLM Wiki 模式。本文件是项目宪法，每次会话自动加载。

## 三重身份
本仓库同时是：
- **Git 仓库**：版本管理 + 云端备份
- **Obsidian vault**：可视化阅读、图谱浏览
- **Claude Code 工作区**：知识摄入、查询、维护

## 目录约定
- `01_wiki/` — 知识库主体（规范见 @01_wiki/_meta/schema.md）
  - `raw/` — 原始资料（不可变，LLM 只读不改）
  - `concepts/` — 概念、理论
  - `entities/` — 工具、框架、人物
  - `howtos/` — 操作方法
  - `references/` — 来源摘要
  - `synthesis/` — 跨领域综合分析
  - `_meta/` — schema + taxonomy + extraction-frames
  - `index.md` — 内容索引（LLM 维护）
  - `log.md` — 操作日志（append-only）
  - `.manifest.json` — 摄入追踪账本
- `.claude/skills/` — Claude Code 操作能力
- `.claude/commands/` — 快捷指令

## 铁律（不可违反）

1. **本地 Git 是真相源**。所有数据改动先改本地文件，git commit 之后才算数。

2. **读文件再行动**。wiki 操作前先读：
   - @01_wiki/_meta/schema.md（规范）
   - @01_wiki/_meta/taxonomy.md（标签）
   - @01_wiki/index.md（已有页面）
   - @01_wiki/.manifest.json（已摄入来源）

3. **破坏性操作先确认**。删除页面、批量修改、git push 前，列清单等我确认。

4. **不要编数据**。不确定的信息直接问我，不要猜。

5. **Wiki 是蒸馏后的知识**。不要把原始资料原封不动复制进 wiki，要提取、结构化、建立交叉引用。

6. **commit 信息用约定格式**：
   - `feat(wiki): ...` wiki 知识页面
   - `chore(wiki): ...` wiki 维护（lint/crosslink/tags）
   - `chore(os): ...` 系统层面
   - `feat(career): ...` 新增 career 内容（log/feedback/jd/interview）
   - `chore(career): ...` career 维护（review 产物、skills-map/roadmap/aggregate 更新）
   - `feat(finance): ...` 新增 finance 内容（import/equity/review-weekly/schema 校准）
   - `chore(finance): ...` finance 维护（review 产物、manifest/budget 维护）
   - `fix(finance): ...` finance 代码/数据修复

7. **联网默认直接搜**。`WebSearch` / `WebFetch` 是默认联网方式——公开网页、文档、API 检索直接用，不绕 skill。**仅在以下情况才调用 web-access skill**：需要登录态、反爬/动态站点（如 Coinglass 面板、小红书）、或需要并行子 agent 共享浏览器。本条**覆盖** web-access skill 描述里"所有联网操作必须通过此 skill"的旧说法。

## 常见请求 → skill 路由
- "整理/沉淀概念" / `/wiki ingest` → wiki-ingest skill
- "X 是什么 / 对比 X 和 Y" / `/wiki query` → wiki-query skill
- "检查 wiki" / `/wiki lint` → wiki-lint skill
- "wiki 状态 / 有多少页" / `/wiki status` → wiki-status skill
- "补充链接 / 交叉引用" / `/wiki crosslink` → cross-linker skill
- "整理标签 / 加标签" / `/wiki tags` → tag-taxonomy skill
- "记一下今天工作 / 收到反馈" / `/career log` → career-log skill
- "新 JD / 分析 JD" / `/career jd` → career-jd skill
- "周/月/季复盘" / `/career review [week|month|quarter]` → career-review skill
- "学习路线 / 差距分析" / `/career roadmap` → career-roadmap skill
- "面试题 / 整理面试题" / `/career interview` → career-interview skill
- "导入成交 / 导入流水 / 上传交易 / 贴账单 / 记一下消费" / `/finance import` → finance-import skill
- "周复盘 / 本周交易 / 本周总结" / `/finance review week` → finance-review skill（month/quarter/year MVP-2 起启用）
- ~~`/finance record`~~ 已并入 finance-import；~~`/finance plan`~~ → later（MVP-3 起）
- "逆向这份分析/报告/演讲" / "复盘这个人的思维" / "推证据链" / `/forge` → analysis-forge skill
- （仅 Telegram 频道会话）"重置会话 / 清空上下文 / reset" → 先用 reply 工具回复确认，再执行 `.tools/telegram-reset.sh`（5 秒后会话自杀重建，上下文清空，无需再回复）

## 04_career — 职业成长追踪
- 事件式输入（log / feedback / jd / interview）+ 周期复盘（reviews）+ 持续维护（skills-map / roadmap / aggregate）
- 五个 career-* skill 配合三层定时提醒（周/月/季）
- 与 01_wiki 边界：技术知识点走 wiki（中性、永恒），职业事件走 04_career（个人、有时间戳）
- 提醒由 macOS launchd 触发 `04_career/_tools/<period>-reminder.sh` → `.tools/notify.sh` → 飞书
- 详见 `04_career/_design/2026-05-22-career-growth-module-design.md`

## 05_finance — 个人理财追踪
- v2.1 重构：「稳健 + 风险」两层架构，导入型输入替代手填快照，先用 Bitget 交易 loop（MVP-1）验证习惯再扩稳健层（MVP-2）
- 两个 finance-* skill：`finance-import`（导入型唯一写入口，按来源分流交易/支出）+ `finance-review`（week 周复盘 MVP-1；month/quarter/year MVP-2 起启用）；旧 finance-record / finance-plan 已废弃（record 并入 import，plan 推迟到 MVP-3；skill 文件已按裁决删除 2026-07-03）
- 目标锚点迁移至 `00_north-star/goals.md`（年储蓄目标 + drawdown_cap_from_peak）；旧 `05_finance/goals/` 已标废弃、新 loop 跑通后删
- 自动化只剩 weekly 一档：周日 20:00 全自动拉取（launchd → `weekly-auto-pull.sh`：API 拉已平仓+权益 → 写表 → commit → 通知；任何失败降级为催促探针 `weekly-submit-reminder.sh`），月/季/年三档已停；fills 已校准接入（trades.csv 自动落盘，亏损加仓诊断激活）
- 与 04_career 边界：career 管"赚钱能力"，finance 管"赚到的钱怎么用"——两个模块互相提示但不互相写
- 与 01_wiki 边界：理财通用知识（标普家庭资产象限 / 再平衡原理）入 wiki；个人事件、目标、决策入 finance
- 加密资产按月初汇率统一折 RMB；隐私采用明文存储，未来上云需走 README 的"双文件分层"升级路径
- 通知基础设施（`.tools/notify.sh`）与 04_career 共用，飞书（lark-cli）+ telegram 双通道可配置
- 详见 `05_finance/_design/2026-06-03-finance-refactor-design.md`（v2.1）

## 输出风格
直接、具体、可执行。不铺垫，不寒暄。不合理的建议直接指出。

## 后续扩展（留给 v0.4）
- wiki 搜索引擎（qmd 等，小规模用 index.md 够用）
- 自动从 Claude 对话历史摄入知识
- 批量 ingest 模式
