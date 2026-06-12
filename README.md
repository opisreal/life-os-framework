# Life OS

LLM 驱动的个人操作系统，跑在 [Claude Code](https://claude.com/claude-code) 上：知识库、职业成长、个人理财、自动化调度，四件事一个工作区。知识库部分基于 [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 模式。

三重身份：**Git 仓库**（版本管理 + 备份）/ **Obsidian vault**（图谱浏览）/ **Claude Code 工作区**（摄入、查询、维护全部对话完成）。

## 双仓库设计

| 仓库 | 内容 | 可见性 |
|---|---|---|
| `life-os`（私有工作区） | 框架 + 个人数据，日常唯一工作区 | 私有/本地 |
| `life-os-framework`（本仓库的公开形态） | 仅框架：skills、工具脚本、schema、目录骨架 | 公开 |

公开仓库由私有工作区**白名单导出**自动生成（`.tools/export-framework.sh`）：显式枚举可导出路径（默认拒绝）→ 机器路径脱敏 → 敏感模式扫描门（命中即中止并告警）→ 独立署名提交推送，由 post-commit hook 触发。公开仓库永不直接编辑。

## 模块

| 目录 | 职责 |
|---|---|
| `00_north-star/` | 目标锚点（年度目标、风控红线） |
| `01_wiki/` | 知识库：raw → 蒸馏 → concepts/entities/howtos/references/synthesis，规范见 `_meta/` |
| `02_daily/` | 日常记录 |
| `03_study/` | 课程学习（转录稿 → 结构化笔记） |
| `04_career/` | 职业成长：事件式输入（log/feedback/jd/interview）+ 周期复盘 + skills-map/roadmap |
| `05_finance/` | 个人理财：导入型输入（交易/支出）+ 周期复盘，「稳健 + 风险」两层架构 |
| `.claude/skills/` | 全部操作能力（wiki-* / career-* / finance-* / analysis-forge 等） |
| `.tools/` | 自动化层：launchd 调度、Telegram 通知、常驻通道、框架导出 |

项目宪法（铁律、skill 路由、模块边界）见 [CLAUDE.md](CLAUDE.md)。

## 快速开始

```bash
git clone git@github.com:opisreal/life-os-framework.git life-os
cd life-os && claude
```

对话即操作：

- `/wiki ingest` 摄入资料 · `/wiki query` 基于库回答 · `/wiki lint` 健康审计
- `/career log` 记工作事件 · `/career review week` 周复盘 · `/career roadmap` 差距分析
- `/finance import` 导入交易/支出 · `/finance review week` 交易周报

Obsidian 用户：Open folder as vault 选本目录，Graph View 浏览知识网络。

## 自动化层（可选）

三层调度，按"是否需要模型"分界：

1. **launchd + 纯 bash** — 机械任务（CLI 升级、提醒通知），零 token
2. **launchd + `claude -p`** — 需要搜索/理解/组织的定时推送（如每日早报），可锁定轻量模型
3. **Claude Code Channels** — 事件驱动：Telegram 消息实时推进本地常驻会话，远程操作本机文件

配置步骤：

```bash
cp .tools/.env.example .tools/.env.private        # 填入你的 Telegram 群 ID 等
cp .tools/notify.config.example.json .tools/notify.config.private.json
cp .tools/launchd/*.plist ~/Library/LaunchAgents/ # 按需挑选
cp .tools/git-hooks/post-commit .git/hooks/       # 如需框架导出管线
```

launchd 任务清单与卸载方式见 [.tools/README.md](.tools/README.md)。

## 隐私设计

- 个人数据（wiki 内容、career 事件、finance 数据）只存在于私有工作区，公开仓库零数据
- 敏感标识符（群 ID、token）一律走 gitignore 的私有配置，框架脚本本体零硬编码
- 导出管线双闸：白名单显式枚举 + 发布前敏感扫描，任一不过即中止

## 版本

v0.4 · 2026-06
