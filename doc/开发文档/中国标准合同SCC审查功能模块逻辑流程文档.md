# 中国个人信息出境标准合同 SCC 审查功能 — 全线模块逻辑流程

## 文件总览（7 个源文件，389 行业务逻辑）

```
backend/modules/scc/
├── __init__.py
├── schema.py          (60行)   ← 数据模型层（6个模型）
├── service.py         (389行)  ← 核心业务逻辑（全部代码在一个文件）
├── router.py          (83行)   ← API端点
└── tests/
    ├── __init__.py
    ├── test_service.py (67行)  ← 2个功能测试
    └── test_async_api.py       ← 异步API测试
```

**依赖的外部公共组件**：

```
backend/common/llm/client.py           → LLMClient（chat方法）
backend/common/llm/module_generator.py → generate_chapter()（SCC专用4章prompt）
backend/common/rag/retriever.py        → retrieve_regulations()
backend/common/render/report.py        → render_docx_template / render_markdown_template
backend/common/render/docx_comments.py → render_commented_docx / DocxComment（批注生成）
backend/common/render/summary.py       → summarize_for_slot / attach_citations
backend/common/quality/alignment.py    → check_cn_alignment()
backend/common/risk/scoring.py         → risk_level()
backend/common/storage/file_parser.py  → FileParser（附件文本提取）
backend/common/tasks/manager.py         → InMemoryTaskManager
```

---

## 一、数据模型层

### 模块 1：schema.py — 6 个模型

**文件**：`backend/modules/scc/schema.py`

```
SCCRequest:
  company_name       ← 企业名称（≥2字）
  receiver_name      ← 境外接收方名称（≥2字）
  receiver_country   ← 境外接收方国家/地区（≥2字）
  transfer_purpose   ← 出境目的（≥2字）
  pii_count          ← 普通个人信息出境人数（默认0, ≥0）
  spi_count          ← 敏感个人信息出境人数（默认0, ≥0）
  has_scc_draft      ← 是否已有标准合同草案（默认False）
  uploaded_files[]   ← 上传附件路径列表

SCCProfile:
  company_name, receiver_name, receiver_country,
  transfer_purpose, pii_count, spi_count, has_scc_draft,
  extracted_notes[]   ← 附件解析摘要（每个文件: "路径: 前160字"）

SCCChapter:
  chapter_no, title, content, citations[], risk_level

SCCResult:
  report_path, output_files{}, profile, chapters[], consistency_issues[]

SCCAsyncAccepted / SCCAsyncStatus:
  异步任务模型（task_id, module, state, attempts, max_attempts, created_at, updated_at, error?, result?）
```

---

## 二、核心业务逻辑

### 模块 2：service.py — SCCService

**文件**：`backend/modules/scc/service.py`

**类**：`SCCService`（389 行，是 CN SCC 模块唯一的业务代码）

**构造函数注入 3 个组件**：

```python
self.llm_client          ← LLMClient（4章LLM生成）
self.parser              ← FileParser（附件文本提取）
self.tasks               ← InMemoryTaskManager(module="scc")
```

---

#### 主方法：`generate_report(payload) → SCCResult`

**9 步流程**：

```
① _build_profile(payload)
   → SCCProfile（直接映射字段 + 附件解析）

② _generate_chapters(profile)
   → (chapters[4章], issues[], findings[])

③ check_cn_alignment(report_content, receiver_country)
   → alignment_issues[]（输入与生成内容一致性校验）

④ 如果有 alignment issues → 追加到 findings 和 consistency_issues

⑤ _build_scc_template_mapping() → 模板变量映射

⑥ render_markdown_template() → .md 报告

⑦ render_docx_template() → .docx 报告

⑧ _render_annotated_docx() → 批注版.docx（findings作为批注插入源文件）

⑨ 返回 SCCResult
```

---

## 三、各步骤详解

### 步骤 1：企业画像构建（_build_profile）

**方法**：`_build_profile(payload) → SCCProfile`

**逻辑**：

```
① 遍历 uploaded_files[]
   for each file_path:
     try:
       text = FileParser.parse_text(file_path)
       note = f"{file_path}: {text[:160]}"
     except:
       note = f"{file_path}: [parse skipped] {exc}"

② 构造 SCCProfile:
   直接映射 7 个字段 + extracted_notes[]

输出：SCCProfile { company_name, receiver_name, receiver_country,
                   transfer_purpose, pii_count, spi_count,
                   has_scc_draft, extracted_notes[] }
```

**特征**：附件仅提取前 160 字作为摘要，**不参与合规规则判断**。规则判断仅基于用户填写的结构化字段（pii_count / spi_count / has_scc_draft）。

---

### 步骤 2：章节生成 + 问题识别（_generate_chapters）

**方法**：`_generate_chapters(profile) → (chapters, issues, findings)`

**3 个子步骤**：

#### 2a. 风险等级计算（risk_level）

```python
level = risk_level(
    is_ciio=False,               # 固定为False（SCC路径不涉及CIIO）
    contains_important_data=False, # 固定为False
    pii_count=profile.pii_count,
    spi_count=profile.spi_count,
)
```

调用 `backend/common/risk/scoring.py` 的 `risk_level()` 函数，根据 PII / SPI 人数计算风险等级。

#### 2b. 法规检索（retrieve_regulations）

```python
regs = retrieve_regulations(
    f"standard contract PIPIA {profile.transfer_purpose} {profile.receiver_country}",
    top_k=4,
    jurisdiction="cn",
    path="scc",
)
```

**半动态查询**：将出境目的和接收国家拼入 query。提取 citations（法规引用）和 reg_snippet（法规摘要）。

#### 2c. 构建上下文块（context_block）

```
【企业信息】
- 企业名称：{company_name}
- 境外接收方：{receiver_name}（{receiver_country}）
- 出境目的：{transfer_purpose}
- 个人信息规模：{pii_count:,}人
- 敏感个人信息规模：{spi_count:,}人
- 是否已有标准合同草案：{has_scc_draft ? '是' : '否'}
- 已上传文件摘要：{extracted_notes的前3条}
- 风险等级：{level}

【法规参考】
{reg_snippet}
```

#### 2d. LLM 章节生成

**4 章**：

```python
SCC_CHAPTERS = [
    "审查依据说明",
    "总体合规评级",
    "条款级问题清单",
    "修订建议与行动计划",
]
```

**每章生成逻辑**：

```
LLM 可用:
  content = generate_chapter(llm_client, "scc", title, context_block, citations)
  system prompt: "你是一名专注于中国个人信息出境标准合同备案的资深合规律师..."

LLM 不可用:
  content = f"（{title}：LLM未配置，此处为占位内容）"
```

**SCC 章节 prompt**（来自 module_generator.py）：

| 章节 | Prompt 要求 |
|------|-----------|
| 审查依据说明 | (1)适用法律法规清单；(2)审查范围和边界（仅基于已提供合同/附件）；(3)审查限制与假设 |
| 总体合规评级 | (1)总体评级（高风险/部分合规/基本合规）；(2)给出评级理由；(3)明确是否建议立即整改后再备案 |
| 条款级问题清单 | 按清单格式输出问题，至少包含：定位、原文引用、问题类型、风险分析、法规依据、修改建议 |
| 修订建议与行动计划 | 按优先级给出可执行整改步骤，并给出建议完成时限和提交备案前检查要点 |

#### 2e. 内部问题识别（issues + findings）

**issues（3 条一致性检查）**：

```
① !has_scc_draft → "No SCC draft provided; legal terms should be manually reviewed before filing."
② pii_count ≥ 1,000,000 → "PII volume reaches 1,000,000 threshold; verify whether security assessment path is required."
③ spi_count ≥ 10,000 → "Sensitive personal information volume exceeds 10,000; verify route with security assessment obligations."
```

**findings（4 条规则 + 1 条兜底）**：

```
① !has_scc_draft → HIGH: "未提供可审查的SCC草案文本。缺少合同文本会导致无法完成条款级定位审查。"
   建议: "先补齐SCC完整文本（含附件），再执行逐条款审查与修订。"

② spi_count > 0 → MEDIUM: "涉及敏感个人信息但缺少专项控制条款，存在权利侵害与监管质疑风险。"
   建议: "增加敏感个人信息最小化处理、传输加密与访问留痕条款。"

③ pii_count ≥ 1,000,000 或 spi_count ≥ 10,000 → HIGH: "出境规模可能达到强制安全评估阈值。"
   建议: "先完成路径复核；触发门槛时应转入安全评估流程。"

④ 如果以上 3 条都没触发 → LOW 兜底:
   "未发现阻断性问题。当前输入范围内未命中高风险缺口，但仍需持续复核合同版本变更。"
```

**特征**：findings 是硬编码规则生成的，不来自 LLM。LLM 仅负责将 context_block 扩展成 4 章自然语言报告。这保证了核心合规判断的一致性。

---

### 步骤 3：输入对齐检查（check_cn_alignment）

```python
alignment_issues = check_cn_alignment(
    report_content,           # 4章LLM生成的完整文本
    receiver_country=profile.receiver_country,
)
```

调 `backend/common/quality/alignment.py` 检查 LLM 生成的报告是否引入了未提供的国家、行业等事实。若发现不一致 → 追加到 issues + findings。

---

### 步骤 4：模板映射（_build_scc_template_mapping）

**函数**：`_build_scc_template_mapping(profile, chapters, findings, date_stamp, alignment_warning) → dict[str, str]`

**8 个模板变量**：

```
contract_name          ← 从 extracted_notes 的第一条取文件名
contract_version       ← has_scc_draft ? "draft-v1" : "未提供"
review_date            ← 日期戳
legal_references       ← citations 逐行列出
overall_rating         ← 取所有 findings 的最高风险等级
executive_summary      ← 从"总体合规评级"章节提取摘要（前2句/220字）+ citations
issue_table            ← findings 格式化为Markdown表格（7列）
revision_recommendations ← 从"修订建议与行动计划"章节提取摘要（前2句/260字）+ citations
```

**风险评级逻辑（_resolve_rating）**：

```
!has_scc_draft 或 findings 含 HIGH → "高风险"
findings 含 MEDIUM → "部分合规"
其他 → "基本合规"
```

**问题表格格式化（_format_issue_table）**：

```
| 定位 | 原文引用 | 问题类型 | 风险等级 | 风险分析 | 法规/标准依据 | 修改建议 |
| --- | --- | --- | --- | --- | --- | --- |
| {location} | {quote} | {issue_type} | {risk_level} | {risk_analysis} | {basis} | {suggestion} |
```

---

### 步骤 5：报告渲染

**输出产物**：

```
① .docx  ← render_docx_template(TEMPLATE_PATH, mapping)
           模板: doc/v2/assets/templates/3.1_scc_review_template_v0.docx

② .md    ← render_markdown_template(TEMPLATE_MD, mapping)
           模板: doc/v2/assets/templates/3.1_scc_review_template_v0.md

③ .docx (批注版) ← render_commented_docx(source_docx, output_path, comments)
                    仅在 uploaded_files 中有 .docx 文件时生成
                    将 findings 作为 DocxComment 批注插入源 SCC 文档
                    每个 comment 含: label, location, quote, risk_level, basis, risk_analysis, suggestion
```

---

## 四、关键辅助函数

### _build_review_findings — 4 条硬编码规则

```python
def _build_review_findings(profile, citations) -> list[dict]:
```

| # | 触发条件 | risk_level | issue_type | 受影响 location |
|---|---------|-----------|-----------|---------------|
| 1 | !has_scc_draft | HIGH | 缺失条款 | 合同主文/附件 |
| 2 | spi_count > 0 | MEDIUM | 定义模糊 | 附录II 技术与组织措施 |
| 3 | pii ≥ 1,000,000 或 spi ≥ 10,000 | HIGH | 与法规冲突 | 路径适用性说明 |
| 4 | 以上均未触发 | LOW | 完善建议 | 合同整体 |

### _resolve_rating — 风险评级

```
!has_scc_draft 或 findings 含 HIGH → "高风险"
findings 含 MEDIUM → "部分合规"
其他 → "基本合规"
```

### _render_annotated_docx — 批注版生成

```python
def _render_annotated_docx(payload, findings, date_stamp) -> Path | None:
```

```
① _pick_source_docx(uploaded_files) → 找第一个 .docx 文件
② 将 findings[] 转为 DocxComment 列表
   每个: label=issue_type, location, quote, risk_level, basis=法规依据,
         risk_analysis, suggestion
③ render_commented_docx(source, output, comments) → 批注版.docx
```

---

## 五、API 路由

**文件**：`backend/modules/scc/router.py`

| 端点 | 方法 | 说明 |
|------|------|------|
| `/scc/generate` | POST | 同步生成，返回 `SCCResult`，注册 artifacts |
| `/scc/generate_async` | POST | 异步提交，返回 `SCCAsyncAccepted`，记录 task owner |
| `/scc/tasks/{task_id}` | GET | 轮询状态，完成后注册 artifacts |
| `/scc/tasks/{task_id}/retry` | POST | 重试失败任务 |

---

## 六、完整数据流总图

```
SCCRequest {
    company_name, receiver_name, receiver_country,
    transfer_purpose, pii_count, spi_count,
    has_scc_draft, uploaded_files[]
}
         │
    ┌────▼──────────────────────────────────────────────────────────┐
    │  SCCService.generate_report()                                 │
    │                                                               │
    │  ① _build_profile(payload)                                   │
    │     映射7个字段 + 遍历uploaded_files → FileParser提取前160字   │
    │     → SCCProfile { company_name, receiver_name, ...,          │
    │                     extracted_notes[] }                       │
    │                                                               │
    │  ② _generate_chapters(profile)                                │
    │                                                               │
    │     2a. risk_level(is_ciio=False, contains_important=False,   │
    │                    pii_count, spi_count)                      │
    │         → level ("HIGH" / "MEDIUM" / "LOW")                   │
    │                                                               │
    │     2b. retrieve_regulations(                                 │
    │           "standard contract PIPIA {purpose} {country}",      │
    │           top_k=4, jurisdiction="cn", path="scc"              │
    │         )                                                     │
    │         → regs[]: RegulationHit                               │
    │         → citations[]: str                                    │
    │         → reg_snippet: str                                    │
    │                                                               │
    │     2c. 构建 context_block:                                    │
    │         企业信息 + 境外接收方 + 出境目的 + PII/SPI规模         │
    │         + draft状态 + 附件摘要 + 风险等级 + 法规摘要            │
    │                                                               │
    │     2d. LLM生成4章:                                           │
    │         审查依据说明 → 总体合规评级 → 条款级问题清单 → 修订建议 │
    │         system prompt: "中国个人信息出境标准合同备案资深律师"    │
    │         LLM不可用 → 占位文本                                  │
    │                                                               │
    │     2e. 内部问题识别:                                          │
    │         issues: 3条规则（draft缺失 / PII阈值 / SPI阈值）       │
    │         findings: 4条规则（draft缺失→HIGH / SPI>0→MEDIUM /     │
    │                   阈值触发→HIGH / 兜底→LOW）                   │
    │     → (chapters[4章], issues[], findings[])                   │
    │                                                               │
    │  ③ check_cn_alignment(report_content, receiver_country)      │
    │     检查LLM报告是否引入未提供的事实                             │
    │     → alignment_issues[]                                      │
    │     若不一致 → 追加到 issues + findings                       │
    │                                                               │
    │  ④ _build_scc_template_mapping(profile, chapters,            │
    │                                  findings, date_stamp, warn)  │
    │     → {contract_name/version/date/references/rating/          │
    │        summary/issue_table/recommendations}                   │
    │                                                               │
    │  ⑤ render_markdown_template → .md                             │
    │  ⑥ render_docx_template → .docx                               │
    │  ⑦ _render_annotated_docx:                                    │
    │       findings→DocxComment→render_commented_docx → 批注版.docx│
    │                                                               │
    └────┬──────────────────────────────────────────────────────────┘
         │
    SCCResult {
        report_path: .docx路径,
        output_files: {markdown, docx, annotated_docx?},
        profile: SCCProfile,
        chapters: SCCChapter[4章],
        consistency_issues: list[str]
    }
```

---

## 七、与 eu_scc 模块的关键区别

| 维度 | CN SCC（scc/） | EU SCC（eu_scc/） |
|------|---------------|-------------------|
| **审查对象** | 中国个人信息出境标准合同 | EU 2021/914 SCC |
| **法律依据** | 《个人信息保护法》《个人信息出境标准合同办法》 | GDPR Article 46, Schrems II, EDPB 01/2020 |
| **输入模式** | 表单驱动 — 7个结构化字段 + 附件 | 文档驱动 — scc_text全文 + 结构化字段 |
| **规则引擎** | 4条硬编码规则 | 5组件8阶段确定性规则引擎 |
| **模块验证** | 无 | C2C/C2P/P2P/P2C 4种模块验证 |
| **条款比对** | 无 | 6组关键条款 + 15条弱化信号正则 |
| **TIA审查** | 无 | 22国充分性表 + Schrems II 3类措施 + 美国特有风险 |
| **附录审查** | 无 | Annex I.A / I.B / II / III |
| **管线架构** | 直接调用 — 无 WorkflowPipeline | WorkflowPipeline — 12个callable注入 |
| **LLM角色** | 4章全部LLM生成 | LLM生成 + placeholder兜底 |
| **批注版DOCX** | ✓（相同） | ✓（相同） |
| **章节数** | 4章 | 4章 |
| **核心组件数** | 3个 | 9个业务组件 |
| **文件数** | 3个业务文件 | 9个业务文件 |

---

## 八、关键设计决策

| 维度 | 实现方式 |
|------|---------|
| 架构 | 单体 service.py — 全部业务逻辑集中在单个文件 |
| 规则判断 | 4条硬编码规则 — 确定性、不可变、不依赖LLM |
| 报告生成 | LLM 全量生成 — 基于 context_block 展开4章 |
| 附件处理 | 仅提取前160字作为报告素材，不参与规则判断 |
| 合规假设 | 规则直接硬编码 — 无 checklist / rulebook 分离 |
| 批注版 | render_commented_docx — findings作为批注插入源docx |
| 对齐检查 | check_cn_alignment — 防止LLM引入未提供的事实 |
| 风险评级 | 简单取最高 — 有HIGH→高风险，有MEDIUM→部分合规，否则基本合规 |
| RAG | 半动态 — 含出境目的 + 接收国家 |

## 九、回归验证状态

```
基础报告生成:     PASS ✓（4章输出，.docx + .md）
批注版DOCX:       PASS ✓（comments.xml 包含在输出包中）
draft缺失检测:    PASS ✓（生成 HIGH finding + consistency issue）
阈值触发检测:     PASS ✓（PII≥100万 / SPI≥1万）
对齐校验:         集成 check_cn_alignment ✓
异步API:         支持 submit_async / get_async_status / retry ✓
```
