---
name: wiki-lint
description: 健康审计 wiki 知识库。当用户说"检查一下 wiki""wiki 状态""wiki 有哪些问题"或输入 /wiki lint 时使用。执行 6 项检查，生成健康报告，建议修复方案。
---

# Wiki Lint

## 前置读取
1. `01_wiki/_meta/taxonomy.md`（标签受控词表）
2. `01_wiki/index.md`（索引）
3. `01_wiki/.manifest.json`（摄入记录）

## 执行步骤

### Step 1: 扫描所有页面
读取 `01_wiki/` 下所有 `.md` 文件（排除 `_meta/`、`raw/`、`index.md`、`log.md`）。
收集每个页面的：frontmatter、所有出链（`[[wikilinks]]`）、文件路径、最后修改时间。

### Step 2: 执行 6 项检查

#### Check 1: 断链（Broken Links）🔴
扫描所有 `[[wikilinks]]`，找出目标文件不存在的链接。
- 严重程度：**高**
- 输出：`[[concepts/xxx]]` in `entities/yyy.md` → 目标不存在

#### Check 2: 孤页（Orphan Pages）🟡
找出没有任何入链的页面（没有其他页面 `[[链接]]` 到它）。
- 严重程度：**中**（孤页说明知识没有连接到网络中）
- 排除：index.md 中的链接不算入链

#### Check 3: Frontmatter 完整性 🟡
检查每个页面是否包含必要字段：
- `title`（必须）
- `category`（必须，且值在 concepts/entities/howtos/references/synthesis 中）
- `tags`（必须，且每个标签在 taxonomy.md 中存在）
- `created`（必须）
- `updated`（必须）
- `status`（必须，且值在 stub/draft/mature/stale 中）
- `sources`（建议有）

#### Check 4: 过时检测（Staleness）🟢
- `status: stale` 的页面
- `updated` 超过 60 天且 `status` 不是 `mature` 的页面
- manifest 中记录的来源文件已修改但 wiki 页未更新

#### Check 5: 索引一致性（Index Sync）🔴
- index.md 中列出但文件不存在的条目
- 文件存在但 index.md 中没有的页面
- 严重程度：**高**

#### Check 6: 标签健康（Tag Health）🟡
- 使用了 taxonomy.md 中不存在的标签
- 超过 5 个标签的页面
- taxonomy.md 中定义但从未使用的标签（僵尸标签）

### Step 3: 生成报告

```markdown
## 📋 Wiki 健康报告 YYYY-MM-DD

### 📊 总览
- 页面总数：X
- 来源总数：Y（manifest）
- 问题总数：Z

### 🔴 高优先级（必须修复）
1. **断链**：N 处
   - `entities/yyy.md` → `[[concepts/不存在的页面]]`
2. **索引不同步**：N 处
   - `howtos/zzz.md` 不在 index.md 中

### 🟡 中优先级（建议修复）
1. **孤页**：N 个
   - `references/aaa.md` — 无入链，建议在相关 concept 页补充引用
2. **Frontmatter 缺失**：N 个
   - `concepts/bbb.md` 缺少 tags
3. **标签问题**：N 个
   - `concepts/ccc.md` 使用了未定义标签 `unknown-tag`

### 🟢 建议
1. **过时页面**：N 个
   - `entities/ddd.md` 60 天未更新
2. **Stub 待补充**：N 个
   - `concepts/eee.md`（stub）
3. **僵尸标签**：N 个
   - taxonomy 中定义了 `xxx` 但无页面使用
```

### Step 4: 建议修复
对每个问题给出具体修复建议。分为：
- **自动可修**：索引不同步、frontmatter 缺失 → 用户确认后直接修复
- **需要判断**：孤页（是否该建链接还是删除）、过时（是否需要更新）→ 逐项确认

### Step 5: 执行修复（用户确认后）
- 修复 index.md 同步
- 补充缺失的 frontmatter 字段
- 移除无效标签 / 更新 taxonomy
- 在相关页面补充交叉引用

### Step 6: 追加 log.md
```markdown
## [YYYY-MM-DD] lint | 健康检查
- 扫描页面数：X
- 发现问题：Y 个（🔴 A / 🟡 B / 🟢 C）
- 自动修复：Z 个
- 待用户确认：W 个
```

### Step 7: 更新 manifest stats
```json
"stats": { "last_lint": "2026-04-07T20:30:00+08:00" }
```

## 反模式
- 不要自动修复不确定的问题——先报告，等用户确认
- 不要删除任何页面，只标记为 `stale`
- 不要把 lint 报告本身存为 wiki 页面（它是临时输出）
