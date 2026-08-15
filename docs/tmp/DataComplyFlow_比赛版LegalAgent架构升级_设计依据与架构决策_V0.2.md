# DataComplyFlow 比赛版 Legal Agent 架构升级——设计依据与架构决策 V0.2

> **Document Type**：Architecture Rationale / Architecture Decision  
> **Status**：REVIEW CANDIDATE  
> **Version**：V0.2  
> **Target**：比赛阶段增量式架构升级  
> **Primary Purpose**：解释为什么进行本轮 Legal Agent 架构升级、采用哪些外部思想、哪些能力保留、哪些机制新增，以及该升级如何形成真实、可执行、可用于比赛表达的技术主线  
> **Out of Scope**：Benchmark 指标体系、完整 Runtime 重构、11 模块全面迁移、具体代码文件命名

---

## 0. 文档定位、事实基线与证据规则

### 0.1 文档定位

DataComplyFlow 当前已经形成面向 CN / EU / US 三法域的 11 个正式业务模块，并具备 Rule Engine、LLM、RAG、Citation、Trace、Reporting、Artifact 等公共能力。

本轮不是重新建设一套 Legal AI 系统，而是在保持现有业务功能稳定的前提下，解决不同 Domain Workflow 对 Fact、Rule、Evidence、Citation 与自动化退出条件缺少统一控制语义的问题。

本轮架构目标冻结为：

> **不重写 Domain Workflow，而在现有 Workflow 之上增量增加轻量 Legal Agent Control Plane。**

该 Control Plane 统一回答：

1. 当前关键事实是否足够继续；
2. 确定性规则是否已经形成必须优先遵守的执行结果；
3. 当前证据与引用是否满足最低支持条件；
4. 自动化是否应继续、降级、澄清、人工复核或阻断。

### 0.2 当前事实基线

当前设计以 2026-08-13 后最新架构说明为主事实依据：

- 11 个正式业务模块；
- 4 个模块使用或部分使用公共 `WorkflowPipeline`；
- 7 个模块保持专用 Service / Workflow；
- `backend/common/reporting/` 已形成统一报告编排；
- `backend/harness/` 已独立承担 CLI 白盒执行职责；
- RAG / Knowledge 当前为 16 个逻辑索引；
- SourceRegistry 已存在 `review_status`、`can_be_cited`、`can_enter_external_report`、`allowed_usage` 等来源治理字段。

2026-08-04 Repository FACT 仅作为历史系统级补充。若与更新后的代码事实冲突，以更新后的事实为准。

### 0.3 证据等级

| 等级 | 来源 | 用途 |
|---|---|---|
| P0 | 当前源码、最新 FACT、真实 Trace | 判断系统当前是什么 |
| P1 | OpenAI / Anthropic / LangGraph 官方架构资料 | 判断当前 Agent Engineering 的主流工程思想 |
| P2 | 正式发表论文 | 判断法律 Agent 领域已被正式研究的问题 |
| P3 | 最新预印本 | 吸收快速发展的前沿设计思想 |
| P4 | DataComplyFlow 自身设计综合 | 将外部思想映射到当前系统后的架构决策 |

### 0.4 设计状态

- `PROPOSED`
- `DESIGNED`
- `IMPLEMENTING`
- `IMPLEMENTED`
- `VALIDATED`
- `ROLLED_OUT`

本文件中的 Control Plane 与 Gate 在开发完成前均属于 `DESIGNED`。

---

# 1. 当前系统真实架构

## 1.1 当前业务结构

当前正式业务模块为：

- CN：Transfer Diagnosis、Security Assessment、PIPIA、Document Review；
- EU：SCC Review、BCR Review、DPIA、TIA；
- US：EO 14117、EO 14117 Flow Review、CPRA。

当前并不存在“一套统一 Agent Workflow 驱动 11 个模块”的实现。

## 1.2 当前 Workflow 组织

当前真实组织更接近：

```text
11 Domain Modules
│
├── Shared WorkflowPipeline
│   ├── Assessment
│   ├── EO 14117
│   ├── EU SCC
│   └── CN Flow
│
└── Specialized Workflows / Services
    ├── Diagnosis
    ├── PIPIA
    ├── Document Review
    ├── BCR
    ├── DPIA
    ├── TIA
    └── CPRA
```

不同 Workflow 本身不构成本轮必须消除的问题。路径诊断、合同审查、影响评估和监管合规分析具有不同的专业拓扑，强制统一会产生大量 optional hook、空步骤和模块分支。

## 1.3 当前已经平台化的能力

当前已经存在较明确的公共能力：

```text
LLM Provider
RAG / Knowledge
Citation
Trace
Reporting
Artifact
Task / Ownership（部分）
CLI Harness
```

因此本轮原则不是“重新造平台”，而是“让现有公共能力进入统一法律执行控制协议”。

## 1.4 当前中间语义

当前已经真实存在：

```text
FactItem
IssueItem
EvidenceItem
GenerationContextPack
CitationItem
```

其中 Fact 已具有 provenance / confidence / evidence status，Evidence 已能够关联 Fact / Rule / Citation / Document。

本轮不认为系统“缺乏 Fact / Evidence”，真正缺少的是：

> **这些语义尚未成为跨 Workflow 的统一控制协议。**

## 1.5 当前架构核心判断

> **DataComplyFlow 已经实现业务模块化和部分公共能力平台化，但不同 Domain Workflow 对 Fact、Deterministic Rule、Retrieval、LLM、Evidence、Citation 与失败升级的执行控制仍未形成统一协议。**

---

# 2. 为什么需要本轮架构升级

## 2.1 不需要解决的问题：Workflow 差异

本轮不统一所有 Workflow，不将 Document Review、Diagnosis、Assessment 等强行压入同一个固定 DAG。

## 2.2 真正需要解决的问题：控制边界

需要统一回答：

### A. Fact

关键事实 UNKNOWN / AMBIGUOUS / CONFLICTED 时，系统是否还能输出强确定结论？

### B. Deterministic Rule

确定性 Rule Engine 已经形成明确结果后，概率性 LLM 是否还能静默改变该结果？

### C. Evidence / Citation

RAG 有命中、报告有引用，并不自动意味着证据足以支持当前法律 Claim。

### D. Escalation

自动化无法可靠处理时，是否应继续、降级、澄清、人工复核还是阻断？

这四类问题属于 **Control Problem**，而不是业务 Workflow 设计问题。

## 2.3 比赛阶段的现实约束

本轮必须同时满足：

```text
Architecture Innovation
+
Implementation Feasibility
+
Functional Stability
```

因此采用：

> **Incremental Overlay，而非 Runtime Rewrite。**

---

# 3. 外部思想来源及其项目映射

## 3.1 Agent Engineering / Harness

### 官方来源

- OpenAI Agents SDK：Agents、Guardrails、Tracing、Sessions、Human-in-the-loop 等被视为 Agent 执行的重要 primitives；
- Anthropic：强调 workflow 与 agent 的区分，并主张从最简单可行方案开始，仅在需要时增加复杂性；其 Agent Harness 讨论明确把外围系统视为模型能够稳定行动的重要组成；
- LangGraph：明确区分 framework / runtime / harness，强调 durable execution、streaming、persistence、human-in-the-loop。

### Adopted Insight

本项目不迁移上述框架，但吸收共同原则：

> **Agent 的可靠性不仅来自模型，还来自外围 state、guard、verification、trace 与 human-control。**

### Project Mapping

```text
Generic Agent Harness
↓
Legal-domain control requirements
↓
Legal Agent Control Plane
```

## 3.2 ContextLens → Fact Completeness

ContextLens 已正式发表于 ACL 2026 Long Papers。其核心价值是针对真实合规场景中的不完整、模糊上下文，显式识别 known / unknown / ambiguous / missing factor，而非在信息不充分时直接给出确定合规判断。

DataComplyFlow 不复现 ContextLens 全套框架，只吸收：

> **关键 Unknown 不得被后续启发式或 LLM 静默确定化。**

映射为：

> **Fact Completeness Gate**

## 3.3 GraphCompliance → 轻量 Rule–Fact Alignment

GraphCompliance 的启发在于把法律规则的主体、条件、约束和业务事实之间的结构关系显式化。

本轮只吸收：

> Rule 必须明确对应当前 Fact 条件。

不采用：

- 全平台 Policy Graph；
- Context Graph；
- Graph Database；
- GraphRAG 全面迁移。

## 3.4 LegalBench-RAG / RefWalk → Minimum Evidence Sufficiency

法律检索不仅要求“相关”，还要求精确定位及对完成当前法律判断真正必要的证据集合。

本轮吸收：

> **Retrieval Hit ≠ Sufficient Evidence**

并转化为：

> **Minimum Evidence Sufficiency Policy**

不声称首轮已经完整解决 citation closure / evidence-set closure。

## 3.5 LegalCiteTrust → Citation Validity

LegalCiteTrust 将 Citation Trustworthiness 拆为 Existence / Fidelity / Applicability。

本轮将其作为理论方向，但 V1 只承诺可以可靠落地的三项：

```text
Existence
Eligibility
Traceability
```

其中 Semantic Fidelity 和细粒度 Applicability 作为 V1.1 / 后续增强，不在首轮夸大实现程度。

## 3.6 LawThinker → Intermediate Verification

LawThinker 的核心启发是验证应进入推理过程，而非全部延迟到最终报告之后。

本轮不采用其 Explore–Verify–Memorize 完整 Agent 架构，只吸收：

> Evidence / Citation verification 应成为执行过程中的显式控制步骤。

---

# 4. 架构设计原则

## P1 — FACT First

设计不得覆盖真实代码事实。

## P2 — Incremental Overlay

优先 Adapter / Gate / opt-in Hook，不重写业务 Workflow。

## P3 — Domain Workflow Autonomy

不同法律任务保持不同 Workflow 拓扑。

## P4 — Deterministic Before Probabilistic

确定性 Rule 已形成有效执行结论时，后续 LLM 不得静默覆盖。

> 注意：这里的“优先”是 **Execution Precedence**，不是法规来源的 `authority_level` 或法律效力意义上的 Legal Source Authority。

## P5 — Evidence Before Strong Claim

证据不满足最低支持条件时，不允许输出超出当前 Evidence 的强法律结论。

## P6 — Explicit Uncertainty & Escalation

Unknown / Ambiguous / Conflict / Insufficient Evidence 必须显式表达。

## P7 — Reuse Before Rebuild

优先复用 Fact、Evidence、Citation、RAG、Trace、Reporting、Rule Engine。

## P8 — Pilot Isolation

Pilot 控制行为必须显式 opt-in，不得通过修改共享 Service / Workflow 默认语义而影响未迁移模块。

---

# 5. Target Architecture：Legal Agent Control Plane

## 5.1 定位

比赛叙事可以使用：

> **Legal Agent Harness**

工程责任定义为：

> **Legal Agent Control Plane**

它不是新的 Workflow Engine，也不是新的 Agent Runtime。

## 5.2 最小结构

```text
                    Existing Domain Workflow
                              │
                              ▼
                       Module Adapter
                              │
          ┌───────────────────┼──────────────────┐
          │                   │                  │
          ▼                   ▼                  ▼
    Fact Completeness   Deterministic      Evidence &
         Gate          Rule Precedence     Citation Gate
          │                   │                  │
          └───────────────────┼──────────────────┘
                              ▼
                       GateResult[]
                              │
                              ▼
                      Escalation Gate
                              │
                              ▼
                      ControlDecision
                              │
              ┌───────────────┼──────────────┐
              ▼               ▼              ▼
          Domain Result      Trace       Frontend Status
```

本轮不引入统一 `HarnessContext`。各模块通过 Adapter 把已有对象转化为 Gate 可消费的输入。

## 5.3 G1 — Fact Completeness Gate

处理：

```text
KNOWN
UNKNOWN
AMBIGUOUS
CONFLICTED
```

目标不是重做 Fact Pipeline，而是决定是否允许进入下一阶段。

## 5.4 G2 — Deterministic Rule Precedence Gate

处理的是 **Execution Precedence**：

```text
Deterministic Rule Result
↓
Precedence Check
↓
LLM may explain
but cannot silently reverse
```

该名称专门避免与法规来源 `authority_level / binding_force` 混淆。

## 5.5 G3 — Evidence & Citation Gate

V1 包含：

### Evidence

Minimum Evidence Sufficiency。

### Citation

- Existence
- Eligibility
- Traceability

首轮不宣称完整实现 Semantic Fidelity / Fine-grained Applicability。

## 5.6 G4 — Escalation Gate

统一输出：

```text
AUTO
CONDITIONAL
NEEDS_CLARIFICATION
NEEDS_REVIEW
BLOCKED
```

其中 `NEEDS_REVIEW` 在 V1 中仅表示 **Human Escalation State**，不声称已经实现完整可暂停、人工审批、恢复执行的 HITL Runtime。

## 5.7 Task Status 与 Legal Control Status 分离

严格区分：

```text
task_status
```

描述软件运行状态，例如 COMPLETED / FAILED。

```text
legal_control_status
```

描述法律结果的自动化可用程度，例如 AUTO / NEEDS_REVIEW。

允许：

```text
task_status = COMPLETED
legal_control_status = NEEDS_REVIEW
```

表示软件成功完成分析，但法律结果需要人工复核。

---

# 6. 统一什么、不统一什么

| 对象 | 决策 |
|---|---|
| GateResult | 统一 |
| ControlDecision | 统一 |
| legal_control_status | 统一 |
| Fact 基础状态 | 最小统一 |
| Evidence 最低支持状态 | 最小统一 |
| Citation Validity V1 | 统一 |
| Trace Control Event | 统一 |
| Module Adapter | 模块级 |
| Workflow topology | **不统一** |
| Rule Engine | **不统一** |
| Legal Source Authority | **不由 Rule Gate 改写** |
| Domain Finding | 部分统一 |
| Prompt | **不统一** |
| Domain Legal Rules | **不统一** |
| Task Runtime | 本轮不统一 |

核心原则：

> **统一执行控制，不统一专业业务语义。**

---

# 7. 技术评估与创新边界

## 7.1 Mainstream Alignment

**高。**

当前主流 Agent Engineering 已普遍强调 Guardrails、Tracing、Human-in-the-loop、State / Runtime 与 deterministic + probabilistic orchestration。

本项目不以“迁移某框架”证明先进性，而以架构思想对齐当前主流。

## 7.2 Legal Research Alignment

**高。**

本设计直接对应：

- incomplete context；
- rule–fact relevance；
- evidence sufficiency；
- citation validity；
- intermediate verification。

## 7.3 Project Fit

**很高。**

大部分底层能力已经存在，因此本轮主要增加控制契约与 Adapter，而不是新增完整技术栈。

## 7.4 Technical Differentiation

普通 RAG：

```text
Retrieve → Generate
```

本设计：

```text
Fact
→ Fact Gate
→ Deterministic Rule
→ Rule Precedence
→ Retrieval
→ Minimum Evidence Gate
→ LLM
→ Citation Validity
→ Escalation
→ Artifact
```

## 7.5 创新归属

### 非原创

- Harness；
- Guardrail；
- Trace；
- HITL；
- Unknown-aware compliance；
- citation closure；
- citation trustworthiness。

### DataComplyFlow 可合理强调的项目贡献

> **面向真实多法域数据合规任务，将通用 Agent Harness 的执行控制思想与法律任务中的 Fact、Deterministic Rule、Evidence、Citation 和 Escalation 要求结合，并在已有 Rule Engine + Legal RAG + Citation + Trace 系统上形成轻量、可增量接入的 Rule-Grounded、Evidence-Gated Legal Agent Control Plane。**

创新属于：

> **法律领域特化的系统架构综合与真实产品落地。**

## 7.6 技术裁决

> **建议实施，但限定为 Incremental Control Plane Pilot，不进行全面 Workflow / Runtime 重构。**

---

# 8. 对比赛故事线的影响

## 8.1 Before

DataComplyFlow 已经可以真实描述为：

> 多法域数据合规 Legal Agentic RAG Workbench，通过 Rule、LLM、RAG、Citation、Trace 与 Reporting 完成路径诊断、影响评估、文件审查和成果生成。

## 8.2 当前故事不足

仅讲：

```text
Rule + Multi-Agent + RAG
```

无法体现：

- 谁约束谁；
- 什么时候不能继续；
- 什么时候应该降级；
- 为什么系统比普通 RAG 更可信。

## 8.3 Upgrade

增加：

> **Legal Agent Control Plane**

后，故事从“能力组合”升级为“受控执行”。

## 8.4 After

> **DataComplyFlow 不仅组合确定性规则、法律 RAG 与大语言模型，而且通过 Legal Agent Control Plane 对事实完整性、确定性规则执行优先级、最低证据支持、Citation 有效性和异常升级进行分阶段约束，使系统在信息不足时主动澄清，在确定性规则明确时禁止 LLM 静默反转，在证据不足时降低结论强度，并在自动化无法可靠处理时升级人工复核。**

## 8.5 四个核心展示行为

1. 事实不足 → 主动澄清；
2. Rule 明确 → LLM 不得静默反转；
3. Evidence / Citation 不足 → 降级输出；
4. 无法可靠自动处理 → `NEEDS_REVIEW` / `BLOCKED`。

---

# 9. 实施范围与 Non-goals

## 9.1 Pilot A — CN Transfer Diagnosis

首轮：

```text
Fact Completeness
+
Deterministic Rule Precedence
+
Escalation
```

但必须满足：

> **Diagnosis Control 必须 opt-in，不能因为 Assessment 内部复用 DiagnosisService 而改变 Assessment 当前默认行为。**

## 9.2 Pilot B — CN Security Assessment

首轮：

```text
Minimum Evidence Sufficiency
+
Citation Validity V1
+
Escalation
```

必须通过 Assessment-specific hook / adapter 接入，不允许修改公共 `WorkflowPipeline` 的默认行为而影响 EO 14117、EU SCC、CN Flow。

## 9.3 Non-goals

本轮不实施：

- 11 模块全面迁移；
- One Giant Workflow；
- Full Policy Graph；
- Task Runtime 重写；
- 新 Agent Framework 迁移；
- Retriever / Embedding 全量替换；
- 完整 Citation E/F/A Semantic Judge；
- 完整 Evidence Closure；
- 完整 HITL Runtime；
- 新 Claim IR；
- 新 HarnessContext；
- Reporting 重写；
- CLI `backend/harness/` 重定义。

---

# Appendix A — Source Ledger

| 来源 | 类型 | 采用内容 | 首轮明确不采用 |
|---|---|---|---|
| DataComplyFlow 最新 FACT | P0 | 当前真实架构与插入基础 | — |
| OpenAI Agents SDK 官方文档 | P1 | Guardrail / Trace / HITL primitives | 不迁移 SDK |
| Anthropic Agent / Harness Engineering | P1 | Harness、复杂度控制、workflow/agent distinction | 不照搬 Claude Agent SDK |
| LangGraph 官方文档 | P1 | runtime / harness distinction、HITL、durability | 不迁移 Runtime |
| ContextLens, ACL 2026 | P2 | incomplete / ambiguous / unknown context | 不复现完整框架 |
| LegalAgentBench, ACL 2025 | P2 | process-aware Legal Agent | Benchmark 不属于本轮 |
| RefWalk, 2026 | P3 | evidence-set closure / per-rule attribution | 不建设完整 OKG |
| LegalCiteTrust, 2026 | P3 | Citation Existence / Fidelity / Applicability | V1 不完整实现 E/F/A |
| LawThinker, 2026 | P3 | intermediate verification | 不采用完整 E-V-M Agent |

# Appendix B — Architecture Decisions

| ID | Decision |
|---|---|
| D01 | 不统一 11 个 Domain Workflow |
| D02 | 新增轻量 Legal Agent Control Plane |
| D03 | 采用 4 Gate 最小设计 |
| D04 | Rule Gate 正式命名为 Deterministic Rule Precedence Gate |
| D05 | Legal Source Authority 与 Execution Precedence 严格分离 |
| D06 | 删除首轮 HarnessContext |
| D07 | 引入统一 GateResult + ControlDecision |
| D08 | Citation V1 仅承诺 Existence / Eligibility / Traceability |
| D09 | NEEDS_REVIEW 定义为 Escalation State，不夸大为完整 HITL |
| D10 | task_status 与 legal_control_status 分离 |
| D11 | Diagnosis / Assessment Pilot 必须 opt-in 隔离 |
| D12 | 复用当前 Fact / Evidence / Citation / Trace |
| D13 | 不引入新 Agent Framework 作为本轮前提 |
| D14 | 实现完成后必须重新生成 FACT |

## 当前总裁决

本轮比赛版架构优化最终冻结为：

> **Existing Domain Workflow + Module Adapter + Four Legal Control Gates + GateResult / ControlDecision**

而不是：

> 新 Workflow Runtime / 新 Agent Graph / 新统一 Context。

这使设计在保持技术创新叙事的同时，将代码影响面压缩到比赛阶段可接受范围。
