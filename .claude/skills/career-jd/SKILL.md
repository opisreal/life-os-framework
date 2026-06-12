---
name: career-jd
description: 录入目标岗位 JD 并抽取技能要求。当用户说"新 JD""分析这个 JD""目标岗位"或输入 /career jd 时使用。支持粘贴原文，也支持直接给 BOSS 直聘（zhipin.com）链接自动提取。归档到 04_career/jd/active/，抽取硬技能+软技能，自动重算 jd/aggregate.md 聚合画像。
---

# Career JD

## 前置读取
1. `04_career/.manifest.json`（确认/初始化 `jd.active` 与 `jd.archive` 数组）
2. `04_career/jd/aggregate.md`（聚合视图当前内容，保留 `created` 字段）
3. `04_career/skills-map.md`（用于对照标 ✅/⚠️/❌）
4. `04_career/jd/active/` 与 `04_career/jd/archive/` 现有文件列表（去重）

## 数据契约（来自 04_career 模块设计文档 §2.2）

### JD 单文件
- 路径：`04_career/jd/active/YYYY-MM-DD-{company}-{title}.md`（status=active 时）或 `04_career/jd/archive/...md`（status=archived 时）
- frontmatter 字段（YAML）：
  - `type: career-jd`
  - `company: <公司名>`
  - `title: <岗位名>`
  - `seniority: junior | mid | senior | staff`（**闭集**，超出 → 问用户确认）
  - `location: <地点>`
  - `status: active | archived | applied | rejected`（**闭集**）
  - `captured: YYYY-MM-DD`
  - `source: <来源平台，如 拉勾/Boss/官网/内推>`
- 正文四段：`## 原文` + `## 抽取的技能要求` + `## 软性要求` + `## 备注`

### 抽取技能字段
- `skill: <通用术语>`（**用通用术语，不要照搬 JD 措辞**，便于聚合）
- `required-level: junior | mid | senior | staff`（**闭集**，按 JD 上下文判断）
- `in-jd-weight: 1 | 2 | 3`（**闭集**：1=普通；2=重点/加粗/反复出现；3=核心必备/必须/熟练掌握）

抽取条目格式（一行）：
```
- skill: <名称>, required-level: <level>, in-jd-weight: <1|2|3>
```

**`required-level` 与 `seniority` 相互独立**：单项技能要求可高于或低于岗位整体定位（如 senior 岗对某核心技能要求 staff 级深度；mid 岗里有个 senior 级的核心技能要求）。按 JD 措辞判断即可，不要硬压到 seniority。

### jd/aggregate.md
- 路径：`04_career/jd/aggregate.md`
- frontmatter：
  - `type: career-jd-aggregate`
  - `created: YYYY-MM-DD`（**保留原值**，不要每次重写）
  - `updated: YYYY-MM-DD`（每次重算更新）
  - `active-count: N`（统计 `jd/active/` 下符合 `type: career-jd` 的 JD 文件数量）
- 正文三段：
  - `## 高频要求（coverage ≥ 60%）`
  - `## 中频要求（coverage 30%-60%）`
  - `## 低频但高权重（coverage < 30% 但 in-jd-weight=3）`
- 每个技能条目格式：
  ```
  - {skill} ({n}/{total}) · 平均 required-level: {level} · 你的 level: {level} ✅|⚠️|❌
  ```

### 状态判定逻辑
- level 排序：`none < junior < mid < senior < staff`
- 你的 level（来自 `skills-map.md`，未列出按 `none`）≥ 平均 required-level → ✅
- 低 1 档 → ⚠️
- 低 ≥ 2 档 或 `none` → ❌

**skill 名匹配（JD 抽取 skill → skills-map 条目）**：

按以下顺序依次尝试，命中即停。

1. **精确匹配**：去掉空格和标点后两边完全相同 → 命中
2. **字面包含（双向）**：JD skill 作子串包含在 skills-map 条目名中，**或**反过来 skills-map 条目名作子串包含在 JD skill 中 → 命中
   - 正向例：JD `Flink` ⊆ skills-map `Flink 框架（状态管理 / 容错 / 反压）` → 命中
   - 反向例：JD `Hadoop 生态` ⊇ skills-map `Hadoop 系统架构（HDFS / NameNode HA / MapReduce / Yarn）` 中的 `Hadoop`？反向匹配要求 skills-map 条目名**作为整体**是 JD skill 子串——这里 skills-map 条目整体不是 JD `Hadoop 生态` 子串，所以正向反向都不命中，继续走第 3 步
3. **语义等价（你来判断，不依赖字面）**：字面规则不命中时，判断 JD skill 与 skills-map 某条是否指向**同一概念**：
   - ✅ 同一技术 / 同一框架家族的不同表述：`大模型应用` ↔ `LLM 应用开发全链路`、`AI Agent` ↔ `Claude SDK / Agent 框架开发` / `Supervisor 编排模式` / `多 Skill 协同的 Agent 架构设计`
   - ✅ 同一方法论 / 软技能的不同措辞：`跨团队推动` ↔ `跨团队协作`、`数据治理` ↔ `数据全生命周期治理`、`端到端项目闭环` ↔ `独立负责复杂项目` + `研发流程设计`
   - ✅ 同一概念的修饰差异：`数据仓库建模` ↔ `数据仓库维度建模`、`Hadoop 生态` ↔ `Hadoop 系统架构`
   - ❌ 不要跨抽象层级：`SQL` ≠ `Spark SQL`（Spark SQL 是 SQL 的具体实现之一，可走第 2 步反向包含；但 `数据建模` ≠ `用户触达归因建模`，前者是顶层方法论，后者是具体业务领域）
   - ❌ 不要跨领域：`Java` ≠ `JavaScript`、`数据建模` ≠ `网络建模`
   - ❌ 不要拿"我有相关经验"当等价：`SQL` ≠ `数据仓库建模`（虽然建模常用 SQL，但概念不同）
4. **多重命中取较高**：第 2、3 步命中多条 skills-map 条目时 → 取**较高 level**（与"多个众数取较高"规则一致）
5. **标注分级（写入 aggregate.md 时附注）**：
   - 字面命中（1、2 步）→ 无标注
   - 语义命中（3 步）→ 标 `🔗 语义匹配（命中：<skills-map 条目名>）`，提示用户可考虑给 skills-map 加 alias 或重命名让下次直接字面命中
   - 字面包含但跨抽象层级 / 可能误判（如 `Java` 命中 `JavaScript`、`SQL` 命中 `MySQL`）→ 标 `⚠️ 可能误匹配（命中：<条目名>）`，提醒用户人工核对
6. **完全无命中** → `none`

### 文件命名转义规则
- `{company}` / `{title}` 保留中文与拉丁字符
- 去除路径不安全字符（`/`、`:`、`?`、`#`、`\`、`*`、`<`、`>`、`|`、`"`）
- 空格 → 短横线 `-`
- 不要做大小写归一化（保留 JD 原写法）
- 示例：
  - `字节` → `字节`
  - `资深数据开发工程师` → `资深数据开发工程师`
  - `Senior Data Engineer (Tokyo)` → `Senior-Data-Engineer-(Tokyo)`（括号合法但若 shell 命令行涉及，路径必须用双引号包裹）

### .manifest.json 更新
- `jd.active` 数组：
  - 新增 JD（status=active）→ push 文件名（不含目录前缀，如 `2026-05-22-字节-资深数据开发.md`）
  - JD archive → 从此数组 remove
- `jd.archive` 数组：
  - archive 时 push 文件名（不含目录前缀）
  - 移回 active 时 remove
- status 改为 `applied` / `rejected` 但文件仍在 `active/` → manifest **不动**（只动 frontmatter，aggregate 仍包含该文件）

### growth-trajectory.md 追加
- 按 `## YYYY-MM` H2 月段组织，**月段倒序**（最新月在上）
- **月内条目按日期倒序**，最新事件在段落顶部
- 同日多条事件保留插入顺序（即最后追加的在最上面）
- 事件格式：
  - 新增 JD：`- YYYY-MM-DD → jd added → [[相对路径]]`
  - archive：`- YYYY-MM-DD → jd archived → [[原相对路径]]`
  - status applied/rejected：`- YYYY-MM-DD → jd {applied|rejected} → [[相对路径]]`

## 输入
用户提供以下任一形式：
- **JD 原文**（粘贴文本）→ 直接进入 Step 1
- **支持的链接**（详见下方白名单）→ 进入 Step 0 自动抓取
- **不在白名单的链接** → 询问用户粘贴 JD 原文，**不要自己访问**（防止幻觉/越权抓取）

### 链接白名单（已验证可抓取的平台）
| 平台 | URL 模式 | 默认 source 字段 |
|------|---------|-----------------|
| BOSS 直聘 | `zhipin.com/job_detail/...` | `Boss直聘` |

新增平台时：先用 web-access skill 验证可抓取且字段稳定，再补到此表 + 在 Step 0 加对应解析逻辑。

## 执行步骤

### Step 0: 链接预处理（仅当输入是白名单链接时）

1. **调用 web-access skill** 通过 CDP 打开链接（BOSS 直聘需要登录态，CDP 模式天然携带）。
2. 用 `/eval` 提取关键字段。BOSS 直聘选择器（**已验证 2026-05-23**）：
   - `jobName`：`.name h1`（岗位名）
   - `salary`：`.name .salary`（薪资）
   - `jobTags`：`.job-primary .info-primary p`（"上海 5-10年 本科" 单串文本，需拆分到 location/experience/education）
   - `companyName`：通过 `.boss-info-attr` 或页面 mainText 中"招聘"前缀文本提取
   - `jobDescription`：`.job-sec-text`（**核心**：职责 + 任职要求一段）
   - `address`：`.location-address`（详细工作地址）
3. **抓取失败的回退**：选择器变更 / 页面结构异常 / 内容空 → 不要硬撑，向用户报错并要求粘贴 JD 原文，同时更新本文件的选择器（追加新发现日期）。
4. **关闭 CDP tab** 后再进入 Step 1。
5. 抓取到的 `jobDescription` 整段当作 "JD 原文"，company/title/location 等元数据直接预填 Step 1 的字段，`source` 字段按白名单表填写。
6. **抓取到原文后必须输出给用户预览一次**（折叠展示前 30 行 + 后续元数据预填值），等用户说继续或修正后再进入 Step 1。这步是替代"用户粘贴原文"的人工 sanity check。

### Step 1: 提取元数据
从 JD 原文识别：
- `company`（公司名）
- `title`（岗位名）
- `seniority`（**闭集**：junior / mid / senior / staff，按 JD 描述判断；如"P7"/"高级"→ senior，"专家/架构师"→ staff，"应届/初级"→ junior）
- `location`（地点）
- `source`（来源平台，问用户）

任何一项 JD 原文没明说 → **问用户**，不要编。`seniority` 超出闭集 → 询问归并到哪一档（不静默猜）。

### Step 2: 文件命名与去重
按"文件命名转义规则"生成路径：
```
04_career/jd/active/{captured}-{company}-{title}.md
```

去重逻辑（**先扫 active/，再扫 archive/**）：
- `jd/active/` 已有同 company + 同 title 文件 → 询问用户：
  - 1) 覆盖更新原文件（保留 frontmatter `captured`，更新其他）
  - 2) 创建新版本（路径追加 `-v2` 后缀，如 `2026-05-22-字节-资深数据开发-v2.md`）
  - 3) 取消
- `jd/archive/` 有同名 → 询问用户是否移回 active（移回时同时更新 manifest 的两个数组）
- 同日同公司同岗位（罕见） → 同样按上述询问

**不静默覆盖**。

### Step 3: 技能抽取（**先输出列表给用户确认，不直接落盘**）
- **硬技能**：技术栈（语言/框架/工具）、领域知识、平台经验
- **软技能**：leadership、跨团队、沟通、推动落地、业务理解
- 每项三个闭集字段（见数据契约）
- 抽取规则：
  - `skill` 用通用术语（"实时数仓"而非"基于 Flink+Kafka 的实时数据仓库建设"），便于聚合
  - `required-level` 按 JD 措辞映射：
    - "了解 / 熟悉" ≈ junior~mid
    - "熟练掌握 / 精通" ≈ mid~senior
    - "深入理解 / source-code 级" ≈ senior
    - "主导 / 架构 / 制定标准" ≈ staff
  - `in-jd-weight` 按强调程度：
    - 1：普通要求
    - 2：JD 反复提到 / 加粗 / 放在"要求"段靠前
    - 3：含"必须""熟练掌握""核心""资深方向"等强词

**抽取后输出技能列表给用户**，等用户调整 / 补充 / 删除后再写文件。

### Step 4: 写入 JD 文件
确认无误后，按数据契约写入：

```markdown
---
type: career-jd
company: 字节
title: 资深数据开发工程师
seniority: senior
location: 北京
status: active
captured: 2026-05-22
source: 拉勾
---

## 原文
（JD 原始文本，逐字粘贴，不删减）

## 抽取的技能要求
- skill: Flink, required-level: senior, in-jd-weight: 3
- skill: 数据建模, required-level: senior, in-jd-weight: 2
- skill: LLM 应用, required-level: mid, in-jd-weight: 1

## 软性要求
- skill: 跨团队推动, required-level: senior, in-jd-weight: 2

## 备注
（用户对这个岗位的想法，问用户；若用户无补充则写"无"）
```

### Step 5: 重算 `jd/aggregate.md`
**必须读所有 `jd/active/*.md`（不能只基于增量算）**：

1. 列出 `jd/active/*.md` 全部文件
2. 对每个文件解析"## 抽取的技能要求"和"## 软性要求"段（用同一套字段）
3. 对每个 skill 聚合：
   - `coverage` = 出现该 skill 的 JD 数 / `active-count`
   - `平均 required-level` = 各条 JD 该 skill `required-level` 的众数；多个众数取**较高**那个（按 level 排序）
   - 该 skill 在所有 JD 中的最大 `in-jd-weight`（用于"低频但高权重"判定）
4. 读 `skills-map.md` 取"你的 level"（未列出 → `none`）
5. 状态判定：见数据契约
6. 分三档输出：
   - 高频要求（coverage ≥ 60%）
   - 中频要求（30% ≤ coverage < 60%）
   - 低频但高权重（coverage < 30%，且至少一条 JD 标 `in-jd-weight=3`）
7. 覆盖式写入 `aggregate.md`：
   - **保留原 `created` 字段**
   - 更新 `updated` 字段为今天
   - 更新 `active-count` 字段
   - 覆盖三段正文

`active-count = 0` 的边界场景：写入"暂无 active JD"提示文案，不产出三段。

### Step 6: 输出（按场景分支）

**场景 A：新增 JD（首次入库）**
```
✅ 已录入 JD：<相对路径>
📊 聚合画像已更新：04_career/jd/aggregate.md（active-count: N）
🆕 这条 JD 暴露的新缺口（你的 level vs JD required-level）：
  - X（你 mid，JD 要求 senior）⚠️
  - Y（你 none，JD 要求 mid）❌
建议执行 /career roadmap 更新学习路线。
```

若该 JD 没有暴露新缺口（所有抽取技能你都 ≥ JD 要求）：
```
✅ 已录入 JD：<相对路径>
📊 聚合画像已更新：04_career/jd/aggregate.md（active-count: N）
🟢 这条 JD 没有暴露新缺口——你当前能力覆盖所有要求。
```

**场景 B：重复入库（已有同公司同岗位，用户选了覆盖/v2）**
```
✅ 已<覆盖|创建 v2>：<相对路径>（原文件：<原路径>）
📊 聚合画像已更新：04_career/jd/aggregate.md（active-count: N）
🆕 / 🟢 ...（同场景 A 的缺口部分）
```

**场景 C：从 archive 移回 active**
```
✅ 已移回 active：<新路径>（原 archive 路径：<原路径>）
📊 聚合画像已更新：04_career/jd/aggregate.md（active-count: N）
```

### Step 7: 追加成长轨迹
向 `growth-trajectory.md` 对应 `## YYYY-MM` 段落顶部追加一行：

```
- 2026-05-22 → jd added → [[04_career/jd/active/2026-05-22-字节-资深数据开发工程师.md]]
```

如果月份段落不存在，新建 `## YYYY-MM` 段落，按月段倒序（新月在上）插入。

### Step 8: 更新 `.manifest.json`
- 新增 JD → `jd.active` 数组 push 文件名（如 `2026-05-22-字节-资深数据开发工程师.md`，**只存文件名，不含目录前缀**——因为 active/archive 两个数组已经标明目录位置）
- 字段缺失则初始化为空数组后再 push

### Step 9: Commit

按实际写入的文件 git add（不要把未变更的文件加入暂存）。**含中文/特殊字符的路径必须用双引号包裹**。

**新增 JD**：
```
git add "04_career/jd/active/<新文件>" 04_career/jd/aggregate.md 04_career/growth-trajectory.md 04_career/.manifest.json
git commit -m "feat(career): add JD <公司>-<岗位>"
```

**status 变更（applied/rejected，文件留在 active/）**：
```
git add "04_career/jd/active/<原文件>" 04_career/growth-trajectory.md
git commit -m "chore(career): jd <公司>-<岗位> status -> <applied|rejected>"
```

**archive（移到 archive/）**：
```
# 物理移动 + 暂存一步到位
git mv "04_career/jd/active/<原文件名>" "04_career/jd/archive/<原文件名>"
# 追加其它变更
git add 04_career/jd/aggregate.md 04_career/growth-trajectory.md 04_career/.manifest.json
git commit -m "chore(career): archive JD <公司>-<岗位>"
```

## archive 与 status 变更
触发：用户说"我已经投了 X / X 不投了 / X 已 reject / 不再关注 X / archive X"。

询问要把 status 改成 `applied / archived / rejected` 中哪个（**闭集**，不要静默猜）：
- `applied` / `rejected` → 文件**留在 `active/`**，仅更新 frontmatter `status`；**仍计入 active-count**（aggregate 重算时把它算上，因为你还在追踪这条 JD 的画像）
- `archived` → 用 `git mv "04_career/jd/active/<原文件>" "04_career/jd/archive/<原文件>"` 一步完成物理移动 + git 暂存；然后更新 `.manifest.json` 的 active/archive 两个数组；**从 active-count 中排除**
- 三种情况**都必须重算 `aggregate.md`**（即使 active-count 没变，因为状态变化可能影响后续语义；且实现简单——总是重算）
- 三种情况都向 `growth-trajectory.md` 追加事件标记

**archive 不可逆地改文件位置——必须先询问确认再操作**。

## 铁律
- **不臆测 JD 没写的要求**——抽取只能基于 JD 原文，"看起来应该要求 X" 不算
- **不直接判断"你能不能拿到这个岗位"**——那是 `/career review` 的事
- **archive 操作必须问确认**——物理移动文件不可静默
- **同公司同岗位重复入库 → 询问处理方式**，不静默覆盖
- **链接只走白名单**——白名单内的平台（当前：BOSS 直聘）通过 web-access skill 自动抓取；不在白名单的链接必须由用户粘贴原文，不要凭印象访问
- **自动抓取后必须人工 sanity check**——Step 0 抓到的原文要先输出预览给用户确认，再进入 Step 1，避免选择器漂移导致脏数据落盘
- **抽取技能后必须让用户确认**——可能漏抽或抽错，不直接落盘
- **重算 aggregate 必须读所有 active JD**——不能只基于增量算
