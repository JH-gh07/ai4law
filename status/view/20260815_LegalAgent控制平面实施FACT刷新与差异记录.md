# task073 Legal Agent 控制平面 — 实施 FACT 刷新与设计-实现差异记录（2026-08-15）

> 本文是 task073（DataComplyFlow Legal Agent 控制平面）Phase 8 的 FACT refresh 交付物，
> 记录**代码真实落地位置**、Gate 实际接口、opt-in 机制、canonical source identity、
> Trace、UI、回归范围，以及与 V0.3 设计文档（`status/todo/DataComplyFlow_LegalAgent架构升级_*_最终版.md`）的差异。
> 口径：代码与运行证据优先；本文件不是法律意见，也不是"schema 通过即完成"的替代证明。

---

## 0. 一句话结论

控制平面以**加性（additive）、opt-in**方式落地于两个 pilot 模块——CN Transfer Diagnosis 与 CN Security Assessment，
未修改公共 `WorkflowPipeline` 默认行为；契约、trace、canonical identity、三个 Assessment 门、前端 UI 均已实现并有测试/运行证据。
后端全量回归 1295 passed / 9 failed（9 个失败均为与 task073 无关的历史遗留，见 §7）；task073 相关子集 341 passed；前端 vitest 200 passed / 2 skipped，`tsc -b` 通过，`git diff --check` 清洁。

---

## 1. 最终 HEAD 与提交序列

| 提交 | 说明 |
|---|---|
| `c444d081` | 实施前存档快照（Phase 0 基线） |
| `9d021b97` | Phase 1-4：契约/聚合 + trace + CN Transfer Diagnosis 控制适配器 + Assessment canonical identity |
| `124e6852` | Phase 5-6：Assessment Evidence + Citation Validity + Escalation 门 |
| `464c5b1a` | Phase 7：前端呈现 Legal Agent 控制状态（T09） |

最终 HEAD：`464c5b1ac6bf54c8df02dda82d52fd412f393ae0`

变更规模（`c444d081..HEAD`）：34 文件，+3097 / -29。

---

## 2. Control Contracts 真实代码位置

| 契约 | 文件 | 真实内容 |
|---|---|---|
| `LegalControlGateResult` | `backend/common/legal_control/contracts.py:34` | `gate`/`outcome`/`reasons`/`refs`/`required_actions`/`details` |
| `LegalControlDecision` | `backend/common/legal_control/contracts.py:50` | `legal_control_status`/`gate_results`/`reasons`/`required_actions` |
| 状态优先级 | `contracts.py:65-79` | 显式字典 `_STATUS_PRIORITY`（AUTO<CONDITIONAL<NEEDS_CLARIFICATION<NEEDS_REVIEW<BLOCKED）；禁止用字典迭代顺序决定 |
| outcome→status | `contracts.py:74-79` | PASS→AUTO、CONDITIONAL→CONDITIONAL、ESCALATE→NEEDS_REVIEW、BLOCK→BLOCKED |
| `merge_gate_results` | `contracts.py:104` | 特例：`FACT_COMPLETENESS`+`ESCALATE`+`details.critical_missing`→NEEDS_CLARIFICATION |
| 动作常量 | `contracts.py:82-87` | `ACTION_*` 七项标准动作 |
| 对外导出 | `backend/common/legal_control/__init__.py` | 独立命名空间，杜绝与 `render_manifest.GateResult` 混用 |

Gate 名称（5）：`FACT_COMPLETENESS`、`RULE_PRECEDENCE`、`EVIDENCE_SUFFICIENCY`、`CITATION_VALIDITY`、`ESCALATION`。
Gate outcome（4）：`PASS`、`CONDITIONAL`、`ESCALATE`、`BLOCK`。
`legal_control_status`（5）：`AUTO`、`CONDITIONAL`、`NEEDS_CLARIFICATION`、`NEEDS_REVIEW`、`BLOCKED`。

> 关键约束落实：`legal_control_status` 只表达法律自动化可用程度，与 `task_status/state`（程序执行状态）严格分离，禁止互相映射为失败。

---

## 3. Gate 实际接口与归属

### 3.1 CN Transfer Diagnosis（T03-T05）— `backend/domains/cn/transfer_diagnosis/control_adapter.py`

| 函数 | 门 | 逻辑 |
|---|---|---|
| `build_fact_completeness_gate` | G1 `FACT_COMPLETENESS` | 关键事实（`is_ciio`/`contains_important_data`/`no_personal_info`）缺失→ESCALATE+`critical_missing`；既有冲突→ESCALATE+`conflicts`；否则 PASS |
| `build_rule_precedence_gate` | G2 `RULE_PRECEDENCE` | default 分支→CONDITIONAL（不打确定性标签）；决定性事实来自 LLM_INFERENCE/ESTIMATE/DEFAULT→ESCALATE；确定性命中→PASS+`execution_precedence=True` |
| `build_control_decision` | G4 聚合 | 逐门 `record_gate_trace` + `merge_gate_results` |

### 3.2 CN Security Assessment（T06-B/T07/T08）

| 函数 | 门 | 逻辑 |
|---|---|---|
| `run_evidence_gate` | `EVIDENCE_SUFFICIENCY` | `backend/domains/cn/security_assessment/evidence_gate.py:88`；E1 引用完整性、E2 法律依据、E3 外部积极事实、E4 单一低置信、E5 既有 consistency dangling refs |
| `run_citation_validity_gate` | `CITATION_VALIDITY` | `citation_validity_gate.py:118`；C1 精确解析最终 marker、C2 exact Registry eligibility（fail-closed）、C3 issue/fact/evidence 可追溯 |
| `run_escalation_gate` | `ESCALATION` | `escalation_gate.py`；`repair_blocked`/`REPAIR_BLOCKED:`/blocking signals→ESCALATE，否则 PASS |

---

## 4. opt-in 机制（不修改共享 Pipeline 默认行为）

- **Diagnosis**：`DiagnosisService.evaluate(..., control=True)` 显式 opt-in；`control_adapter.py` 为纯函数，由 service 在 result 完成后调用并写回 `result.control_decision`/`result.clarification_questions`。
- **Assessment**：`AssessmentService.generate_report(..., control: bool | None = None)`；`_build_pipeline` 通过**闭包**把 `control` 传入 `_build_context_pack`，**不存储在 singleton service 上**，避免跨请求串状态。
- `control=False/None` 时：`control_gate_results` 保持空列表，`control_decision=None`，输出与事件顺序与基线一致（`test_control_service.py`、`test_schema_additive_compat.py` 覆盖）。
- 公共 `WorkflowPipeline` 默认签名/事件顺序**未改**；EU SCC / US14117 的 `render_artifacts` 使用 `**kw` 吸收多余 kwargs（Phase 1 已核验）。

---

## 5. Canonical source identity 与 Eligibility lookup

- `backend/common/citation/source_identity.py`：`SourceIdentityResolver` 通过 **exact membership** 解析 `source_id` 回 `SourceRegistry` 权威身份；三类结果 `REGISTERED`/`UNREGISTERED`/`INELIGIBLE`。
- `backend/common/citation/models.py`：`CitationItem` 增加 `registry_source_id`（additive，`None` 默认）。
- fail-closed：`review_status=metadata_review_required` 或 `can_be_cited=False`→`INELIGIBLE`；未命中→`UNREGISTERED`，**绝不 fuzzy 提升**；权威值只来自 `SourceRegistryEntry`，不从 chunk 复制第二真相源。
- `_build_context_pack` 中 `source_identity_resolver = SourceIdentityResolver() if control else None`，传给 `build_citations(..., source_identity_resolver=...)`。

> ⚠️ 数据治理观察（待法律/数据复核，记录不修）：SourceRegistry 中 `CN-TPL-019` 结构化字段为
> `can_be_cited=true`、`can_enter_external_report=true`、`allowed_usage=["legal_grounding","external_report","internal_review"]`，
> 但 `metadata.usage="结构参照"`、`metadata.report_usage="用于结构参照，不直接作为法律依据"`。
> 两者与方案"不得提升为实体法依据"的意图存在口径差异；本实现**忠实按结构化字段**判定（fail-closed 边界在 metadata 层未收敛）。此项为数据侧待办，不影响本阶段代码验收结论。

---

## 6. Trace 与 UI

### 6.1 Trace

- `backend/common/legal_control/trace.py`：复用 `TraceRecorder.record`，`raw_name` 用 `control.*` 命名空间（`control.fact_completeness` 等）；**不扩展 SSE event union**。
- event type：`PASS`/`CONDITIONAL`→`intermediate`；`ESCALATE`/`BLOCK`→`warning`。
- 只记录 `gate/outcome/reasons/refs` 摘要，不写敏感正文（§6 安全控制）。

### 6.2 前端 UI

| 文件 | 变更 |
|---|---|
| `frontend/src/features/module-runner/types.ts` | 新增 `UserFacingControlStatus`，`UserFacingResult` 增加 `control` 字段 |
| `frontend/src/features/module-runner/model.ts` | `buildUserFacingResult` 读取 `control_decision.legal_control_status/reasons/required_actions` 与 `clarification_questions`；旧 response 无控制字段时 `control=null` 不崩溃 |
| `frontend/src/components/workspace/ModuleRunPanel.tsx` | 新增法律自动化控制块：`NEEDS_CLARIFICATION`→显示缺失事实、`NEEDS_REVIEW`→人工复核提示、`CONDITIONAL`→条件结论；非 AUTO 时显示控制 chip |
| `frontend/src/styles/app/workspace.css` | 新增控制块样式（琥珀色区分普通结果块） |
| `frontend/src/lib/trace-adapter.ts` + `trace-i18n.ts` | 识别 `control.*` 事件，trace 面板显示"执行控制门判定" |
| `frontend/src/api/generated/openapi.d.ts` | 重新生成：新增 `LegalControlDecision`/`LegalControlGateResult`，`DiagnosisResult`/`AssessmentResult` 增加 `control_decision`/`clarification_questions` |

> 出口核对：结果面板与 trace 面板均可看到控制状态；控制字段缺失时默认隐藏而非报错；`state/asyncState` 未被复用于表示控制状态。

---

## 7. 回归范围与结果

### 7.1 后端

| 范围 | 命令 | 结果 |
|---|---|---|
| task073 相关子集 | `.venv/bin/python -m pytest -q backend/common/legal_control backend/common/citation backend/domains/cn/security_assessment backend/domains/cn/transfer_diagnosis backend/common/workflow` | **341 passed** |
| 全量 | `.venv/bin/python -m pytest -q`（testpaths=backend+benchmarks） | **1295 passed / 9 failed** |

9 个失败均为**与 task073 无关的历史遗留**，逐一核验不在 `c444d081..HEAD` 变更集内：

| 失败测试 | 归类 |
|---|---|
| `api/v1/test_system_settings.py::test_runtime_settings_blank_secret_preserves_existing_value` | 系统设置（历史遗留） |
| `cn/pipia/test_service.py::test_scc_evidence_drives_source_findings` / `test_certification_evidence_drives_path_findings` | 报告迁移 golden fixture（与 task073 无关，FACT 基线已标注） |
| `eu/scc_review/test_service.py::test_uploaded_scc_document_drives_core_review` | EU SCC 引用 display label（`2021/914` 未命中） |
| `tests/harness/test_case_parity.py` ×3 | case catalog(28) vs frontend inventory(40) 计数漂移（未触碰案例清单） |
| `benchmarks/test_rag_eval.py` ×2 | `us_privacy_review` 模块名不在 RetrievalRequest literal 枚举 |

### 7.2 前端

| 项 | 结果 |
|---|---|
| `npx tsc -b` | 通过（无类型错误） |
| `npx vitest run` | **200 passed / 2 skipped**（32 files passed / 1 skipped） |
| `git diff --check` | 清洁（exit 0） |

---

## 8. 其他模块影响与默认关闭回归

- 加性字段：`GenerationContextPack.control_gate_results`（默认空）、`DiagnosisResult`/`AssessmentResult` 的 `control_decision=None`、`clarification_questions=[]`。
- 公共 `WorkflowPipeline` 未改默认行为；EU SCC / US14117 / CN Flow 的 `render_artifacts` 用 `**kw` 吸收新增 kwargs。
- `frontend/src/lib/dev-test-cases.ts` 因 OpenAPI 重生成后 `TIARequest` 默认值字段变为可选，仅做 `?? ""`/`?? []` 可空访问收敛，无行为变化。

---

## 9. 与 V0.3 设计的差异（Designed/Implemented/Difference/Reason/Impact）

| 项 | Designed | Implemented | Difference | Reason | Impact |
|---|---|---|---|---|---|
| 试点范围 | 5 门通用控制平面，覆盖多模块 | 5 门仅落地 2 个 pilot（CN Transfer Diagnosis + CN Security Assessment） | 未做 11 模块迁移 | 方案明确"非目标：11 模块迁移"；先 pilot 验证 | 无跨模块回归风险 |
| FACT/RULE 门归属 | 通用 gate | Diagnosis 专用 `control_adapter.py` 纯函数 | 未上收为通用 Pipeline 门 | 保持 Domain Workflow 自治（P3） | Diagnosis 独立 opt-in |
| Evidence/Citation/Escalation 门归属 | 插入 Pipeline 阶段 | Assessment-specific adapter 显式调用；Citation Validity 在 `pipeline.run()` **之后**读最终章节做只读校验 | 未改公共 Pipeline 阶段顺序 | 避免修改共享 Pipeline 默认行为；fail-closing 在 `_build_context_pack` 前已完成 | 公共 Pipeline 零回归 |
| BLOCK/BLOCKED | 保留契约 | 契约保留，pilot 不主动触发 BLOCK | 无 pilot 触发 BLOCK 的路径 | `BLOCKED` 保留契约供后续 fail-closed 硬阻断 | 无 |
| canonical identity | 需建立 | `SourceIdentityResolver` exact membership + fail-closed | 无 fuzzy 提升 | Eligibility 只能 exact（升级触发器） | C2 可精确回查 |
| Trace | 复用 trace | 复用 `TraceRecorder.record`，`control.*` raw_name，不扩展 SSE union | 无新 event type | 前端 trace 面板与 SSE 契约稳定 | 旧事件顺序不变 |
| legal vs task state | 分离 | `legal_control_status` 独立于 `task_status/state` | 无映射 | 升级触发器：禁止把 legal status 写入 task state | `task_status=COMPLETED` 可与 `NEEDS_REVIEW` 并存 |

---

## 10. 结论

- T01-T10 出口条件均有测试/运行证据（关键路径正负 fixture 齐备：`test_contracts.py`、`test_trace.py`、`test_control_adapter.py`、`test_evidence_gate.py`、`test_citation_validity_gate.py`、`test_escalation_gate.py`、`test_control_service.py` ×2、`test_schema_additive_compat.py`、`test_source_identity.py`、`test_citation_identity.py`）。
- 默认关闭回归：未传 `control` 时结果与 trace 与基线一致（`test_control_off_has_no_control_decision` + 全量子集无新增失败）。
- 剩余数据治理待办（§5 注）与 9 个历史遗留失败不在本 task073 收口范围内，已如实记录，不写成"已完成"。
