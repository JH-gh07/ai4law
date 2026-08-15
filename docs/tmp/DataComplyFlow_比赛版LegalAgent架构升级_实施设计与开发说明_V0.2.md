# DataComplyFlow 比赛版 Legal Agent 架构升级——实施设计与开发说明 V0.2

> **Document Type**：Architecture Implementation Design / Development Contract  
> **Status**：REVIEW CANDIDATE  
> **Version**：V0.2  
> **Primary Consumer**：DataComplyFlow 项目开发负责人  
> **Related Document**：`DataComplyFlow_比赛版LegalAgent架构升级_设计依据与架构决策_V0.2.md`  
> **Purpose**：将已冻结的 Legal Agent Control Plane 设计映射到当前真实代码，明确插入点、最小公共契约、Pilot 隔离方式、任务顺序、禁止修改项与功能验收条件  
> **Out of Scope**：Benchmark、11 模块全面迁移、完整 Runtime 重写、RAG 替换

---

# 0. 实施基线与硬约束

## 0.1 本文职责

WHY 解释为什么这样设计。

本文只回答：

> **开发负责人基于当前 HEAD 应该如何以最小影响实现。**

## 0.2 Current FACT

当前：

- 11 个正式业务模块；
- Assessment / EO 14117 / EU SCC / CN Flow 使用或部分使用公共 `WorkflowPipeline`；
- 其余模块保持专用 Service / Workflow；
- 公共层已有 Fact / Issue / Evidence / ContextPack、RAG、Citation、Trace、Reporting；
- `backend/harness/` 是 CLI 白盒 Harness；
- Assessment 内部会调用 DiagnosisService 做路径诊断；
- SourceRegistry 已提供来源审核、引用资格和外部报告资格。

## 0.3 实施原则

```text
Reuse > Extend > Adapter > Insert > Replace
```

## 0.4 Pilot Isolation Principle

**硬约束：**

> Pilot Control 必须 opt-in。

禁止通过修改共享 Service / Workflow 默认行为，隐式影响未迁移调用方。

特别是：

### Diagnosis

Assessment 内部复用 DiagnosisService，因此 Diagnosis Pilot 不得直接改变 DiagnosisService 的全局默认控制语义。

### Assessment

`WorkflowPipeline` 被多个模块共享，因此 Evidence Gate 不得写死为所有 Pipeline 使用者默认步骤。

## 0.5 禁止范围

禁止：

- 重写 11 模块；
- 全部迁移 WorkflowPipeline；
- 重写 Task Runtime；
- 替换 Rule Engine；
- 替换 RAG / Embedding；
- Full Policy Graph；
- 引入新 Agent Runtime；
- 重写 Reporting；
- 新统一 Claim IR；
- 新 HarnessContext；
- 将 CLI `backend/harness/` 改造成 Agent Runtime。

---

# 1. Current → Target 组件映射

| Current | 处理 | Target Role |
|---|---|---|
| `FactItem` | 复用/适配 | Fact Gate Input |
| Diagnosis 专用 Facts | Adapter | Fact Gate Input |
| `IssueItem` | 保留 | Domain Finding |
| `EvidenceItem` | 复用 | Evidence Gate Input |
| `CitationItem / CitationRegistry` | 复用 | Citation Validity Input |
| SourceRegistry | 复用 | Citation Eligibility Source |
| Domain Rule Engine | 完全保留 | Deterministic Decision Source |
| `WorkflowPipeline` | 保留 | Existing Workflow |
| Specialized Workflow | 保留 | Existing Workflow |
| RAG Service | 保留 | Retrieval Provider |
| UsagePolicyFilter | 复用 | Source Usage Policy |
| TraceRecorder | 扩展 event | Control Event Sink |
| Reporting | 保留 | Artifact Output |
| Task status | 保留 | Runtime Status |
| `backend/harness/` | 完全独立 | CLI / Evaluation Harness |

---

# 2. 最小公共契约

本轮只新增两个真正公共的概念。

## 2.1 `GateResult`

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

### `gate`

首轮：

```text
FACT_COMPLETENESS
DETERMINISTIC_RULE_PRECEDENCE
EVIDENCE_SUFFICIENCY
CITATION_VALIDITY
ESCALATION
```

### `outcome`

统一只使用：

```text
PASS
CONDITIONAL
ESCALATE
BLOCK
```

各 Gate 的领域判断放入 `details`。

例如 Fact：

```text
details.fact_states = {
  "is_ciio": "UNKNOWN"
}
```

Evidence：

```text
details.support_status = "PARTIAL"
```

这样 Control Plane 不需要理解每个 Gate 的所有领域枚举。

## 2.2 `ControlDecision`

```text
ControlDecision
├── legal_control_status
├── gate_results[]
├── reasons[]
└── required_actions[]
```

### `legal_control_status`

冻结：

```text
AUTO
CONDITIONAL
NEEDS_CLARIFICATION
NEEDS_REVIEW
BLOCKED
```

## 2.3 Task Status 与 Legal Control Status

严禁混用。

```text
task_status
```

描述程序任务生命周期。

```text
legal_control_status
```

描述法律结论的自动化可用程度。

允许：

```text
task_status = COMPLETED
legal_control_status = NEEDS_REVIEW
```

## 2.4 Trace Event

建议：

```text
control.fact_completeness
control.rule_precedence
control.evidence_sufficiency
control.citation_validity
control.escalation
```

Event 至少记录：

```text
outcome
refs
reason_summary
required_actions
```

---

# 3. Change Card FG-01 — Fact Completeness Gate

## 3.1 Current FACT

CN Diagnosis 当前已有：

```text
DiagnosisAnswers
→ DiagnosisService
→ normalization
→ missing/conflict check
→ Rule Engine
→ DiagnosisDecision
→ DiagnosisResult
```

因此本轮不是新增“事实检查”，而是把已有 missing/conflict 结果转化为可以控制后续执行的统一 GateResult。

## 3.2 Target

```text
Normalized Facts
→ Existing Missing / Conflict Check
→ Fact Gate Adapter
→ PASS / CLARIFY / REVIEW
→ Existing Rule Engine
```

## 3.3 Critical Isolation Requirement

Assessment 会复用 DiagnosisService。

因此不允许：

```text
DiagnosisService.evaluate()
→ 默认强制 Fact Gate
```

推荐两类实现：

### Option A：模块边界 Adapter

```text
Diagnosis API / Module Boundary
→ Fact Gate
→ existing DiagnosisService
```

### Option B：显式 opt-in

```text
DiagnosisService.evaluate(..., control_enabled=False)
```

仅正式 Diagnosis Pilot 调用：

```text
control_enabled=True
```

开发可选择实现方式，但 **opt-in 语义必须保留**。

## 3.4 Input

优先消费已有：

- normalized facts；
- missing facts；
- conflict result。

禁止重新从 Request 二次解析事实。

## 3.5 Output

GateResult 示例：

```text
gate = FACT_COMPLETENESS
outcome = ESCALATE

details:
  fact_states:
    is_ciio = UNKNOWN
  missing_fact_keys:
    - is_ciio

required_actions:
  - ASK_USER
```

## 3.6 Clarification

首轮不要求 LLM 动态生成问题。

优先：

```text
missing_fact_key
→ predefined user-facing clarification
```

## 3.7 Functional Acceptance

- 完整输入：原路径结论保持一致；
- 关键事实缺失：`legal_control_status = NEEDS_CLARIFICATION`；
- 冲突事实：不得输出无条件确定路径；
- Trace 可见 Fact Gate；
- Assessment 内部 Diagnosis 调用不因 Pilot 默认改变。

## 3.8 Do Not Change

- Decision Tree；
- Rule 阈值；
- 法律路径定义；
- API Path；
- EU / US；
- 不增加 LLM Fact Judge。

---

# 4. Change Card RG-01 — Deterministic Rule Precedence Gate

## 4.1 名称与边界

正式名称：

> **Deterministic Rule Precedence Gate**

中文：

> **确定性规则优先门禁**

该 Gate 表达的是：

> **Execution Precedence**

不是法规来源的：

- `authority_level`
- `binding_force`
- Legal Source Authority

不得将 Rule Engine 输出描述为“具有法律权威”。

## 4.2 Current FACT

多个模块当前已有 deterministic Rule：

- Diagnosis；
- EU SCC；
- EO 14117；
- TIA；
- CPRA。

## 4.3 Target

```text
Rule Engine
→ Rule Precedence Adapter
→ downstream LLM / explanation
→ conflict check
→ ControlDecision
```

## 4.4 Gate Input

现有 Rule Engine 结果。

## 4.5 Gate Output

```text
gate = DETERMINISTIC_RULE_PRECEDENCE
outcome = PASS

details:
  deterministic_result = ...
  execution_precedence = true
  rule_refs = [...]
```

## 4.6 Conflict Policy

如果 downstream probabilistic output 与 deterministic result 冲突：

```text
outcome = ESCALATE
legal_control_status = NEEDS_REVIEW
```

不得静默采用 LLM 结果覆盖 Rule。

## 4.7 Diagnosis V1

如果开发确认 Diagnosis 在 Rule 之后根本不存在可能改变路径的 LLM 输出，则 V1 不需要额外构造冲突判定器。

只需要：

- 显式标记 deterministic decision；
- 写 Trace；
- 保证后续解释链不能改写路径字段。

这比人为制造新的 LLM 校验更符合最小实现原则。

## 4.8 Acceptance

- 原 Rule 结果不变；
- deterministic result 可被显式识别；
- downstream output 不可静默改变路径；
- Trace 可见 precedence event。

---

# 5. Change Card EG-01 — Evidence & Citation Gate

## 5.1 Current FACT

Assessment 当前已有：

```text
Facts
→ Issues
→ Evidence
→ per_issue_rag
→ GenerationContextPack
→ Chapters
→ consistency/alignment
→ repair
→ reporting
```

并已有：

- EvidenceItem；
- CitationRegistry；
- SourceRegistry；
- UsagePolicyFilter；
- RAG。

因此本轮不新建 Evidence Pipeline。

## 5.2 Pilot Isolation

公共 `WorkflowPipeline` 同时被其他模块使用。

禁止：

```text
WorkflowPipeline.run()
→ 默认强制 Evidence Gate
```

推荐：

### Option A

Assessment-specific Adapter。

### Option B

`WorkflowPipeline` 增加 optional injected hook：

```text
evidence_gate=None
citation_gate=None
```

只有 Assessment Pilot 注入真实实现。

## 5.3 Evidence Sufficiency V1

正式名称：

> **Minimum Evidence Sufficiency Policy**

不声称已经完整解决 evidence closure。

### V1 可以使用的已有结构

```text
EvidenceItem.fact_refs
EvidenceItem.rule_refs
EvidenceItem.citation_refs
EvidenceItem.document_refs
EvidenceItem.strength
EvidenceItem.status
```

### 建议最低规则

#### E1

核心 Issue 无事实关联：

```text
PARTIAL / UNSUPPORTED
```

#### E2

要求法律依据的 Claim / Finding 无 regulation / citation：

```text
UNSUPPORTED
```

#### E3

唯一支持 Evidence 为 UNVERIFIED：

```text
PARTIAL
```

#### E4

存在冲突 Evidence：

```text
CONFLICTED
```

#### E5

引用来源 `can_be_cited = false`：

不得作为正式强 Claim 的充分法律 Evidence。

## 5.4 Evidence 插入点

设计必须满足：

> 正式进入 Generation Context 前存在一次 sufficiency 判断。

概念：

```text
build_evidence()
→ per_issue_rag
→ Evidence Sufficiency Gate
→ build_context_pack()
```

真实位置由开发根据当前调用签名确认。

## 5.5 Citation Validity V1

V1 只冻结：

```text
Existence
Eligibility
Traceability
```

### C1 Existence

Citation 是否可通过现有 CitationRegistry / CitationMap 正常解析。

### C2 Eligibility

基于 SourceRegistry：

```text
review_status
can_be_cited
can_enter_external_report
allowed_usage
authority_level
binding_force
```

判断来源是否允许用于当前输出。

### C3 Traceability

Citation 是否可追溯到当前：

- issue；
- fact；
- evidence。

## 5.6 Citation Join Key — 必须由开发确认

当前 CitationItem 与 SourceRegistry 的稳定 Join Key 必须明确。

开发需要确认：

> CitationItem / Retrieval Hit 中是否已有稳定 `source_id` 可直接连接 SourceRegistry？

如果已有：

> 复用。

如果没有：

> 最小扩展 `source_id` 或复用现有 stable ID。

**禁止：**

通过法规标题文本做模糊 Join。

## 5.7 V1 不承诺

首轮不声称完整实现：

- Semantic Fidelity；
- Fine-grained Applicability；
- LegalCiteTrust 全 E/F/A；
- LLM Citation Judge。

如果当前已有结构足以判断部分 Applicability，可作为增强，但不得成为首轮依赖。

## 5.8 Claim Unit

首轮不新增统一 Claim IR。

优先使用已有：

- `EvidenceItem.claim`；
- Issue finding；
- 报告核心 statement；

作为最小验证单元。

## 5.9 Citation 插入点

设计必须满足：

> 正式报告渲染前存在一次 Citation Validity 检查。

概念：

```text
generate_chapters()
→ Citation Validity
→ existing consistency/alignment
→ Escalation
→ reporting
```

若现有 consistency checker 已承担相同职责，应优先复用而不是重复实现。

## 5.10 Acceptance

- 正常 Evidence：正常生成；
- 核心 Evidence 缺失：PARTIAL / UNSUPPORTED；
- quarantine source：不得作为正式 Citation 通过；
- Citation 无稳定关联：进入 CONDITIONAL / NEEDS_REVIEW；
- 其他 `WorkflowPipeline` 模块默认行为不变；
- Trace 可见 evidence / citation events。

---

# 6. Change Card ES-01 — Escalation Gate

## 6.1 Purpose

将多个 GateResult 汇总成一个统一 `ControlDecision`。

## 6.2 Mapping

### AUTO

Fact Pass + no deterministic conflict + supported evidence + valid citation。

### CONDITIONAL

证据部分充分，但可以通过限定表达继续。

### NEEDS_CLARIFICATION

关键 Fact UNKNOWN / AMBIGUOUS，且补充事实后可继续。

### NEEDS_REVIEW

- deterministic vs probabilistic conflict；
- evidence conflict；
- citation traceability / eligibility 无法可靠确认。

### BLOCKED

关键支持不存在，且任务要求正式法律结论。

## 6.3 Human Escalation Boundary

V1 的：

```text
NEEDS_REVIEW
```

只表示：

> **Human Escalation State**

不表示已实现完整：

```text
pause
→ reviewer action
→ resume
```

的 HITL Runtime。

## 6.4 API Contract

建议 additive 增加：

```text
legal_control_status
control_reasons
required_actions
```

不得改写 `task_status`。

## 6.5 Acceptance

至少存在：

- AUTO；
- NEEDS_CLARIFICATION；
- CONDITIONAL / NEEDS_REVIEW；
- BLOCKED 或明确说明首轮哪些业务不触发 BLOCKED。

---

# 7. Pilot A — CN Transfer Diagnosis

## 7.1 Target

验证 Decision-oriented Legal Task：

```text
Request
→ Existing Normalization
→ Existing Missing / Conflict
→ Fact Completeness Gate
→ Existing Rule Engine
→ Deterministic Rule Precedence
→ Existing Explanation / RAG
→ Escalation
→ Diagnosis Result
→ Trace
```

## 7.2 Must Preserve

- API；
- input schema；
- Decision Tree；
- threshold；
- recommended path semantics；
- 正常案例路径；
- Assessment 内部 Diagnosis 默认语义。

## 7.3 Suggested Additive Output

```text
legal_control_status
control_reasons
required_actions
clarification_questions
```

## 7.4 Functional Scenarios

### D1 完整事实

```text
task_status = COMPLETED
legal_control_status = AUTO
```

原路径不变。

### D2 缺关键事实

```text
task_status = COMPLETED
legal_control_status = NEEDS_CLARIFICATION
```

带具体待补事实。

### D3 冲突事实

```text
legal_control_status = NEEDS_REVIEW / CONDITIONAL
```

不得输出无条件确定路径。

### D4 downstream explanation 冲突

Rule path 保留，ControlDecision 升级。

---

# 8. Pilot B — CN Security Assessment

## 8.1 Target

验证 Generation-oriented Legal Task：

```text
Facts
→ Issues
→ Evidence
→ per_issue_rag
→ Minimum Evidence Sufficiency
→ ContextPack
→ Generation
→ Citation Validity V1
→ consistency/alignment
→ Escalation
→ Reporting
```

## 8.2 Must Preserve

- Assessment API；
- 原主要业务输入；
- 原 WorkflowPipeline 主链；
- 原报告章节；
- RAG 索引；
- CitationRegistry；
- Reporting；
- 其他 WorkflowPipeline 模块默认行为。

## 8.3 Formal Report Behavior

### SUPPORTED

正常生成。

### PARTIAL

条件式表达：

```text
legal_control_status = CONDITIONAL
```

### UNSUPPORTED

核心 Claim 不得作为无保留正式法律结论。

### CONFLICTED

```text
legal_control_status = NEEDS_REVIEW
```

---

# 9. Frontend Minimal Exposure

不重构 Workspace。

只要求用户能感知：

```text
AUTO
CONDITIONAL
NEEDS_CLARIFICATION
NEEDS_REVIEW
BLOCKED
```

## 9.1 Diagnosis

`NEEDS_CLARIFICATION`：

展示：

- 为什么不能直接判断；
- 缺哪些信息；
- 可返回原表单补充。

## 9.2 Assessment

`CONDITIONAL`：

展示报告存在待确认结论。

`NEEDS_REVIEW`：

展示当前成果建议人工复核。

## 9.3 Trace

优先使用现有 RunTranscript / TraceNodeView。

如果前端不支持新 event type，可暂映射为：

```text
intermediate / warning
```

但 detail 中保留完整 Control Event。

---

# 10. 开发任务顺序

## T01 — Core Contract

新增：

```text
GateResult
ControlDecision
legal_control_status
```

不改变业务行为。

## T02 — Trace Integration

支持 `control.*` event。

## T03 — Diagnosis Fact Gate

必须 opt-in 隔离。

## T04 — Diagnosis Rule Precedence

显式 deterministic execution precedence。

## T05 — Diagnosis Escalation

形成第一个完整 ControlDecision。

## T06 — Assessment Evidence Gate

Assessment-specific hook，不影响其他 WorkflowPipeline 使用者。

## T07 — Assessment Citation Validity V1

先完成 Existence / Eligibility / Traceability。

## T08 — Assessment Escalation

形成第二个完整 ControlDecision。

## T09 — Frontend Minimal Status

仅展示 Control Status / clarification / review warning。

## T10 — Regression + FACT Refresh

- 现有功能回归；
- 两 Pilot 验证；
- 其他 9 模块未受影响；
- 更新当前 HEAD FACT；
- WHY/HOW 状态回写。

---

# 11. 开发前 Fact / Feasibility Review

开发负责人正式写代码前必须回答：

## Q1

Diagnosis missing / conflict check 的真实返回对象及调用位置是什么？

## Q2

Assessment 调用 DiagnosisService 的具体入口及参数是什么？

## Q3

如何确保 Diagnosis Pilot Control 不改变 Assessment 内部 Diagnosis 默认行为？

## Q4

Diagnosis Rule 后是否存在任何 LLM 步骤可能改写路径性结论？

若不存在，Rule Precedence V1 不增加多余冲突 Judge。

## Q5

Assessment 中：

```text
build_evidence
retrieve_per_issue
build_context_pack
```

真实调用顺序是什么？

## Q6

EvidenceItem 当前字段实际填充率如何？哪些字段只是 Schema 存在但运行时常为空？

## Q7

CitationItem / Retrieval Hit 与 SourceRegistry 当前的稳定 Join Key 是什么？

若没有，最小扩展方案是什么？

## Q8

当前 consistency / alignment checker 是否已经承担部分 citation mismatch / unsupported claim 检查？

有则复用。

## Q9

TraceRecorder 是否支持自定义 event / metadata？

## Q10

当前 API Response 最适合在哪个层级 additive 增加：

```text
legal_control_status
control_reasons
required_actions
```

## Q11

前端 RunTranscript 是否可直接展示新增 control event？

## Q12

Assessment Evidence Gate 若通过 WorkflowPipeline optional hook 接入，会影响哪些共享调用方和测试？

## Q13

SourceRegistry 的 `can_be_cited / can_enter_external_report / allowed_usage` 是否能从当前 Citation 所持有的数据稳定查询？

## Q14

是否存在本设计未识别的共享 Service 调用关系，可能造成 Pilot 跨模块回归？

---

# 12. Regression / Rollback

## 12.1 Additive API

所有 Control 字段 additive only。

## 12.2 Legacy Modules

未迁移模块继续：

```text
original workflow
```

## 12.3 Bypass

推荐支持 module-level control enable / disable。

不是强制 Feature Flag，但新 Control 必须可低成本旁路。

## 12.4 Pilot Failure Isolation

Diagnosis Gate 问题不得影响 Assessment。

Assessment Gate 问题不得影响 EO 14117 / EU SCC / CN Flow。

---

# 13. Implementation Ledger

| ID | Work Item | Initial Status | Regression Scope |
|---|---|---|---|
| T01 | Core Contract | DESIGNED | Common only |
| T02 | Trace Integration | DESIGNED | Trace |
| T03 | Diagnosis Fact Gate | DESIGNED | Diagnosis only |
| T04 | Diagnosis Rule Precedence | DESIGNED | Diagnosis only |
| T05 | Diagnosis Escalation | DESIGNED | Diagnosis only |
| T06 | Assessment Evidence Gate | DESIGNED | Assessment only |
| T07 | Assessment Citation Validity | DESIGNED | Assessment / Citation |
| T08 | Assessment Escalation | DESIGNED | Assessment only |
| T09 | Frontend Minimal Exposure | DESIGNED | Two Pilots |
| T10 | Regression + FACT Refresh | DESIGNED | Repo-wide verification |

---

# 14. 开发交付格式

每个 Task 完成后开发负责人返回：

1. 修改位置；
2. 实际实现方式；
3. 复用的现有组件；
4. 新增对象；
5. 是否改变原业务结果；
6. Regression Scope；
7. 测试结果；
8. 当前 Status；
9. 与设计的差异及理由。

若设计与实际实现不同，必须记录：

```text
Designed
→ Implemented
→ Difference
→ Reason
```

---

# 15. 首轮完成定义

本轮不要求：

```text
Unified Agent Runtime
```

只要求真实形成：

```text
Existing DataComplyFlow
+
Legal Agent Control Plane Core
+
Diagnosis Pilot
+
Assessment Pilot
```

## Decision-oriented

```text
Facts
→ Fact Completeness
→ Deterministic Rule
→ Rule Precedence
→ Escalation
→ Decision
```

## Generation-oriented

```text
Facts
→ Issues
→ Evidence
→ Minimum Evidence Sufficiency
→ Generation
→ Citation Validity
→ Escalation
→ Artifact
```

如果两条链真实运行、ControlDecision 可观察、其他模块保持稳定，本轮比赛版架构升级达到预期。

---

# 16. 实现完成后的事实更新

开发结束后必须重新扫描真实 HEAD，更新 FACT：

- Control Plane 实际代码位置；
- Gate 实际接口；
- Pilot 实际接入方式；
- opt-in 隔离是否成立；
- Citation Join Key；
- Trace；
- Frontend；
- Regression；
- 未迁移模块；
- 设计与实现差异。

只有新 FACT 支持后，相关状态才可从：

```text
DESIGNED
```

升级为：

```text
IMPLEMENTED / VALIDATED
```

## 最终开发裁决

> **如果某个 Gate 为了接入需要大规模修改现有业务流程，优先重新设计 Adapter，而不是扩大重构。**
