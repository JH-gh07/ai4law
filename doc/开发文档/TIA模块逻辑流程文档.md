# TIA (Transfer Impact Assessment) 传输影响评估 — 全线模块逻辑流程

## 文件总览（17 个文件）

```
backend/modules/tia/
├── __init__.py                              ← 包标记
├── schema.py                    (133行)     ← 数据模型层（12个模型 + 5个枚举）
├── data/
│   └── tia_country_riskbook.json (89行)     ← 国家风险规则库
├── route_decider.py             (58行)      ← 路径判断器
├── country_risk.py              (39行)      ← 国家风险评估器
├── data_sensitivity.py          (53行)      ← 数据敏感性分类器
├── measure_sufficiency.py       (86行)      ← 补充措施充分性检查器
├── attachment_evidence.py        (69行)      ← 附件证据抽取器
├── agents/
│   ├── __init__.py                           ← TIAAgentBase + create_tia_agents()
│   ├── rag_planning_agent.py                 ← Agent 1: 多query检索规划
│   ├── attachment_review_agent.py            ← Agent 2: 附件证据深度审查
│   └── dpo_review_agent.py                   ← Agent 3: DPO质量闸门
├── service.py                   (316行)     ← 总调度器
├── router.py                    (82行)      ← API端点
└── tests/
    ├── __init__.py
    ├── test_service.py                       ← 基础功能测试
    └── test_async_api.py                     ← 异步API测试
```

**依赖的外部公共组件**：

```
backend/common/llm/client.py           → LLMClient
backend/common/llm/module_generator.py → generate_chapter()（TIA专用6章 prompt）
backend/common/rag/retriever.py        → retrieve_regulations()
backend/common/render/report.py        → render_docx_template / render_markdown_template
backend/common/storage/file_parser.py  → FileParser
backend/common/tasks/manager.py        → InMemoryTaskManager
```

---

## 一、数据模型层

### 模块 1：schema.py — 12 个模型 + 5 个枚举

**文件**：`backend/modules/tia/schema.py`

**按生成时间分两代**：

#### 第一代（原有）—— 表单驱动输出

- **TIAAttachment**：`file_role`（transfer_agreement / country_law_analysis / technical_control_doc / other），`file_name`，`file_format`（docx/pdf），`storage_uri`，`size_bytes?`，`checksum_sha256?`

- **TIAChapter**：`chapter_no, title, content, citations[], risk_level`

- **TIAResult**：`report_path, output_files, transfer_tool, risk_level, chapters[], consistency_issues[], attachment_notes[]`，以及新增的 `route_decision?, country_risk?, measure_assessments[]`

#### 第二代（新增）—— 结构化输入 + 判断输出

- **DataCategory**：18 种枚举值（`contact_information, transaction_records, crm_data, employee_data, hr_records, financial_data, health_data, genetic_data, biometric_data, clinical_trial_data, political_opinion, religious_belief, children_data, location_data, behavioral_data, communication_content, other`）

- **TIAStructuredInput**：`exporter_country, importer_country, destination_country, transfer_purpose, data_categories[], has_special_category_data, special_category_types[], data_subjects[], transfer_frequency, transfer_scale, encryption_before_transfer, key_managed_in_eu, has_end_to_end_encryption, has_secure_enclave, has_key_separation` — 全部 Optional，向后兼容

- **TIARouteDecision**：`route`（adequacy_simplified / full_tia_scc / full_tia_bcr / derogation_exception / missing_or_invalid_tool），`need_full_tia, adequacy_decision_exists, adequacy_country, adequacy_notes[], reason`

- **TIACountryRisk**：`country, has_adequacy, risk_level`（LOW/MEDIUM/HIGH/VERY_HIGH），`risk_sources[], gov_access_risk, effective_remedy, independent_oversight, notes`

- **TIAMeasureAssessment**：`measure_name, measure_type`（contractual/organizational/technical_weak/technical_strong/technical_extreme），`sufficient_for_risk, assessment`

- **TIARequest**：保留原有 6 个自由文本字段 + attachments，新增 `structured_input: TIAStructuredInput | None` — 全部 Optional，向后兼容

---

## 二、数据层 — 国家风险规则库

### 模块 2：tia_country_riskbook.json

**文件**：`backend/modules/tia/data/tia_country_riskbook.json`

**3 个顶层 section**：

#### adequacy_countries（9 个国家）

| 国家 | 来源 | 注意事项 |
|------|------|---------|
| United Kingdom | EU-UK adequacy decision 2021 | Monitor adequacy decision renewal |
| Switzerland | EU adequacy decision | Monitor changes |
| Japan | EU adequacy decision 2019 | — |
| South Korea | EU adequacy decision 2021 | — |
| New Zealand | EU adequacy decision | — |
| Argentina | EU adequacy decision | — |
| Uruguay | EU adequacy decision | — |
| Israel | EU adequacy decision | — |
| Canada | Partial (PIPEDA) | Limited scope |

#### country_risks（4 个国家）

**United States**：
- adequacy: false，risk_level: HIGH
- risk_sources: ["FISA Section 702", "CLOUD Act", "EO 12333"]
- gov_access_risk: true，effective_remedy: false
- required_measures: ["encryption_before_transfer", "key_managed_in_eu"]

**United Kingdom**：
- adequacy: true，risk_level: LOW
- notes: "EU adequacy decision in force. No full TIA needed."

**India**：
- adequacy: false，risk_level: VERY_HIGH
- risk_sources: ["IT Act Section 69", "Government access powers", "Weak data protection framework"]
- required_measures: ["encryption_before_transfer", "key_managed_in_eu", "has_secure_enclave", "has_key_separation"]
- notes: "For clinical/genetic data, regulatory consultation is strongly advised."

**China**：
- adequacy: false，risk_level: VERY_HIGH
- risk_sources: ["Cybersecurity Law", "Data Security Law", "PIPL cross-border restrictions"]

#### 权重表

**data_sensitivity_weights**：18 种数据类别 → 整数权重（1-5）

**measure_sufficiency_thresholds**：4个风险等级 → 最低措施要求 + 合同措施是否单独足够：
- VERY_HIGH → technical_extreme，contractual_alone_sufficient=false
- HIGH → technical_strong，contractual_alone_sufficient=false
- MEDIUM → technical_weak，contractual_alone_sufficient=false
- LOW → contractual，contractual_alone_sufficient=true

---

## 三、判断引擎层（5 个独立检查器）

### 模块 3：route_decider.py — 路径判断器

**文件**：`backend/modules/tia/route_decider.py`

**类**：`TIARouteDecider`

**方法**：`decide(transfer_tool, structured_input) → TIARouteDecision`

**逻辑**：

```
① 提取目的地国家
   dest = structured.destination_country OR structured.importer_country

② 充分性决定检查（第一优先级）
   遍历 adequacy_countries 的 9 个国家名
   取子串匹配（country_name.lower() in dest.lower()）
   匹配 → adequacy_simplified, need_full_tia=False
          reason: "Destination has EU adequacy decision. No full TIA required."

③ SCC 路径
   tool == "scc" → full_tia_scc, need_full_tia=True
   reason: "SCC transfer to non-adequacy country — full TIA required."

④ BCR 路径
   tool == "bcr" → full_tia_bcr, need_full_tia=True

⑤ Derogation 路径
   tool == "derogation" → derogation_exception, need_full_tia=True
   reason: "Article 49 — assess strict necessity, occasional nature, explicit consent."

⑥ 兜底
   → missing_or_invalid_tool, need_full_tia=False
   reason: "No valid transfer tool identified."
```

**输出**：`TIARouteDecision { route, need_full_tia, adequacy_decision_exists, adequacy_country, adequacy_notes[], reason }`

---

### 模块 4：country_risk.py — 国家风险评估器

**文件**：`backend/modules/tia/country_risk.py`

**类**：`TIACountryRiskAssessor`

**方法**：`assess(structured_input) → TIACountryRisk`

**逻辑**：

```
① 提取目的地国家
   dest = structured.destination_country OR structured.importer_country

② 精确匹配
   遍历 country_risks 的 4 个国家
   if dest.lower() == country_name.lower() → 返回该国家的风险数据

③ 模糊匹配
   遍历 country_risks 的 4 个国家
   if country_name.lower() in dest.lower() → 返回该国家的风险数据

④ 未知国家
   → risk_level=MEDIUM, risk_sources=["No structured risk data"]
   notes: "No country risk profile found. Manual legal assessment required."
```

**输出**：`TIACountryRisk { country, has_adequacy, risk_level, risk_sources[], gov_access_risk, effective_remedy, independent_oversight, notes }`

---

### 模块 5：data_sensitivity.py — 数据敏感性分类器

**文件**：`backend/modules/tia/data_sensitivity.py`

**类**：`TIADataSensitivity`

**方法**：`assess(structured_input) → dict`

**逻辑**：

```
① if structured is None:
     → {sensitivity: "unknown", max_weight: 0, special_categories: [], risk_factor: 1.0}

② 逐类别查权重表
   for cat in structured.data_categories:
     w = data_sensitivity_weights[cat]  ← 1-5的整数
     if w > max_w: max_w = w
     if w >= 5: special_categories.append(cat)

③ 特殊类别标记
   if has_special_category_data:
     max_w = max(max_w, 5)
     special_categories += special_category_types

④ 敏感等级判定
   max_w >= 5 → very_high (risk_factor=2.0)    ← 健康/基因/生物识别/儿童/临床试验
   max_w >= 4 → high (risk_factor=1.5)          ← 金融/通信内容
   max_w >= 3 → medium_high (risk_factor=1.25)   ← 员工/HR/位置/行为
   max_w >= 2 → medium (risk_factor=1.0)         ← CRM
   其他 → low (risk_factor=0.75)

输出：{sensitivity, max_weight, special_categories[], risk_factor}
```

---

### 模块 6：measure_sufficiency.py — 补充措施充分性检查器

**文件**：`backend/modules/tia/measure_sufficiency.py`

**类**：`TIAMeasureSufficiency`

**方法**：`assess(structured_input, country_risk_level) → (list[TIAMeasureAssessment], overall_str)`

**逻辑**：

```
① 措施分级（从强到弱）：
   has_secure_enclave + has_key_separation
     → "安全飞地+密钥分离" (technical_extreme, sufficient_for_risk=True)
   has_end_to_end_encryption + key_managed_in_eu
     → "E2E加密+EU密钥" (technical_strong, sufficient_for_VERY_HIGH以外)
   encryption_before_transfer + key_managed_in_eu
     → "传输前加密+EU密钥" (technical_strong, sufficient_for_VERY_HIGH/HIGH以外)
   encryption_before_transfer only
     → "传输前加密" (technical_weak, sufficient_for_LOW以外)
   无加密
     → "仅合同措施" (contractual, 查规则书是否足够)

② 对照规则书阈值
   VERY_HIGH → minimum_level=technical_extreme, contractual_alone_sufficient=false
   HIGH      → minimum_level=technical_strong, contractual_alone_sufficient=false
   MEDIUM    → minimum_level=technical_weak
   LOW       → minimum_level=contractual

③ 整体判定
   措施等级 ≥ minimum_level → sufficient
   VERY_HIGH 且措施 < technical_extreme → highly_conditional
   HIGH 且措施 < technical_strong → conditional
   HIGH/VERY_HIGH + 仅合同措施 → insufficient

输出：(list[TIAMeasureAssessment], "sufficient"|"conditional"|"highly_conditional"|"insufficient"|"unknown")
```

---

### 模块 7：attachment_evidence.py — 附件证据抽取器

**文件**：`backend/modules/tia/attachment_evidence.py`

**类**：`TIAAttachmentEvidence`

**方法**：`extract(attachment: TIAAttachment) → dict`

**3 种 file_role 路由**：

#### transfer_agreement → 6 个 bool 检查

- `has_scc_mention`："scc|standard contractual clause|标准合同条款"
- `is_2021_914_scc`："2021/914|2021.*scc|scc.*2021"
- `has_module_selection`："module (one|two|three|four|1|2|3|4)"
- `has_gov_access_notice`："government.*access|government.*request|执法.*请求|政府.*访问"
- `has_onward_transfer_restriction`："onward.*transfer|sub.?processor|再传输"
- `has_audit_rights`："audit|inspection|审计|检查"

#### country_law_analysis → 6 个字段

- `countries_mentioned[]`：9 个国家名逐一匹配
- `has_gov_access_analysis`："government.*access|surveillance|监控|FISA"
- `has_remedy_assessment`："remedy|redress|救济|complaint|司法"
- `has_oversight_assessment`："oversight|independent|supervisory|独立|监管"
- `has_edpb_reference`："edpb|schrems|european data protection board"

#### technical_control_doc → 8 个 bool 检查

- `has_encryption_at_rest`："encryption.*rest|encryption.*storage|静态加密|存储加密"
- `has_encryption_in_transit`："encryption.*transit|encryption.*transport|传输加密|TLS|HTTPS"
- `has_end_to_end_encryption`："end.?to.?end.*encrypt|e2ee|端到端加密"
- `has_key_management`："key.*manage|key.*control|密钥管理|key.*rotation"
- `key_location_eu`："key.*(EU|Europe|Germany|France|Ireland|Netherlands)"
- `has_secure_enclave`："secure enclave|安全飞地|trusted execution|confidential computing|机密计算"
- `has_audit_logging`："audit.*log|审计.*日志|access.*log"
- `has_access_control`："access.*control|访问控制|RBAC|role.?based|MFA|2FA"

**输出**：每个 attachment 一个 dict，解析失败返回 `{"parse_error": True}`。

---

## 四、Agent 层（3 个 Agent）

### Agent Base

**文件**：`backend/modules/tia/agents/__init__.py`

**类**：`TIAAgentBase`

```
属性：
  agent_name: str = "base"
  temperature: float = 0.1
  max_tokens: int = 600

方法：
  enabled → bool
  _call_llm(prompt) → dict | None
  run(**kwargs) → dict

system prompt:
  "You are an EU data protection officer (DPO) specializing in TIA
   under GDPR, Schrems II, EDPB 01/2020, and SCC 2021/914."
```

---

### Agent 1：RAGPlanningAgent — 多query检索规划

**文件**：`backend/modules/tia/agents/rag_planning_agent.py`

**触发条件**：结构化输入非空

**逻辑**：

```
输入：transfer_tool, dest_country, data_categories, sensitivity,
      country_risk_level, has_spi, gov_access_risk, route

① 构建 prompt（含5个purpose的query模板）
② LLM生成4-5条针对性检索query：
   - transfer_tool_legal_basis → "GDPR Article 46 SCC BCR legal basis"
   - destination_law_risk → "{country} government access surveillance Schrems II"
   - supplementary_measures → "EDPB 01/2020 encryption key management"
   - data_protection → "GDPR Article 9 special category {cats} transfer safeguards"
   - remedy_oversight → "{country} independent oversight judicial remedy"

③ LLM不可用 → fallback到4个启发式query
④ 逐query并行检索 → 去重合并 → 最多8条
```

**输出**：
```json
{
  "queries": [{"purpose": "...", "query": "..."}, ...],
  "priority_order": ["transfer_tool_legal_basis", "destination_law_risk", "supplementary_measures"]
}
```

---

### Agent 2：AttachmentReviewAgent — 附件证据深度审查

**文件**：`backend/modules/tia/agents/attachment_review_agent.py`

**触发条件**：始终运行

**逻辑**：

```
输入：transfer_agreement_evidence, country_law_evidence,
      technical_control_evidence, structured_input_summary

① 格式化3类附件证据为文本块
② 与用户声明的structured_input对比
③ LLM判断：
   - 每条evidence的confidence (high/medium/low)
   - 是否存在冲突（用户声称 vs 附件实际）
   - 缺失的关键证据
   - 整体证据质量 (strong/adequate/weak/critical_gaps)

④ 冲突和缺失证据注入到报告attachment_notes
```

**输出**：
```json
{
  "evidence_items": [{"source": "file_role", "claim": "...", "confidence": "medium", "problem": "...", "recommendation": "..."}],
  "missing_evidence": ["...", "..."],
  "conflicts": ["用户声明E2E加密，但技术文档仅说明TLS传输加密"],
  "overall_evidence_quality": "adequate",
  "summary": "<one sentence overall>"
}
```

---

### Agent 3：DPOReviewAgent — DPO质量闸门

**文件**：`backend/modules/tia/agents/dpo_review_agent.py`

**触发条件**：始终运行

**逻辑**：

```
输入：route, country_risk_level, sensitivity, measure_overall,
      effective_risk, issues, chapter_summaries

① 检查报告是否弱化了规则引擎的风险判断
② 评估是否需要强制警告（VERY_HIGH场景）
③ 生成DPO立场和强制前置条件

④ 注入到报告：
   - non_reliance_warning_needed → 第一章顶部加警告
   - dpo_position → 追加到第一章
   - mandatory_conditions → 追加到第六章
```

**输出**：
```json
{
  "review_result": "approved|needs_revision|rejected",
  "critical_issues": ["SCC单独不足以对抗政府访问风险"],
  "risk_softening_detected": true|false,
  "dpo_position": "高度条件化同意，需安全飞地+密钥分离+监管咨询",
  "mandatory_conditions": ["实施安全飞地", "实施密钥分离", "完成第三方安全审计"],
  "review_plan_suggestion": "每6个月复审或法律变化时立即复审",
  "regulatory_consultation_required": true|false,
  "non_reliance_warning_needed": true|false
}
```

---

## 五、总调度层

### 模块 8：service.py — TIAService

**文件**：`backend/modules/tia/service.py`

**构造函数注入 11 个组件**：

```python
self.llm_client              ← LLMClient（6章生成）
self.parser                  ← FileParser（附件文本提取）
self.tasks                   ← InMemoryTaskManager(module="tia")
# 5 个规则判断组件
self.route_decider           ← TIARouteDecider
self.country_risk            ← TIACountryRiskAssessor
self.data_sensitivity        ← TIADataSensitivity
self.measure_sufficiency     ← TIAMeasureSufficiency
self.attachment_evidence     ← TIAAttachmentEvidence
# 3 个Agent
self.agents                  ← create_tia_agents(llm_client)
```

#### 主方法：`generate_report(payload) → TIAResult`

**分两路径**：

- `payload.structured_input` 非空 → 走新路径（结构化评估）
- `payload.structured_input` 为空 → 走旧路径（关键词风险标签 fallback）

**新路径 — 10 步流程**：

```
① 路径判断
   route = self.route_decider.decide(transfer_tool, structured_input)
   → adequacy_simplified / full_tia_scc / full_tia_bcr / derogation / missing_tool

② 国家风险评估
   country_risk_result = self.country_risk.assess(structured_input)
   → country + risk_level(VERY_HIGH/HIGH/MEDIUM/LOW) + risk_sources

③ 数据敏感性评估
   data_sens = self.data_sensitivity.assess(structured_input)
   → sensitivity + risk_factor + special_categories

④ 复合风险评估
   if country_risk_level == "VERY_HIGH" or sensitivity == "very_high":
     effective_risk = "VERY_HIGH"
   elif country_risk_level == "HIGH" or risk_factor >= 1.5:
     effective_risk = "HIGH"
   else: effective_risk = country_risk_level

⑤ 补充措施充分性
   measure_assessments, measure_overall = self.measure_sufficiency.assess(structured_input, effective_risk)
   → 措施分级 + sufficiency 判定

⑥ 系统风险等级
   if effective_risk == "VERY_HIGH" or measure_overall == "insufficient":
     level = "HIGH"
   elif effective_risk == "HIGH" or measure_overall == "conditional":
     level = "MEDIUM"
   else: level = "LOW"

⑦ 🤖 Agent 1：RAGPlanningAgent 多query检索
   4-5条针对性query → 逐条 retrieve_regulations → 去重合并 → 最多8条

⑧ 附件证据抽取 + 🤖 Agent 2：AttachmentReviewAgent 深度审查
   冲突和缺失证据注入到 attachment_notes

⑨ 增强上下文构建
   _build_context() → 传输信息 + 路径判断 + 国家风险 + 数据敏感性
                      + 补充措施评估 + 法规摘要

⑩ 6章 LLM 生成 + 🤖 Agent 3：DPOReviewAgent 质量闸门
   警告注入第一章，DPO意见追加，强制条件追加第六章
```

**旧路径 fallback**：

```
如果 structured_input 为空：
  _resolve_risk_level(third_country_assessment, final_conclusion)
  → 10 个关键词匹配（高/high/不可/cannot → HIGH, 中/medium/条件 → MEDIUM, 其他 → LOW）
```

---

## 六、增强一致性检查（14 条规则）

**方法**：`_check_consistency(payload, level, route, country_risk, data_sens, measures, evidences)`

#### 原有 3 条

1. country_law_analysis 附件是否存在
2. SCC 工具 + 结论未提 SCC → 警告
3. HIGH 风险 + 缺暂停/suspend → 警告

#### 新增 11 条

4. 充分性决定国家却使用 SCC/BCR → 警告（冗余TIA）
5. HIGH/VERY_HIGH 目的地 + 未确认传输前加密 → 警告
6. 政府访问风险 + 无强技术措施 → 警告
7. 特殊类别数据 + 极高风险目的地 → 监管咨询建议
8. SCC + HIGH 风险 + 未加密 → SCC单独可能无效
9. Article 49 减损 → 严格必要性警告
10. 传输协议未提 SCC 条款 → 警告
11. 静态加密但密钥未确认在 EU → 警告
12. VERY_HIGH 组合（敏感数据+极高风险国家）→ 强制警告
13. 加密缺失 + HIGH 风险 → insufficient measures 警告
14. 充分性决定 + 非减损工具 → 路径不一致警告

---

## 七、完整数据流总图

```
TIARequest {
    transfer_tool: "scc"|"bcr"|"derogation",
    6个自由文本字段,
    attachments[],
    structured_input?: TIAStructuredInput  ← Optional
}
         │
    ┌────▼──────────────────────────────────────────────────┐
    │  TIAService.generate_report()                         │
    │                                                       │
    │  if structured_input 非空:                             │
    │                                                       │
    │  ① TIARouteDecider.decide(tool, structured)           │
    │     遍历 9 个充分性国家 → 匹配 → adequacy_simplified   │
    │     否则 → full_tia_scc/full_tia_bcr/derogation        │
    │     → TIARouteDecision                                │
    │                                                       │
    │  ② TIACountryRiskAssessor.assess(structured)          │
    │     查 country_risks (4个国家) → 精确/模糊匹配         │
    │     → TIACountryRisk (US=HIGH, India=VERY_HIGH, ...)  │
    │                                                       │
    │  ③ TIADataSensitivity.assess(structured)              │
    │     查 data_sensitivity_weights (18类权重)             │
    │     → {sensitivity, risk_factor, special_categories}  │
    │                                                       │
    │  ④ 复合风险评估                                        │
    │     country_risk + data_sensitivity                    │
    │     + VERY_HIGH/very_high → VERY_HIGH                  │
    │     + HIGH/risk_factor≥1.5 → HIGH                      │
    │     → effective_risk                                   │
    │                                                       │
    │  ⑤ TIAMeasureSufficiency.assess(structured, risk)     │
    │     5级措施分级 + 对照 measure_sufficiency_thresholds  │
    │     → (assessments[], "sufficient"|"conditional"|     │
    │         "highly_conditional"|"insufficient")           │
    │                                                       │
    │  ⑥ 系统风险等级                                        │
    │     VERY_HIGH or insufficient → HIGH                   │
    │     HIGH or conditional → MEDIUM                       │
    │     其他 → LOW                                         │
    │                                                       │
    │  else (旧 fallback):                                   │
    │     _resolve_risk_level() → 10个关键词匹配              │
    │                                                       │
    │  ⑦ 🤖 RAGPlanningAgent → 4-5条针对性query              │
    │     逐条检索 → 去重合并 → 最多8条                       │
    │                                                       │
    │  ⑧ TIAAttachmentEvidence.extract() × N个附件           │
    │     transfer_agreement → 6个bool                       │
    │     country_law_analysis → 6个字段                     │
    │     technical_control_doc → 8个bool                    │
    │     🤖 AttachmentReviewAgent → 证据质量 + 冲突检测       │
    │                                                       │
    │  ⑨ _build_enhanced_context()                          │
    │     传输信息 + 路径判断 + 国家风险 + 数据敏感性          │
    │     + 补充措施评估 + 法规摘要                           │
    │                                                       │
    │  ⑩ 6章 LLM 生成 (generate_chapter, "tia")             │
    │     system prompt: GDPR DPO, Schrems II expert         │
    │     LLM不可用 → 占位文本                               │
    │     🤖 DPOReviewAgent → DPO意见 + 警告注入              │
    │                                                       │
    │  ⑪ _check_consistency() (14条规则)                    │
    │                                                       │
    │  ⑫ _render() → .docx + .md + .zip                    │
    │                                                       │
    └────┬──────────────────────────────────────────────────┘
         │
    TIAResult {
        report_path, output_files{3种},
        transfer_tool, risk_level,
        chapters[6章],
        consistency_issues[], attachment_notes[],
        route_decision?, country_risk?, measure_assessments[]
    }
```

---

## 八、API 路由

**文件**：`backend/modules/tia/router.py`

| 端点 | 方法 | 说明 |
|------|------|------|
| `/tia/generate` | POST | 同步生成，返回 `TIAResult`，注册 artifacts |
| `/tia/generate_async` | POST | 异步提交，返回 `TIAAsyncAccepted`，记录 task owner |
| `/tia/tasks/{task_id}` | GET | 轮询状态，完成后注册 artifacts |
| `/tia/tasks/{task_id}/retry` | POST | 重试失败任务 |

---

## 九、关键设计决策

| 维度 | 实现方式 |
|------|---------|
| 国家风险 | 规则库优先 — 4 个国家有硬编码风险数据，充分性国家列表做路径分流 |
| 数据敏感性 | 权重表分类 — 18 种 DataCategory 映射到 1-5 分 |
| 补充措施 | 5 级技术强度 — contractual / organizational / technical_weak / technical_strong / technical_extreme |
| 风险评估 | 国家 + 数据 + 措施三因子复合 |
| 附件证据 | 3 种 file_role 分别提取 6-8 个结构化 bool 字段 |
| 一致性检查 | 14 条规则 |
| RAG | 从固定 query 升级为多query Agent规划 + 去重合并 |
| 向后兼容 | structured_input 为空 → 走旧关键词标签 fallback |
| Agent 失败 | 静默降级，不阻塞 pipeline |

## 十、回归验证状态

```
UK (adequacy):          route=adequacy_simplified ✓
US (SCC + CRM):         route=full_tia_scc, MEDIUM risk ✓
India (clinical):       VERY_HIGH risk, extreme measures needed ✓
Clinical data:          sensitivity=very_high ✓
Weak vs HIGH risk:      insufficient ✓
Strong vs HIGH risk:    sufficient ✓
Backward compat:        PASS ✓
Structured USA path:    PASS ✓ (6 chapters, enriched issues)
```
