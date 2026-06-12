---
name: career-interview
description: 面试题单题记录与分析。当用户说"面试题""今天的面试""复盘面试""整理面试题"或输入 /career interview 时使用。按知识点聚合（同题多场→单文件累积），抽取知识点 wikilink 到 01_wiki，错点反哺 roadmap。
---

# Career Interview

## 前置读取
1. `04_career/.manifest.json`（确认/初始化 `interviews.questions` 数组）
2. `04_career/interviews/questions/` 现有单题文件列表（用于模糊匹配 topic）
3. `04_career/interviews/aggregate.md`（当前错题集 + 高频考点视图）
4. `01_wiki/index.md`（判断知识点是否已沉淀）
5. `04_career/skills-map.md`（错点反哺判定时参考，**只读不写**）
6. `04_career/roadmap.md`（错点反哺判定时参考，**只读不写**）

## 数据契约（来自 04_career 模块设计文档 §2.2 + §3.5）

### interview question 单题文件
- 路径：`04_career/interviews/questions/<topic>.md`
- **topic 命名规则**（**必须严格遵守**）：
  - 小写中横线分隔
  - 保留中文（如 `flink-反压机制` 而非 `flink-fanya-jizhi`）
  - 去除空格 + 路径不安全字符（`/`、`:`、`?`、`#`、`\`、`*`、`<`、`>`、`|`、`"`）
  - 不要做大小写归一化（保留用户给的术语原写法）
  - 示例：`flink-反压机制.md` / `spark-shuffle-内存调优.md` / `langchain-memory-类型.md`

- frontmatter 字段（YAML）：
  - `type: career-interview-question`
  - `topic: <topic 字符串，与文件名一致>`
  - `category: 数据工程 | AI 应用 | 算法 | 系统设计 | 软实力 | 其他`（**闭集**，超出 → 问用户归并到哪档）
  - `knowledge-point: [[01_wiki/concepts/...]] | <topic>（待 /wiki ingest 沉淀）`
  - `difficulty: easy | medium | hard | staff-level`（**闭集**）
  - `status: ✅ complete | ⚠️ partial | ❌ failed`（**闭集**；文件级聚合状态，取所有 encountered 中 my-answer-quality 的最差档）
  - `encountered:` YAML 数组，每条含：
    - `date: YYYY-MM-DD`
    - `company: <公司>`
    - `position: <岗位>`
    - `round: <轮次，如 一面/二面/技术面/HR 面>`
    - `my-answer-quality: complete | partial | failed`（**闭集**，对应文件级 status 的三档）
  - `times-asked: <整数>`（= `encountered` 数组长度）
  - `last-seen: YYYY-MM-DD`（= 所有 encountered 中最近的 date）

- 正文五段（**顺序固定，标题不变**）：
  1. `## 题面`
  2. `## 我的回答`（单场直接写；多场按 `## 我的回答 · 第 N 场（YYYY-MM-DD）` 分段，N 按 encountered 索引递增）
  3. `## 标准答案要点`（基于 wiki 已有知识或公认参考给要点；wiki 未沉淀 → 写"待补充"或建议 wiki-query 找；**不写范文**）
  4. `## 我的差距`（对比"我的回答" vs "标准答案要点"列出漏点/错点；多场合并增量，不删旧）
  5. `## Next Actions`（待补的知识点 / 是否进 roadmap）

### 状态符号闭集
- `✅ complete` — 答得基本完整，方向对 + 关键点齐全
- `⚠️ partial` — 漏了关键点但方向对
- `❌ failed` — 答错或完全没答出来

`my-answer-quality` 三档与 status 完全对应（单场记录 → 文件级聚合时取最差档）。

### 难度闭集
- `easy` — 基础概念题
- `medium` — 涉及实操或深度
- `hard` — 综合 / 边界 / 性能调优
- `staff-level` — 系统设计 / 架构权衡 / 跨领域整合

### category 闭集
- `数据工程` / `AI 应用` / `算法` / `系统设计` / `软实力` / `其他`
- 超出 → **问用户**归到哪档；不要静默猜。

**常见细分领域映射**（避免每次问用户）：
- 实时计算 / 离线计算 / 数据库 / 数仓 / OLAP / 数据治理 → 数据工程
- LLM / Agent / Prompt / RAG / 多模态 → AI 应用
- 算法题 / 数据结构 / 复杂度分析 → 算法
- 架构设计 / 高可用 / 分布式 → 系统设计
- 跨团队 / 沟通 / leadership / 推动落地 → 软实力
- 其它无法归类 → 其他（**保留用户确认入口**）

### level 排序（错点反哺判定用）
- `none < junior < mid < senior < staff`
- 与 career-jd / career-roadmap / career-review 完全一致

### 文件级 status 升级规则（B 更新模式）
新场次 my-answer-quality 进来时，按"最差档保留"语义：

| 新场次 quality | 文件原 status | 文件新 status |
|---|---|---|
| ❌ failed | 任意 | ❌ failed |
| ⚠️ partial | ✅ complete | ⚠️ partial |
| ⚠️ partial | ⚠️ partial | ⚠️ partial（不变）|
| ⚠️ partial | ❌ failed | ❌ failed（不降级）|
| ✅ complete | ✅ complete | ✅ complete |
| ✅ complete | ⚠️ partial | ⚠️ partial（不降级）|
| ✅ complete | ❌ failed | ❌ failed（不降级）|

**核心语义**：历史失败不会因一次成功而被抹除。文件级 status 反映"这道题你是否已经稳定掌握"，只要任何一场失败/部分，就要保留。

### B 模式：文件级 status 显式升级（用户兜底路径）

当连续多场（建议 ≥ 3 场）`my-answer-quality = complete` 后，**询问用户**：
"该题最近 3 场都是 ✅ complete，是否把文件级 status 从 <旧 status> 升级到 ✅？"

- 用户同意 → 修改 frontmatter `status` 为 `✅ complete`，并在文件正文末尾加一行注释 `> <YYYY-MM-DD>：用户确认掌握，status 由 <旧> 升级为 ✅`
- 用户拒绝 → 保持不变（默认行为）

**或者用户在执行 `/career interview` 时显式 override**："这道题我现在掌握了，把 status 改成 ✅" → 直接修改 status + 加注释。

铁律 #6（status 不自动降级）仍然成立——只是允许用户显式触发。

### 跨场次去重
- **同一个 topic 多场遇到 → 累积到同一个文件**，不创建新文件
- 题面文字略有差异（如不同公司措辞）→ 仍归并；可在 "## 题面" 段追加"（字节版：...）/（阿里版：...）"区分
- 模糊匹配阈值（Step 1 用）：
  1. 精确匹配（去掉空格/标点/大小写归一后比对）
  2. 包含匹配（新 topic 包含已有 topic 或反之）
  3. 相似度高（编辑距离 ≥ 80% 相似）
  4. 命中即询问用户"是否合并到 X？"——**不静默合并**

### interviews/aggregate.md
- 路径：`04_career/interviews/aggregate.md`
- frontmatter：
  - `type: career-interview-aggregate`
  - `created: YYYY-MM-DD`（**保留原值**，不重写）
  - `updated: YYYY-MM-DD`（每次重算更新为今天）
  - `question-count: N`（统计 `interviews/questions/*.md` 中符合 `type: career-interview-question` 的文件数）
- 正文三段（**顺序固定**）：
  1. `## 错题集 Top 10`
  2. `## 高频考点`
  3. `## 全部题目按 category 分组`

### 错题集 Top 10 排序公式
- 排序键：`times-asked × status_weight`
- 权重闭集：
  - `❌ failed` → 10
  - `⚠️ partial` → 3
  - `✅ complete` → 0
- 设计意图：让单次 ❌（键=10）优先于多次 ⚠️（如 3 次 ⚠️ 键=9），符合"完全失败的题应该最优先复习"直觉。

- 直觉对照（按排序键从高到低）：
  - ❌ × 1 = 10（最优先）
  - ❌ × 2 = 20（即使是 1 次错+1 次错也是优先级 1）
  - ⚠️ × 4 = 12
  - ⚠️ × 3 = 9（次于"❌ × 1"）
  - ⚠️ × 1 = 3（最低优先级中的 partial）
  - ✅ × N = 0（不进错题集）

- 平局规则：键相同 → 按 `last-seen` 倒序（最近遇到的优先）
- 状态为 ✅ 的题目排序键 = 0，不出现在错题集
- 取前 10；不足 10 条则全部列出

错题集条目格式：
```
- [[questions/<topic>.md]] · times-asked: N · status: ❌|⚠️ · last-seen: YYYY-MM-DD · category: <category>
```

### 高频考点判定
- `times-asked >= 2` 的题目都列入（与错题集独立——一道高频题可能已 ✅，也仍然列入高频）
- 按 `times-asked` 倒序，同分按 `last-seen` 倒序

高频考点条目格式：
```
- [[questions/<topic>.md]] · times-asked: N · status: <符号> · last-seen: YYYY-MM-DD
```

### growth-trajectory.md 追加格式
- 按 `## YYYY-MM` H2 月段组织，**月段倒序**（最新月在上）
- **月内条目按日期倒序**，最新事件在段落顶部
- 事件类型（闭集）：`interview question`
- 事件格式：
  ```
  - 2026-05-23 → interview question (字节-资深数据开发-一面) → [[04_career/interviews/questions/flink-反压机制.md]]
  ```
- 若月份段落不存在，新建 `## YYYY-MM` 段落，按月段倒序插入

### .manifest.json 更新规则
- **仅新建模式**（A 场景）才动 manifest：向 `interviews.questions` 数组 push 新文件名（**不含目录前缀**，如 `flink-反压机制.md`）
- 更新模式（B 场景）**不动 manifest**（文件已存在）
- 字段缺失 → 初始化为空数组后再 push

### skill 名匹配规则（错点反哺 skills-map / roadmap 时用）
复用 career-jd / career-roadmap 同一套：
1. **精确匹配**：去掉空格和标点后比对名称 — 命中即用
2. **包含匹配**：若错点 topic 作为子串包含在 skills-map 条目或 roadmap 项名中（如 `flink-反压机制` 命中 skills-map `Flink 框架（状态管理 / 容错 / 反压）`）— 算命中
3. **多重命中**：多个条目同时命中 → 取较高 level（与"多个众数取较高"规则一致）
4. **可疑匹配**：包含匹配可能误判（如 `java-gc` 命中 `JavaScript`）→ 输出时标"⚠️ 可能误匹配"，提醒人工核对
5. **完全无命中**：视为"新缺口"，提示 `/career roadmap`

## 输入
用户提供：
- **题面**（题目内容，原文/转述均可）
- **我的回答**（用户实际答的内容；用户没回答出来 → 写"未答出"）
- **场次信息**：date / company / position / round

**date/company/position/round 若用户没说 → 必须问，不能编**。新建模式与更新模式都一样。

## 场景分支总览

主分支（A 与 B 互斥，按 Step 1 模糊匹配结果选）：
- **A. 新建模式**（topic 在 `interviews/questions/` 不存在）：建文件 + frontmatter + 五段正文
- **B. 更新模式**（topic 已存在）：encountered 数组累加 + times-asked +1 + status 取最差档 + 增量更新差距点

子条件（C/D 正交于 A/B，可组合 A+C / A+D / B+C / B+D）：
- **C. 知识点已在 wiki**（`01_wiki/index.md` 含对应 concepts/entities 页）：`knowledge-point` 用 wikilink
- **D. 知识点未沉淀**：`knowledge-point` 填占位（`<topic>（待 /wiki ingest 沉淀）`）+ Step 5 提示用户考虑 `/wiki ingest`

## 执行步骤

### Step 1: 题面归类 + 模糊匹配
1. 读用户给的题面，提炼 topic（用知识点术语，**不照搬题目句子**）：
   - 好：`flink-反压机制` / `spark-shuffle-内存调优` / `transformer-attention-复杂度`
   - 差：`flink-面试题` / `今天的题1` / `字节问的反压`
2. 按 topic 命名规则规范化
3. 扫 `interviews/questions/`：
   - 读所有文件的 frontmatter `topic` 字段 + 文件名
   - 按"跨场次去重"模糊匹配规则比对
4. 命中处理：
   - **精确命中** → 直接走 B 更新模式
   - **包含/相似命中** → 询问用户"是否合并到 `<已有 topic>`？"
     - 用户确认 → 走 B 模式
     - 用户拒绝 → 走 A 模式（建新文件，topic 用用户给的新名）
   - **完全无命中** → 走 A 模式

### Step 2A: 新建模式

1. 抽取/确认元数据：
   - `category`（**闭集**，按题面判断；如"Flink 反压" → `数据工程`；"LangChain memory" → `AI 应用`；"系统设计 - 设计微博 feed" → `系统设计`）；超出闭集 → 问用户
   - `difficulty`（**闭集**，按题目深度判断；不确定 → 问用户）
   - `my-answer-quality`（**闭集**，根据用户描述的回答完整度判断；模糊 → 问用户）

2. 查 `01_wiki/index.md`，找是否有匹配 topic 的 concepts/entities 页：
   - 有 → 子场景 **C**：`knowledge-point: [[01_wiki/concepts/<page>]]`（实际路径以 index.md 为准）
   - 无 → 子场景 **D**：`knowledge-point: <topic>（待 /wiki ingest 沉淀）`

3. 拟"标准答案要点"：
   - 基于 wiki 已有知识（C 场景）+ 公认参考给要点
   - **wiki 没沉淀（D 场景）** → 在该段写"待补充（建议先 /wiki ingest）"或调用 wiki-query 找已有知识
   - **不编**——不知道的要点宁可写"待补充"也不臆造

4. 写"我的差距"：
   - 对比 "我的回答" vs "标准答案要点"
   - 列出**漏点**（标准要点里有但我没说的）和**错点**（我说错的）
   - 若 my-answer-quality = ✅ 且差距为空 → 写"无明显差距"

5. 拟"Next Actions"：
   - 缺什么知识点 → `[ ] 补 <知识点>`
   - 是否进 roadmap → `[ ] 考虑加入 roadmap.md（执行 /career roadmap）`
   - 是否沉淀 wiki → `[ ] /wiki ingest <topic>`

6. **写入 frontmatter 前给用户确认五段正文 + frontmatter 三个闭集字段**——避免抽错落盘。

7. 用户确认后写入 `04_career/interviews/questions/<topic>.md`：

```markdown
---
type: career-interview-question
topic: flink-反压机制
category: 数据工程
knowledge-point: [[01_wiki/concepts/flink-反压]]
difficulty: medium
status: ⚠️ partial
encountered:
  - date: 2026-05-23
    company: 字节
    position: 资深数据开发
    round: 一面
    my-answer-quality: partial
times-asked: 1
last-seen: 2026-05-23
---

## 题面
请详细讲讲 Flink 的反压机制。

## 我的回答
（用户原话，逐字粘贴）

## 标准答案要点
- TaskManager 之间的反压传导
- credit-based 流控（1.5+）
- 反压定位：metric / 日志 / Flame Graph

## 我的差距
- 没提 credit-based
- 不熟悉 Flame Graph 排查

## Next Actions
- [ ] 补 credit-based 原理
- [ ] [[01_wiki/concepts/flink-反压]] 沉淀更深
```

### Step 2B: 更新模式

1. 读已有文件
2. 在 frontmatter `encountered` 数组追加新场次：
   ```yaml
   - date: 2026-05-23
     company: 阿里
     position: P7
     round: 二面
     my-answer-quality: failed
   ```
3. `times-asked += 1`
4. `last-seen = max(原值, 新 date)`（一般就是新 date）
5. 文件级 `status` 按"文件级 status 升级规则"取最差档（**不降级**）。**特殊情况**：若 `times-asked >= 3` 且最近 3 场 `my-answer-quality` 全为 ✅ complete → 触发"B 模式：文件级 status 显式升级（用户兜底路径）"询问用户是否升级 status
6. 正文 "## 我的回答" 段：基于 frontmatter `times-asked` 判定迁移逻辑：

   - **若 times-asked == 1（旧文件是单场写法）**：
     把现有 `## 我的回答` 段内容改写为 `## 我的回答 · 第 1 场（<旧 encountered[0].date>）` + 追加新段 `## 我的回答 · 第 2 场（<新 date>）`
   - **若 times-asked >= 2（旧文件已是多场写法）**：
     直接追加 `## 我的回答 · 第 (times-asked + 1) 场（<新 date>）`，不动其它段

   **判定依据用 frontmatter 而非正文文本**——避免用户手编标题导致误判。

   注：这里的 `times-asked` 指**追加新场次之前**的旧值（即追加后 = 旧值 + 1）。
7. 正文 "## 我的差距" 段：合并策略：
   - 读取旧文件中已有的差距点列表
   - 抽取本场新发现的差距点
   - **列出新旧合并清单给用户确认**：
     ```
     旧差距（已记录）：
     - 没提 credit-based 流控
     - 不熟悉 Flame Graph 排查

     新发现：
     - 状态管理细节模糊
     - 反压源码版本差异不清

     合并后清单（请确认哪些保留 / 哪些合并 / 哪些移除）：
     1. ...
     2. ...
     ```
   - 用户确认后写入；**不静默判断同义漏点**——避免误合并或误重复
8. 正文 "## Next Actions" 段：若发现新缺口 → 追加新行（不勾旧的）
9. "## 标准答案要点" 段：不动（除非有新发现的要点要补，且与场次无关）
10. "## 题面" 段：若新场次题面与旧版本措辞不同 → 在段尾追加"（<新公司>版：<新措辞>）"

### Step 3: 重算 `interviews/aggregate.md`

读所有 `interviews/questions/*.md`（**全量重算，不增量**）：

1. 解析每个文件的 frontmatter：`topic` / `status` / `times-asked` / `last-seen` / `category`
2. **错题集 Top 10**：
   - 计算 `times-asked × status_weight`（权重 ❌=10, ⚠️=3, ✅=0）
   - 设计意图：让单次 ❌（键=10）优先于多次 ⚠️（如 3 次 ⚠️ 键=9），符合"完全失败的题应该最优先复习"直觉
   - 直觉对照：❌×1=10 / ❌×2=20 / ⚠️×4=12 / ⚠️×3=9 / ⚠️×1=3 / ✅×N=0
   - 过滤排序键 > 0 的题目（即剔除 ✅）
   - 按排序键倒序，同分按 `last-seen` 倒序（最近遇到的优先）
   - 取前 10
3. **高频考点**：所有 `times-asked >= 2` 的题目（含 ✅），按 `times-asked` 倒序 + `last-seen` 倒序
4. **按 category 分组**：所有题目按 category 字段分组列出（每组内按 last-seen 倒序）

覆盖式写入 `aggregate.md`：
- 保留 `created` 字段
- 更新 `updated` = 今天
- 更新 `question-count`

`question-count = 0` 的边界场景：写"暂无面试题记录"提示文案，不产出三段。

### Step 4: 错点反哺 roadmap / skills-map

**只读不写**——仅输出提示给用户，**不修改 skills-map / roadmap 文件**。

按 skill 名匹配规则对照本次记录的 topic：

- **该错点对应的知识点已在 `roadmap.md`** → 输出：
  ```
  🔄 错点 <topic> 已在 roadmap（优先级 <Px>）→ 本次再次验证该缺口
  ```
- **该错点暴露 roadmap 没列的新缺口** → 输出：
  ```
  🆕 错点 <topic> 暴露 roadmap 未列的新缺口
  建议执行 /career roadmap 更新学习路线
  ```
- **该错点对应的技能在 `skills-map.md` 中 level 标得过高**（如标 senior 但 my-answer-quality=failed） → 输出：
  ```
  ⚠️ 错点 <topic> 在 skills-map 标 <level>，但本次表现 <my-answer-quality>
  建议在下次 /career review 时调整 skills-map（**本 skill 不自动改**）
  ```
- **可疑匹配** → 标"⚠️ 可能误匹配"提示人工核对

A 场景（✅ complete + 新建）：无错点，跳过 Step 4。

### Step 5: 提示 wiki ingest（D 子场景）

若 Step 2 落到子场景 D（`knowledge-point` 用占位） → 输出：

```
💡 知识点 <topic> 未沉淀。考虑执行 /wiki ingest 把它收录进 01_wiki/concepts/。
```

**只提示，不自动调用 wiki-ingest skill**。

C 子场景：跳过 Step 5。

### Step 6: 追加 growth-trajectory

向 `04_career/growth-trajectory.md` 对应 `## YYYY-MM` 月段顶部追加一行：

```
- 2026-05-23 → interview question (字节-资深数据开发-一面) → [[04_career/interviews/questions/flink-反压机制.md]]
```

若月份段落不存在，新建 `## YYYY-MM` 段落，按月段倒序（新月在上）插入。

A / B 模式都追加（每次遇到题目都是一个事件）。

### Step 7: 更新 .manifest.json

- **A 新建模式**：向 `interviews.questions` 数组 push 新文件名（**不含目录前缀**，如 `flink-反压机制.md`）；字段缺失先初始化为空数组
- **B 更新模式**：**不动 manifest**（文件已存在）

### Step 8: Commit（按场景分支）

含中文/括号/空格的路径**必须用双引号包裹**。

**A 新建模式**：
```bash
git add "04_career/interviews/questions/<topic>.md" "04_career/interviews/aggregate.md" "04_career/growth-trajectory.md" "04_career/.manifest.json"
git commit -m "feat(career): interview question <topic> (encounter <公司>-<轮次>)"
```

**B 更新模式**：
```bash
git add "04_career/interviews/questions/<topic>.md" "04_career/interviews/aggregate.md" "04_career/growth-trajectory.md"
git commit -m "chore(career): interview question <topic> +encounter (now times-asked=<N>)"
```

`<N>` 是更新后的 times-asked 值。

### Step 9: 输出确认（按场景分支）

**A 新建模式**：
```
✅ 已新建面试题：04_career/interviews/questions/<topic>.md
   场次：<公司>-<岗位>-<轮次>（<date>）· difficulty: <level> · my-answer-quality: <符号>
   knowledge-point: <wikilink | 待沉淀>
📊 aggregate.md 已重算（question-count: N）
📈 growth-trajectory 已追加 1 条事件
<错点反哺提示，若有>
<wiki ingest 提示，若 D 场景>
```

**B 更新模式**：
```
🔄 已更新面试题：04_career/interviews/questions/<topic>.md
   新场次：<公司>-<岗位>-<轮次>（<date>）· my-answer-quality: <符号>
   times-asked: <N> · 文件级 status: <符号>（<升级 | 不变>）
📊 aggregate.md 已重算（question-count: N）
📈 growth-trajectory 已追加 1 条事件
<错点反哺提示，若有>
```

## 铁律
- **标准答案要点未知 → 写"待补充"或 wiki-query 找**——不编造，不照搬题目句子
- **掌握度只标三档（✅ complete / ⚠️ partial / ❌ failed）**——不打分（"7/10"之类禁止）
- **不替你写"我应该怎么答得更好"的范文**——只指出漏点，不重写答案
- **跨场次同题去重**——归并到一个文件，多场记录到 `encountered` 数组；不创建重复文件
- **不自动调用 /career roadmap 或 /wiki ingest 或修改 skills-map**——只提示，所有跨 skill 联动由用户触发
- **新建模式必须问场次信息**——date/company/position/round 不能编
- **抽取后必须让用户确认 frontmatter + 五段正文再落盘**——闭集字段（category/difficulty/my-answer-quality）可能误判
- **文件级 status 不降级**——历史失败不会因一次成功而抹除（见"文件级 status 升级规则"表）
