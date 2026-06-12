# 04_career — 职业成长追踪模块

> Life OS 的第二个领域模块。事件式输入 + 周期复盘 + 持续维护。

## 目录导航

| 路径 | 用途 | 维护者 |
|---|---|---|
| `简历/` | 简历版本 | 用户手工 |
| `log/` | 工作日志（事件式） | `career-log` |
| `feedback/` | 反馈记录 | `career-log` |
| `jd/active/` | 关注中的 JD | `career-jd` |
| `jd/archive/` | 已淘汰/已应聘 JD | `career-jd` (需确认) |
| `jd/aggregate.md` | JD 聚合画像 | `career-jd` (自动) |
| `interviews/questions/` | 面试题单题 | `career-interview` |
| `interviews/aggregate.md` | 错题集 | `career-interview` (自动) |
| `reviews/{weekly,monthly,quarterly}/` | 周/月/季复盘报告 | `career-review` |
| `skills-map.md` | 能力地图 | `career-review` (更新 level/evidence/last-used) |
| `growth-trajectory.md` | 成长轨迹时间线 | 所有 career-* skill 追加 |
| `roadmap.md` | 学习路线 | `career-roadmap` |
| `.manifest.json` | 摄入与状态账本 | 所有 career-* skill |
| `_design/` | 模块设计文档 | 设计阶段产物 |

## 命令

| 命令 | 用途 |
|---|---|
| `/career log` | 记录工作/反馈 |
| `/career jd` | 录入 JD + 技能抽取 |
| `/career review week|month|quarter` | 周期复盘 |
| `/career roadmap` | 学习路线 + 差距分析 |
| `/career interview` | 面试题单题记录与分析 |

## 与其他模块的边界

- 技术知识 → `01_wiki/`（中性、永恒、可复用）
- 个人事件、能力评估、目标对照 → `04_career/`（强职业目的）
- 学习材料的笔记 → `03_study/`（由 `transcript-to-notes` 处理）
- 简历 → `04_career/简历/`（用户手工维护，复盘只提示不改写）

详见 `_design/2026-05-22-career-growth-module-design.md`。
