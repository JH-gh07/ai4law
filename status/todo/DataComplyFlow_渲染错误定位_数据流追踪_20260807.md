# 渲染链路逐阶段数据追踪与错误定位

> 编写日期：2026-08-07
> 目的：从原始 JSON 中间产物 → LLM 粗 Markdown → 后处理 → 模板拼装 → 前端渲染，每一步展示**真实文本**，定位渲染错误的根因

---

## 零、总体数据流（问题定位版）

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 阶段0: 结构化 JSON 中间产物                                              │
│   facts.json → issue_list.json → legal_grounding.json →                 │
│   compliance_reasoning.json → writing_strategy.json                     │
│   ↓                                                                     │
│   这些 JSON 组装为 LLM 的 context_block（prompt 上下文）                  │
├─────────────────────────────────────────────────────────────────────────┤
│ 阶段1: LLM 粗输出 Markdown（_generate_chapter 第432行）                   │
│   raw = str(response.get("content")).strip()                            │
│   状态: 中文层级（第一章/一、/（一））、{{CIT-xxx}} 占位符、              │
│         【依据：未检索到】、**粗体标记**、残缺文件路径                     │
├─────────────────────────────────────────────────────────────────────────┤
│ 阶段2: 后处理链（_generate_chapter 第433-446行）                          │
│   Step A: strip_markdown_inline(raw) ← 去 ** / * / `                    │
│   Step B: convert_citation_markers(raw, registry) ← {{CIT}} → [N]       │
│           └─ 内部调用 normalize_legal_markdown_structure()               │
│   产出: chapter.content 字符串                                           │
├─────────────────────────────────────────────────────────────────────────┤
│ 阶段3: 模板拼装（external_report_generator.build_official_report_mapping）│
│   按照 official_risk_self_assessment_template.md 模板                    │
│   将各 chapter.content 填入 {{section_x_content}} 占位符                 │
│   执行简单的字符串 replace，不做额外后处理                                │
│   产出: 最终 .md 文件                                                    │
├─────────────────────────────────────────────────────────────────────────┤
│ 阶段4: API 传输到前端，前端接收 chapter 或 markdown 文本                  │
│   WorkspaceShell.normalizeMarkdownForRender() 或                          │
│   normalizeFallbackMarkdownForRender()                                   │
│   产出: 归一化后的纯文本                                                  │
├─────────────────────────────────────────────────────────────────────────┤
│ 阶段5: CitationMarkdownRenderer → ReactMarkdown → DOM                    │
│   renderInlineCitationText() 扫描 [N] / 【依据】                         │
│   CitationPopover / CitationArticleDrawer 交互注入                       │
│   产出: 最终浏览器中的 React DOM                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 一、阶段 0 → 阶段 1：JSON 中间产物 → LLM 粗输出

### 1.1 输入给 LLM 的 context_block（JSON 结构化的上下文）

下面展示 `chapter_generator.py` 中 `_build_context_block` 组装的实际上下文（简化）：

```
【企业基本情况（GENERAL）】
企业名称: 东方信托有限责任公司
行业: 金融科技 / 持牌金融机构
CIIO: 是
涉及重要数据: 是

【可引用法规依据】
{{CIT-CN-EXPORT-ASSESSMENT-ART0-P01}} = 数据出境安全评估办法 第4条
{{CIT-CN-EXPORT-ASSESSMENT-ART1-P01}} = 数据出境安全评估办法 第1条
{{CIT-CN-EXPORT-GUIDE-ART1-P01}}   = 数据出境安全评估申报指南（第三版） 第1条

【问题项（与本章相关）】
ISSUE-ciio-security-assessment（CIIO触发安全评估路径）:
  external_expression: 当前出境活动适用路径需结合诊断结论进一步复核...

【表达策略硬约束】
- 对外报告只能使用 external_expression
- 禁止使用: 完全合规、材料齐备、无风险...
```

### 1.2 LLM 输出的 raw Markdown（`_generate_chapter` L432）

以下是从 `东方信托有限责任公司_数据出境风险自评估报告_草案_20260605.md` 中提取的**实际 LLM 生成文本**，这是后处理之前的状态（根据 `strip_markdown_inline` 之前还原）：

```markdown
**1. 1 企业基本情况**

**根据输入事实，本企业被识别为关键信息基础设施运营者（CIIO）。

【依据：未检索到】。**企业作为数据处理者，其数据出境活动需遵循更为严格的合规要求...

**1. 2 数据出境业务背景**

**本次数据出境活动源于企业日常运营及业务开展需求...
根据附件解析摘要，企业提供的现有数据清单（`storage/uploads/cn_regen_data_inventory_20260408_134644.csv`）存在以下问题...

**1. 3 出境活动的必要性说明**

数据出境的必要性论证是安全评估的核心审查要点之一{{CIT-CN-EXPORT-ASSESSMENT-ART0-P01}}。企业需详细阐述...
根据《数据出境安全评估办法》...应当通过国家网信部门组织的数据出境安全评估 [1]。
...准备并提交完整的申报材料 {{CIT-CN-EXPORT-GUIDE-ART1-P01}}。
```

### 1.3 ⚠️ 问题1：LLM 输出格式不受控

| 观察 | 后果 |
|------|------|
| LLM 输出了 `**1. 1 企业基本情况**` 这种非标准格式 | `strip_markdown_inline` 只去掉 `**` 但 `1. 1` 仍保留为普通文本，不是有序列表 |
| LLM 同时输出了 `[1]` 硬编码脚注 和 `{{CIT-xxx}}` 占位符 | 后续 `convert_citation_markers` 只转换 `{{CIT}}` 不处理 `[1]`，产生**编号冲突** |
| LLM 输出 `**` 未闭合（如 `**独立的一行**` 后没有对应闭合） | `strip_markdown_inline` 后残留单独的 `**` 开头符 |
| LLM 输出文件路径换行断裂：`cn_regen_data_inventory_20260408_\n\n134644.csv` | 在最终报告中体现为无意义换行 |

---

## 二、阶段 1 → 阶段 2：LLM 粗输出 → 后处理链

### 2.1 Step A: `strip_markdown_inline(raw)` 的效果

**代码**：`postprocess.py` L205-219

**输入**（实际 LLM 输出）：
```
**1. 1 企业基本情况**\n\n**根据输入事实，本企业被识别为关键信息基础设施运营者（CIIO）。\n\n【依据：未检索到】。**
```

**`_MD_INLINE_RE` 正则**：`(\*{1,3}|_{1,3})([^*_\n]+?)\1|`([^`\n]+`)`

**匹配行为**：
- `**1. 1 企业基本情况**` → 匹配，去除 `**`，保留 `1. 1 企业基本情况`
- `**根据输入事实，本企业被识别为...` → 只有开头 `**`，无闭合 → **不匹配**，`**` 原样保留
- `【依据：未检索到】。**` → 只有结尾 `**`，无开头 → **不匹配**，`**` 原样保留

**输出**（实际文件中可见的残留）：
```
1. 1 企业基本情况

**根据输入事实，本企业被识别为关键信息基础设施运营者（CIIO）。

【依据：未检索到】。**
```

### 2.2 ⚠️ 问题2：`strip_markdown_inline` 残留孤立 `**`

正则 `\1` 反向引用要求开头和结尾的标记符号完全相同数量，但 LLM 输出的 `**` 可能跨段落未闭合，导致：

| 输入 | 正则匹配结果 | 渲染后果 |
|------|------------|---------|
| `**文本**` | ✅ 匹配，去除 | 正常 |
| `**文本`（只有开头） | ❌ 不匹配，`**` 保留 | 渲染为字面 `**文本` |
| `**\n\n# 第一章` | ❌ `\n` 阻断匹配，`**` 保留 | 渲染为 `**` + 标题，破坏视觉 |
| `` `file.csv` `` | ✅ 匹配，去除 backtick | 正常 |

**实际文件中的残留证据**（`东方信托有限责任公司_数据出境风险自评估报告_草案_20260605.md` L10-14）：

```markdown
**

# 第一章 出境活动概述**

**

1. 1 企业基本情况**
```

这里每一行的独立 `**` 都是 `strip_markdown_inline` 正则的漏网之鱼——原来 LLM 输出是 `**\n\n# 第一章 出境活动概述**\n\n**\n\n1. 1 企业基本情况**`，其中 `**` 从未成对出现在同一 `re.search` 范围内。

### 2.3 Step B: `convert_citation_markers(raw, registry)` 的效果

**代码**：`postprocess.py` L330-348

**核心逻辑**：
1. `strip_markdown_inline(text)` — 先做 inline 剥离
2. `_CIT_MARKER_RE.sub(_replace_marker, text)` — `{{CIT-xxx}}` → `[N]`
3. `normalize_legal_markdown_structure(...)` — 中文层级归一化

**输入**（LLM 粗输出片段）：
```
数据出境的必要性论证是安全评估的核心审查要点之一{{CIT-CN-EXPORT-ASSESSMENT-ART0-P01}}。
...应当通过国家网信部门组织的数据出境安全评估 [1]。
...准备并提交完整的申报材料 {{CIT-CN-EXPORT-GUIDE-ART1-P01}}。
```

**registry 中已有映射**：
- `CIT-CN-EXPORT-ASSESSMENT-ART0-P01` → footnote number 1
- `CIT-CN-EXPORT-GUIDE-ART1-P01` → footnote number 2

**输出**：
```
数据出境的必要性论证是安全评估的核心审查要点之一[1]。
...应当通过国家网信部门组织的数据出境安全评估 [1]。
...准备并提交完整的申报材料[2]。
```

### 2.4 ⚠️ 问题3：{{CIT}} 转换不完整导致双轨脚注

**实际文件中的证据**（`东方信托有限责任公司_数据出境风险自评估报告_草案_20260605.md` L45）：

```
应当通过国家网信部门组织的数据出境安全评估 [1]。
...准备并提交完整的申报材料 {{CIT-CN-EXPORT-GUIDE-ART1-P01}}。
```

观察：
- `[1]` 是 LLM 自己写的硬编码脚注（LLM 不遵守"禁止使用其他引用格式"的约束）
- `{{CIT-CN-EXPORT-GUIDE-ART1-P01}}` 是未被转换的占位符

| 根因 | 解释 |
|------|------|
| **LLM 违规** | System prompt 明确要求"禁止使用其他引用格式"，但 LLM 仍然硬编码了 `[1]` |
| **Registry 缺失** | `CIT-CN-EXPORT-GUIDE-ART1-P01` 可能不在 citation_registry 中，导致 `assign_footnote_number()` 返回 `None`，替换为空字符串 |
| **重复注册** | `CIT-CN-EXPORT-ASSESSMENT-ART0-P01` 被转换为 `[1]`，但 LLM 自己也写了 `[1]`，一个脚注编号指向两条不同的法规 |

### 2.5 Step C: `normalize_legal_markdown_structure()` 的效果

**代码**：`postprocess.py` L50-105

**输入**（后处理后的章节内容）：
```
1. 1 企业基本情况

**根据输入事实，本企业被识别为关键信息基础设施运营者（CIIO）。

【依据：未检索到】。**
```

**处理过程**：
1. `_explode_packed_line()` — `【依据：未检索到】。**` → 拆分为 `【依据：未检索到】。` 和 `**`（？不会，因为 `_BASIS_BLOCK_RE` 只匹配完整 `【依据：...】`）
2. `_classify_legal_block()`：
   - `1. 1 企业基本情况` → `_ORDERED_ITEM_RE` 匹配 `1.` → `list_item`，输出 `1. 1 企业基本情况`
   - `**根据输入事实...` → `paragraph`
   - `【依据：未检索到】。**` → 不是完整的 basis 块（多了 `。**`），→ `paragraph`
3. 块间 separator：`paragraph` + `paragraph` → `\n\n`

**输出**：
```
1. 1 企业基本情况

**根据输入事实，本企业被识别为关键信息基础设施运营者（CIIO）。

【依据：未检索到】。**
```

### 2.6 ⚠️ 问题4：`【依据：未检索到】` 被前端解析为无效引用

**触发路径**：
- `CitationMarkdownRenderer.renderInlineCitationText()` 正则 `/【依据：[^】]+】/`
- 匹配到 `【依据：未检索到】` → 调用 `extractBasisItems()` → 得到 `["未检索到"]`
- `findCitationFromMap("未检索到", ...)` → 返回 `null`
- `resolveAll()` → `fetchKnowledgeCitation("未检索到")` → API 返回 404 或空

**渲染后果**：
- `【依据：未检索到】` 被替换为 `<CitationPopover>` 但无数据可展示
- 用户看到蓝色可点击标记，悬浮后显示空白卡片或"解析中..."
- 后端 `apply_citation_policy()` 其实能识别 placeholder（L282 `item in _PLACEHOLDER_CITATIONS`），但**前端不做此过滤**

### 2.7 ⚠️ 问题5：`normalize_legal_markdown_structure` 产生层级倒挂

**输入**（模板中的章节标题 + 章节正文）：
```markdown
## 一、自评估工作情况

# 第一章 出境活动概述
```

**`_classify_legal_block` 分别判断**：
- `## 一、自评估工作情况` → 已有 `#` 前缀 → `heading`，保持 `## 一、自评估工作情况`
- `# 第一章 出境活动概述` → 已有 `#` 前缀 → `heading`，保持 `# 第一章 出境活动概述`

**问题**：模板用的是 `## 一、`（二级标题），但 LLM 生成的章节开头是 `# 第一章`（一级标题）。在同一个文档中，`#` 覆盖了 `##` 的层级，导致：
```
## 一、自评估工作情况    ← 本应是文档的二级标题
# 第一章 出境活动概述    ← 一级标题覆盖了父级，破坏了文档结构！
```

前端渲染时，浏览器的 outline 结构就乱了——"第一章"成了顶级，与报告标题 `# 数据出境风险自评估报告` 平级。

---

## 三、阶段 2 → 阶段 3：后处理章节 → 模板拼装 → 最终 .md

### 3.1 模板结构

模板文件 `official_risk_self_assessment_template.md` 大致结构：

```markdown
# 数据出境风险自评估报告

**报告日期**：{{report_date}}
**报告编号**：{{report_id}}

---

## 一、自评估工作情况

{{section_1_content}}

---

## 二、出境活动整体情况

### （一）数据处理者基本情况

...表格...

{{section_2_1_content}}

### （二）拟出境数据情况

...表格...

{{section_2_2_content}}

...其余子章节...
```

### 3.2 映射规则

`external_report_generator.py` 中的 `_build_section_content()` 按 `mapped_chapters` 将内部章节填入模板：

```python
# schema 中的映射（官方模板章节 → 内部章节 ID）
"section_1": {"mapped_chapters": ["overview"]},           # 第一章 → 一、
"section_2_1": {"mapped_chapters": ["overview"]},         # （一）→ 第一章（复用！）
"section_2_2": {"mapped_chapters": ["data_scope"]},       # （二）→ 第二章
"section_2_3": {"mapped_chapters": ["security_measures"]}, # （三）→ 第六章
"section_2_4": {"mapped_chapters": ["receiver_assessment"]}, # （四）→ 第四章
"section_2_5": {"mapped_chapters": ["legal_basis"]},      # （五）→ 第三章
"section_3":   {"mapped_chapters": ["impact_analysis", "residual_risk", "conclusion"]},
```

### 3.3 ⚠️ 问题6：同一章节被映射到多个模板位置 → 内容重复

**根因**：`section_1`（一、自评估工作情况）和 `section_2_1`（（一）数据处理者基本情况）都映射到了内部章节 `overview`（第一章 出境活动概述）。

P0-5 虽然引入了 `used_chapter_ids` 去重，但只对后续子章节生效。而 `section_1` 是顶级章节，它用掉了 `overview`，轮到 `section_2_1` 时 `overview` 已在 seen 集合中，按理说不应重复。

**但实际文件中仍然重复！** 看文件 L60-74 和 L8-21 完全相同。

这说明 P0-5 的去重逻辑可能未生效，或者有两次独立的 `build_official_report_mapping` 调用中 `used_chapter_ids` 被重置了。

### 3.4 `render_official_report_md()` — 纯字符串替换

**代码**：`external_report_generator.py` L202-222

```python
def render_official_report_md(output_path, mapping):
    template = _MD_TEMPLATE_PATH.read_text(encoding="utf-8")
    result = template
    for key, value in mapping.items():
        placeholder = "{{" + key + "}}"
        result = result.replace(placeholder, str(value))
    output_path.write_text(result, encoding="utf-8")
    return output_path
```

**关键点**：替换后**不再执行任何 normalize/citation_policy/convert 步骤**。章节内容在阶段2已经处理完毕，模板拼装后直接写入文件。

### 3.5 ⚠️ 问题7：模板拼装不调用 `normalize_legal_markdown_structure`

`render_official_report_md` 只做 `str.replace`，不做任何 Markdown 归一化。这意味着：

- 如果某个 `{{section_x_content}}` 的值以 `# 第一章` 开头，插入后文档结构直接破裂
- 各章节之间的分隔完全依赖模板中的 `---`，但模板没有插入 `\n\n` 做安全分隔
- 相邻章节内容直接接触时可能会被渲染为一个段落

---

## 四、阶段 3 → 阶段 4：后端 .md → API → 前端

### 4.1 前端获取章节数据的方式

**优先路径**（`WorkspaceShell.readResponseChapters`）：
```typescript
// 从 run response 中读取 chapters 数组
chapters: [{title: "出境活动概述", content: "# 第一章 出境活动概述\n\n**\n\n1. 1..."}, ...]
```

**降级路径**（`buildFallbackPreviewSections`）：
从 `findings`/`problems`/`citations`/`next_actions` 结构化数据重建 Markdown 表格。

### 4.2 前端归一化

**`normalizeMarkdownForRender()`**（仅 basics）：
```typescript
// \r\n → \n, ## 后补空格, 1) → 1.
```

**`normalizeFallbackMarkdownForRender()`**（深度归一化）：
```typescript
// 调用 normalizeFallbackMarkdown() → 等价于后端 normalize_legal_markdown_structure
```

### 4.3 ⚠️ 问题8：前端二次归一化与后端归一化冲突

后端 `convert_citation_markers` 已经调用了 `normalize_legal_markdown_structure`。前端 `normalizeMarkdownForRender` 又做一次归一化，但两者使用不同的代码实现：

| 操作 | 后端 (Python) | 前端 (TypeScript) |
|------|-------------|-------------------|
| 中文层级 | `第X章` → `# 第X章` | `classifyBlock` → `heading` |
| 列表项 | `1. ` → `list_item` | `1. ` → `list_item` |
| 表格修复 | `_repair_pipeless_tables` | 无此步骤 |
| 依据块处理 | `_BASIS_BLOCK_RE` 整行检测 | 无此步骤 |

**后果**：如果后端归一化结果中 `#`/`##` 层级已正确，前端再走一遍可能因为类名/正则差异（如 `_ORDERED_ITEM_RE` 的细微不同）产生不同输出。

---

## 五、阶段 4 → 阶段 5：Markdown 文本 → ReactMarkdown → DOM

### 5.1 `CitationMarkdownRenderer` 渲染流程

```
1. normalizeMarkdownForRender(markdown) 或直接使用
2. ReactMarkdown + remarkGfm 解析 Markdown
3. 自定义组件覆盖：
   - p → 检测 isBasisOnlyParagraph / isHighlightParagraph
   - p/li/blockquote/td → 调用 renderInlineCitationText()
4. renderInlineCitationText() 正则扫描：
   - /\[(\d+)\]/ → CitationPopover
   - /【依据：[^】]+】/ → extractBasisItems → CitationPopover
```

### 5.2 实际文本 → React 组件树的转换示例

**输入 Markdown**（从 `apply_citation_policy` 处理后）：
```markdown
如涉及个人信息出境，应结合《个人信息保护法》第十三条、第三十八条、第三十九条等要求补充合法性基础、单独同意及告知留痕材料。 【待核验：缺少法规依据】
```

注意这里有 `【待核验：缺少法规依据】` —— 这是 `apply_citation_policy` 在缺少有效引用时追加的标记。

**ReactMarkdown 解析结果**：
- 整个段落被识别为一个 `<p>` 元素
- `CitationMarkdownRenderer` 的自定义 `p` 组件调用 `renderInlineCitationText()`

**`renderInlineCitationText()` 处理**：
1. 正则 `/\[(\d+)\]/` — 本段无 `[N]`，跳过
2. 正则 `/【依据：[^】]+】/` — 也不匹配（因为这是 `【待核验：...】` 不是 `【依据：...】`）
3. 返回原文本，无引用交互

### 5.3 ⚠️ 问题9：`【待核验：缺少法规依据】` 无视觉区分

`【待核验：缺少法规依据】` 和 `【依据：未检索到】` 以纯文本形式出现在最终报告中：

| 标记 | 前端处理 | 视觉效果 |
|------|---------|---------|
| `【依据：《个人信息保护法》】` | ✅ 被 `renderInlineCitationText` 捕获，渲染为蓝色可交互 CitationPopover | 蓝色链接，可点击 |
| `【待核验：缺少法规依据】` | ❌ 不被任何正则匹配，作为纯文本 | 普通黑色文字，用户可能忽略 |
| `【依据：未检索到】` | ✅ 被捕获但解析失败 | 蓝色链接但悬浮后无数据/报错 |
| `{{CIT-CN-EXPORT-GUIDE-ART1-P01}}` | ❌ 不被任何正则匹配（后端未转换），作为字面文本 | 用户看到原始占位符 |

### 5.4 ⚠️ 问题10：LLM 输出 `[1]` 硬编码脚注与 `convert_citation_markers` 产出 `[1]` 的编号冲突

**场景**：
```markdown
...应当通过国家网信部门组织的数据出境安全评估 [1]。
...准备并提交完整的申报材料{{CIT-CN-EXPORT-GUIDE-ART1-P01}}。
```

**`convert_citation_markers` 处理后**（假设 `CIT-CN-EXPORT-GUIDE-ART1-P01` → 脚注编号 2）：
```markdown
...应当通过国家网信部门组织的数据出境安全评估 [1]。
...准备并提交完整的申报材料[2]。
```

**前端渲染**：
- `[1]` → 查 `citationMap["1"]` → 可能得到 LLM 硬编码的 `[1]` 对应的法规（但 `[1]` 是 LLM 瞎写的，不在 citation_map 中）
- 同时 registry 中真正的第1条法规也有 `[1]` 编号

**后果**：同一个 `[1]` 脚注在文档不同位置指向不同法规，但 `CitationMarkdownRenderer` 从 `citationMap` 中只能查到一个。

---

## 六、问题汇总与定位路径

| # | 问题 | 发生位置 | 根因 | 表现 |
|---|------|---------|------|------|
| 1 | LLM 输出格式不受控 | `_generate_chapter` L432 | LLM 不遵守 prompt 约束，输出 `**粗体**`、硬编码 `[N]`、断裂文件路径 | 残留 `**` 字符、脚注冲突、异常换行 |
| 2 | 孤立 `**` 残留 | `strip_markdown_inline` L205-219 | 正则要求 `\1` 反向引用（开头和结尾 `**` 数量一致），跨段落 `**` 不匹配 | 渲染出字面 `**` 字符 |
| 3 | `{{CIT}}` 双轨脚注 | `convert_citation_markers` L330-348 | LLM 硬编码 `[1]` + registry 也分配 `[1]`，且部分 CIT ID 不在 registry 中 | 同序号指向不同法规，部分 CIT 原样显示 |
| 4 | `【依据：未检索到】` 无效引用 | `renderInlineCitationText` (前端) | 前端不区分"未检索到"和有效引用，一律渲染为 CitationPopover | 蓝色可点击标记但无数据 |
| 5 | 层级倒挂 | `_classify_legal_block` L168-202 | LLM 生成的 `# 第一章` 与模板的 `## 一、` 层级冲突 | 文档 outline 结构错乱 |
| 6 | 章节内容重复 | `build_official_report_mapping` | 同一内部章节映射到多个模板 section，去重可能失效 | 两处出现完全相同的段落 |
| 7 | 模板拼装不归一化 | `render_official_report_md` L202-222 | 纯字符串替换，不调用任何 normalize | 各章节衔接处格式不一致 |
| 8 | 前后端归一化冲突 | `normalizeMarkdownForRender` vs `normalize_legal_markdown_structure` | 不同代码实现、不同正则 | 二次归一化可能产生差异 |
| 9 | `【待核验】` 无视觉区分 | `renderInlineCitationText` (前端) | 正则只匹配 `【依据：` 不匹配 `【待核验：` | 用户看不到警告标记 |
| 10 | `{{CIT}}` 字面残留 | `convert_citation_markers` L330-348 | `assign_footnote_number` 返回 None 时替换为空 | 用户看到 `{{CIT-CN-EXPORT-GUIDE-ART1-P01}}` 原文 |

---

## 七、逐问题修复建议

### 问题1-2：LLM 输出格式不受控 + 孤立 `**`

**定位文件**：`backend/domains/cn/security_assessment/chapter_generator.py` L432-435

**建议**：在 `strip_markdown_inline` 之后增加一次**激进去残留**：

```python
# 在 strip_markdown_inline 之后
raw = re.sub(r'\*\*', '', raw)  # 暴力去除所有孤立 **
raw = re.sub(r'\n{3,}', '\n\n', raw)  # 压缩多余空行
```

或者修改 `strip_markdown_inline` 的正则，不再要求 `\1` 反向引用，改为贪婪匹配所有 `**...**` 对，非成对出现的 `**` 也一并移除。

### 问题3：{{CIT}} 双轨脚注

**定位文件**：`backend/domains/cn/security_assessment/chapter_generator.py` L23-27（prompt 约束）

**根因**：LLM prompt 说"禁止使用其他引用格式"但 LLM 不听话。

**建议**：
1. 在 `convert_citation_markers` 之后增加一步：正则 `/\[\d+\]/` 检测所有硬编码脚注，与 registry 分配编号比对，发现冲突时发出 warning 并替换
2. 或者增强 prompt 中引用约束的权重

### 问题4：【依据：未检索到】无效引用

**定位文件**：`frontend/src/components/citation/CitationMarkdownRenderer.tsx` `renderInlineCitationText()` + `extractBasisItems()`

**建议**：在 `extractBasisItems()` 中过滤 placeholder：

```typescript
const PLACEHOLDER_CITATIONS = new Set(["未检索到", "未检索到相关法规", "未检索到法规依据"]);

function extractBasisItems(basisText: string): string[] {
  const inner = basisText.slice(4, -1); // 去掉 "【依据：" 和 "】"
  return inner.split("；").map(s => s.trim()).filter(s => s && !PLACEHOLDER_CITATIONS.has(s));
}
```

### 问题5：层级倒挂

**定位文件**：`backend/common/llm/postprocess.py` `_classify_legal_block()` L189-194

**建议**：`normalize_legal_markdown_structure` 需要感知**上下文层级**。当输入已经包含 `## 一、` 时，后续的 `# 第一章` 应该提升为 `##` 而不是保持 `#`。

或者在模板拼装阶段（`external_report_generator`），在每个 `{{section_content}}` 插入前统一将所有 `# ` 替换为 `### `（因为模板已有 `# 报告标题` 和 `## 一、`）。

### 问题6：章节内容重复

**定位文件**：`backend/domains/cn/security_assessment/external_report_generator.py` `build_official_report_mapping()` L168-189

**建议**：
1. 检查 `used_chapter_ids` 是否在两次调用间被正确共享
2. 如果 `section_1` 和 `section_2_1` 都映射到 `overview`，考虑在 schema 中去重映射，或让 `section_2_1` 使用 `overview` 的摘要而非全文

### 问题7：模板拼装不归一化

**定位文件**：`backend/domains/cn/security_assessment/external_report_generator.py` `render_official_report_md()` L202-222

**建议**：在 `replace` 循环后添加一次 `normalize_legal_markdown_structure(result)`：

```python
result = normalize_legal_markdown_structure(result)
output_path.write_text(result, encoding="utf-8")
```

### 问题9：【待核验】无视觉区分

**定位文件**：`frontend/src/components/citation/CitationMarkdownRenderer.tsx` `renderInlineCitationText()`

**建议**：在 `renderInlineCitationText` 中增加对 `【待核验：...】` 的正则匹配，渲染为黄色/橙色警告样式的标记：

```typescript
const PENDING_VERIFY_RE = /【待核验：[^】]+】/;
// 匹配后渲染为 <span className="citation-pending-verify">⚠️ 待核验：...</span>
```

### 问题10：{{CIT}} 字面残留

**定位文件**：`backend/common/llm/postprocess.py` `convert_citation_markers()` L341-346

**建议**：当 `assign_footnote_number` 返回 None 时，不要替换为空字符串，而是替换为带标记的警告：

```python
def _replace_marker(match):
    cid = match.group(1)
    num = registry.assign_footnote_number(cid)
    if num is not None:
        return f"[{num}]"
    return f"【未注册引用：{cid}】"  # 而不是 ""
```

---

## 八、验证方法

要复现以上所有问题，只需在一个有 LLM 可用的环境中：

```bash
# 1. 触发一次完整的 assessment 评估
# 2. 对比以下三个产物的差异：

# A) LLM 粗输出（在 _generate_chapter L432 处加 log 打印 raw）
# B) 后处理后章节（在 L445 处加 log 打印 convert_citation_markers 的返回值）
# C) 最终 .md 文件（直接读取）

diff <(阶段A的内容) <(阶段B的内容)
diff <(阶段B的内容) <(阶段C的内容)
```

关键关注：
- `**` 残留数量：`grep -c '\*\*' 文件名`
- `{{CIT}}` 残留数量：`grep -c '{{CIT-' 文件名`
- 章节重复：`grep -n '# 第.*章' 文件名 | sort -t: -k2 | uniq -d`
- 层级倒挂：`grep -n '^#' 文件名` 检查 `#`/`##`/`###` 的嵌套关系
