# 报告预览详细审查结果丢失/未表格化排查表

| 优先级 | 错误点 | 典型现象 | 代码位置 | 修复方向 |
| --- | --- | --- | --- | --- |
| P0 | 生成端输出的不是合法 Markdown 表格 | 用户看到很多 `a \| b \| c` 文本行，但没有表格边框、列头、列对齐 | 上游生成内容；前端无直接校验 | 生成端强制输出标准 GFM 表格，至少包含表头行和 `---` 分隔行 |
| P0 | `response.chapters[].content` 只保存成纯文本，结构已丢 | 最终预览只能按段落显示，无法恢复列结构 | `frontend/src/components/workspace/WorkspaceShell.tsx:144` | 后端返回结构化 `table rows/columns`，或保留标准 markdown 原文 |
| P0 | fallback 把对象拼成 `a \| b \| c` 字符串 | 看起来像表格，但始终不会被 Markdown 识别为 `<table>` | `frontend/src/components/workspace/WorkspaceShell.tsx:248` | 不要 `join(" | ")`；改成标准 Markdown 表格或直接渲染 React table |
| P0 | `normalizeLegalMarkdown()` 只把以 `|` 开头的行当表格 | `2-C1 \| Binding...` 被当普通段落 | `frontend/src/lib/legal-markdown.ts:135`, `frontend/src/lib/legal-markdown.ts:169` | 增加 pipe-like row 识别逻辑，或在预处理前先转标准表格 |
| P0 | `ReactMarkdown + remark-gfm` 不会自动猜测表格 | 内容里有很多 `|`，但渲染结果还是 `<p>` | `frontend/src/components/workspace/WorkspaceShell.tsx:1265`, `frontend/src/components/citation/CitationMarkdownRenderer.tsx:341` | 输入必须先变成合法 GFM 表格，不能指望解析器猜 |
| P1 | 预览优先使用 `response.chapters`，没用真实 artifact 文件 | 导出的 md/html 里有完整表格，但页面预览没有 | `frontend/src/components/workspace/WorkspaceShell.tsx:354` | 优先展示 artifact 原文，或加“原始导出内容/重建内容”切换 |
| P1 | 章节内容被 `cleaned.join("\n")` 合并，只有换行没有结构 | 多行明细变成普通连续文本块 | `frontend/src/components/workspace/WorkspaceShell.tsx:228` | 保留二维结构，不要只存单一字符串 |
| P1 | 行内含额外 `|`，列被拆坏 | 部分行错列、列数不齐、表格完全失效 | 生成内容本身；前端无校验 | 生成端转义 `\|`，或前端做列数一致性检查 |
| P1 | 缺少表头或列数不一致 | 前几行像表格，后面突然变正文 | 生成内容本身 | 生成端模板化输出，前端增加 validator |
| P1 | 内容被错误识别为列表/标题而不是表格 | 行首编号被改成 `1.` 列表，结构散掉 | `frontend/src/lib/legal-markdown.ts:148`, `frontend/src/lib/legal-markdown.ts:155` | 在表格识别前先判断“整行含多个 pipe 分隔列” |
| P2 | `CitationMarkdownRenderer` 只对段落/列表/单元格做增强，不负责表格恢复 | 表格没识别时，依据联动照常跑，但结果仍是正文 | `frontend/src/components/citation/CitationMarkdownRenderer.tsx:344` | 先解决表格识别，再考虑单元格内的依据增强 |
| P2 | `flattenTextChildren()` 遇复杂节点返回 `null` | 某些行/单元格不做依据联动或渲染不一致 | `frontend/src/components/citation/CitationMarkdownRenderer.tsx:260` | 补强复杂 children flatten，或单元格内保留原始 markdown |
| P2 | 样式让已存在的详细结果看起来像散文 | 用户误以为“没显示表格”，实际是文本表格退化 | `frontend/src/styles/app.css` 相关正文样式 | 表格识别后使用明确 table 样式；正文和矩阵样式分离 |
| P2 | 预览源选到 txt/report 而不是 html | html 文件里有完整表格，但当前看的是 text 版 | `frontend/src/components/workspace/WorkspaceShell.tsx:138` | 调整 artifact 优先级，或显示“当前预览来源” |
| P3 | 统计链不读取正文中的详细审查矩阵 | 页面 KPI 没有体现审查项数量/风险分布 | `frontend/src/lib/workspace.ts:23`, `frontend/src/lib/workspace.ts:122` | 单独抽取 `review matrix rows` 进入统一状态 |
| P3 | `extractEvidenceHits()` 只看 `regulations` 和 `chapter.citations` | 表格里有很多审查项，但 `evidenceCount` 不变 | `frontend/src/lib/workspace.ts:148` | 从表格行中抽 `evidence/review hits` |
| P3 | `extractInsight()` 不读详细审查表 | 顶部摘要缺少高/中风险条目统计 | `frontend/src/lib/workspace.ts:45` | 新增 `review_rows` / `risk_summary` 字段解析 |
| P3 | basis 匹配只用于显示，不回写统计 | 看起来点得开依据，但统计仍是 0 | `frontend/src/components/citation/CitationMarkdownRenderer.tsx:275` | 将匹配结果上抛或统一入 store |

## 建议排查顺序

1. 先看最终传给 `ReactMarkdown` 的原始字符串是不是合法 Markdown 表格。
2. 如果不是，确认是生成端就错了，还是 `WorkspaceShell` / fallback 把结构降级了。
3. 如果是合法表格，再看 `normalizeLegalMarkdown()` 有没有把它打坏。
4. 表格显示修好后，再单独补统计链，不要两件事混在一起改。
