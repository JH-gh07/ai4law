下面给你一个**可落地的 Agent 接入设计**。我按当前 EU SCC 模块已有结构来讲，不重新造一套系统。

当前 EU SCC 已经是：

```text
规则引擎层：
parse_scc_document()
→ _build_transfer_chain()
→ run_eu_scc_rule_engine()

WorkflowPipeline层：
facts
→ issues
→ evidence
→ context_pack
→ chapters
→ artifacts
```

这套结构本身是对的。文件里也明确说明当前 EU SCC 是“确定性规则引擎 + WorkflowPipeline 14 步流水线”的两层架构，规则引擎负责结构化解析、传输链建模和五大审查器，WorkflowPipeline 再负责 facts、issues、evidence、上下文包和报告生成。

所以 Agent 不应该替代整个流程，而应该插在几个“规则难以穷举”的位置。

---

# 一、总架构：Agent 应该怎么接入

建议加成下面这种结构：

```text
POST /eu_scc/generate
        ↓
parse_scc_document()
        ↓
[Agent 1] 文档结构补全 Agent
        ↓
_build_transfer_chain()
        ↓
[Agent 2] 传输链推理 Agent
        ↓
run_eu_scc_rule_engine()
        ├─ validate_module_selection()      ← 规则为主
        ├─ compare_standard_clauses()       ← 规则 + Agent 3
        ├─ review_annexes()                 ← 规则 + Agent 1/4
        ├─ review_tia_and_measures()        ← 规则 + Agent 4
        └─ score_scc_risk()                 ← 规则为主
        ↓
build_facts()
        ↓
build_issues()
        ↓
build_evidence()
        ↓
[Agent 5] 法规证据复核 Agent
        ↓
[Agent 6] 修改建议生成 Agent
        ↓
generate_chapters()
        ↓
render_artifacts()
```

一句话：

> **规则引擎负责“可确定判断”，Agent 负责“复杂理解、语义补全、证据复核、整改生成”。**

---

# 二、Agent 1：文档结构补全 Agent

## 1. 接入位置

放在 `parse_scc_document()` 之后。

当前解析器已经能提取 SCC 文档结构，包括 `SCCParty`、`SCCAnnexIA`、`SCCAnnexIB`、`SCCAnnexII`、`SCCAnnexIII`、`SCCClause`、`SCCDocument` 等结构化对象。

但是当前解析主要依赖正则、标题匹配和关键词。真实合同里可能出现标题变形、表格错位、附件合并、PDF 转文本混乱、中英混排等情况。

所以这里适合加一个 Agent。

---

## 2. 处理目标

这个 Agent 不做法律判断，只做：

```text
规则解析结果修正
+ 缺失字段补全
+ 不确定字段标注
+ 原文证据定位
```

---

## 3. 输入

```python
DocumentStructureAgentInput = {
    "raw_text": doc.raw_text,
    "parsed_document": doc,
    "declared_module": payload.declared_module_type,
    "parser_warnings": parser_warnings
}
```

其中 `parsed_document` 包括：

```text
module_type
clauses
annex_i_a
annex_i_b
annex_ii
annex_iii
raw_text
```

---

## 4. 内部处理逻辑

```text
Step 1：检查解析完整性
- Clause 数量是否过少
- Annex I.A 是否为空
- Annex I.B 是否为空
- Annex II 是否为空
- Annex III 是否可能被漏提
- module_type 是否为空或和 declared_module 冲突

Step 2：从原文中重新定位关键区域
- 搜索 "LIST OF PARTIES"
- 搜索 "DESCRIPTION OF TRANSFER"
- 搜索 "TECHNICAL AND ORGANISATIONAL MEASURES"
- 搜索 "LIST OF SUB-PROCESSORS"
- 搜索 "Data exporter" / "Data importer"
- 搜索 "controller" / "processor"
- 搜索 "sub-processor" / "cloud provider" / "AWS" / "Azure" / "GCP"

Step 3：补全字段
- party.name
- party.address
- party.contact
- party.role
- party.signature
- data_subjects
- data_categories
- special_category_data
- processing_purpose
- retention_period
- tom_items
- supplementary_measures
- sub_processors

Step 4：标注不确定性
- 如果从文本中只能推断，confidence < 1
- 如果字段来自外部引用，如 See MSA，标记 is_incomplete = true
- 如果无法确认角色，标记 needs_human_review = true

Step 5：保留原文 quote
- 每个补全字段保留 source_quote
- 后续用于批注 DOCX 和 evidence
```

---

## 5. 输出

```python
DocumentStructureAgentOutput = {
    "patched_document": SCCDocument,
    "patches": [
        {
            "field_path": "annex_i_a.parties[0].role",
            "old_value": "",
            "new_value": "processor",
            "source_quote": "Role (controller/processor): Processor",
            "confidence": 0.96,
            "reason": "Role explicitly stated in Annex I.A"
        }
    ],
    "uncertainties": [
        {
            "field_path": "annex_iii.sub_processors",
            "problem": "Sub-processors may be referenced by URL but not listed in document",
            "needs_human_review": true
        }
    ]
}
```

---

## 6. 回写方式

```python
doc = parse_scc_document(...)
agent_output = document_structure_agent.run(doc, raw_text)
doc = agent_output.patched_document
trace.save("document_structure_agent", agent_output)
```

注意：
只允许 Agent 修改结构化字段，不允许它直接生成合规结论。

---

## 7. 效果增益

它解决的是：

```text
解析器没提取到
→ 规则引擎误判为空
→ 报告误报/漏报
```

特别适合真实 Word/PDF 合同。

---

# 三、Agent 2：传输链推理 Agent

## 1. 接入位置

放在 `_build_transfer_chain()` 之后。

当前 `SCCTransferChain` 已经有：

```text
exporter_name
exporter_role
importer_name
importer_role
sub_processors
onward_transfer_locations
storage_locations
access_locations
```

设计上已经能支持传输链建模。

但真实问题是：很多 onward transfer、remote access、cloud storage 不会清楚写在一个字段里，而是散落在 Annex、子处理者清单、云服务说明、甚至附件里。

---

## 2. 处理目标

这个 Agent 做：

```text
从 SCC 文档 + Annex + 子处理者 + 附件说明中推理完整数据流
```

重点不是“谁是 exporter/importer”，而是：

```text
数据最终到了哪里？
谁能访问？
是否存在后续转移？
是否存在云服务商？
是否存在多级子处理者？
是否存在角色矛盾？
```

---

## 3. 输入

```python
TransferChainAgentInput = {
    "document": doc,
    "initial_chain": chain,
    "uploaded_attachment_notes": attachment_notes,
    "adequacy_country_map": adequacy_map
}
```

---

## 4. 内部处理逻辑

```text
Step 1：读取 Annex I.A
- 确认 exporter / importer
- 确认 controller / processor 角色
- 检查是否出现同一主体同时作为 exporter/importer

Step 2：读取 Annex I.B
- 提取处理性质：storage / analysis / profiling / support / troubleshooting
- 提取传输目的
- 提取处理地点、保存地点、访问地点

Step 3：读取 Annex III
- 提取子处理者
- 提取子处理者国家
- 标记 cloud provider：AWS / Azure / GCP / Salesforce / Snowflake 等

Step 4：扫描全文隐藏位置
- "stored in"
- "hosted by"
- "accessed from"
- "support from"
- "affiliates"
- "sub-processor list"
- "cloud infrastructure"
- "United States"
- "India"
- "Serbia"

Step 5：构建图结构
- Node：controller / processor / sub-processor / cloud provider / affiliate
- Edge：transfer / onward_transfer / storage / remote_access / support_access

Step 6：判断风险链
- 如果 importer 在充分性国家，但 sub-processor/storage 在非充分性国家 → 标记 onward transfer risk
- 如果 exporter_role/importer_role 与 module 不一致 → 交给 module validation
- 如果 sub-processor 不在 Annex III 但全文出现云服务商 → 标记 hidden sub-processor
```

---

## 5. 输出

```python
TransferChainAgentOutput = {
    "patched_chain": SCCTransferChain,
    "chain_graph": {
        "nodes": [
            {"id": "EU Fashion", "role": "controller", "country": "France"},
            {"id": "UK Marketing", "role": "controller", "country": "United Kingdom"},
            {"id": "AWS", "role": "cloud_provider", "country": "United States"}
        ],
        "edges": [
            {
                "from": "EU Fashion",
                "to": "UK Marketing",
                "type": "transfer",
                "basis": "Annex I.A"
            },
            {
                "from": "UK Marketing",
                "to": "AWS",
                "type": "onward_transfer_storage",
                "basis": "Annex III / cloud provider reference"
            }
        ]
    },
    "risk_hints": [
        {
            "type": "onward_transfer_to_non_adequate_country",
            "country": "United States",
            "basis": "AWS storage location",
            "confidence": 0.91
        }
    ]
}
```

---

## 6. 回写方式

```python
chain = _build_transfer_chain(...)
agent_output = transfer_chain_agent.run(doc, chain, attachments)
chain = agent_output.patched_chain
trace.save("transfer_chain_agent", agent_output)
```

---

## 7. 效果增益

它直接解决测试案例一的核心问题：

> 英国本身有充分性认定，但数据输入方使用美国 AWS，真正需要审查的是美国法律访问风险、TIA 和补充措施。测试案例中也明确要求识别美国 AWS、CLOUD Act/FISA 702、TIA 缺失和补充措施缺失。

---

# 四、Agent 3：条款语义比对 Agent

## 1. 接入位置

放在 `compare_standard_clauses(doc)` 之后。

当前 `compare_standard_clauses()` 的逻辑是：归一化 clause 内容，遍历 `_WEAKENING_SIGNALS`，如果命中削弱表达，就生成 `SCCFinding`，并标记 `clause.has_deviation = True`。

当前规则能识别典型削弱表达，例如：

```text
as soon as legally permissible
at its sole discretion
if it considers appropriate
to the best of its knowledge
general written authorization
```

这些削弱信号已经在规则表里。

但真实合同可能不用这些原词，而是用法律语言绕开。

---

## 2. 处理目标

这个 Agent 做：

```text
标准 SCC 条款 vs 用户条款的语义级比对
```

判断是否存在：

```text
删除义务
弱化义务
增加限制条件
转为自由裁量
缩小通知范围
削弱监管配合
削弱数据主体权利
改变责任承担
```

---

## 3. 输入

```python
ClauseSemanticAgentInput = {
    "document": doc,
    "rule_clause_comparison": clause_comparison,
    "standard_clause_library": standard_clause_key_provisions,
    "target_clauses": [7, 9, 14, 15, 16, 17, 18]
}
```

---

## 4. 内部处理逻辑

```text
Step 1：选择目标条款
- 优先检查 Clause 9、14、15
- 其次检查 Clause 7、16、17、18
- 如果规则已命中，也复核一次
- 如果规则未命中，但文本明显短于标准条款，也进入检查

Step 2：抽取标准义务
例如 Clause 15：
- promptly notify exporter
- notify data subject where possible
- provide relevant information
- review legality of request
- challenge unlawful request
- document assessment
- make available to supervisory authority

Step 3：抽取用户条款义务
- 从用户 clause 中抽取对应 obligation
- 判断义务主体、触发条件、时间要求、信息范围、例外条件

Step 4：义务矩阵比对
逐项判断：
- present / missing / weakened / restricted / discretionary

Step 5：生成补充 finding
只在以下情况生成：
- rule 未发现，但 agent 判断存在实质削弱
- rule 已发现，但 agent 补充更准确风险分析
- agent 置信度低时只生成 "candidate_finding"，不直接进入 HIGH

Step 6：人工复核标记
- confidence >= 0.85：进入正式 finding
- 0.65 <= confidence < 0.85：进入 candidate_findings
- confidence < 0.65：只记录 trace，不进入报告
```

---

## 5. 输出

```python
ClauseSemanticAgentOutput = {
    "additional_findings": [
        {
            "finding_id": "EU-SCC-CLAUSE-15-SEMANTIC-WEAKENING",
            "location": "Clause 15(a)",
            "clause_ref": "15(a)",
            "original_text": "The data importer shall provide information where it deems necessary.",
            "issue_type": "clause_weakened",
            "severity": "HIGH",
            "risk_analysis": "The clause turns a mandatory information disclosure obligation into importer discretion.",
            "legal_basis": "EU 2021/914 Recital 3; SCC Clause 15; GDPR Article 46",
            "recommendation": "Restore the standard Clause 15 wording requiring prompt notification and provision of all relevant information.",
            "suggested_text": "The data importer shall promptly notify the data exporter...",
            "confidence": 0.89
        }
    ],
    "candidate_findings": [],
    "obligation_matrix": [
        {
            "clause": "15(a)",
            "standard_obligation": "prompt notification",
            "actual_status": "weakened",
            "reason": "Notification depends on local legal permissibility"
        }
    ]
}
```

---

## 6. 回写方式

```python
clause_comparison = compare_standard_clauses(doc)

agent_output = clause_semantic_agent.run(doc, clause_comparison)
clause_comparison.findings.extend(agent_output.additional_findings)

trace.save("clause_semantic_agent", agent_output)
```

---

## 7. 效果增益

它解决的是：

```text
规则只能识别固定削弱词
Agent 能识别语义等价削弱
```

这对 Clause 15 尤其重要。测试案例二明确要求识别 “as soon as legally permissible” 和 “at its discretion” 对通知义务和信息提供义务的削弱。
当前规则能覆盖这个测试词，但 agent 可以覆盖真实合同里的变体表达。

---

# 五、Agent 4：TIA / 补充措施有效性评估 Agent

## 1. 接入位置

放在 `review_tia_and_measures()` 之后。

当前 `review_tia_and_measures()` 已经能识别第三国、TIA 是否存在、Schrems II 技术/合同/组织措施，并针对美国基础设施识别 CLOUD Act / FISA 702 风险。文档中也明确说，它会扫描端到端加密、BYOK、欧盟持钥、政府访问通知、挑战非法请求、透明度报告、独立审计等措施。

但是当前问题是：
它更像“关键词存在性检查”，还不是“措施有效性评估”。

---

## 2. 处理目标

这个 Agent 判断：

```text
补充措施是否真的能抵消第三国法律访问风险
```

不是只看有没有 TLS、AES、RBAC，而是看：

```text
谁持钥？
谁能访问明文？
云服务商是否可解密？
输入方是否能明文处理？
远程支持是否可访问？
合同是否要求挑战政府请求？
是否有透明度报告？
是否有审计和访问记录？
```

---

## 3. 输入

```python
TIAEffectivenessAgentInput = {
    "document": doc,
    "transfer_chain": chain,
    "tia_review": tia_review,
    "annex_ii": doc.annex_ii,
    "has_tia": payload.has_tia,
    "has_supplementary_measures": payload.has_supplementary_measures,
    "third_country_risk_profile": third_country_profiles
}
```

---

## 4. 内部处理逻辑

```text
Step 1：确定第三国风险对象
- 从 storage_locations / access_locations / onward_transfer_locations 中提取国家
- 区分充分性国家与非充分性国家
- 特别识别 US / India / Serbia / China / Russia 等

Step 2：识别处理场景
- storage only
- analysis
- profiling
- support access
- remote maintenance
- cloud hosting
- sub-processing
- marketing analytics
- health research

Step 3：识别数据敏感度
- contact data
- order history
- payment-related data
- health data
- biometric/genetic data
- pseudonymised data
- special category data

Step 4：评估技术措施有效性
- 是否端到端加密
- 是否 EU-held keys
- 是否 BYOK/HYOK
- 输入方是否不能访问明文
- 云服务商是否 zero-access
- 是否只是 TLS/AES 这种基础措施

Step 5：评估合同措施有效性
- 政府访问请求通知
- 挑战非法请求
- 透明度报告
- warrant canary
- 限制 onward transfer
- 子处理者同等义务下沉

Step 6：评估组织措施有效性
- 独立审计
- 访问日志
- 职责分离
- 数据最小化
- 保留期限限制
- 密钥管理职责分离

Step 7：给出有效性评级
- effective
- partially_effective
- insufficient
- unknown_due_to_missing_info

Step 8：生成 finding 或补强原 finding
- 如果第三国高风险 + 无 TIA → HIGH
- 如果有 TIA 但措施无效 → HIGH/MEDIUM
- 如果措施缺密钥控制说明 → MEDIUM
- 如果只有 TLS/AES/RBAC → 补充说明“基础 TOMs，不足以构成 Schrems II 补充措施”
```

---

## 5. 输出

```python
TIAEffectivenessAgentOutput = {
    "effectiveness_matrix": {
        "technical": {
            "status": "insufficient",
            "found": ["TLS", "AES-256", "RBAC"],
            "missing": ["end-to-end encryption", "EU-held keys", "zero-access encryption"],
            "reason": "The importer/cloud provider may still access plaintext data."
        },
        "contractual": {
            "status": "missing",
            "found": [],
            "missing": ["government access notification", "challenge unlawful requests", "transparency report"]
        },
        "organizational": {
            "status": "partial",
            "found": ["security awareness training"],
            "missing": ["independent audit", "separation of duties for key management"]
        }
    },
    "additional_findings": [
        {
            "finding_id": "EU-SCC-TIA-US-MEASURES-EFFECTIVENESS",
            "location": "Annex II",
            "issue_type": "supplementary_measures_insufficient",
            "severity": "HIGH",
            "risk_analysis": "Annex II lists general security controls but does not show measures capable of preventing or materially limiting US government access to plaintext data.",
            "legal_basis": "Schrems II C-311/18; EDPB Recommendations 01/2020; GDPR Article 46",
            "recommendation": "Add end-to-end encryption with EU-held keys, contractual government access challenge obligations, transparency reporting, and access audit controls.",
            "confidence": 0.9
        }
    ]
}
```

---

## 6. 回写方式

```python
tia_review = review_tia_and_measures(...)

agent_output = tia_effectiveness_agent.run(doc, chain, tia_review)
tia_review.findings.extend(agent_output.additional_findings)
tia_review.effectiveness_matrix = agent_output.effectiveness_matrix

trace.save("tia_effectiveness_agent", agent_output)
```

---

## 7. 效果增益

这是最值得加的 Agent。

原因是 SCC 审查的核心不是“有没有写措施”，而是“措施是否足以应对第三国法律风险”。功能说明里明确指出，Schrems II 要求逐案评估第三国法律是否影响数据接收方履行 SCC 的能力，如果第三国法律可能妨碍 SCC 履行，就必须采取额外补充措施，否则必须暂停传输。

---

# 六、Agent 5：法规证据复核 Agent

## 1. 接入位置

放在 `build_evidence()` 之后。

当前 `issue_builder.py` 会把 findings 映射成 issue，例如 module mismatch、clause deviations、third country、每个 HIGH finding 等；如果 RAG 没有返回结果，会用默认引用：`EU 2021/914`、`GDPR Article 46`、`Schrems II C-311/18`、`EDPB 01/2020`。

当前 `evidence_builder.py` 会把 issue、fact、regulation 组织成 EvidenceItem。

但这里存在一个问题：

> 有证据链，不等于证据链精准。

---

## 2. 处理目标

这个 Agent 做：

```text
finding / issue 和 legal_basis 的精确匹配复核
```

它要检查：

```text
这个问题该引用哪条法？
当前引用是否太泛？
是否缺关键依据？
是否引用错了？
是否需要增加 SCC Clause 标准文本依据？
```

---

## 3. 输入

```python
EvidenceReviewAgentInput = {
    "facts": facts,
    "issues": issues,
    "evidence_chain": evidence,
    "regulations": regulations,
    "findings": rule_result.all_findings,
    "default_rule_refs": default_refs
}
```

---

## 4. 内部处理逻辑

```text
Step 1：按 issue_type 分类
- module_mismatch
- clause_weakened
- clause_deleted
- annex_incomplete
- annex_vague
- special_category_misclassified
- tia_missing
- supplementary_measures_insufficient
- sub_processor_chain_incomplete

Step 2：为每类问题匹配标准依据模板
module_mismatch:
  - EU 2021/914 Annex module scope
  - GDPR Article 28(4) if processor/sub-processor chain
clause_weakened:
  - EU 2021/914 Recital 3
  - relevant SCC Clause standard text
  - GDPR Article 46
special_category_misclassified:
  - GDPR Article 9
  - Recital 159
tia_missing:
  - Schrems II C-311/18
  - EDPB Recommendations 01/2020
  - GDPR Article 46
supplementary_measures_insufficient:
  - Schrems II
  - EDPB 01/2020
  - GDPR Article 46
annex_incomplete:
  - EU 2021/914 Annex I requirements
  - Clause 3 / Clause 13 if data subject/supervisory authority issue

Step 3：检查当前 evidence
- fact_refs 是否真的支撑 issue
- rule_refs 是否匹配 issue_type
- conclusion 是否和 finding.recommendation 一致

Step 4：补全或修正
- 添加 missing_rule_refs
- 删除明显 irrelevant_rule_refs
- 增加 rationale
- 标记 low_confidence evidence

Step 5：输出 revised_evidence
```

---

## 5. 输出

```python
EvidenceReviewAgentOutput = {
    "revised_evidence": [...],
    "evidence_patches": [
        {
            "evidence_id": "EU-SCC-EVIDENCE-EU-SCC-ISSUE-CLAUSE-DEVIATIONS",
            "missing_rule_refs": ["EU 2021/914 Recital 3", "SCC Clause 15 standard text"],
            "irrelevant_rule_refs": [],
            "reason": "Clause 15 weakening should be grounded in SCC invariability and the standard Clause 15 obligation."
        }
    ],
    "low_confidence_evidence": [
        {
            "evidence_id": "...",
            "problem": "No direct source quote found for alleged storage location.",
            "needs_human_review": true
        }
    ]
}
```

---

## 6. 回写方式

```python
issues, evidence = build_eu_scc_evidence(...)

agent_output = evidence_review_agent.run(facts, issues, evidence, regulations, findings)
evidence = agent_output.revised_evidence

trace.save("evidence_review_agent", agent_output)
```

---

## 7. 效果增益

它提升的是报告可信度。

预期报告要求每个问题都包含定位、原文引用、问题类型、风险分析、法规/标准依据和修改建议。
如果证据链不准，报告会看起来完整但经不起复核。

---

# 七、Agent 6：修改建议生成 Agent

## 1. 接入位置

放在 `generate_chapters()` 之前。

当前报告章节包括：

```text
文件概要
总体合规评级
条款级审查发现
法规依据与修改建议
```

这和预期报告结构基本一致。

但修改建议如果直接由 LLM 在整章里生成，容易泛泛而谈。更好的方式是：
先对每个 finding 生成结构化修改建议，再让 LLM 写报告。

---

## 2. 处理目标

这个 Agent 做：

```text
每条 finding → 可直接落地的修改建议
```

不是泛泛说“建议完善”，而是生成：

```text
Clause 应恢复什么文本
Annex 应补什么字段
TIA 应补什么评估内容
Annex II 应补哪些技术/合同/组织措施
子处理者授权链应怎么写
```

---

## 3. 输入

```python
RemediationAgentInput = {
    "findings": rule_result.all_findings,
    "evidence": evidence,
    "document": doc,
    "transfer_chain": chain,
    "module_validation": rule_result.module_validation,
    "standard_clause_library": standard_clause_key_provisions
}
```

---

## 4. 内部处理逻辑

```text
Step 1：按 finding 类型选择建议模板

module_mismatch:
- 建议更换 SCC 模块
- 重写 exporter/importer 角色
- 明确 controller/processor/sub-processor 链条

clause_weakened:
- 找到标准 Clause 文本
- 生成“恢复标准文本”建议
- 如果用户加了补充条款，建议移至附加条款且不得冲突

annex_incomplete:
- 列出缺失字段
- 生成 Annex I.A 完整填写模板

annex_vague:
- 把模糊数据类别拆细
- 例如 order history data → products purchased, dates, values, payment status, delivery info

special_category_misclassified:
- 改为 Article 9 特殊类别数据
- 要求写明 Article 9(2) 依据和额外保障

tia_missing:
- 要求完成 TIA
- 列出 TIA 必须包含的项目：第三国法律、政府访问、救济、补充措施有效性

supplementary_measures_insufficient:
- 技术措施：E2EE、EU-held keys、BYOK/HYOK、zero-access
- 合同措施：政府访问通知、挑战非法请求、透明度报告
- 组织措施：审计、访问日志、职责分离、密钥管理

sub_processor_chain_incomplete:
- 补全 Annex III
- 补全 Clause 9 授权机制
- 说明 onward transfer 约束

Step 2：生成 suggested_text
- 尽量给合同可直接替换的文本
- 对无法确定的内容使用 [占位符]

Step 3：生成 action_plan
- P0：阻断性整改
- P1：备案/签署前补正
- P2：优化性建议

Step 4：回写 finding
- finding.recommendation
- finding.suggested_text
- finding.action_priority
```

---

## 5. 输出

```python
RemediationAgentOutput = {
    "patched_findings": [
        {
            "finding_id": "EU-SCC-CLAUSE-15-DEVIATION",
            "recommendation": "Restore Clause 15(a) to the EU 2021/914 standard wording.",
            "suggested_text": "The data importer shall promptly notify the data exporter and, where possible, the data subject if it receives a legally binding request...",
            "action_priority": "P0"
        }
    ],
    "action_plan": [
        {
            "priority": "P0",
            "task": "Restore weakened Clause 15 wording",
            "owner": "Legal",
            "reason": "Core SCC clause has been weakened"
        },
        {
            "priority": "P0",
            "task": "Complete TIA for United States AWS storage",
            "owner": "DPO / Privacy Counsel",
            "reason": "Third-country legal assessment missing"
        }
    ]
}
```

---

## 6. 回写方式

```python
agent_output = remediation_agent.run(findings, evidence, doc, chain)

rule_result.all_findings = agent_output.patched_findings
context_pack.action_plan = agent_output.action_plan

trace.save("remediation_agent", agent_output)
```

---

## 7. 效果增益

它让报告从“指出问题”升级为“指导用户改合同”。

测试案例三预期输出就不是只说“模块错误”，而是明确要求改用 Module Three，并调整各方角色：Orange Cloud BV 作为数据输出方/处理者，Balkan IT Support DOO 作为数据输入方/子处理者，Nordic Retail Group 信息应在 Annex I 中明确。

这类具体建议非常适合由修改建议 Agent 生成。

---

# 八、可选 Agent 7：信息补全追问 Agent

这个不是必须，但产品体验会更好。

## 1. 接入位置

放在 `rule_engine_result` 之后，报告生成之前。

```text
rule_engine_result
        ↓
InformationGapAgent
        ↓
missing_materials / clarification_questions
        ↓
报告中生成“需补充材料清单”
```

---

## 2. 处理目标

当系统无法确认关键事实时，不直接乱判，而是输出缺失材料。

例如：

```text
缺 TIA
缺 AWS DPA
缺子处理者名单
缺密钥管理说明
缺数据流图
缺主服务协议 MSA
缺特殊类别数据处理依据
```

---

## 3. 内部处理逻辑

```text
Step 1：读取 findings 和 uncertainties
Step 2：识别哪些问题是“事实缺失导致”
Step 3：生成材料清单
Step 4：生成追问问题
Step 5：把这些问题写入报告的“需补充材料”章节
```

---

## 4. 输出

```python
InformationGapAgentOutput = {
    "missing_materials": [
        {
            "material": "Transfer Impact Assessment report",
            "reason": "Third-country transfer to United States identified but has_tia=false",
            "priority": "P0"
        },
        {
            "material": "Encryption key management policy",
            "reason": "Annex II lists encryption but does not state who controls the keys",
            "priority": "P0"
        }
    ],
    "clarification_questions": [
        "Does AWS have access to plaintext personal data?",
        "Are encryption keys held exclusively by an EU entity?",
        "Is there a current sub-processor list signed or incorporated into the SCC?"
    ]
}
```

---

# 九、建议新增的数据模型

为了让 Agent 输出稳定，不要让它们直接返回自然语言。建议新增几个模型。

```python
class AgentPatch(BaseModel):
    field_path: str
    old_value: Any | None
    new_value: Any | None
    source_quote: str | None = None
    confidence: float
    reason: str
    needs_human_review: bool = False


class AgentFindingCandidate(BaseModel):
    finding: SCCFinding
    confidence: float
    source_quotes: list[str]
    accepted: bool = False
    reason: str


class MeasureEffectiveness(BaseModel):
    technical_status: str  # effective / partial / insufficient / unknown
    contractual_status: str
    organizational_status: str
    missing_measures: list[str]
    effectiveness_reason: str


class RemediationAction(BaseModel):
    priority: str  # P0/P1/P2
    target: str
    action: str
    suggested_text: str | None
    owner_hint: str | None
    legal_basis: list[str]
```

---

# 十、Agent 不应该拥有的权限

为了稳定性，Agent 权限要收窄。

| Agent        | 可以做                  | 不可以做                   |
| ------------ | -------------------- | ---------------------- |
| 文档结构补全 Agent | 修正结构化字段              | 直接判高风险                 |
| 传输链推理 Agent  | 补全链条和风险 hint         | 直接改 overall_rating     |
| 条款语义比对 Agent | 追加 finding candidate | 删除规则 finding           |
| TIA Agent    | 评估措施有效性              | 覆盖已有规则结果               |
| 证据复核 Agent   | 补证据、改依据              | 删除原始事实                 |
| 修改建议 Agent   | 生成建议文本               | 改变 issue_type/severity |
| 信息补全 Agent   | 生成缺失材料清单             | 阻断报告生成                 |

核心原则：

> **Agent 可以补强，不要让 Agent 直接替代确定性规则结果。**

---

# 十一、完整落地伪代码

可以这样改 `EU_SCCService.generate_report()`：

```python
def generate_report(self, payload: SCCReviewRequest) -> SCCReviewResult:
    task_id = create_task_id()
    trace = TraceRecorder(task_id)

    # 1. 规则解析
    doc = parse_scc_document(
        text=payload.scc_text,
        declared_module=payload.declared_module_type,
        exporter_role=payload.exporter_role,
        importer_role=payload.importer_role,
    )
    trace.save("parsed_document_raw", doc)

    # 2. Agent 1：文档结构补全
    if self.agent_config.enable_document_structure_agent:
        doc_patch = self.document_structure_agent.run(
            raw_text=payload.scc_text,
            parsed_document=doc,
            declared_module=payload.declared_module_type,
        )
        doc = doc_patch.patched_document
        trace.save("document_structure_agent", doc_patch)

    # 3. 规则传输链
    chain = self._build_transfer_chain(
        exporter_role=payload.exporter_role,
        importer_role=payload.importer_role,
        doc=doc,
        attachment_text="",
    )
    trace.save("transfer_chain_raw", chain)

    # 4. Agent 2：传输链推理
    if self.agent_config.enable_transfer_chain_agent:
        chain_patch = self.transfer_chain_agent.run(
            document=doc,
            initial_chain=chain,
            attachments=payload.uploaded_files,
        )
        chain = chain_patch.patched_chain
        trace.save("transfer_chain_agent", chain_patch)

    # 5. 规则引擎
    rule_result = run_eu_scc_rule_engine(
        doc=doc,
        chain=chain,
        declared_module=payload.declared_module_type,
        has_tia=payload.has_tia,
        has_supplementary=payload.has_supplementary_measures,
    )
    trace.save("rule_engine_result_raw", rule_result)

    # 6. Agent 3：条款语义比对
    if self.agent_config.enable_clause_semantic_agent:
        clause_agent_out = self.clause_semantic_agent.run(
            document=doc,
            clause_comparison=rule_result.clause_comparison,
        )
        rule_result.clause_comparison.findings.extend(
            clause_agent_out.additional_findings
        )
        rule_result.all_findings.extend(
            clause_agent_out.additional_findings
        )
        trace.save("clause_semantic_agent", clause_agent_out)

    # 7. Agent 4：TIA / 补充措施有效性
    if self.agent_config.enable_tia_effectiveness_agent:
        tia_agent_out = self.tia_effectiveness_agent.run(
            document=doc,
            transfer_chain=chain,
            tia_review=rule_result.tia_review,
            has_tia=payload.has_tia,
            has_supplementary=payload.has_supplementary_measures,
        )
        rule_result.tia_review.findings.extend(
            tia_agent_out.additional_findings
        )
        rule_result.all_findings.extend(
            tia_agent_out.additional_findings
        )
        rule_result.tia_review.effectiveness_matrix = (
            tia_agent_out.effectiveness_matrix
        )
        trace.save("tia_effectiveness_agent", tia_agent_out)

    # 8. 重新评分：仍由规则评分函数统一决定
    rule_result.overall_rating = score_scc_risk(rule_result.all_findings)

    # 9. WorkflowPipeline
    facts = build_eu_scc_facts(payload, rule_result)
    regulations = self._retrieve_regulations(payload)
    issues = build_eu_scc_issues(facts, rule_result, regulations)
    issues, evidence = build_eu_scc_evidence(facts, issues, regulations)

    # 10. Agent 5：证据复核
    if self.agent_config.enable_evidence_review_agent:
        evidence_agent_out = self.evidence_review_agent.run(
            facts=facts,
            issues=issues,
            evidence=evidence,
            regulations=regulations,
            findings=rule_result.all_findings,
        )
        evidence = evidence_agent_out.revised_evidence
        trace.save("evidence_review_agent", evidence_agent_out)

    # 11. Agent 6：修改建议生成
    if self.agent_config.enable_remediation_agent:
        remediation_out = self.remediation_agent.run(
            findings=rule_result.all_findings,
            evidence=evidence,
            document=doc,
            transfer_chain=chain,
            module_validation=rule_result.module_validation,
        )
        rule_result.all_findings = remediation_out.patched_findings
        action_plan = remediation_out.action_plan
        trace.save("remediation_agent", remediation_out)

    # 12. 上下文包 + 章节生成 + 渲染
    context_pack = build_context_pack(
        facts=facts,
        issues=issues,
        evidence=evidence,
        findings=rule_result.all_findings,
        action_plan=action_plan,
    )

    chapters = self._generate_chapters(context_pack)
    outputs = self._render_outputs(payload, rule_result, chapters)

    return SCCReviewResult(
        report_path=outputs["docx"],
        output_files=outputs,
        findings=rule_result.all_findings,
        module_validation=rule_result.module_validation,
        chapters=chapters,
        consistency_issues=self._check_consistency(rule_result, issues),
    )
```

---

# 十二、最推荐先落地哪几个

不要一次性全加。建议按收益分三期。

## 第一期：最该加

```text
1. TIA / 补充措施有效性 Agent
2. 条款语义比对 Agent
3. 修改建议生成 Agent
```

原因：

| Agent               | 为什么优先                   |
| ------------------- | ----------------------- |
| TIA / 补充措施有效性 Agent | 直接解决 Schrems II 核心风险    |
| 条款语义比对 Agent        | 覆盖非典型 Clause 14/15/9 削弱 |
| 修改建议生成 Agent        | 直接提升报告可用性               |

---

## 第二期：增强可靠性

```text
4. 法规证据复核 Agent
5. 文档结构补全 Agent
```

原因：

| Agent        | 价值           |
| ------------ | ------------ |
| 法规证据复核 Agent | 防止引用泛化、错引、漏引 |
| 文档结构补全 Agent | 解决真实合同解析不稳定  |

---

## 第三期：复杂场景

```text
6. 传输链推理 Agent
7. 信息补全追问 Agent
```

原因：

| Agent        | 价值                |
| ------------ | ----------------- |
| 传输链推理 Agent  | 处理多级子处理者、云服务、远程访问 |
| 信息补全追问 Agent | 适合真实企业交互式补材料      |

---

# 十三、最终一句话

EU SCC 模块加 Agent 的具体逻辑应该是：

```text
规则引擎先给出可复核的基础判断；
Agent 只在“结构补全、复杂链条、语义削弱、措施有效性、证据复核、修改建议”这些非确定性环节介入；
Agent 输出必须结构化回写 findings/evidence/action_plan；
最终评级仍由规则层统一计算。
```

这样加完以后，系统不会变成不稳定的“LLM 随机审合同”，而是变成：

> **规则稳定、Agent 补强、证据可追踪、建议可执行的 EU SCC 审查工作流。**
