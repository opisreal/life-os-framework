---
name: career-log
description: 事件式工作日志/反馈记录。当用户说"记一下今天工作""收到反馈""我做了 X""周报""leader 说 Y"或输入 /career log 时使用。归档到 04_career/log/ 或 04_career/feedback/，追加事件标记到成长轨迹。
---

# Career Log

## 前置读取
1. `04_career/.manifest.json`（首次使用则初始化 `feedback` 数组）
2. `04_career/growth-trajectory.md`（用于追加事件标记）

## 数据契约（来自 04_career 模块设计文档 §2.2）

### log 文件
- 路径：`04_career/log/YYYY/YYYY-W{N}.md`（按 ISO 周分文件）
- frontmatter 字段（YAML）：
  - `type: career-log`
  - `week: YYYY-W{N}`（ISO 周编号）
  - `created: YYYY-MM-DD`
  - `updated: YYYY-MM-DD`（每次追加新条目都要更新）
- 正文结构：按 `## YYYY-MM-DD` 作 H2 分日；每条 H2 下用 `- [tag] 描述` 形式
- 标签闭集：`work` / `learn` / `meta` / `interview` / `side-project` / `networking`

### feedback 文件
- 路径：`04_career/feedback/YYYY-Q{N}/YYYY-MM-DD-{from}-{context}.md`（按季度分目录）
- frontmatter 字段（YAML）：
  - `type: career-feedback`
  - `date: YYYY-MM-DD`
  - `from: leader | peer | report | client | self`（report = 直接下属）
  - `context: <情境短语，如 "季度1on1" / "PR review" / "code review">`
  - `sentiment: positive | mixed | critical`
- 正文三段：`## 原话/要点` + `## 我的解读`（留空给用户）+ `## Action Items`（含 `- [ ] ...` 待办格式）

### growth-trajectory.md 追加格式
- 按 `## YYYY-MM` H2 分月，月段倒序（新月在上）
- **月内条目按日期倒序，最新事件在段落顶部**
- log 事件：`- YYYY-MM-DD → log → [[相对路径]]`
- feedback 事件：`- YYYY-MM-DD → feedback (from, context, sentiment) → [[相对路径]]`

### .manifest.json 更新
- 仅 feedback 路径会追加 `feedback` 数组（push 新文件相对路径）
- log 路径不动 manifest

## 输入识别
用户的自然语言输入可能是：
- "今天我做了 X / 学了 Y / 状态如何"
- "leader/同事/客户 在 1on1/PR review 上说 ABC"
- "我自评一下：..."

## 执行步骤

### Step 1: 判断输入类型
- 含"反馈/评价/1on1/PR review/code review/绩效"等词 → **feedback 路径**
- 否则 → **log 路径**

**歧义处理**：
- "PR review / code review" 同时出现"我"做了 / "我"评审了 vs "别人评审我的"
  - **用户是执行方**（"我 review 了 3 个 PR"） → log 路径（[work] 标签）
  - **用户是接收方**（"老板在 PR review 里说我..."） → feedback 路径
- "开会" / "讨论" 等词暧昧 → **必须问用户确认是工作记录还是反馈情境**

### Step 2A: log 路径
1. 计算当前周（ISO 周编号，如 `2026-W21`）
2. 文件路径：`04_career/log/YYYY/YYYY-W{N}.md`
3. 如果文件不存在 → 创建并写入 frontmatter：
   ```yaml
   ---
   type: career-log
   week: 2026-W21
   created: 2026-05-19
   updated: 2026-05-21
   ---
   ```
4. 检查文件内是否已有今天的 H2 段落（`## YYYY-MM-DD`）：
   - 有 → 在该段下追加条目
   - 无 → 新建 H2 段落
5. 抽取条目分类标签（**闭集**）：
   - work / learn / meta / interview / side-project / networking
   - 模糊时问用户确认
   - 超出闭集 → 询问用户"是否归并到现有标签，或新增（新增需用户显式确认）"——不静默使用未授权的新标签
6. 条目格式：`- [tag] 简洁描述`（保留用户原话的精炼版本，**不展开成长篇大论**）
7. 更新 frontmatter 的 `updated` 字段

### Step 2B: feedback 路径
1. 询问/确认四要素：
   - 日期（YYYY-MM-DD）
   - 来源（leader / peer / report（直接下属）/ client / self）
   - 情境（context，如"季度 1on1"、"PR review"）
   - 情感倾向（positive / mixed / critical）
2. 文件命名：`04_career/feedback/YYYY-Q{N}/YYYY-MM-DD-{from}-{context}.md`
   - **{context} 处理规则**：保留中文与拉丁字符；去除空格和路径不安全字符（`/`、`:`、`?`、`#`、`\`、`*`、`<`、`>`、`|`、`"`）；emoji 保留但避免依赖
   - **重名处理**：若同日同 from 同 context 的文件已存在 → 询问用户"追加到原文件 / 新建带 -2 后缀 / 取消"，不静默覆盖
3. 文件结构：
   ```markdown
   ---
   type: career-feedback
   date: 2026-05-15
   from: leader
   context: 季度1on1
   sentiment: mixed
   ---

   ## 原话/要点
   ...

   ## 我的解读
   ...

   ## Action Items
   - [ ] ...
   ```
4. "原话/要点"段：用户原话或转述
5. "我的解读"段：留空，由用户后续补——不替用户写
6. "Action Items" 段：如果原话里隐含行动项，列出来；否则留空，问用户

### Step 3: 追加成长轨迹
向 `04_career/growth-trajectory.md` 对应月份段落追加一行：

**log 事件**：
```
- 2026-05-21 → log → [[04_career/log/2026/2026-W21.md]]
```

**feedback 事件**：
```
- 2026-05-15 → feedback (leader, 季度1on1, mixed) → [[04_career/feedback/2026-Q2/2026-05-15-leader-季度1on1.md]]
```

如果月份段落不存在，新建 `## YYYY-MM` 段落，按倒序（新月在上）插入。**月内条目按日期倒序，最新事件在段落顶部**——同一日多条事件保留插入顺序（即最后追加的在最上面）。

### Step 4: 更新 .manifest.json（仅 feedback 路径）
向 `feedback` 数组 push 新文件相对路径（log 不需要 track）。

### Step 5: 输出确认

**log 路径**：
```
✅ 追加到：<相对路径>
追加条目：N 条
成长轨迹：已追加 1 条事件标记
```

**feedback 路径**：
```
✅ 写入：<相对路径>
成长轨迹：已追加 1 条事件标记
manifest：feedback 数组 +1
```

### Step 6: Commit

按实际写入的文件 git add（不要把未变更的文件加入暂存）：

**log 路径**：
```
git add 04_career/log/<实际写入的周文件> 04_career/growth-trajectory.md
git commit -m "feat(career): log YYYY-MM-DD <work x2 + learn x1 风格的简短描述>"
```

**feedback 路径**：
```
git add 04_career/feedback/<实际写入的反馈文件> 04_career/growth-trajectory.md 04_career/.manifest.json
git commit -m "feat(career): feedback <from> <context>"
```

## 铁律
- **不编造内容**——用户没说的细节不要添加（包括日期、来源、情感倾向）
- **不展开成长篇大论**——log 条目用一行精炼描述，不写"反思""感悟"段（那是 review 的事）
- **不调用其他 career-* skill**——保持单一职责
- **不主动复盘**——只归档，等用户显式触发 `/career review`
- **模糊信息必须问清楚**——日期、来源、分类标签
- **不替用户写"我的解读"**——feedback 文件该段留空
