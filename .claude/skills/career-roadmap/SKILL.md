---
name: career-roadmap
description: 学习路线 + 差距分析。当用户说"学习路线""差距分析""怎么补 X""下一步学什么"或输入 /career roadmap 时使用。基于 skills-map vs jd/aggregate 计算差距，按 P0-P3 排序，覆盖式更新 roadmap.md。
---

# Career Roadmap

## 前置读取
1. `04_career/skills-map.md`
2. `04_career/jd/aggregate.md`
3. `04_career/jd/active/*.md`（用于 P3 反查 `in-jd-weight=3` 的核心要求）
4. `04_career/roadmap.md`（当前版本，覆盖前比对）
5. `04_career/growth-trajectory.md`（用于追加事件标记）

## 数据契约（来自 04_career 模块设计文档 §3.4）

### roadmap.md
- 路径：`04_career/roadmap.md`（**单文件，覆盖式更新**——不分多版本，旧版本走 git history）
- frontmatter 字段（YAML）：
  - `type: career-roadmap`
  - `created: YYYY-MM-DD`（**保留原值，不重置**）
  - `updated: YYYY-MM-DD`（每次覆盖更新为今天）
  - `status: empty | active`（**闭集**：未生成时 `empty`，已生成后 `active`）
  - `based-on:` YAML 子字段，列出依赖数据源 + 更新时间 + active-count：
    ```yaml
    based-on:
      - skills-map: 04_career/skills-map.md（updated: YYYY-MM-DD）
      - jd-aggregate: 04_career/jd/aggregate.md（updated: YYYY-MM-DD, active-count: N）
    ```
- 正文章节（**顺序固定，标题不变**）：
  1. `## 优先级 P0（立即开始）`
  2. `## 优先级 P1`
  3. `## 优先级 P2`
  4. `## 优先级 P3（低频但核心）`
  5. `## 历史`

### 每项必须三段格式（缺一不可）
```markdown
### {技能名}
- **差距证据**：coverage X/Y · 平均 required-level: Z · 你的 level: W
- **学习路径**：
  1. {步骤 1，含具体内容}，估时 X 周
  2. {步骤 2}，估时 Y 周
  3. （可选）{步骤 3}
- **关联**：[[03_study/{topic}/]]（建议创建 / 已存在）
- **验证标志**：能用 X 完成 Y（**具体可验证动作**）
- **估时合计**：N 周
```

### 优先级闭集（P0/P1/P2/P3）

**P0-P3 优先级闭集**（按 active-count = N 缩放，但仍保留绝对数下限）：
- **P0**：状态 ❌ 且 `coverage ≥ 5/N`（高频技能完全缺失）
- **P1**：状态 ❌ 且 `coverage ∈ [3/N, 4/N]`（中频 + 全缺），**或** 状态 ⚠️ 且 `coverage ≥ 5/N`（高频 + 距离 1 档）
- **P2**：状态 ⚠️ 且 `coverage ∈ [3/N, 4/N]`（中频 + 距离 1 档）
- **P3**：低频但 `in-jd-weight=3` 的核心要求——需从 `jd/active/*.md` 反查哪些 JD 给该 skill 标了 `in-jd-weight=3`（即使 `coverage < 3/N`）

**N 较小时的特例**：
- N=1 时，5/N 等价于全覆盖（仅 1 条 JD），按"⚠️/❌ 即 P0/P1"处理
- N=2 时，3/N=1.5 取下限 = 1（即 1/2 = 50% 已算 P1.lower）

**优先级互斥**：一个 skill 同时满足多档时，归入**数字最小的那档**（如 ❌ + coverage 6/8 + in-jd-weight=3 → 归 P0，不重复列入 P3）。

### 状态符号闭集
- ✅ 满足（你的 level ≥ 平均 required-level）
- ⚠️ gap 但小（你低 1 档）
- ❌ gap 大或全缺（你低 ≥ 2 档，或 `none`）

### level 排序
- `none < junior < mid < senior < staff`
- 与 career-jd / career-review 完全一致

### skill 名匹配规则（aggregate.md skill → skills-map.md 条目）
复用 career-jd 同一套：
1. **精确匹配**：去掉空格和标点后比对 skill 名 — 命中即用
2. **包含匹配**：若 skill 作为子串包含在 skills-map 条目名中（如 `Flink` 命中 `Flink 框架（状态管理 / 容错 / 反压）`）— 算命中
3. **多重命中**：多个 skills-map 条目同时被命中 → 取**较高 level**（与"多个众数取较高"规则一致）
4. **可疑匹配**：包含匹配命中但可能误判（如 `Java` 命中 `JavaScript`）→ 在变更清单里标"⚠️ 可能误匹配"，提醒用户人工核对
5. **完全无命中**：取 `none`（走"新增"路径，进入差距分析）

### 03_study 联动规则
- 路径骨架：`03_study/<topic>/raw/` + `03_study/<topic>/processed/`
- **只建空骨架，不写文件**（由 transcript-to-notes / wiki-ingest 按需填充）
- `<topic>` 命名：小写英文 + 短横线（如 `langchain` / `multimodal-llm` / `flink`），保留中文用户偏好优先按用户答复确定
- 建目录前必须问用户：是否要为这项学习建骨架？默认不建，等用户确认

### growth-trajectory.md 追加格式
- 按 `## YYYY-MM` H2 月段组织，**月段倒序**（最新月在上）
- **月内条目按日期倒序**，最新事件在段落顶部
- 事件类型（闭集）：`roadmap updated`
- 事件格式：
  ```
  - 2026-05-23 → roadmap updated → [[04_career/roadmap.md]]
  ```
- 如果月份段落不存在，新建 `## YYYY-MM` 段落，按月段倒序插入

## 前置检查（决定执行哪个场景）
- 若 `jd/aggregate.md` 的 `active-count: 0` 或 `aggregate.md` 不存在 → **场景 D（前置缺失）**：告知"暂无 active JD，无法生成路线"，建议先 `/career jd`，**不动 roadmap.md，不 commit**
- 若 `skills-map.md` 为空（除 frontmatter 外无任何条目）→ **场景 D**：告知"skills-map 未初始化，请先确认"，**不动 roadmap.md，不 commit**

## 场景分支总览

**A. 首次生成**：当前 roadmap.md 的 `status: empty`（或文件不存在） → 正常生成全量。
**B. 增量更新**：当前 roadmap.md 的 `status: active` → 比对差异 + 进展继承询问 + 覆盖式更新。
**C. 无差距**：差距清单为空（所有 skill 状态 ✅） → 不出具体项目，仅更新 frontmatter 的 `updated` 字段表明"已审计"，正文章节为空白或写"当前能力已满足所有 active JD 要求"。
**D. 前置缺失**：`active-count=0` 或 `skills-map` 空 → 不动 roadmap.md，仅输出提示。

四种场景在不同 Step 处分叉，下文每步注明。

## 执行步骤

### Step 1: 计算差距清单（A / B / C 场景）

读 `jd/aggregate.md` 全部技能条目（高频 + 中频 + 低频但高权重三段），对照 `skills-map.md`（按 skill 名匹配规则）：

| 你的 level vs 平均 required-level | 状态 |
|---|---|
| 你 ≥ JD 要求 | ✅（跳过，不入清单） |
| 你低 1 档（或 skills-map 无对应条目但 JD 要求 ≤ mid） | ⚠️ |
| 你低 ≥ 2 档，或 你 = `none` 且 JD 要求 ≥ mid | ❌ |

对每个 gap 项，记录：
- `skill` 名
- `coverage`（如 `4/8`）
- `平均 required-level`
- `你的 level`（含 `none`）
- `gap 状态`（⚠️ / ❌）
- 该 skill 在所有 active JD 中的最大 `in-jd-weight`（用于 P3 判定）

**C 场景判定**：若上述清单为空（所有 skill 状态 ✅） → 跳到 Step 4 走 C 场景流程。

### Step 2: 按优先级分档（A / B 场景）

按数据契约的 **P0/P1/P2/P3 判定规则**对 Step 1 清单分档。

每项必须能填出三段：
- **差距证据**：从 Step 1 记录直接生成
- **学习路径**：1-4 步，每步带估时（不写"待补充"以外的虚资料）
- **验证标志**：能用 X 完成 Y（**具体可验证动作**，不是"理解 X"或"了解 X")

**关于资料推荐**：
- 默认**不主动给资料列表**——避免堆资料 AI slop
- 用户问"推荐什么资料" → 每项至多 2-3 个推荐，必须真实可考
- 不知道具体资料 → 步骤里写"找 X 方向的入门资料"或"待补充"，**不编书名/课程名**

### Step 3: 用户确认 + 收集补充信息（A 场景）

列出 P0/P1/P2/P3 清单给用户确认。问：
1. 哪些项**不学**（用户可能因转型/不感兴趣 reject 某项——例如目标转岗时旧技能栈不再补）
2. 是否要在 `03_study/` 下建对应学习目录骨架（默认不建）
3. 是否需要资料推荐（默认不给）

用户回复后按需调整清单 + 计划建的骨架目录列表。

**Step 3 用户全拒绝处理**：
若用户在 Step 3 把所有差距项标"不学" → 退化到 C 场景流程（正文四个优先级章节均"（无）"，commit message 改为 `chore(career): roadmap, all gaps deferred by user`）。

### Step 3'（B 场景特例）: 进展继承询问

**仅 B 场景**（当前 roadmap.md 的 `status: active`）执行。

覆盖前先识别上版 roadmap 中的进展标记：
- `[x]` 完成标记
- 步骤里手写"已完成"/"已做到 Step N"/"进展：..."等
- 同名技能项在新清单中仍存在但优先级变化

输出给用户：

```
🔍 识别到上版 roadmap 含进展标记：
- X 项 P0 已部分完成（<技能名>，已完成步骤 1）
- Y 项 P1 进行中（<技能名>）
- Z 项已不在新差距清单中（你的 level 已升级 / JD aggregate 变化）

是否：
1. 保留进展，仅追加新差距 / 调整优先级（推荐）
2. 全量重新生成（旧进展进 git history，但新版本不显示）

请选择：
```

默认推荐选项 1。

- 选 1 → 在覆盖时，把仍在新清单中的项的进展段照搬到新文件；新增项按 Step 2 三段格式补全
- 选 2 → 全量按 Step 2 生成新清单（旧进展不传递）

然后走 Step 3 的用户确认流程（不学项 / 03_study 骨架 / 资料推荐）。

### Step 4: 覆盖式写入 roadmap.md

**C 场景 noop 短路（写入前检查）**：
若当前 `04_career/roadmap.md` 已是 C 场景模板（status: active 且四个优先级章节均为"（无）"）**且** frontmatter `updated == today` → 跳过写文件 + 跳过 growth-trajectory 追加 + 跳过 commit；仅输出"今日已审计过，无变化"。

**其它情况**正常按场景写入（A/B/C/D 模板，见下方）。

按场景分支：

#### A / B 场景（生成或更新）

写入 `04_career/roadmap.md`（覆盖原文件）：

```markdown
---
type: career-roadmap
created: <保留原 created；首次生成则填今天>
updated: 2026-05-23
status: active
based-on:
  - skills-map: 04_career/skills-map.md（updated: YYYY-MM-DD）
  - jd-aggregate: 04_career/jd/aggregate.md（updated: YYYY-MM-DD, active-count: N）
---

# 学习路线 · 2026-05-23 版

## 优先级 P0（立即开始）

### {技能名}
- **差距证据**：coverage 4/8 · 平均 required-level: mid · 你的 level: none
- **学习路径**：
  1. 看 {资料 / 课程 / 文档（具体或"待补充"）}，估时 1 周
  2. 做 mini 项目 {具体描述}，估时 2 周
  3. （可选）实操到工作场景
- **关联**：[[03_study/{topic}/]]（建议创建 / 已存在）
- **验证标志**：能用 X 完成 Y（如"能用 LangChain 写一个多模态查询 Agent"）
- **估时合计**：3 周

## 优先级 P1
（同上格式）

## 优先级 P2
（同上格式）

## 优先级 P3（低频但核心）
（同上格式；说明为何低频但仍列入——因为有 JD 标 in-jd-weight=3）

## 历史
- 上版：YYYY-MM-DD（git log 可回溯具体改动）
```

**B 场景**：若用户选了"保留进展"，则在被继承项的"学习路径"步骤里保留 `[x]` 已完成标记或"进展：..."文字。

#### C 场景（无差距）

仍覆盖 roadmap.md，但正文章节简化：

```markdown
---
type: career-roadmap
created: <保留原 created>
updated: 2026-05-23
status: active
based-on:
  - skills-map: 04_career/skills-map.md（updated: YYYY-MM-DD）
  - jd-aggregate: 04_career/jd/aggregate.md（updated: YYYY-MM-DD, active-count: N）
---

# 学习路线 · 2026-05-23 版

> 当前能力已满足所有 active JD 要求，无 gap 项。

## 优先级 P0（立即开始）
（无）

## 优先级 P1
（无）

## 优先级 P2
（无）

## 优先级 P3（低频但核心）
（无）

## 历史
- 上版：YYYY-MM-DD（git log 可回溯）
```

#### D 场景（前置缺失）

**不写文件，不 commit**。直接输出提示并退出。

### Step 5: （可选）创建 03_study 目录骨架（A / B 场景）

对用户在 Step 3 同意创建的学习项：

```bash
mkdir -p "03_study/<topic>/raw" "03_study/<topic>/processed"
touch "03_study/<topic>/raw/.gitkeep" "03_study/<topic>/processed/.gitkeep"
```

> `.gitkeep` 是必需的——git 不跟踪空目录。

**不写文件**（由 transcript-to-notes / wiki-ingest 按需填充）。`<topic>` 名含中文或特殊字符的，路径必须用双引号包裹。

### Step 6: 追加 growth-trajectory（A / B / C 场景）

向 `04_career/growth-trajectory.md` 对应 `## YYYY-MM` 月段顶部追加一行：

```
- 2026-05-23 → roadmap updated → [[04_career/roadmap.md]]
```

如果月份段落不存在，新建 `## YYYY-MM` 段落，按月段倒序（新月在上）插入。

**D 场景**：不追加。

### Step 7: Commit（按场景分支）

含中文/括号/空格的路径必须用双引号包裹。

**A / B 场景（生成或更新 roadmap）**：

```bash
git add "04_career/roadmap.md" "04_career/growth-trajectory.md"
# 若 Step 5 建了 03_study 骨架，把目录或 .gitkeep 一起 add（git 不跟踪空目录，需在每个新目录里 touch 一个 .gitkeep）
# 例：git add "03_study/langchain/.gitkeep" "03_study/multimodal-llm/.gitkeep"
git commit -m "chore(career): update roadmap (gap analysis 2026-05-23)"
```

> **空目录提示**：若 Step 5 创建了空骨架，请在每个新目录内 `touch .gitkeep` 让 git 能跟踪——否则 `git add` 不会记录空目录。

**C 场景（无差距，仅更新 frontmatter `updated` 字段）**：

```bash
git add "04_career/roadmap.md" "04_career/growth-trajectory.md"
git commit -m "chore(career): re-audit roadmap, no gaps 2026-05-23"
```

**D 场景（前置缺失）**：

```
# 不执行任何 git 操作。仅输出提示：
# "暂无 active JD（或 skills-map 未初始化），无法生成路线。建议先执行 /career jd 录入目标岗位。"
```

### Step 8: 输出确认（按场景分支）

**A 场景（首次生成）**：
```
✅ 已生成学习路线：04_career/roadmap.md
📊 P0: N 项 · P1: M 项 · P2: K 项 · P3: J 项
📁 03_study 骨架：已创建 <topic 列表>（若有）
📈 growth-trajectory：已追加 1 条事件标记
💡 建议下一步：从 P0 开始执行，记录到 /career log
```

**B 场景（增量更新）**：
```
✅ 已更新学习路线：04_career/roadmap.md
🔄 进展继承：<保留 N 项 / 全量重新生成>
📊 P0: N 项 · P1: M 项 · P2: K 项 · P3: J 项
📈 growth-trajectory：已追加 1 条事件标记
```

**C 场景（无差距）**：
```
🟢 当前能力已满足所有 active JD 要求，无 gap。
✅ roadmap.md 已重新审计（frontmatter updated → 2026-05-23）
💡 建议：继续保持，或新增更高目标 JD（/career jd）扩展画像
```

**D 场景（前置缺失）**：
```
⚠️ 前置缺失：<暂无 active JD | skills-map 未初始化>
建议：先执行 <推荐命令>，再回来跑 /career roadmap
```

## 铁律
- **不堆砌资料列表**——每项至多 2-3 个推荐，且必须真实可考；用户没要资料时不主动给
- **每项必须有"差距证据 → 学习路径 → 验证标志"三段**——缺一不可
- **不删旧 roadmap**——覆盖前先 git commit，依靠 git log 回溯
- **不动 skills-map / log / feedback / jd**——只读不写
- **学习路径里的"具体资料"必须可考**——不知道资料就写"待补充"，不编书名/课程名
- **验证标志必须是可执行动作**——"能用 X 完成 Y"，不是"理解 X 的原理"
- **不计算"还要多久能拿到 X 岗位"**——避免假预测
