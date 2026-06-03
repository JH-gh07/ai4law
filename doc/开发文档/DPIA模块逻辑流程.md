# DPIA 模块逻辑流程

> GDPR Data Protection Impact Assessment (Article 35) 草案生成 Pipeline  
> 基于 WP248 高风险标准、ICO DPIA 模板、EDPB 指南

---

## 一、整体架构

系统以 `WorkflowPipeline`（16步编排引擎）为核心，输入为 `DPIARequest`（7组DPIA模板字段），输出为 `DPIAResult`（7章草案 + 风险矩阵 + 证据链 + 14个输出文件）。

```
DPIARequest  →  [16步 WorkflowPipeline]  →  DPIAResult
                  │
                  ├── 阶段一：事实构建（步骤1-5）
                  ├── 阶段二：问题识别与证据链（步骤6-9）
                  ├── 阶段三：法规绑定与生成策略（步骤10）
                  ├── 阶段四：LLM生成与一致性检查（步骤11-13）
                  ├── 阶段五：修复与渲染（步骤14-16）
```

---

## 二、数据模型层次

```
DPIARequest (7组40+字段)
    ├── 组1 识别需求: project_name, project_goal, dpia_trigger_reasons
    ├── 组2 处理活动: processing_flow_description, data_categories,
    │                special_category_data, automated_decision_making,
    │                systematic_monitoring, cross_border_transfer, 等12项
    ├── 组3 咨询过程: consulted_internal_departments, external_experts,
    │                data_subject_consultation_plan
    ├── 组4 必要性与相称性: lawful_basis, necessity_statement,
    │                       proportionality_statement, transparency_information
    ├── 组5 风险评估: identified_risks (list[RiskInput])
    ├── 组6 缓解措施: mitigation_measures (list[MitigationInput])
    └── 组7 签署记录: dpia_owner, dpo_name, dpo_opinion, review_date

RiskInput: risk_id, risk_description, likelihood(low/medium/high),
           impact(low/medium/high), affected_data_subjects, risk_source

MitigationInput: mitigation_id, description, target_risk_ids,
                 status(planned/in_progress/implemented/verified), responsible_party

DPIAProjectProfile: 处理活动画像（25字段，非企业画像）

DPIANeedAssessment: dpia_required, trigger_reasons, legal_basis,
                    prior_consultation_possible, reasoning

FactItem (shared): fact_id, source_type(schema/attachment/diagnosis),
                   field_path, value, normalized_value, confidence,
                   evidence_status(user_claim_only/partial_evidence/documented_evidence),
                   can_support_external_positive_claim

IssueItem (shared): issue_id, title, description, category, severity,
                    fact_refs, rule_refs, evidence_refs, recommended_action,
                    affects_outputs (→ 映射到7个DPIA章节)

EvidenceItem (shared): evidence_id, claim, fact_refs, rule_refs,
                       conclusion, confidence, used_by

RegulationHit: source_id, title, article, snippet

DPIAChapterContent: chapter_no, title, content, citations, risk_level

DPIAResult: task_id, state, report_path, output_files, profile,
            regulations, chapters, consistency_issues, need_assessment,
            risk_matrix, mitigation_plan
```

---

## 三、逐步骤详细逻辑

### 步骤 1 — extract_profile（画像提取）

**文件**: `backend/modules/dpia/profile_extractor.py`  
**输入**: `DPIARequest`  
**输出**: `DPIAProjectProfile`

**逻辑**:
1. 将 `DPIARequest` 的所有字段直接映射到 `DPIAProjectProfile`（处理活动画像，非企业画像）
2. 调用 `FileParser` 解析 `uploaded_files` 中的附件
3. 调用 `parse_attachment_metadata()` 提取附件元数据（类型、字数、摘要）
4. 附件语义识别：数据流程图、隐私政策、算法说明、公平性审计报告、DPO意见文件、RoPA等

---

### 步骤 2 — evaluate_diagnosis（DPIA必要性判断）

**文件**: `backend/modules/dpia/need_detector.py`  
**输入**: `DPIARequest`  
**输出**: `DPIANeedAssessment`

**逻辑**:
1. 逐一检查 `DPIARequest` 的8个布尔字段，匹配 WP248 高风险标准：

| 字段 | WP248 标准 | 法规依据 |
|------|-----------|---------|
| `automated_decision_making` | 自动化决策/画像对个人产生法律效力 | GDPR Art 22, WP251 |
| `systematic_monitoring` | 公共区域大规模系统性监控 | GDPR Art 35, WP248 |
| `special_category_data` | 处理特殊类别个人数据 | GDPR Art 9 |
| `large_scale_processing` | 大规模处理个人数据 | GDPR Art 35, WP248 |
| `data_matching` | 数据匹配或重识别组合 | GDPR Art 35, WP248 |
| `new_technology` | 使用新技术处理方式 | GDPR Art 35(1) |
| `vulnerable_data_subjects` | 处理弱势数据主体 | GDPR Art 35, WP248 |
| `cross_border_transfer` | 跨境传输需额外保障评估 | GDPR Art 44, 46 |

2. **关键词增强检测**: 对 `project_goal` 做关键词扫描（"评估/评分/排名/预测/分类/画像/scoring/ranking/profiling/evaluation/predict"），若命中且尚未触发 automated_decision_making，追加 profiling 触发项

3. **事先咨询判断**: `dpia_required=True` 且触发 ≥2 项高风险标准 → `prior_consultation_possible=True`

4. **构建推理文本**: 逐项列出触发原因，若需事先咨询则追加 Art 36 建议

---

### 步骤 3 — validate_path（路径验证）

**文件**: `backend/modules/dpia/service.py:_noop_validate`  
**逻辑**: DPIA 不需要路径验证（不像 assessment 模块需要判断 security_assessment/standard_contract/certification），直接返回 `None`

---

### 步骤 4 — build_facts（事实构建）

**文件**: `backend/modules/dpia/fact_builder.py`  
**输入**: `DPIARequest` + `DPIAProjectProfile` + `DPIANeedAssessment`  
**输出**: `list[FactItem]`（约35-45条）

**逻辑**:

**a) Schema 事实（约32条）**:
- 来源: `DPIARequest` 的每个字段
- `source_type="schema"`, `confidence=0.6`, `evidence_status="user_claim_only"`
- `can_support_external_positive_claim=False`（不可作为外部报告正面结论的唯一依据）
- 示例: `DPIA-FACT-dpia-project-name`, `DPIA-FACT-dpia-automated-decision-making`, `DPIA-FACT-dpia-special-category-data`

**b) 附件事实（约1-5条）**:
- 来源: `profile.extracted_notes`
- `source_type="attachment"`, `confidence=0.8`, `evidence_status="partial_evidence"`
- 示例: `DPIA-FACT-attachment-note-1`

**c) 诊断事实（4条）**:
- 来源: `DPIANeedAssessment`
- `source_type="diagnosis"`, `confidence=1.0`, `evidence_status="documented_evidence"`
- `can_support_external_positive_claim=True`
- 示例: `DPIA-FACT-dpia-need-dpia-required`, `DPIA-FACT-dpia-need-prior-consultation-possible`

**d) 风险输入事实**:
- 逐条 `RiskInput` 展开: `dpia.identified_risks.{risk_id}`
- 值格式: `"{description} (likelihood={likelihood}, impact={impact})"`

**e) 缓解措施事实**:
- 逐条 `MitigationInput` 展开: `dpia.mitigation_measures.{mitigation_id}`
- 值格式: `"{description} (status={status})"`

---

### 步骤 5 — retrieve_regulations（法规检索）

**文件**: `backend/modules/dpia/retriever.py`  
**输入**: `DPIAProjectProfile`  
**输出**: `list[RegulationHit]`

**逻辑**:
1. 从 `DPIAProjectProfile` 提取关键信息拼接检索查询串:
   ```
   "DPIA GDPR Article 35" + project_goal + processing_flow_description
   + (if special_category_data) "special category data Article 9"
   + (if automated_decision_making) "automated decision making Article 22"
   + (if systematic_monitoring) "systematic monitoring WP248"
   + (if cross_border_transfer) "cross border transfer {transfer_destination}"
   + lawful_basis 各项
   ```
2. 通过 `RetrievalOrchestrator` 检索（`module="eu_dpia"`, `jurisdiction="eu"`, `path="dpia"`）
3. 再调用 `retrieve_regulations()` 获取 `RegulationHit` 列表（source_id, title, article, snippet）

---

### 步骤 6 — build_attachment_notes（附件解析摘要）

**文件**: `backend/modules/dpia/service.py:_attachment_notes_from_profile`  
**输入**: `DPIAProjectProfile`  
**输出**: `list[dict[str, str]]`

**逻辑**:
1. 优先从 `profile.attachment_metadata` 提取（结构化元数据，含 type/filename/char_count/summary）
2. 降级到 `profile.extracted_notes`（字符串格式 "filename: summary"）

---

### 步骤 7 — build_issues（问题识别）

**文件**: `backend/modules/dpia/issue_builder.py`  
**输入**: `facts` + `diagnosis` + `regulations` + `attachment_notes`  
**输出**: `list[IssueItem]`（12-18条，取决于触发条件）

**逻辑** — 18种DPIA issue类型：

| # | Issue ID | 类别 | 严重度 | 触发条件 | 影响章节 |
|---|----------|------|--------|---------|---------|
| 1 | `DPIA-ISSUE-automated-decision` | automated_decision | HIGH | `automated_decision_making=True` | need_identification, processing_description, necessity_proportionality, risk_assessment, mitigation, signoff |
| 2 | `DPIA-ISSUE-profiling-risk` | profiling | HIGH | project_goal 含"评估/评分/排名/画像"等关键词 | need_identification, processing_description, risk_assessment, mitigation |
| 3 | `DPIA-ISSUE-special-category` | special_category | HIGH | `special_category_data=True` | need_identification, processing_description, necessity_proportionality, risk_assessment, mitigation, signoff |
| 4 | `DPIA-ISSUE-large-scale` | large_scale | HIGH | `large_scale_processing=True` | need_identification, processing_description, risk_assessment, mitigation |
| 5 | `DPIA-ISSUE-systematic-monitoring` | systematic_monitoring | HIGH | `systematic_monitoring=True` | need_identification, processing_description, risk_assessment, mitigation, signoff |
| 6 | `DPIA-ISSUE-data-matching` | data_matching | MEDIUM | `data_matching=True` | processing_description, necessity_proportionality, risk_assessment |
| 7 | `DPIA-ISSUE-new-technology` | new_technology | MEDIUM | `new_technology=True` | need_identification, processing_description, risk_assessment, mitigation |
| 8 | `DPIA-ISSUE-vulnerable-subjects` | vulnerable_subjects | HIGH | `vulnerable_data_subjects=True` | need_identification, processing_description, risk_assessment, mitigation, signoff |
| 9 | `DPIA-ISSUE-necessity-weak` | necessity_proportionality | HIGH | `necessity_statement` < 50字符 | necessity_proportionality, risk_assessment |
| 10 | `DPIA-ISSUE-proportionality-weak` | necessity_proportionality | MEDIUM | `proportionality_statement` < 50字符 | necessity_proportionality, risk_assessment |
| 11 | `DPIA-ISSUE-lawful-basis-unclear` | lawful_basis | HIGH | `lawful_basis` 为空 | necessity_proportionality, signoff |
| 12 | `DPIA-ISSUE-consent-not-free` | lawful_basis | HIGH | special_category_types 含"健康/health/医疗/medical" | necessity_proportionality, risk_assessment, signoff |
| 13 | `DPIA-ISSUE-transparency-gap` | transparency | MEDIUM | `transparency_information` < 50字符 | processing_description, necessity_proportionality |
| 14 | `DPIA-ISSUE-discrimination-risk` | discrimination | HIGH | automated_decision_making **且** special_category_data 同时为 True | risk_assessment, mitigation, signoff |
| 15 | `DPIA-ISSUE-cross-border-risk` | cross_border | HIGH | `cross_border_transfer=True` **且** transfer_destination 不在欧盟充分性认定国家列表中 | processing_description, risk_assessment, mitigation, signoff |
| 16 | `DPIA-ISSUE-mitigation-insufficient` | mitigation_gap | HIGH/MEDIUM | 风险数 > 缓解措施数 | risk_assessment, mitigation, signoff |
| 17 | `DPIA-ISSUE-prior-consultation-needed` | prior_consultation | **BLOCKER** | `prior_consultation_possible=True` | signoff |
| 18 | `DPIA-ISSUE-dpo-opinion-missing` | documentation | MEDIUM | `dpo_opinion` 为空 | signoff |

**触发逻辑分三类**:
- **布尔触发**: Issue #1-8 — 检查对应字段的 `bool` 值
- **文本长度触发**: Issue #9, 10, 13 — 检查对应文本字段 `< 50` 字符
- **组合触发**: Issue #14（automated_decision + special_category）、#15（cross_border + 非充分性认定国家）、#16（风险数 vs 缓解数对比）

每个 issue 的 `affects_outputs` 精确映射到7个DPIA章节ID：
```
need_identification / processing_description / consultation
/ necessity_proportionality / risk_assessment / mitigation / signoff
```

**附件增强检测** (`_attachment_evidence`):
- 扫描 attachment_notes 识别：数据流程图、隐私政策、算法说明、公平性审计、安全评估、同意流程、DPO意见文件、RoPA、数据清单、保障措施文档

---

### 步骤 8 — build_evidence（证据链构建）

**文件**: `backend/modules/dpia/evidence_builder.py`  
**输入**: `facts` + `issues` + `regulations`  
**输出**: `(list[IssueItem], list[EvidenceItem])`

**逻辑**:
1. 对每个有 fact_refs 的 issue，创建对应的 `EvidenceItem`
2. **claim**（主张）和 **conclusion**（结论）来自18种DPIA issue的中文措辞映射 `_EVIDENCE_WORDING`
3. **rule_refs** 优先使用 issue 自身的 rule_refs，降级到 retain regulation 的 source_id（取前3条）
4. **confidence 评分规则**:
   - `severity ∈ {HIGH, BLOCKER}` 且有 rule_refs → **0.9**
   - `severity ∈ {HIGH, BLOCKER}` 无 rule_refs → **0.8**
   - `severity = MEDIUM` → **0.75**
   - 其他 → **0.6**
5. **evidence_id** 格式: `DPIA-EVIDENCE-{issue_id除去DPIA-ISSUE-前缀}`
6. 将 evidence_id 回写到 issue 的 `evidence_refs` 字段

---

### 步骤 9 — retrieve_per_issue（逐问题检索）

**逻辑**: DPIA 不启用逐问题外部法律API检索（不同于 assessment 模块的 DeliLegal search_laws/search_cases），设为 `None`

---

### 步骤 10 — build_context_pack（生成上下文包）

**文件**: `backend/modules/dpia/service.py:_build_context_pack`  
**输入**: `facts` + `issues` + `regulations` + `evidence_chain` + `attachment_notes`  
**输出**: `GenerationContextPack`

**逻辑** — 串联三个子步骤：

**a) 法规绑定 (legal_grounding)**:
- 调用 [legal_grounding.py](backend/modules/dpia/legal_grounding.py) 中的 `build_dpia_legal_grounding()`
- **三阶段重排序引擎**:
  - **S1 主源匹配 (0–0.40)**: 将 issue.category 与 `DPIA_ISSUE_LEGAL_SOURCE_MAP`（16个类别→GDPR Art 35/22/9/5/6/13/14/44/46、WP248/251/260、EDPB Guidelines、ICO Guidance）匹配，直接 rule_refs 命中+0.30，法规标题匹配按权重+0.25×weight，条文级匹配额外+0.10
  - **S2 内容相关性 (0–0.30)**: 查询词与法规文本的 token 重叠（每个token+0.04，上限0.25）+ category hint 命中(+0.05)
  - **S3 权威调整 (0–0.28)**: authority_level(high/medium/low → 0.15/0.10/0.05) + binding_force(mandatory/recommended/reference → 0.08/0.04/0.02) + severity boost(HIGH/BLOCKER +0.05)
  - **总分上限 0.98**

- `DPIA_ISSUE_LEGAL_SOURCE_MAP` 示例:
  ```python
  "automated_decision": [
      {"title": "GDPR", "article": "Article 22", "weight": 1.0},
      {"title": "WP251", "article": "", "weight": 0.9},
      {"title": "EDPB Guidelines", "article": "automated decision", "weight": 0.8},
  ]
  ```

- 法规权威级别推断（EU语境）:
  - GDPR Article → authority=high, binding=mandatory
  - WP248/WP251/WP260/EDPB → authority=medium, binding=recommended
  - ICO/Template/Standard → authority=low, binding=recommended

**b) 表达策略 (writing_strategy)**:
- 调用 [writing_strategy_builder.py](backend/modules/dpia/writing_strategy_builder.py) 中的 `build_writing_strategy()`
- 为每个 issue 生成：
  - `internal_expression`: 内部使用的技术性描述（问题+建议）
  - `external_expression`: 对外报告的审慎措辞
  - `forbidden_expressions`: 该 issue 专属的禁用措辞
- **11项全局禁用措辞**:
  ```
  "风险已完全消除"、"不存在歧视风险"、"已充分取得所有同意"、
  "匿名化后无任何个人数据风险"、"自动化决策不影响个人权利"、
  "无需进一步监管沟通"、"可直接上线"、"完全符合GDPR要求"、
  "不涉及个人数据"、"数据处理绝对安全"、"彻底解决了隐私问题"
  ```
- **全局外部基调**: "审慎、正式、避免绝对化断言。使用'建议''可能''尚需'等审慎措辞"

**c) 生成依据包 (generation_basis_pack)**:
- 调用 [generation_basis.py](backend/modules/dpia/generation_basis.py) 中的 `build_generation_basis_pack()`
- 按7个DPIA章节将数据精筛到 `section_packs`:
  - 每个 section_pack 包含: confirmed_facts, issues, legal_basis, legal_grounding, writing_strategies, evidence_refs, missing_materials
  - `affects_outputs` 字段决定 issue 归属到哪些章节

---

### 步骤 11 — generate_chapters（LLM生成7章）

**文件**: `backend/modules/dpia/chapter_generator.py`  
**输入**: `profile` + `regulations` + `context_pack`  
**输出**: `list[DPIAChapterContent]`（7章）

**逻辑**:

| # | 章节ID | 标题 | LLM指令要点 |
|---|--------|------|-----------|
| 1 | `need_identification` | 识别需求 (Identify Need for DPIA) | 项目背景、WP248触发理由、Art 35法律依据、Art 36事先咨询可能性 |
| 2 | `processing_description` | 描述处理活动 (Describe the Processing) | 数据全生命周期、数据类别清单、特殊类别标注、自动化决策/画像/监控/跨境/新技术使用、保留期限 |
| 3 | `consultation` | 咨询过程 (Consultation Process) | 内部部门咨询、外部专家、数据主体咨询计划、DPO参与情况 |
| 4 | `necessity_proportionality` | 必要性与相称性 (Necessity & Proportionality) | Art 6合法性基础、Art 9豁免条件、必要性论证、相称性分析、Art 13/14透明度评估 |
| 5 | `risk_assessment` | 风险识别与评估 (Identify & Assess Risks) | 风险矩阵（描述/可能性/影响/等级）、风险来源分析、受影响主体、歧视/跨境/弱势群体重点风险 |
| 6 | `mitigation` | 降低风险的措施 (Mitigation Measures) | 缓解措施清单（对应具体风险）、实施状态、负责方、残余风险水平、未覆盖风险标注 |
| 7 | `signoff` | 签署与记录 (Sign Off & Record Outcomes) | DPIA负责人、DPO审查意见、整体结论、Art 36事先咨询建议、复审日期和触发条件 |

**System Prompt**: "欧盟GDPR资深数据保护律师"

**严格写作约束**:
1. 仅使用上下文提供的事实与法规条文，不得新增数据类别/主体/场景
2. 引用使用 `{{CIT-xxx}}` 标记
3. 对外报告只能使用 external_expression，不得使用 internal_expression
4. 不得出现全局禁用表达中的任何措辞
5. user_claim_only 事实不得作为外部正面结论的唯一依据
6. signoff 章节如 prior_consultation_possible=True，必须声明残余高风险并建议 Art 36 事先咨询

**上下文构建**: `build_context_block_from_pack()` 从 per-section pack 筛选数据：
- 确认事实（field_path → value）
- 法规依据（source_id | title article : snippet）
- 相关问题（issue_id | severity | title : description）
- 法律绑定（issue_id → title article confidence_score）
- 表达策略（external_expression + forbidden_expressions）
- 全局禁用表达

---

### 步骤 12 — check_consistency（一致性检查）

**文件**: `backend/modules/dpia/consistency_checker.py`  
**输入**: `profile` + `chapters` + `context_pack`  
**输出**: `list[str]`

**9项DPIA专属检查**:

| # | 检查项 | 检测逻辑 |
|---|--------|---------|
| 1 | DPIA触发覆盖 | diagnosis.dpia_required=True 但报告中未提及 "Article 35" / "WP248" |
| 2 | 处理描述完整性 | 检查报告中是否包含 "数据流/收集/处理/存储/删除"、"数据类别/data categor"、"保留期/retention" |
| 3 | 咨询过程记录 | 检查报告中是否提及 "咨询/consult/DPO" |
| 4 | 必要性/相称性 | 检查 "必要性/necessity"、"相称性/proportionality"、"Art 6" |
| 5 | 风险矩阵完整 | 每个 HIGH/BLOCKER issue 的 issue_id 或 title 是否在报告中出现 |
| 6 | 缓解措施可验证性 | 检查是否存在模糊措辞（"加强管理"、"提升意识"、"持续关注"、"定期检查"） |
| 7 | DPO意见集成 | 检查报告中是否提及 "DPO" |
| 8 | Art 36 事先咨询 | prior_consultation_possible=True 但报告中未提及 "Art 36" / "Article 36" |
| 9 | 禁用措辞检测 | 扫描8项预设禁用措辞（"风险已完全消除"、"可直接上线"等） |

**通用检查（延续 assessment 模式）**:
- 交叉引用完整性: issue/evidence 引用的 fact_id/rule_ref/evidence_ref 是否存在于上下文
- 内部表达泄漏: internal_expression 片段是否出现在外部报告
- user_claim_only 滥用: user_claim_only 事实是否被用作正面确定性结论的依据
- 全局策略禁用措辞: writing_strategy 中 global_forbidden 和 issue_forbidden 的检测

---

### 步骤 13 — check_alignment（对齐检查）

**文件**: `backend/modules/dpia/service.py:_noop_check_alignment`  
**逻辑**: DPIA 不需要对齐检查（与 assessment 模块不同），直接返回 `[]`

---

### 步骤 14 — repair_chapters（修复循环）

**文件**: `backend/modules/dpia/repair_generator.py`  
**输入**: `chapters` + `consistency_issues` + `profile` + `context_pack`  
**输出**: `(repaired_chapters, remaining_issues, blocked)`

**逻辑**:

**问题分类**:

| 类别 | Marker | 说明 |
|------|--------|------|
| **可修复** | citation_missing | 追加 "【依据：本章暂未引用GDPR条文】" |
| **可修复** | forbidden_expression | 替换为 "【已移除禁用措辞：⋯】" |
| **可修复** | internal_leakage | 替换为 "【内部表述已移除】" |
| **可修复** | user_claim_positive | 追加 "【依据为企业自述，须进一步验证】" |
| **可修复** | trigger_ref_missing | 在第1章追加 WP248 引用说明 |
| **可修复** | description_incomplete | 在第2章追加 "【需补充】缺少XX相关描述" |
| **可修复** | vague_mitigation | 在第6章追加 "【缓解措施具体化要求】" |
| **可修复** | dpo_mention_missing | 在第7章追加 "【待补充】DPO审查意见" |
| **可修复** | art36_missing | 在第7章追加 "【事先咨询建议】GDPR Article 36" |
| **阻断** | missing_fact_ref / missing_rule_ref | 引用不存在的 fact/rule — 需修正输入数据 |
| **阻断** | missing_high_issue | 高危issue完全未提及 — 需重新生成章节 |
| **阻断** | case_in_external | 案例引用泄漏到外部报告 — 需重新生成 |

**修复循环**:
1. 分类当前 issues → fixable + blockers
2. 对每个 fixable 执行文本替换/追加修复
3. 重新调用 `DPIAConsistencyChecker.check_with_context()` 检查
4. 若仅剩阻断性 issues → 设置 `blocked=True`，停止循环
5. 最多重复3轮

---

### 步骤 15 — render_artifacts（渲染输出）

**文件**: `backend/modules/dpia/report_renderer.py`  
**输入**: `profile` + `chapters` + `issues` + `evidence` + `facts` + `need_assessment` + `legal_grounding` + `writing_strategy` + `generation_basis_pack`  
**输出**: `dict[str, str]`（14个输出文件路径）

**输出制品**:

| # | 文件名 | 格式 | 内容 |
|---|--------|------|------|
| 1 | `{project}_DPIA草案_{date}.md` | Markdown | 完整7章DPIA草案 + DPIA必要性预判 |
| 2 | `issue_list.json` | JSON | 问题清单（结构化） |
| 3 | `issue_list.xlsx` | Excel | 问题清单（表格） |
| 4 | `evidence_chain.json` | JSON | 证据链（结构化） |
| 5 | `evidence_chain.xlsx` | Excel | 证据链（表格） |
| 6 | `risk_matrix.json` | JSON | 风险矩阵 |
| 7 | `risk_matrix.xlsx` | Excel | 风险矩阵 |
| 8 | `mitigation_plan.json` | JSON | 缓解措施计划 |
| 9 | `mitigation_plan.xlsx` | Excel | 缓解措施计划 |
| 10 | `facts.json` | JSON | 事实清单 |
| 11 | `dpia_need_assessment.json` | JSON | DPIA必要性判断结果 |
| 12 | `legal_grounding.json` | JSON | 法规绑定结果 |
| 13 | `writing_strategy.json` | JSON | 表达策略 |
| 14 | `generation_basis_pack.json` | JSON | 生成依据包 |
| 15 | `citation_map.json` | JSON | 引用映射表 |
| 16 | `consistency_issues.json` | JSON | 一致性问题清单 |
| 17 | `trace_manifest.json` | JSON | 全链路追踪 |
| 18 | `{project}_DPIA输出包_{date}.zip` | ZIP | 完整输出包（包含以上所有文件） |

---

## 四、API端点

**文件**: `backend/modules/dpia/router.py`

| 端点 | 方法 | 功能 | 请求体 | 响应体 |
|------|------|------|--------|--------|
| `/api/v1/dpia/generate` | POST | 同步生成DPIA草案 | `DPIARequest` | `DPIAResult` |
| `/api/v1/dpia/generate_async` | POST | 异步提交任务 | `DPIARequest` | `DPIAAsyncAccepted`（含task_id） |
| `/api/v1/dpia/tasks/{task_id}` | GET | 查询异步任务状态 | — | `DPIAAsyncStatus`（完成时含DPIAResult） |
| `/api/v1/dpia/tasks/{task_id}/retry` | POST | 重试失败任务 | — | `DPIAAsyncStatus` |

**异步任务管理**: 基于 `InMemoryTaskManager`（module="dpia"）

**任务所有权**: `TASK_OWNERS` 字典追踪每个 task_id 的创建用户，防止跨用户访问

---

## 五、工具函数模块一览

| 文件 | 类/函数 | 职责 |
|------|---------|------|
| [schema.py](backend/modules/dpia/schema.py) | `DPIARequest`, `DPIAProjectProfile`, `DPIANeedAssessment`, `RegulationHit`, `DPIAChapterContent`, `DPIAResult`, `DPIAAsyncAccepted`, `DPIAAsyncStatus`, `RiskInput`, `MitigationInput` | 数据模型定义 |
| [profile_extractor.py](backend/modules/dpia/profile_extractor.py) | `DPIAProfileExtractor.extract()` | 提取处理活动画像 |
| [need_detector.py](backend/modules/dpia/need_detector.py) | `DPIANeedDetector.evaluate()` | WP248高风险标准判断 |
| [fact_builder.py](backend/modules/dpia/fact_builder.py) | `build_dpia_facts()` | 构建结构化事实列表 |
| [issue_builder.py](backend/modules/dpia/issue_builder.py) | `build_dpia_issues()` | 识别18种DPIA合规问题 |
| [evidence_builder.py](backend/modules/dpia/evidence_builder.py) | `build_dpia_evidence()` | 构建事实→法规证据链 |
| [retriever.py](backend/modules/dpia/retriever.py) | `DPIARetriever.search()` | GDPAR/WP/EDPB法规检索 |
| [legal_grounding.py](backend/modules/dpia/legal_grounding.py) | `build_dpia_legal_grounding()` | 三阶段法规重排序 |
| [writing_strategy_builder.py](backend/modules/dpia/writing_strategy_builder.py) | `build_writing_strategy()` | 内外部措辞策略 |
| [generation_basis.py](backend/modules/dpia/generation_basis.py) | `build_generation_basis_pack()` | 按章节精筛数据 |
| [chapter_generator.py](backend/modules/dpia/chapter_generator.py) | `DPIAChapterGenerator.generate()` | LLM生成7章草案 |
| [consistency_checker.py](backend/modules/dpia/consistency_checker.py) | `DPIAConsistencyChecker.check_with_context()` | 9项一致性检查 |
| [repair_generator.py](backend/modules/dpia/repair_generator.py) | `run_dpia_repair_pass()` | 修复循环 |
| [report_renderer.py](backend/modules/dpia/report_renderer.py) | `DPIAReportRenderer.render()` | 渲染14个输出文件 |
| [service.py](backend/modules/dpia/service.py) | `DPIAService` | 16步Pipeline编排 |
| [router.py](backend/modules/dpia/router.py) | 4个端点 | HTTP API |
| [tests/test_service.py](backend/modules/dpia/tests/test_service.py) | 12个单元测试 | 覆盖全部Pipeline步骤 |
| [tests/test_async_api.py](backend/modules/dpia/tests/test_async_api.py) | 异步集成测试 | 端到端异步流程 |

---

## 六、关键设计决策

| 决策 | 理由 |
|------|------|
| `validate_path` 设为 no-op (返回 None) | DPIA 不需要路径验证（不像 assessment 需要判断 security_assessment/standard_contract/certification） |
| `check_alignment` 设为 no-op (返回 []) | DPIA 对齐检查由 consistency_checker 的9项专项检查覆盖 |
| `retrieve_per_issue` 设为 None | 法规绑定完全由本地三阶段重排序引擎完成，不依赖外部法律API |
| Issue severity 引入 BLOCKER 级别 | `prior_consultation_needed` 是无法通过文本修复解决的阻断性问题 |
| schema FactItem 的 evidence_status 标记为 user_claim_only | 用户填报数据不可作为外部报告正面结论的唯一依据 |
| diagnosis FactItem 的 evidence_status 标记为 documented_evidence | 系统诊断结果置信度高，可作为外部结论依据 |
| 18种 issue 的 `affects_outputs` 精确映射到7个章节 | 每个 issue 仅在相关章节的 section_pack 中出现，避免无效上下文膨胀 |
| 修复最多3轮 | 防止无限循环；阻断性 issues 在第1轮后即终止 |
