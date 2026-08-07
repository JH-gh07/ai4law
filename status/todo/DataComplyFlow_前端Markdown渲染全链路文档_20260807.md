# DataComplyFlow 前端 Markdown 渲染全链路技术文档

> 编写日期：2026-08-07
> 覆盖范围：前端 Markdown 处理、渲染组件、后端后处理管线、实际数据流走通

---

## 一、总体架构概览

### 1.1 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 前端框架 | React | ^18.3.1 |
| Markdown→React 渲染 | react-markdown | ^10.1.0 |
| GFM 扩展（表格/任务列表等） | remark-gfm | ^4.0.1 |
| 路由 | react-router-dom | ^6.30.4 |
| 构建工具 | Vite | ^8.1.4 |
| 类型系统 | TypeScript | ^5.6.3 |
| 后端 Markdown 处理 | Python (re, dataclasses) | — |

### 1.2 核心渲染链路

```
后端 LLM 输出 (raw Markdown + {{CIT-xxx}} markers)
    │
    ├─ normalize_legal_markdown_structure()  ← 中文层级归一化
    ├─ apply_citation_policy()               ← 引用合规校验
    └─ convert_citation_markers()            ← {{CIT-xxx}} → [1][2][3] 脚注
           │
           ▼
    API 传输 → 前端接收
           │
           ▼
    normalizeMarkdownForRender()             ← 基础归一化 (\r\n→\n, ##补空格)
           │
           ▼
    CitationMarkdownRenderer                 ← ReactMarkdown + remarkGfm
           │
           ├─ p/li/blockquote/td/h1-h3       ← 自定义组件覆盖
           ├─ renderInlineCitationText()     ← 正则扫描 [N] / 【依据】
           ├─ CitationPopover                ← 悬浮卡片
           └─ CitationArticleDrawer          ← 条文抽屉
```

---

## 二、文件索引：前端渲染相关代码全表

### 2.1 核心 Markdown 渲染组件

| 文件 | 行数 | 核心职责 | 关键函数 |
|------|------|---------|---------|
| `frontend/src/components/citation/CitationMarkdownRenderer.tsx` | 381 | 中央 Markdown 渲染器，包装 ReactMarkdown，注入法律引用交互 | `renderInlineCitationText()`, `resolveAll()`, `buildResolvedCitation()`, `findCitationFromMap()`, `chineseNumberToInt()`, `extractArticleNo()`, `extractBasisItems()`, `isBasisOnlyParagraph()`, `isHighlightParagraph()` |
| `frontend/src/components/citation/CitationPopover.tsx` | 112 | 引用角标悬浮卡片：法规名称、条号、摘要、权威等级、置信度、治理状态 | — |
| `frontend/src/components/citation/CitationArticleDrawer.tsx` | 184 | 点击引用后右侧滑出的条文抽屉，展示完整法条原文及上下文 | — |

### 2.2 Fallback Markdown 归一化

| 文件 | 行数 | 核心职责 | 关键函数 |
|------|------|---------|---------|
| `frontend/src/lib/fallback-markdown.ts` | ~100 | 前端中文法律文本→标准 Markdown 归一化（后端等价物的前端版本） | `normalizeFallbackMarkdown()`, `explodePackedLine()`, `classifyBlock()` |

### 2.3 工作区 Shell（报告渲染入口）

| 文件 | 行数 | 核心职责 | 关键函数 |
|------|------|---------|---------|
| `frontend/src/components/workspace/WorkspaceShell.tsx` | 1494 | 主工作区组件，三面板布局，报告 Tab 渲染，资源预览分发 | `readResponseChapters()`, `buildFallbackPreviewSections()`, `buildSectionsFromArtifactPreview()`, `buildMarkdownTable()`, `normalizeMarkdownBasics()`, `normalizeFallbackMarkdownForRender()`, `normalizeMarkdownForRender()`, `escapeMarkdownCell()`, `parseCsvRows()`, `renderTextArtifactPreview()`, `renderTabSurface()` |

### 2.4 中间产物面板

| 文件 | 行数 | 核心职责 | 关键函数 |
|------|------|---------|---------|
| `frontend/src/components/workspace/AssessmentIntermediatesPanel.tsx` | ~450 | 渲染安全评估中间产物（10个子标签页：事实/路径/问题/差距/证据/SPI/供应商/材料/合规推理/报告） | `ReportTab()`, `DataTab()`, `IssueTab()` |

### 2.5 轨迹时间线

| 文件 | 行数 | 核心职责 | 关键函数 |
|------|------|---------|---------|
| `frontend/src/components/workspace/RunTranscript.tsx` | 137 | 执行轨迹时间线容器，SSE 事件监听，自动滚动 | — |
| `frontend/src/lib/trace-adapter.ts` | ~630 | 原始事件→语义节点聚合 | `adaptEvents()`, `semanticFromDetail()`, `formatDetailContent()` |
| `frontend/src/components/workspace/TraceNodeView.tsx` | — | 单节点渲染：色点、Badge、描述、耗时、Token 统计、展开块 | — |
| `frontend/src/components/workspace/TraceExpandableBlock.tsx` | — | 可折叠代码块，复制按钮，展开/折叠切换 | — |

### 2.6 报告中心

| 文件 | 行数 | 核心职责 | 关键函数 |
|------|------|---------|---------|
| `frontend/src/pages/ReportCenterPage.tsx` | — | 三栏布局：筛选树、Markdown 预览（520字截断）、追溯链接面板 | — |
| `frontend/src/lib/report-adapter.ts` | — | 聚合报告快照（artifact + moduleRun + issue + evidence），构建追溯链接列表（max 120） | `buildReportSnapshots()`, `buildTraceLinks()` |

### 2.7 入口与路由

| 文件 | 行数 | 核心职责 |
|------|------|---------|
| `frontend/src/main.tsx` | — | 入口，按 `?trace_probe=1` 参数分发 App 或 TraceProbeApp |
| `frontend/src/App.tsx` | — | React Router 路由定义，懒加载页面，Modal 编排 |

---

## 三、后端 Markdown 后处理管线

### 3.1 文件清单

| 文件 | 核心职责 | 关键函数 |
|------|---------|---------|
| `backend/common/llm/postprocess.py` | LLM 输出后处理：结构归一化、引用策略校验、引用标记转换 | `normalize_legal_markdown_structure()`, `apply_citation_policy()`, `convert_citation_markers()`, `strip_markdown_inline()`, `ensure_paragraph_citations()` |
| `backend/common/render/markdown_renderer.py` | ReportDocument 结构化块→Markdown 字符串 | `MarkdownRenderer.render()` |
| `backend/common/render/html_renderer.py` | ReportDocument→自包含 HTML（内联 CSS） | `HtmlRenderer.render()` |
| `backend/common/render/content_adapter.py` | 章节 Markdown→结构化 ReportDocument 块 | `ContentAdapter.from_chapters()`, `parse_markdown_blocks()` |
| `backend/common/render/report.py` | 报告文件生成工具函数 | `render_markdown_report()`, `render_docx_report()`, `render_docx_template()` |

### 3.2 `normalize_legal_markdown_structure()` 详解

**入口**：`postprocess.py` L50-105

**六阶段处理**：

| 阶段 | 函数/逻辑 | 作用 |
|------|----------|------|
| 0 | `_repair_pipeless_tables()` | 修复缺前导 `|` 的表格（LLM 常输出 `项目 | 内容` 而非 `| 项目 | 内容`） |
| 1 | `text.replace("\r\n", "\n")` 等 | 统一换行符、全角空格→半角、清除行尾空白 |
| 2 | `_explode_packed_line()` | 拆解挤压行：在第X章/一、/（一）前插入换行，将「依据」块独立分行 |
| 3 | `_classify_legal_block()` | 逐行分类为 heading / list_item / table_row / table_rule / paragraph / basis |
| 4 | `items` 遍历 + separator 逻辑 | 同类块间紧凑拼接（list_item 间 `\n`，table_row 间 `\n`），不同类型间 `\n\n` |
| 5 | `re.sub(r"\n{3,}", "\n\n", output)` | 压缩多余空行 |

**分类规则**（`_classify_legal_block`，L168-202）：

| 行模式 | 输出类型 | Markdown 格式 |
|--------|---------|-------------|
| `第X章...` | heading | `# 第X章...` |
| `一、...` | heading | `## 一、...` |
| `（一）...` | heading | `### （一）...` |
| `|...` | table_row / table_rule | 保持原样 |
| `\d+. ...` 或 `- ...` | list_item | 保持原样 |
| 已有 `#` 前缀 | heading | 保持原样 |
| `【依据：...】`（整行） | basis | 保持原样 |
| 其他 | paragraph | 保持原样 |

### 3.3 `apply_citation_policy()` 详解

**入口**：`postprocess.py` L247-327

**核心逻辑**：

1. 将 allowed_citations 列表归一化为 canonical key（去空格、书名号、括号，转小写）
2. 按 `\n\n` 分段
3. 对每段检测 claim_type：
   - `LEGAL_RULE`：匹配"依据《X》应当/必须/不得/禁止"或"《X》第Y条规定/要求"
   - `RISK_JUDGMENT`：匹配"经评估…为高风险"或"合规结论：是/为/系"
   - 否则 `NONE`
4. 检查 `【依据：...】` 块中每条引用是否在 allowed 集合中
   - `未检索到` / `未检索到相关法规` / `未检索到法规依据` → violation: `citation_placeholder`
   - 不在 allowed 集合中 → violation: `citation_not_allowed`
5. 如果是 LEGAL_RULE 或 RISK_JUDGMENT 但没有有效引用 → 追加 `【待核验：缺少法规依据】` + violation: `required_citation_missing`
6. 最终通过 `normalize_legal_markdown_structure()` 重新归一化

### 3.4 `convert_citation_markers()` 详解

**入口**：`postprocess.py` L330-348

**核心逻辑**：

1. 正则匹配 `{{CIT-xxx}}` 占位符
2. 通过 `CitationRegistry.assign_footnote_number()` 获取全局脚注编号
3. 替换为 `[1]` `[2]` `[3]` 格式
4. 同一 CIT ID 在多处出现时分配同一编号
5. 最后通过 `normalize_legal_markdown_structure()` 归一化

---

## 四、前端 CitationMarkdownRenderer 核心逻辑

### 4.1 组件结构

```
CitationMarkdownRenderer
├─ Props: markdown, taskId, moduleKey
├─ State:
│   ├─ citationMap: Record<string, CitationDetail>     ← 脚注映射 { "1": {...}, "2": {...} }
│   └─ resolvedBasisMap: Record<string, CitationDetail> ← 依据块解析结果
├─ Effects:
│   ├─ useEffect → fetchCitationMap(taskId)            ← 加载 citation_map.json
│   └─ useEffect → resolveAll()                        ← 批量解析未匹配的依据块
└─ Render:
    └─ ReactMarkdown
        ├─ remarkPlugins={[remarkGfm]}
        └─ components={{
              p, li, blockquote, td,   ← 注入 CitationPopover
              h1, h2, h3               ← 添加 workspace-legal-* class
           }}
```

### 4.2 `renderInlineCitationText()` 核心算法

**位置**：`CitationMarkdownRenderer.tsx` L167-245

**两步正则匹配**：

1. 扫描 `[数字]` 模式：
   - 正则：`/\[(\d+)\]/`
   - 匹配后查 `citationMap["N"]` → 渲染 `<CitationPopover>`

2. 扫描 `【依据：...】` 模式：
   - 正则：`/【依据：[^】]+】/`
   - 提取内容后调用 `extractBasisItems()` 拆分为数组
   - 逐条：
     - 先查本地 `citationMap`（按标题模糊匹配 + 条号精确匹配）
     - 未命中则查 `resolvedBasisMap`
     - 仍未命中则标记为 "待解析"
   - 渲染为 `<CitationPopover>` 列表

### 4.3 引用解析流程

```
citationMap (本地)
    │
    ├─ findCitationFromMap(title, articleNo)
    │     ├─ 步骤1: 遍历 citationMap 所有 values，模糊匹配标题
    │     │          (title.includes(citation.title) || citation.title.includes(title))
    │     │          且 articleNo 精确相等
    │     ├─ 步骤2: 如果 articleNo 为空，仅按标题模糊匹配
    │     └─ 步骤3: 都未匹配 → 返回 null
    │
    ├─ 本地命中 → 直接使用 citationMap 中的数据
    │
    └─ 本地未命中 → resolveAll()
          └─ fetchKnowledgeCitation(moduleKey, title, articleNo)
                └─ buildResolvedCitation() → 存入 resolvedBasisMap
```

---

## 五、前端 Fallback Markdown 归一化器

### 5.1 适用场景

仅当后端 chapters 数据不可用时，前端从 `findings` / `problems` / `citations` / `next_actions` 重建报告段落时使用。此时输入是结构化 JSON，需要渲染为 Markdown 表格，因此只需 `normalizeMarkdownBasics()` 处理基本格式。

`normalizeFallbackMarkdown()` 作为独立归一化器存在，用于处理非结构化中文法律文本，其逻辑与后端 `normalize_legal_markdown_structure()` 等价。

### 5.2 函数对照

| 前端函数 | 后端函数 | 功能 |
|---------|---------|------|
| `normalizeFallbackMarkdown()` | `normalize_legal_markdown_structure()` | 完整归一化管线 |
| `explodePackedLine()` | `_explode_packed_line()` | 拆解挤压行 |
| `classifyBlock()` | `_classify_legal_block()` | 行分类 |

### 5.3 三级报告重建优先级

```
WorkspaceShell.reconstructedReport
    │
    ├─ 优先级 1: response.chapters[{title, content}]
    │     → normalizeMarkdownForRender() (仅 basics)
    │     → CitationMarkdownRenderer
    │
    ├─ 优先级 2: buildFallbackPreviewSections()
    │     从 findings/problems/citations/next_actions 重组
    │     → normalizeFallbackMarkdownForRender() (深度归一化)
    │     → CitationMarkdownRenderer
    │
    └─ 优先级 3: buildSectionsFromArtifactPreview()
          从 artifact 文件列表读取预览
          → 直接用 preview.content
          → CitationMarkdownRenderer (如有 taskId) 或 ReactMarkdown (无 taskId)
```

---

## 六、资源预览扩展名分发

**入口**：`WorkspaceShell.renderTextArtifactPreview()` L907-998

| 扩展名 | 渲染方式 | 引用交互 |
|--------|---------|---------|
| `.csv` | `parseCsvRows()` 手写解析 → `<table>` | ❌ |
| `.json` | `JSON.parse()` → `<pre>` + `JSON.stringify(parsed, null, 2)` | ❌ |
| `.txt` | `<pre>` 原文 | ❌ |
| `.md` / `.markdown` | `CitationMarkdownRenderer`（有 taskId）或 `ReactMarkdown`（无 taskId） | 取决于 taskId |
| `.html` | `<iframe srcDoc={htmlContent}>` | ❌ 静态 |
| `.pdf` | `<iframe src={blobUrl}>`（浏览器原生 PDF 渲染） | ❌ |

---

## 七、中间产物面板渲染

**入口**：`AssessmentIntermediatesPanel.tsx`

**10 个子标签页**：

| Tab | dataKey | 渲染组件 | 表格列 |
|-----|---------|---------|--------|
| 事实识别 | `facts_json` | `DataTab` | 编号 / 来源类型 / 字段路径 / 值 / 置信度 |
| 路径判断 | `path_judgment_json` | `DataTab` | 推荐路径 / 风险等级 / 依据 / 路径警告 |
| 问题清单 | `issue_list_json` | `IssueTab` | 标题 / 严重度 / 建议措施（左表）+ 详情面板（右） |
| 差距项 | `gap_items_json` | `DataTab` | 领域 / 风险等级 / 差距描述 / 法律依据 / 建议 |
| 证据链 | `evidence_chain_json` | `DataTab` | 编号 / 主张 / 结论 / 置信度 / 关联事实 / 规则 |
| 敏感信息风险 | `spi_risks_json` | `DataTab` | 风险类型 / 等级 / 描述 |
| 供应商问题 | `vendor_issues_json` | `DataTab` | 问题类型 / 等级 / 描述 |
| 材料清单 | `material_checklist_json` | `DataTab` | 材料名称 / 状态 / 备注 |
| 合规推理 | `compliance_reasoning_json` | `DataTab` | 评估维度 / 事实状态 / 合理性 / 法律风险 / 建议表达 / 是否允许正面结论 |
| 报告输出 | `markdown` 文件 | `ReportTab` | `CitationMarkdownRenderer` 渲染 Markdown 正文 |

---

## 八、轨迹时间线渲染

### 8.1 事件流

```
SSE 事件流 (useTaskEvents)
    │
    ▼
adaptEvents() (trace-adapter.ts)
    │
    ├─ tool_start + tool_result → mergeTool() → 聚合为一个语义节点
    ├─ 独立事件 (status, facts_built, issues_built 等) → standaloneNode
    ├─ 缓冲 thought 事件 → attach 到最近节点
    └─ 按 correlation_id 关联
    │
    ▼
TraceNode[] → RunTranscript 渲染
    │
    ▼
TraceNodeView (每个节点)
    ├─ 阶段色点: PARSER=橙 RAG=蓝 GEN=紫 REVIEW=青
    ├─ Badge 标签
    ├─ 描述文本
    ├─ 耗时、Token 统计
    └─ TraceExpandableBlock (INPUT/OUTPUT 展开)
```

### 8.2 `semanticFromDetail()` 阶段推断规则

| 关键词 | 推断阶段 |
|--------|---------|
| retriev / RAG / search / query | `RAG` |
| parse / extract / fact | `PARSER` |
| chapter / gen / write / compose | `GEN` |
| review / check / validate / audit | `REVIEW` |
| issue / risk / assess | `REVIEW` |

---

## 九、实际数据流六阶段走通（安全评估模块）

### 阶段 0：用户输入 → 事实提取

**输入**：用户在 ModuleRunPanel 表单填写的数据 + 上传附件

**输出**：`facts.json` — 20 条结构化事实记录，每条含 `fact_id`, `source_type`, `field_path`, `value`, `confidence`, `evidence_status`

```json
{
  "fact_id": "FACT-request-company-name",
  "source_type": "schema",
  "field_path": "request.company_name",
  "value": "智慧云联科技（上海）有限公司",
  "confidence": 0.6,
  "evidence_status": "user_claim_only"
}
```

### 阶段 1：事实 → 法律检索 + 问题清单

**输出**：
- `issue_list.json` — 11 个问题项（3 HIGH, 2 MEDIUM, 1 LOW severity），每个关联 `fact_refs` 和 `rule_refs`
- `legal_grounding.json` — 逐 issue 5 条法规，含 `confidence_score`, `authority_level`, `binding_force`, `external_report_allowed`

### 阶段 2：事实 + 问题 + 法规 → 合规推理 + 写作策略

**输出**：
- `compliance_reasoning.json` — 8 维评估（KIIO认定/重要数据认定/合法性基础/必要性/接收方保障/告知同意/安全措施/数据主体权利），每维含 `fact_status`, `legal_risk`, `external_claim_allowed`
- `writing_strategy.json` — 逐 issue 内外表达策略 + 禁止用语列表 + tone 偏好

### 阶段 3：中间产物面板渲染

后端生成的全部中间文件（按 `generation_basis_pack.json` 索引），10 个子标签页在前端 `AssessmentIntermediatesPanel` 中渲染。

### 阶段 4：LLM 生成章节 → 后处理

**Step A**: `normalize_legal_markdown_structure()` — 修复缺前导 `|` 表格、中文层级归一化

**Step B**: `convert_citation_markers()` — `{{CIT-xxx}}` → `[1]` `[2]` `[3]`

**生成结果示例**（`.md` 中的实际段落）：

```markdown
## 三、出境必要性与合法性基础

### 第三章 出境必要性与合法性基础

#### 3.2 合法性基础

本次个人信息出境的合法性基础，主要援引《中华人民共和国个人信息保护法》第十三条第一款第二项。

此外，根据《个保法》第三十八条，个人信息处理者因业务等需要向境外提供个人信息的，应当具备下列条件之一：

### （一）通过国家网信部门组织的安全评估；
### （二）按照国家网信部门的规定经专业机构进行个人信息保护认证；
### （三）按照国家网信部门制定的标准合同与境外接收方订立合同；

鉴于本次出境涉及重要数据（依据 EVIDENCE-important-data-security-assessment），必须通过国家网信部门组织的安全评估。[1]
```

### 阶段 5：citation_map.json — 脚注映射

```json
{
  "footnote_map": {
    "1": {
      "citation_id": "CIT-CN-UNKNOWN-GEN-P01",
      "title": "数据出境安全管理政策问答（2025年4月）",
      "article_no": "六十二",
      "authority_level": "low",
      "confidence_score": 0.59
    },
    "2": {
      "title": "中华人民共和国个人信息保护法",
      "article_no": "一",
      "authority_level": "high",
      "confidence_score": 0.77
    }
  }
}
```

### 阶段 6：前端渲染 — 三路径汇合

#### 路径 A：主报告 Tab（`WorkspaceShell` → `activeTab === "report"`）

```
WorkspaceShell.renderTabSurface()
  ├─ reconstructedReport.sections[]  ← 三级优先级决策
  │     ├─ 优先: response.chapters[{title, content}]
  │     ├─ 降级: buildFallbackPreviewSections()
  │     └─ 兜底: buildSectionsFromArtifactPreview()
  │
  └─ 每个 section:
        normalizeMarkdownForRender(section.content)
        → CitationMarkdownRenderer(markdown, taskId, moduleKey)
           ├─ ReactMarkdown + remarkGfm → 组件树
           └─ renderInlineCitationText() → CitationPopover
```

**逐行渲染过程**：

1. **Markdown 归一化**：`\r\n` → `\n`，`##` 后补空格，`1)` → `1.`
2. **React 组件树构建**：`react-markdown` + `remark-gfm` 将 Markdown 转为 React 元素树，覆盖 `p`/`li`/`blockquote`/`td` 渲染以注入引用交互
3. **引用悬浮气泡**（`CitationPopover`）：鼠标悬停 `[2]` 时显示法规名称、条号、摘要（截断120字）、类型标签、权威标签、置信度百分比、治理状态
4. **条文抽屉**（`CitationArticleDrawer`）：点击引用后右侧滑出，展示完整条文原文（`exact_article` 类型）或法规概述（`source_overview` 类型）

#### 路径 B：资源预览 → 按扩展名分发

- CSV → `<table>`（手写 `parseCsvRows()` 解析器）
- JSON → `<pre>` + `JSON.stringify`
- Markdown/.md → `CitationMarkdownRenderer`（有 taskId 则启用引用交互）或 `ReactMarkdown`
- HTML → `<iframe srcDoc>`
- PDF → `<iframe src={blobUrl}>`

#### 路径 C：轨迹时间线（`RunTranscript`）

33 个原始事件 → `adaptEvents()` 聚合 → `TraceNodeView` 渲染，展示阶段色点、Badge、描述、耗时、Token 统计、INPUT/OUTPUT 展开块。

---

## 十、关键渲染差异总结

| 场景 | 渲染器 | 归一化函数 | 引用交互 |
|------|--------|-----------|---------|
| 主报告正文（chapters 路径） | `CitationMarkdownRenderer` | `normalizeMarkdownForRender()` (仅 basics) | ✅ 完整 |
| Fallback 报告（findings 重建） | `CitationMarkdownRenderer` | `normalizeFallbackMarkdownForRender()` (深度中文层级修复) | ✅ 完整 |
| 中间产物报告 Tab | `CitationMarkdownRenderer` | 无额外归一化 | ✅ 提取 taskId 后完整 |
| 资源预览 .md 文件 | `CitationMarkdownRenderer` 或 `ReactMarkdown` | 取决于是否有 taskId | 有 taskId 才启用 |
| 诊断报告 HTML | `<iframe srcDoc>` | 无 | ❌ 静态 |
| CSV 文件 | 自定义 `<table>` | `parseCsvRows()` | ❌ |
| JSON 文件 | `<pre>` | 无 | ❌ |
| PDF 文件 | `<iframe>` + blob URL | ❌ 静态 |

---

## 十一、样式文件

| 文件 | 内容 |
|------|------|
| `frontend/src/styles/app/workspace.css` | 工作区布局（glassmorphism 面板、浏览器标签页、报告段落间距） |
| `frontend/src/styles/app/pages.css` | 报告中心三栏布局 |
| `frontend/src/styles/app/product-pages-and-overrides.css` | 引用标记（`.citation-marker-inline`）、悬浮卡片、抽屉视觉样式 |
| `frontend/src/styles/tokens.css` | 全局设计令牌 |
