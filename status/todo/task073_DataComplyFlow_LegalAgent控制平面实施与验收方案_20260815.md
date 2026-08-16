# task073：DataComplyFlow Legal Agent 控制平面落实情况与剩余验收方案（重生成版）

重生成日期：2026-08-16

原任务日期：2026-08-15

核对基准：提交 `2df778bf` + 2026-08-16 当前未提交工作树

设计依据：

- `status/todo/DataComplyFlow_LegalAgent架构升级_设计依据与架构决策_最终版.md`（V0.3）
- `status/todo/DataComplyFlow_LegalAgent架构升级_实施设计与开发说明_最终版.md`（V0.3）
- `status/view/20260815_LegalAgent控制平面实施FACT刷新与差异记录.md`

文档定位：本文件是基于代码、测试、提交记录和当前工作树重新生成的独立落实报告与收尾验收合同。它替代 task073 原稿作为当前执行口径，不把“代码存在”“测试通过”“已提交”“业务验收”“生产发布”混写成一个“完成”。

## 0. 结论先行

当前准确裁决为：

> **IMPLEMENTED_IN_WORKTREE / TECHNICALLY_VALIDATED / NOT_COMMITTED / ACCEPTANCE_PENDING / NOT_RELEASED**

换成中文：两个 pilot 的核心控制平面已经在当前工作树中实现，针对性技术验证通过；但关键收尾修复尚未提交，数据/法律责任人尚未签字，生产灰度和回滚演练尚无证据，因此 task073 不能标记为“全部完成”或“已发布”。

| 维度 | 当前状态 | 判定依据 |
|---|---|---|
| 架构设计 | `FINAL` | V0.3 已冻结 D01-D18 和两个 pilot 边界 |
| 核心门禁代码 | `COMMITTED` | `9d021b97`、`124e6852` |
| 前端控制状态展示 | `COMMITTED` | `464c5b1a` |
| 产品入口显式 opt-in | `IMPLEMENTED_IN_WORKTREE` | Diagnosis/Assessment 请求 `control=false` 默认值及前端 `control:true` 尚未提交 |
| Citation/升级门正确生命周期 | `IMPLEMENTED_IN_WORKTREE` | `WorkflowPipeline.before_render` 和 Assessment 接入尚未提交 |
| 技术验证 | `PASSED_WITH_KNOWN_BASELINE_FAILURES` | task073 组合回归 378 passed；另有 EU SCC 1 个、Harness 3 个既有失败 |
| 数据/法律验收 | `PENDING` | 无责任人签字记录 |
| 灰度与回滚 | `PENDING` | 无生产灰度记录和回滚演练证据 |
| 生产状态 | `NOT_RELEASED` | 不得以本地测试代替发布证据 |

### 0.1 已经真正落实的内容

1. 已建立独立 Legal Control 契约、状态优先级和 `required_actions`，没有复用 Reporting 同名 `GateResult`。
2. CN Transfer Diagnosis 已接入事实完整性、确定性规则优先级和控制决策聚合。
3. CN Security Assessment 已接入 Evidence Sufficiency、Citation Validity 和 Escalation。
4. Citation 已使用 exact `SourceRegistry` identity，未注册或不合格来源 fail-closed，不使用 title fuzzy join 作为治理身份。
5. `legal_control_status` 与程序 `state/task_status` 分离，允许 `COMPLETED + NEEDS_REVIEW`。
6. Trace 使用 `control.*` raw name，未扩展既有 SSE event type；前端可显示复核、补充事实和条件结论。
7. 当前工作树已补齐两个 pilot 的请求开关、前端显式启用以及 repair 后、render 前门禁时序。

### 0.2 尚未落实或尚未闭环的内容

1. 2026-08-16 的关键收尾代码仍在未提交工作树，HEAD `2df778bf` 本身不是完整可发布实现。
2. `POST /diagnosis/report` 已有 `control` 请求字段，但 `POST /diagnosis/evaluate` 仍接收裸 `DiagnosisAnswers`，没有 API 级 opt-in；必须明确“只支持报告入口”或补齐该端点。
3. Assessment 虽会随完整 payload 继承 async `control`，但尚缺一条 `control=true` 的异步端到端断言。
4. 当前未重新执行全仓测试；历史全量结果 `1295 passed / 9 failed` 只能作为历史基线，不能冒充本轮结果。
5. EU SCC 仍有 1 个历史引用标签失败，Harness 仍有 3 个案例清单/前端库存漂移失败；虽非 task073 引入，但发布验收必须有修复或书面豁免。
6. 数据/法律签字、灰度观察、回滚演练和最终发布签字均未完成。

## 1. 范围与验收边界

本轮只验收两个 pilot：

- Pilot A：CN Transfer Diagnosis
- Pilot B：CN Security Assessment

本轮不包含 11 模块全面迁移、Unified Runtime、完整 Evidence Graph、语义 entailment verifier、LLM Citation Judge、完整 HITL pause/resume runtime 或 Reporting 重写。未做这些事项不算 task073 缺陷；把未列入范围的能力宣传成已具备则属于验收失败。

必须持续满足以下硬边界：

1. `control` 默认关闭；旧调用方不传控制字段时保持原行为。
2. 所有共享模型变更 additive/default-safe。
3. per-run `ControlDecision` 不进入 singleton service 状态。
4. non-default RuleMatch 才能锁定 deterministic path；default 分支保留 AI inference 语义。
5. Evidence Gate 位于 ContextPack 完成后、生成前。
6. Citation Validity 和 Escalation 位于 repair 后、manifest/render 前。
7. Citation eligibility 只认 exact SourceRegistry lookup。
8. `NEEDS_REVIEW`、`NEEDS_CLARIFICATION` 不得映射为程序 `FAILED`。

## 2. T01-T10 落实矩阵

状态含义：`DONE` 表示已提交且有证据；`DONE_IN_WORKTREE` 表示当前代码已实现并验证但尚未提交；`PARTIAL` 表示主链成立但验收面仍有缺口；`PENDING` 表示尚无完成证据。

| Task | 原定目标 | 实际落实 | 状态 | 剩余动作 |
|---|---|---|---|---|
| T01 Core Contract | GateResult、ControlDecision、状态与动作 | `backend/common/legal_control/contracts.py` 已实现独立契约、显式优先级和兼容默认值 | `DONE` | 无 |
| T02 Trace | `control.*`，不新增 SSE type | `backend/common/legal_control/trace.py`、前端 trace adapter 已接入；PASS/CONDITIONAL→intermediate，ESCALATE/BLOCK→warning | `DONE` | 收尾 trace 测试随工作树提交 |
| T03 Diagnosis Fact | Agents→facts→validation 后执行 G1 | `control_adapter.py` + `service.py` 已处理 critical missing、冲突和固定澄清问题 | `DONE` | 无 |
| T04 Rule Precedence | non-default 锁定；default 保留 AI | 已区分 `execution_precedence`，推断/估算/默认决定性事实至少 NEEDS_REVIEW | `DONE` | 无 |
| T05 Diagnosis API | 形成 Pilot A API 闭环 | service/result 契约已提交；`/report` 请求开关在工作树；`/evaluate` 无请求级开关 | `PARTIAL` | 决定并补齐 `/evaluate`，或书面限定 report-only |
| T06 Canonical Identity | exact Registry、关系 union、fallback fail-closed | resolver、`registry_source_id`、三类关系 union 已提交；模板用途纠偏在工作树 | `DONE_IN_WORKTREE` | 提交 Registry 生成逻辑、测试与缓存 |
| T07 Evidence Gate | ContextPack 后、generation 前执行 E1-E5 | `evidence_gate.py` 已按真实字段运行；`document_refs=[]` 仅记 limitation | `DONE` | 无 |
| T08 Citation + Escalation | repair 后、render 前形成 Pilot B | 门本体已提交；正确 `before_render` 生命周期和请求开关在工作树 | `DONE_IN_WORKTREE` | 提交 seam；补 async control=true 验收 |
| T09 Frontend | 状态、澄清、复核、trace 可见 | UI 展示已提交；两个 pilot builder 的 `control:true` 在工作树 | `DONE_IN_WORKTREE` | 分离无关前端改动后提交 |
| T10 Regression + FACT | 全链回归、差异登记、发布前收口 | FACT 已有；本轮组合验证完成，但全仓未重跑且存在已知基线失败 | `PARTIAL` | 完成收尾提交、失败豁免/修复、灰度和回滚证据 |

## 3. 当前真实运行链

### 3.1 Pilot A：CN Transfer Diagnosis

```text
POST /diagnosis/report { control: true }
  → DiagnosisService.evaluate(..., control=True)
  → _resolve_answers
  → ImportantData / PIClassify / Exemption Agents
  → facts_from_module + provenance + missing_facts
  → existing fact conflict validation
  → FACT_COMPLETENESS
  → DiagnosisRuleEngine.evaluate
  → RULE_PRECEDENCE
  → existing rule/default/AI result
  → merge LegalControlDecision
  → control.* trace
  → report result / frontend control panel
```

控制关闭时 `control_decision=None`、`clarification_questions=[]`。Assessment 内部复用 Diagnosis 时仍不传 control，因此不会把 Pilot A 门禁隐式扩散到 Assessment 内部诊断。

已知入口差距：`POST /diagnosis/evaluate` 当前直接调用 `service.evaluate(answers)`，没有传递 `control`。这不是代码门禁缺失，而是 API 可达面未完全统一。

### 3.2 Pilot B：CN Security Assessment

```text
AssessmentRequest { control: true }
  → profile / diagnosis / facts / issues / evidence
  → _build_context_pack
  → exact SourceRegistry identity + CitationRegistry
  → EVIDENCE_SUFFICIENCY
  → chapter generation
  → consistency / alignment / repair
  → WorkflowPipeline.before_render
       → CITATION_VALIDITY
       → ESCALATION
  → trace manifest
  → render artifacts
  → merge LegalControlDecision
  → result / frontend control panel
```

`before_render` 默认 `None`，只有 Assessment 在 `control=true` 时传入 `_run_control_gates`。EU SCC、US EO 14117 等其他 WorkflowPipeline 调用方不会自动执行 Legal Control 门。

## 4. 代码与证据登记

| 能力 | 真实位置 | 证据边界 |
|---|---|---|
| Control contracts | `backend/common/legal_control/contracts.py` | 独立于 `render_manifest.GateResult` |
| Gate trace | `backend/common/legal_control/trace.py` | 只记录摘要和稳定 refs，不应写敏感正文 |
| Diagnosis adapter | `backend/domains/cn/transfer_diagnosis/control_adapter.py` | G1/G2 和决策聚合 |
| Diagnosis service seam | `backend/domains/cn/transfer_diagnosis/service.py` | `control` 为 per-call 参数 |
| Diagnosis report opt-in | `backend/domains/cn/transfer_diagnosis/schema.py`、`router.py` | 当前仅 report 请求闭环 |
| Source identity | `backend/common/citation/source_identity.py` | exact membership；无 fuzzy 提升 |
| Citation relation union | `backend/domains/cn/security_assessment/citation_builder.py` | issue/fact/evidence 关系集合合并 |
| Evidence Gate | `backend/domains/cn/security_assessment/evidence_gate.py` | ContextPack 后、generation 前 |
| Citation Gate | `backend/domains/cn/security_assessment/citation_validity_gate.py` | C1/C2/C3，只校验最终章节 |
| Escalation Gate | `backend/domains/cn/security_assessment/escalation_gate.py` | repair blocked 和剩余 blocking signal |
| Render 前 seam | `backend/common/workflow/pipeline.py` | 当前工作树新增，默认 `None` |
| Assessment orchestration | `backend/domains/cn/security_assessment/service.py` | `control=true` 才启用 resolver、三门和决策 |
| Request contract | `backend/domains/cn/security_assessment/schema.py` | `control: bool = False` |
| UI result mapping | `frontend/src/features/module-runner/model.ts` | 不复用 task state |
| Pilot request builders | `frontend/src/features/module-runner/payload-builders/cn.ts` | 当前工作树显式发送 `control:true` |
| Control UI | `frontend/src/components/workspace/ModuleRunPanel.tsx` | 显示 clarification/review/conditional |
| Registry policy | `backend/common/knowledge/registry.py`、`resources/legal/registry/source_registry.v1.json` | template 仅 `structure_control/internal_review` |

提交链：

| 提交 | 已提交内容 |
|---|---|
| `c444d081` | 实施前存档快照 |
| `9d021b97` | T01-T06-A：契约、trace、Diagnosis、canonical identity |
| `124e6852` | T06-B/T07/T08：Assessment 三门 |
| `464c5b1a` | T09：前端控制状态展示 |
| `2df778bf` | T10 初版 FACT 刷新 |

必须注意：API opt-in、render 前 seam、模板 Registry 纠偏及相应测试位于 `2df778bf` 之后的当前工作树，不能写成已经进入上述提交链。

## 5. 2026-08-16 实测记录

以下均为本次重新生成文档时实际执行的结果。

| 验证范围 | 命令摘要 | 实际结果 |
|---|---|---|
| task073 + knowledge 组合后端 | `pytest backend/common/legal_control backend/common/citation backend/common/knowledge/tests backend/domains/cn/security_assessment backend/domains/cn/transfer_diagnosis backend/common/workflow` | **378 passed，1 warning，249.59s** |
| US EO 14117 + CN Flow | `pytest backend/domains/us/eo14117/tests backend/domains/us/eo14117_flow_review/tests` | **42 passed，1 warning** |
| V0 Task Gateway | `pytest backend/api/v0/tests/test_task_gateway.py` | **7 passed，1 warning** |
| EU SCC | `pytest backend/domains/eu/scc_review/tests` | **25 passed / 1 failed** |
| Harness | `pytest backend/tests/harness` | **96 passed / 3 failed** |
| Frontend unit/component | `npx vitest run` | **206 passed / 2 skipped；33 files passed / 1 skipped** |
| Frontend types | `npx tsc -b` | **通过** |
| Registry drift | `python scripts/build_source_registry.py --check` | **120 entries；0 missing；0 field delta** |
| Patch hygiene | `git diff --check` | **通过** |

测试告警为 Starlette `TestClient`/httpx2 弃用提示，不是 task073 失败。

### 5.1 已知失败的准确归属

| 失败 | 本次结果 | 归属判断 | task073 处置 |
|---|---|---|---|
| EU SCC `test_uploaded_scc_document_drives_core_review` | citation display label 未包含 `2021/914` | 历史全量基线已有，task073 未修改该测试链 | 发布前修复或形成书面豁免 |
| Harness `test_committed_tree_passes_the_gate` | case catalog 28 vs frontend inventory 40 | Phase 0 已存在 | 由案例治理任务修复或豁免 |
| Harness `test_python_gate_reads_frontend_counts_from_structured_inventory` | 期望 28，实际 40 | Phase 0 已存在 | 同上 |
| Harness `test_case_catalog_has_unique_registered_cases_and_real_sources` | inventory 数量漂移 | Phase 0 已存在 | 同上 |

“不是 task073 引入”只说明回归归因，不等于“发布时可以忽略”。最终发布门必须记录 owner、修复提交或豁免人。

### 5.2 本次没有执行的验证

- 没有重新执行全仓 `.venv/bin/python -m pytest -q`。
- 没有执行真实生产环境外部服务联调。
- 没有执行生产灰度。
- 没有执行真实回滚演练。
- 没有取得数据或法律责任人签字。

历史 `1295 passed / 9 failed` 仅为 2026-08-15 基线，不作为本次实测结果。

## 6. 设计—实现差异与影响

| 项 | 设计 | 当前实现 | 差异原因 | 影响与结论 |
|---|---|---|---|---|
| Pipeline 改动 | 优先 Assessment-specific adapter，不改共享 Pipeline | 新增默认空 `before_render` seam，仅 Assessment control 模式启用 | run 返回后校验发生在 render 之后，无法满足 D08 | 差异合理且默认安全，但必须随收尾提交并保留共享调用方回归 |
| API opt-in | 两个 pilot 显式 opt-in | Assessment 和 Diagnosis report 已实现；Diagnosis evaluate 未实现 | 原前端主链走 report builder | 产品主链可用，但 API 契约不完整，需作明确决策 |
| Citation 时序 | repair 后、render 前 | 初版在 render 后；当前工作树已移到 before_render | 初版生命周期 seam 不足 | 当前实现符合 D08，HEAD 单独检出仍不符合 |
| Template 身份 | 模板只用于结构控制 | 当前工作树把 template 统一为不可引用、不可进外部报告、仅 structure/internal | 原 Registry 结构化字段与 metadata 口径冲突 | 数据口径已技术纠偏，仍需法律/数据签字 |
| BLOCK/BLOCKED | 契约保留，pilot 不要求触发 | 无主动 BLOCK 路径 | V1 采用警告/人工复核而非硬阻断 | 符合 D14，不得宣传为完整硬阻断运行时 |
| 模块范围 | 两个 pilot | 未迁移其余模块 | 遵守非目标和 Pilot Isolation | 符合设计 |

## 7. 剩余工作包

### P0-1：形成可审查的收尾提交

目标：把 task073 相关工作从当前混合工作树中分离，形成可复核提交；不得把 task075、CPRA、运行产物清理等无关修改混入。

至少包含：

- `backend/common/workflow/pipeline.py`
- `backend/domains/cn/security_assessment/{schema.py,service.py,tests/test_control_service.py}`
- `backend/domains/cn/transfer_diagnosis/{schema.py,router.py,tests/test_api.py}`
- `backend/common/knowledge/{registry.py,tests/test_registry.py}`
- `resources/legal/registry/source_registry.v1.json`
- `frontend/src/features/module-runner/payload-builders/cn.ts` 及其测试
- task073 的 OpenAPI、model、trace 相关测试增量
- 本文与最终 FACT

出口条件：提交 diff 只包含 task073 相关 hunk；从该提交新检出后可重复第 5 节验证。

### P0-2：关闭 API 可达性缺口

二选一并记录决策：

1. 为 `/diagnosis/evaluate` 增加带 `control: bool = false` 的兼容请求契约；或
2. 明确 V1 Control Plane 只对 `/diagnosis/report` 和前端报告主链提供，`/evaluate` 保持 legacy endpoint。

出口条件：API 测试覆盖默认关闭和显式开启，OpenAPI 与前端类型同步。

### P0-3：补齐异步控制验收

新增 Assessment `control=true` async 测试，至少断言：

- submit 后最终状态可完成；
- result 存在 `control_decision`；
- 三个 Assessment gate 均存在；
- Citation/Escalation 在 render 前执行；
- `NEEDS_REVIEW` 不把 task state 改为 FAILED。

### P0-4：数据/法律签字

责任人应核对：

- critical fact 与 provenance 范围；
- exact Registry identity 和 eligibility；
- template 仅用于 `structure_control/internal_review`；
- Citation/Evidence 不足时的文案、人工复核动作和对外报告限制；
- `BLOCKED` 在 V1 不主动触发的产品含义。

出口条件：签字人、日期、意见和例外项写入第 9 节，不接受口头“看过”。

### P0-5：基线失败处置

为 EU SCC 1 个失败和 Harness 3 个失败分别记录：owner、关联 issue、计划修复时间、是否阻断 task073 发布。若不修复，必须由发布责任人书面接受风险。

### P0-6：灰度与回滚演练

灰度顺序：

1. 后端 schema/契约上线但保持 `control=false`；
2. 仅对白名单 pilot 请求开启；
3. 观察 AUTO/CONDITIONAL/NEEDS_CLARIFICATION/NEEDS_REVIEW 分布及错误率；
4. 前端开启控制面板；
5. 扩大白名单前复核 trace 和人工处理量。

回滚动作：前端停止发送 `control:true` 即可恢复默认关闭；如需代码回滚，再撤销 Assessment `before_render` 接入，公共 Pipeline 的默认 `None` 不要求其他模块迁移。

出口条件：保存灰度批次、样本 task_id、指标、异常、回滚步骤、演练结果和责任人。

## 8. 最终验收门

### 8.1 技术实现门

- [x] 独立 Legal Control contracts 和显式状态优先级
- [x] Diagnosis G1/G2 与 per-run decision
- [x] Assessment Evidence/Citation/Escalation
- [x] exact SourceRegistry identity 和 citation relation union
- [x] legal control status 与 task state 分离
- [x] Trace/UI 可解释控制状态
- [x] 当前组合回归、前端测试、类型检查和 Registry 零漂移通过
- [ ] task073 收尾改动已形成独立提交
- [ ] `/diagnosis/evaluate` 的 V1 边界已决定并测试
- [ ] Assessment async `control=true` 已有端到端测试

### 8.2 业务与法律门

- [ ] 数据责任人核对 critical fact、provenance 和 Registry 数据
- [ ] 法律责任人核对 Gate policy、引用资格和对外文案
- [ ] 人工复核动作有明确 owner、SLA 和处理入口
- [ ] 已知基线失败已有修复或书面豁免

### 8.3 发布门

- [ ] 从收尾提交的新检出环境复跑验收命令
- [ ] 白名单灰度完成并记录样本
- [ ] 回滚演练成功
- [ ] FACT 更新为最终提交哈希和实际发布状态
- [ ] 发布责任人签字

只有三组门全部完成后，状态才允许从：

```text
IMPLEMENTED_IN_WORKTREE
TECHNICALLY_VALIDATED
ACCEPTANCE_PENDING
NOT_RELEASED
```

更新为：

```text
IMPLEMENTED
VALIDATED
ACCEPTED
RELEASED
```

## 9. 签字与最终记录

| 角色 | 当前结论 | 姓名/日期 | 备注 |
|---|---|---|---|
| 开发 | 技术实现已在工作树完成并验证；待独立提交 | 待填 | 378 backend + 206 frontend passed |
| 后端复核 | 待收尾提交后复核 | 待填 | 重点核对 before_render、async、默认关闭 |
| 前端复核 | 待收尾提交后复核 | 待填 | 重点核对请求 opt-in、旧响应兼容和提示文案 |
| 数据责任人 | 未验收 | 待填 | Registry/template/provenance |
| 法律责任人 | 未验收 | 待填 | Gate policy、引用资格、对外限制 |
| 发布责任人 | 未验收 | 待填 | 灰度、已知失败豁免、回滚 |

最终判定：task073 的“代码建设”已基本落实，“可发布收口”尚未落实。下一步不是继续扩写设计文档，而是完成收尾提交、API/async 两个验收缺口、责任人签字和灰度回滚证据。
