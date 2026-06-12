# Life OS — Wiki

LLM 驱动的个人知识库。基于 [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 模式。

三重身份：Git 仓库 + Obsidian vault + Claude Code 工作区。

## 快速开始

### 用 Claude Code
```bash
cd ~/life-os && claude
```
然后试试：
- `/wiki ingest` — 摄入资料到知识库
- `/wiki query` — 基于知识库回答问题
- `/wiki lint` — 健康审计
- `/wiki status` — 查看状态
- `/wiki crosslink` — 补充交叉引用
- `/wiki tags` — 标签管理

### 用 Obsidian
打开 Obsidian → Open folder as vault → 选 `~/life-os`。
用 Graph View 浏览知识网络。

## 目录说明
- `01_wiki/` — 知识库主体
  - `raw/` — 原始资料
  - `concepts/` — 概念
  - `entities/` — 工具/框架
  - `howtos/` — 操作方法
  - `references/` — 来源摘要
  - `synthesis/` — 综合分析
- `.claude/` — Claude Code 配置

## 版本
v0.3-wiki · 2026-04
