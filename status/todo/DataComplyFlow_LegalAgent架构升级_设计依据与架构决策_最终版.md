# DataComplyFlow 比赛版 Legal Agent 架构升级——设计依据与架构决策 V0.3

> **Document Type**：Architecture Rationale / Final Design  
> **Status**：FINAL DESIGN — READY FOR IMPLEMENTATION  
> **Version**：V0.3  
> **Design Baseline Review**：`DataComplyFlow Legal Agent 架构升级：开发事实与可行性审查 V0.1`  
> **Reviewed Code Baseline**：branch `new`，HEAD `2b9f5d16e397cf760216a4b6f8cc90d884a96dbc`（2026-08-15）  
> **Primary Purpose**：冻结比赛阶段 Legal Agent 架构升级的设计依据、系统边界、技术主线与实现范围  
> **Out of Scope**：Benchmark 指标体系、全量 Runtime 重构、11 模块全面迁移、新 Agent Framework 迁移

---

# 0. 文档定位、事实基线与设计状态

## 0.1 文档定位

DataComplyFlow 当前已经形成 CN / EU / US 三法域 11 个正式业务模块，并具备确定性 Rule Engine、LLM、RAG、Citation、Trace、Reporting、Artifact 等公共能力。

本轮架构升级不重新建设 Legal AI 平台，而是在现有 Domain Workflow 基础上增加轻量控制层，使系统能够统一回答：

1. 当前关键事实是否足以继续；
2. 确定性规则是否已经形成必须优先遵守的执行结果；
3. 当前 Evidence 与 Citation 是否满足最低支持和治理条件；
4. 当前自动化结果应该正常输出、条件输出、补充事实还是人工复核。

冻结目标为：

> **Existing Domain Workflow + Module Adapter + Four Legal Control Gates + GateResult / ControlDecision**

不建设新的统一 Workflow Runtime，不建设新的 Agent Graph。

---

## 0.2 当前事实基线

V0.3 的代码映射依据 2026-08-15 开发事实审查，审查 HEAD：

```text
branch: new
HEAD:   2b9f5d16e397cf760216a4b6f8cc90d884a96dbc
```

审查对两个 Pilot 的真实调用链、共享 Service、WorkflowPipeline、EvidenceItem、CitationRegistry、SourceRegistry、Trace 和前端展示链进行了源码核验，并执行聚焦测试：

```text
68 passed
```

V0.3 对 V0.2 的修订以该审查为直接事实依据。

如果后续开发开始时 HEAD 已发生影响以下链路的变化：

- CN Diagnosis；
- CN Security Assessment；
- WorkflowPipeline；
- Citation / SourceRegistry；
- Trace；
- ModuleRunPanel；

则开发负责人应先做一次 delta check，再按本设计实施。

---

## 0.3 当前真实 Workflow 结构

当前生产代码存在 3 个直接 `WorkflowPipeline(...)` 实例：

- CN Security Assessment；
- EU SCC；
- US EO 14117。

历史 CN Flow 入口通过 `CNFlowService.canonical_service` 委托 US EO 14117，因此属于**间接经过 Pipeline**，不是第四个独立 Pipeline 实例。

其余业务模块保留专用 Service / Workflow。

因此本设计继续坚持：

> **不统一 Domain Workflow，只统一跨 Workflow 的 Legal Control 语义。**

---

## 0.4 设计状态

V0.3 之后：

- Control Plane 架构：`DESIGNED / FINAL`
- Gate Contract：`DESIGNED / FINAL`
- Diagnosis Pilot：`IMPLEMENTED / TECHNICALLY_VALIDATED`
- Assessment Pilot：`IMPLEMENTED / TECHNICALLY_VALIDATED`
- 其他模块：`NOT_MIGRATED`

实现与验收依据：`status/view/20260815_LegalAgent控制平面实施FACT刷新与差异记录.md`（2026-08-16 收尾复验）。生产状态仍为 `NOT_RELEASED`，数据/法律签字与灰度不由技术验收替代。

---

# 1. 当前系统真实能力与真实缺口

## 1.1 当前已经存在的能力

当前已经真实存在：

```text
Domain Services / Workflows
Deterministic Rule Engines
Fact / Issue / Evidence
RAG / Knowledge
CitationRegistry / CitationItem
SourceRegistry
TraceRecorder
Reporting
Task / Artifact
```

因此本轮不是“补齐不存在的基础设施”。

---

## 1.2 当前 Evidence 的真实边界

公共 `EvidenceItem` 已能表达：

- `claim`
- `fact_refs`
- `rule_refs`
- `document_refs`
- `legal_basis`
- `supporting_basis`
- `discarded_basis`
- `confidence`
- `used_by`
- RAG query / hit metadata

但当前 Assessment 运行时存在重要边界：

- 不存在 `EvidenceItem.citation_refs`
- 不存在 `EvidenceItem.status`
- 不存在 `EvidenceItem.strength`
- `document_refs` 在正常链中通常为空
- `supporting_basis / discarded_basis / issue_refs` 当前常为空
- per-issue RAG 不回写 EvidenceItem

因此 V1 Evidence Gate 必须使用真实字段，不得把 Schema 中不存在或运行时未填充的字段当成已实现能力。

---

## 1.3 当前 Citation 的真实边界

当前已有：

- CitationRegistry；
- CitationItem；
- CitationMap 输出；
- SourceRegistry；
- `source_id`；
- issue / fact 等关联信息。

但 SourceRegistry 的治理信息并未完整传播到 CitationItem：

```text
review_status
can_be_cited
can_enter_external_report
allowed_usage
authority_level
binding_force
```

本地 multi-index 路径通常具有稳定 SourceRegistry `source_id`；fallback / DeliLegal 路径的 synthetic/provider ID 不保证是 SourceRegistry ID。

因此：

> **Citation Eligibility 不能依赖 CitationItem 自身的推断属性，必须通过 canonical source identity 精确回查 SourceRegistry。**

---

## 1.4 当前 Diagnosis 的真实边界

Diagnosis 真实执行并不是：

```text
Normalization → Rule
```

而是：

```text
_resolve_answers()
→ ImportantData / PIClassify / Exemption Agents
→ facts_from_module()
→ conflict validation
→ deterministic Rule Engine
→ non-default deterministic result
   or
   default → AI inference
```

ImportantData / PIClassify Agent 可将 UNKNOWN 改写为 yes/no；default RuleMatch 后还可能由 `_build_ai_inference_result()` 生成新的路径性结果。

因此 Fact Gate 与 Rule Precedence Gate 必须严格遵循真实生命周期。

---

## 1.5 当前架构核心缺口

真实缺口继续冻结为四类 Control Problem：

### A. Fact Completeness

最终用于决策的事实中，哪些仍是 missing / ambiguous / inferred？

### B. Deterministic Rule Precedence

确定性 non-default RuleMatch 已经形成路径结论时，后续概率性步骤是否允许改写？

### C. Evidence / Citation

生成前是否满足最低 Evidence 支持；最终 Citation 是否存在、合规且可追溯？

### D. Escalation

自动化不能可靠完成时，怎样显式表达：

```text
AUTO
CONDITIONAL
NEEDS_CLARIFICATION
NEEDS_REVIEW
BLOCKED
```

---

# 2. 外部思想来源与项目采用边界

## 2.1 Agent Harness / Guardrails

OpenAI、Anthropic、LangGraph 等当前 Agent Engineering 均强调模型外围的：

- state；
- guardrail；
- trace；
- deterministic / probabilistic orchestration；
- human escalation / human-in-the-loop。

DataComplyFlow 不迁移这些框架，而吸收共同架构思想：

> **Agent 能力必须被外围执行控制约束，而不是把全部判断权交给 LLM。**

---

## 2.2 ContextLens → Fact Completeness

ContextLens 针对法律合规中的不完整和模糊上下文，将 known / unknown / ambiguous / missing factor 显式化。

本项目只采用：

> **关键 Unknown 不应被无记录地转化为确定结论。**

不复现其完整问题体系。

---

## 2.3 GraphCompliance → Rule–Fact Alignment

采用：

> 确定性 Rule 必须基于明确 Fact 条件，并保留 Fact provenance。

不采用：

- Full Policy Graph；
- Context Graph；
- Graph DB；
- 全面 GraphRAG。

---

## 2.4 RefWalk / LegalBench-RAG → Minimum Evidence Sufficiency

采用：

> Retrieval hit 不等于当前法律 Claim 已有足够支持。

首轮只建设：

> **Minimum Evidence Sufficiency Policy**

不声称解决完整 Evidence Closure。

---

## 2.5 LegalCiteTrust → Citation Validity

理论方向包括：

```text
Existence
Fidelity
Applicability
```

但基于当前真实代码，V1 只冻结可可靠实现的：

```text
Existence
Eligibility
Traceability
```

Semantic Fidelity / Fine-grained Applicability 作为后续增强。

---

## 2.6 LawThinker → Intermediate Verification

采用：

> 验证进入执行过程，而不是全部推迟到最终报告之后。

因此 Evidence Gate 位于 generation 前；最终 Citation Gate 位于 repair 后、render 前。

---

# 3. 架构设计原则

## P1 — FACT First

当前源码优先于设计假设。

## P2 — Incremental Overlay

优先 Adapter / additive field / small component，不重写业务链。

## P3 — Domain Workflow Autonomy

不同法律任务保留不同 Workflow。

## P4 — Deterministic Before Probabilistic

只有 **non-default deterministic RuleMatch** 才形成 execution precedence lock。

default RuleMatch 不被错误包装成确定性法律结论。

## P5 — Evidence Before Strong Claim

Evidence 未达到最低支持条件时，强 Claim 必须降级、限定或进入人工复核。

## P6 — Canonical Identity Before Citation Governance

Citation Eligibility 必须依赖 canonical SourceRegistry identity，而不是 title 模糊匹配或 provider synthetic ID。

## P7 — Explicit Uncertainty & Escalation

missing、inference、conflict、unsupported source 必须进入显式 ControlDecision。

## P8 — Reuse Before Rebuild

复用现有 Fact、Evidence、Citation、SourceRegistry、Trace、Reporting。

## P9 — Pilot Isolation

所有 Pilot 控制能力必须 opt-in。

不得改变：

- Assessment 对 DiagnosisService 的默认复用；
- EU SCC / US14117 / CN Flow 的 WorkflowPipeline 默认行为；
- 公共 Citation Pipeline 的默认语义。

## P10 — Per-run State Only

当前 router Service 为 singleton。

禁止将 `ControlDecision`、GateResult 等每次运行状态存入 Service 实例成员。

---

# 4. Final Target Architecture

```text
                    Existing Domain Workflow
                              │
                              ▼
                       Module Adapter
                              │
          ┌───────────────────┼────────────────────┐
          │                   │                    │
          ▼                   ▼                    ▼
 Fact Completeness     Deterministic        Evidence &
      Gate             Rule Precedence      Citation Gate
          │                   │                    │
          └───────────────────┼────────────────────┘
                              ▼
                       GateResult[]
                              │
                              ▼
                       Escalation Gate
                              │
                              ▼
                       ControlDecision
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
       Domain Result         Trace          UI / Artifact
```

本轮不建设：

- HarnessContext；
- Unified Claim IR；
- Central Agent Runtime；
- Universal Workflow Graph。

---

# 5. 四个 Gate 的最终定义

## 5.1 G1 — Fact Completeness Gate

真实评估对象：

- Agent 辅助后的最终 `DiagnosisFacts`
- `missing_facts`
- `field_provenance`
- 既有 conflict validation 结果

V1 行为：

### Critical missing

进入：

```text
NEEDS_CLARIFICATION
```

### Existing conflict

保持现有 manual-review 业务结果，同时增加：

```text
legal_control_status = NEEDS_REVIEW
```

### Decisive inferred facts

如果影响路径判断的关键事实来自 `LLM_INFERENCE / ESTIMATE / DEFAULT` 而非用户或确定性规则来源：

```text
legal_control_status = NEEDS_REVIEW
```

首轮不要求重新推断事实，只显式暴露不确定性。

---

## 5.2 G2 — Deterministic Rule Precedence Gate

只锁定：

> **non-default deterministic RuleMatch**

此时：

```text
execution_precedence = true
```

LLM 允许生成 explanation，不允许改变 `recommended_path`。

default RuleMatch：

```text
execution_precedence = false
```

继续允许现有 AI inference 分支工作，并由 Fact / Escalation 控制其不确定性。

本 Gate 描述的是系统执行顺序，不代表法规来源的 `authority_level / binding_force`。

---

## 5.3 G3-A — Minimum Evidence Sufficiency

真实插入点：

> `AssessmentService._build_context_pack()` 已完成之后、`generate_chapters()` 之前。

原因：

只有此时同时具有：

- facts；
- issues；
- EvidenceItem；
- per-issue RAG；
- legal_grounding；
- CitationRegistry。

V1 不依赖不存在的 `citation_refs/status/strength`。

最低判断使用：

- Issue fact/rule/evidence references；
- Evidence `fact_refs / rule_refs / legal_basis / confidence`；
- Fact `evidence_status / can_support_external_positive_claim`；
- `legal_grounding.by_issue`；
- 现有 consistency checker 的结构检查结果。

`document_refs` 在当前运行链中通常为空，因此 V1 不将其作为硬 PASS/BLOCK 条件；如开发顺带修复当前字符串引用提取缺口，可作为增强，但不成为架构前提。

---

## 5.4 G3-B — Citation Validity V1

最终插入点：

> repair 完成后、render 前。

最终 Gate 使用：

- final chapters；
- in-memory CitationRegistry；
- SourceRegistry exact lookup。

不依赖尚未写出的 CitationMap 文件。

V1 检查：

### Existence

最终引用是否可被 CitationRegistry 精确解析。

### Eligibility

canonical source identity 是否可精确回查 SourceRegistry，且符合：

```text
review_status
can_be_cited
can_enter_external_report
allowed_usage
```

### Traceability

Citation 是否保留足够的 issue / fact / evidence 关联。

外部或 fallback source 如果无法得到 canonical SourceRegistry identity：

> fail-closed，不得被视为“已审核正式法律 Citation”。

首轮不做 title fuzzy join。

---

## 5.5 G4 — Escalation Gate

统一形成：

```text
ControlDecision
```

其 `legal_control_status`：

```text
AUTO
CONDITIONAL
NEEDS_CLARIFICATION
NEEDS_REVIEW
BLOCKED
```

Pilot V1 实际要求：

- Diagnosis：AUTO / NEEDS_CLARIFICATION / NEEDS_REVIEW；
- Assessment：AUTO / CONDITIONAL / NEEDS_REVIEW。

`BLOCKED` 保留在公共契约中，但首轮两个 Pilot **不要求主动产生 BLOCKED**，除非现有确定性业务校验已经明确禁止继续。

这样避免把法律控制状态错误实现成 `task_status=FAILED`。

---

# 6. Task Status 与 Legal Control Status

严格分离：

```text
task_status
```

表示程序执行：

```text
RUNNING
COMPLETED
FAILED
...
```

```text
legal_control_status
```

表示法律结果自动化可用程度：

```text
AUTO
CONDITIONAL
NEEDS_CLARIFICATION
NEEDS_REVIEW
BLOCKED
```

合法组合包括：

```text
task_status = COMPLETED
legal_control_status = NEEDS_REVIEW
```

说明：

> 系统成功完成自动分析，但结果不应被视为无需人工复核的正式法律结论。

---

# 7. 两个 Pilot 的最终范围

## 7.1 Pilot A — CN Transfer Diagnosis

实现：

```text
Fact Completeness
+
Deterministic Rule Precedence
+
Escalation
```

真实 Gate seam：

```text
_resolve_answers()
→ existing Agents
→ facts_from_module()
→ existing conflict validation
→ Fact Gate
→ Rule Engine
→ Rule Precedence
→ existing explanation / default AI inference
→ Escalation
```

控制必须 default-off / opt-in。

Assessment 继续保持原：

```text
DiagnosisService.evaluate(answers)
```

默认行为。

---

## 7.2 Pilot B — CN Security Assessment

实现：

```text
Minimum Evidence Sufficiency
+
Citation Validity V1
+
Escalation
```

真实链：

```text
facts
→ issues
→ evidence
→ per_issue_rag
→ _build_context_pack()
→ Evidence Sufficiency
→ generate_chapters()
→ consistency
→ alignment
→ repair
→ Citation Validity
→ Escalation
→ render
```

首轮优先采用 Assessment-specific Adapter。

不先修改公共 WorkflowPipeline。

---

# 8. 技术评估

## 8.1 Mainstream Agent Engineering Alignment

**高。**

方案与当前主流 Agent Engineering 的 guardrail / trace / human escalation / deterministic-probabilistic orchestration 方向一致。

## 8.2 Legal Research Alignment

**高。**

直接对应：

- incomplete legal context；
- rule–fact consistency；
- evidence sufficiency；
- citation governance；
- intermediate verification。

## 8.3 Project Fit

**高。**

V0.3 已完全按当前运行字段和调用生命周期重新落位，不要求替换核心系统。

## 8.4 Engineering Risk

| Area | Risk |
|---|---|
| Core Contract | LOW |
| Trace | LOW |
| Diagnosis Fact Gate | MEDIUM |
| Rule Precedence | LOW |
| Diagnosis Escalation | MEDIUM |
| Evidence Sufficiency | MEDIUM |
| Citation Validity | **HIGH** |
| Assessment Escalation | MEDIUM |
| Frontend | MEDIUM |
| Regression | MEDIUM |

最高风险：

> **canonical source identity + SourceRegistry Eligibility + Citation traceability**

而不是 Gate 抽象本身。

---

# 9. 比赛技术故事线

## 9.1 Before

DataComplyFlow 已经具有：

```text
Rule
+
RAG
+
LLM
+
Citation
+
Trace
```

但各 Workflow 的控制方式仍分散。

## 9.2 Upgrade

新增轻量：

> **Legal Agent Control Plane**

## 9.3 After

冻结比赛表述：

> **DataComplyFlow 面向多法域数据合规任务，将确定性规则、法律 RAG 与大语言模型组织在统一的 Legal Agent Control Plane 下。系统在形成法律结果前显式检查关键事实是否充分、确定性 Rule 是否已形成不可被概率性语言生成静默改写的执行结论、当前 Evidence 是否满足最低支持条件以及 Citation 是否具有可验证的来源身份和使用资格；当自动化条件不足时，系统主动降级、请求补充事实或升级人工复核。**

## 9.4 四个可展示行为

1. 缺关键事实 → `NEEDS_CLARIFICATION`
2. non-default deterministic Rule → LLM explanation 不改变路径
3. Evidence / Citation 不足 → `CONDITIONAL / NEEDS_REVIEW`
4. task 完成但法律结果需复核 → `COMPLETED + NEEDS_REVIEW`

---

# 10. 创新边界

## 非原创

- Harness；
- Guardrail；
- Trace；
- Human escalation；
- Unknown-aware compliance；
- Evidence Closure；
- Citation Trustworthiness。

## DataComplyFlow 项目贡献

> **将通用 Agent Harness 的执行控制思想针对真实多法域数据合规任务进行领域特化，并在现有 Rule Engine、Legal RAG、Citation、Trace 和多种 Domain Workflow 之上形成可增量接入的 Fact–Rule–Evidence/Citation–Escalation 控制链。**

创新属于：

> **领域特化系统架构综合 + 真实多模块产品落地**

不声称发明 Harness 或首次提出 Citation Verification。

---

# 11. Non-goals

本轮明确不做：

- 11 模块全面迁移；
- One Giant Workflow；
- Full Policy Graph；
- Task Runtime 重写；
- LangGraph / OpenAI Agents SDK 迁移；
- RAG / Embedding 全量替换；
- 完整 Evidence Closure；
- 完整 E/F/A semantic verifier；
- LLM Citation Judge；
- 完整 pause/review/resume HITL Runtime；
- 新统一 Claim IR；
- HarnessContext；
- Reporting 重写；
- CLI `backend/harness/` 重定义。

---

# 12. Final Architecture Decisions

| ID | Decision |
|---|---|
| D01 | 不统一 Domain Workflow |
| D02 | 新增轻量 Legal Agent Control Plane |
| D03 | 保留 Four-Gate 主线 |
| D04 | Fact Gate 位于 Diagnosis Agents 后、Rule 前 |
| D05 | non-default RuleMatch 才具有 execution precedence |
| D06 | default RuleMatch 保持现有 AI inference 语义 |
| D07 | Evidence Gate 位于 ContextPack 构造后、generation 前 |
| D08 | Citation final Gate 位于 repair 后、render 前 |
| D09 | Citation V1 = Existence + Eligibility + Traceability |
| D10 | Eligibility 必须 exact SourceRegistry lookup |
| D11 | external / fallback source 无 canonical identity 时 fail-closed |
| D12 | 不把 EvidenceItem 不存在字段写入 V1 设计 |
| D13 | task_status 与 legal_control_status 分离 |
| D14 | V1 Pilot 不要求主动产生 BLOCKED |
| D15 | Diagnosis 与 Assessment 均 opt-in 隔离 |
| D16 | 首轮优先 Assessment-specific Adapter，不改公共 Pipeline |
| D17 | 不在 singleton Service 保存 per-run ControlDecision |
| D18 | 实施完成后重新生成 FACT |

---

# 13. Final Design Verdict

开发事实审查给出的结论为：

> `READY_WITH_MAJOR_IMPLEMENTATION_CHANGES`

V0.3 已完成这些实现级修订。

因此设计阶段裁决为：

> **IMPLEMENTED / TECHNICALLY_VALIDATED / NOT_RELEASED**

核心架构不再进入探索阶段。实现为满足 D08 增加了默认关闭的 `WorkflowPipeline.before_render` seam，仅 Assessment pilot 启用；该差异及回归证据已登记在 FACT。

后续允许调整：

- 具体类名；
- 文件位置；
- 参数形式；
- Adapter 实现细节；

但不得无记录改变：

- Four-Gate 主线；
- 两个 Pilot；
- 真实插入生命周期；
- opt-in 隔离；
- canonical source identity；
- task/legal control status 分离。
