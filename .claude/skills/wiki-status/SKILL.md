---
name: wiki-status
description: 查看 wiki 知识库状态和增量变化。当用户说"wiki 有多少页了""wiki 状态""最近 wiki 有什么变化"或输入 /wiki status 时使用。快速统计页面数、最近操作、待摄入资料。
---

# Wiki Status

## 执行步骤

### Step 1: 读取基础数据
- `01_wiki/.manifest.json` → stats + sources
- `01_wiki/index.md` → 页面清单
- `01_wiki/log.md` → 最近操作

### Step 2: 统计页面
按分类统计 `01_wiki/` 下的 `.md` 文件数（排除 _meta/、raw/、index.md、log.md）：
- concepts: N 页
- entities: N 页
- howtos: N 页
- references: N 页
- synthesis: N 页

按 status 统计：
- mature: N | draft: N | stub: N | stale: N

### Step 3: 增量检测（Delta）
扫描 `01_wiki/raw/` 下所有文件，与 `.manifest.json` 对比：
- **新文件**：raw/ 中有但 manifest 中没有 → 待摄入
- **已修改**：manifest 中有但文件 modified_at 更新了 → 待重新摄入
- **已处理**：一致 → 跳过

### Step 4: 输出状态报告
```markdown
## 📊 Wiki 状态

### 页面统计
| 分类 | 页数 |
|---|---|
| concepts | X |
| entities | X |
| howtos | X |
| references | X |
| synthesis | X |
| **总计** | **X** |

### 质量分布
mature: X | draft: X | stub: X | stale: X

### 来源追踪
- 已摄入来源：X 个
- 待摄入（raw/ 新文件）：Y 个
- 待更新（来源已修改）：Z 个

### 最近 5 次操作
（从 log.md 尾部提取）

### 建议
- 有 Y 个新文件待摄入，运行 `/wiki ingest` 处理
- 有 Z 个 stub 页面待补充
```

## 反模式
- 不要修改任何文件——这是只读操作
- 不要自动触发 ingest——只报告状态
