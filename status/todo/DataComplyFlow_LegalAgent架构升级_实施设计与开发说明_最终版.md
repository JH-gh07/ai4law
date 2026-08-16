# DataComplyFlow 比赛版 Legal Agent 架构升级——实施设计与开发说明 V0.3

> **Document Type**：Final Architecture Implementation Contract  
> **Status**：FINAL — READY FOR IMPLEMENTATION  
> **Version**：V0.3  
> **Reviewed Code Baseline**：branch `new`，HEAD `2b9f5d16e397cf760216a4b6f8cc90d884a96dbc`  
> **Input Review**：`DataComplyFlow Legal Agent 架构升级：开发事实与可行性审查 V0.1`  
> **Primary Consumer**：DataComplyFlow 开发负责人  
> **Purpose**：作为比赛版 Legal Agent Control Plane 首轮代码实现的开发合同  
> **Out of Scope**：Benchmark、全量 Runtime 重构、11 模块全面迁移

---

# 0. 开发前置规则

## 0.1 HEAD / Worktree Preflight

开发事实审查时：

```text
Branch: new
HEAD: 2b9f5d16e397cf760216a4b6f8cc90d884a96dbc
Worktree: DIRTY
```

其中 `frontend/src/components/workspace/ModuleRunPanel.tsx` 存在未提交修改。

正式实施前必须：

1. 记录当前 HEAD；
2. 检查相关文件是否已发生新修改；
3. 保留现有未提交工作，不覆盖 ModuleRunPanel 当前改动；
4. 若 Diagnosis / Assessment / Citation / Trace / WorkflowPipeline 自审查后已发生实质变化，先做 delta check。

---

## 0.2 最高实施原则

```text
Reuse > Extend > Adapter > Insert > Replace
```

本轮不允许 `REWRITE`。

---

## 0.3 Pilot Isolation

所有 Control 行为必须 **opt-in**。

禁止：

- 修改 `DiagnosisService.evaluate()` 默认语义后隐式影响 Assessment；
- 修改公共 WorkflowPipeline 默认顺序后隐式影响 EU SCC / US14117 / CN Flow；
- 修改公共 citation pipeline 默认治理规则后影响其他模块。

---

## 0.4 Per-run State

router 中 Service 为 singleton。

禁止：

```text
self.last_control_decision
self.current_gate_results
self.current_citation_state
```

等 per-run 可变状态。

所有 GateResult / ControlDecision 必须：

- 通过局部变量；
- context/result；
- callback 参数；

在单次运行内部传递。

---

# 1. Current → Target 组件映射

| Current | V0.3 处理 | Target Role |
|---|---|---|
| `DiagnosisFacts` | REUSE | Fact Gate input |
| `missing_facts` list | REUSE | Missing signal |
| `field_provenance` | REUSE | Inferred-fact signal |
| `_validate_fact_consistency()` | REUSE | Conflict signal |
| `RuleMatch` | REUSE | Deterministic precedence source |
| `DiagnosisResult` | ADDITIVE_FIELD | Control output carrier |
| `IssueItem` | REUSE | Evidence policy input |
| `EvidenceItem` | REUSE | Evidence policy input |
| `GenerationContextPack` | EXTEND optional | Per-run Assessment control carrier |
| `CitationRegistry` | REUSE | Citation existence / relation source |
| `CitationItem.source_id` | REUSE with exact membership | Local canonical identity candidate |
| `SourceRegistryEntry` | REUSE | Eligibility authority |
| `TraceRecorder` | EXTEND event | Control observability |
| `AssessmentResult` | ADDITIVE_FIELD | Control output carrier |
| `WorkflowPipeline` | REUSE unchanged | Existing workflow |
| Reporting | REUSE | Existing artifact path |
| Task status | REUSE unchanged | Runtime lifecycle |

---

# 2. 公共最小契约

本轮只冻结两个公共对象。

## 2.1 GateResult

概念结构：

```text
GateResult
├── gate
├── outcome
├── reasons[]
├── refs[]
├── required_actions[]
└── details{}
```

### gate

```text
FACT_COMPLETENESS
DETERMINISTIC_RULE_PRECEDENCE
EVIDENCE_SUFFICIENCY
CITATION_VALIDITY
ESCALATION
```

### outcome

只统一：

```text
PASS
CONDITIONAL
ESCALATE
BLOCK
```

不同 Gate 的专业状态放入 `details`。

---

## 2.2 ControlDecision

```text
ControlDecision
├── legal_control_status
├── gate_results[]
├── reasons[]
└── required_actions[]
```

### legal_control_status

```text
AUTO
CONDITIONAL
NEEDS_CLARIFICATION
NEEDS_REVIEW
BLOCKED
```

V1 Pilot 不要求主动触发 `BLOCKED`。

---

## 2.3 Required Actions

建议统一字符串 / Enum：

```text
ASK_USER
KEEP_DETERMINISTIC_RESULT
QUALIFY_OUTPUT
HUMAN_REVIEW
EXCLUDE_CITATION
OMIT_UNSUPPORTED_CLAIM
```

首轮避免设计完整 approval workflow。

---

## 2.4 API Additive Fields

### DiagnosisResult

建议：

```text
legal_control_status
control_reasons
required_actions
clarification_questions
gate_results  # optional
```

### AssessmentResult

建议：

```text
legal_control_status
control_reasons
required_actions
gate_results  # optional
```

全部提供向后兼容默认值。

不得修改：

```text
task_status
state
async state
```

---

# 3. Trace Contract

## 3.1 Backend

当前 `TraceRecorder.record(name, payload)` 已允许自定义 name / dict payload。

使用：

```text
control.fact_completeness
control.rule_precedence
control.evidence_sufficiency
control.citation_validity
control.escalation
```

payload 至少：

```text
outcome
reason_summary
refs
required_actions
```

---

## 3.2 SSE / Frontend

首轮不新增 `RunEvent.event_type="control"`。

继续使用现有标准 event type：

- pass / normal → `intermediate`
- review / limitation → `warning`

同时保留：

```text
raw_name = control.*
```

前端 `trace-adapter.ts::semanticFromDetail()` 根据 `/^control\./` 映射明确 action / badge。

---

# 4. Pilot A — CN Transfer Diagnosis

# 4.1 Current Flow

真实链：

```text
POST /api/v1/diagnosis/evaluate
or /report
→ DiagnosisService.evaluate()
→ _resolve_answers()
   ├─ rule normalization
   ├─ estimation
   └─ missing_facts
→ ImportantDataAgent
→ PIClassifyAgent
→ ExemptionAgent
→ facts_from_module() → DiagnosisFacts
→ _validate_fact_consistency()
   └─ conflict → manual_review DiagnosisResult → return
→ DiagnosisRuleEngine.evaluate() → RuleMatch
   ├─ non-default
   │  → _build_rule_result()
   │  → _build_rule_explanation()
   │  → return
   └─ default
      → _needs_ai_inference()
      → _build_ai_inference_result()
      → or default tree result
```

---

# 4.2 Pilot Isolation Contract

推荐实现：

```text
DiagnosisService.evaluate(
    answers,
    trace=None,
    control=None,   # default disabled
)
```

或等价显式 hook。

Assessment 当前：

```text
self.diagnosis_service.evaluate(self._to_diagnosis_answers(payload))
```

保持不传 control。

禁止将启用状态存入 Service 实例。

---

# 4.3 G1 Fact Completeness — Exact Seam

真实处理顺序：

```text
_resolve_answers()
→ Agents
→ facts_from_module()
→ existing conflict validation
→ Fact Completeness Gate
→ Rule Engine
```

### Conflict 分支

如果 `_validate_fact_consistency()` 返回现有 manual-review `DiagnosisResult`：

1. 不改变原业务结果；
2. 生成 GateResult：
   ```text
   gate = FACT_COMPLETENESS
   outcome = ESCALATE
   reason = FACT_CONFLICT
   ```
3. 生成：
   ```text
   legal_control_status = NEEDS_REVIEW
   ```
4. 附加到结果后返回。

### Missing 分支

消费最终：

```text
DiagnosisFacts
missing_facts
field_provenance
```

V1 关键 missing 范围沿用当前 `_resolve_answers()` 已有语义，不另建新的法学关键字段体系。

若关键 missing 仍存在：

```text
outcome = ESCALATE
legal_control_status = NEEDS_CLARIFICATION
required_actions = [ASK_USER]
```

### Inferred decisive fact

如果关键事实由：

```text
LLM_INFERENCE
ESTIMATE
DEFAULT
```

补齐并实际参与后续路径决定：

V1 不视为完全自主可靠事实，记录：

```text
outcome = CONDITIONAL / ESCALATE
```

最终至少：

```text
legal_control_status = NEEDS_REVIEW
```

`RULE_DERIVED` 的确定性推导不自动触发人工复核。

具体 provenance Enum 名称按当前代码实际类型复用。

---

# 4.4 Clarification

首轮不增加 LLM 追问 Agent。

使用：

```text
missing_fact_key
→ predefined clarification question
```

例如问题映射放在 Diagnosis domain 内部，不进入公共 Control Contract。

---

# 4.5 G2 Deterministic Rule Precedence

插入：

```text
rule_match = DiagnosisRuleEngine.evaluate(facts)
→ Rule Precedence Adapter
```

### non-default

```text
rule_match.is_default = false
```

记录：

```text
execution_precedence = true
expected_path = rule_match.path
```

现有 `_build_rule_result()` 继续生成 canonical result。

现有 `_build_rule_explanation()` 只能解释。

在返回前断言：

```text
DiagnosisResult.recommended_path == expected_path
```

如果不一致：

- 保留 deterministic canonical path；
- `outcome = ESCALATE`
- `legal_control_status = NEEDS_REVIEW`

不新增 LLM Judge。

### default

```text
rule_match.is_default = true
```

记录：

```text
execution_precedence = false
```

继续执行现有：

```text
_needs_ai_inference()
_build_ai_inference_result()
```

不得把 default 结果描述为 deterministic lock。

---

# 4.6 Diagnosis Escalation

优先级建议：

```text
existing conflict
    → NEEDS_REVIEW

critical missing
    → NEEDS_CLARIFICATION

decisive inferred fact
    → NEEDS_REVIEW

non-default deterministic result, no conflict
    → AUTO

default + AI inference
    → NEEDS_REVIEW
```

如果当前 default 分支已有 `requires_human_review` / uncertainty signal，直接复用，不重复定义。

---

# 4.7 Diagnosis Acceptance

### D1 Complete deterministic case

```text
task execution successful
legal_control_status = AUTO
recommended_path unchanged
```

### D2 Critical missing

```text
legal_control_status = NEEDS_CLARIFICATION
clarification_questions != empty
```

不得作为无条件最终路径展示。

### D3 Existing fact conflict

```text
existing manual_review result preserved
legal_control_status = NEEDS_REVIEW
```

### D4 non-default Rule + LLM explanation

`recommended_path` 必须保持 deterministic result。

### D5 default → AI inference

不得标记 execution precedence lock；默认进入 review-aware control state。

### D6 Assessment Regression

Assessment 未启用 Diagnosis control 时，原结果和测试保持一致。

---

# 5. Pilot B — CN Security Assessment

# 5.1 Current Flow

真实链：

```text
AssessmentService.generate_report()
→ prepare_run()
→ _build_pipeline()
→ WorkflowPipeline.run()
→ profile
→ Diagnosis reuse
→ path validation
→ facts
→ regulations
→ attachment notes
→ issues
→ evidence
→ per_issue_rag
→ _build_context_pack()
   ├─ legal_grounding
   ├─ writing strategy
   ├─ generation basis
   └─ build_citations() → CitationRegistry
→ generate_chapters()
→ consistency
→ alignment
→ repair
→ manifest
→ _render_outputs()
→ renderer
→ AssessmentResult
```

---

# 5.2 Pilot Isolation

首轮优先：

> **Assessment-specific Adapter**

不先修改公共 WorkflowPipeline。

如果开发最终必须使用 optional hook：

- keyword-only；
- default `None`；
- 默认 event 顺序不变；
- EU SCC / US14117 / CN Flow 回归通过。

---

# 6. Assessment Prerequisite — Canonical Source Identity

这是 Assessment Citation Validity 的前置任务。

## 6.1 当前事实

本地 multi-index：

```text
SourceRegistryEntry.source_id
→ KnowledgeChunkV2.source_id
→ RegulationHit.source_id
→ CitationItem.source_id
```

通常可形成稳定链。

但 fallback / DeliLegal：

- provider / synthetic source ID
- 不保证是 SourceRegistry ID。

---

## 6.2 V1 Canonical Lookup Rule

Gate 只接受：

```text
exact registry membership
```

概念：

```text
registry_id =
    citation.registry_source_id
    or citation.source_id if source_id in SourceRegistry
    else None
```

如果当前 CitationItem 没有 `registry_source_id`，允许 additive 增加：

```text
registry_source_id: str | None = None
```

不得删除或重定义现有 `source_id`。

---

## 6.3 External / fallback source

如果：

```text
registry_source_id is None
and citation.source_id not in SourceRegistry
```

则：

```text
eligibility = UNREGISTERED
```

不得通过 title fuzzy matching 变成 approved source。

正式 Claim 如果仅依赖该来源：

```text
legal_control_status >= NEEDS_REVIEW
```

---

## 6.4 Citation Relationship Merge

当前 Citation 去重可能没有完整 union：

- issue；
- fact；
- evidence；

关联。

Assessment Pilot 需要保证同一 Citation 去重后：

```text
related_issue_ids
related_fact_ids
related_evidence_ids
```

做 union merge，而不是 first-wins。

优先修 Assessment citation builder。

只有确认公共 helper 修改不会影响其他模块时，才上升为公共修复。

---

# 7. G3-A Minimum Evidence Sufficiency V1

## 7.1 Exact Insertion Point

最终冻结：

```text
_build_context_pack()
→ Evidence Sufficiency Adapter
→ generate_chapters()
```

Gate 在 ContextPack 构造后执行，因为此时已有：

- Facts；
- Issues；
- Evidence；
- legal_grounding；
- per-issue RAG；
- CitationRegistry。

---

## 7.2 真实输入

使用：

### Issue

```text
fact_refs
rule_refs
evidence_refs
severity
```

### EvidenceItem

```text
claim
fact_refs
rule_refs
legal_basis
document_refs
confidence
supporting_basis
discarded_basis
```

### Fact

```text
evidence_status
can_support_external_positive_claim
```

### Context

```text
legal_grounding.by_issue
```

不得使用不存在的：

```text
EvidenceItem.citation_refs
EvidenceItem.status
EvidenceItem.strength
```

---

## 7.3 Minimum Policy

V1 不构建完整 Evidence Graph。

建议规则：

### E1 — Missing Fact Support

对已有高风险 / 核心 Issue：

若关联 Fact 不存在或悬空：

```text
support = UNSUPPORTED
```

### E2 — Missing Legal Basis

对需要法律依据的 Issue / Claim：

如果：

```text
EvidenceItem.rule_refs empty
AND EvidenceItem.legal_basis empty
AND legal_grounding.by_issue 无有效法律依据
```

则：

```text
support = UNSUPPORTED
```

### E3 — Unverified External-positive Fact

如果用于外部积极结论的关键 Fact：

```text
can_support_external_positive_claim = false
```

则：

```text
support = PARTIAL
```

不得形成无保留强结论。

### E4 — Low-confidence sole support

如果核心 Claim 仅有单一低置信 Evidence 支持：

```text
support = PARTIAL
```

具体阈值不在架构文档创造；使用当前项目已有 confidence 语义或开发确认的既有阈值。

### E5 — Existing structural inconsistency

复用当前 context consistency checker 发现的 dangling fact/rule/evidence refs：

```text
support = PARTIAL / UNSUPPORTED
```

根据是否影响核心 Claim。

---

## 7.4 document_refs 处理

当前 `document_refs` 在正常链中通常为空。

V1：

- 不把 `document_refs == []` 直接作为 hard fail；
- 记录：
  ```text
  DOCUMENT_TRACE_GAP
  ```
  作为 limitation；
- 如果开发修复当前字符串 supporting-material reference 提取，可纳入增强验证。

该修复不是 Four-Gate 架构成立的前提。

---

## 7.5 Evidence Gate Output

GateResult.details 建议：

```text
issue_support = {
  issue_id: SUPPORTED | PARTIAL | UNSUPPORTED
}

unsupported_issue_ids = [...]
partial_issue_ids = [...]
limitations = [...]
```

Gate outcome：

```text
all core supported
→ PASS

core partial
→ CONDITIONAL

core unsupported
→ ESCALATE
```

---

# 8. G3-B Citation Validity V1

## 8.1 Candidate Precheck

ContextPack / CitationRegistry 建成后可选执行：

```text
candidate source identity / eligibility precheck
```

用于在 generation 前标记不合规候选。

但它不是最终 Gate。

---

## 8.2 Final Insertion Point

最终冻结：

```text
generate
→ consistency
→ alignment
→ repair
→ Citation Validity V1
→ Escalation
→ render
```

原因：

repair 可能修改最终正文。

CitationMap 文件此时尚未生成，因此 Gate 使用：

```text
final chapters
+
in-memory CitationRegistry
+
SourceRegistry
```

---

## 8.3 C1 — Existence

最终引用 marker / citation ID：

必须能够通过当前 CitationRegistry 精确解析。

无法解析：

```text
citation_status = MISSING
```

不能因为 renderer 能显示“待核验”而视为通过。

---

## 8.4 C2 — Eligibility

通过 canonical registry ID exact lookup：

读取：

```text
review_status
can_be_cited
can_enter_external_report
allowed_usage
authority_level
binding_force
```

V1 核心通过条件：

```text
source registered
AND can_be_cited = true
AND allowed_usage permits current use
AND external output 时 can_enter_external_report = true
```

若 SourceRegistry 对 `review_status` 有明确未审核状态，则按现有治理规则 fail-closed。

---

## 8.5 C3 — Traceability

用于核心 Claim 的 Citation 至少必须与当前业务语义有稳定关联。

优先使用：

```text
related_issue_ids
related_fact_ids
related_evidence_ids
```

如果 Citation 存在但完全无法关联当前 Issue / Fact / Evidence：

```text
traceability = PARTIAL
```

核心 Claim 依赖该 Citation 时：

```text
legal_control_status >= NEEDS_REVIEW
```

---

## 8.6 V1 明确不做

不做：

- Semantic Fidelity Judge；
- Fine-grained Applicability LLM Judge；
- 法条语义 entailment 模型；
- title fuzzy governance；
- 完整 citation closure。

---

# 9. Assessment Escalation

建议最小映射：

## AUTO

```text
core evidence supported
AND citations exist
AND citations eligible
AND core citation traceability sufficient
```

## CONDITIONAL

例如：

- 非核心 Evidence partial；
- 低风险 limitation；
- claim 可通过限定表述保持正确。

required action：

```text
QUALIFY_OUTPUT
```

## NEEDS_REVIEW

例如：

- 核心 Evidence unsupported；
- 只有 unregistered / ineligible source；
- 核心 Citation 无稳定 traceability；
- repair_blocked；
- existing consistency / alignment unresolved。

V1 中：

```text
task_status = COMPLETED
legal_control_status = NEEDS_REVIEW
```

允许生成内部/比赛展示用报告，但：

- UI 必须明确提示人工复核；
- 不得把不合格 Citation 作为“正式已核验来源”展示；
- unsupported strong claim 应限定或省略。

## BLOCKED

公共契约保留。

两个 Pilot V1 不要求主动触发。

---

# 10. Frontend Minimal Exposure

## 10.1 Result Status

前端读取：

```text
legal_control_status
control_reasons
required_actions
clarification_questions
```

不重用：

```text
state
asyncState
task_status
```

---

## 10.2 Diagnosis

### NEEDS_CLARIFICATION

显示：

- 当前缺失哪些关键事实；
- 为什么不能形成无条件最终判断；
- 返回表单补充。

### NEEDS_REVIEW

显示：

- 当前路径包含推断或冲突因素；
- 建议人工复核。

---

## 10.3 Assessment

### CONDITIONAL

显示：

> 当前报告包含条件式 / 待确认结论。

### NEEDS_REVIEW

显示：

> 当前自动分析已完成，但报告需要人工复核后再作为正式法律成果使用。

---

## 10.4 Trace

不新增前端 event union。

使用：

```text
raw_name = control.*
```

由 trace adapter 映射为：

- Fact Check
- Rule Precedence
- Evidence Check
- Citation Check
- Escalation

---

# 11. 开发任务顺序 V0.3

## T01 — Core Contract

实现：

```text
GateResult
ControlDecision
legal_control_status
required_actions
```

全部 additive/default-safe。

**Cost：LOW**

---

## T02 — Trace Integration

增加：

```text
control.*
```

记录与前端 raw_name 映射。

不新增新的 SSE event type。

**Cost：LOW**

---

## T03 — Diagnosis Fact Completeness

在真实 service seam：

```text
Agents
→ facts
→ validation
→ Gate
→ Rule
```

实现。

加入 Assessment default-off regression。

**Cost：MEDIUM**

---

## T04 — Diagnosis Rule Precedence

区分：

```text
non-default → locked deterministic path
default → existing AI inference
```

不增加 LLM Judge。

**Cost：LOW**

---

## T05 — Diagnosis Escalation / API

新增 additive result fields，形成 Pilot A 闭环。

**Cost：MEDIUM**

---

## T06 — Assessment Canonical Source Identity

在 Citation Gate 前先解决：

- exact SourceRegistry lookup；
- optional `registry_source_id`（如需要）；
- fallback / DeliLegal unregistered policy；
- Assessment citation relation union merge。

**Cost：HIGH**

这是本轮最高风险任务。

---

## T07 — Assessment Evidence Sufficiency

在：

```text
_build_context_pack()
→ Gate
→ generate
```

实现真实字段 Minimum Policy。

`document_refs` 空值只作为 limitation，不做硬依赖。

**Cost：MEDIUM**

---

## T08 — Assessment Citation Validity + Escalation / API

在：

```text
repair
→ Citation Validity
→ ControlDecision
→ render
```

实现 Existence / Eligibility / Traceability。

形成 Pilot B 闭环。

**Cost：HIGH / MEDIUM**

---

## T09 — Frontend Minimal Exposure

处理：

- result status；
- clarification；
- review warning；
- trace raw_name semantic mapping。

必须保留实施开始时 ModuleRunPanel 的已有未提交修改。

**Cost：MEDIUM**

---

## T10 — Regression + FACT Refresh

至少覆盖：

### Diagnosis

- evaluate；
- report；
- Harness；
- Assessment internal diagnosis reuse。

### Assessment

- sync；
- async；
- Evidence；
- Citation；
- consistency；
- renderer；
- V0 Task Gateway。

### Shared

- EU SCC；
- US14117；
- CN Flow；
- common citation；
- WorkflowPipeline；
- Trace。

完成后重新扫描 HEAD 并更新 FACT。

**Cost：MEDIUM**

---

# 12. 回归硬边界

## 12.1 Diagnosis

必须保证：

```text
control disabled
→ original DiagnosisService semantics
```

Assessment 内部调用保持原行为。

---

## 12.2 Assessment

首轮不得要求其他 Pipeline 使用者执行新 Gate。

---

## 12.3 Citation

禁止：

- title fuzzy join 作为治理依据；
- synthetic provider ID 假装 SourceRegistry ID；
- 修改公共 citation default policy 未做全模块回归。

---

## 12.4 Shared Model

如果扩展：

- CitationItem；
- GenerationContextPack；
- DiagnosisResult；
- AssessmentResult；

必须：

```text
optional / defaulted / additive
```

不得增加 required field 破坏旧构造。

---

## 12.5 Legal Control != Runtime Failure

严禁：

```text
NEEDS_REVIEW
→ task FAILED
```

法律状态与程序状态分离。

---

# 13. 实施验收

## 13.1 Pilot A

必须证明：

1. 完整 deterministic case 结果不变；
2. missing fact 能产生 NEEDS_CLARIFICATION；
3. conflict 保留原 manual_review 并产生 NEEDS_REVIEW；
4. non-default Rule path 不被 LLM explanation 改写；
5. default AI inference 不被错误标 deterministic；
6. Assessment 复用 Diagnosis 未被默认 Gate 改变；
7. Trace 可见 Control 事件。

---

## 13.2 Pilot B

必须证明：

1. 正常 Assessment 原报告链正常；
2. Evidence Gate 在 ContextPack 后运行；
3. local registered source 能 exact lookup Eligibility；
4. `can_be_cited=false` / `can_enter_external_report=false` 来源不能作为正式通过 Citation；
5. unregistered fallback / DeliLegal source fail-closed；
6. Citation 去重后关系不丢失；
7. final Citation Gate 在 repair 后、render 前；
8. NEEDS_REVIEW 不导致 task FAILED；
9. 其他 Pipeline 使用者默认行为不变；
10. Trace/UI 能看到 ControlDecision。

---

# 14. 开发交付要求

每个 Task 返回：

1. 实际文件 / 类 / 方法；
2. 修改方式；
3. 复用能力；
4. 新增能力；
5. Regression Scope；
6. 测试；
7. 设计差异；
8. 当前状态。

如果实现与 V0.3 不一致：

```text
Designed
→ Implemented
→ Difference
→ Reason
→ Architecture impact
```

必须记录。

---

# 15. 设计变更门槛

开发过程中以下修改不需要重新做 Architecture Review：

- 类名；
- 文件目录；
- 参数名；
- dataclass / Pydantic 选择；
- Adapter 的局部组织。

以下修改必须反馈架构设计者：

1. 无法保持 Diagnosis opt-in；
2. 必须修改公共 WorkflowPipeline 默认行为；
3. canonical source identity 无法建立；
4. Citation Eligibility 无法 exact lookup；
5. 必须引入新的 LLM Judge 才能完成 V1；
6. `task_status` 必须与 legal control 混用；
7. 必须新增 Central Runtime；
8. 其他模块产生不可隔离回归。

---

# 16. Final Implementation Definition

本轮实现成功的最低标准：

```text
Existing DataComplyFlow
+
GateResult / ControlDecision
+
Diagnosis Controlled Decision Path
+
Assessment Controlled Generation Path
+
Trace / UI Exposure
```

不要求：

```text
All 11 Modules Migrated
```

最终两条真实链必须成立。

## Decision-oriented

```text
Final Facts
→ Fact Completeness
→ Deterministic Rule
→ Rule Precedence
→ Escalation
→ Diagnosis Result
```

## Generation-oriented

```text
ContextPack
→ Minimum Evidence Sufficiency
→ Generation
→ Consistency / Repair
→ Citation Validity
→ Escalation
→ Assessment Artifact
```

---

# 17. 实施完成后的 FACT Refresh

代码完成后重新生成事实基线，必须记录：

- final HEAD；
- Control contracts 真实代码位置；
- Gate 实际接口；
- Diagnosis opt-in 方式；
- Assessment Adapter 方式；
- canonical citation identity；
- Eligibility lookup；
- Trace；
- UI；
- regression；
- 其他模块影响；
- 与 V0.3 差异。

只有新 FACT 支持后，状态更新为：

```text
IMPLEMENTED
VALIDATED
```

2026-08-16 状态：两个 pilot 已达到 `IMPLEMENTED / TECHNICALLY_VALIDATED`。实际实现补充了 default-false 请求开关、前端显式 opt-in，以及 `WorkflowPipeline.before_render` 可选 seam，从而满足 `repair → Citation Validity → Escalation → render`。组合后端回归 378 passed，前端 205 passed / 2 skipped，`tsc -b` 与 Registry 零漂移检查通过。生产发布、数据/法律签字和回滚演练仍未完成。

---

# 18. Final Development Verdict

> **V0.3 首轮两个 pilot 已完成技术实现与代码验收；当前可进入数据/法律签字和受控灰度，不代表已经生产发布。**

实施过程中如果某个 Gate 需要大规模改造现有业务链才能落地：

> **优先缩小 Gate 或重新设计 Adapter，不扩大重构。**
