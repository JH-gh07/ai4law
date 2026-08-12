# MD / DOCX / PDF 渲染一致性审计报告

> 生成时间：2026-08-10
> 审计范围：全部 10 个合规模块的三格式（Markdown、DOCX、PDF）渲染管道
> 方法：逐模块检查模板文件存在性、渲染路径、占位符集合、内容一致性

---

## 一、总体结论

**当前三格式一致性存在系统性缺陷。** 根本原因有三：

1. **模板文件分离** — `.md` 和 `.docx` 是两个独立文件，占位符可能不同，无关联约束；
2. **DOCX 缺失** — PIPIA 双模板均不存在，us_14117 缺 `.docx`，触发降级路径；
3. **PDF 内容源不统一** — 有的从 MD 模板渲染，有的从 sections 元组渲染，有的从 MD 文件读取——内容各不相同。

---

## 二、逐模块审计

### 2.1 us_14117（❌ 严重不一致）

| 项目 | 状态 |
|------|------|
| `.md` 模板 | `resources/templates/us/4.2_us_14117_compliance_template_v0.md` ✅ |
| `.docx` 模板 | **缺失** ❌ |
| MD 渲染路径 | `render_markdown_template(TEMPLATE_MD, mapping)` — 9 段结构化模板 |
| DOCX 渲染路径 | `render_docx_report(docx, title, sections)` — **降级路径** |
| PDF 渲染路径 | `render_pdf_report(pdf, title, sections)` — sections 元组 |
| MD vs DOCX | **结构完全不同**：MD 有 一~九 章 + 子标题，DOCX 是平铺 H2 |
| DOCX vs PDF | 同源 sections，一致 |

**降级路径质量极差**：
```
render_docx_report() 行为：
  - 所有 section 头部变成 H1（无层级）
  - 每行 `- xxx` → ListBullet，其余全部 Plain Paragraph
  - 无表格、无粗体/斜体、无引用格式
  - 无 normalize_legal_markdown_structure
```

**PDF 同样使用 sections = 输入摘要 + 评估结论 + 附件摘要 + 章节内容，丢失模板中 9 段完整结构和所有子标题。**

---

### 2.2 PIPIA（❌ 严重不一致）

| 项目 | 状态 |
|------|------|
| `.md` 模板 | `resources/templates/cn/2.3_pipia_template_v0.md` — **缺失** ❌ |
| `.docx` 模板 | `resources/templates/cn/2.3_pipia_template_v0.docx` — **缺失** ❌ |
| MD 渲染路径 | `render_markdown_report(md, title, _fallback_sections())` — **降级路径** |
| DOCX 渲染路径 | `render_docx_report(docx, title, _fallback_sections())` — **降级路径** |
| PDF 渲染路径 | `PdfRenderer.from_sections(pdf, title, _fallback_sections())` — **降级路径** |

三格式均走降级路径 → **内容一致**，但**质量均为最低等级**：
- 无模板结构（章节、表格、清单、引用块全部丢失）
- 所有内容以平级 H2 section 摊开

---

### 2.3 DPIA（⚠️ DOCX 信息丢失）

| 项目 | 状态 |
|------|------|
| 模板 | 无（走自渲染路径） |
| MD 渲染路径 | `_render_dpia_markdown()` — 丰富 Markdown（项目概况 + DPIA 必要性预判 + 全部章节含引用） |
| DOCX 渲染路径 | `render_docx_report(docx, title, docx_sections)` — 仅有项目目标 + 章节 |
| PDF 渲染路径 | `PdfRenderer.from_markdown(md_path.read_text())` — 从 MD 文件读取 |

| 对比 | MD | DOCX | PDF |
|------|:--:|:----:|:---:|
| 项目概况（profile） | ✅ | ❌ | ✅ |
| DPIA 必要性预判 | ✅ | ❌ | ✅ |
| 触发理由 | ✅ | ❌ | ✅ |
| 章节内容 | ✅ | ✅ | ✅ |
| 引用信息 | ✅ | ❌ | ✅ |

**DOCX 比 MD/PDF 少 3 个信息区块。**

---

### 2.4 CPRA（⚠️ 模板占位符不同）

| 项目 | 状态 |
|------|------|
| `.md` 模板 | `resources/templates/us/4.2_cpra_panorama_template_v0.md` ✅ |
| `.docx` 模板 | `resources/templates/us/4.2_cpra_panorama_template_v0.docx` ✅ |
| MD 渲染路径 | `render_markdown_template(TEMPLATE_MD, mapping)` |
| DOCX 渲染路径 | `render_docx_template(TEMPLATE_PATH, mapping)` |
| PDF 渲染路径 | `render_pdf_report(pdf, title, sections)` — sections 元组 |

**占位符不匹配：**

| | MD 占位符（8个） | DOCX 占位符（5个） |
|--|-----------------|-------------------|
| 1 | `{{executive_summary}}` | `{{cpra_mapping}}` |
| 2 | `{{applicability_scope}}` | `{{current_state}}` |
| 3 | `{{processing_analysis}}` | `{{gaps_and_risks}}` |
| 4 | `{{gaps_and_risks}}` | `{{final_conclusion}}` |
| 5 | `{{consumer_rights}}` | `{{remediation_roadmap}}` |
| 6 | `{{sensitive_and_vendor}}` | — |
| 7 | `{{action_plan}}` | — |
| 8 | `{{final_conclusion}}` | — |

**只有 `gaps_and_risks` 和 `final_conclusion` 两个占位符同时存在于两个模板。其余完全不同！**

PDF 走 sections → 与两个模板内容均不同。

---

### 2.5 Security Assessment（✅ 最佳实践）

| 项目 | 状态 |
|------|------|
| `.md` 模板 | `resources/templates/cn/2.2_risk_assessment_template_v0.md` ✅ |
| `.docx` 模板 | `resources/templates/cn/2.2_risk_assessment_template_v0.docx` ✅ |
| MD 渲染路径 | `render_markdown_template(TEMPLATE_MD, mapping)` |
| DOCX 渲染路径 | `render_docx_template(TEMPLATE_PATH, mapping)` |
| PDF 渲染路径 | `PdfRenderer.from_template(TEMPLATE_MD, mapping)` — 与 MD 同模板 |

**占位符完全匹配**（21 个占位符两个模板完全一致）。

**仍需注意**：有官方报告和内部分析报告两条路径，输出两个 MD 文件。

---

### 2.6 BCR / TIA / CN Flow（✅ 良好）

这三个模块的渲染模式一致且正确：
- MD: `render_markdown_template(TEMPLATE_MD, mapping)`
- DOCX: `render_docx_template(TEMPLATE_PATH, mapping)`  
- PDF: `PdfRenderer.from_template(TEMPLATE_MD, mapping)` — **与 MD 同源**

PDF 从 MD 模板渲染，保证 MD 与 PDF 结构一致。

---

### 2.7 其他模块

| 模块 | MD | DOCX | PDF | 备注 |
|------|:--:|:----:|:---:|------|
| transfer_diagnosis | HTML | ❌ | ✅ | 仅 HTML + PDF，无 DOCX |
| eu_scc | ❌ | DOCX | ❌ | 仅 DOCX 输出 |
| document_review | ❌ | ❌ | ❌ | 无三格式输出 |
| vendor_review | ❌ | ❌ | ❌ | 仅通过 API 返回 |

---

## 三、`render_docx_report()` 降级函数质量分析

这是 DOCX 降级路径的核心函数（`backend/common/render/report.py:36-53`）：

```python
def render_docx_report(output_path, title, sections):
    doc = Document()
    doc.add_heading(title, level=0)
    for header, content in sections:
        doc.add_heading(header, level=1)       # 全部 H1 — 无层级
        for line in content.splitlines():
            if line.startswith("- "):
                doc.add_paragraph(line[2:], style="List Bullet")  # 仅支持无序列表
            else:
                doc.add_paragraph(line)         # 其余一切为纯文本
    doc.save(...)
```

**缺失能力**：
- ❌ 多级标题（全部 H1，无 H2/H3）
- ❌ 表格
- ❌ 粗体/斜体等内联格式
- ❌ 有序列表
- ❌ 引用格式（`{{CIT-xxx}}` 按字面输出）
- ❌ Markdown 后处理（不调用 normalize_legal_markdown_structure）
- ❌ 章节编号

---

## 四、`render_pdf_report()` sections 路径质量分析

`backend/common/render/artifacts.py:15-40` — 从 `list[tuple[str, str]]` 生成 PDF：

```python
def render_pdf_report(output_path, title, sections):
    # sections: [(header, content), ...]
    # header → H2 style (Section)
    # content → markdown-to-flowables parsing (headers, lists, tables, paragraphs)
```

**能力评级**：中等偏上
- ✅ Markdown 标题解析（## → H1, ### → H2, #### → H3）
- ✅ 表格解析（Markdown pipe table）
- ✅ 无序/有序列表
- ✅ 粗体 `**text**` 内联格式
- ✅ 水平线 `---`
- ❌ 引用格式 `{{CIT-xxx}}`（字面输出，不解析）
- ❌ HTML 实体（不处理 `&mdash;` 等）
- ❌ 代码块（🔴 字面输出）

---

## 五、根因分类

| 根因 | 影响模块 | 严重度 |
|------|---------|:------:|
| `.docx` 模板文件缺失 | us_14117 | 🔴 P0 |
| `.md` 和 `.docx` 双模板均缺失 | PIPIA | 🔴 P0 |
| `.md` / `.docx` 占位符不匹配 | CPRA | 🟠 HIGH |
| DOCX 降级路径缺少质量保证 | us_14117, DPIA, PIPIA | 🟠 HIGH |
| PDF 与 MD/DOCX 使用不同内容源 | us_14117, CPRA | 🟠 HIGH |
| DOCX 信息丢失（比 MD 少） | DPIA | 🟡 MEDIUM |
| 无 DOCX 输出 | transfer_diagnosis, eu_scc+ | 🟡 MEDIUM |
| 无 PDF 输出 | eu_scc, document_review, vendor_review | 🟡 MEDIUM |

---

## 六、推荐修复策略

### P0：补齐缺失的 DOCX 模板

```
resources/templates/us/4.2_us_14117_compliance_template_v0.docx  ← 新建
resources/templates/cn/2.3_pipia_template_v0.md                   ← 新建
resources/templates/cn/2.3_pipia_template_v0.docx                 ← 新建
```

### P0：统一 PDF 渲染源

PDF 应从 MD 渲染（而不是 sections 元组），保证 MD ↔ PDF 完全一致：
```python
# 当前（us_14117, cpra）：
render_pdf_report(pdf_output, title, sections)  # sections ≠ MD template

# 应改为：
get_pdf_renderer().from_template(pdf_output, title, TEMPLATE_MD, mapping)
# 或缓存 MD 内容后再渲染
```

### HIGH：建立 MD/DOCX 模板占位符一致性门禁

```
- 每次构建时校验 .md 和 .docx 的 {{placeholder}} 集合完全相等
- 不一致时阻断构建（或至少警告）
- 考虑从单一源（如 JSON schema）自动生成 .md 和 .docx 模板
```

### HIGH：DOCX 降级路径升级

`render_docx_report()` 应至少支持：
- 多级标题（解析 Markdown `##` / `###`）
- 粗体/斜体内联格式
- 表格（python-docx 原生支持）

### MEDIUM：DPIA DOCX 信息补充

DOCX 应包含 MD 中已有的项目概况和必要性预判区块。

---

## 七、验证脚本

```bash
# 检查每个模块模板文件存在性
python3 -c "
from pathlib import Path
modules = {
    'us_14117': 'us/4.2_us_14117_compliance_template_v0',
    'pipia': 'cn/2.3_pipia_template_v0',
    'cpra': 'us/4.2_cpra_panorama_template_v0',
    'assessment': 'cn/2.2_risk_assessment_template_v0',
    'bcr': 'eu/3.2_bcr_review_template_v0',
    'tia': 'eu/3.4_tia_template_v0',
    'cn_flow': 'us/4.1_cn_flow_compliance_template_v0',
}
for mod, prefix in modules.items():
    md = Path(f'resources/templates/{prefix}.md')
    docx = Path(f'resources/templates/{prefix}.docx')
    status = []
    if md.exists(): status.append('MD')
    if docx.exists(): status.append('DOCX')
    missing = [x for x in ['MD','DOCX'] if x not in status]
    flag = '✅' if not missing else '❌ MISSING: ' + ','.join(missing)
    print(f'  {mod:15s} {flag}')
"
```
