# 欧盟标准合同 SCC 审查功能 — 全线模块逻辑流程

## 文件总览（22 个源文件，2,240 + 389 行）

### eu_scc 模块 — 新版独立审查引擎（9 个业务文件）

```
backend/modules/eu_scc/
├── __init__.py
├── schema.py                      (214行)  ← 数据模型层（20+模型 + 4枚举）
├── scc_parser.py                  (383行)  ← SCC文档结构化解析器
├── scc_rule_engine.py              (606行)  ← 确定性规则引擎（5组件8阶段）
├── fact_builder.py                (66行)   ← 事实构建器
├── issue_builder.py               (103行)  ← 问题识别器
├── evidence_builder.py            (39行)   ← 证据链构建器
├── service.py                     (385行)  ← 总调度器（WorkflowPipeline编排）
├── router.py                      (54行)   ← API端点
└── tests/
    ├── __init__.py
    └── test_service.py                       ← 功能测试（18个测试）
```

### scc 模块 — 旧版通用审查模块（保留兼容）

```
backend/modules/scc/
├── __init__.py
├── schema.py
├── service.py                     (389行)  ← 旧版SCC服务
├── router.py
└── tests/
    ├── __init__.py
    ├── test_service.py
    └── test_async_api.py
```

### 公共基础设施依赖

```
backend/common/workflow/pipeline.py         ← WorkflowPipeline（16步策略模式管道）
backend/common/workflow/context_pack.py     ← GenerationContextPack
backend/common/workflow/facts.py            ← FactItem
backend/common/workflow/issues.py           ← IssueItem
backend/common/workflow/evidence.py         ← EvidenceItem
backend/common/render/docx_comments.py      ← render_commented_docx（批注）
backend/common/render/summary.py            ← summarize_for_slot / attach_citations
backend/common/render/report.py             ← render_docx_template / render_markdown_template
backend/common/llm/module_generator.py      ← generate_chapter（EU SCC专用prompt）
backend/common/rag/retriever.py             ← retrieve_regulations
backend/common/tasks/manager.py             ← InMemoryTaskManager
backend/common/trace/                       ← TraceRecorder（全链路记录）
```

---

## 一、数据模型层

### 模块 1：schema.py — 20+ 模型 + 4 枚举

**文件**：`backend/modules/eu_scc/schema.py`

#### SCC 文档结构（解析产物）

```
SCCModuleType = Literal["Module One", "Module Two", "Module Three", "Module Four"]
PartyRole = Literal["controller", "processor"]

SCCParty:
  name, address, contact, role(controller/processor), signature, is_incomplete

SCCAnnexIA:
  parties[]: SCCParty, signing_info

SCCAnnexIB:
  data_subjects, data_categories, special_category_data[],
  processing_purpose, processing_nature,
  transfer_frequency, retention_period

SCCAnnexII:
  tom_items[]: str                    ← 技术组织措施列表
  supplementary_measures[]: str       ← Schrems II补充措施

SCCAnnexIII:
  sub_processors[]: dict{name, location}

SCCClause:
  clause_no (1-18), title, content,
  has_deviation, deviation_type(deletion/weakening/restriction_added/none),
  deviation_description

SCCDocument:
  module_type, clauses[]: SCCClause (Clauses 1-18),
  annex_i_a, annex_i_b, annex_ii, annex_iii, raw_text
```

#### 传输链路模型

```
SCCTransferChain:
  exporter_name, exporter_role(controller/processor),
  importer_name, importer_role(controller/processor),
  sub_processors[]: str, onward_transfer_locations[],
  storage_locations[], access_locations[]
```

#### 审查发现模型

```
FindingSeverity = Literal["HIGH", "MEDIUM", "LOW"]

FindingType = Literal[
    "module_mismatch",              ← 模块选择错误
    "clause_weakened",              ← 标准条款被弱化
    "clause_deleted",               ← 标准条款被删除
    "annex_incomplete",             ← 附录信息不完整
    "annex_vague",                  ← 附录描述过于笼统
    "special_category_misclassified", ← 特殊类别数据未正确声明
    "tia_missing",                  ← TIA缺失
    "supplementary_measures_insufficient", ← 补充措施不足
    "sub_processor_chain_incomplete", ← 子处理者链条不完整
    "party_info_incomplete",        ← 主体信息不完整
    "governing_law_issue",          ← 管辖法问题
    "other"                         ← 其他
]

SCCFinding:
  finding_id, location, clause_ref, original_text,
  issue_type: FindingType, severity: FindingSeverity,
  risk_analysis, legal_basis, recommendation, suggested_text
```

#### 审查结果组件

```
ModuleValidation:
  expected_module, actual_module, is_correct, mismatch_reason

ClauseComparison:
  clauses_checked, deviations_found, findings[]: SCCFinding

AnnexReview:
  findings[]: SCCFinding

TIAReview:
  has_third_country_transfer, third_country_transfers[],
  tia_present, has_supplementary_measures,
  schrems_ii_measures_present, findings[]: SCCFinding
```

#### 输入输出模型

```
SCCReviewRequest:
  project_name, scc_text(完整文档文本≥10字),
  declared_module_type, exporter_role, importer_role,
  has_tia, has_supplementary_measures,
  uploaded_files[], company_name

SCCRuleEngineResult:
  recommended_path="eu_scc", rationale,
  document: SCCDocument, transfer_chain: SCCTransferChain,
  module_validation: ModuleValidation,
  clause_comparison: ClauseComparison,
  annex_review: AnnexReview, tia_review: TIAReview,
  all_findings[]: SCCFinding, overall_rating: str

SCCChapter:
  chapter_no, title, content, citations[], risk_level

SCCReviewResult:
  report_path, output_files{}, company_name, overall_rating,
  findings[]: SCCFinding, module_validation,
  chapters[]: SCCChapter, consistency_issues[], attachment_notes[]
```

---

## 二、SCC 文档解析器

### 模块 2：scc_parser.py — 结构化解析

**文件**：`backend/modules/eu_scc/scc_parser.py`

**入口函数**：`parse_scc_document(text, declared_module, exporter_role, importer_role) → SCCDocument`

**5 步解析流程**：

#### 第 1 步：模块类型识别（`_find_module_type`）

```
8 组正则模式：
  MODULE ONE / Module One → "Module One"
  MODULE TWO / Module Two → "Module Two"
  MODULE THREE / Module Three → "Module Three"
  MODULE FOUR / Module Four → "Module Four"

未匹配 → 使用用户声明的 declared_module
```

#### 第 2 步：章节分拆（`_split_sections`）

```
扫描 4 个附录边界（Annex I.A / I.B / II / III）
取第一个附录的位置作为分界点
  ├─ clauses: 附录前的正文（Clause 1-18区域）
  └─ annex_ia / annex_ib / annex_ii / annex_iii: 各附录区域

附录识别模式（30+ 种正则）：
  Annex I.A → "ANNEX I", "List of Parties", "A. LIST OF PARTIES" 等
  Annex I.B → "DESCRIPTION OF TRANSFER", "B. DESCRIPTION OF" 等
  Annex II  → "TECHNICAL AND ORGANISATIONAL MEASURES" 等
  Annex III → "LIST OF SUB-PROCESSORS", "List of Sub-processors" 等
```

#### 第 3 步：条款提取（`_extract_clauses`）

```
18 条标准 Clause 标题匹配：
  Clause 1: "purpose and scope"
  Clause 7: "docking clause" / "Docking Clause"
  Clause 9: "use of sub-processors" 等
  Clause 14: "local laws and practices" / "local laws"
  Clause 15: "access by public authorities" / "government access"
  Clause 17: "governing law" / "Governing law"
  Clause 18: "choice of forum and jurisdiction" / "jurisdiction"

提取方式：逐 Clause 标题定位 → 取下一条 Clause 作为边界 → 截取内容

兜底：正则 [Cc]lause\s+(\d+) 扫描 → 没有子句结构的文档不解析
```

#### 第 4 步：附录提取

**Annex I.A**（`_extract_annex_ia`）：

```
按 "data exporter:" / "data importer:" 切分 party 块
逐块提取：name（正则 "name|名称[: ]"）, address
检测 incomplete 信息：正则 "see MSA|as set forth in the agreement"
```

**Annex I.B**（`_extract_annex_ib`）：

```
8 个字段正则提取：
  data_subjects, data_categories, processing_purpose,
  processing_nature, retention_period, transfer_frequency

特殊类别检测：
  正则扫描 "special categor/health data/genetic/biometric/religious/political/ethnic/trade union"
```

**Annex II**（`_extract_annex_ii`）：

```
提取列表项（- * 开头）→ tom_items[]
补充措施扫描（supplement/additional/schrems/onward transfer restriction）→ supplementary_measures[]
```

**Annex III**（`_extract_annex_iii`）：

```
逐行提取子处理者列表项 → name + location（正则 "located|location|country"）
```

#### 第 5 步：传输链路构建（`_build_transfer_chain`）

```
从 Annex I.A parties 提取：
  exporter_name → role 含 "exporter" / "controller" 的 party
  importer_name → role 含 "importer" / "processor" 的 party

从 Annex III sub_processors 提取：sub_processors[]: name

从文档全文扫描国家名（22个国家）：
  美国/印度/塞尔维亚/中国/英国/日本/韩国/新加坡/巴西/澳大利亚等
  → storage_locations[], access_locations[], onward_transfer_locations[]
```

---

## 三、确定性规则引擎

### 模块 3：scc_rule_engine.py — 5 组件 8 阶段审查

**文件**：`backend/modules/eu_scc/scc_rule_engine.py`

**入口函数**：`run_eu_scc_rule_engine(doc, chain, declared_module, has_tia, has_supplementary_measures) → SCCRuleEngineResult`

**5 个审查组件，8 个执行阶段**：

```
① 模块选择验证      → ModuleValidation
② 标准条款比对      → ClauseComparison
③ 附录审查          → AnnexReview
④ TIA + 补充措施审查 → TIAReview
⑤ 总体风险评分      → overall_rating
```

---

#### 组件 1：模块选择验证器（`validate_module_selection`）

**输入**：`SCCTransferChain` + 声明的 module

**规则表**：

```
exporter=controller + importer=controller → Module One (C2C)
exporter=controller + importer=processor  → Module Two (C2P)
exporter=processor  + importer=processor  → Module Three (P2P)
exporter=processor  + importer=controller → Module Four (P2C)
```

**输出**：`ModuleValidation { expected_module, actual_module, is_correct, mismatch_reason }`

**报告**：不匹配时生成 HIGH severity finding。

---

#### 组件 2：标准条款比对器（`compare_standard_clauses`）

**标准条款定义**：Clauses 7, 9, 14, 15, 16, 17, 18 的关键条款文本

**弱化信号检测（5 组 15 条正则）**：

| 条款 | 弱化模式 | 风险描述 | 建议修复 |
|------|---------|---------|---------|
| Clause 15(a) 通知 | "as soon as legally permissible" | 修改为'法律许可时'通知，而非'立即(promptly)' | restore "promptly notify" |
| | "without undue delay to the extent legally permissible" | 增加法律许可限定条件 | restore unconditional prompt notification |
| | "subject to applicable local law" | 受限于当地法律 | restore unconditional obligation |
| Clause 15(b) 审查 | "at the data importer's sole discretion" | 将审查义务改为酌情处理 | restore mandatory review obligation |
| | "if it considers it appropriate" | 降低审查标准 | restore "reasonably considers there are grounds" |
| Clause 15(c) 信息 | "at the data importer's discretion" | 信息提供改为酌情处理 | restore "as much relevant information as possible" |
| | "to the extent reasonably practicable" | 增加合理可行限定条件 | restore full disclosure obligation |
| Clause 14 评估 | "to the best of its knowledge" | 将评估义务降低为'据其所知' | restore objective assessment obligation |
| Clause 9 授权 | "general written authorization" | 改为一般授权而非具体授权 | require specific prior authorization |

**逐条款检查**：遍历 doc.clauses（Clause 1-18）→ 逐条匹配弱化信号正则 → 检测到 → 生成 HIGH finding + 标记 deviation

**输出**：`ClauseComparison { clauses_checked, deviations_found, findings[] }`

---

#### 组件 3：附录审查器（`review_annexes`）

**Annex I.A — 主体信息检查**：

```
遍历所有 parties：
  - is_incomplete → MEDIUM finding（引用外部MSA）
  - 缺少 name / role → MEDIUM finding
  - party 数量 < 2 → MEDIUM/HIGH finding
```

**Annex I.B — 传输描述检查**：

```
数据类别过泛：
  "order history data" / "order data" / "customer data" / "transaction data"
  → LOW finding（过于笼统）

特殊类别数据误判：
  传输描述含 health/medical/patient/diagnosis/clinical 等词
  但 special_category_data 未声明
  → HIGH finding（GDPR Article 9）
```

**Annex II — TOM 措施检查**：

```
tom_items 为空 → HIGH finding（缺少技术和组织措施）
```

**Annex III — 子处理者**：可为空（合法情况），不强制报错。

**输出**：`AnnexReview { findings[] }`

---

#### 组件 4：TIA + 补充措施审查器（`review_tia_and_measures`）

**第 1 步：识别第三国传输**

```
遍历 transfer_chain 的所有 location（storage/access/onward）
匹配 _THIRD_COUNTRY_ADEQUACY 表（22个国家）
非充分性国家 → third_country_locations[]
```

**第三国充分性决定表**：

| 充分性国家 | 非充分性国家 |
|-----------|------------|
| UK, Japan, South Korea, Switzerland, Canada, Argentina, Israel, New Zealand, Uruguay, Andorra, Faroe Islands, Guernsey, Jersey, Isle of Man | United States, India, China, Russia, Brazil, Singapore, Australia, Serbia |

**第 2 步：TIA 检查**

```
has_third_country AND !has_tia → HIGH finding（TIA缺失）
has_third_country AND Clause 14 被削弱 → HIGH finding（风险评估义务被削弱+第三国传输）
```

**第 3 步：Schrems II 补充措施检测**

3 类措施关键词扫描：

| 类别 | 关键词 |
|------|--------|
| 技术措施 | end-to-end encryption, hold your own key, customer-managed keys, EU-held encryption keys, BYOK, zero-access encryption, zero knowledge encryption, 端到端加密, 欧盟持钥 |
| 合同措施 | government access notification, challenge unlawful requests, transparency report, warrant canary, 政府访问通知, 挑战非法请求, 透明度报告 |
| 组织措施 | data minimization and retention limits, independent annual audit, privacy impact assessment for government access, separation of duties for key management, 独立年度审计 |

```
has_third_country AND 措施不足 → HIGH finding（含三类措施检测结果）
```

**第 4 步：美国特有风险检测**

```
location 匹配 us/usa/amazon/aws/google cloud/azure/microsoft
AND 技术+合同措施不完整 → HIGH finding（US CLOUD Act / FISA 702 风险）
recommendation: E2E加密+EU持钥,合同挑战FISA,透明度报告
```

**第 5 步：子处理者链条检查**

```
逐个子处理者(sp_name) → 匹配第三国充分性表
非充分性国家 → MEDIUM finding（子处理者在非充分性国家）
recommendation: 确认Clause 9授权,TIA覆盖,onward transfer条款
```

**输出**：`TIAReview { has_third_country_transfer, third_country_transfers[], tia_present, has_supplementary_measures, schrems_ii_measures_present, findings[] }`

---

#### 组件 5：总体风险评分（`score_scc_risk`）

```
取所有 findings 的最高严重度：
  HIGH in severities → "HIGH"
  MEDIUM in severities → "MEDIUM"
  其他 → "LOW"
```

---

#### 主入口：run_eu_scc_rule_engine — 8 阶段汇总

```
① validate_module_selection(chain, declared_module)       → module_val
② compare_standard_clauses(doc)                           → clause_comp
③ review_annexes(doc, declared_module)                     → annex_rev
④ review_tia_and_measures(chain, doc, has_tia, has_supp)  → tia_rev
⑤ 收集所有 findings:
     module mismatch + clause deviations + annex findings + TIA findings
⑥ score_scc_risk(all_findings)                             → overall_rating
⑦ 组装 SCCRuleEngineResult 返回
```

---

## 四、管线辅助组件

### 模块 4：fact_builder.py — 事实构建

**文件**：`backend/modules/eu_scc/fact_builder.py`

**函数**：`build_eu_scc_facts(request, rule_result) → list[FactItem]`

**22 条事实，分 4 个来源**：

```
Request facts（6条）：
  project_name, declared_module_type, exporter_role,
  importer_role, has_tia, has_supplementary_measures

Document facts（5条）：
  module_type, clause_count, annex_ia.party_count,
  annex_ii.tom_count, annex_iii.sub_processor_count

Transfer chain facts（3条）：
  exporter_role, importer_role, sub_processor_count

Rule engine facts（8条）：
  module_is_correct, expected_module, clauses_checked,
  deviations_found, has_third_country_transfer,
  tia_present, schrems_ii_measures, overall_rating, finding_count
  （标记 source_type="derived", source_ref="RuleEngine"）
```

---

### 模块 5：issue_builder.py — 问题识别

**文件**：`backend/modules/eu_scc/issue_builder.py`

**函数**：`build_eu_scc_issues(facts, rule_result, regulations) → list[IssueItem]`

**4 章结构**：

```
EU_SCC_CHAPTER_KEYS:
  文件概要          → document_overview
  总体合规评级        → overall_rating
  条款级审查发现      → clause_findings
  法规依据与修改建议   → legal_basis_and_recommendations
```

**6 类 issue 生成**：

```
① 模块选择错误 → HIGH: "模块选择错误: 应为{expected}, 实际{actual}"
② 条款偏离 → HIGH: "标准条款被修改: {n}处偏离"
③ 第三国传输风险 → HIGH: "第三国传输风险: {countries}, TIA={status}"
④ 逐条 HIGH finding → 对应严重度
⑤ 干净通过 → LOW: "未发现高风险问题"
```

---

### 模块 6：evidence_builder.py — 证据链

**文件**：`backend/modules/eu_scc/evidence_builder.py`

**函数**：`build_eu_scc_evidence(facts, issues, regulations) → (issues, evidence_chain)`

**逻辑**：

```
遍历每个 issue：
  筛选有效 fact_refs（在facts中实际存在）
  构建 evidence_id = "EU-SCC-EVIDENCE-{issue_id}"
  置信度分配：BLOCKER=0.95, HIGH=0.90, MEDIUM=0.75, LOW=0.60
  生成 EvidenceItem 并回填 evidence_refs
```

---

## 五、总调度层

### 模块 7：service.py — EU_SCCService

**文件**：`backend/modules/eu_scc/service.py`

**构造函数注入**：

```python
self.llm_client          ← LLMClient（4章LLM生成）
self.parser              ← FileParser（附件文本提取）
self.tasks               ← InMemoryTaskManager(module="eu_scc")
```

#### 主方法：`generate_report(payload) → SCCReviewResult`

**12 步流程**：

```
① parse_scc_document(payload.scc_text, declared_module, exporter_role, importer_role)
   → SCCDocument（完整的结构化SCC文档：Clauses 1-18 + 4个Annex）

② _build_transfer_chain(exporter_role, importer_role, doc, "")
   → SCCTransferChain（主体、子处理者、存储/访问位置）

③ run_eu_scc_rule_engine(doc, chain, declared_module, has_tia, has_supplementary_measures)
   → SCCRuleEngineResult（5组件8阶段确定规则引擎输出）

④ trace.record("rule_engine_result")

⑤ _build_pipeline(rule_result).run(payload, task_id, trace)
   → WorkflowPipeline 12步执行：
     extract_profile      → identity
     evaluate_diagnosis   → rule_result
     validate_path        → None（路径校验不适用）
     build_facts          → build_eu_scc_facts (22条)
     retrieve_regulations → RAG (GDPR Article 46 + Schrems II + module type)
     build_attachment_notes → FileParser提取附件前160字
     build_issues         → build_eu_scc_issues (6类)
     build_evidence       → build_eu_scc_evidence
     build_context_pack   → GenerationContextPack (module_key="eu_scc")
     generate_chapters    → LLM生成 或 placeholder渲染
     check_consistency    → 3条检查
     check_alignment      → []
     render_artifacts     → .md + .docx + .json + 批注版.docx

⑥ 返回 SCCReviewResult
```

#### _build_pipeline — 组装 WorkflowPipeline

```python
WorkflowPipeline(
    extract_profile         → identity (payload原样返回)
    evaluate_diagnosis      → lambda: rule_result
    validate_path           → lambda: None
    build_facts             → _build_facts(rule_result)
    retrieve_regulations    → _retrieve_regulations (动态query含module+role)
    build_attachment_notes  → _extract_notes
    build_issues            → _build_issues(rule_result)
    build_evidence          → _build_evidence
    build_context_pack      → _build_context_pack(rule_result)
    generate_chapters       → _generate_chapters(rule_result)
    check_consistency       → _check_consistency
    check_alignment         → lambda: []
    render_artifacts        → _render_outputs(rule_result)
)
```

#### RAG 检索（`_retrieve_regulations`）

```
query = "GDPR Article 46 standard contractual clauses EU 2021/914
         EDPB recommendations Schrems II transfer impact assessment
         {declared_module_type} {exporter_role} {importer_role}"

top_k=5, jurisdiction="eu", path="scc"
```

#### 上下文块构建（`_build_context_block`）

```
包含：
  - Module 信息（声明/预期/正确性）
  - Clause 偏离数
  - 第三国传输列表
  - TIA 存在状态
  - Schrems II 措施状态
  - 总体评级
  - Findings 列表（前10条）
  - Issues 列表（与章节关联）
  - Regulations 列表（前5条）
```

#### 章节生成（`_generate_chapters`）

**4 章**：

```
文件概要 (document_overview):
  LLM生成或placeholder渲染：
  - SCC模块信息
  - 条款数 / Annex I.A主体数 / Annex II措施数 / Annex III子处理者数

总体合规评级 (overall_rating):
  LLM生成或placeholder渲染：
  - 总体评级
  - 模块选择正确性
  - 标准条款偏离数
  - 第三国传输 / TIA / Schrems II措施

条款级审查发现 (clause_findings):
  LLM生成或placeholder渲染：
  - 逐条finding展示
  - 问题类型 / 风险分析 / 法规依据 / 修改建议 / 建议文本

法规依据与修改建议 (legal_basis_and_recommendations):
  LLM生成或placeholder渲染：
  - 法规依据汇总（去重）
  - 修改建议汇总（按严重度排序）
```

**LLM 不可用时**：`_render_placeholder(title, chapter_id, rule_result)` 生成结构化占位内容。

#### 一致性检查（`_check_consistency`）

```
3 条规则：
① SCC 文本过短（<100字符）→ 警告
② context_pack 包含 HIGH/BLOCKER issues → 法律审查建议
③ 空列表初始化
```

#### 产物渲染（`_render_outputs`）

```
输出产物：
  .md                    ← self-rendered markdown 报告
  .docx                  ← 模板渲染（当前为placeholder touch）
  .docx (批注版)         ← render_commented_docx — 将findings作为批注插入源docx
  findings.json          ← 全部findings序列化
  rule_engine_result.json ← 规则引擎完整结果
  issues.json            ← 问题列表
  evidence.json          ← 证据链
```

---

## 六、完整数据流总图

```
SCCReviewRequest {
    project_name, scc_text(完整文档), declared_module_type,
    exporter_role, importer_role, has_tia, has_supplementary_measures,
    uploaded_files[], company_name
}
         │
    ┌────▼──────────────────────────────────────────────────────────────┐
    │  EU_SCCService.generate_report()                                  │
    │                                                                   │
    │  ① parse_scc_document(scc_text, module, exporter, importer)       │
    │     _find_module_type → _split_sections → _extract_clauses        │
    │     → _extract_annex_ia → _extract_annex_ib → _extract_annex_ii  │
    │     → _extract_annex_iii                                          │
    │     → SCCDocument (Clauses 1-18 + 4 Annes)                        │
    │                                                                   │
    │  ② _build_transfer_chain(exporter, importer, doc)                 │
    │     parties提取 → sub_processors提取 → 国家名扫描                  │
    │     → SCCTransferChain                                            │
    │                                                                   │
    │  ③ run_eu_scc_rule_engine(doc, chain, module, tia, supp)         │
    │     组件1: validate_module_selection → ModuleValidation           │
    │     组件2: compare_standard_clauses → ClauseComparison            │
    │       (Clause 7/9/14/15/16/17/18 的15条弱化信号检测)              │
    │     组件3: review_annexes → AnnexReview                           │
    │       (Annex I.A: 主体完整性, Annex I.B: 数据类别+特殊类别,       │
    │        Annex II: TOMs, Annex III: 子处理者)                       │
    │     组件4: review_tia_and_measures → TIAReview                    │
    │       (第三国识别+充分性表+TIA+Schrems II措施+美国特有+子处理者)   │
    │     组件5: score_scc_risk → overall_rating                       │
    │     → SCCRuleEngineResult                                        │
    │                                                                   │
    │  ④ WorkflowPipeline.run(payload, task_id, trace)                  │
    │                                                                   │
    │     ⑤ extract_profile → identity                                 │
    │     ⑥ evaluate_diagnosis → rule_result                           │
    │     ⑦ build_facts → 22条FactItem                                  │
    │     ⑧ retrieve_regulations → RAG检索(5条)                         │
    │     ⑨ build_attachment_notes → 附件前160字                         │
    │     ⑩ build_issues → 6类IssueItem                                │
    │     ⑪ build_evidence → fact↔issue←evidence链                     │
    │     ⑫ build_context_pack → GenerationContextPack                  │
    │     ⑬ generate_chapters → 4章LLM / placeholder                   │
    │     ⑭ check_consistency → 3条规则                                 │
    │     ⑮ render_artifacts → .md + .docx + .json×4 + 批注版.docx     │
    │                                                                   │
    └────┬──────────────────────────────────────────────────────────────┘
         │
    SCCReviewResult {
        report_path, output_files{m任何8},
        company_name, overall_rating,
        findings[]: SCCFinding, module_validation,
        chapters[]: SCCChapter[4章],
        consistency_issues[], attachment_notes[]
    }
```

---

## 七、与旧版 scc 模块的关系

```
旧版 scc/（backend/modules/scc/）：
  - 通用SCC审查（含CN标准合同）
  - 基于generate_chapter的LLM报告
  - 表单驱动 + uploaded_files
  - 使用 render_commented_docx 生成批注版报告

新版 eu_scc/（backend/modules/eu_scc/）：
  - 独立EU SCC审查（EU 2021/914）
  - 确定性规则引擎（5组件8阶段）
  - 文档驱动（scc_text全文输入）
  - 使用 WorkflowPipeline 编排
  - 使用 render_commented_docx 生成批注版报告

两个模块并存，通过不同的API端点区分：
  - /scc/generate      ← 旧版
  - /eu_scc/generate    ← 新版
```

---

## 八、关键设计决策

| 维度 | 实现方式 |
|------|---------|
| 管线架构 | WorkflowPipeline — 12个callable注入 |
| 文档解析 | 正则+启发式 — 模块识别→章节分拆→18条Clause提取→4个Annex提取 |
| 规则引擎 | 确定性纯Python — 5组件，全部规则硬编码，无LLM依赖 |
| 模块验证 | 4种模块的角色映射表（C2C/C2P/P2P/P2C） |
| 条款比对 | 6组关键条款+15条弱化信号正则 |
| 附录审查 | Annex I.A(主体完整性)/I.B(数据类别+特殊类别)/II(TOMs)/III(子处理者) |
| TIA审查 | 第三国识别(22国充分性表)→TIA有无→Schrems II三类措施→美国特有风险→子处理者链条 |
| 批注版DOCX | render_commented_docx — findings作为批注插入源SCC文档 |
| 总评分 | 取最高严重度 |
| LLM角色 | 仅用于4章写作（含占位兜底），不参与核心审查判断 |
| 全链路trace | TraceRecorder记录规则引擎结果+pipeline各阶段 |

## 九、回归验证状态

```
模块验证:        C2C→Module One, C2P→Module Two ✓
条款弱化检测:     15条正则覆盖6组关键条款 ✓
附录完整性:       Annex I.A(主体)/I.B(特殊类别)/II(TOMs) ✓
第三国识别:       22国充分性表匹配 ✓
TIA缺失检测:      has_third_country + !has_tia → HIGH finding ✓
Schrems II检测:   3类措施关键词扫描 ✓
美国特有风险:      US CLOUD Act / FISA 702检测 ✓
子处理者链条:      非充分性国家子处理者 → MEDIUM finding ✓
4章报告:          LLM生成 或 placeholder渲染 ✓
批注版DOCX:        findings→comments插入源docx ✓
```
