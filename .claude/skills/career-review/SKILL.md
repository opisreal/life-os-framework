---
name: career-review
description: 周/月/季周期复盘。当用户说"周复盘""月度复盘""季度复盘""本周/本月总结"或输入 /career review week|month|quarter 时使用。聚合 log+feedback+jd+interview 素材，生成诊断报告+教练评述，更新 skills-map 和 growth-trajectory。
---

# Career Review

## 前置读取
1. `04_career/.manifest.json`
2. `04_career/skills-map.md`（用于更新 level/evidence/last-used）
3. `04_career/jd/aggregate.md`（对照 JD 差距）
4. `04_career/reviews/<period>/` 上期复盘文件（用于"上期 Next Actions 完成情况"段；首次复盘则跳过）
5. `04_career/growth-trajectory.md`

## 数据契约（来自 04_career 模块设计文档 §2.2、§3.3）

### review 文件
- 路径（按 period 分目录）：
  - `week`   → `04_career/reviews/weekly/YYYY-W{N}-review.md`（ISO 周编号，如 `2026-W21-review.md`）
  - `month`  → `04_career/reviews/monthly/YYYY-MM-review.md`（如 `2026-05-review.md`）
  - `quarter` → `04_career/reviews/quarterly/YYYY-Q{N}-review.md`（公历季度，如 `2026-Q2-review.md`）
- frontmatter 字段（YAML）：
  - `type: career-review`
  - `period: <2026-W21 | 2026-05 | 2026-Q2>`（**闭集**：周用 `YYYY-W{N}`、月用 `YYYY-MM`、季用 `YYYY-Q{N}`）
  - `window-start: YYYY-MM-DD`（窗口起始日，含）
  - `window-end: YYYY-MM-DD`（窗口结束日，含）
  - `created: YYYY-MM-DD`（生成日，即今天）
- 正文九段（**顺序固定，标题不变**）：
  1. 一、本期摘要
  2. 二、亮点（与目标 JD 对齐的进展）
  3. 三、缺口与风险
  4. 四、反馈消化情况
  5. 五、能力地图变化
  6. 六、vs 目标 JD 差距（aggregate 对照）
  7. 七、下期 Next Actions
  8. 八、教练评述
  9. 九、上期 Next Actions 完成情况

### period 字段闭集
- `week` / `month` / `quarter` —— 三选一，超出 → 询问用户归并到哪一档（不静默猜）。
- 用户没说周期 → **默认 weekly + 询问确认**。

### 状态符号闭集
- ✅ 达标 / 已完成 / 在轨
- ⚠️ 有缺口 / 部分完成 / 偏离
- ❌ 完全缺失 / 未完成 / 严重风险

### level 排序
- `none < junior < mid < senior < staff`
- 用于 skills-map 升降判断、vs JD 差距状态判定（与 career-jd 一致）。

### skill 名匹配规则（review 内 skills-map 更新 → 现有条目；vs JD 段 → skills-map 条目）
复用 career-jd 同一套：
1. **精确匹配**：去掉空格和标点后比对 skill 名 — 命中即用
2. **包含匹配**：若 skill 作为子串包含在 skills-map 条目名中（如 `Flink` 命中 `Flink 框架（状态管理 / 容错 / 反压）`）— 算命中
3. **多重命中**：多个 skills-map 条目同时被命中 → 取**较高 level**（与"多个众数取较高"规则一致）
4. **可疑匹配**：包含匹配命中但可能误判（如 `Java` 命中 `JavaScript`）→ 在变更清单里标"⚠️ 可能误匹配"，提醒用户人工核对
5. **完全无命中**：在 skills-map 中视为不存在 → 走"新增"路径

### skills-map 更新规则
- 条目格式（与现状一致）：
  ```
  - **<技能名>** — level: <level> · evidence: [[<相对路径>]] · last-used: YYYY-MM
  ```
- **level 上升**：修改 `level` 字段 + `evidence` 追加新链接（保留旧链接，用 `, ` 分隔，最多保留最近 3 条）+ `last-used` 更新为本期月份
- **长期未用（stale）**：在 `evidence` 字段后追加 ` [stale]` 标记（**不删除条目**，不动 level）
- **新涌现**：添加到对应分类章节末尾；若现有章节均不适合 → 询问用户分类（不静默丢到"软实力"或"待补充评估"）
- **降级**：本 skill 不主动降级（level 只升不降）；若用户明确说"我这块退步了" → 询问确认后修改

### growth-trajectory.md 追加格式
- 按 `## YYYY-MM` H2 月段组织，**月段倒序**（最新月在上）
- **月内条目按日期倒序**，最新事件在段落顶部
- 事件类型：`review week` / `review month` / `review quarter`（**闭集**）
- 事件格式：
  ```
  - YYYY-MM-DD → review <week|month|quarter> <period> → [[相对路径]]
  ```
  示例：
  ```
  - 2026-05-23 → review week 2026-W21 → [[04_career/reviews/weekly/2026-W21-review.md]]
  ```

### .manifest.json 更新规则
- `reviews.<period>` 数组（`reviews.weekly` / `reviews.monthly` / `reviews.quarterly`）→ push 本次 period 标识：
  - 周：`"2026-W21"`
  - 月：`"2026-05"`
  - 季：`"2026-Q2"`
- `cron.<period>-reminder.last-run` → 更新为本次执行时间戳（即使是手动触发也算一次复盘，避免短期内重复提醒）
- `cron.<period>-reminder.skip-count` → 若本次完成了对应周期复盘且原值 > 0 → **重置为 0**
- `last-run` 字段格式：**ISO8601 带时区**，如 `"2026-05-23T10:30:00+08:00"`（与 career-log / career-jd 保持一致）

## 输入
用户参数：`week` / `month` / `quarter`，或自然语言识别（"周复盘"="week"，"月度复盘"="month"，"季度复盘"="quarter"）。

如果用户没说周期，**默认是 weekly + 询问确认**。

## 执行步骤

### Step 0: 重复检测（前置）

若目标 review 文件已存在（如 `04_career/reviews/weekly/2026-W21-review.md` 已在），询问用户：

1. **覆盖**（推荐）：删除旧文件 + git history 保留旧版本 + 重新生成；manifest 数组不重复 push，growth-trajectory 不追加新事件标记（旧的保留）
2. **取消**：不动任何文件，直接退出（用户可能只是想读上次结果）
3. **新版本**：命名为 `<period>-review-v2.md`（v3、v4 类推）；manifest 数组 push 新文件标识 `2026-W21-v2`；growth-trajectory 追加 review v2 事件

默认推荐选项 1。

### Step 1: 计算时间窗
- `week`：上一个完整 ISO 周（如今天是 W22 周一，则窗口 = W21 = 上周一到周日）
- `month`：上一个完整月（如今天是 2026-06-01，则窗口 = 2026-05-01 到 2026-05-31）
- `quarter`：上一个完整季度（按公历季度：Q1=1-3 月，Q2=4-6 月，Q3=7-9 月，Q4=10-12 月）

输出窗口给用户确认（如 "本次复盘窗口：2026-05-11 ~ 2026-05-17 (W21)，对吗？"）。用户可以指定其他窗口（比如复盘当前进行中的本周，则窗口取本周一 ~ 今天）。

### Step 2: 聚合素材
按时间窗筛选：
- **log 条目**：读对应周/月份的 `04_career/log/YYYY/YYYY-W{N}.md` 文件（month/quarter 复盘需要读多个周文件），按 `## YYYY-MM-DD` H2 段在窗口内的所有条目
- **feedback**：读 `04_career/feedback/YYYY-Q{N}/` 目录下 frontmatter `date` 在窗口内的文件
- **JD 变化**：读 `04_career/jd/active/` 和 `04_career/jd/archive/`，筛选 frontmatter `captured` 在窗口内、或窗口内 status 有变化的（status 变化通过 growth-trajectory 的 jd 事件标记反推）
- **面试题**：读 `04_career/interviews/questions/` 在窗口内有新 encountered 条目的题目
- **上期 Next Actions**：读上一期 review 文件的"七、下期 Next Actions"段（按 period 类型匹配上期：week→上一周 review、month→上一月 review、quarter→上一季 review；若文件不存在 → 进入**首次复盘场景**）

### Step 3: 判断场景（在生成报告前必须分支）

**素材稀薄判定阈值**（log 条目 + feedback 数量之和）：
- `week`：< 3 → 稀薄
- `month`：< 10 → 稀薄
- `quarter`：< 30 → 稀薄

**三种场景：**

#### 场景 A：完整场景（素材充足）
按九段结构完整生成报告。继续 Step 4。

#### 场景 B：素材稀薄场景
**不强行编报告**。输出诊断信息：

```
⚠️ 本期素材稀薄，建议不出复盘：
- log 条目：N 条（阈值 X）
- feedback：M 条
- JD 变化：K 条
- 面试题：J 条

可能原因：
- 本周/月节奏较慢
- 忘了用 /career log 记录

可选操作：
1. 补录素材后重跑（推荐——回忆窗口内做了什么，先 /career log 记录，再 /career review）
2. 仍生成简化报告（仅含已有素材，跳过空段，标记"本期素材稀薄"）
3. 跳过本期，只重置 cron skip-count（保持节奏感不打断）

请选择：
```

- 选 1 → 退出，等用户补录后重跑
- 选 2 → 走简化版九段（空段标"本期无数据"，第八段教练评述聚焦"为什么这周/月这么静"），走 Step 4-7（A 场景流程）
- 选 3 → **跳过 Step 3 报告生成 + Step 4 skills-map 更新 + Step 5 growth-trajectory 追加**，只执行 Step 7 manifest 更新（last-run + skip-count 重置），进入 Step 8 的 B 场景 commit

#### 场景 C：首次复盘场景
`04_career/reviews/<period>/` 目录为空（或对应上期文件不存在）：
- 按九段结构生成，**但第九段填**：
  ```
  ## 九、上期 Next Actions 完成情况
  首次复盘，无上期对照。
  ```
- 第七段 Next Actions 不再标"延后自上期"
- 教练评述（第八段）可以补一句"这是首次复盘，建立基线"
- 继续 Step 4

### Step 4: 生成报告（A / C 场景）
按下面九段模板生成，写入对应路径：

```markdown
---
type: career-review
period: 2026-W21         # 或 2026-05 / 2026-Q2
window-start: 2026-05-11
window-end: 2026-05-17
created: 2026-05-23
---

# 周复盘 · 2026-W21

## 一、本期摘要
（3-5 句话总结：你做了什么、状态如何、关键变化。基于真实事件，不套模板。）

## 二、亮点（与目标 JD 对齐的进展）
- ✨ <事件描述>（对应 jd/aggregate.md 哪个技能；引用 [[log/...]] 或 [[feedback/...]]）
- ✨ ...

## 三、缺口与风险
- ⚠️ <识别本期暴露但未补的缺口>
- ⚠️ ...

## 四、反馈消化情况
（窗口内的每条 feedback：原话要点 / 你的解读 / Action Items 进展）
- [[feedback/2026-Q2/2026-05-15-leader-季度1on1.md]] — 状态：已消化 / 部分消化 / 延后到下期
- [[...]] — ...

## 五、能力地图变化
- ↑ Claude SDK: mid → senior（证据：[[log/2026/2026-W21.md]]）
- ↓ Flink: 已 3 周未实操，标记 stale
- + 新增："Agent 架构设计"

## 六、vs 目标 JD 差距（aggregate 对照）
| 技能 | coverage | 你的 level | 状态 |
|---|---|---|---|
| Flink | 8/8 | senior | ✅ |
| Agent 架构 | 6/8 | senior | ✅ |
| 多模态 | 4/8 | none | ❌ |

## 七、下期 Next Actions
- [ ] 学 X（指向 [[03_study/...]]）
- [ ] 做 Y
- [ ] 补简历 Z 段落

## 八、教练评述
（200-400 字开放评述。职业教练视角，针对窗口内的真实事件评论，必须有实质内容。
 不能套模板"继续加油"。可以指出节奏问题、状态问题、战略选择问题。）

## 九、上期 Next Actions 完成情况
- [x] <原 Action 描述> ✅
- [ ] <原 Action 描述> ❌ 原因：<具体原因>
- [-] <原 Action 描述> → 延后到本期（已写入本期第七段）
```

**反馈消化标注规则**（第四段）：
- 已消化：Action Items 全部完成或显式不再跟进
- 部分消化：Action Items 部分完成
- 延后到下期：未动 → **必须在第七段显式重述该 Action**，不静默忽略

### Step 5: 副作用 - 更新 skills-map.md
基于窗口内的 log 和 feedback，识别三类变化：
1. **level 上升**：窗口内反复实操或被认可的技能 → 升档
2. **stale**：超过阈值未实操（建议：未用 ≥ 4 周）→ 追加 `[stale]` 标记
3. **新涌现**：log 标签出现但 skills-map 不在的技能（按 skill 名匹配规则判断是否新增）

**变更清单格式（必须输出给用户确认）**：

```
📋 skills-map 拟更新（请确认）：
↑ <技能> : <旧 level> → <新 level>（证据：[[log/2026/2026-W21.md]]）
↑ <技能> : mid → senior（证据：[[feedback/...]]）⚠️ 可能误匹配（命中条目：<现有条目名>）
↓ <技能> : 标记 [stale]（原因：N 周未实操）
+ <技能> : 新增到 "<分类章节>"（level: <初始 level>，证据：[[log/...]]）
(不删除条目，仅 stale 标记)

确认？(yes / 调整哪一项 / 全部取消)
```

- 用户回 `yes` → 落盘所有变更
- 用户指定调整某项 → 局部修订后再问一次
- 用户 `全部取消` → 跳过 skills-map 写入（仍继续 Step 6-8，只是 commit 不含 skills-map）

**关键：用户全部取消 skills-map 变更时**

skills-map.md 保持不变，但报告里的"第五段：能力地图变化"必须**回写**为：

```
## 五、能力地图变化（已审阅，未入库）

> 本期识别出以下能力变化迹象，但用户审阅后选择**暂不更新 skills-map.md**，仅作记录：
>
> - ↑ Claude SDK: mid → senior（候选证据：[[log/...]]）
> - ↓ Flink: 候选 stale 标记
> - + 新增："Agent 架构设计"
>
> 下次复盘时请重新评估是否落盘。
```

避免报告叙述与 skills-map 事实脱钩。

### Step 6: 副作用 - 追加 growth-trajectory.md
向对应 `## YYYY-MM` 月段顶部追加一行（**月段倒序，月内条目按日期倒序**）：

```
- 2026-05-23 → review week 2026-W21 → [[04_career/reviews/weekly/2026-W21-review.md]]
```

如果月份段落不存在，新建 `## YYYY-MM` 段落，按月段倒序（新月在上）插入。

若本期 period 已有 review 事件行 → 不重复追加（避免时间线噪声）；除非是 Step 0 选项 3 的 v2 版本。

### Step 7: 副作用 - 提示后续动作
基于本期产出，输出**建议**（不自动调用）：
- 若第七段 Next Actions 含明确学习项（关联 `[[03_study/...]]`） → 提示：
  ```
  💡 检测到 N 条学习 Action，建议执行 /career roadmap 更新学习路线。
  ```
- 若本期识别有重大项目里程碑（log 中 `[work]` 标签 + 强项词收紧表："上线 / 主导 / 立项 / 拍板 / 交付 / 发版"（**去掉"完成"以避免日常用语误报**）；并要求**强项词 + 时长/范围/影响范围**双条件（如"主导 X 项目交付"而非裸"完成"）） → 提示：
  ```
  💡 本期有重大里程碑（<事件简述>），考虑更新简历 <段落名> 段落。
  ```
- 若第六段 vs JD 差距出现新 ❌ → 提示：
  ```
  💡 本期暴露新缺口（<技能>），考虑执行 /career roadmap 调整 P0。
  ```
- **只提示，不自动调用**。

### Step 8: 更新 .manifest.json
1. 向 `reviews.<period>` 数组 push 本次 period 标识：
   - 周：`"2026-W21"`
   - 月：`"2026-05"`
   - 季：`"2026-Q2"`
2. 更新 `cron.<period>-reminder.last-run` 为今天时间戳（ISO8601，如 `"2026-05-23T10:30:00+08:00"`）。
3. 若 `cron.<period>-reminder.skip-count > 0` → 重置为 `0`。

若 `reviews.<period>` 数组已含本次 period 标识 → 不重复 push（避免数组膨胀）；若是 Step 0 选项 3 的 v2 版本 → push `<period>-v2` 等子标识。

**B 场景特例**：不 push reviews 数组（因未生成报告），但仍更新 `last-run` 与重置 `skip-count`（用户主动跳过本期，避免下次再提醒；同时记录此次决策）。

### Step 9: Commit

**含中文/括号/空格的路径用双引号包裹**。按场景分支：

**A / C 场景（完整生成或首次复盘）**：
```
git add "04_career/reviews/<period>/<file>" "04_career/skills-map.md" "04_career/growth-trajectory.md" "04_career/.manifest.json"
git commit -m "chore(career): review <period>"
```

示例：
```
git add "04_career/reviews/weekly/2026-W21-review.md" "04_career/skills-map.md" "04_career/growth-trajectory.md" "04_career/.manifest.json"
git commit -m "chore(career): review 2026-W21"
```

若用户在 Step 5 选了"全部取消" → 不 add skills-map：
```
git add "04_career/reviews/<period>/<file>" "04_career/growth-trajectory.md" "04_career/.manifest.json"
git commit -m "chore(career): review <period> (skills-map unchanged)"
```

**B 场景（素材稀薄，未生成报告但需重置 skip-count）**：
```
git add "04_career/.manifest.json"
git commit -m "chore(career): mark <period> period as too sparse to review"
```

示例：
```
git add "04_career/.manifest.json"
git commit -m "chore(career): mark 2026-W21 period as too sparse to review"
```

### Step 10: 输出确认

**A / C 场景**：
```
✅ 已生成复盘：<相对路径>
📊 skills-map：N 处变更已落盘 / 跳过
📈 growth-trajectory：已追加 1 条事件标记
🗂  manifest：reviews.<period> +1，cron last-run 已更新，skip-count 已重置
💡 后续建议：（Step 7 提示原文）
```

**B 场景**：
```
⚠️ 本期未生成复盘（素材稀薄，用户选择跳过）
🗂  manifest：cron last-run 已更新，skip-count 已重置（避免重复提醒）
建议：在窗口结束前用 /career log 补录关键事件，下期复盘前可重新评估。
```

## 铁律
- **不打分到具体数字**——用 ✅/⚠️/❌ 三档（包括反馈消化、vs JD 差距、上期 Action 完成度）
- **教练评述必须有实质内容**——基于真实事件评论，不套模板；空洞如"继续加油""保持节奏"算违规
- **未消化的反馈必须显式标记"延后到下期"**——并在第七段重述该 Action，不静默忽略
- **不自动调用 /career roadmap**——只在 Step 7 提示，由用户决定
- **更新 skills-map 前列出变更清单让用户确认**——skills-map 是关键文件，不静默改
- **用户取消 skills-map 变更 → 报告第五段必须标"已审阅，未入库"**——避免叙述与事实脱钩
- **窗口内没有素材 → 输出"本期素材稀薄"，不强行编报告**（场景 B 分支）
- **上期 review 不存在（首次复盘）→ 第九段填"首次复盘，无上期对照"**（场景 C 分支）
