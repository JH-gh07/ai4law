# task073：DataComplyFlow Legal Agent 控制平面实施与验收方案

日期：2026-08-15  
依据：`status/todo/DataComplyFlow_LegalAgent架构升级_设计依据与架构决策_最终版.md`（V0.3）、`status/todo/DataComplyFlow_LegalAgent架构升级_实施设计与开发说明_最终版.md`（V0.3）、`docs/tmp/DataComplyFlow_LegalAgent架构升级_开发事实与可行性审查_V0.1.md`。  
状态：待实施；本文件是开发合同、证据清单、验收标准和回滚预案，不等同于已完成实现。

## 0. 目标与不可变约束

本任务在现有 Domain Workflow 上叠加轻量 Legal Agent Control Plane，首轮只实现两个 pilot：CN Transfer Diagnosis 和 CN Security Assessment。目标链路为：

```text
Existing Domain Workflow
  + Module Adapter
  + Fact / Rule / Evidence-Citation / Escalation Gates
  -> GateResult[] -> ControlDecision -> Domain Result / Trace / UI
```

不可变约束：

1. 所有控制逻辑 opt-in；未传 `control` 时，当前输出、事件顺序和异常语义保持不变。
2. 使用 `Reuse > Extend > Adapter > Insert > Replace`；不新建 Unified Runtime、Agent Graph、Central Workflow 或全量重写。
3. `task_status/state` 只表达程序执行；`legal_control_status` 只表达法律自动化可用程度，禁止互相映射为失败。
4. 所有新增 API 字段 optional/default-safe；不得给共享构造器增加 required 参数。
5. singleton service 不保存任何 per-run `ControlDecision`；状态只存在调用栈、返回对象或 trace。
6. Citation 资格必须 exact `SourceRegistry` lookup；title fuzzy matching、synthetic provider ID 均不得作为治理依据。
7. V1 不引入 LLM Judge、完整 Evidence Graph、semantic entailment 或新的前端 SSE event type。

## 1. 事实基线与证据登记

### 1.1 代码事实（可复核地址）

| 事实 | 证据地址 | 当前行为/风险 |
|---|---|---|
| Diagnosis 真实入口和 seam | `backend/domains/cn/transfer_diagnosis/service.py:42`、`:121`、`:138`、`:163` | `_resolve_answers`→Agents→`facts_from_module`→冲突校验→Rule Engine；default 分支仍可能进入 AI inference。 |
| Assessment 入口 | `backend/domains/cn/security_assessment/service.py:81` | `generate_report` 调用 `WorkflowPipeline.run`，结果由 `AssessmentResult` 返回。 |
| Assessment context pack | `backend/domains/cn/security_assessment/service.py:288` | ContextPack 内才同时有 facts/issues/evidence/legal grounding/CitationRegistry；Gate 过早插入会缺输入。 |
| Assessment final repair | `backend/domains/cn/security_assessment/service.py:398` 附近 | repair 可能改变最终章节，Citation final gate 必须在 repair 后、render 前。 |
| Citation 去重 | `backend/domains/cn/security_assessment/citation_builder.py:141-202` | 以 `(title, article_no)` 去重；当前只追加 issue 关系，fact/evidence union 不完整。 |
| 现有同名 GateResult | `backend/common/reporting/render_manifest.py:115-121` | 字段为 `name/status/diagnostics`，与 Legal Control 契约不同，禁止直接复用。 |
| Trace 可扩展 raw name | `backend/common/trace/recorder.py:145-181` | 未知名称落到标准 event type，并保留 `detail.raw_name`；可写 `control.*`，无需新 SSE union。 |
| Pipeline 共享调用者 | `backend/common/workflow/pipeline.py:24-188`；`backend/domains/eu/scc_review/service.py:302`；`backend/domains/us/eo14117/service.py:153` | 公共 hook 若改变默认签名/事件顺序会跨模块回归；首轮优先 Assessment-specific adapter。 |

模板证据不是抽象说明，按以下地址核验：

| 模板层 | 实际地址 | 使用链/边界 |
|---|---|---|
| 官方自评估结构文本 | `resources/templates/cn/official_risk_self_assessment_template.md` | `backend/common/knowledge/builders_v2.py:17` 建索引，`backend/domains/cn/security_assessment/external_report_generator.py:25` 与 `report_renderer.py:44` 读取；仅作为结构依据。 |
| 报告渲染模板 | `resources/templates/cn/2.2_risk_assessment_template_v0.docx`、同名 `.md` | `backend/domains/cn/security_assessment/report_renderer.py:40-41`；用于渲染/章节结构，不是法律依据。 |
| 法律资料快照 | `resources/legal/sources/cn/snapshots/cn-tpl-019_数据出境风险自评估报告模板_48ec6e2b.md` | Registry 中 canonical `source_id=CN-TPL-019`；资格与用途以 Registry 为准。 |
| 来源治理记录 | `resources/legal/registry/source_registry.v1.json:976`、`resources/legal/catalog/sources.csv:24` | 明示 `doc_type=template`、`allowed_usage/用途=结构参照`；不得提升为实体法依据。 |
| 模板检索入口 | `backend/domains/cn/security_assessment/service.py:309-326` | `module=cn_assessment/task_stage=report_generation/path=assessment`；Gate 应验证来源身份和允许用途。 |

模板验核命令：

```bash
test -f resources/templates/cn/official_risk_self_assessment_template.md
test -f resources/templates/cn/2.2_risk_assessment_template_v0.docx
rg -n 'CN-TPL-019|allowed_usage|can_enter_external_report' resources/legal/registry resources/legal/catalog
./.venv/bin/pytest -q backend/core/tests/test_resource_paths.py backend/domains/cn/security_assessment/tests/test_generation_basis.py
```

### 1.2 运行数据与现状样例

基线命令（必须在 `.venv` 中运行，系统 pytest 可能因 site-package 编码启动错误失败）：

```bash
./.venv/bin/pytest -q backend/tests/harness
./.venv/bin/pytest -q backend/domains/cn/transfer_diagnosis/tests backend/domains/cn/security_assessment/tests
git diff --check
```

当前工作树审查记录：Level A 输入 50/50 非空；Level B 转换 `converted=2`、`rejected=36`、`pending_correction=12`、`gap=0`；定向 harness 28 passed；backend/tests/harness 合计 89 passed（以执行时输出为准，提交前必须重新运行并把完整输出写入交付记录）。

事实保真反例（必须作为 Gate fixture）：

源文件 `benchmarks/datasets/seed-cases-v1/inputs/task07_case1.input.json` 明确包含健康、基因、特殊类别数据、未成年人、50 万影像/年、10 年留存和 GDPR 第 6/9/22 条依据；当前派生 `benchmarks/datasets/seed-cases-v1/requests/task07_case1.request.json` 却为 `data_categories: []`、`special_category_data: false`、`lawful_basis: []`、`retention_period: ""`。这证明“schema-valid ≠ source-faithful”，G1 必须能识别空值/默认值掩盖的关键事实缺失，不能只做 JSON Schema 校验。

另一个可复核问题：`scripts/build_seed_case_requests.py` 的 `_parse_count()` 在 `<1万` 前缀存在时可能拒绝同段落中的精确 `5000`；`_parse_ynu()` 先做正向子串匹配，`不属于CIIO`、`不含敏感信息` 可能被误判为肯定。以上解析器证据不能被 Gate 当作用户确认事实，必须记录 provenance 并进入 clarification/review。

### 1.3 证据登记规则

每项实现证据登记四元组：`事实/断言`、`代码或运行输出地址`、`复现命令`、`结论边界`。禁止只引用模板文字而无运行证据；禁止把工作树未提交修改写成基线。所有路径在交付前由 `test -f` 或 `rg` 复核。

## 2. 根因链路（问题→机制→修复点→验证）

| 问题 | 根因机制 | 修复点 | 验证 |
|---|---|---|---|
| 关键事实被默认值吞掉 | 解析/适配器只抽取少数字段；schema 默认值与“未知”语义混同 | G1 使用 `missing_facts`、`field_provenance`、源字段覆盖率和冲突结果 | 缺失、LLM/estimate/default、冲突三类 fixture 均得到预期状态 |
| 确定性路径可能被概率性说明改写 | Rule Engine 结果与 explanation 没有统一 precedence contract | non-default `RuleMatch` 锁定 canonical path；explanation 只读 | 断言 `recommended_path == expected_path`，注入改写尝试仍保持原路径 |
| Evidence Gate 放错生命周期 | ContextPack 前缺 legal grounding/CitationRegistry，无法判断支持关系 | `_build_context_pack` 完成后、generation 前执行 E1-E5 | Gate details 可列 issue 支持状态，旧 pipeline 默认不触发 |
| Citation 看似存在但来源不可治理 | fallback/synthetic ID 无 Registry 身份；fuzzy title 不是稳定 join | `registry_source_id` additive + exact Registry lookup + fail-closed | unregistered、`can_be_cited=false`、外部不可用来源均不得 PASS |
| 去重导致 trace 关系丢失 | `(title, article_no)` first/highest-confidence merge 只合并 issue | citation builder 对 issue/fact/evidence 做集合 union | 重复 binding fixture 断言三类关系不丢 |
| 法律需复核被错误当作程序失败 | 只有 `state` 的旧模型承载两种语义 | Domain Result 增 `ControlDecision`，保留 `task_status=COMPLETED` | NEEDS_REVIEW + COMPLETED 组合测试 |
| 前端无法解释控制原因 | trace 仅按标准 event type 显示，未知 raw name 默认 Task | 保留 `intermediate/warning`，增加 `control.*` raw-name 映射和结果状态读取 | Transcript/UI fixture 检查四类 Gate 可见 |
| 方案/代码/种子证据漂移 | manifest、gap ledger、任务文档未同步 | FACT refresh、provenance lint、文档交叉引用检查 | 交付前扫描差异并记录 Designed/Implemented/Difference/Reason |

## 3. 目标契约（先冻结再编码）

### 3.1 独立命名空间，解决同名冲突

新增建议文件：`backend/common/legal_control/contracts.py`（或等价模块）。名称必须带 Legal Control 语义，例如 `LegalControlGateResult`、`LegalControlDecision`；不得从 `render_manifest.GateResult` 直接导入。若最终选择别名，必须有类型测试证明序列化字段互不污染。

```python
class LegalControlGateResult(BaseModel):
    gate: Literal["FACT_COMPLETENESS", "RULE_PRECEDENCE", "EVIDENCE_SUFFICIENCY", "CITATION_VALIDITY", "ESCALATION"]
    outcome: Literal["PASS", "CONDITIONAL", "ESCALATE", "BLOCK"]
    reasons: list[str] = Field(default_factory=list)
    refs: list[str] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)

class LegalControlDecision(BaseModel):
    legal_control_status: Literal["AUTO", "CONDITIONAL", "NEEDS_CLARIFICATION", "NEEDS_REVIEW", "BLOCKED"] = "AUTO"
    gate_results: list[LegalControlGateResult] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)
```

### 3.2 优先级与状态合并

Gate 状态合并采用显式优先级：`BLOCKED > NEEDS_REVIEW > NEEDS_CLARIFICATION > CONDITIONAL > AUTO`；但 G1 critical missing 固定映射 `NEEDS_CLARIFICATION`，既有冲突和决定性推断固定至少 `NEEDS_REVIEW`。不得用字典迭代顺序或最后写入值决定状态。

### 3.3 API 与 trace

DiagnosisResult/AssessmentResult 只追加：`control_decision: LegalControlDecision | None = None`、必要时 `clarification_questions: list[...] = []`。control 未启用时序列化可省略或为 `null`，旧 consumer 仍可解析。Trace 写入 `control.fact_completeness`、`control.rule_precedence`、`control.evidence_sufficiency`、`control.citation_validity`、`control.escalation`；正常/pass 用 `intermediate`，review/limitation 用 `warning`，保持原 event union。

## 4. 分阶段实施（含文件、动作、出口条件）

### Phase 0：工作树、基线和契约冻结

动作：记录 `git rev-parse HEAD`、`git status --short`、Python/pytest 版本；运行第 1.2 节命令；建立 `docs/tmp/task073-evidence/`（如项目约定允许）保存 stdout、JSON fixture 和 trace 样本。不要清理或回滚用户未提交修改。

出口：基线测试可重复；所有引用文件存在；`GateResult` 同名冲突已登记；默认关闭行为快照完成。

### Phase 1：Core Contract + aggregation（T01）

动作：实现独立契约、状态优先级、`required_actions` 常量；为 DiagnosisResult/AssessmentResult 增加 additive 字段；编写空决策、单 Gate、多 Gate 合并及旧 JSON 反序列化测试。

出口：契约单测通过；未启用 control 的旧 fixture 字节/字段兼容；`render_manifest.GateResult` 测试无变化。

### Phase 2：Trace integration（T02）

动作：复用 `TraceRecorder.record`，新增 raw names；适配 `frontend/src/lib/trace-adapter.ts` 语义标签。不得扩展 SSE event union；为每个控制事件写 `gate/outcome/reasons/refs` 摘要，不写敏感正文。

出口：同步/异步 trace 均有 seq、task_id、raw_name；既有 status/intermediate/warning 顺序不变；未知控制事件仍可回放。

### Phase 3：CN Transfer Diagnosis（T03-T05）

动作：

1. `DiagnosisService.evaluate(..., control=None)` 保持 Assessment 现有调用不传参数。
2. Agents 与 `facts_from_module` 后执行 G1；critical missing 生成固定 clarification question；冲突保留既有 manual-review result 并附 G1。
3. Rule Engine 后执行 G2：non-default 锁定 path；default 保留 AI inference，不打 deterministic 标签。
4. 在返回前执行 G4，按固定优先级合并；每次结果写控制 trace。
5. 记录 field provenance：用户输入、确定性规则、`LLM_INFERENCE`、`ESTIMATE`、`DEFAULT`，禁止把模型输出伪装为 user fact。

建议文件：`backend/domains/cn/transfer_diagnosis/control_adapter.py`、`service.py`（最小 seam）、`schema.py`、对应 tests；如公共契约放 elsewhere，更新 API schema/OpenAPI。

出口：D1-D6 全部通过；Assessment 内部 diagnosis 默认行为回归通过；控制开关关闭时结果和 trace 与基线一致。

### Phase 4：Assessment canonical identity（T06-A，最高风险前置）

动作：

1. 核对 `SourceRegistryEntry`、`KnowledgeChunkV2`、`CitationItem` 的 source_id 链；必要时给 CitationItem 增 `registry_source_id: str | None = None`。
2. 实现 exact membership 查询；未注册 fallback/DeliLegal 返回 `UNREGISTERED`，不得 fuzzy 提升。
3. 修改 `build_citations` 的 duplicate merge，对 `related_issue_ids/fact_ids/evidence_ids` 做 set-union，并保持最高置信度字段策略可解释。
4. 对 `review_status`、`can_be_cited`、`can_enter_external_report`、`allowed_usage` 采用 fail-closed；从 Registry 读取权威值，不复制到 chunk 形成第二真相源。

出口：local registered、unregistered、ineligible 三类 fixture；重复 citation 关系 union 测试；EU SCC/US14117/CN Flow 公共链无行为变化。

### Phase 5：Assessment Evidence Gate（T06-B/T07）

插入：`_build_context_pack` 返回后、`generate_chapters` 前；首轮以 Assessment-specific adapter 传递 gate，公共 `WorkflowPipeline` 不改默认行为。

实现 E1-E5：核心 Issue 的 fact/rule/evidence 引用完整性、法律依据存在性、外部积极事实可支持性、单一低置信支持、既有 consistency dangling refs。`document_refs=[]` 只生成 `DOCUMENT_TRACE_GAP` limitation，不直接 BLOCK。

出口：supported→PASS、core partial→CONDITIONAL、core unsupported→ESCALATE；Gate details 列出 issue 支持矩阵和 refs。

### Phase 6：Citation Validity + Assessment Escalation（T08）

插入：`generate → consistency → alignment → repair → Citation Validity → Escalation → render`。C1 精确解析最终 marker；C2 exact Registry eligibility；C3 issue/fact/evidence traceability。只有核心全部满足才 AUTO；非核心 limitation 可 CONDITIONAL；核心不满足 NEEDS_REVIEW。`BLOCKED` 保留契约，pilot 不主动触发。

出口：render 前 gate 可阻止“正式已核验”标签，但不把 `task_status` 改为 FAILED；内部报告可输出但 UI 必须显示复核提示。

### Phase 7：Frontend 与 API（T09）

动作：在 `ModuleRunPanel` 保留现有未提交修改基础上，读取 `legal_control_status/control_reasons/required_actions/clarification_questions`；`NEEDS_CLARIFICATION` 显示缺失事实，`NEEDS_REVIEW` 显示人工复核提示，Assessment `CONDITIONAL` 显示条件结论。更新生成 types/OpenAPI，不复用 `state/asyncState`。

出口：桌面和窄屏 UI 无重复入口；结果和 trace 均能看到控制状态；旧 response 无控制字段时不崩溃。

### Phase 8：全量回归、FACT refresh 和发布（T10）

必须覆盖 Diagnosis evaluate/report/harness、Assessment sync/async/evidence/citation/consistency/renderer、EU SCC、US14117、CN Flow、common citation、WorkflowPipeline、V0 Task Gateway。重新扫描 HEAD、工作树和所有设计引用，输出 Designed/Implemented/Difference/Reason/Impact 表。

## 5. 验证矩阵（可直接执行）

### 5.1 Diagnosis

| 场景 | 输入/fixture | 预期 |
|---|---|---|
| 完整 non-default | `backend/domains/cn/transfer_diagnosis/tests/test_rule_engine.py` + service fixture | task 成功、AUTO、path 不变 |
| critical missing | q2/q5 等 unknown 且 Agent 未补齐 | NEEDS_CLARIFICATION、问题非空、不输出无条件最终路径 |
| 既有冲突 | `_validate_fact_consistency` 冲突 fixture | 原 manual-review 保留 + NEEDS_REVIEW |
| decisive inference | provenance 为 LLM_INFERENCE/ESTIMATE/DEFAULT | 至少 NEEDS_REVIEW |
| default→AI | `_needs_ai_inference` 为真 | execution_precedence=false、不得标 deterministic |
| Assessment reuse | `backend/domains/cn/security_assessment/tests` | 未传 control 时结果/trace 不变 |

### 5.2 Assessment

| 场景 | 证据 | 预期 |
|---|---|---|
| context seam | `service.py:288` | Evidence Gate 在 pack 完成后运行 |
| source exact match | local SourceRegistry fixture | C2 PASS |
| fallback/unregistered | synthetic/DeliLegal fixture | UNREGISTERED，核心依赖 NEEDS_REVIEW |
| ineligible | `can_be_cited=false` 或 external=false | 不得作为正式通过 citation |
| duplicate merge | `test_citation_builder.py` duplicate fixture | issue/fact/evidence 三类集合 union |
| final marker missing | final chapter marker 无 registry item | C1 MISSING，render 前 NEEDS_REVIEW |
| repair changed citation | repair fixture | gate 看到 repair 后最终章节 |
| legal/runtime 分离 | 正常生成但控制不足 | `task_status=COMPLETED` + `NEEDS_REVIEW` |

### 5.3 Trace/UI/API

断言每个 `control.*` 事件具备 `task_id/seq/raw_name/gate/outcome`；旧事件顺序和 event type 不变；旧 JSON response 可被新模型读取；控制字段缺失时前端采用默认隐藏而非报错。

## 6. 安全、数据和可观测性控制

- trace 只记录事实键、状态和证据 ID，不记录患者/员工原文、完整健康数据或模型提示词。
- `refs` 只能引用稳定 ID/路径，不接受未经清洗的任意文件路径或用户可执行内容。
- Gate 失败原因需可审计但不可泄露敏感 payload；日志使用 task_id/correlation_id。
- 控制开关必须配置白名单（pilot/module），默认关闭；禁止全局 singleton flag。
- 同一 run 的 GateResult 不得跨请求复用；并发测试验证互不串状态。

## 7. 发布、回滚与故障处理

发布顺序：契约和 trace（无业务行为）→ Diagnosis pilot 灰度→ Assessment identity/evidence/citation 灰度→ UI 展示。每阶段保留开关和旧路径。

回滚条件：默认路径测试失败、跨模块 trace 顺序改变、出现未授权正式 citation、控制状态串请求、任何 PII 泄露。回滚只关闭 pilot flag/adapter，不删除历史 trace，不回滚用户未提交文件。

故障降级：Gate adapter 异常时记录 `control.escalation` 和 `NEEDS_REVIEW`，不得静默 PASS；若控制模块不可用且 opt-in 请求明确要求 fail-closed，则返回可审计错误，但仍保持 `task_status` 与法律状态分离。

## 8. 交付物与“设计—实现差异”记录

每个 T01-T10 交付：文件/类/方法、复用点、新增点、测试命令及输出、回归范围、设计差异。差异模板：

```text
Designed:
Implemented:
Difference:
Reason:
Architecture impact:
Evidence:
```

不得以“schema 通过”替代源事实保真；不得以“报告成功渲染”替代 Citation Gate 通过。

## 9. 最终验收门槛

只有同时满足以下条件才可将 task073 标记完成：

1. T01-T10 的出口条件均有测试或运行证据；关键路径至少一正一负 fixture。
2. Diagnosis 六项验收、Assessment 十项验收全部通过。
3. 默认关闭回归证明 Assessment、EU SCC、US14117、CN Flow、V0 Gateway 无行为变化。
4. 同名 `GateResult` 契约隔离已由类型/序列化测试证明。
5. SourceRegistry exact lookup、fallback fail-closed、citation relation union 均有测试。
6. UI/API/Trace 可解释 `AUTO/CONDITIONAL/NEEDS_CLARIFICATION/NEEDS_REVIEW`，且不混用 task state。
7. 重新生成 FACT，更新所有受影响文档和证据地址；`git diff --check` 清洁。
8. 未声明的漏洞、未复现的运行数字或无路径证据的结论不得写成“已完成”。

## 10. 明确非目标与升级触发器

非目标：11 模块迁移、Unified Runtime、完整 Evidence Closure、语义 Citation Judge、完整 HITL pause/resume、框架迁移、benchmark 重设计。

以下任一情况必须暂停编码并进行架构复审：无法保持 Diagnosis opt-in；必须修改公共 WorkflowPipeline 默认行为；无法建立 canonical source identity；Eligibility 只能 fuzzy；必须引入 LLM Judge；必须把 legal status 写入 task state；出现跨模块不可隔离回归；或发现源事实保真要求超出当前适配器能力。

## 11. 复核签字栏

- [ ] 开发：已按 T01-T10 提交代码、测试和差异记录
- [ ] 后端复核：已核对运行输出、trace、SourceRegistry 和并发隔离
- [ ] 前端复核：已核对结果状态、复核提示和旧响应兼容
- [ ] 数据/法律复核：已核对关键事实 provenance、证据和引用资格
- [ ] 发布复核：已完成灰度、回滚演练和 FACT refresh
