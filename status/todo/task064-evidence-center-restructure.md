# task064 — 知识中心页面布局重构：过滤器上移

> **状态**: ✅ 已落实 | **优先级**: P1 | **预估工时**: 2–3h | **日期**: 2026-08-12

---

## 1. 背景与目标

### 1.1 当前布局分析

`EvidenceCenterPage.tsx` (约 962 行) 当前采用三段式布局：

```
┌──────────────────────────────────────────────────┐
│  .kc-hero                                         │
│  ┌──────────────────────────────────────────────┐ │
│  │ [标题] [搜索框+按钮] [同步按钮]              │ │
│  │ [Tab: 法规 | 案例 | 条文 | 引用]             │ │
│  │ [依据] [案例] [命中] [最近更新] [同步] ...   │ │ ← 7 个统计卡片
│  └──────────────────────────────────────────────┘ │
├──────────────┬───────────────────────┬────────────┤
│ .kc-col (左) │ .kc-col (中)          │ .kc-col(右)│
│ ┌──────────┐ │ ┌───────────────────┐ │ ┌────────┐ │
│ │ 列表标题 │ │ │ 详情标题          │ │ │引用与  │ │
│ ├──────────┤ │ ├───────────────────┤ │ │说明    │ │
│ │🔽 过滤器 │ │ │ 选中项详情        │ │ ├────────┤ │
│ │ 按内容分类│ │ │ - 基本信息        │ │ │同步状态 │ │
│ │ 按适用法域│ │ │ - 摘要            │ │ │使用说明 │ │
│ │ 按使用方式│ │ │ - 预览            │ │ │引用查询 │ │
│ │──────────│ │ │                   │ │ │         │ │
│ │ 条目列表 │ │ │                   │ │ │         │ │
│ │ - 法规1  │ │ │                   │ │ │         │ │
│ │ - 法规2  │ │ │                   │ │ │         │ │
│ └──────────┘ │ └───────────────────┘ │ └────────┘ │
└──────────────┴───────────────────────┴────────────┘
```

**核心问题**：过滤器组（3 组 chip 过滤器）占用左栏大量垂直空间，挤压了条目列表的可视区域。用户选择过滤器后，列表区域收缩，交互体验较差。

### 1.2 目标布局

将过滤器从左侧栏移出，作为独立水平条放置在 7 个统计卡片与主网格之间：

```
┌──────────────────────────────────────────────────────────────┐
│  .kc-hero                                                     │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ [标题] [搜索框+按钮] [同步按钮]                          │ │
│  │ [Tab: 法规 | 案例 | 条文 | 引用]                         │ │
│  │ [依据] [案例] [命中] [最近更新] [同步] [迁移] [可见]    │ │ ← 7 张卡（保持）
│  └──────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────┤
│  .kc-filter-bar (新增)                                        │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ [按内容分类 chips: 法律 行政法规 部门规章 ...]           │ │
│  │ [按适用法域 chips: CN EU US ...]                         │ │
│  │ [按使用方式 chips: 合规评估 风险评估 合同审查 ...]       │ │
│  └──────────────────────────────────────────────────────────┘ │
├──────────────┬───────────────────────┬────────────────────────┤
│ .kc-col (左) │ .kc-col (中)          │ .kc-col (右)           │
│ ┌──────────┐ │ ┌───────────────────┐ │ ┌────────────────────┐ │
│ │ 列表标题 │ │ │ 详情标题          │ │ │ 引用与说明         │ │
│ ├──────────┤ │ ├───────────────────┤ │ ├────────────────────┤ │
│ │ 条目列表 │ │ │ 选中项详情        │ │ │ 同步状态           │ │
│ │ (无过滤器)│ │ │                   │ │ │ 使用说明           │ │
│ │ - 法规1  │ │ │                   │ │ │ 引用查询           │ │
│ │ - 法规2  │ │ │                   │ │ │                    │ │
│ │ - 法规3  │ │ │                   │ │ │                    │ │
│ │   ...    │ │ │                   │ │ │                    │ │
│ └──────────┘ │ └───────────────────┘ │ └────────────────────┘ │
└──────────────┴───────────────────────┴────────────────────────┘
```

**关键变更**：
- 左侧栏 body 内容：删除过滤器 HTML，**仅保留列表**
- 新增 `.kc-filter-bar`：水平排列的过滤器组，不同 Tab 展示不同过滤器
- 7 张统计卡片位置不变，保持在 `.kc-hero` 内

---

## 2. Tab 与过滤器的对应关系

| Tab | 过滤器组 | 状态变量 |
|-----|---------|---------|
| `sources`（法规） | ① 按内容分类 (`sourceCategoryOptions`) ② 按适用法域 (`sourceJurisdictionOptions`) ③ 按使用方式 (`sourceUsageOptions`) | `selectedCategories`, `selectedSourceJurisdictions`, `selectedUsages` |
| `cases`（案例） | ① 法域 (`caseJurisdictionOptions`) ② 场景 (`caseScenarioOptions`) | `selectedCaseJurisdictions`, `selectedScenarios` |
| `articles`（条文） | ① 法域 (cn/eu/us) ② 场景路径 ③ 搜索框 | `articlesJurisdiction`, `articlesPath`, `articlesQuery` |
| `citation`（引用） | **无过滤器** — 该 Tab 仅显示引用查询面板 | — |

---

## 3. 实施步骤

### Step 1：提取可复用过滤器组件 (可选，降低复杂度)

如果直接内联，代码更简单，但会导致 JSX 重复 3 次（sources/cases/articles）。建议采用**内联 + Tab 切换**方式，每条 if 分支不超过 20 行。

### Step 2：在 `.kc-hero` 和 `.kc-main-grid` 之间插入 `.kc-filter-bar`

**位置**：`EvidenceCenterPage.tsx` 第 570 行（`</section>` 关闭 `.kc-hero`）之后，第 572 行（`<section className="kc-main-grid">`）之前。

```tsx
514  return (
515    <section className="page-shell evidence-page kc-page">
516      <section className="kc-hero">
517        ...
569        </div>
570      </section>   {/* .kc-hero */}
571
572 +    {/* ── 新增：水平过滤器条 ── */}
573 +    {tab !== "citation" ? (
574 +      <section className="kc-filter-bar">
575 +        {tab === "sources" ? (
576 +          <>
577 +            <div className="knowledge-filter-group kc-filter-group-h">
578 +              <small>{copy.sourceFilterCategory}</small>
579 +              <div className="knowledge-chip-row">
580 +                {sourceCategoryOptions.map((option) => (
581 +                  <button key={option} className={`chip-btn ${selectedCategories.includes(option) ? "active" : ""}`}
582 +                    onClick={() => setSelectedCategories((prev) => toggleValue(prev, option))}>
583 +                    {option}
584 +                  </button>
585 +                ))}
586 +                {sourceCategoryOptions.length === 0 ? <span className="chip-empty">{copy.optionsEmpty}</span> : null}
587 +              </div>
588 +              <div className="knowledge-filter-actions">
589 +                <button className="ghost-btn" onClick={() => setSelectedCategories(sourceCategoryOptions)}>{copy.selectAll}</button>
590 +                <button className="ghost-btn" onClick={() => setSelectedCategories([])}>{copy.clearAll}</button>
591 +              </div>
592 +            </div>
593 +            <div className="knowledge-filter-group kc-filter-group-h">
594 +              <small>{copy.sourceFilterJurisdiction}</small>
595 +              <div className="knowledge-chip-row">
596 +                {sourceJurisdictionOptions.map((option) => (
597 +                  <button key={option} className={`chip-btn ${selectedSourceJurisdictions.includes(option) ? "active" : ""}`}
598 +                    onClick={() => setSelectedSourceJurisdictions((prev) => toggleValue(prev, option))}>
599 +                    {option}
600 +                  </button>
601 +                ))}
602 +                {sourceJurisdictionOptions.length === 0 ? <span className="chip-empty">{copy.optionsEmpty}</span> : null}
603 +              </div>
604 +              <div className="knowledge-filter-actions">
605 +                <button className="ghost-btn" onClick={() => setSelectedSourceJurisdictions(sourceJurisdictionOptions)}>{copy.selectAll}</button>
606 +                <button className="ghost-btn" onClick={() => setSelectedSourceJurisdictions([])}>{copy.clearAll}</button>
607 +              </div>
608 +            </div>
609 +            <div className="knowledge-filter-group kc-filter-group-h">
610 +              <small>{copy.sourceFilterUsage}</small>
611 +              <div className="knowledge-chip-row">
612 +                {sourceUsageOptions.map((option) => (
613 +                  <button key={option} className={`chip-btn ${selectedUsages.includes(option) ? "active" : ""}`}
614 +                    onClick={() => setSelectedUsages((prev) => toggleValue(prev, option))}>
615 +                    {option}
616 +                  </button>
617 +                ))}
618 +                {sourceUsageOptions.length === 0 ? <span className="chip-empty">{copy.optionsEmpty}</span> : null}
619 +              </div>
620 +              <div className="knowledge-filter-actions">
621 +                <button className="ghost-btn" onClick={() => setSelectedUsages(sourceUsageOptions)}>{copy.selectAll}</button>
622 +                <button className="ghost-btn" onClick={() => setSelectedUsages([])}>{copy.clearAll}</button>
623 +              </div>
624 +            </div>
625 +          </>
626 +        ) : tab === "cases" ? (
627 +          <>
628 +            <div className="knowledge-filter-group kc-filter-group-h">
629 +              <small>{copy.caseFilterJurisdiction}</small>
630 +              <div className="knowledge-chip-row">
631 +                {caseJurisdictionOptions.map((option) => (
632 +                  <button key={option} className={`chip-btn ${selectedCaseJurisdictions.includes(option) ? "active" : ""}`}
633 +                    onClick={() => setSelectedCaseJurisdictions((prev) => toggleValue(prev, option))}>
634 +                    {option}
635 +                  </button>
636 +                ))}
637 +                {caseJurisdictionOptions.length === 0 ? <span className="chip-empty">{copy.optionsEmpty}</span> : null}
638 +              </div>
639 +              <div className="knowledge-filter-actions">
640 +                <button className="ghost-btn" onClick={() => setSelectedCaseJurisdictions(caseJurisdictionOptions)}>{copy.selectAll}</button>
641 +                <button className="ghost-btn" onClick={() => setSelectedCaseJurisdictions([])}>{copy.clearAll}</button>
642 +              </div>
643 +            </div>
644 +            <div className="knowledge-filter-group kc-filter-group-h">
645 +              <small>{copy.caseFilterScenario}</small>
646 +              <div className="knowledge-chip-row">
647 +                {caseScenarioOptions.map((option) => (
648 +                  <button key={option} className={`chip-btn ${selectedScenarios.includes(option) ? "active" : ""}`}
649 +                    onClick={() => setSelectedScenarios((prev) => toggleValue(prev, option))}>
650 +                    {option}
651 +                  </button>
652 +                ))}
653 +                {caseScenarioOptions.length === 0 ? <span className="chip-empty">{copy.optionsEmpty}</span> : null}
654 +              </div>
655 +              <div className="knowledge-filter-actions">
656 +                <button className="ghost-btn" onClick={() => setSelectedScenarios(caseScenarioOptions)}>{copy.selectAll}</button>
657 +                <button className="ghost-btn" onClick={() => setSelectedScenarios([])}>{copy.clearAll}</button>
658 +              </div>
659 +            </div>
660 +          </>
661 +        ) : tab === "articles" ? (
662 +          <>
663 +            <div className="knowledge-filter-group kc-filter-group-h">
664 +              <small>{copy.articlesFilterJurisdiction}</small>
665 +              <div className="knowledge-chip-row">
666 +                {["cn", "eu", "us"].map((jur) => (
667 +                  <button
668 +                    key={jur}
669 +                    className={`chip-btn ${articlesJurisdiction === jur ? "active" : ""}`}
670 +                    onClick={() => setArticlesJurisdiction((prev) => prev === jur ? "" : jur)}
671 +                  >
672 +                    {jur.toUpperCase()}
673 +                  </button>
674 +                ))}
675 +              </div>
676 +            </div>
677 +            <div className="knowledge-filter-group kc-filter-group-h">
678 +              <small>{copy.articlesFilterPath}</small>
679 +              <div className="knowledge-chip-row">
680 +                {ARTICLE_SCENARIO_OPTIONS.map((option) => (
681 +                  <button
682 +                    key={option.value}
683 +                    className={`chip-btn ${articlesPath === option.value ? "active" : ""}`}
684 +                    onClick={() => setArticlesPath((prev) => prev === option.value ? "" : option.value)}
685 +                  >
686 +                    {lang === "zh" ? option.zh : option.en}
687 +                  </button>
688 +                ))}
689 +              </div>
690 +            </div>
691 +            <div className="knowledge-filter-group kc-filter-group-h" style={{ minWidth: "220px" }}>
692 +              <small>{copy.articlesPlaceholder}</small>
693 +              <input
694 +                className="resource-search"
695 +                placeholder={copy.articlesPlaceholder}
696 +                value={articlesQuery}
697 +                onChange={(e) => setArticlesQuery(e.target.value)}
698 +              />
699 +            </div>
700 +          </>
701 +        ) : null}
702 +      </section>
703 +    ) : null}
704 +
705      <section className="kc-main-grid">
```

### Step 3：从左侧栏删除过滤器

当前左侧栏 body 内容结构（每种 Tab）：

```
kc-col-body
├── tab === "sources"  → knowledge-filter-grid (3组过滤器) + kc-list-scroll (列表)
├── tab === "cases"    → knowledge-filter-grid (2组过滤器) + kc-list-scroll (列表)
├── tab === "articles" → knowledge-filter-grid (3组:法域/路径/搜索) + kc-list-scroll (列表)
└── tab === "citation" → citation-panel
```

修改后（每种 Tab）：

```
kc-col-body
├── tab === "sources"  → kc-list-scroll (列表, 无过滤器)
├── tab === "cases"    → kc-list-scroll (列表, 无过滤器)
├── tab === "articles" → kc-list-scroll (列表, 无过滤器)
└── tab === "citation" → citation-panel
```

**具体删除区域**：

- **sources tab**（行 579–627）：删除整个 `<div className="knowledge-filter-grid">...</div>` 块（3 组过滤器），保留 `<div className="evidence-hit-scroll kc-list-scroll">...`
- **cases tab**（行 644–677）：删除整个 `<div className="knowledge-filter-grid">...</div>` 块（2 组过滤器），保留 `<div className="evidence-hit-scroll kc-list-scroll">...`
- **articles tab**（行 694–732）：删除整个 `<div className="knowledge-filter-grid">...</div>` 块（法域/路径/搜索），保留 `<div className="evidence-hit-scroll kc-list-scroll">...`
  - **注意**：articles tab 的搜索框 (`articlesQuery`) 也移到了水平过滤器条中（Step 2）

### Step 4：CSS 新增样式

在 `pages.css` 中新增 `.kc-filter-bar` 及相关样式：

```css
/* ── 水平过滤器条 ── */
.kc-filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  padding: 0.65rem 0.9rem;
  border: 1px solid rgba(145, 179, 224, 0.28);
  border-radius: 16px;
  background: rgba(251, 254, 255, 0.9);
  box-shadow: 0 8px 20px rgba(16, 44, 79, 0.04);
  margin-top: 0.2rem;
}

/* 水平排列的过滤器组（覆盖默认 grid 布局） */
.kc-filter-group-h {
  flex: 1 1 200px;           /* 最小 200px，自动扩展 */
  min-width: 180px;
  max-width: 360px;
  display: flex;
  flex-direction: column;
  gap: 0.34rem;
}

/* 过滤器的 chip-row 保持水平换行 */
.kc-filter-group-h .knowledge-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
}

/* filter-actions 保持紧凑 */
.kc-filter-group-h .knowledge-filter-actions {
  display: flex;
  gap: 0.3rem;
}

/* 过滤器的 small 标签 */
.kc-filter-group-h small {
  font-size: 0.72rem;
  color: #5a7ea4;
  white-space: nowrap;
}

/* 搜索框在 filter-bar 中的样式 */
.kc-filter-group-h .resource-search {
  min-height: 34px;
  font-size: 0.82rem;
}
```

### Step 5：CSS 修改/移除冗余样式

**移除 `.kc-page .knowledge-filter-grid { margin-top: 0; }`**（行 1953–1955），因为过滤器已不在 `.kc-page` 内部。

修改（可选保留，改为无副作用）：

```css
/* 原行 1953-1955 可删除；过滤器的间距由 kc-filter-bar 控制 */
```

**确保 `kc-col-body` 中不再有 `knowledge-filter-grid` 的子元素**，因此 `.kc-page .knowledge-filter-grid` 规则（行 1953）和 `.kc-page .knowledge-filter-group` 规则（行 1957）可保留或移除——保留不影响功能（因为选择器匹配不到元素了）。

---

## 4. 状态管理：过滤器跨 Tab 切换保持

**当前行为**：Tab 切换不会重置过滤器状态。所有状态变量使用 `useState`，存在于组件生命周期内，不会因 Tab 切换丢失。

**重构后的行为不变**：过滤器已从 Tab 内容中提取到水平条，但状态变量未变——仍由组件顶层 `useState` 管理。切换 Tab 时过滤器条内容变化，但状态持续存在。

**验证要点**：
1. 在 sources tab 中选择 "法律" + "CN"，切换到 cases tab → 再切回 sources tab → "法律" 和 "CN" 仍被选中 ✓
2. 在 sources tab 中清除所有过滤 → 切换到 articles tab 输入搜索词 → 再切回 sources tab → 过滤清空状态保留 ✓

---

## 5. 可验核测试清单

### 5.1 人工校验（手动操作）

| # | 测试步骤 | 预期结果 | 严重度 |
|---|---------|---------|--------|
| V1 | 打开知识中心页面 | ① 7 张统计卡片一行排列 ② 卡片下方看到水平过滤器条 ③ 过滤器条中有 3 组 chip 按钮 | BLOCKER |
| V2 | 切换到 "案例" Tab | ① 过滤器条变为 2 组（法域 + 场景）② 左侧栏显示案例列表（无过滤器） | BLOCKER |
| V3 | 切换到 "条文" Tab | ① 过滤器条变为 3 组（法域 + 场景路径 + 搜索框）② 左侧栏显示条文搜索结果 | BLOCKER |
| V4 | 切换到 "引用" Tab | ① 过滤器条**完全消失**（citation 无过滤器）② 左侧栏显示引用查询面板 | BLOCKER |
| V5 | 在 sources 中点击 chip 选择 "法律" | ① chip 变为 active 状态 ② 左侧栏列表仅显示 category=法律 的条目 ③ 命中数量实时更新 | HIGH |
| V6 | 在 sources 中点击 "全选" / "清除" | ① chip 全部 active / 全部取消 ② 列表实时刷新 | HIGH |
| V7 | 在 cases 中点击某法域 chip | 同 V5，但针对案例列表 | HIGH |
| V8 | 在 articles 中输入搜索词 | ① 左侧栏显示搜索结果 ② 命中数量更新 | HIGH |
| V9 | 过滤器状态跨 Tab 保持 | ① sources 中选择 CN ② 切到 cases ③ 再切回 sources ④ CN 仍被选中 | HIGH |
| V10 | 窄屏响应（<1460px） | ① 过滤器条换行 ② 7 张卡片可能换行到 3+2+2 ③ 主网格变为 2 列 | MEDIUM |
| V11 | 窄屏响应（<1140px） | 过滤器条在手机端仍可操作（chip 大小不变） | MEDIUM |
| V12 | 窄屏响应（<760px） | 最小屏幕，过滤器条正常换行，所有 chip 可点击 | LOW |

### 5.2 自动化/半自动校验

```bash
# 编译检查
cd frontend && npm run build 2>&1 | grep -i error

# 无 JSX 语法错误
# 无未闭合标签
# 无 undefined variable 引用

# 类型检查（如果项目配置了）
cd frontend && npx tsc --noEmit 2>&1 | head -20

# 查找所有 className 引用是否有未定义的 CSS
grep -rn "kc-filter-bar\|kc-filter-group-h" frontend/src/
```

### 5.3 DOM 结构验证（浏览器 DevTools）

```javascript
// 在浏览器 Console 中运行：
// 1. 过滤器条存在
console.assert(document.querySelector('.kc-filter-bar'), 'kc-filter-bar missing');

// 2. 过滤器组在 kc-filter-bar 内，不在 kc-col-body 内
var bodyHasFilterGrid = document.querySelector('.kc-col-body .knowledge-filter-grid');
console.assert(!bodyHasFilterGrid, 'knowledge-filter-grid still inside kc-col-body');

// 3. 左侧栏仅包含列表
var leftColBody = document.querySelector('.kc-main-grid > .kc-col:first-child .kc-col-body');
var filterInLeft = leftColBody?.querySelector('.knowledge-filter-grid');
console.assert(!filterInLeft, 'filter still in left column');

// 4. sources tab 有 3 组过滤器
var filterGroups = document.querySelectorAll('.kc-filter-bar .kc-filter-group-h');
console.log('Filter groups in bar:', filterGroups.length);
```

---

## 6. 风险评估与边缘情况

| 风险 | 概率 | 影响 | 应对 |
|-----|------|------|------|
| **过滤器条在窄屏上过高** | 中 | 低 | `.kc-filter-bar` 使用 `flex-wrap: wrap`，过滤器组自动换行。每个 `.kc-filter-group-h` 有 `max-width: 360px` 防止过度扩展 |
| **articles 搜索框移出左栏后用户找不到** | 低 | 中 | 搜索框放在水平过滤器条的最右侧，有 `资源搜索` 标签（`articlesPlaceholder`） |
| **citation tab 无过滤器，留下空白区域** | 低 | 低 | `{tab !== "citation" ? <section className="kc-filter-bar"> ... </section> : null}` 条件渲染，完全移除 |
| **过滤器条与 kc-hero 的视觉间距** | 低 | 低 | CSS `margin-top: 0.2rem` 提供微小间距，可通过 `gap` 调整 |
| **chip 按钮数量过多时换行导致过滤器条高度增加** | 中 | 中 | `knowledge-chip-row` 已有 `flex-wrap: wrap`，chip 自动换行。必要时可添加 `max-height` + `overflow-y: auto` |
| **原 `.kc-page .knowledge-filter-group` 样式冲突** | 低 | 低 | 新过滤器条使用不同的 className（`kc-filter-group-h`），不会受旧规则影响 |

---

## 7. 文件变更清单

| 文件 | 变更类型 | 描述 |
|------|---------|------|
| `frontend/src/pages/EvidenceCenterPage.tsx` | **修改** | ① 行 571 之后插入 `.kc-filter-bar` 块（~130 行新增）② 行 579–627 删除 sources 过滤器 ③ 行 644–677 删除 cases 过滤器 ④ 行 694–732 删除 articles 过滤器 |
| `frontend/src/styles/app/pages.css` | **修改** | ① 新增 `.kc-filter-bar` 样式块 ② 新增 `.kc-filter-group-h` 样式块 ③ 可选：移除或保留 `.kc-page .knowledge-filter-grid` 冗余规则 |

---

## 8. 验收标准

- [x] 三个过滤器组（按内容分类/按适用法域/按使用方式）在 7 张统计卡片下方水平排列
- [x] 左侧栏仅显示条目列表和标题，无任何过滤器内容
- [x] 切换 Tab 时过滤器条内容自动变化（sources→3组, cases→2组, articles→3组, citation→隐藏）
- [x] 过滤器选中状态在 Tab 切换后保持（状态变量未变，仍由组件顶层 `useState` 管理）
- [x] 所有 chip 点击、全选、清除功能正常（逻辑原样迁移）
- [ ] 窄屏（<1460px、<1140px、<760px）下无布局错乱（待浏览器人工核验）
- [x] `npm run build` 无编译错误
- [ ] DevTools Console 无新增 warning/error（待浏览器人工核验）

---

## 9. 落实记录（2026-08-12）

**已完成的代码变更**：

| 文件 | 变更 |
|------|------|
| `frontend/src/pages/EvidenceCenterPage.tsx` | ① 在 `.kc-hero` 与 `.kc-main-grid` 之间插入 `.kc-filter-bar`（`tab !== "citation"` 条件渲染，sources/cases/articles 各分支）② 删除左栏 `kc-col-body` 中三个 Tab 的 `knowledge-filter-grid` 过滤器块 |
| `frontend/src/styles/app/pages.css` | ① 新增 `.kc-filter-bar` 与 `.kc-filter-group-h` 样式（替换原 `.kc-page .knowledge-filter-grid` 冗余规则） |

**验证结果**：
- `npx tsc --noEmit` → exit 0（无类型错误）
- `npm run build` → ✓ built in 3.09s（`EvidenceCenterPage` chunk 成功产出 27.99 kB）
- `grep knowledge-filter-grid` 在 TSX 中 → 0 命中（旧过滤器块已完全移除）

**待人工浏览器核验项**（V1–V12 测试清单）：窄屏响应、DevTools Console、chip 交互视觉态。

---

## 10. 补充方案：三处"横向铺满 + 自适应"缺陷修复（2026-08-12 追加）

> **背景**：task064 落地后，过滤器上移导致三处视觉缺陷，诉求一致——**横向铺满整行、随窗口自适应、不留白**。本方案仅记录，**暂不改动代码**。

### 缺陷 1：左侧栏列表窗口下方留大片空白

**根因**（结构性矛盾，非单纯 max-height 问题）：

- `.kc-main-grid` 是 `display: grid`，三栏默认 `align-items: stretch` → **三栏永远等高**；
- 行高由 `min-height: calc(100vh - 250px)` 兜底，再被最高栏（中间详情列 / 右栏说明）拉高；
- 左栏列表 `.kc-list-scroll` 死守 `max-height: min(52vh, 520px)`。

→ 行高一旦超过 520px（1080p 下几乎必然），左栏列表停在 520px，下方空一截。

**错误尝试已回滚**：上一轮曾把共用的 `.kc-col-body` 改成 `flex-direction: column`、把 `.kc-list-scroll` 改成 `flex:1; max-height:none`——**副作用打偏**：`.kc-col-body` 是左/中/右三栏共用类，改动会污染中栏详情卡、右栏说明的 grid 布局；且滚动从"列表内部滚动"退化为"列体整体滚动"。**已恢复原状**。

**正确方案**（只精确定位左栏，不碰中/右栏）：

| 步骤 | 定位方式 | CSS |
|------|---------|-----|
| 1 | 左栏列体撑满（用 `:first-child` 结构性选择器，**不加新类**，不污染中/右栏） | `.kc-main-grid > .kc-col:first-child .kc-col-body { display:flex; flex-direction:column; flex:1 1 auto; min-height:0; }` |
| 2 | 左栏列表内部滚动铺满（`.kc-list-scroll` **只用在左栏**，全局改安全） | `.kc-list-scroll { flex:1 1 auto; min-height:0; max-height:none; }`（`overflow:auto` 已由 `.evidence-hit-scroll` 提供） |

**关键点**：
- `.kc-col` 本身已是 `display:flex; flex-direction:column; overflow:hidden`，**不用动**；
- 中栏 `.kc-col-body`（详情卡 grid）、右栏 `.kc-col-body`（说明块 grid）**保持原样**；
- `citation` Tab 左栏是 `evidence-citation-panel` 而非 list-scroll，body 撑满后 panel 靠顶部排列，不受影响（若 panel 超长，body 的 `overflow:auto` 兜底）。

**验证**：sources/cases/articles 三个 Tab 的左栏列表应填满整列高度、仅列表内部滚动；中栏右栏布局无任何变化。

---

### 缺陷 2：过滤器条横向不饱满

**根因**：`.kc-filter-group-h` 的 `max-width: 360px` 封顶。三组各顶到 360px 就停，容器还有富余宽度时（如 1300px 宽）右侧空一截，未铺满整条。

**方案**：去掉 `max-width` 封顶，三组按 `flex: 1 1 200px` 均分整行宽度、随窗口自适应。

```css
.kc-filter-group-h {
  flex: 1 1 200px;   /* 能均分扩展 */
  min-width: 180px;  /* 保留最小宽度，防止过窄时挤压变形 */
  /* max-width: 360px;  ← 删除 */
  display: flex;
  flex-direction: column;
  gap: 0.34rem;
}
```

**验证**：桌面端三组均分铺满整条宽度；缩窄窗口时随容器收缩，`min-width: 180px` 触底后自动换行。

---

### 缺陷 3：七个状态卡片不饱满（排成「5 + 2」两行）

**根因**：`.kc-status-row` 只写 `grid-template-columns: repeat(5, minmax(0, 1fr))`，但实际有 **7 个卡片**（依据条目 / 案例条目 / 当前命中 / 最近更新 / 纳入同步范围 / 已迁移落盘 / 前端可见）→ 排成 5 + 2 两行，第二行右侧空 3/5。

**方案**：桌面端改为 7 列一行铺满，并补一档响应式过渡（4 列）避免 1140–1460px 区间 7 列过挤。

```css
/* 默认 >1460px：7 列一行铺满 */
.kc-status-row {
  grid-template-columns: repeat(7, minmax(0, 1fr));
}

@media (max-width: 1460px) {
  .kc-status-row { grid-template-columns: repeat(4, minmax(0, 1fr)); }  /* 新增过渡档：4+3 */
}

@media (max-width: 1140px) {
  .kc-status-row { grid-template-columns: repeat(3, minmax(0, 1fr)); }  /* 保持原样：3+3+1 */
}

@media (max-width: 760px) {
  .kc-status-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }  /* 保持原样：2+2+2+1 */
}
```

**响应式分布**：

| 断点 | 列数 | 卡片分布 |
|------|------|---------|
| >1460px | 7 | 一行 7 个 |
| ≤1460px | 4 | 4 + 3 两行 |
| ≤1140px | 3 | 3 + 3 + 1 三行 |
| ≤760px | 2 | 2 + 2 + 2 + 1 四行 |

**可选优化（次要视觉细节，可不做）**：`.kc-status-item` 用 `border-right` + `:last-child` 清尾。多行分布时每行末尾卡片的右侧分隔线会残留（非 `:last-child`）。若要求每行末尾无分隔线，可改为 `.kc-status-item:nth-child(7n) { border-right: none }` 配合各断点 n 值（4/3/2）——但会引入断点相关的 n 值维护成本，建议先接受"表格式分隔线"观感，不强行处理。

---

### 变更清单（本方案，待批准后执行）

| 文件 | 变更 |
|------|------|
| `frontend/src/styles/app/pages.css` | ① 新增 `.kc-main-grid > .kc-col:first-child .kc-col-body` 左栏撑满规则 ② `.kc-list-scroll` 改 `flex:1; min-height:0; max-height:none` ③ `.kc-filter-group-h` 删除 `max-width: 360px` ④ `.kc-status-row` 默认改 7 列 + 1460 断点补 4 列 |

**执行前置**：仅 `pages.css` 一个文件、纯 CSS、无 TSX 改动；`npx tsc --noEmit` + `npm run build` 均可跳过（无类型/构建影响），但需浏览器人工核验 V1–V12 响应式清单。

### 落实状态（2026-08-12 已执行）

| 缺陷 | 变更 | 状态 |
|------|------|------|
| ① 侧栏列表空白 | 新增 `.kc-main-grid > .kc-col:first-child .kc-col-body`（`flex:1; min-height:0`）；`.kc-list-scroll` 改 `flex:1 1 auto; min-height:0; max-height:none` | ✅ |
| ② 过滤器条不饱满 | `.kc-filter-group-h` 删除 `max-width: 360px`，保留 `flex:1 1 200px` + `min-width:180px` | ✅ |
| ③ 七卡片排成 5+2 | `.kc-status-row` 默认改 `repeat(7,…)`；1460 断点补 `repeat(4,…)`；1140/760 断点不动 | ✅ |

**验证结果**：
- `npm run build` → ✓ built in 1.98s（EvidenceCenterPage chunk 正常产出 27.99 kB）
- `grep repeat(7|4|3|2)` 确认 1879 行默认 7 列、2127/2142/2161 行断点 4/3/2 列均生效
- `grep max-width: 360px` → 0 命中（过滤器封顶已移除）
- `.kc-main-grid > .kc-col:first-child .kc-col-body` 结构性选择器就位（第 2046 行）

**待浏览器人工核验**：三栏左列表铺满、过滤器条均分、7 卡片一行，以及 V10–V12 窄屏响应。
