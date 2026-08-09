# DataComplyFlow 知识库前端展示质量问题分析

> **版本**: v1.0
> **日期**: 2026-08-10
> **范围**: 前端知识库中心（LawViewerPage + EvidenceCenterPage）法律条文展示
> **状态**: 待修复
> **涉及链路**: 原始文件 → snapshot → JSONL / 解析器 → API → 前端渲染

---

## 一、问题全景

前端知识库中心在展示法律条文时存在两大类质量问题：
- **A 类**：条文内容不完整（截断、缺段、仅元数据）
- **B 类**：OCR/格式错误（PDF 页码、HTML 标签、乱码字符、排版坍塌）

共识别 **15 个具体问题**，按严重度分 P0（直接阻断阅读）4 个、P1（严重影响体验）7 个、P2（影响美观）4 个。

---

## 二、A 类问题：条文内容不完整

### A1 [P0] 前端渲染将多段落条文压成一行

**文件**: `frontend/src/pages/LawViewerPage.tsx:264`
```tsx
<p>{article.article_content}</p>
```

**问题**: `<p>` 标签内换行符 `\n` 在 HTML 中折叠为空格。如果 `article_content` 包含多个自然段（例如 GDPR Art 5 有 2 个段落、CCPA §1798.100 有 6 个子段），渲染后全部挤成一段连续文本，完全丧失结构。

**证据**: `EvidenceCenterPage.tsx:805` 已使用 `whiteSpace: "pre-wrap"` 解决同类问题，但 `LawViewerPage` 未同步。

**严重度**: **P0** — 直接导致条文不可读

**影响范围**: LawViewerPage 展示的全部 3 个法域所有条文

**修复方案**:
1. 给 `.law-viewer-article p` 添加 `white-space: pre-wrap`（CSS 方案，5 分钟）
2. 或将 `<p>` 改为 `<pre>` 或使用 `<br/>` 替换 `\n`（JS 方案）
**推荐 CSS 方案**，与 EvidenceCenterPage 保持一致。

---

### A2 [P0] 7 个数据源仅有元数据桩，无实际条文正文

**文件**: `resources/legal/sources/*/snapshots/` 中以下文件：
```
cn/snapshots/cn-sup-005_汽车数据安全管理若干规定_试行_..._69b8dec0.md   (35 chars)
cn/snapshots/cn-tpl-022_隐私政策样例_510dc5fc.md                        (160 chars)
us/snapshots/us_cpra_reference.md                                       (~200 chars)
us/snapshots/us_eo_14117_reference.md                                   (~200 chars)
eu/snapshots/eu_gdpr_art35_reference.md                                 (~200 chars)
eu/snapshots/eu_gdpr_art47_bcr_reference.md                             (~200 chars)
eu/snapshots/eu_edpb_012020_tia_reference.md                            (~200 chars)
```

**问题**: 这些文件只有 `# 标题` 和 metadata 注释（如 "This file tracks benchmark query intent"），没有法律条文正文。当用户点击这些来源时，只能看到元数据信息，无法阅读条文。

**当前情况**:
- `eu_gdpr_art35_reference.md` / `eu_gdpr_art47_bcr_reference.md` — 对应的 GDPR Art 35/47 内容已通过本次索引修复导入 `regulation_articles.jsonl`，实际可检索
- `eu_edpb_012020_tia_reference.md` — EDPB 01/2020 有真实的 excerpts 文件 `edpb_recommendations_01_2020_excerpts.md`
- `us_cpra_reference.md` / `us_eo_14117_reference.md` — CPRA/EO14117 原文已入库
- `cn-sup-005` / `cn-tpl-022` — 仍无实际内容

**严重度**: **P0** — 知识库入口可点但无内容

**修复方案**:
1. 对有实际内容的源，更新 `snapshot_path` 指向正确文件
2. 对无内容的源，在 `sources.csv` 中标记 `path=reference` 或在快照中添加占位说明

---

### A3 [P1] 部分 CN 法律条文在 snapshot 中被人工换行截断

**文件**: 如 `cn/snapshots/cn-sup-001_个人信息出境认证办法_b1078d14.md`

**问题**: PDF 提取或 OCR 过程中，原始文本的行宽被保留，导致每条约 30 字符就强制换行：
```
第一条 为了保护个人信息权益，规范个人信息出境认证活
动，促进个人信息高效安全跨境流动，根据《中华人民共和国个
人信息保护法》、
      《网络数据安全管理条例》、
                    《中华人民共和国认
证认可条例》等法律法规，制定本办法。
```

这种硬换行破坏了条文的自然语义段，阅读时需要脑补断句。

**严重度**: P1 — 可读但不流畅

**影响范围**: 至少 7 个 CN snapshot 文件有此问题（cn-sup-001, 002, 003, 004, 006 等）

**修复方案**: 在 `_clean_source_text()` 中添加「中文行合并」逻辑：检测到中文字符后的 `\n` 且下一行以中文开始时，合并行。

---

### A4 [P1] 非中文法条（EU/US）的 snapshot fallback 解析器完全不工作

**文件**: `backend/services/knowledge_index.py:262-297` (`_parse_articles_from_text`)

**问题**: 解析器仅匹配 `第X条` 格式（中文法律标准），对 EU GDPR（`Article X`）、US CCPA（`§1798.XXX`）的 snapshot 文件完全无法识别条目标记，导致：
- EU/US 来源如果不在 `regulation_articles.jsonl` 中，就无法按条文检索
- 即使 snapshot 中有完整文本，API 也返回 404

**当前规避**: 在本次索引修复中已将 GDPR 99 条、CPRA 90 sub-section 全部导入 `regulation_articles.jsonl`，当前无实际影响。但这是一个结构性风险——如果有新的 EU/US 来源仅通过 snapshot 入库，将完全无法检索。

**严重度**: P1 — 当前无实际影响（已规避），但属结构性缺陷

**修复方案**: 在 `_parse_articles_from_text()` 中增加 EU/US 文章的解析器分支：
- EU: 匹配 `Article \d+` 或 `Article \d+[A-Z]?` 作为标题
- US: 匹配 `^§\s*\d+\.\d+` 或 `^Section \d+` 作为标题

---

### A5 [P2] 部分 CN snapshot 将多部法律拼接在同一文件中

**文件**: 
- `cn-sup-003_信息安全技术_个人信息安全规范_98413de1.md` (48,560 chars, 1391 lines)
- `cn-sup-006_金融数据安全_数据安全分级指南_1311542a.md` (106,844 chars, 1822 lines)

**问题**: 这些文件是标准的全文文档（非法律条文），不适合用 `第X条` 的方式解析。在 `regulation_articles.jsonl` 中它们被当作单条大型 chunk 存储，前端展示时看到的是整本规范书，而非单条条款。

**严重度**: P2 — 全文文档也可以有用，但缺少内页导航

**修复方案**: 
1. 按章节 `##` 标题拆分这些大文件为多个 article
2. 或在 LawViewerPage 中为长内容添加目录导航

---

## 三、B 类问题：OCR 和格式错误

### B1 [P0] EU CELEX PDF 提取文件含有大量页码/页眉干扰

**文件**: `resources/legal/sources/eu/snapshots/eu-sup-*_celex_*_en_txt_*.md`（共 16 个文件）

**问题**: 从 EU Official Journal PDF 提取时，以下结构标记未被清除：
```
7.6.2021            EN                            Official Journal of the European Union                                                L 199/31
```

出现频率：SCC 决定文件中多达 32 处页码标记，整段正文夹带页码编号。

**示例** (eu-sup-013, SCC 2021 决定文件):
```
7.6.2021            EN                            Official Journal of the European Union                                                L 199/31

                                     COMMISSION IMPLEMENTING DECISION (EU) 2021/914
```

**严重度**: **P0** — 页码直接混入正文，严重影响阅读

**修复方案**: 在 `_clean_source_text()` 中添加 PDF 页眉/页脚过滤正则：
```python
import re
# Remove EU Official Journal page headers
text = re.sub(r'^\d+\.\d+\.\d+\s+EN\s+Official Journal.*$', '', text, flags=re.MULTILINE)
# Remove page numbers
text = re.sub(r'^L\s+\d+/\d+$', '', text, flags=re.MULTILINE)
```

---

### B2 [P1] 52 个 snapshot 文件含有非标准字符（OCR 残留）

**分布**:
- EU CELEX 文件：约 20 个（含西欧特殊字符如 °, §, é, ñ, ö 等，多数是合法的欧洲语言字符）
- US 文件：约 10 个（Federal Register 文件中的 § 符号、em-dash、特殊引号）
- CN 文件：约 22 个（含 U+000C 换页符、圈数字 ①②③ 等）

**问题**: 部分字符是合法文本（如 GDPR 的法语/德语变音字符），部分是 OCR 转换残留（如 U+000C 换页符 Form Feed）。

**严重度**: P1 — 部分可正常显示，部分会产生视觉噪音或方框乱码

**修复方案**:
1. 替换 Form Feed (U+000C) 为 `\n\n`
2. 保留合法的西欧语言特殊字符（它们对 EU 文本是正确内容）
3. 仅为 `jurisdiction=cn` 的源过滤非 CJK/ASCII 字符

---

### B3 [P1] CELEX 文件尾部有大量无意义的省略号行

**文件**: 所有 CELEX snapshot 文件

**问题**: PDF 提取时，欧盟官方公报的省略号（用于标记条款内被省略的段落）被保留为大量点号：
```
. . . . . . . . . . . . . . . . . . . .

     2. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
```

**严重度**: P1 — 占用视觉空间，无信息量

**修复方案**: 在 `_clean_source_text()` 中添加省略号行过滤：
```python
text = re.sub(r'^\s*[.·]\s*[.·]\s*[.·][.\s·]*$', '', text, flags=re.MULTILINE)
```

---

### B4 [P1] 1 个文件含有未清理的 HTML 标签

**文件**: `eu-sup-015_celex_32022d0254_en_txt_a6b2d568.md` — 含 9 处 HTML 标签

**问题**: 从 HTML 网页抓取后，标签没有被完全清除。

**严重度**: P1

**修复方案**: `_clean_source_text()` 已有 HTML 清理逻辑（`_extract_text_from_html`），但触发条件是 `<` and `>` 同时出现。检查为何此文件未被清理——可能是 HTML 片段不完整导致判断失败。

---

### B5 [P2] CN snapshot 文件排版不一致——缩进、空格混乱

**文件**: 多数 CN snapshot（8/13 个）

**问题**: 
- 部分文件从网页抓取，保留了原始 HTML 的 `&nbsp;` 等效缩进
- 文件内混合使用空格和 Tab
- 法律标题前的空格数量不统一（有的 4 空格，有的 8 空格）

**严重度**: P2 — 影响美观但不影响理解

---

### B6 [P1] PDF 提取导致的英文单词断字（hyphenation）未被修复

**文件**: CELEX 系列、Federal Register 系列

**问题**: PDF 文本提取保留了原始排版中的音节断字符，例如：
```
trans- fer → transfer
pro- cessing → processing
```

在 EU 文件中表现为 `trans-` 单独一行、下一行 `fer`，在渲染时可能显示为带连字符的破碎单词。

**严重度**: P1 — 阅读干扰

**修复方案**: 在 `_clean_source_text()` 中添加断字修复：
```python
# Fix PDF line-break hyphenation (lowercase word broken across lines)
text = re.sub(r'([a-z]{3,})- *\n *([a-z]{3,})', r'\1\2', text)
```

---

### B7 [P1] `_clean_source_text` 函数对 PDF 分页符处理不彻底

**文件**: `backend/services/knowledge_index.py:300-307`

```python
def _clean_source_text(text: str) -> str:
    normalized = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    if "<" in normalized and ">" in normalized:
        normalized = _extract_text_from_html(_extract_primary_html_segment(normalized))
    normalized = html.unescape(normalized)
    normalized = re.sub(r"[ \t\f\v]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()
```

**具体缺陷**:
1. `\f` (form feed, U+000C) 被替换为空格 → 应替换为 `\n\n`（表示新页）
2. `\v` (vertical tab) 被替换为空格 → 应替换为 `\n`
3. PDF 页码行（`L 199/31`）未过滤
4. EU Official Journal 页眉（`Date  EN  Official Journal...`）未过滤
5. 省略号噪音行（`. . . . .`）未过滤
6. `\n{3,}` → `\n\n` 只能折叠过多空行，不能重建语义段落
7. 中文硬换行（30 字符断行）未合并
8. 无 HTML entity 完全清理（`&nbsp;` `&amp;` 等）

**严重度**: P1 — 需要整体重写

---

## 四、C 类问题：前端渲染缺陷

### C1 [P0] LawViewerPage 不保留换行

等同于 A1，此处从渲染管线角度再次强调。

**修复**: `pages.css` 中 `.law-viewer-article p { white-space: pre-wrap; }`

---

### C2 [P1] LawViewerPage 不渲染 Markdown

**现状**: `article_content` 直接插入 `<p>` 标签，如果内容中使用了 Markdown 标记（如 GDPR excerpts 文件中的 `## Article 5`），前端显示为原始 Markdown 文本。

**严重度**: P1 — 因为当前内容中 Markdown 使用较少，但架构上应支持

**修复方案**: 对 `article_content` 使用已有的 `CitationMarkdownRenderer` 组件，或至少用 `react-markdown` 做基础渲染。

---

### C3 [P2] EvidenceCenterPage 和 LawViewerPage 的法条渲染行为不一致

| 特性 | EvidenceCenterPage | LawViewerPage |
|------|:---:|:---:|
| `whiteSpace: pre-wrap` | ✅ | ❌ |
| 上下文条文（前后条） | ❌ | ✅ |
| Markdown 渲染 | ❌ | ❌ |

两个页面应统一渲染管线。

**严重度**: P2

---

## 五、D 类问题：数据源质量分化

### D1 [P1] 双轨数据源质量不一致

| 数据源 | 质量 | 来源 |
|------|:---:|------|
| `regulation_articles.jsonl` | 高（手工整理/PDF 提取并人工校验） | GDPR 99 条、CPRA 90 条、CN 法律条文 |
| snapshot `.md` 文件 | 中低（直接 PDF→txt/HTML→txt 转换） | CELEX 决定、EDPB 指南、Federal Register |

当前 `get_article_detail()` 的查找优先级：
1. 先查 `regulation_articles.jsonl`（质量高）✅
2. 查不到则 fallback 到 snapshot 文件解析（质量低）⚠️

**问题**: 当一个 source 同时有 JSONL 和 snapshot 数据时，JSONL 优先（正确）。但当用户通过源详情页看到 snapshot 预览时（`get_user_source_preview` → `read_text_preview`），看到的仍是低质量内容。

**严重度**: P1 — 已通过 JSONL 覆盖了核心源，但边缘源仍有风险

---

### D2 [P2] 缺少自动化的 snapshot → JSONL 导入流水线

**现状**: 每次导入新的法律条文到 `regulation_articles.jsonl` 需要手写 Python 脚本。

**建议**: 当有新 snapshot 文件入库时，应自动解析其内容并生成 JSONL 条目。

**严重度**: P2

---

## 六、修复优先级矩阵

```
                    高影响                            低影响
             ┌──────────────────────┐    ┌──────────────────────┐
  容易修复    │ A1 (pre-wrap)         │    │ C3 (统一渲染)         │
             │ B3 (省略号清理)        │    │ B5 (缩进统一)         │
             │ A2 (元数据桩补内容)     │    │                      │
             ├──────────────────────┤    ├──────────────────────┤
  中等难度    │ B1 (PDF页码清理)       │    │ A5 (全文文档导航)      │
             │ B6 (断字修复)          │    │                      │
             │ B2 (特殊字符清理)      │    │                      │
             ├──────────────────────┤    ├──────────────────────┤
  困难/      │ B7 (_clean_source_text │    │ D2 (自动导入流水线)    │
  结构性      │  重写)               │    │                      │
             │ A4 (EU/US解析器)      │    │                      │
             │ D1 (数据源统一)        │    │                      │
             └──────────────────────┘    └──────────────────────┘
```

---

## 七、分阶段修复路线

### Phase 1：P0 阻断项（本周，3 项）

| 编号 | 修复项 | 文件 | 工作量 |
|:---:|------|------|:---:|
| A1 | LawViewerPage 添加 `white-space: pre-wrap` / `pre-line` | `pages.css:1227` | 5 min |
| A2 | 7 个 metadata 桩文件补实际内容或标记为不可检索 | 7 个 `.md` 文件 + `sources.csv` | 2 h |
| B1 | CELEX snapshot PDF 页码/页眉清理 | `knowledge_index.py` `_clean_source_text()` | 3 h |

### Phase 2：P1 体验项（本月，7 项）

| 编号 | 修复项 | 文件 | 工作量 |
|:---:|------|------|:---:|
| B3 | 省略号噪音行过滤 | `_clean_source_text()` | 1 h |
| B6 | 英文断字符修复 | `_clean_source_text()` | 1 h |
| B7 | 重写 `_clean_source_text` 全链路清洗（8 项缺陷） | `knowledge_index.py` | 4 h |
| B4 | HTML 标签彻底清除 | `_clean_source_text()` | 30 min |
| A3 | CN snapshot 中文换行合并 | `_clean_source_text()` 或预处理脚本 | 2 h |
| A4 | 扩展 `_parse_articles_from_text` 支持 EU/US 文章格式 | `knowledge_index.py` | 3 h |
| C2 | LawViewerPage 接入 Markdown 渲染 | `LawViewerPage.tsx` | 1 h |

### Phase 3：P2 优化项（按需，4 项）

| 编号 | 修复项 | 文件 | 工作量 |
|:---:|------|------|:---:|
| C3 | EvidenceCenterPage/LawViewerPage 渲染统一 | 前端两个页面组件 | 2 h |
| B5 | CN snapshot 排版标准化 | 批量脚本处理 | 2 h |
| A5 | 大型规范文件按章节拆分 | `regulation_articles.jsonl` | 3 h |
| D2 | snapshot → JSONL 自动导入脚本 | 新工具脚本 | 4 h |

---

## 八、关键数据

### 8.1 Snapshot 文件概况
```
总 snapshot 文件:         59 个
├── 含 PDF 页码干扰:      16 个 (27%)
├── 含非标准字符:         52 个 (88%)
├── 含 HTML 标签:          1 个
├── 仅元数据无正文:         7 个 (12%)
└── CN 文件含"第X条"结构:   7/13 个 (54%)
```

### 8.2 数据源覆盖现状
```
regulation_articles.jsonl: 102 source_ids, 3,213 条目
├── EU-LAW-001 (GDPR):    99 条目（全量覆盖）
├── US-CA-001 (CPRA):     90 条目（全量覆盖）
└── CN laws:              3,024 条目

snapshot 文件 fallback:    59 个文件，质量参差不齐
```

### 8.3 前端渲染现状
```
LawViewerPage:         <p>{content}</p>     ← 无 white-space 保留
EvidenceCenterPage:    <p style="whiteSpace:pre-wrap">  ← 有 white-space 保留
```

---

## 九、根因总结

前端知识库展示问题的根因可以归纳为三层：

1. **数据源层**：法律文件来源多样（PDF、HTML、DOCX、网页），提取过程中保留了原始格式噪音。59 个 snapshot 中 52 个含非标准字符，16 个含 PDF 页码，7 个仅有元数据桩。

2. **清洗管线层**：`_clean_source_text()` 函数处理能力有限——不处理 PDF 页码、不修复断字、不清理省略号、不标准化段落分隔。清洗规则是针对中文网页场景设计的，对 EU/US 的 PDF 场景覆盖不足。

3. **前端渲染层**：`LawViewerPage` 对「条文」的展示模型不匹配内容实际——法律条文本质是多段落的结构化文本，但前端只用单个 `<p>` 标签渲染，且缺少 `white-space` 保留策略。与之形成对比的是 `EvidenceCenterPage` 已正确使用了 `white-space: pre-wrap`，两者渲染行为不一致。
