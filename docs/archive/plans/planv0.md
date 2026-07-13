# 一、总体改造原则

当前系统不是推倒重写，而应采用 **“以 assessment 为主链路，先打通一条真实中间产物流水线，再扩散到其他模块”** 的方式。

原因很简单：

| 方案                  | 风险                                                          |
| ------------------- | ----------------------------------------------------------- |
| 一次性统一所有模块           | 容易大改崩坏，且 Codex 会用抽象接口假装统一                                   |
| 每个模块各改一点            | 会继续分散，不能形成统一架构                                              |
| 先改 assessment 为标准链路 | 最稳，因为 assessment 已有诊断、RAG、章节生成、渲染、trace_manifest，是最接近主链路的模块 |

所以改造路线应是：

```text
阶段 0：冻结当前真实链路，建立基线测试
阶段 1：定义统一中间产物 schema
阶段 2：在 assessment 中真实生成 facts
阶段 3：在 assessment 中真实生成 issue_list
阶段 4：让 issue_list 真正驱动 RAG / prompt / report
阶段 5：落地 evidence_chain
阶段 6：扩展 consistency_checker
阶段 7：输出中间产物附件
阶段 8：前端展示中间产物，避免只在后端“悄悄生成”
阶段 9：抽象可复用 WorkflowPipeline
阶段 10：复用到 cn_flow / cpra / bcr / scc / dpia / tia
```

> 执行边界：第一轮只执行 Phase 0–4。Phase 5 及以后必须等 `GenerationContextPack`
> 已经真实进入 LLM prompt 且有测试证明后再继续，避免“生成了但没用”的假落实。

## 全局实现约定

- 当前计划按现有 `AssessmentRequest` 字段落地，不在 Phase 0–4 修改请求 schema。
- 当前字段名必须使用：
  - `contains_important_data`
  - `pii_count`
  - `spi_count`
  - `receiver_country`
  - `uploaded_files`
- `contains_important_data` 当前是 `bool`，Phase 0–4 不实现 unknown/None 规则；如需支持“未知”，另开三态 schema 兼容迁移。
- `rule_refs` 统一使用稳定 ID：
  - RAG 法规引用使用 `RegulationHit.source_id`。
  - 诊断规则引用使用 `diagnosis:{matched_rule_id}`；无 `matched_rule_id` 时使用 `diagnosis:{recommended_path}`。
  - 仅用于展示时再拼 `title + article`，不得把展示文本作为内部引用主键。
- `trace_manifest.json` 只负责索引 trace event 文件；中间产物写入独立 event payload，不要求 manifest 内联大对象。
- `IssueItem.evidence_refs` 在 evidence 生成后回填；不得在 Phase 3 假填不存在的 evidence ID。

---

# 二、阶段 0：建立当前代码基线，防止越改越乱

## 目标

先确认当前系统真实做了什么，并写成测试。否则后面 Codex 改完，你不知道它是增强了，还是把原有功能破坏了。

## Codex 任务清单

```markdown
## Phase 0: Baseline audit and regression tests

- [ ] 阅读并记录 assessment 当前主流程：
  - `backend/modules/assessment/schema.py`
  - `backend/modules/assessment/service.py`
  - `backend/modules/assessment/profile_extractor.py`
  - `backend/modules/assessment/retriever.py`
  - `backend/modules/assessment/chapter_generator.py`
  - `backend/modules/assessment/consistency_checker.py`
  - `backend/modules/assessment/report_renderer.py`

- [ ] 新增或补充 assessment 的回归测试，至少覆盖：
  - [ ] 合法 security_assessment 路径可以生成报告。
  - [ ] 非 security_assessment 路径在 `force_override_path=false` 时会阻断。
  - [ ] `force_override_path=true` 时允许继续生成，并保留 path warning。
  - [ ] RAG 检索函数被调用，且 query 包含行业、目的、接收国家、CIIO/重要数据信息。
  - [ ] 渲染输出至少包含 `md/docx/zip`。
  - [ ] `trace_manifest` 被写入，且能索引到包含基本输入的 trace event 文件。

- [ ] 不改变业务行为，只补测试和记录。
```

## 验收标准

```markdown
## Phase 0 Acceptance Criteria

- [ ] 运行 assessment 测试时，当前主流程可复现。
- [ ] 测试失败时能定位到具体阶段：schema / diagnosis / retriever / generator / renderer。
- [ ] 没有新增“目标架构”字段。
- [ ] 没有修改业务流程。
- [ ] 没有为了测试而 mock 掉核心流程。
- [ ] 不要求 manifest 内联输入/输出 payload；当前验收以 trace event 文件存在和可读取为准。
```

## 人工验收方式

你可以让 Codex 输出：

```text
1. 当前 assessment 的实际调用链
2. 每个测试文件路径
3. 每个测试验证了什么
4. 是否改动业务代码；如果改了，说明为什么
```

如果它直接开始“优化架构”，说明它跑偏了。

---

# 三、阶段 1：定义统一中间产物 schema，但先不强行接管所有模块

## 目标

先定义统一数据结构，但不要急着让所有模块都用。否则容易变成“有 schema，没人用”。

建议新增目录：

```text
backend/common/workflow/
  __init__.py
  artifacts.py
  facts.py
  issues.py
  evidence.py
  context_pack.py
  trace.py
```

## 核心中间产物

### 1. FactItem：事实项

```python
class FactItem(BaseModel):
    fact_id: str
    source_type: Literal["schema", "attachment", "user_text", "diagnosis", "derived"]
    source_ref: str | None
    field_path: str | None
    value: Any
    normalized_value: Any | None = None
    confidence: float = 1.0
    notes: str | None = None
```

它解决的问题是：

```text
这个事实从哪里来？
是用户表单字段？
是附件抽取？
是诊断结果？
是系统推导？
可信度多少？
```

### 2. IssueItem：问题项

```python
class IssueItem(BaseModel):
    issue_id: str
    title: str
    description: str
    category: Literal[
        "path", 
        "data_scope", 
        "consent", 
        "recipient", 
        "contract", 
        "security_measure", 
        "documentation", 
        "other"
    ]
    severity: Literal["LOW", "MEDIUM", "HIGH", "BLOCKER"]
    fact_refs: list[str]
    rule_refs: list[str]
    evidence_refs: list[str] = []
    recommended_action: str
    affects_outputs: list[str] = []
```

它解决的问题是：

```text
系统到底发现了什么合规问题？
这个问题依据哪些事实？
依据哪些法规？
会影响哪些报告章节或材料？
```

### 3. EvidenceItem：证据链节点

```python
class EvidenceItem(BaseModel):
    evidence_id: str
    claim: str
    fact_refs: list[str]
    rule_refs: list[str]
    conclusion: str
    confidence: float
    used_by: list[str] = []
```

它解决的问题是：

```text
报告中的一句判断，是怎么从事实 + 法规推出的？
```

### 4. GenerationContextPack：统一生成上下文包

```python
class GenerationContextPack(BaseModel):
    module_key: str
    request_id: str
    facts: list[FactItem]
    diagnosis_result: dict | None = None
    regulations: list[dict]
    issues: list[IssueItem]
    evidence_chain: list[EvidenceItem]
    path_warning: str | None = None
    risk_summary: dict | None = None
    attachment_notes: list[dict] = []
    output_requirements: dict = {}
```

它解决的问题是：

```text
LLM 不能再由每个模块临时拼 context_block。
所有生成都应从 context_pack 中取信息。
```

## Codex 任务清单

```markdown
## Phase 1: Define workflow intermediate schemas

- [x] 新增 `backend/common/workflow/` 目录。
- [x] 新增 `facts.py`，定义 `FactItem`。
- [x] 新增 `issues.py`，定义 `IssueItem`。
- [x] 新增 `evidence.py`，定义 `EvidenceItem`。
- [x] 新增 `context_pack.py`，定义 `GenerationContextPack`。
- [x] 新增 `trace.py`，定义 trace 序列化辅助函数。
- [x] 所有 schema 必须使用 Pydantic BaseModel。
- [x] 所有 item 必须有稳定 ID 字段：
  - `fact_id`
  - `issue_id`
  - `evidence_id`
- [x] 新增 schema 单元测试，验证：
  - [x] 必填字段缺失时报错。
  - [x] severity 只能取限定枚举。
  - [x] category 只能取限定枚举。
  - [x] context_pack 可以被 JSON 序列化。
```

## 验收标准

```markdown
## Phase 1 Acceptance Criteria

- [x] 新增 schema 不破坏现有 assessment 流程。
- [x] schema 有独立测试。
- [x] 没有把 schema 只写成普通 dict。
- [x] 没有使用过度宽泛的 `Any` 替代关键字段。
- [x] `GenerationContextPack` 可以完整序列化进 trace 文件。
```

---

# 四、阶段 2：在 assessment 中真实生成 facts，而不是只复制字段

## 目标

把 `AssessmentRequest` 转成标准 `FactItem` 列表。

这一步不是做复杂 NLP，而是先把结构化输入变成统一事实层。

## 当前问题

现在是：

```text
AssessmentRequest → CompanyProfile
```

但 `CompanyProfile` 更像报告生成用对象，不是可追溯事实表。

应该变成：

```text
AssessmentRequest
  → CompanyProfile
  → facts[]
```

或者更直接：

```text
AssessmentRequest → facts[] → CompanyProfile / context_pack
```

## Codex 任务清单

```markdown
## Phase 2: Generate facts for assessment

- [x] 新增 `backend/modules/assessment/fact_builder.py`。
- [x] 实现 `build_assessment_facts(request, profile, diagnosis_result=None) -> list[FactItem]`。
- [x] 至少生成以下事实项：
  - [x] 企业名称 fact：来自 `request.company_name`
  - [x] 行业 fact：来自 `request.industry`
  - [x] 是否 CIIO fact：来自 `request.is_ciio`
  - [x] 是否涉及重要数据 fact：来自 `request.contains_important_data`
  - [x] 个人信息数量 fact：来自 `request.pii_count`
  - [x] 敏感个人信息数量 fact：来自 `request.spi_count`
  - [x] 出境目的 fact：来自 `request.transfer_purpose`
  - [x] 接收国家/地区 fact：来自 `request.receiver_country`
  - [x] 附件路径 fact：来自 `request.uploaded_files`
  - [x] 诊断推荐路径 fact：来自 `diagnosis_result.recommended_path`
  - [x] 诊断理由 fact：来自 `diagnosis_result.rationale`

- [x] 每个 fact 必须包含：
  - [x] `fact_id`
  - [x] `source_type`
  - [x] `field_path`
  - [x] `value`
  - [x] `confidence`

- [x] 在 `AssessmentService.generate_report()` 中调用 `build_assessment_facts()`。
- [x] 将 facts 写入独立 trace event，例如 `facts_built`；`trace_manifest.json` 只负责索引该 event 文件。
```

## 验收标准

```markdown
## Phase 2 Acceptance Criteria

- [x] assessment 生成报告后，trace 中存在 `facts_built` event，event payload 中存在 `facts` 数组。
- [x] `facts` 数组不是空数组。
- [x] 每个 fact 有稳定 ID。
- [x] 至少 8 个核心输入字段被转换为 FactItem。
- [x] 诊断结果中的 recommended_path 被转换为 FactItem。
- [x] 单元测试断言 `receiver_country`、`is_ciio`、`contains_important_data` 等字段真实进入 facts。
- [x] 不允许只把原始 request 整体 dump 成一个 fact。
```

## 防止假落实的关键测试

必须加这种测试：

```python
def test_assessment_facts_include_core_fields():
    facts = build_assessment_facts(request, profile, diagnosis_result)
    by_field = {f.field_path: f for f in facts}

    assert "request.receiver_country" in by_field
    assert "request.is_ciio" in by_field
    assert "request.contains_important_data" in by_field
    assert "diagnosis_result.recommended_path" in by_field
```

如果 Codex 只是写：

```python
FactItem(value=request.dict())
```

这就不合格。

---

# 五、阶段 3：在 assessment 中真实生成 issue_list

## 目标

让系统在生成报告之前，先明确产生“问题清单”。

当前 `assessment` 缺少这个层，所以 LLM 只能根据松散字段写章节。

改造后应变成：

```text
facts + diagnosis_result + regulations + attachment_notes
  → issue_list
  → context_pack
  → chapter_generator
  → report
```

## Issue 生成规则

先不要复杂到用 LLM。第一版建议用规则生成，保证稳定可测。

### 至少生成这些问题

| 条件                                                               | issue               |
| ---------------------------------------------------------------- | ------------------- |
| `diagnosis_result.recommended_path != security_assessment` 且强行生成 | 路径不匹配 warning issue |
| `contains_important_data == true`                                | 重要数据触发高风险路径         |
| `is_ciio == true`                                                | CIIO 触发高风险路径        |
| `pii_count` 超阈值                                                  | 个人信息规模触发安全评估        |
| `spi_count` 超阈值                                                  | 敏感个人信息规模触发安全评估      |
| `uploaded_files` 为空                                               | 申报材料缺失              |
| `receiver_country` 为空                                             | 境外接收方信息不足           |
| `transfer_purpose` 为空                                             | 出境目的不明确             |

> 暂不实现 unknown/None 重要数据规则：当前 `AssessmentRequest.contains_important_data`
> 是 `bool`，无法区分“明确不涉及”和“用户未知”。三态迁移应作为单独 schema 兼容改造，
> 不混入 Phase 3。

## Codex 任务清单

```markdown
## Phase 3: Add issue_list generation for assessment

- [x] 新增 `backend/modules/assessment/issue_builder.py`。
- [x] 实现 `build_assessment_issues(facts, diagnosis_result, regulations, attachment_notes) -> list[IssueItem]`。
- [x] Issue 生成必须基于 FactItem，不允许直接只读 request。
- [x] 每个 IssueItem 必须包含：
  - [x] `issue_id`
  - [x] `title`
  - [x] `description`
  - [x] `category`
  - [x] `severity`
  - [x] `fact_refs`
  - [x] `rule_refs`
  - [x] `recommended_action`
  - [x] `affects_outputs`

- [x] 至少实现以下 issue 规则：
  - [x] 路径不匹配 issue。
  - [x] CIIO 高风险 issue。
  - [x] 重要数据 true issue。
  - [x] 个人信息数量阈值 issue。
  - [x] 敏感个人信息数量阈值 issue。
  - [x] 附件缺失 issue。
  - [x] 接收国家缺失 issue。
  - [x] 出境目的缺失 issue。

- [x] 在 `AssessmentService.generate_report()` 中：
  - [x] RAG 之后调用 issue_builder。
  - [x] 将 issues 写入独立 trace event，例如 `issues_built`；`trace_manifest.json` 只负责索引该 event 文件。
  - [x] 将 issues 放入 `GenerationContextPack`。
```

## 验收标准

```markdown
## Phase 3 Acceptance Criteria

- [x] assessment 生成报告前会产生 `issue_list`。
- [x] trace 中存在 `issues_built` event，event payload 中存在 `issues` 数组。
- [x] 每个 issue 至少引用一个 `fact_ref`。
- [x] 涉及法规的 issue 至少引用一个 `rule_ref`。
- [x] 测试用例中，设置 `is_ciio=true` 必须产生 CIIO issue。
- [x] 设置 `contains_important_data=true` 必须产生 important data issue。
- [x] 不上传附件必须产生 documentation/material issue。
- [x] `issue_list` 不允许只作为 trace 存在，后续 prompt 必须消费它。
```

---

# 六、阶段 4：让 issue_list 真正进入 LLM prompt，避免“生成了但没用”

这是最关键的一步。

很多假落实会停在：

```text
生成了 issue_list
写进 trace_manifest
但 LLM prompt 仍然不用
```

这不算完成。

## 当前问题

你已经指出：

```text
chapter_generator.py 的 prompt 没有 diagnosis_result、path_warning、extracted_notes、issue_list、evidence_chain
```

所以要明确改。

## Codex 任务清单

```markdown
## Phase 4: Make issue_list drive chapter generation

- [x] 修改 `backend/modules/assessment/chapter_generator.py`。
- [x] 新增稳定章节 key 映射 `ASSESSMENT_CHAPTER_KEYS`，至少包含：
  - [x] `overview`
  - [x] `data_scope`
  - [x] `necessity_legal_basis`
  - [x] `recipient_capability`
  - [x] `rights_impact`
  - [x] `security_measures`
  - [x] `risk_remediation`
  - [x] `conclusion`
- [x] 将原来的临时 `context_block` 改为由 `GenerationContextPack` 构造。
- [x] 新增函数：
  - [x] `build_context_block_from_pack(context_pack: GenerationContextPack, chapter_id: str) -> str`

- [x] context_block 必须包含：
  - [x] 企业基本事实摘要。
  - [x] diagnosis_result 推荐路径。
  - [x] path_warning，如果存在。
  - [x] risk_summary。
  - [x] regulations 前 5 条摘要。
  - [x] 与当前章节相关的 issues。
  - [x] issue_id、severity、recommended_action。
  - [x] attachment_notes，如果存在。
  - [x] evidence_chain，如果存在。

- [x] 每个章节生成时，应筛选 `affects_outputs` 包含当前 chapter_id 的 issue。
- [x] 如果没有匹配 issue，应放入全局 HIGH/BLOCKER issue。
- [x] prompt 中必须明确要求：
  - [x] 不得编造 facts 中没有的事实。
  - [x] 每个风险判断需要引用 issue_id 或 regulation citation。
  - [x] 对材料缺失应写成“需补充”，不得假设已经具备。
```

## 验收标准

```markdown
## Phase 4 Acceptance Criteria

- [x] 单元测试可以捕获最终传给 LLM 的 prompt。
- [x] 单元测试验证章节标题能映射到稳定 chapter_id。
- [x] prompt 中真实出现 issue_id。
- [x] prompt 中真实出现 diagnosis recommended_path。
- [x] prompt 中真实出现 attachment_notes。
- [x] 当存在附件缺失 issue 时，生成 prompt 中必须出现“材料缺失/需补充”相关内容。
- [x] 删除 issue_list 后，对应测试失败。
- [x] `chapter_generator` 不再只依赖零散字段和 regulations。
```

## 防止假落实的测试

要求 Codex 加测试：

```python
def test_chapter_prompt_contains_issues_and_diagnosis():
    prompt = build_context_block_from_pack(context_pack, chapter_id="risk_analysis")

    assert "ISSUE-" in prompt
    assert "recommended_path" in prompt
    assert "security_assessment" in prompt
    assert "需补充" in prompt or "材料缺失" in prompt
```

只要 prompt 里没有 issue_id，就说明 issue_list 没有真实参与生成。

---

# 七、阶段 5：落地 evidence_chain，不要只做 citations

## 目标

现在系统最多有 citations，但 citations 不是证据链。

真正证据链应是：

```text
事实：企业是 CIIO
法规：CIIO 出境数据可能触发安全评估
结论：推荐安全评估路径
用途：用于第 2 章路径判断、第 4 章风险分析
```

## EvidenceItem 应该连接三类东西

```text
FactItem → Regulation/Citation → Conclusion
```

## Codex 任务清单

```markdown
## Phase 5: Add evidence_chain for assessment

- [x] 新增 `backend/modules/assessment/evidence_builder.py`。
- [x] 实现 `build_assessment_evidence(facts, issues, regulations, diagnosis_result) -> tuple[list[IssueItem], list[EvidenceItem]]`。
- [x] evidence 生成后必须回填 `IssueItem.evidence_refs`，不能让 issue 与 evidence 脱节。
- [x] 每个 EvidenceItem 必须包含：
  - [x] `evidence_id`
  - [x] `claim`
  - [x] `fact_refs`
  - [x] `rule_refs`
  - [x] `conclusion`
  - [x] `confidence`
  - [x] `used_by`

- [x] 至少生成以下 evidence：
  - [x] CIIO → 安全评估路径判断。
  - [x] 重要数据 → 安全评估路径判断。
  - [x] 个人信息规模 → 安全评估路径判断。
  - [x] 敏感个人信息规模 → 高风险判断。
  - [x] 接收国家/地区 → 境外接收方风险判断。
  - [x] 附件缺失 → 材料完整性风险判断。

- [x] evidence_chain 必须写入：
  - [x] `GenerationContextPack`
  - [x] 独立 trace event，例如 `evidence_built`；`trace_manifest.json` 只负责索引该 event 文件
  - [x] LLM prompt
```

## 验收标准

```markdown
## Phase 5 Acceptance Criteria

- [x] trace 中存在 `evidence_built` event，event payload 中存在 `evidence_chain`。
- [x] 每个 evidence 至少引用一个 fact_ref。
- [x] 每个 evidence 至少引用一个 rule_ref，除非该 evidence 是纯材料完整性判断。
- [x] issue 中的 evidence_refs 能指向实际存在的 evidence_id。
- [x] prompt 中能看到 evidence_id 或 claim。
- [x] 测试断言：CIIO=true 时，至少产生一个包含 CIIO fact_ref 的 evidence。
```

---

# 八、阶段 6：升级 consistency_checker，让它检查 facts/issues/evidence/report 的一致性

## 当前问题

现在检查比较轻：

```text
citations 是否存在
最后章节风险是否 HIGH
少量关键词冲突
```

改造后应该检查：

```text
facts → issues → evidence → generated chapters
```

## Codex 任务清单

```markdown
## Phase 6: Upgrade consistency checking

- [x] 修改 `backend/modules/assessment/consistency_checker.py`。
- [x] 新增 `check_context_pack_consistency(context_pack)`。
- [x] 新增 `check_report_against_context(report_content, context_pack)`。

- [x] 至少检查以下规则：
  - [x] 每个 issue.fact_refs 都能在 facts 中找到。
  - [x] 每个 issue.rule_refs 都能在 regulations 中找到。
  - [x] 每个 evidence.fact_refs 都能在 facts 中找到。
  - [x] 每个 evidence.rule_refs 都能在 regulations 中找到。
  - [x] HIGH/BLOCKER issue 必须在报告正文中被提及。
  - [x] 如果附件缺失 issue 存在，报告不得写“材料齐备”。
  - [x] 如果后续三态迁移引入 `contains_important_data=unknown`，报告不得写“确认不涉及重要数据”。
  - [x] 如果 path_warning 存在，报告必须包含路径提示或风险说明。
  - [x] 如果 diagnosis_result 不推荐 security_assessment 且 force_override_path=true，报告必须声明该报告为强制生成/参考草案。

- [x] consistency 结果写入独立 trace event；`trace_manifest.json` 只负责索引该 event 文件。
```

## 验收标准

```markdown
## Phase 6 Acceptance Criteria

- [x] consistency_checker 不再只检查 citations。
- [x] 可以检查 context_pack 内部引用完整性。
- [x] 可以检查报告正文是否遗漏 HIGH/BLOCKER issue。
- [x] 人为构造一个缺失 fact_ref 的 issue，测试必须失败。
- [x] 人为构造“附件缺失但报告写材料齐备”，测试必须失败。
- [x] consistency issues 被写入 trace event，manifest 可索引到该 event。
```

---

# 九、阶段 7：让 report_renderer 输出中间产物附件

## 目标

不能只在 trace_manifest 里有中间产物。用户真正验收时，需要看到：

```text
主报告
问题清单
证据链
材料补充清单
trace_manifest
```

## 建议输出结构

```text
outputs/assessment/{request_id}/
  assessment_report.md
  assessment_report.docx
  assessment_package.zip
  issue_list.json
  issue_list.xlsx
  evidence_chain.json
  evidence_chain.xlsx
  material_checklist.xlsx
  trace_manifest.json
```

## Codex 任务清单

```markdown
## Phase 7: Render intermediate artifacts

- [x] 修改 `backend/modules/assessment/report_renderer.py`。
- [x] 新增中间产物渲染：
  - [x] `issue_list.json`
  - [x] `issue_list.xlsx`
  - [x] `evidence_chain.json`
  - [x] `evidence_chain.xlsx`
  - [x] `material_checklist.xlsx`

- [x] `issue_list.xlsx` 至少包含列：
  - [x] issue_id
  - [x] title
  - [x] category
  - [x] severity
  - [x] fact_refs
  - [x] rule_refs
  - [x] recommended_action
  - [x] affects_outputs

- [x] `evidence_chain.xlsx` 至少包含列：
  - [x] evidence_id
  - [x] claim
  - [x] fact_refs
  - [x] rule_refs
  - [x] conclusion
  - [x] confidence
  - [x] used_by

- [x] `material_checklist.xlsx` 包含列：source_ref / summary / status（派生自 attachment_notes）。

- [x] zip 包必须包含上述中间产物。
```

## 验收标准

```markdown
## Phase 7 Acceptance Criteria

- [x] assessment zip 中包含 issue_list.json。
- [x] assessment zip 中包含 issue_list.xlsx。
- [x] assessment zip 中包含 evidence_chain.json。
- [x] assessment zip 中包含 evidence_chain.xlsx。
- [x] assessment zip 中包含 material_checklist.xlsx。
- [x] issue_list.xlsx 行数与 `issues_built` trace event 中 issues 数量一致。
- [x] evidence_chain.xlsx 行数与 `evidence_built` trace event 中 evidence_chain 数量一致。
```

这一步能有效防止“后端生成了但用户看不到”的假落实。

---

# 十、阶段 8：前端展示中间产物，不要只下载报告

## 目标

当前系统如果只给用户一个 docx/pdf，就还是“黑箱报告生成”。

应在工作台中展示：

```text
事实表
路径判断
问题清单
证据链
材料补充项
最终报告
```

## Codex 任务清单

```markdown
## Phase 8: Frontend display for workflow intermediates

- [x] 修改 assessment 任务运行结果的数据适配逻辑（后端新增 facts_json / path_judgment_json / material_checklist_json writer）。
- [x] 在前端 artifact/result panel 中新增 tabs：
  - [x] 事实识别
  - [x] 路径判断
  - [x] 问题清单
  - [x] 证据链
  - [x] 材料清单
  - [x] 报告输出

- [x] 每个 tab 读取后端返回或 artifact preview 中的对应文件。
- [x] 问题清单 tab 至少展示：
  - [x] issue_id
  - [x] severity
  - [x] title
  - [x] recommended_action
  - [x] related facts
  - [x] related rules

- [x] 证据链 tab 至少展示：
  - [x] claim
  - [x] facts
  - [x] rules
  - [x] conclusion
  - [x] used_by

- [x] 如果后端没有返回 issues/evidence，应显示”当前模块尚未生成该中间产物”，不得伪造空成功状态。
```

## 验收标准

```markdown
## Phase 8 Acceptance Criteria

- [x] 运行 assessment 后，前端能看到问题清单。
- [x] 运行 assessment 后，前端能看到证据链。
- [x] 点击 issue 可以看到关联 fact/rule。
- [x] 没有中间产物时，前端明确显示缺失状态。
- [x] 前端不 hardcode 示例 issue。
```

---

# 十一、阶段 9：把 assessment 标准链路抽成可复用 WorkflowPipeline

前面先不要抽象。等 assessment 真跑通后，再抽。

## 目标

把重复逻辑抽成：

```text
build_facts
retrieve_regulations
build_issues
build_evidence
build_context_pack
generate_chapters
check_consistency
render_artifacts
```

## Codex 任务清单

```markdown
## Phase 9: Extract reusable workflow pipeline

- [x] 新增 `backend/common/workflow/pipeline.py`。
- [x] 定义 `WorkflowPipeline` 或 `BaseWorkflowRunner`。
- [x] 只抽象已经在 assessment 中真实跑通的步骤。
- [x] 不要提前设计未使用接口。
- [x] assessment 改为调用 pipeline，但业务规则仍保留在 assessment 自己的 builder 中：
  - [x] `assessment/fact_builder.py`
  - [x] `assessment/issue_builder.py`
  - [x] `assessment/evidence_builder.py`

- [x] pipeline 负责顺序编排：
  - [x] facts
  - [x] regulations
  - [x] issues
  - [x] evidence
  - [x] context_pack
  - [x] generation
  - [x] consistency
  - [x] rendering
  - [x] trace
```

## 验收标准

```markdown
## Phase 9 Acceptance Criteria

- [x] assessment 行为与 Phase 8 保持一致。
- [x] pipeline 中没有空实现。
- [x] pipeline 中没有只 pass 的抽象方法。
- [x] 单元测试确认 pipeline 每一步都会产生真实产物。
- [x] 删除 issue_builder 后，assessment 测试失败，而不是静默跳过。
```

---

# 十二、阶段 10：迁移 cn_flow / cpra / bcr / scc 等模块

不要一上来全迁移。建议顺序：

```text
assessment → cn_flow → cpra → bcr → scc → dpia/tia/pipia
```

原因：

| 模块             | 为什么排这里                       |
| -------------- | ---------------------------- |
| assessment     | 主链路最完整                       |
| cn_flow        | 已有 risk_items，适合对齐 IssueItem |
| cpra           | 已有 gap_items，适合对齐 IssueItem  |
| bcr            | 已有 problems，适合对齐 IssueItem   |
| scc            | 已有 findings，适合对齐 IssueItem   |
| dpia/tia/pipia | 更依赖文书生成，后迁移更稳                |

## 每个模块迁移模板

```markdown
## Module Migration Checklist: {module_key}

- [ ] 梳理当前模块已有中间产物：
  - risk_items / gap_items / problems / findings / citations / regulations / checks

- [ ] 建立映射：
  - 当前 risk_items → IssueItem
  - 当前 gap_items → IssueItem
  - 当前 problems → IssueItem
  - 当前 findings → IssueItem
  - 当前 citations → rule_refs
  - 当前 checks → consistency issues

- [ ] 新增 `{module}/fact_builder.py`。
- [ ] 新增 `{module}/issue_adapter.py` 或 `{module}/issue_builder.py`。
- [ ] 新增 `{module}/evidence_builder.py`。
- [ ] 生成 `GenerationContextPack`。
- [ ] 修改 prompt，使其消费 context_pack。
- [ ] 修改 renderer，输出 issue/evidence 附件。
- [ ] 修改 trace_manifest。
- [ ] 增加模块级测试。
```

## 验收标准

```markdown
## Module Migration Acceptance Criteria

- [ ] 模块运行后 trace manifest 能索引到 facts trace event。
- [ ] 模块运行后 trace manifest 能索引到 issues trace event。
- [ ] 模块运行后 trace manifest 能索引到 evidence_chain trace event。
- [ ] prompt 中真实出现 issue_id。
- [ ] zip/docx/pdf 输出包中包含中间产物文件。
- [ ] 原模块已有的 risk_items/gap_items/problems/findings 没有丢失。
- [ ] 测试覆盖至少 2 个典型场景和 1 个缺失材料场景。
```

### Phase 10 Progress: `cn_flow`（2026-05-20）

- [x] 梳理当前模块中间产物并完成映射：`risk_items -> IssueItem`，`citations -> rule_refs`。
- [x] 新增 `backend/modules/cn_flow/fact_builder.py`。
- [x] 新增 `backend/modules/cn_flow/issue_builder.py`。
- [x] 新增 `backend/modules/cn_flow/evidence_builder.py`。
- [x] 接入 `GenerationContextPack` 并改造章节生成消费 context pack。
- [x] 接入 `WorkflowPipeline`，按 `facts -> regulations -> issues -> evidence -> context -> generation -> consistency -> rendering -> trace` 顺序执行。
- [x] 输出中间产物附件：`facts.json`、`issue_list.json`、`evidence_chain.json`、`trace_manifest.json`（随 zip 打包）。
- [x] 模块级测试覆盖同步更新（同步场景 + 异步场景）。
- [ ] 后续模块迁移（`cpra/bcr/scc/dpia/tia/pipia`）待继续推进。

---

# 十三、最终总验收：判断是否真的从 v0 流水线升级为中间产物驱动工作流

你可以要求 Codex 最终提交一份 `IMPLEMENTATION_VERIFICATION.md`，结构如下：

```markdown
# Implementation Verification

## 1. Pipeline evidence

- [ ] 用户输入是否进入 FactItem？
  - 代码位置：
  - 测试位置：
  - 示例输出文件：

- [ ] FactItem 是否进入 IssueItem？
  - 代码位置：
  - 测试位置：
  - 示例输出文件：

- [ ] IssueItem 是否进入 EvidenceItem？
  - 代码位置：
  - 测试位置：
  - 示例输出文件：

- [ ] IssueItem / EvidenceItem 是否进入 LLM prompt？
  - 代码位置：
  - 测试位置：
  - prompt 截取：

- [ ] IssueItem / EvidenceItem 是否进入最终交付物？
  - 文件路径：
  - zip 内容截图/列表：

## 2. Negative tests

- [ ] 删除 issue_list 后，prompt 测试是否失败？
- [ ] 删除 evidence_chain 后，trace 测试是否失败？
- [ ] 构造附件缺失但报告写“材料齐备”，一致性检查是否失败？
- [ ] 构造 important_data unknown 但报告写“不涉及重要数据”，一致性检查是否失败？

## 3. Module coverage

| module | facts | issues | evidence | context_pack | prompt uses pack | artifacts | tests |
|---|---|---|---|---|---|---|---|
| assessment | yes/no | yes/no | yes/no | yes/no | yes/no | yes/no | yes/no |
| cn_flow | yes/no | yes/no | yes/no | yes/no | yes/no | yes/no | yes/no |
| cpra | yes/no | yes/no | yes/no | yes/no | yes/no | yes/no | yes/no |
| bcr | yes/no | yes/no | yes/no | yes/no | yes/no | yes/no | yes/no |
| scc | yes/no | yes/no | yes/no | yes/no | yes/no | yes/no | yes/no |
```

这份文件的关键是：**每个 yes 都必须附代码位置、测试位置、示例输出文件路径**。否则就是口头 yes。

---

## 总验收执行记录（2026-05-20）

- [x] 已提交 `IMPLEMENTATION_VERIFICATION.md`。
- [x] assessment 验收链路完成（facts/issues/evidence/context_pack/prompt/artifacts/tests）。
- [x] cn_flow 验收链路完成（facts/issues/evidence/context_pack/prompt/artifacts/tests）。
- [ ] `cpra/bcr/scc` 尚未迁移完成，模块覆盖仍为 no。
- [ ] “删除 evidence_chain 后 trace 测试失败”负向测试尚未补齐。
