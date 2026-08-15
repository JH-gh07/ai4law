# DataComplyFlow Legal Agent 架构升级：开发事实与可行性审查 V0.1

## 0. 审查说明与 HEAD 信息

### 0.1 审查对象

- WHY：`docs/tmp/DataComplyFlow_比赛版LegalAgent架构升级_设计依据与架构决策_V0.2.md`
- HOW：`docs/tmp/DataComplyFlow_比赛版LegalAgent架构升级_实施设计与开发说明_V0.2.md`
- 事实优先级：当前源码 HEAD 高于上述设计文档、历史 FACT、README 和历史讨论。
- 审查范围：Fact、Feasibility、Insertion Point、Regression Risk、Minimum Change。
- 本轮未修改任何业务代码或架构代码，仅新增本审查文档。

### 0.2 HEAD 与工作区

| Item | Value |
|---|---|
| Branch | `new` |
| HEAD | `2b9f5d16e397cf760216a4b6f8cc90d884a96dbc` |
| Short HEAD | `2b9f5d16` |
| Commit time | `2026-08-15 04:04:19 +0800` |
| Commit subject | `docs(status): task071 补充子方案B 接入 seed-cases-v1/inputs 取代现有前端案例` |
| Review date | `2026-08-15` |
| Worktree | DIRTY：审查开始时 78 项（72 modified，6 untracked） |

工作区的相关业务后端文件未显示未提交修改；`frontend/src/components/workspace/ModuleRunPanel.tsx` 有未提交修改，因此涉及该文件的判断额外以 `git show HEAD:frontend/src/components/workspace/ModuleRunPanel.tsx` 复核。两份 V0.2 输入文档位于未跟踪的 `docs/tmp/`，这是本次审查输入，不作为 HEAD 代码事实。

### 0.3 验证

执行了以下无副作用聚焦测试：

```text
pytest -q \
  backend/core/tests/test_module_registry.py \
  backend/common/workflow/tests/test_pipeline.py \
  backend/common/trace/tests \
  backend/domains/cn/transfer_diagnosis/tests \
  backend/domains/cn/security_assessment/tests/test_evidence_builder.py \
  backend/domains/cn/security_assessment/tests/test_citation_builder.py \
  backend/domains/cn/security_assessment/tests/test_consistency_checker.py \
  backend/domains/cn/security_assessment/tests/test_legal_grounding.py
```

结果：`68 passed in 1.54s`。

# 1. 总体审查结论

## 1.1 架构主线

冻结主线成立：

```text
Existing Domain Workflow
        +
Module Adapter
        +
Four Legal Control Gates
        +
GateResult / ControlDecision
```

当前代码确实具备可复用的 Domain Service、确定性 Rule Engine、Fact/Issue/Evidence、RAG、Citation、Trace 和 Reporting。两个 Pilot 都能以增量方式接入，不需要 Runtime 重构、统一全部 Workflow 或迁移 Agent Framework。

## 1.2 是否可以进入实现

可以，但不能直接按 V0.2 HOW 开发。必须先修订 V0.3 Final Design 的代码映射、字段契约和插入点，再进入实现。

## 1.3 最大风险

最高工程风险是 **Assessment Citation Validity V1 的 SourceRegistry Eligibility 闭环**：

1. 本地 multi-index 链有稳定 `source_id`；
2. fallback 和 per-issue DeliLegal 链不保证该 ID 是 SourceRegistry ID；
3. `RegulationHit` 丢弃大部分来源治理字段；
4. `CitationItem` 没有 `review_status` 和 `can_be_cited`；
5. Assessment 的 citation builder 会按 title/source kind 重新推断治理属性，而不是从 SourceRegistry 读取；
6. 当前 Citation 去重逻辑可能不完整合并 issue/fact/evidence 关联。

因此，V1 的 Existence 可以低成本实现，Eligibility 和 Traceability 需要先收紧 source identity 与关联传播，不能仅凭现有 `CitationItem` 字段宣称完成。

## 1.4 对 V0.2 的总体判断

V0.2 WHY 的架构方向基本成立；V0.2 HOW 存在多项实现级事实错误：

- 将不存在的 `EvidenceItem.citation_refs/status/strength` 当成现有字段；
- 将 Evidence Gate 放在无法取得最终 legal grounding / CitationRegistry 的位置；
- 未区分本地稳定 `source_id` 与外部/fallback synthetic ID；
- 将 SourceRegistry 已有能力等同于 Assessment Citation 链已可直接消费；
- 未准确描述 Diagnosis 默认 RuleMatch 后仍可能进入 AI inference；
- 将“4 个 WorkflowPipeline 使用者”写成 4 个直接实现，实际是 3 个直接实例加 1 个委托入口。

# 2. 当前代码事实校正

## 2.1 与 V0.2 一致的事实

1. `config/module_registry.json` 注册 11 个正式模块；`backend/core/tests/test_module_registry.py::test_registry_has_unique_stable_ids_and_frontend_keys` 明确断言数量为 11。
2. `cn.transfer_diagnosis` 的正式 API 入口是 `backend/domains/cn/transfer_diagnosis/router.py` 的 `/api/v1/diagnosis/evaluate` 与 `/api/v1/diagnosis/report`，核心调用为 `DiagnosisService.evaluate()`。
3. `cn.security_assessment` 的正式 API 入口是 `backend/domains/cn/security_assessment/router.py` 的 `/api/v1/assessment/generate`、`generate_async` 和任务查询，核心调用为 `AssessmentService.generate_report()`。
4. Assessment 确实复用 `DiagnosisService`，且复用发生在共享 Pipeline 的 `evaluate_diagnosis` callback。
5. Assessment 的真实主流程包含 Facts、Issues、Evidence、per-issue RAG、ContextPack、Chapters、Consistency、Alignment、Repair、Render。
6. SourceRegistry 定义了 `review_status/can_be_cited/can_enter_external_report/allowed_usage/authority_level/binding_force`。
7. `TraceRecorder` 支持任意名称的文件事件和任意字典 payload，前端实时事件统一通过标准 `RunEvent.event_type` 消费。
8. `task_status/state` 与拟新增的法律控制状态在语义上应分离。

## 2.2 需要修正的事实

1. 生产代码只有 3 个直接 `WorkflowPipeline(...)` 实例：Assessment、EU SCC、US EO 14117。历史 `cn_flow` 入口通过 `CNFlowService.canonical_service` 委托 US EO 14117，因此可说“4 个产品入口会直接或间接经过 Pipeline”，不能说 4 个独立模块各自构建 Pipeline。
2. Diagnosis 不存在独立、统一的“missing check 返回对象”。`_resolve_answers()` 返回 `(DiagnosisAnswers, dict[str, FactSource], list[str])`；missing 只是字符串列表，随后可被 Agent 结果移除。
3. Diagnosis 在 Rule Engine 之前有 ImportantData、PIClassify、Exemption Agent；前两个可把 UNKNOWN 改成 yes/no。Rule Engine 返回 default 后还可能调用 `_build_ai_inference_result()` 并生成新的路径性结果。
4. `EvidenceItem` 没有 `citation_refs`、`status`、`strength`。实际字段是 `legal_basis/supporting_basis/discarded_basis/confidence` 等。
5. Assessment 当前 `EvidenceItem.document_refs` 实际难以填充：Fact builder 写入的是字符串 `supporting_material_refs`，Evidence builder 的 `_extract_document_refs()` 却不处理字符串分支，当前正常构造链中通常为空。
6. `CitationMap` 存在，但由 renderer 在输出阶段写入；正式渲染前的 Gate 不能依赖尚未产生的文件，应使用内存 `CitationRegistry`。
7. SourceRegistry 治理字段在 KnowledgeChunk 层部分传播，但并未完整进入 `RegulationHit` 和 `CitationItem`。
8. 当前 consistency/alignment/repair 只覆盖部分结构一致性和表达约束，不等价于 Evidence Sufficiency 或 Citation Eligibility Gate。

## 2.3 新发现的重要共享调用关系

| Shared relationship | Code evidence | Impact |
|---|---|---|
| Assessment → Diagnosis | `AssessmentService.__init__()`、`_evaluate_diagnosis()` | Diagnosis 默认语义改变会跨 Pilot 回归 |
| V0 Task Gateway → AssessmentService | `backend/api/v0/task_gateway/service.py` | Assessment result 字段可向下兼容，但 V0 status/audit 不会自动展示控制状态 |
| Harness → 两个 Pilot Service | `backend/harness/runner.py` | opt-in 参数必须有默认值；Harness 是否启用 Pilot 要显式决定 |
| CN Flow → US14117Service → WorkflowPipeline | `backend/domains/us/eo14117_flow_review/service.py` | Pipeline 变更会间接影响历史兼容入口 |
| Citation pipeline 为公共能力 | `backend/common/llm/postprocess.py` | 不应为 Assessment 修改公共默认 citation policy |
| Source governance 经 KnowledgeChunk 传播 | `builders_v2.py`、`usage_policy.py` | 可复用，但不能假设 Citation 已携带全部治理字段 |
| Module-level singleton services | 两个 Pilot router 的 `service = ...Service()` | 禁止在 Service 实例上保存每次运行的可变 ControlDecision；异步并发会串状态 |

# 3. Q1-Q14 逐项回答

## Q1 Diagnosis missing / conflict check 的真实返回对象和调用位置是什么？

**Missing：**

- `DiagnosisService.evaluate()` 首行调用 `_resolve_answers()`。
- `_resolve_answers()` 位于 `backend/domains/cn/transfer_diagnosis/service.py:230`，返回：
  `tuple[DiagnosisAnswers, dict[str, FactSource], list[str]]`。
- 第三个返回值 `missing_facts` 只检查 `q1/q2/q5` 是否仍为 `unknown`，不是独立 Pydantic result。
- ImportantData/PIClassify Agent 可在 `evaluate()` 内把 q2/q5 改写并从 `missing_facts` 删除。
- `facts_from_module()` 将该列表写入 `DiagnosisFacts.missing_facts`；最终 `_attach_fact_metadata()` 再复制到 `DiagnosisResult.missing_facts`。

**Conflict：**

- `_validate_fact_consistency()` 位于同文件约 `:353`，返回 `DiagnosisResult | None`。
- 调用点在 Agent 辅助和 `facts_from_module()` 之后、Rule Engine 之前（约 `:121`）。
- 冲突时直接返回 `recommended_path="manual_review"`、`conclusion_source="validation"`、`requires_human_review=True` 的 `DiagnosisResult`。
- `DiagnosisRuleEngine.evaluate()` 另有 `conflicting_facts` RuleMatch，但当前同类 q5 冲突通常已被 service validation 提前截获。

结论：V0.3 不应描述为一个既有的统一 missing/conflict result；应描述为“missing list + conflict DiagnosisResult”。

## Q2 Assessment 调用 DiagnosisService 的真实入口、参数和调用目的是什么？

调用链：

```text
AssessmentService.generate_report(payload)
→ AssessmentService._build_pipeline().run(...)
→ WorkflowPipeline.run()
→ self.evaluate_diagnosis(payload)
→ AssessmentService._evaluate_diagnosis(payload)
→ self.diagnosis_service.evaluate(self._to_diagnosis_answers(payload))
```

- 入口：`AssessmentService._evaluate_diagnosis(payload: AssessmentRequest)`。
- 参数：通过 `_to_diagnosis_answers()` 将 `AssessmentRequest` 转为完整 `DiagnosisAnswers`；没有传 `trace`，也没有 control flag。
- 目的：得到 `recommended_path/rationale/risk_level/matched_rule_id`，供 path validation、Fact/Issue 构造、风险单一来源和报告生成使用。

## Q3 如何保证 Diagnosis Pilot 的 Control Gate 不改变 Assessment 内部复用 DiagnosisService 的默认行为？

推荐在 `DiagnosisService.evaluate()` 增加默认关闭的显式注入点，例如 `control_hook=None`，或新增显式 `evaluate_with_controls()` 入口并共享内部准备逻辑。正式 Diagnosis API/Harness Pilot 显式启用；Assessment 的 `_evaluate_diagnosis()` 保持现有 `evaluate(answers)` 调用。

关键约束：

- 不在 `DiagnosisService.__init__()` 上设置可变全局开关；router service 是单例，可能并发。
- 不改变 `evaluate()` 默认返回路径、Agent 行为或缺失处理。
- 增加 Assessment 回归测试，断言其调用未传 control，并保持原 DiagnosisResult。

最佳 Gate seam 不是 API 外层二次解析，而是 service 内 Agent 辅助完成、`DiagnosisFacts` 已形成、Rule Engine 尚未执行的位置。

## Q4 Diagnosis Rule Engine 之后是否存在任何 LLM / Agent 步骤可能改写路径性法律结论？

**存在，但只发生在 default RuleMatch 分支。**

真实分支：

```text
rule_match = DiagnosisRuleEngine.evaluate(facts)
├─ non-default → _build_rule_result()
│                → LLM _build_rule_explanation() 仅写 final_explanation
│                → recommended_path 不被改写
└─ default → _needs_ai_inference()
             → _build_ai_inference_result()
             → LLM 可返回 recommended_path
```

因此：

- 对 **non-default deterministic match**，Rule Precedence V1 只需显式 precedence 标识、Trace 和字段不覆盖保证，不需要新 LLM Judge。
- 对 **default match**，不能标记为已锁定的 deterministic conclusion；当前代码允许后续 AI inference 形成路径结果，应标记为非 precedence-lock，并由 Fact/Escalation Gate 处理不确定性。
- Rule 前的 ImportantData/PIClassify Agent 还可能改变用于规则匹配的事实，这不属于“Rule 后覆盖”，但必须进入 provenance 和 Escalation 判断。

## Q5 Assessment 中 build_evidence、retrieve_per_issue、build_context_pack 的真实顺序、调用对象和参数是什么？

顺序固定在 `backend/common/workflow/pipeline.py:91-120`：

```text
issues, evidence_chain = build_evidence(facts, issues, regulations, diagnosis)
per_issue_rag = retrieve_per_issue(
    issues=issues,
    profile=profile,
    regulations=regulations,
)
context_pack = build_context_pack(
    task_id=task_id,
    diagnosis=diagnosis,
    facts=facts,
    regulations=regulations,
    issues=issues,
    evidence_chain=evidence_chain,
    path_warning=path_warning,
    attachment_notes=attachment_notes,
    per_issue_rag=per_issue_rag,
)
```

Assessment 绑定对象分别是：

- `build_assessment_evidence`
- `AssessmentService._retrieve_per_issue`
- `AssessmentService._build_context_pack`

`_build_context_pack()` 内才构造 `legal_grounding/case_grounding` 和 `CitationRegistry`。因此 V0.2 所画的 Evidence Gate 位于 `per_issue_rag` 与 `build_context_pack` 之间时，尚拿不到最终 grounding 和 registry。

## Q6 EvidenceItem 当前各字段在运行时的实际填充情况如何？

| Field | Schema | Assessment runtime | Classification |
|---|---|---|---|
| `claim` | 存在、required | `_EVIDENCE_WORDING` 或 issue title，始终填充 | Schema 存在且实际使用 |
| `fact_refs` | 存在 | 从 issue 过滤有效 fact ID；没有有效 fact 的 issue 不创建 Evidence | Schema 存在且实际使用 |
| `rule_refs` | 存在 | issue refs、前 3 个 regulation source IDs 或 diagnosis ref；材料类 issue 可为空 | Schema 存在且实际使用，但可为空 |
| `citation_refs` | 不存在 | 无 | 当前根本不存在 |
| `document_refs` | 存在 | builder 尝试填；但 Fact 侧给字符串，extractor 不处理字符串，正常链通常为空 | Schema 存在但当前通常为空 |
| `status` | 不存在 | 无 | 当前根本不存在 |
| `strength` | 不存在 | 无；近似概念是 `confidence` 和 CitationBinding.support_level | 当前根本不存在 |
| `confidence` | 存在 | 根据 issue severity / rule refs 计算并填充 | Schema 存在且实际使用 |
| `legal_basis` | 存在 | 对所有 regulations 构造 bindings；无检索命中时为空 | Schema 存在且实际使用 |
| `supporting_basis` | 存在 | Assessment builder 未填 | Schema 存在但常为空 |
| `discarded_basis` | 存在 | Assessment builder 未填 | Schema 存在但常为空 |
| `issue_refs` | 存在 | Assessment builder 未填 | Schema 存在但常为空 |
| `used_by` | 存在 | 填 issue ID 和受影响章节 | Schema 存在且实际使用 |
| `rag_query_used/rag_hits_count` | 存在 | 当前 builder 填全局 retrieval 信息，不是 per-issue RAG 结果 | Schema 存在且实际使用，但语义有限 |

V0.3 必须用真实字段制定 V1 规则；若确需 `status/strength`，应明确列为 additive extension，而不能写成 REUSE。

## Q7 CitationItem / Retrieval Hit 与 SourceRegistry 当前的稳定 Join Key 是什么？

**局部存在，端到端不完全稳定。**

- `SourceRegistryEntry.source_id`、`KnowledgeChunkV2.source_id`、`RegulationHit.source_id`、`CitationItem.source_id` 具备同名连接键。
- 本地 multi-index 路径由 `builders_v2.py` 从 SourceRegistry 构造 KnowledgeChunk，`AssessmentRetriever.search()` 保留 `chunk.source_id`，local citation 通常可稳定连接。
- single-index/enriched fallback 的 `source_id` 来自 `RegulationDoc.id`，不保证是 SourceRegistry ID。
- per-issue DeliLegal binding 使用 `delilegal-law-<title>` / `delilegal-case-<title>` synthetic ID，不能连接 SourceRegistry。
- `backend/common/citation/output.py` 存在 title 模糊补救，但该逻辑只适合兼容输出，不可作为本 Gate 的正式 Join。

最小、安全方案：

1. 将现有 `source_id` 明确定义为“已治理来源的 canonical SourceRegistry ID”。
2. Gate 通过 `registry_by_source_id` 做 exact membership lookup。
3. 外部/fallback 候选若未提供 canonical ID，标记 `UNREGISTERED/NOT_TRACEABLE`，不得靠 title 模糊通过 Eligibility。
4. 需要纳入正式引用的外部来源先创建 SourceRegistry entry，再把 canonical ID 传入 binding/CitationItem。
5. 若必须同时保留 provider ID，仅 additive 增加 `external_source_id` 或 `registry_source_id`，不要复用 title。

## Q8 现有 consistency / alignment / repair 是否已经检查四类问题？

| Concern | Current coverage | Code evidence | Conclusion |
|---|---|---|---|
| unsupported claim | 检查 HIGH/BLOCKER issue 是否出现、材料缺失却声称齐备、user_claim_only 附近的强正面表述 | `consistency_checker.py` | PARTIAL |
| citation mismatch | 生成时 registry 无法解析 marker 会变成“待核验”；一致性检查只看 chapter.citations 是否为空、案例是否泄漏；pipeline violations 未进入 consistency result | `common/llm/postprocess.py`、`consistency_checker.py` | PARTIAL，不是 Gate |
| rule/output conflict | 检查非 assessment path 的强制草案说明、风险等级和 CN 事实文本对齐 | `check_report_against_context()`、`check_cn_alignment()` | PARTIAL |
| evidence inconsistency | 检查 issue/evidence 的 fact/rule/evidence 引用是否悬空 | `check_context_pack_consistency()` | PARTIAL，仅结构引用 |

当前没有：SourceRegistry Eligibility、citation-to-current-issue/fact/evidence 完整性、冲突 Evidence 状态、minimum evidence set、完整 unsupported-claim closure。新 Gate 应复用现有 checker 的结果，但不能把它们等同于完整 Gate。

## Q9 TraceRecorder 是否支持自定义 event / metadata？新增 control.* 的成本如何？

- `TraceRecorder.record(name, payload)` 接受任意 name 和任意 `dict[str, Any]`。
- payload 没有名为 `metadata` 的固定 schema，但 `detail` 可承载任意结构；落盘事件文件保留完整 payload。
- manifest 只保存 `seq/name/path/created_at`，详情在对应 JSON 文件。
- 未知 name 的 SSE `event_type` 默认映射为 `status`。

新增 5 个 `control.*` 事件的后端记录成本为 LOW。若只要求“可见”，无需扩展 `RunEvent.EventType`；若要求前端呈现为 Legal Control 语义，需要补 `_NAME_TO_EVENT_TYPE` 和 `trace-adapter.ts` 的 `raw_name` 映射，成本仍为 LOW。

## Q10 当前 API Response 最适合在哪一层 additive 增加控制字段？

**Diagnosis：** 增加在 domain `DiagnosisResult`：

- `legal_control_status`
- `control_reasons`
- `required_actions`
- `clarification_questions`
- 可选 `gate_results`

这样 `/diagnosis/evaluate` 直接返回，`DiagnosisReportResponse.result` 自动携带；不要加到任务状态。

**Assessment：** 增加在 domain `AssessmentResult`。同步接口直接返回；异步接口在 `AssessmentAsyncStatus.result` 完成后携带。不要加到 `AssessmentAsyncAccepted.state` 或 `AssessmentAsyncStatus.state` 顶层。

字段应给向后兼容默认值。OpenAPI types 需要重新生成。V0 Task Gateway 的 status 只表达执行生命周期；若比赛入口使用 V0 audit，需另行 additive 暴露，但仍不得改写 `status`。

## Q11 当前前端 RunTranscript / TraceNodeView 是否能够直接展示新增 control event？

能展示，但默认只会显示为通用 Task 节点：

- recorder 将未知 `control.*` 映射为 `status`；
- `raw_name` 和其他 detail 会被前端保留；
- `TraceNodeView` 可显示 action、description、detail、input/output。

最低成本兼容方式：

1. 后端把 pass 类映射为 `intermediate`、review/block 类映射为 `warning`，或统一保持标准 event type；
2. `trace-adapter.ts::semanticFromDetail()` 识别 `/^control\./` 的 `raw_name`，映射到 Review stage 和明确 action/badge；
3. 不新增 `RunEvent.event_type="control"`，避免同步修改后端 Literal、SSE、前端联合类型及测试。

## Q12 Assessment Evidence Gate 若采用 WorkflowPipeline optional hook，会影响哪些共享调用方、类型签名和测试？

直接共享调用方：

- `AssessmentService._build_pipeline()`
- `EU_SCCService._build_pipeline()`
- `US14117Service._build_pipeline()`
- `backend/common/workflow/tests/test_pipeline.py`

间接入口：`CNFlowService` 委托 `US14117Service`。

影响包括：`WorkflowPipeline.__init__` callback 类型、`run()` 顺序、`WorkflowRunResult` 是否携带 gate results、Trace 事件顺序测试、三模块 service tests。

推荐最低风险方案不是先改公共 Pipeline，而是：

- Assessment `_build_context_pack()` 构造 per-run context 后执行 Evidence adapter，并把结果放入 additive context field；
- Assessment `_render_outputs()` 在最终 chapters/repair 后执行 Citation + Escalation adapter；
- 使用 per-run context 传递结果，禁止保存到 singleton service 成员。

只有当后续第二个直接 Pipeline 模块也需要相同 seam 时，再升级为默认 `None` 的公共 optional hook。

## Q13 SourceRegistry 的治理字段是否能从当前 Citation / Evidence 链稳定查询？

**不能完整稳定查询。**

| Field | Produced | Current Assessment consumption |
|---|---|---|
| `review_status` | SourceRegistry builder | 未进入 KnowledgeChunk/CitationItem；不能从 Citation 查询 |
| `can_be_cited` | Registry → KnowledgeChunk | Retrieval filter 和 legal grounding 使用；CitationItem 不保存 |
| `can_enter_external_report` | Registry → KnowledgeChunk | chunk 层可用，但 legal grounding/citation builder 按 source kind 重算，非稳定直传 |
| `allowed_usage` | Registry → KnowledgeChunk | chunk 层可用；Assessment binding/citation 可能被重算 |
| `authority_level` | Registry → KnowledgeChunk | grounding 可读；Citation builder 又按 title 推断 |
| `binding_force` | Registry → KnowledgeChunk | grounding 可读；Citation builder 又按 title 推断 |

结论：只有通过 canonical `source_id` 回查 SourceRegistry 才能获得权威 Eligibility；不得把 CitationItem 上的推断字段当作 SourceRegistry 审核事实。

## Q14 是否存在尚未识别的共享关系，可能造成跨模块回归？

存在：

1. `V0TaskGatewayService` 内部持有 AssessmentService。
2. Harness 直接实例化两个 Pilot Service；no-LLM Assessment 还替换其 diagnosis service。
3. `CNFlowService` 间接复用 US14117 的 Pipeline。
4. 公共 `apply_citation_pipeline()` 被 Assessment、EU SCC、DPIA、TIA、CPRA 等使用。
5. SourceRegistry/Knowledge builders/UsagePolicyFilter 是多模块共享公共层。
6. `GenerationContextPack`、`EvidenceItem`、`CitationItem` 是跨模块共享类型；增加 required 字段会造成广泛回归，必须 additive + default。
7. router 使用 singleton service；Control 结果不得保存在实例字段。
8. `CitationMap` writer 是公共单一输出契约，Assessment Gate 不应绕过或另写第二套 map。

# 4. G1 Fact Completeness Gate 审查

## 1. Current Code Fact

Diagnosis 的事实准备不是单纯 normalization：`_resolve_answers()` 会用结构化问卷规则补值/估算，随后 ImportantData 和 PIClassify Agent 还可把 UNKNOWN 改成 yes/no；最终产生 `DiagnosisFacts`、`missing_facts` 和 provenance。冲突检查在 Rule Engine 前直接返回 manual review。

## 2. 与 V0.2 设计是否一致

**PARTIALLY CONSISTENT**

已有 missing、provenance、conflict 与 human-review 信号可复用，但它们不是统一返回对象，且 V0.2 的 API boundary Adapter 无法在不重复/偏离 service 逻辑的情况下获得 Agent 后最终事实状态。

## 3. 最佳插入位置

`DiagnosisService.evaluate()` 内：Agent 辅助与 `facts_from_module()` 之后、Rule Engine 之前，即现有 `_validate_fact_consistency()` 周围（约 `service.py:115-139`）。

## 4. 推荐实现方式

**optional hook + ADAPTER + extend existing object**

默认关闭的 fact-control hook 消费最终 `DiagnosisFacts`、missing list、provenance 和 conflict result；正式 Diagnosis Pilot 显式启用。

## 5. 最小新增代码

- 公共 `GateResult/ControlDecision` 小契约；
- Diagnosis Fact Gate adapter；
- 默认关闭的 service seam；
- `DiagnosisResult` additive control fields；
- predefined clarification mapping；
- Trace event 和聚焦测试。

## 6. 可直接复用代码

`_resolve_answers()`、`facts_from_module()`、`DiagnosisFacts.missing_facts/field_provenance`、`_validate_fact_consistency()`、`DiagnosisResult.requires_human_review/uncertainty_notes`。

## 7. Regression Scope

Diagnosis evaluate/report API、Assessment 内部复用、Harness diagnosis、Assessment tests、报告 renderer。

## 8. Risk

**MEDIUM**

风险来自 Gate 必须位于 service 内部真实生命周期，并需正确区分 USER/RULE/LLM_INFERENCE/ESTIMATE/DEFAULT，而不是 Gate 逻辑本身复杂。

## 9. 对 V0.2 HOW 需要修正什么

- 删除“优先在 API boundary 直接消费 normalized facts”的笼统建议；
- 明确 missing 是 list、conflict 是 `DiagnosisResult | None`；
- 明确 Agent 会在 Gate 前改变 unknown；
- 定义 inferred decisive facts 对应 `NEEDS_REVIEW`，而不是误判为完整事实 PASS；
- 将插入点落到 `evaluate()` 内 Agent 后、Rule 前。

## 10. 是否建议进入首轮实现

**YES_WITH_CHANGES**

# 5. G2 Deterministic Rule Precedence Gate 审查

## 1. Current Code Fact

`DiagnosisRuleEngine` 是纯确定性。non-default match 后，`_build_rule_result()` 固定 `recommended_path`，LLM 只生成 `final_explanation`。但 default match 后可进入 `_build_ai_inference_result()` 并由 LLM 产生路径结果。

## 2. 与 V0.2 设计是否一致

**PARTIALLY CONSISTENT**

V0.2 对 non-default rule 的判断正确；对 default 分支描述不完整。

## 3. 最佳插入位置

`rule_match = self._rule_engine.evaluate(facts)` 之后，按 `rule_match.is_default` 分支：non-default 在 `_build_rule_result()` 后写 precedence；default 不加 lock，进入 inference/escalation。

## 4. 推荐实现方式

**ADAPTER + extend existing object**

不修改 Rule Engine，不引入冲突 Judge。Adapter 从 `RuleMatch` 和最终 `DiagnosisResult` 生成 precedence GateResult。

## 5. 最小新增代码

- RuleMatch→GateResult adapter；
- `execution_precedence=true/false` details；
- non-default result invariant test；
- `control.rule_precedence` Trace。

## 6. 可直接复用代码

`RuleMatch.rule_id/path/legal_basis/is_default/condition_fields`、`DiagnosisResult.matched_rule_id/conclusion_source`、现有 `_build_rule_explanation()` 的“只解释不改判”边界。

## 7. Regression Scope

Diagnosis、Assessment path validation、Assessment Fact/Issue/risk generation。

## 8. Risk

**LOW**

前提是只锁 non-default deterministic match，不把 default 当作确定性法律结论。

## 9. 对 V0.2 HOW 需要修正什么

- 明确 Rule 后存在 default→AI inference；
- precedence 只表示系统执行优先级，不等于 `authority_level/binding_force`；
- 对 non-default 只做标识、Trace 和字段 invariant；
- default 进入 CONDITIONAL/NEEDS_REVIEW 逻辑，不标 precedence PASS。

## 10. 是否建议进入首轮实现

**YES_WITH_CHANGES**

# 6. G3 Evidence & Citation Gate 审查

## 6.A Minimum Evidence Sufficiency V1

### 1. Current Code Fact

Assessment 在 ContextPack 前创建 EvidenceItem。Evidence 具备 claim/fact/rule/legal basis/document/confidence，但没有 V0.2 所称 status/strength/citation_refs。per-issue RAG 不回写 EvidenceItem；最终 issue-level grounding 和 CitationRegistry 在 `_build_context_pack()` 内才形成。

### 2. 与 V0.2 设计是否一致

**INCONSISTENT**

“已有 Evidence Pipeline 可复用”成立，但 V1 输入字段和插入点与真实代码不一致。

### 3. 最佳插入位置

`AssessmentService._build_context_pack()` 完成 legal_grounding、case_grounding、CitationRegistry 和 GenerationContextPack 构造后、该 pack 返回给 `generate_chapters()` 之前。

这是“ContextPack 已构造但尚未被生成器消费”的真实 seam。

### 4. 推荐实现方式

**ADAPTER + extend existing object**

Assessment-specific Evidence adapter；GateResult 存入 per-run ContextPack 的 additive control field。首轮不必改公共 Pipeline。

### 5. 最小新增代码

- 基于真实字段的 Evidence policy；
- ContextPack additive `control_results` 或等价 per-run carrier；
- 对 core Issue 的 fact refs、rule/legal basis、document support 做最小判断；
- Trace 和 tests。

### 6. 可直接复用代码

`IssueItem.fact_refs/rule_refs/evidence_refs/severity`、`EvidenceItem.fact_refs/rule_refs/legal_basis/document_refs/confidence`、`FactItem.evidence_status/can_support_external_positive_claim`、`legal_grounding.by_issue`、现有 context consistency checks。

### 7. Regression Scope

Assessment ContextPack、chapter prompt、result schema、renderer；若扩展 shared model 必须验证 EU SCC/US14117 等构造点。

### 8. Risk

**MEDIUM**

首轮规则可小，但需要重新定义真实的支持状态。当前对象不能原样实现 V0.2 的 E3/E4。

### 9. 对 V0.2 HOW 需要修正什么

- 删除不存在的 `citation_refs/status/strength`；
- 用 `legal_basis/confidence/FactItem.evidence_status` 等真实字段；
- `CONFLICTED` 若首轮保留，必须说明来源是现有 conflict signal 还是新增 additive 状态；当前 EvidenceItem 本身不支持；
- 插入点改为 ContextPack 构造后、generation 前；
- 明确 per-issue RAG 当前不会增强 EvidenceItem 本身。

### 10. 是否建议进入首轮实现

**YES_WITH_CHANGES**

## 6.B Citation Validity V1

### 1. Current Code Fact

CitationRegistry 在 ContextPack 内、章节生成前建立。章节生成通过公共 citation pipeline 把 marker 转成数字脚注；无法映射的 marker 会显示待核验，但 violation 未进入 Assessment consistency result。CitationMap 文件在 renderer 内写出。SourceRegistry Eligibility 没有在 Citation 层完整执行。

### 2. 与 V0.2 设计是否一致

**PARTIALLY CONSISTENT**

Existence/Traceability 有可复用基础；Eligibility 的“直接基于现有 Citation 链查询全部 registry 字段”不成立。

### 3. 最佳插入位置

分两段最符合真实生命周期：

1. Candidate eligibility：ContextPack/CitationRegistry 建成后、generation 前；
2. 最终 V1 gate：repair 完成后、`render_artifacts()` 前，使用最终 chapters + CitationRegistry + SourceRegistry exact lookup。

最终裁决必须以第 2 个位置为准，因为 repair 可修改正文，CitationMap 此时尚未写出。

### 4. 推荐实现方式

**ADAPTER + NEW_SMALL_COMPONENT + extend existing object**

新增只读 `source_id → SourceRegistryEntry` lookup，小型 Citation Gate adapter；不新增 LLM Judge，不改公共 citation pipeline 默认行为。

### 5. 最小新增代码

- exact registry lookup；
- Existence：registry item/最终引用是否可解析；
- Eligibility：review/citable/external/usage exact policy；
- Traceability：related issue/fact/evidence IDs 是否存在且非空；
- external/unregistered source 的 CONDITIONAL/REVIEW 规则；
- 修复 citation dedupe 关联合并或在 Gate 中识别不完整关系；
- Trace/tests。

### 6. 可直接复用代码

`CitationRegistry`、`CitationItem.source_id/related_*_ids`、`KnowledgeChunkV2.source_id`、`SourceRegistryEntry`、`UsagePolicyFilter`、citation compiler/marker utilities、CitationMap writer。

### 7. Regression Scope

Assessment citation builder、legal grounding、renderer、公共 SourceRegistry 读取；若修改 CitationItem shared schema，会影响多模块 citation tests/renderers。

### 8. Risk

**HIGH**

这是本轮最高风险项。风险是 identity/governance/traceability，而不是 marker 语法。

### 9. 对 V0.2 HOW 需要修正什么

- 明确 local source_id only 的稳定边界；
- 禁止把 output.py 的 title fuzzy resolution 用作 Gate join；
- 明确 CitationMap 在 render 后产生，Gate 使用 CitationRegistry；
- 明确 `review_status/can_be_cited` 不在 CitationItem；
- 明确 external DeliLegal source 的 fail-closed 策略；
- 将最终插入点改为 repair 后、render 前。

### 10. 是否建议进入首轮实现

**YES_WITH_CHANGES**

# 7. G4 Escalation Gate 审查

## 1. Current Code Fact

Diagnosis 已有 `requires_human_review/missing_facts/uncertainty_notes/confidence/conclusion_source`；Assessment 已有 `path_warning/consistency_issues/repair_blocked`，但没有统一 legal control status。任务执行状态由 Diagnosis 同步响应、AssessmentResult.state 和异步 TaskSnapshot.state 分别表示。

## 2. 与 V0.2 设计是否一致

**CONSISTENT**

统一聚合 GateResult 并输出独立 ControlDecision 是可行的 additive overlay。

## 3. 最佳插入位置

- Diagnosis：`DiagnosisService.evaluate()` 已得到最终 result 后、API/renderer 返回前。
- Assessment：最终 Citation Gate 和 repair 结果已知后、正式 renderer 前聚合；结果再写入 AssessmentResult。

## 4. 推荐实现方式

**ADAPTER + ADDITIVE_FIELD**

纯确定性聚合器，不调用 LLM，不改 task state。

## 5. 最小新增代码

- GateResult→ControlDecision reducer；
- 两个 domain result 的 additive fields；
- Diagnosis clarification questions；
- Assessment 内/外报告行为映射；
- 前端最小 status display。

## 6. 可直接复用代码

Diagnosis human-review signals、Assessment path/consistency/repair signals、现有 required action 文本、TraceRecorder、frontend generic result extraction。

## 7. Regression Scope

两个 result schema、OpenAPI generated types、ModuleRunPanel result presenter、异步 result serialization、V0 audit 可见性。

## 8. Risk

**MEDIUM**

状态聚合本身低风险；`BLOCKED` 时是否仍生成 internal draft、是否禁止 external artifact 必须在 V0.3 明确，否则容易把法律控制状态误做任务失败。

## 9. 对 V0.2 HOW 需要修正什么

明确状态和当前信号的最小映射：

| legal_control_status | Minimum mapping |
|---|---|
| `AUTO` | 所有适用 Gate PASS |
| `CONDITIONAL` | 非关键限制，允许保守输出 |
| `NEEDS_CLARIFICATION` | Diagnosis 关键 missing facts |
| `NEEDS_REVIEW` | conflict、inferred decisive facts、Evidence/Citation 不足、repair blocked |
| `BLOCKED` | 明确禁止自动形成正式外部结论/产物的控制结果 |

并写明 `task_status=COMPLETED` 可与后四种法律状态并存。

## 10. 是否建议进入首轮实现

**YES_WITH_CHANGES**

# 8. CN Diagnosis Pilot 真实代码映射

## 8.1 Current Flow

```text
POST /api/v1/diagnosis/evaluate
  or POST /api/v1/diagnosis/report
→ transfer_diagnosis.router.evaluate()/generate_report()
→ DiagnosisService.evaluate(DiagnosisAnswers, trace=None|TraceRecorder)
→ _resolve_answers()
   ├─ rule-based normalization
   ├─ count estimation
   └─ missing_facts list
→ ImportantDataAgent / PIClassifyAgent / ExemptionAgent
→ facts_from_module() → DiagnosisFacts
→ _validate_fact_consistency()
   └─ conflict → DiagnosisResult(manual_review) → return
→ DiagnosisRuleEngine.evaluate(facts) → RuleMatch
   ├─ non-default
   │  → _build_rule_result()
   │  → _build_rule_explanation() [LLM explanation only]
   │  → _attach_fact_metadata()
   │  → return DiagnosisResult
   └─ default
      → _needs_ai_inference()
      → _build_ai_inference_result() [may choose path]
      → or tree default result
→ DiagnosisReportRenderer.render() [report endpoint only]
→ DiagnosisResult / DiagnosisReportResponse
```

## 8.2 Target Flow

```text
Existing router
→ DiagnosisService.evaluate(..., control_hook=None by default)
→ Existing _resolve_answers()
→ Existing Agents
→ Existing facts_from_module()
→ Existing _validate_fact_consistency()
→ [G1 Fact Completeness Adapter, opt-in]
→ Existing DiagnosisRuleEngine.evaluate()
→ [G2 Rule Precedence Adapter: non-default only]
→ Existing rule explanation OR existing default AI inference
→ [G4 Escalation Adapter]
→ Existing renderer/API response
```

不修改的现有节点：Decision Tree、Rule 条件/阈值、Agents、risk scoring、报告 renderer、Assessment 的默认 `evaluate(answers)` 调用。

## 8.3 Assessment 复用风险

Assessment 传入的 `DiagnosisAnswers` 由 `_to_diagnosis_answers()` 推断场景、接收方、数据类型并调用同一 `evaluate()`。任何默认启用的 Fact Gate、任何 UNKNOWN 处理改动、任何 Rule default 行为改动，都会改变 Assessment path validation、Fact/Issue、风险等级和最终报告。必须 default-off 并以回归测试固定。

# 9. CN Assessment Pilot 真实代码映射

## 9.1 Current Flow

```text
POST /api/v1/assessment/generate[_async]
→ AssessmentService.generate_report()
→ prepare_run()
→ AssessmentService._build_pipeline()
→ WorkflowPipeline.run()
→ ProfileExtractor.extract(payload)
→ AssessmentService._evaluate_diagnosis(payload)
→ validate_path(payload, diagnosis path, rationale)
→ build_assessment_facts(payload, profile, diagnosis)
→ AssessmentRetriever.search(profile)
→ _attachment_notes_from_profile(profile)
→ build_assessment_issues(facts, diagnosis, regulations, attachment_notes)
→ build_assessment_evidence(facts, issues, regulations, diagnosis)
→ AssessmentService._retrieve_per_issue(issues=..., profile=..., regulations=...)
→ AssessmentService._build_context_pack(..., per_issue_rag=...)
   ├─ build_legal_grounding()
   ├─ build_writing_strategy()/compliance_reasoning/generation_basis
   └─ build_citations() → CitationRegistry
→ AssessmentChapterGenerator.generate(profile, regulations, context_pack)
→ ConsistencyChecker.check_with_context()
→ check_cn_alignment()
→ run_repair_pass()
→ trace.write_manifest()
→ AssessmentService._render_outputs()
→ AssessmentReportRenderer.render()
→ AssessmentResult
```

## 9.2 Target Flow

```text
Existing API / AssessmentService / WorkflowPipeline
→ Existing profile + Diagnosis reuse + path validation
→ Existing facts + retrieval + issues + evidence + per_issue_rag
→ Existing _build_context_pack()
→ [G3-A Minimum Evidence Sufficiency Adapter]
→ Existing generate_chapters()
→ Existing consistency + alignment + repair
→ [G3-B Citation Validity V1 on final chapters + registry]
→ [G4 Escalation Adapter]
→ Existing renderer, with formal-output behavior controlled by decision
→ AssessmentResult additive control fields
```

不修改的现有节点：retrieval implementation、issue builder、chapter generator、consistency/alignment/repair 默认逻辑、reporting/citation-map writer、其他 Pipeline services。

## 9.3 插入点裁决

- Evidence Gate：ContextPack 构造完成后、chapter generation 前。
- Citation Gate：repair 后、render 前；candidate eligibility 可提前执行，但最终 verdict 必须在此处。
- Escalation：Citation verdict 后、render 前。

## 9.4 公共 WorkflowPipeline 风险

首轮可用 Assessment-specific callback 内部 Adapter 完成，无需扩展公共 Pipeline。若选择 optional hook，必须默认 `None`，保持 `test_pipeline.py` 原事件顺序，并增加 Assessment-only hook test；EU SCC、US14117、CN Flow 兼容入口必须回归。

# 10. Current → Target 实现映射表

| Design Component | Current Code | Proposed Mapping | Change Type | Affected Modules | Risk |
|---|---|---|---|---|---|
| GateResult | 无统一对象 | 小型公共 Pydantic/dataclass contract | NEW_SMALL_COMPONENT | 两个 Pilot | LOW |
| ControlDecision | 分散 human review/path/consistency 信号 | 纯确定性 reducer | NEW_SMALL_COMPONENT | 两个 Pilot | LOW |
| Diagnosis fact input | DiagnosisFacts + missing/provenance | Fact Gate adapter input | REUSE | Diagnosis | LOW |
| Fact completeness | `_resolve_answers` + conflict validation | Agent 后、Rule 前 adapter | ADAPTER | Diagnosis，间接保护 Assessment | MEDIUM |
| Clarification questions | 无统一输出 | missing key → 固定问题映射 | NEW_SMALL_COMPONENT | Diagnosis | LOW |
| Deterministic decision | `RuleMatch` + `DiagnosisResult` | non-default precedence marker | ADAPTER | Diagnosis | LOW |
| Rule result metadata | matched_rule/conclusion_source | additive gate/control fields | ADDITIVE_FIELD | Diagnosis result consumers | LOW |
| Evidence Gate input | Issue/Evidence/Fact/grounding | 真实字段 policy | ADAPTER | Assessment | MEDIUM |
| Evidence carrier | GenerationContextPack | additive control results | ADDITIVE_FIELD | Shared type，Assessment writes | MEDIUM |
| Citation Existence | CitationRegistry + marker pipeline | final chapter/registry check | REUSE | Assessment | LOW |
| Citation Eligibility | SourceRegistry + partial chunk policy | exact source_id lookup | NEW_SMALL_COMPONENT | Assessment/Knowledge | HIGH |
| Citation Traceability | CitationItem.related_* | ID existence/completeness check | EXTEND | Assessment citation builder | HIGH |
| External source identity | synthetic/provider IDs | fail-closed or canonical registry ID | ADAPTER | Assessment per-issue RAG | HIGH |
| Trace control events | TraceRecorder arbitrary event | `control.*` records + mapping | EXTEND | Trace/frontend | LOW |
| Diagnosis API | DiagnosisResult / report wrapper | additive fields on inner result | ADDITIVE_FIELD | Diagnosis | LOW |
| Assessment API | AssessmentResult / async nested result | additive fields on result | ADDITIVE_FIELD | Assessment | LOW |
| Frontend status | generic result presenter | read/display legal control fields | EXTEND | Two Pilot UI | MEDIUM |
| RunTranscript | generic standard events | raw_name semantic mapping | EXTEND | Shared frontend trace | LOW |
| WorkflowPipeline | 3 direct instances | keep default unchanged; avoid first-round shared hook | REUSE | Assessment/EU SCC/US14117/CN Flow | LOW |

不需要 `REPLACE` 或 `REWRITE`。

# 11. Regression / Compatibility 风险

## 11.1 Diagnosis

- 默认 control 行为若改变，会影响 Assessment。
- Rule default 与 non-default 若未区分，会错误锁定 AI inference 或错误放行 deterministic result。
- 前置 Agents 会改写事实；Fact Gate 若放在 API 外层会观察到错误生命周期状态。
- sync diagnosis router 通过 `trace_sync()` 设置 contextvar，但未把 recorder 显式传给 `evaluate()`；Control event 需要显式传递或读取 current trace。

## 11.2 Assessment

- Service router 是单例，禁止 `self.last_control_decision` 一类 per-run 可变状态。
- Evidence Gate 使用错误字段会直接运行失败或形成虚假 PASS。
- Gate 放在 context 前无法看到 legal grounding/CitationRegistry；放在 repair 前无法验证最终引用文本。
- `BLOCKED` 不能简单抛异常并把 task state 变为 FAILED；应明确内部报告与正式外部报告的输出策略。

## 11.3 Shared Pipeline

- 3 个直接构造方和 1 个间接入口。
- 新 hook 必须 keyword-only、default `None`，不得改变默认 trace 顺序和 result shape 的 required contract。
- 若 `WorkflowRunResult` 增 required field，所有构造/测试都会受影响；应 default/additive。

## 11.4 Citation / Knowledge

- `CitationItem` 是多模块共享 dataclass；新增 required 字段风险高。
- `SourceRegistryEntry.review_status` 未进入 chunk；V1 应 exact lookup，不应复制一套可能漂移的值。
- `build_citations()` 以 `(title, article_no)` 去重，关系合并不完整；Traceability Gate 会暴露该问题。
- `output.py` 的 fuzzy title resolution 是输出兼容层，不得提升为治理判定。
- fallback/external source 必须 fail-closed，避免 synthetic ID 被误当 reviewed source。

## 11.5 API / Frontend

- additive result 字段对现有 JSON consumer 安全；OpenAPI types 需重新生成。
- `ModuleRunResponse.response` 当前是 `unknown`，传输层不会因新增字段失败；展示层需显式读取。
- `asyncState/state` 只用于执行完成判断，禁止塞入 legal statuses。
- RunTranscript 可兼容标准 event types；不要新增 event type 联合值扩大改动面。

# 12. 实施成本与任务顺序建议

## 12.1 成本评级

| Item | Cost | Reason |
|---|---|---|
| 1. Core Contract | LOW | 两个小型 additive contract |
| 2. Trace integration | LOW | recorder 已支持自定义 payload/name |
| 3. Diagnosis Fact Gate | MEDIUM | 必须进入 Agent 后、Rule 前真实 seam |
| 4. Diagnosis Rule Precedence | LOW | non-default RuleMatch 显式标记即可 |
| 5. Diagnosis Escalation | MEDIUM | 需整合 missing/conflict/inferred/default 分支 |
| 6. Assessment Evidence Gate | MEDIUM | 需按真实字段重写 V1 policy |
| 7. Assessment Citation Validity | HIGH | source identity、registry governance、关系合并 |
| 8. Assessment Escalation | MEDIUM | 需定义 internal/external output 行为 |
| 9. Frontend minimal exposure | MEDIUM | status card + trace semantic mapping + generated types |
| 10. Regression | MEDIUM | 两个共享链及异步/API/renderer 覆盖 |

本轮真正工程风险最高点：**Assessment Citation Validity V1，尤其是 canonical source identity 与 SourceRegistry Eligibility。**

## 12.2 建议任务顺序

不扩大 T01-T10 范围，但调整依赖顺序：

1. T01 Core Contract：先冻结 additive/default 规则。
2. T02 Trace Integration：保留标准 event types，建立 `control.*` raw_name。
3. T03 Diagnosis Fact Gate：在真实 seam 接入，先锁 Assessment 默认回归。
4. T04 Diagnosis Rule Precedence：区分 non-default/default。
5. T05 Diagnosis Escalation/API：完成 Pilot A 闭环。
6. T07-A Source Identity/Registry Lookup：在 Citation Gate 前先解决 exact join。
7. T06 Assessment Evidence Gate：按真实字段与 ContextPack seam 实现。
8. T07-B Citation Existence/Eligibility/Traceability：repair 后最终裁决。
9. T08 Assessment Escalation/API：明确 formal/internal output 行为。
10. T09 Frontend Minimal Exposure。
11. T10 两个 Pilot + shared callers regression 与 FACT refresh。

# 13. 对 WHY / HOW V0.2 的明确修改建议

| Document | Section | Current Statement | Required Change | Code Evidence |
|---|---|---|---|---|
| WHY | 0.2 / 1.2 | 4 个模块使用或部分使用 WorkflowPipeline，并将 CN Flow列为直接分支 | 写成“3 个直接 Pipeline 实例；CN Flow 通过 US14117Service 间接经过 Pipeline” | `rg WorkflowPipeline(`；`CNFlowService.canonical_service` |
| WHY | 1.4 | Evidence 已能关联 Fact/Rule/Citation/Document | 限定为 schema 能表达 Fact/Rule/legal binding/Document；Assessment runtime 不存在 citation_refs，document refs 通常空 | `common/workflow/evidence.py`、`assessment/evidence_builder.py` |
| WHY | 9.1 | Diagnosis Control 可放模块边界 | 说明真实 Gate seam 在 Agent 后、Rule 前；API boundary 只能负责 opt-in，不负责二次事实解析 | `DiagnosisService.evaluate()` |
| WHY | 9.2 | Assessment-specific hook / adapter | 保留原则，但明确首轮优先 Assessment callback adapter，避免公共 Pipeline hook | `AssessmentService._build_pipeline()` |
| HOW | 0.2 | SourceRegistry 已提供资格，可供 Pilot | 改为“字段存在于 Registry/Chunk，但 Citation 链不能完整直接查询” | `knowledge/v2.py`、`citation/models.py` |
| HOW | 3.1 | normalization → missing/conflict → Rule | 补上 Rule 前 Agents、missing list 被更新、default Rule 后 AI inference | `transfer_diagnosis/service.py:42-207` |
| HOW | 3.3 | Option A API boundary Fact Gate | 标为仅能控制 opt-in；真实 gate evaluation 必须进入 service seam | 同上 |
| HOW | 4.7 | 若 Rule 后不存在路径改写，只做标识 | 改为 non-default 分支成立；default 分支存在 AI path inference | `service.py:138-207, 531+` |
| HOW | 5.3 | EvidenceItem 有 citation_refs/status/strength | 删除并替换为真实字段；新增字段必须标 EXTEND | `common/workflow/evidence.py:91-170` |
| HOW | 5.4 | per_issue_rag → Gate → build_context_pack | 改为 context_pack 建成后、generate 前；否则没有 grounding/registry | `workflow/pipeline.py:100-122`、`assessment/service.py:288-402` |
| HOW | 5.5 | Eligibility 基于 Citation 现有字段 | 改为 canonical source_id exact lookup SourceRegistry；Citation 自身字段不权威 | `citation/models.py`、`knowledge/v2.py` |
| HOW | 5.6 | 待确认是否有 stable source_id | 写明“local multi-index 有；fallback/DeliLegal 无端到端保证” | `assessment/retriever.py`、`rag/service.py`、`legal_grounding.py:409+` |
| HOW | 5.9 | generation 后、consistency 前 Citation Gate | 最终 gate 改为 repair 后、render 前；可选候选资格预检在 generation 前 | `workflow/pipeline.py:122-188` |
| HOW | 6.4 | API additive fields | 明确字段加入 domain result，不加入 task state；async 在 nested result 携带 | 两个 Pilot schema/router |
| HOW | 9.3 | 优先使用现有 RunTranscript | 写明未知 control name 默认显示为 Task；需 raw_name semantic mapping 才是明确 Gate UI | `trace/recorder.py`、`trace-adapter.ts` |
| HOW | T06/T07 | Evidence/Citation 可直接按既有对象实现 | T07 前增加 canonical identity/registry lookup 子任务；T06 按真实字段重写 | 上述 Evidence/Citation 证据 |
| HOW | Q12 后实施约束 | optional hook 是推荐主路径 | 改为 Assessment-specific callback adapter 优先；公共 hook 是后续复用升级 | 3 个直接 Pipeline 构造方 |

# 14. 最终裁决

## B. READY_WITH_MAJOR_IMPLEMENTATION_CHANGES

核心架构前提没有被源码否定：两个 Pilot 都可在现有 Domain Workflow 上以 Adapter、additive field 和小型公共契约实现，且不需要重构 Runtime。

但 V0.2 HOW 不能直接作为开发合同。进入实现前，V0.3 Final Design 至少必须完成以下修订：

1. 用真实 EvidenceItem 字段重写 Evidence Sufficiency V1；
2. 将 Evidence Gate 改到 ContextPack 建成后、generation 前；
3. 将最终 Citation Gate 改到 repair 后、render 前；
4. 明确 canonical `source_id` 的 local-only 稳定边界和外部来源 fail-closed 策略；
5. 用 SourceRegistry exact lookup 实现 Eligibility，禁止 title fuzzy join；
6. 区分 Diagnosis non-default deterministic match 与 default→AI inference；
7. 将控制字段加到 domain result，而不是 task status；
8. 保持 Diagnosis 与 WorkflowPipeline 所有新行为 default-off；
9. 修复或显式处理 Citation 关系去重不完整与 document_refs 运行时空值问题；
10. 以 Assessment、EU SCC、US14117、CN Flow、V0 Gateway、Harness 为回归边界。



```
你现在负责对 DataComplyFlow 当前比赛版 Legal Agent 架构升级方案进行一次“开发事实与可行性审查”。

我会提供两份设计文档：

1. 《DataComplyFlow_比赛版LegalAgent架构升级_设计依据与架构决策_V0.2.md》
   - WHY 文档
   - 负责说明为什么这样设计、架构主线、技术来源、比赛故事和设计边界

2. 《DataComplyFlow_比赛版LegalAgent架构升级_实施设计与开发说明_V0.2.md》
   - HOW 文档
   - 负责说明如何基于当前代码，以最小改造方式实现该架构

你的当前任务不是重新设计架构，也不是立即修改代码。

你的任务是：

> 基于当前代码仓库最新 HEAD，对这两份设计文档进行严格的 Fact / Feasibility Review，确认设计中的代码事实、调用关系、插入位置、共享依赖、数据结构、实现成本和回归风险是否与当前真实系统一致，并形成一份可以返回给架构设计者继续修订 V0.3 Final Design 的审查文档。

==================================================
一、最高优先级原则
==================================================

1. 当前最新源码 HEAD 是最高优先级事实依据。

如果：
设计文档
历史 FACT
旧说明文档
README
历史讨论

与当前源码不一致：

一律以当前源码为准。

请明确指出差异，不要为了让设计文档“看起来正确”而迁就设计。

2. 本轮只做审查，不做代码修改。

除非为了确认事实必须执行：
- grep / rg
- 阅读源码
- 查找调用关系
- 阅读测试
- 运行极少量无副作用测试

否则不要修改业务代码。

不要创建新的架构实现。

3. 不重新讨论已经冻结的架构主线，除非源码事实证明其核心前提不成立。

当前冻结主线是：

Existing Domain Workflow
        +
Module Adapter
        +
Four Legal Control Gates
        +
GateResult / ControlDecision

四类控制机制为：

G1 Fact Completeness Gate
G2 Deterministic Rule Precedence Gate
G3 Evidence & Citation Gate
G4 Escalation Gate

首轮 Pilot 为：

A. CN Transfer Diagnosis
   - Fact Completeness
   - Deterministic Rule Precedence
   - Escalation

B. CN Security Assessment
   - Minimum Evidence Sufficiency
   - Citation Validity V1
   - Escalation

除非真实代码事实证明上述某一点无法成立，否则不要重新提出：
- 全面 Runtime 重构
- 统一所有 Workflow
- LangGraph / OpenAI Agents SDK 迁移
- Full Policy Graph
- 新 Multi-Agent 架构
- RAG 全面替换
- 新统一 Claim IR
- 新万能 HarnessContext

4. 本轮重点不是“你认为更好的架构是什么”。

重点是回答：

> 设计是否能够准确、低风险地映射到当前代码？

==================================================
二、必须先完成的代码事实扫描
==================================================

请基于当前 HEAD 至少核查以下内容。

A. 模块与执行拓扑
- 当前正式模块数量及注册情况
- cn.transfer_diagnosis 的真实入口
- cn.security_assessment 的真实入口
- WorkflowPipeline 当前真实使用者
- Specialized Service / Workflow 当前情况

B. Diagnosis
重点检查：

- DiagnosisAnswers
- DiagnosisService
- facts normalization
- missing check
- conflict check
- deterministic rule engine
- DiagnosisDecision
- DiagnosisResult
- Rule 之后是否存在 LLM / Agent 步骤
- 后续步骤是否可能改变路径性结论
- Assessment 是否、以及如何复用 DiagnosisService

请形成真实调用链，不要只看文件名猜测。

C. Assessment
重点检查：

- AssessmentService / API entry
- WorkflowPipeline.run
- build_facts
- build_issues
- build_evidence
- per_issue_rag
- build_context_pack
- generate_chapters
- consistency
- alignment
- repair
- render

重点确认：
Evidence Gate 最合理的真实插入点在哪里；
Citation Validity 最合理的真实插入点在哪里。

D. 数据对象
请检查当前实际定义和运行时使用情况：

- FactItem
- IssueItem
- EvidenceItem
- GenerationContextPack
- CitationItem
- CitationRegistry
- CitationMap（如存在）
- SourceRegistryEntry
- retrieval hit / chunk metadata

不要只检查 Schema 是否定义字段，还要尽量判断：

> 字段在当前真实运行链中是否实际被填充。

特别关注：

EvidenceItem:
- fact_refs
- rule_refs
- citation_refs
- document_refs
- strength
- status
- claim

Citation:
- source_id 或其他 stable source identifier
- associated_issue_ids
- associated_fact_ids

E. Citation → SourceRegistry
这是本轮必须重点核实的事实。

请回答：

CitationItem / Retrieval Hit / KnowledgeChunk
与
SourceRegistryEntry

当前是否存在稳定 Join Key？

优先检查：
- source_id
- registry id
- stable metadata key

如果不存在：
请给出“最小、最安全”的扩展建议。

禁止建议：
通过法规 title / name 做模糊匹配作为正式 Join 机制。

F. Source Governance
确认当前以下字段在哪里产生、在哪里消费：

- review_status
- can_be_cited
- can_enter_external_report
- allowed_usage
- authority_level
- binding_force

特别判断：

这些字段当前是否已经能够被 Assessment 的 Citation / Evidence 链直接使用。

G. Trace
确认：

- TraceRecorder / manifest / event 真实结构
- 是否支持自定义 event
- 是否支持 metadata/details
- 新增 control.* event 的最低改造成本
- 前端 RunTranscript / TraceNodeView 是否可以消费

H. API / frontend
确认：

- Diagnosis result schema
- Assessment result schema
- task_status 当前定义
- frontend status 当前定义
- additive 增加 legal_control_status / control_reasons / required_actions 是否安全
- 哪个响应层最适合增加

==================================================
三、必须逐项回答 HOW 文档中的 14 个问题
==================================================

请逐项回答，不得遗漏。

Q1
Diagnosis missing / conflict check 的真实返回对象和调用位置是什么？

Q2
Assessment 调用 DiagnosisService 的真实入口、参数和调用目的是什么？

Q3
如何保证 Diagnosis Pilot 的 Control Gate 不改变 Assessment 内部复用 DiagnosisService 的默认行为？

Q4
Diagnosis Rule Engine 之后是否存在任何 LLM / Agent 步骤可能改写路径性法律结论？

如果不存在，请明确说明：
Rule Precedence V1 是否只需要做显式 precedence 标识 + Trace + 防止结果字段被覆盖。

Q5
Assessment 中：
build_evidence
retrieve_per_issue
build_context_pack
的真实顺序、调用对象和参数是什么？

Q6
EvidenceItem 当前各字段在运行时的实际填充情况如何？

请至少检查：
fact_refs
rule_refs
citation_refs
document_refs
status
strength
claim

区分：
- Schema 存在且实际使用
- Schema 存在但常为空
- 当前根本不存在

Q7
CitationItem / Retrieval Hit 与 SourceRegistry 当前的稳定 Join Key 是什么？

如果没有，请提出最小扩展方案。

Q8
现有 consistency / alignment / repair 是否已经检查：
- unsupported claim
- citation mismatch
- rule/output conflict
- evidence inconsistency

如已有，请指出真实代码位置，避免新 Gate 重复实现。

Q9
TraceRecorder 是否支持自定义 event / metadata？
新增：
control.fact_completeness
control.rule_precedence
control.evidence_sufficiency
control.citation_validity
control.escalation
的成本如何？

Q10
当前 API Response 最适合在哪一层 additive 增加：

legal_control_status
control_reasons
required_actions
clarification_questions（Diagnosis only，如适用）

Q11
当前前端 RunTranscript / TraceNodeView 是否能够直接展示新增 control event？

若不能：
最低成本兼容方式是什么？

Q12
Assessment Evidence Gate 若采用 WorkflowPipeline optional hook，会影响哪些共享调用方、类型签名和测试？

Q13
SourceRegistry 中：
can_be_cited
can_enter_external_report
allowed_usage
review_status

是否能够从当前 Citation / Evidence 链稳定查询？

Q14
当前仓库是否存在设计文档尚未识别的共享 Service / Common Utility / Workflow 调用关系，可能使两个 Pilot 产生跨模块回归？

==================================================
四、对四个 Gate 分别做 Implementation Review
==================================================

对每个 Gate 使用完全相同的格式。

--------------------------------
G1 Fact Completeness Gate
--------------------------------

请写：

1. Current Code Fact
2. 与 V0.2 设计是否一致
   - CONSISTENT
   - PARTIALLY CONSISTENT
   - INCONSISTENT
3. 最佳插入位置
4. 推荐实现方式
   - Adapter
   - optional hook
   - extend existing object
   - other
5. 最小新增代码
6. 可直接复用代码
7. Regression Scope
8. Risk
   - LOW
   - MEDIUM
   - HIGH
9. 对 V0.2 HOW 需要修正什么
10. 是否建议进入首轮实现
   - YES
   - YES_WITH_CHANGES
   - NO

--------------------------------
G2 Deterministic Rule Precedence Gate
--------------------------------

同样格式。

特别注意：

这里的 Precedence 指“系统执行优先级”。

不要与：
authority_level
binding_force

等法规来源法律权威属性混淆。

--------------------------------
G3 Evidence & Citation Gate
--------------------------------

分别审查：

A. Minimum Evidence Sufficiency V1
B. Citation Validity V1

Citation V1 当前只要求：

- Existence
- Eligibility
- Traceability

不要擅自把首轮扩大成：
- 完整 Semantic Fidelity
- 完整 Fine-grained Applicability
- LLM Citation Judge

除非当前代码已经有可直接复用能力。

--------------------------------
G4 Escalation Gate
--------------------------------

重点判断：

当前 API / result / frontend 最低成本如何表达：

AUTO
CONDITIONAL
NEEDS_CLARIFICATION
NEEDS_REVIEW
BLOCKED

并确保：

task_status
和
legal_control_status

完全分离。

==================================================
五、两个 Pilot 分别做完整代码映射
==================================================

A. CN Transfer Diagnosis

请输出：

Current Flow:
文件 / 类 / 方法级真实调用链

Target Flow:
标出 Gate 插入点

例如：

A
→ B
→ [Fact Gate]
→ C
→ [Rule Precedence]
→ D

必须注明：
哪些现有节点不修改。

特别审查：
Assessment 对 DiagnosisService 的复用风险。

B. CN Security Assessment

同样输出：

Current Flow
Target Flow
Evidence Gate 插入点
Citation Gate 插入点
Escalation 插入点

特别审查：
公共 WorkflowPipeline 共享风险。

==================================================
六、给出“当前设计 → 实际代码”的映射表
==================================================

至少包含：

| Design Component | Current Code | Proposed Mapping | Change Type | Affected Modules | Risk |

Change Type 只能优先使用：

- REUSE
- EXTEND
- ADAPTER
- OPTIONAL_HOOK
- ADDITIVE_FIELD
- NEW_SMALL_COMPONENT

如你认为必须：
- REPLACE
- REWRITE

必须单独解释为什么 Adapter / Extend 不可行。

==================================================
七、检查比赛阶段实施成本
==================================================

请不要给虚假精确工时。

只需要给：

- LOW
- MEDIUM
- HIGH

分别评价：

1. Core Contract
2. Trace integration
3. Diagnosis Fact Gate
4. Diagnosis Rule Precedence
5. Diagnosis Escalation
6. Assessment Evidence Gate
7. Assessment Citation Validity
8. Assessment Escalation
9. Frontend minimal exposure
10. Regression

并指出：

> 哪一个是本轮真正的工程风险最高点？

==================================================
八、明确指出设计中任何“不够写实”的地方
==================================================

请主动寻找：

1. 文档中把 Schema 存在误认为运行时已经填充；
2. 文档中把设计能力误写成当前已实现；
3. 文档假设某个调用关系存在，但当前代码不存在；
4. 文档假设模块相互独立，但实际上共享 Service；
5. 文档建议插入点与当前参数生命周期不匹配；
6. Citation / SourceRegistry 无法稳定连接；
7. Control Status 与现有 Task Status 可能冲突；
8. 任何会导致其他模块回归的问题。

不要因为这些问题与设计文档冲突而省略。

==================================================
九、不要做的事情
==================================================

本轮严禁：

- 修改项目架构代码；
- 直接实现 Gate；
- 大规模 refactor；
- 创建新 Runtime；
- 迁移 Agent Framework；
- 重新设计整个 DataComplyFlow；
- 讨论 Benchmark 指标；
- 用“最佳实践”覆盖当前真实代码；
- 因为设计文档写了某组件就假设它已经存在。

==================================================
十、最终交付物
==================================================

只生成一份 Markdown：

`DataComplyFlow_LegalAgent架构升级_开发事实与可行性审查_V0.1.md`

推荐目录：

# 0. 审查说明与 HEAD 信息

必须记录：
- branch
- commit / HEAD
- 审查日期
- 是否有未提交修改（如可确认）

# 1. 总体审查结论

给出：
- 架构主线是否成立
- 是否可以进入实现
- 最大风险是什么
- 是否需要先修改 V0.2

# 2. 当前代码事实校正

列出：
- 与 V0.2 一致的事实
- 需要修正的事实
- 新发现的重要共享调用关系

# 3. Q1—Q14 逐项回答

不得遗漏。

# 4. G1 Fact Completeness Gate 审查

# 5. G2 Deterministic Rule Precedence Gate 审查

# 6. G3 Evidence & Citation Gate 审查

# 7. G4 Escalation Gate 审查

# 8. CN Diagnosis Pilot 真实代码映射

# 9. CN Assessment Pilot 真实代码映射

# 10. Current → Target 实现映射表

# 11. Regression / Compatibility 风险

# 12. 实施成本与任务顺序建议

可基于 T01—T10 调整“实施顺序”，但不得重新扩大架构范围。

# 13. 对 WHY / HOW V0.2 的明确修改建议

使用：

| Document | Section | Current Statement | Required Change | Code Evidence |

# 14. 最终裁决

只能从以下三类选择：

A. READY_FOR_V0.3
核心方案成立，仅需按真实代码修正后即可进入开发。

B. READY_WITH_MAJOR_IMPLEMENTATION_CHANGES
核心方案成立，但 HOW 的实现方式需要明显调整。

C. ARCHITECTURE_PREMISE_INVALID
只有当前源码直接证明核心架构前提不成立时才能选择。

==================================================
十一、审查质量要求
==================================================

1. 所有“当前已经实现”的判断必须来自真实源码。
2. 尽量给出：
   - 文件路径
   - 类名
   - 方法名
   - 关键调用关系
3. 不需要复制大段代码。
4. 不需要讨论与本次架构无关的代码质量问题。
5. 不要为了显得完整而扩大审查范围。
6. 对不确定事实明确写：
   NOT_CONFIRMED
7. 不要猜测。
8. 重点是：
   FACT
   FEASIBILITY
   INSERTION POINT
   REGRESSION RISK
   MINIMUM CHANGE

完成审查后只返回：

`DataComplyFlow_LegalAgent架构升级_开发事实与可行性审查_V0.1.md`

不要修改业务代码。
```