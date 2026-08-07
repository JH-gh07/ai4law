前端 Markdown 渲染体系全景表

一、渲染管线总览

Markdown 内容来源 → 预处理/归一化 → ReactMarkdown 核心渲染 → 引用增强层 → 样式层 → 用户可见输出

---
二、详细模块对照表

序号: A. Markdown 内容来源与重建
文件路径:
代码模块/函数:
功能逻辑:
────────────────────────────────────────
序号: 1
文件路径: frontend/src/components/workspace/WorkspaceShell.tsx
代码模块/函数: readResponseChapters() (L133-142)
功能逻辑: 从后端 JSON response 提取 chapters 数组（含 title + content），作为 Markdown
渲染的主输入源
────────────────────────────────────────
序号: 2
文件路径: frontend/src/components/workspace/WorkspaceShell.tsx
代码模块/函数: buildFallbackPreviewSections() (L268-331)
功能逻辑: 当 response 不含结构化 chapters 时，从 findings/problems/citations/next_actions
等散落字段重建 Markdown 段落，作为 fallback 输入
────────────────────────────────────────
序号: 3
文件路径: frontend/src/components/workspace/WorkspaceShell.tsx
代码模块/函数: buildSectionsFromArtifactPreview() (L333-343)
功能逻辑: 从已落盘的 artifact 文件预览中提取文字内容作为第三级 fallback
────────────────────────────────────────
序号: 4
文件路径: frontend/src/components/workspace/WorkspaceShell.tsx
代码模块/函数: buildMarkdownTable() (L150-159)
功能逻辑: 将结构化数据（findings 数组）动态拼接为 Markdown 表格字符串
────────────────────────────────────────
序号: 5
文件路径: frontend/src/components/workspace/WorkspaceShell.tsx
代码模块/函数: reconstructedReport (L407-435)
功能逻辑: 三级优先级决策：chapters > fallback sections > artifact preview，生成最终 Markdown
sections 数组

| B. Markdown 预处理 / 归一化 | | | |
| 6 | frontend/src/components/workspace/WorkspaceShell.tsx | normalizeMarkdownBasics() (L200-206) | 基础换行统一、标题 #后补空格、列表前缀归一化（1)→1.、•→-） |
| 7 | frontend/src/components/workspace/WorkspaceShell.tsx | normalizeFallbackMarkdownForRender() (L208-209) | 对 fallback 路径额外执行 normalizeFallbackMarkdown() |
| 8 | frontend/src/components/workspace/WorkspaceShell.tsx | normalizeMarkdownForRender() (L211-212) | 对章节内容仅做 basics 归一化，保留已有 Markdown 结构 |
| 9 | frontend/src/lib/fallback-markdown.ts | normalizeFallbackMarkdown() (L50-81) | 前端版 normalize_legal_markdown_structure：将松散中文法律文本（含"第一章"、"一、"、"（一）"等中文层级）自动转为标准 Markdown 标题/列表；处理紧贴行爆炸、依据块隔离、表格/列表紧凑换行 |
| 10 | frontend/src/lib/fallback-markdown.ts | explodePackedLine() (L12-22) | 将一行内紧贴的中文章节号、依据块、序号拆分为多行 |
| 11 | frontend/src/lib/fallback-markdown.ts | classifyBlock() (L24-48) | 对每行文本分类为 heading / list_item / table_row / table_rule / paragraph / basis |
| 12 | frontend/src/lib/fallback-markdown.ts | chineseNumberToInt() (L20-69) — 实际在 CitationMarkdownRenderer 中 | 将中文数字（一、二、十、百）转为阿拉伯数字，用于"第X条"的条号提取 |
| 13 | frontend/src/components/workspace/WorkspaceShell.tsx | escapeMarkdownCell() (L147-148) | 转义表格单元格中的 \| 和换行，防止破坏 Markdown 表格结构 |
| 14 | frontend/src/components/workspace/WorkspaceShell.tsx | parseCsvRows() (L214-260) | 手写 CSV 解析器（处理引号转义、换行内嵌），将 CSV 文本转为二维数组供表格渲染 |

| C. 核心 Markdown → React 渲染 | | | |
| 15 | frontend/src/components/citation/CitationMarkdownRenderer.tsx | <CitationMarkdownRenderer> (L259-381) | 主渲染入口组件：接收 markdown 字符串 + taskId，用 ReactMarkdown + remarkGfm 渲染，同时注入引用交互 |
| 16 | frontend/src/components/citation/CitationMarkdownRenderer.tsx | ReactMarkdown components 重写 (L327-371) | 逐一覆写 p、li、blockquote、td、h1、h2、h3 渲染逻辑，在文本节点中插入可交互的引用标记 |
| 17 | frontend/src/components/workspace/WorkspaceShell.tsx | renderTextArtifactPreview() (L907-998) | 按文件扩展名分发渲染策略：CSV→表格、JSON→<pre>、TXT→<pre>、其他（md/markdown）→ CitationMarkdownRenderer |
| 18 | frontend/src/components/workspace/WorkspaceShell.tsx | activeTab === "report" 分支 (L1186-1321) | 主报告 Tab：逐 section 遍历，每段调用 CitationMarkdownRenderer，可选切到 PDF 视图 |
| 19 | frontend/src/components/workspace/AssessmentIntermediatesPanel.tsx | ReportTab() (L163-187) | 评估中间产物面板的报告 Tab：从 outputFiles 路径提取 taskId，调用 CitationMarkdownRenderer 渲染 |
| 20 | frontend/package.json | react-markdown: ^10.1.0 + remark-gfm: ^4.0.1 | 底层依赖：react-markdown（Markdown→React 组件树）、remark-gfm（表格/删除线/任务列表等 GFM 扩展语法） |

| D. 引用（Citation）增强层 | | | |
| 21 | frontend/src/components/citation/CitationMarkdownRenderer.tsx | renderInlineCitationText() (L167-245) | 核心引用注入函数：遍历文本，用正则匹配 [1] 脚注编号和 【依据：...】 依据块，替换为带 hover popover 的 <span> |
| 22 | frontend/src/components/citation/CitationMarkdownRenderer.tsx | fetchCitationMap() + citationMap state (L264-269) | 组件挂载时通过 API 拉取 taskId 对应的引用映射表 {footnoteNumber → CitationDetail} |
| 23 | frontend/src/components/citation/CitationMarkdownRenderer.tsx | findCitationFromMap() (L104-120) | 在本地 citationMap 中模糊匹配法规标题（compact 后 substring 比较）并尝试精确条号匹配 |
| 24 | frontend/src/components/citation/CitationMarkdownRenderer.tsx | resolveAll() (L286-311) | 对本地匹配失败的依据项，批量调用 fetchKnowledgeCitation() 服务端接口做远程解析 |
| 25 | frontend/src/components/citation/CitationMarkdownRenderer.tsx | buildResolvedCitation() (L122-165) | 将服务端返回的 matched 信息构造为临时 CitationDetail，标记为 source_overview resolution |
| 26 | frontend/src/components/citation/CitationMarkdownRenderer.tsx | isBasisOnlyParagraph() (L92-94) | 检测整段是否全部为【依据】块，用于特殊 CSS class |
| 27 | frontend/src/components/citation/CitationMarkdownRenderer.tsx | isHighlightParagraph() (L96-102) | 检测段落是否为结论/风险/建议高亮段，匹配中文前缀模式 |
| 28 | frontend/src/components/citation/CitationPopover.tsx | <CitationPopover> | 悬浮气泡组件：展示引用标题、条号、原文摘录（截断120字）、类型徽章、权威等级、置信度、治理状态（可对外引用/待验证/禁止） |
| 29 | frontend/src/components/citation/CitationArticleDrawer.tsx | <CitationArticleDrawer> | 侧边抽屉组件：点击引用后展示完整条文，支持加载上文/下文、跳转知识库全文、查看官方发布版本 |
| 30 | frontend/src/components/citation/CitationArticleDrawer.tsx | fetchArticleDetail() + resolution 分支 (L43-69) | 按 resolutionType 分支：exact_article→拉取条文原文；source_overview→展示法规级定位说明；external_verified→提示待入库 |
| 31 | frontend/src/components/citation/CitationMarkdownRenderer.tsx | extractBasisItems() (L79-85) | 拆分 【依据：A；B；C】 为数组，过滤占位符（"未检索到"） |
| 32 | frontend/src/components/citation/CitationMarkdownRenderer.tsx | shortenCitationLabel() (L87-90) | 生成长格式引用标签：《法规名》 第X条 |
| 33 | frontend/src/components/citation/CitationMarkdownRenderer.tsx | extractArticleNo() (L72-77) | 从中文依据文本中提取"第X条"的条号数字 |

| E. 执行轨迹（Trace）渲染 | | | |
| 34 | frontend/src/components/workspace/RunTranscript.tsx | <RunTranscript> | SSEManager 事件流 → adaptEvents() → TraceNodeView 时间线渲染；自动滚动到底部 |
| 35 | frontend/src/lib/trace-adapter.ts | adaptEvents() (L539-630) | 事件→语义节点聚合器：将 tool_start/tool_result 配对、处理 thought 缓冲、关联 correlation_id，输出 TraceNode[] |
| 36 | frontend/src/lib/trace-adapter.ts | createEventToSemantic() (L19-31) | 事件类型 → 语义映射（stage: Task/LLM/RAG/Tool/Parser/Generator/Review） |
| 37 | frontend/src/lib/trace-adapter.ts | semanticFromDetail() (L178-280) | 基于 detail 内容二次推断：根据 tool/agent/raw_name 字符串匹配中英文关键词（retriev→RAG、parse→PARSER、chapter→GEN 等） |
| 38 | frontend/src/lib/trace-adapter.ts | formatDetailContent() (L116-162) | 将 detail JSON 展开为可读的多行文本（按优先级排序 key、截断数组、缩进嵌套对象） |
| 39 | frontend/src/components/workspace/TraceNodeView.tsx | <TraceNodeView> | 单个轨迹节点的视觉渲染：stage 彩色圆点、badge 标签、描述、耗时、token 统计、input/output 展开块 |
| 40 | frontend/src/components/workspace/TraceExpandableBlock.tsx | <TraceExpandableBlock> | 可折叠代码块：label 标签、一键复制、展开/收起长内容 |
| 41 | frontend/src/lib/trace-i18n.ts | getTraceI18n() / getTraceLocale() | 轨迹渲染的中英文国际化文案（action 名称、字段前缀等） |

| F. 其他渲染模式（CSV / JSON / TXT / HTML / PDF） | | | |
| 42 | frontend/src/components/workspace/WorkspaceShell.tsx | CSV 分支 (L912-950) | 调用 parseCsvRows 解析后渲染为 <table>，最多预览 200 行 |
| 43 | frontend/src/components/workspace/WorkspaceShell.tsx | JSON 分支 (L953-969) | JSON.parse 后 JSON.stringify(parsed, null, 2) 美化输出到 <pre> |
| 44 | frontend/src/components/workspace/WorkspaceShell.tsx | HTML 分支 (L1301-1303) | 通过 <iframe srcDoc={content} sandbox> 内嵌渲染后端生成的完整 HTML 报告 |
| 45 | frontend/src/components/common/PdfViewer.tsx | <PdfViewer> | 通过 fetchArtifactBlob 获取 PDF blob → URL.createObjectURL → <iframe> 内嵌预览；支持 loading/error/retry 三态 + 请求去重 |
| 46 | frontend/src/components/workspace/WorkspaceShell.tsx | renderTextArtifactPreview() (L907-998) | 扩展名分发器：csv/json/txt → 各自预览；md/markdown → CitationMarkdownRenderer（带引用交互）vs 纯 ReactMarkdown（无引用） |

| G. 报告中心（ReportCenterPage）渲染 | | | |
| 47 | frontend/src/pages/ReportCenterPage.tsx | readChapters() (L13-22) | 从 ModuleRun response 中提取 chapters（最多 8 个），截断 content 到 520 字符用于预览 |
| 48 | frontend/src/pages/ReportCenterPage.tsx | buildReportSnapshots() (L38-55, 调用自 report-adapter.ts) | 将 state 中的 artifacts + moduleRuns + issues + evidenceHits 聚合为报告快照列表 |
| 49 | frontend/src/lib/report-adapter.ts | buildTraceLinks() (L57-105) | 从 moduleRuns/issues/evidenceHits 构建追溯链接列表（最多 120 条） |
| 50 | frontend/src/components/report-center/ReportTaskTreeSidebar.tsx | <ReportTaskTreeSidebar> | 报告侧边树：按任务空间分组、文档标题可点击选择、空状态提示 |

| H. 工作区布局与 Tab 调度 | | | |
| 51 | frontend/src/components/workspace/WorkspaceShell.tsx | renderTabSurface() (L1001-1323) | Tab 渲染总调度器：details→StageSplitView、canvas→工作流画布、docs→模板说明、terminal→日志、timeline→RunTranscript、report→Markdown+PDF、资源Tab→各类型预览 |
| 52 | frontend/src/components/workspace/StageSplitView.tsx | <StageSplitView> | 运行面板包装器：显示模块运行状态徽章，嵌入 ModuleRunPanel |
| 53 | frontend/src/components/workspace/ResourcePanel.tsx | <ResourcePanel> | 左侧资源面板：展示工作区的输入/输出文件树，支持点击打开资源 Tab |

| I. 样式层 | | | |
| 54 | frontend/src/styles/app/workspace.css | CSS 变量 + workspace-* 系列 class | 工作区 UI 样式：background/glassmorphism 效果、Tab 栏、报告章节间距、引用标记样式 |
| 55 | frontend/src/styles/app/pages.css | report-review-* / report-preview-* 系列 | 报告中心的列表/预览/追溯链路三栏布局样式 |
| 56 | frontend/src/styles/app/product-pages-and-overrides.css | citation-* 系列 | 引用标记（上标按钮）、悬浮气泡、抽屉面板的视觉样式 |
| 57 | frontend/src/styles/tokens.css | CSS 自定义属性 | 全局设计 token（颜色、间距、字体层级） |

| J. 后端 Markdown 生成（供前端消费） | | | |
| 58 | backend/common/render/markdown_renderer.py | MarkdownRenderer.render() | 将 ReportDocument（结构化报告模型）渲染为 Markdown 字符串，按 heading/paragraph/list/table/divider 递归 |
| 59 | backend/common/render/report.py | render_markdown_report() | 简易 Markdown 报告生成：取 title + sections → # title + ## section_header + content |
| 60 | backend/common/render/html_renderer.py | HtmlRenderer.render() | 将 ReportDocument 渲染为独立 HTML 页面（含内嵌 CSS、inline <strong>/<code> 转换） |
| 61 | backend/common/render/content_adapter.py | ContentAdapter.from_chapters() | 将 chapter 数组适配为 ReportDocument → parse_markdown_blocks 解析每章 content 为结构化 block |
| 62 | backend/common/render/content_adapter.py | parse_markdown_blocks() | 将 Markdown 字符串解析为 Paragraph/HeadingBlock/ListBlock/TableBlock/DividerBlock 对象数组 |
| 63 | backend/common/llm/postprocess.py | normalize_legal_markdown_structure() | 后端版法律 Markdown 归一化：处理中文章节号、修复缺前导 \| 的表格、【依据】 块独立成行 |
| 64 | backend/common/llm/postprocess.py | apply_citation_policy() | 引用合规校验：检查段落中的 【依据】 是否在 allowed_citations 中、高风险主张是否缺少法规依据 |
| 65 | backend/common/llm/postprocess.py | convert_citation_markers() | 将 LLM 生成的 {{CIT-xxx}} 标记转换为全局统一的 [1] [2] 脚注编号 |

---
三、数据流示意

后端 AI 生成
  │
  ├─ LLM 输出原始 Markdown（含 {{CIT-xxx}} 引用标记）
  │     │
  │     ├─ postprocess.normalize_legal_markdown_structure()    ← 中文章节修复
  │     ├─ postprocess.convert_citation_markers()              ← {{CIT}}→[1]
  │     └─ postprocess.apply_citation_policy()                 ← 引用合规校验
  │
  ├─ content_adapter.ContentAdapter.from_chapters()            ← 结构化适配
  │     └─ parse_markdown_blocks() → ReportDocument
  │
  └─ 多重渲染输出:
        ├─ MarkdownRenderer → .md 文件
        ├─ HtmlRenderer → 独立 .html
        ├─ DOCX 渲染 → .docx
        └─ PDF 渲染 → .pdf

────────────────────────── 网络传输 ──────────────────────────

前端接收
  │
  ├─ ModuleRun.response.chapters[{title, content}]    ← 主要输入
  │     或
  ├─ buildFallbackPreviewSections()                   ← fallback 重建
  │
  ├─ normalizeMarkdownForRender()                     ← 基础归一化
  │     或
  ├─ normalizeFallbackMarkdownForRender()             ← 深度归一化（中文层级→Markdown）
  │
  ├─ CitationMarkdownRenderer                        ← 核心渲染
  │     ├─ ReactMarkdown + remarkGfm                 ← Markdown→React
  │     ├─ renderInlineCitationText()                 ← 注入引用标记
  │     │     ├─ [1] → CitationPopover                ← 悬浮详情
  │     │     └─ 【依据】→ CitationPopover             ← 依据交互
  │     └─ CitationArticleDrawer                      ← 点击展开条文
  │
  └─ 按扩展名分发其他渲染:
        ├─ CSV  → <table>
        ├─ JSON → <pre>
        ├─ HTML → <iframe>
        └─ PDF  → <iframe> (blob URL)

---
四、关键依赖

┌──────────────────┬─────────┬────────────────────────────────────────────────────────────────┐
│       依赖       │  版本   │                              用途                              │
├──────────────────┼─────────┼────────────────────────────────────────────────────────────────┤
│ react-markdown   │ ^10.1.0 │ Markdown → React 组件树的核心引擎                              │
├──────────────────┼─────────┼────────────────────────────────────────────────────────────────┤
│ remark-gfm       │ ^4.0.1  │ 增强 GitHub Flavored Markdown 支持（表格、任务列表、删除线等） │
├──────────────────┼─────────┼────────────────────────────────────────────────────────────────┤
│ react-router-dom │ ^6.30.4 │ 前端路由（知识库链接跳转、页面导航）                           │
├──────────────────┼─────────┼────────────────────────────────────────────────────────────────┤
│ Vite             │ ^8.1.4  │ 构建工具，生产环境代码分割各页面为独立 chunk                   │
└──────────────────┴─────────┴────────────────────────────────────────────────────────────────┘

✻ Crunched for 1m 58s

❯ 有没有实际已有的运行的实际的渲染的各个阶段数据流真实示例

  Thought for 17s, read 9 files

以下是以 安全评估 (assessment) 模块为例的实际六阶段数据流完整走通示例：

---
真实数据流六阶段走通

阶段 0：用户输入 → 事实提取

触发入口：用户在 ModuleRunPanel 填写表单，点击"执行"

输入（用户在 wizard 中填写的表单数据）：

┌──────────────────┬─────────────────────────────────────────┐
│       字段       │                   值                    │
├──────────────────┼─────────────────────────────────────────┤
│ 企业名称         │ 智慧云联科技（上海）有限公司            │
├──────────────────┼─────────────────────────────────────────┤
│ 行业             │ 云计算与数据服务 / 中外合资             │
├──────────────────┼─────────────────────────────────────────┤
│ 出境目的         │ 全球统一客户服务、集中化风险分析与建模… │
├──────────────────┼─────────────────────────────────────────┤
│ 接收方国家       │ 新加坡                                  │
├──────────────────┼─────────────────────────────────────────┤
│ 普通个人信息规模 │ 1,200,000 人                            │
├──────────────────┼─────────────────────────────────────────┤
│ 敏感个人信息规模 │ 15,000 人                               │
├──────────────────┼─────────────────────────────────────────┤
│ 是否涉及重要数据 │ 是                                      │
├──────────────────┼─────────────────────────────────────────┤
│ 上传文件         │ review_case_scc_contract.docx           │
└──────────────────┴─────────────────────────────────────────┘

后端输出：facts.json — 将表单字段 + 诊断结果 + 文档解析结果统一提取为结构化事实：

// facts.json (20 条事实记录)
{
  "fact_id": "FACT-request-company-name",
  "source_type": "schema",
  "field_path": "request.company_name",
  "value": "智慧云联科技（上海）有限公司",
  "confidence": 0.6,
  "evidence_status": "user_claim_only"
}

{
  "fact_id": "FACT-diagnosis-result-recommended-path",
  "source_type": "diagnosis",
  "field_path": "diagnosis_result.recommended_path",
  "value": "security_assessment",
  "confidence": 1.0,
  "evidence_status": "documented_evidence"
}

{
  "fact_id": "FACT-attachment-note-1",
  "source_type": "attachment",
  "value": "…个人信息出境标准合同…法律文件缺少以下核心条款：违约责任。",
  "confidence": 0.8,
  "evidence_status": "partial_evidence"
}

---
阶段 1：事实 → 法律检索 + 问题清单

后端流程：
- fact_builder → retriever (RAG 语义检索) → legal_grounding (逐 issue 检索法规)
- issue_builder (基于事实 + 规则匹配 + LLM 判断，生成 11 个问题项)

输出：issue_list.json

// issue_list.json (11 个问题，选出 3 个示例)
[
  {
    "issue_id": "ISSUE-important-data-security-assessment",
    "title": "重要数据触发高风险路径",
    "severity": "HIGH",
    "recommended_action": "[confirmed_issue] 补充重要数据识别依据、目录映射和出境必要性说明。",
    "fact_refs": ["FACT-request-contains-important-data"],
    "rule_refs": ["diagnosis:important_data", "CN-LAW-001", "CN-QA-012", "CN-LAW-003"]
  },
  {
    "issue_id": "ISSUE-pii-threshold",
    "title": "个人信息规模达到安全评估阈值",
    "severity": "HIGH",
    "fact_refs": ["FACT-request-pii-count"]
  },
  {
    "issue_id": "ISSUE-recipient-security-evidence-missing",
    "title": "境外接收方安全保障能力证明不足",
    "severity": "HIGH"
  },
  // ... 其余 8 个
]

输出：legal_grounding.json — 每个 issue 关联 5 条法规（从 CN-LAW-001 / CN-LAW-003 / CN-REG-004 / CN-QA-012 / CN-GUIDE-009 知识库检索），每条带置信度、权威等级、约束力、是否允许对外引用：

// legal_grounding.json — ISSUE-important-data-security-assessment 的 5 条法规
{
  "rule_id": "CN-LAW-003",
  "title": "中华人民共和国个人信息保护法",
  "article": "第一条",
  "confidence_score": 0.77,
  "authority_level": "high",
  "binding_force": "mandatory",
  "can_enter_external_report": true
},
{
  "rule_id": "CN-GUIDE-009",
  "title": "数据出境安全评估申报指南（第三版）",
  "confidence_score": 0.14,
  "authority_level": "low",
  "binding_force": "recommended",
  "confidence_passed": false,        ← 低于阈值 0.30
  "external_report_allowed": false   ← 禁止进入对外报告！
}

---
阶段 2：事实 + 问题 + 法规 → 合规推理 + 写作策略

输出：compliance_reasoning.json — 对 8 个评估维度逐个判断事实状态和风险：

// compliance_reasoning.json — 「重要数据认定」维度的完整推理
{
  "target": "重要数据认定",
  "fact_status": "user_claim_only",         // → 仅有用户自述
  "reasonableness": "方向明确但缺少分类分级支撑",
  "legal_risk": "如果实际涉及重要数据但未申报安全评估，数据出境行为可能违法",
  "correct_expression": "用户声明不涉及重要数据，但建议完成数据分类分级并取得主管部门确认后再行申报。",
  "external_claim_allowed": false,          // → 不可对外做正面结论
  "related_issue_ids": ["ISSUE-spi-classification-uncertain"]
}

同时生成 compliance_reasoning.md（人类可读的表格版本，见阶段 3 中间产物面板）。

输出：writing_strategy.json — 每个 issue 的内外表达策略 + 禁止用语：

{
  "issue_id": "ISSUE-recipient-security-evidence-missing",
  "internal_expression": "当前材料对境外接收方的数据安全管理制度…描述不足，无法充分证明其保障能力。",
  "external_expression": "当前材料已对境外接收方基本情况作出说明，但其数据安全管理制度…仍有待进一步补充。",
  "forbidden_expressions": [
    "完全合规", "材料齐备", "无风险", "已充分证明", "必然合法",
    "接收方具备充分安全保障能力",   ← issue 独有的禁用词
    "接收方完全符合数据安全要求"
  ],
  "tone": "conservative"
}

---
阶段 3：中间产物面板渲染（前端 AssessmentIntermediatesPanel）

后端生成的全部中间文件（按 generation_basis_pack.json 索引）：

outputs/assessment/fresh-assessment-deepseek/outputs/
├── facts.json                ← 事实提取
├── path_judgment.json        ← 路径判断
├── issue_list.json           ← 问题清单（11项）
├── evidence_chain.json       ← 证据链
├── legal_grounding.json      ← 逐 issue 法规检索
├── compliance_reasoning.json ← 合规推理
├── compliance_reasoning.md   ← 合规推理 Markdown 版
├── writing_strategy.json     ← 写作策略
├── material_checklist.json   ← 材料清单
├── citation_map.json         ← 引用映射（脚注编号→法规详情）
└── trace_manifest.json       ← 33 步执行轨迹清单

前端渲染 (AssessmentIntermediatesPanel.tsx)：根据 SUB_TABS 数组渲染 10 个子标签页：

┌──────────┬────────────────────┬────────────────────────────────────────────────────┬───────┐
│   Tab    │      dataKey       │                      渲染方式                      │ 代码  │
│          │                    │                                                    │ 位置  │
├──────────┼────────────────────┼────────────────────────────────────────────────────┼───────┤
│ 事实识别 │ facts_json         │ DataTab —                                          │ L281- │
│          │                    │ 通用表格（编号/来源类型/字段路径/值/置信度）       │ 331   │
├──────────┼────────────────────┼────────────────────────────────────────────────────┼───────┤
│ 路径判断 │ path_judgment_json │ DataTab — 表格（推荐路径/风险等级/依据/路径警告）  │ 同上  │
├──────────┼────────────────────┼────────────────────────────────────────────────────┼───────┤
│ 问题清单 │ issue_list_json    │ IssueTab — 左侧表格 +                              │ L346- │
│          │                    │ 右侧详情面板（描述/建议措施/关联事实/规则/证据）   │ 433   │
├──────────┼────────────────────┼────────────────────────────────────────────────────┼───────┤
│ 差距项   │ gap_items_json     │ DataTab —                                          │ 同上  │
│          │                    │ 表格（领域/风险等级/差距描述/法律依据/建议）       │       │
├──────────┼────────────────────┼────────────────────────────────────────────────────┼───────┤
│ 证据链   │ evidence_chain_jso │ DataTab —                                          │ 同上  │
│          │ n                  │ 表格（编号/主张/结论/置信度/关联事实/规则）        │       │
├──────────┼────────────────────┼────────────────────────────────────────────────────┼───────┤
│ 敏感信息 │ spi_risks_json     │ DataTab                                            │ 同上  │
│ 风险     │                    │                                                    │       │
├──────────┼────────────────────┼────────────────────────────────────────────────────┼───────┤
│ 供应商问 │ vendor_issues_json │ DataTab                                            │ 同上  │
│ 题       │                    │                                                    │       │
├──────────┼────────────────────┼────────────────────────────────────────────────────┼───────┤
│ 材料清单 │ material_checklist │ DataTab                                            │ 同上  │
│          │ _json              │                                                    │       │
├──────────┼────────────────────┼────────────────────────────────────────────────────┼───────┤
│ 规则分析 │ compliance_reasoni │ DataTab — 9 列表格（评估维度/事实状态/合理性/法律  │ 同上  │
│ 结论     │ ng_json            │ 风险/建议表达/是否允许正面结论）                   │       │
├──────────┼────────────────────┼────────────────────────────────────────────────────┼───────┤
│ 报告输出 │ markdown (即 .md   │ ReportTab — CitationMarkdownRenderer 渲染 Markdown │ L163- │
│          │ 文件)              │  正文，带引用交互                                  │ 187   │
└──────────┴────────────────────┴────────────────────────────────────────────────────┴───────┘

compliance_reasoning.md 在前端的最终预览（ReportTab 通过 CitationMarkdownRenderer 渲染）：

合规推理说明

| 评估维度 | 事实状态 | 合理性 | 法律风险 | 对外表达策略 |
|---------|---------|--------|---------|------------|
| 关键信息基础设施运营者认定 | user_claim_only | 方向明确但缺少外部证据佐证… | 如果实际属于CIIO但未申报… | 不可正面肯定 |
| 重要数据认定 | user_claim_only | 方向明确但缺少分类分级支撑… | 如果实际涉及重要数据… | 不可正面肯定 |

### 逐项详细说明

### 重要数据认定
- **事实状态**: user_claim_only
- **法律风险**: 如果实际涉及重要数据但未申报安全评估，数据出境行为可能违法
- **是否允许正面结论**: 否
- **关联问题**: ISSUE-spi-classification-uncertain

---
阶段 4：LLM 生成章节 → normalize_legal_markdown_structure → 引用转换

后端 chapter_generator 按 section 生成 Markdown，经过两个后处理：

Step A: postprocess.normalize_legal_markdown_structure()
→ 修復缺前导 | 的表格、中文层级（第一章→#，一、→##，1.→1. list）独立依据块

Step B: postprocess.convert_citation_markers() → {{CIT-xxx}} → [1] [2] [3]

生成结果（.md 文件中的实际段落）：

## 三、出境必要性与合法性基础

### 第三章 出境必要性与合法性基础

#### 3.1 业务必要性论证

本次数据出境旨在服务于"全球统一客户服务、集中化风险分析与建模…"等业务目的。

风险与说明：当前关于"技术架构与成本最优"的论述较为概括，未能充分论证为何无法通过境内部署同类系统或采用其他技术方案实现相同业务目标。根据问题清单 ISSUE-necessity-argument-generic 的提示，出境必要性论证可能过于泛化，不足以支撑严格的必要性审查。

#### 3.2 合法性基础

本次个人信息出境的合法性基础，主要援引《中华人民共和国个人信息保护法》第十三条第一款第二项。

此外，根据《个保法》第三十八条，个人信息处理者因业务等需要向境外提供个人信息的，应当具备下列条件之一：

### （一）通过国家网信部门组织的安全评估；
### （二）按照国家网信部门的规定经专业机构进行个人信息保护认证；
### （三）按照国家网信部门制定的标准合同与境外接收方订立合同；

鉴于本次出境涉及重要数据（依据 EVIDENCE-important-data-security-assessment），必须通过国家网信部门组织的安全评估。{{CIT-CN-EXPORT-ASSESSMENT-ART1-P01}}

可以看到 LLM 生成的原始章节混合含 {{CIT-xxx}} 占位标记、中文章节号、ISSUE-xxx 引用、EVIDENCE-xxx 引用。

---
阶段 5：citation_map.json — 脚注映射

后端 citation_builder 汇总全章节的引用，建立 footnote_map：

{
  "footnote_map": {
    "1": {
      "citation_id": "CIT-CN-UNKNOWN-GEN-P01",
      "source_id": "CN-QA-012",
      "title": "数据出境安全管理政策问答（2025年4月）",
      "article_no": "六十二",
      "authority_level": "low",
      "binding_force": "reference",
      "confidence_score": 0.59,
      "can_enter_external_report": true,
      "external_report_allowed": true
    },
    "2": {
      "citation_id": "CIT-CN-PIPL-GEN-P01",
      "title": "中华人民共和国个人信息保护法",
      "article_no": "一",
      "authority_level": "high",
      "binding_force": "mandatory",
      "confidence_score": 0.77
    },
    "3": {
      "title": "中华人民共和国网络安全法（2025修正）",
      "article_no": "十三",
      "authority_level": "high",
      "binding_force": "mandatory",
      "confidence_score": 0.58
    }
  }
}

---
阶段 6：前端渲染 — 三路径汇合

路径 A：主报告 Tab（WorkspaceShell → activeTab === "report"）

WorkspaceShell.renderTabSurface()
  ├─ reconstructedReport.sections[]   ← 三级优先级决策
  │     ├─ 优先: response.chapters[{title, content}]
  │     ├─ 降级: buildFallbackPreviewSections() 从 findings 重建
  │     └─ 兜底: buildSectionsFromArtifactPreview() 从 artifact 文件
  │
  └─ 每个 section 渲染:
        <CitationMarkdownRenderer
          markdown={normalizeMarkdownForRender(section.content)}
          taskId={reconstructedReport.citationTaskId}
          moduleKey={taskSpace.module}
        />

逐行渲染过程（以实际生成的报告段落为例）：

Step 1: Markdown 归一化 (normalizeMarkdownBasics)

原始:
  "## 三、出境必要性与合法性基础\r\n\r\n### 第三章..."
↓
归一化:
  "## 三、出境必要性与合法性基础\n\n### 第三章..."
- \r\n → \n
- ## 后补空格
- 1) → 1.

注意这里用的是 normalizeMarkdownForRender()（仅 basics），因为 LLM 生成的 chapters 已有良好的 Markdown 结构。normalizeFallbackMarkdown() 只在 fallback 重建路径使用（需要将松散中文文本转为 Markdown）。

Step 2: React 组件树构建 (ReactMarkdown + remarkGfm)

react-markdown 将以下 Markdown：
## 三、出境必要性与合法性基础

### 第三章 出境必要性与合法性基础

#### 3.1 业务必要性论证

本次数据出境旨在服务于"全球统一客户服务…"等业务目的。…根据问题清单 ISSUE-necessity-argument-generic 的提示，出境必要性论证可能过于泛化，不足以支撑严格的必要性审查。【依据：《数据出境安全评估办法》；《个保法》】

#### 3.2 合法性基础

本次个人信息出境的合法性基础，主要援引《中华人民共和国个人信息保护法》[2] 第十三条第一款第二项。

鉴于本次出境涉及重要数据，必须通过国家网信部门组织的安全评估。[1]

转换为 React 树：
<h2 className="workspace-legal-h2">三、出境必要性与合法性基础</h2>
<h3 className="workspace-legal-h3">第三章 出境必要性与合法性基础</h3>
<h4>3.1 业务必要性论证</h4>
<p className="workspace-legal-basis-block">
  "本次数据出境旨在服务于…不足以支撑严格的必要性审查。"
  <span className="citation-marker-inline">  ← 【依据】被替换
    <CitationPopover footnoteNumber={1} citation={...} label="《数据出境安全评估办法》 第1条" />
  </span>
</p>
<h4>3.2 合法性基础</h4>
<p>
  "本次个人信息出境的合法性基础，主要援引《中华人民共和国个人信息保护法》"
  <span className="citation-marker-inline">  ← [2] 被替换
    <CitationPopover footnoteNumber={2} citation={...} />
  </span>
  " 第十三条第一款第二项。"
</p>
<p>
  "鉴于本次出境涉及重要数据，必须通过国家网信部门组织的安全评估。"
  <span className="citation-marker-inline">  ← [1] 被替换
    <CitationPopover footnoteNumber={1} citation={...} />
  </span>
</p>

关键正则匹配（renderInlineCitationText 中）：
- \[2\] → 匹配脚注编号，查 citationMap["2"] → {title: "个人信息保护法", article_no: "一", authority_level: "high"}
- 【依据：…】 → 匹配依据块 → 拆分 ； → 逐条查 citationMap 或远程解析

Step 3: 引用悬浮气泡（CitationPopover）

鼠标悬停 [2] 时渲染：

┌─────────────────────────────────────────┐
│ 中华人民共和国个人信息保护法  第一条    │
│ "保护个人信息权益…"                    │  ← quote_text 截断 120 字
│ [法律条文] [高权威]                      │  ← citation_type + authority_level
│ ✅ 可对外引用                           │  ← governance 状态
│ L1 法规证据层                            │  ← source_kind
└─────────────────────────────────────────┘

Step 4: 点击引用 → 抽屉面板（CitationArticleDrawer）

点击 [2] → 弹出右侧抽屉：
- resolutionType === "exact_article" → 调用 fetchArticleDetail("CN-LAW-003", "1") 获取条文字段
- 展示：上文（第0条？不展示）、当前条文正文、下文
- 底部按钮："在知识库中继续阅读"（跳转 /knowledge/laws/CN-LAW-003）

点击 【依据：《数据出境安全评估办法》】：
- resolutionType === "source_overview"（因为本地 citationMap 仅匹配到法规来源，条号未确认）
- 显示："当前为法规来源级定位 — 引用未提供条号，当前只能定位到法规来源。"
- 底部按钮："查看法规概览"

---
路径 B：资源预览 → 按扩展名分发

B1: CSV 表格预览

// WorkspaceShell.renderTextArtifactPreview() → CSV 分支 (L912-950)
const rows = parseCsvRows(content);  // 手写 CSV 解析器
return (
  <table className="workspace-data-table">
    <thead><tr>{header.map(cell => <th>{cell}</th>)}</tr></thead>
    <tbody>{body.map(row => <tr>{...}</tr>)}</tbody>
  </table>
);

B2: JSON 结构化预览

// WorkspaceShell L953-969
const parsed = JSON.parse(content);
return <pre className="workspace-resource-json">{JSON.stringify(parsed, null, 2)}</pre>;

B3: Markdown 正文预览（带引用 vs 不带引用）

// WorkspaceShell L981-998
if (previewTaskId) {
  // ← 有 taskId 时，启用引用交互
  <CitationMarkdownRenderer markdown={content} taskId={previewTaskId} moduleKey={...} />
} else {
  // ← 无 taskId 时，纯 Markdown 渲染（无引用交互）
  <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
}

B4: HTML 内嵌预览

// WorkspaceShell L1301-1303
<iframe title={fileName} srcDoc={htmlContent} sandbox="allow-same-origin" />

例如诊断报告的 HTML 输出（阶段 3 中的 diagnosis_report.html）直接通过 <iframe> 渲染：
<h1>合规路径诊断报告</h1>
<h2>诊断结果</h2>
<ul>
  <li>推荐路径：标准合同备案 / 认证路径（scc_or_certification）</li>
  <li>风险等级：LOW</li>
  <li>命中规则ID：default</li>
</ul>

B5: PDF 预览

// PdfViewer.tsx
const blob = await fetchArtifactBlob(path);  // API 拉取 PDF blob
const objectUrl = URL.createObjectURL(blob);
return <iframe src={objectUrl} />;  // 浏览器原生 PDF 渲染

---
路径 C：轨迹时间线（RunTranscript）

33 个原始事件 → adaptEvents() 聚合 → TraceNodeView 渲染：

trace_manifest.json
  seq:1  status
  seq:2  assessment_request
  seq:3  profile_extracted
  seq:4  tool_start ─┐
  seq:5  tool_result ─┴→ mergeTool() → "解析附件并提取结构化信息" (PARSER | 7.5s)
  seq:8  facts_built       → standaloneNode → "事实提取完成" (PARSER)
  seq:9  retrieval_hits    → standaloneNode → "RAG 检索命中 25 条" (RAG)
  seq:10 issues_built      → "问题清单构建完成, 11 个问题" (REVIEW)
  seq:14 tool_start ─┐
  seq:15 tool_result ─┴→ "生成第1章: 出境活动概述" (GEN | 18.1s)
  seq:16 tool_start ─┐
  seq:17 tool_result ─┴→ "生成第2章: 数据类型与规模" (GEN | 34.5s)
  ...
  seq:30 chapters_generated → "全部章节生成完成" (GEN)
  seq:31 consistency_issues → "一致性检查: 2 个问题" (REVIEW)
  seq:32 alignment_issues   → "对齐检查" (REVIEW)
  seq:33 repair_pass        → "修复完成" (REVIEW)

每个 TraceNodeView 的视觉元素：
- 阶段色点：PARSER=橙色 #ea580c, RAG=蓝色 #2563eb, GEN=紫色 #8b5cf6, REVIEW=青色 #0891b2
- Badge 标签：PARSER / RAG / GEN / REVIEW / LLM
- 耗时：⏱ 18.1s（从 tool_start 到 tool_result 的时间差）
- Token 统计：⬆ 12,500 ⬇ 3,200
- 展开块（TraceExpandableBlock）：
  - INPUT — 输入参数（原文预览 8 行 + "..." → 点击展开完整内容）
  - OUTPUT — 输出结果（同上）
  - 一键复制按钮

---
完整数据流链路可视化

用户表单输入
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│ 后端 Pipeline (33 步)                                        │
│                                                              │
│ facts.json ──→ legal_grounding.json ──→ issue_list.json     │
│     │                    │                    │               │
│     │                    ▼                    ▼               │
│     │           compliance_reasoning.json    │               │
│     │                    │                   │               │
│     │                    ▼                   ▼               │
│     │           writing_strategy.json    evidence_chain.json │
│     │                                         │               │
│     └─────────────────────────────────────────┘               │
│                         │                                    │
│                         ▼                                    │
│              chapter_generator (LLM)                         │
│                         │                                    │
│     ┌───────────────────┼───────────────────┐               │
│     ▼                   ▼                   ▼                │
│ normalize_legal_ convert_citation_   citation_builder         │
│ markdown_structure  markers()        → citation_map.json     │
│     │                   │                   │                │
│     └───────────────────┼───────────────────┘               │
│                         ▼                                    │
│              ReportDocument.chapters[]                       │
│                         │                                    │
│     ┌───────────────────┼───────────────────┐               │
│     ▼                   ▼                   ▼                │
│ MarkdownRenderer   HtmlRenderer         DocxRenderer         │
│ → .md 文件         → .html 文件          → .docx 文件        │
└──────────────────────────────────────────────────────────────┘
                         │
                    API 传输
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│ 前端渲染                                                      │
│                                                              │
│ ModuleRun.response.chapters[]                                │
│     │                                                        │
│     ├─ normalizeMarkdownForRender()  ← 基础归一化            │
│     │   （\r\n→\n, ##补空格, 1)→1.）                         │
│     │                                                        │
│     ▼                                                        │
│ CitationMarkdownRenderer                                    │
│     │                                                        │
│     ├─ fetchCitationMap(taskId) → citationMap state          │
│     │   { "1"→{title:"个人信息保护法", article_no:"一", ...}, │
│     │     "2"→{title:"网络安全法", ...} }                    │
│     │                                                        │
│     ├─ 提取所有【依据：...】块                               │
│     │   → 本地匹配 或 远程 fetchKnowledgeCitation()          │
│     │   → resolvedBasisMap state                            │
│     │                                                        │
│     ├─ ReactMarkdown + remarkGfm                             │
│     │   ├─ p  → 检测 isBasisOnlyParagraph/高亮 → renderInlin │
│     │   ├─ li → renderInlineCitationText()                  │
│     │   ├─ blockquote → renderInlineCitationText()           │
│     │   ├─ td → renderInlineCitationText()                  │
│     │   ├─ h1/h2/h3 → workspace-legal-h1/h2/h3 class        │
│     │                                                        │
│     └─ renderInlineCitationText()                            │
│         ├─ /\[(\d+)\]/ → CitationPopover (脚注编号)          │
│         └─ /【依据：[^】]+】/ → CitationPopover (依据标签)   │
│                                                              │
│ 点击引用 → CitationArticleDrawer                             │
│     ├─ exact_article → fetchArticleDetail() → 条文原文       │
│     ├─ source_overview → 法规来源级定位说明                  │
│     └─ external_verified → 外部来源待入库提示                │
└──────────────────────────────────────────────────────────────┘

---
关键渲染差异总结

┌────────────────────┬────────────────────────┬───────────────────────────────────┬─────────────┐
│        场景        │      使用的渲染器      │            归一化函数             │  引用交互   │
├────────────────────┼────────────────────────┼───────────────────────────────────┼─────────────┤
│ 主报告正文（chapte │ CitationMarkdownRender │ normalizeMarkdownForRender() (仅  │ ✅ 完整引用 │
│ rs 路径）          │ er                     │ basics)                           │ 交互        │
├────────────────────┼────────────────────────┼───────────────────────────────────┼─────────────┤
│ Fallback           │ CitationMarkdownRender │ normalizeFallbackMarkdownForRende │ ✅ 完整引用 │
│ 报告（findings     │ er                     │ r() (深度中文层级修复)            │ 交互        │
│ 重建）             │                        │                                   │             │
├────────────────────┼────────────────────────┼───────────────────────────────────┼─────────────┤
│                    │ CitationMarkdownRender │ 无额外归一化（直接用              │ ✅ 提取     │
│ 中间产物报告 Tab   │ er                     │ preview.content）                 │ taskId      │
│                    │                        │                                   │ 后完整交互  │
├────────────────────┼────────────────────────┼───────────────────────────────────┼─────────────┤
│ 资源预览 Markdown  │ CitationMarkdownRender │ 取决于是否有 taskId               │ 有 taskId   │
│ 文件               │ er 或 ReactMarkdown    │                                   │ 才启用      │
├────────────────────┼────────────────────────┼───────────────────────────────────┼─────────────┤
│ 诊断报告 HTML      │ <iframe srcDoc>        │ 无 (后端已渲染为完整 HTML)        │ ❌ 静态     │
│                    │                        │                                   │ HTML 无交互 │
├────────────────────┼────────────────────────┼───────────────────────────────────┼─────────────┤
│ CSV 文件           │ 自定义 <table>         │ parseCsvRows() (手写解析器)       │ ❌          │
├────────────────────┼────────────────────────┼───────────────────────────────────┼─────────────┤
│                    │ <pre> +                │                                   │             │
│ JSON 文件          │ JSON.stringify(parsed, │ 无                                │ ❌          │
│                    │  null, 2)              │                                   │             │
├────────────────────┼────────────────────────┼───────────────────────────────────┼─────────────┤
│ PDF 文件           │ <iframe> + blob URL    │ 无                                │ ❌          │
└────────────────────┴────────────────────────┴───────────────────────────────────┴─────────────┘


