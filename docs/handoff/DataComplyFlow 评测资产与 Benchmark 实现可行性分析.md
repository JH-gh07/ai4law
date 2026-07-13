# DataComplyFlow 评测资产与 Benchmark 实现可行性分析

> 项目：AI4Law / 数规通 DataComplyFlow  
> 专项：评测资产、Benchmark 可行性与最小实现路径  
> 审计日期：2026-07-13（Asia/Shanghai）  
> 审计性质：只读事实分析；本轮未修改业务代码、规则、Prompt 或测试。

## 1. 审计目的、范围与结论摘要

本专项回答两个问题：当前仓库已经具备哪些可验证的评测条件；围绕“中国企业数据出境合规路径诊断及其下游任务”，如何在不先重构全系统的条件下建立第一版产品级 Benchmark。

事实依据依次为当前代码、上一轮实际测试结果、当前配置和调用链、已有 QA/Trace/Fixture/输出，以及 `docs/handoff/AI4Law_项目事实基线与真实系统理解.md`。规划文档只用于发现候选需求，不作为能力实现证据。

上一轮在当前检出版本执行完整测试，结果为 **290 passed、18 failed、17 errors、133 warnings，耗时 166.13 秒**。本轮不重复创建测试环境，沿用该已记录运行事实。

### 1.1 一页式结论

1. 当前不是“没有 Benchmark”，而是已有 **RAG 检索基准、分层生成评测、v0 输出回归、单元/集成测试、前端 demo cases、知识文档案例和历史 traces**，但尚未统一为一个版本化、可重复、可比较的产品 Benchmark。
2. 可机器读取的主要资产包括：300 条 RAG 主查询、80 条额外 hard negatives、31 条分层 retrieval/generation JSONL、7 条 v0 样本及 expected hashes、29 条前端开发案例、78 个测试文件/约 308 个测试函数、25 个历史 trace manifest、16 份历史 review DOCX。
3. 中国路径诊断最适合做第一版 Benchmark：输入输出 Schema 明确、规则确定性强、已有 4 个代码测试和 3 个知识文档案例，且可直接构造 Rule-only baseline。
4. 第一版不应把完整报告质量作为唯一主指标。应按 **事实结构化→节点判断→最终路径→检索→证据/缺失事实→分流→下游交付** 分层评测，避免一个生成结果掩盖上游错误。
5. 最小实现不需要统一重构所有模块：新增独立 `benchmark/` 或 `qa/benchmark/` Harness，以 Adapter 包装现有 `DiagnosisService`、`retrieve_regulations()`、`LLMClient`、assessment/SCC/PIPIA service；统一写入评测专用结果 Schema 即可。
6. 第一轮必须先修复 SCC `uuid`、CN Flow Pipeline 参数、v0 DPIA 映射等运行 Bug；但 Smoke Benchmark 若只覆盖 diagnosis + RAG + assessment 下游，可暂时绕开 CN Flow，并将 SCC/PIPIA 报告链标为“条件执行”。

## 2. 评测资产盘点

### 2.1 资产总表

| 资产 | 物理数量 | 逻辑数量/案例数 | 格式 | 主要法域/模块 | 当前性质 | 可复用等级 |
|---|---:|---:|---|---|---|---|
| `qa/` | 8 文件 | RAG v1 17 query；RAG v2 380 query；v0 7 cases | JSON/MD | CN/EU/US；10 个 RAG module；7 个 v0 module | 已运行结果、回归快照、expected output | 高，但需版本与重复清理 |
| `doc/knowledge/_evaluation/` | 9 文件 | 31 JSONL cases + 380 CSV queries | JSONL/CSV/MD | CN/EU/US | RAG/生成 Gold-like constraints | 高 |
| `doc/knowledge/evaluation/` | 9 文件 | 与 `_evaluation` 完全相同 | JSONL/CSV/MD | 同上 | 镜像重复 | 不应双计 |
| 后端测试 | 78 文件 | 约 308 test functions | Python | API/common/11 模块/review | 单元、组件、集成、准 E2E | 中高；输入多为 inline fixture |
| 知识模块 `test-cases.md` | 10 文件 | 正则识别约 33 个案例标记 | Markdown prose | CN 4 类、EU 4 类、US 2 类 | 需求案例/预期描述 | 中；需结构化和法律复核 |
| 前端 `dev-test-cases.ts` | 1 文件 | 29 named cases | TypeScript object | 诊断、assessment、SCC、EU SCC、BCR、DPIA、TIA、PIPIA、EO14117、CN Flow、review、CPRA | Demo/开发注入数据 | 中；高度可能为合成 |
| 前端 `demoPayloads.ts` | 1 文件 | 11 module payload builders | TypeScript | 全前端 adapter 模块 | Demo 默认数据 | 低中；无 Gold |
| 前端 `dev-presets.ts` | 1 文件 | 8 preset ids | TypeScript | assessment、PIPIA、EU SCC、BCR、DPIA、TIA、diagnosis、review | 开发 preset | 中低；与 dev cases 有重叠 |
| `qa/baseline` | 2 文件 | 7 input cases + 7 expected records | JSON | assessment/PIPIA/BCR/DPIA/TIA/CN Flow/CPRA | 端到端输出回归 | 中；Gold 仅 artifact type/hash |
| `storage/traces` | 约 751 文件 | 25 有 manifest 的运行；另有无 manifest 目录 | JSON | assessment 等 11 类 | 历史运行/测试/模型比较混合 | 中高；provenance 不足 |
| `storage/reports` | 16 文件 | 16 review outputs | DOCX | 通用文档审查 | 历史输出 | 中；无配套 Gold/输入清单 |
| `storage/uploads` | 48 文件 | 48 上传/样本 | TXT/DOCX/CSV/MD | 多模块 | fixture、demo、可能真实材料混合 | 低至中；必须先分类脱敏 |

“逻辑数量”排除了已确认的字节级重复目录；知识文档案例数以文本标记计数，只能作为近似，不等于已经可运行的 machine-readable cases。

### 2.2 QA 资产的字段与覆盖

#### RAG v2 数据集

`doc/knowledge/_evaluation/rag_eval_v2_queries.csv` 有 300 行，字段：

```text
query_id, module, split, difficulty, label_type, query,
gold_source_ids, gold_article_ids, expected_jurisdiction,
expected_path, expected_empty, notes
```

分布：10 个 module 各 30；train 240、holdout 60；positive 240、negative 60；CN 150、EU 90、US 60；hard 183、medium 117。`rag_eval_v2_hard_negatives.csv` 另有 80 条 hard negative：10 模块各 8；train 60、holdout 20；CN 40、EU 24、US 16。两者合计正样本 240、负样本 140。

`qa/rag_eval_v2.json` 是已运行结果，vector 模式：Recall@5 0.8875、Top1 0.6875、MRR 0.7674、negative safe reject 0.8571；hybrid 模式：Recall@5 0.8542、Top1 0.6750、MRR 0.7434、negative safe reject 0.9357。这里的 hybrid 对负样本更稳，但正样本 Recall/Top1 低于 vector；不能仅凭“hybrid”命名称其更优。

`qa/regression/rag_eval_v2_20260404.json` 与 `qa/rag_eval_v2.json` SHA-256 完全相同，是重复快照；20260403 结果不同，可作为前一版本回归点。`qa/rag_baseline_v1.json` 只有 17 queries 且各指标均为 1.0，样本过小，不宜作为当前主结论。

#### 分层 JSONL

逻辑上有 17 个 retrieval cases：CN 10（assessment 5、review 5）、EU 4、US 3。字段支持 must-retrieve source ids、禁止 layer/source kind/jurisdiction，并在 EU/US 中含 jurisdiction/path/document_type/task_stage。

逻辑上有 14 个 generation cases：CN 10（assessment 5、review 5）、EU 2、US 2。字段包括：

```text
case_id, module, must_find_issues, must_cite_source_ids,
must_not_use_layers, must_not_claim,
must_use_official_template_sections（仅部分 CN case）
```

这些字段适合做约束式 Gold，但并非完整自然语言报告 Gold。`backend/common/rag/eval.py` 已计算 Recall@K、MRR、禁止层泄漏、跨法域污染、Issue recall、Citation correctness、Unsupported-claim rate 等。

### 2.3 测试资产分类

| 类别 | 代表位置 | 数量事实 | 复用价值 | 限制 |
|---|---|---:|---|---|
| 单元测试 | `backend/common/citation/tests`、knowledge、schema、规则/agent tests | citation 27、knowledge 19、RAG 15、assessment 65 等 | 可提取边界条件和断言 | 多为函数内 inline 数据，无统一 case id |
| API/集成测试 | `backend/api/test_*.py`、各模块 `test_async_api.py` | API 43 tests；各模块 async tests | 可验证契约、状态和文件 | 当前多处鉴权预期不一致 |
| 准 E2E | `backend/modules/v0_task_gateway/tests/test_api.py` | 7 流程 | 输入→任务→artifact/download/audit | DPIA、CN Flow 当前失败；不含 diagnosis/SCC/EO14117 |
| 生成/渲染回归 | assessment renderer、service tests；v0 hashes | 多项 | Schema、报告结构、artifact 存在性 | LLM 文本非确定时 hash 脆弱 |
| RAG 评测 | `backend/common/rag/tests/test_eval.py` 和 `eval.py` | 7 eval tests + 数据集 | 可直接复用 | 与产品路径 Benchmark 尚未统一 |

本仓库仅发现 4 个显式 `@pytest.fixture` 装饰器，大部分测试数据直接写在测试函数或 module-level client 中。因此“测试数”不能等同“独立数据集案例数”，提取前需去重。

### 2.4 Demo、合成、可能真实数据与 Gold

- **明确 Demo/开发数据**：`demoPayloads.ts`、`dev-test-cases.ts`、`dev-presets.ts`，名称含 Demo、测试或典型虚构公司。29 个 named cases 很适合生成 Smoke 候选，但无权威 Gold。
- **合成/需求案例**：10 个 `doc/knowledge/*/test-cases.md`，约 33 个案例标记，包含丰富背景与预期输出；内容与前端案例存在明显重叠，例如中国 diagnosis 的跨境电商、医疗研究案例。应视为同源派生候选，不应独立计数。
- **expected output**：v0 的 7 条 expected 只标注 artifact types 和 Markdown SHA-256；适合 deterministic regression，不足以评估法律正确性。JSONL 的 must-find/must-cite/must-not 则更接近部分 Gold。
- **可能真实运行**：随机 UUID trace 目录、`storage/reports/review/*`、部分上传 DOCX 可能来自手工或真实运行；但 manifest 不记录 dataset/source/user/demo 标识，无法确认。
- **历史模型比较**：`assessment_siliconflow_assessment`、`assessment_tencent_hunyuan_assessment`、PIPIA 的同类目录明确像模型对照实验，可用于比较输出，但配置版本不完整。

### 2.5 重复、过期、来源不明与敏感性风险

1. `_evaluation/` 与 `evaluation/` 的 9 对文件逐一 SHA-256 相同，必须选择单一 canonical path。
2. `qa/rag_eval_v2.json` 与 `qa/regression/rag_eval_v2_20260404.json` 完全相同，不应重复统计。
3. v1 RAG 17-query 结果被 v2 380-query 体系实质取代，可保留历史但不作为主 baseline。
4. 前端 dev cases、知识 test-cases、后端 tests 之间存在同源案例；需要 stable `source_case_id` 和 lineage。
5. traces 的 manifest 缺 module、dataset id、commit、provider、knowledge version 和输入 digest；名称含“测试企业”“AI招聘公司”等不足以证明数据来源。
6. uploads 中有 `测试使用的同一个合同.docx`、个人信息出境标准合同模板、`CC源码分析.docx` 及多份 evidence 文本。即便名称像测试，也可能含合同、个人信息或商业信息。未做内容级 PII 扫描前不得进入公开 Benchmark。
7. 历史 LLM trace response 主要只保存 `content`，没有稳定 usage；部分 request/response 可能包含用户输入和模型输出，应按敏感运行数据处理。

## 3. 中国数据出境任务与 Schema 映射

### 3.1 主链边界

第一版产品 Benchmark 建议以以下链条为对象：

```text
企业场景/表单/材料
→ 事实标准化
→ 路径节点判断
→ 最终路径（豁免/安全评估/SCC或认证/需补充）
→ 法规条款检索
→ 缺失事实与证据构建
→ 追问/人工分流
→ assessment 或 SCC/PIPIA 下游产物
```

当前不存在一个自动完成全部链条的统一 API。diagnosis、assessment、SCC、PIPIA 是独立模块，必须由 Benchmark Adapter 显式串联。

### 3.2 任务映射表

| 任务 | 当前输入 Schema | 当前输出 Schema | 真实调用 | 已有可评字段 | 主要缺口 | 低侵入接入 |
|---|---|---|---|---|---|---|
| 事实结构化 | `DiagnosisAnswers` 的 q1-q8 + m1-m5；assessment `AssessmentRequest`；SCC `SCCRequest` | diagnosis 内部 normalized answers；公共 `FactItem`；assessment `CompanyProfile` | `DiagnosisService._normalize_answers()`；assessment profile/fact builder；SCC fact builder | q 字段、normalized value、source/confidence/evidence status | diagnosis 不输出 normalized answers/FactItem；跨模块字段名重复 | Adapter 调用 normalize/evaluate并投影到评测 FactRecord；不改 service |
| 节点级法律判断 | q1 CIIO、q2 重要数据、q5 PI、q6 豁免场景、q3/q4 阈值 | `matched_rule_id`、legal_basis、risk、Agent notes | `decision_tree.json` + `_rule_match()` + 3 agents | matched_rule_id、conclusion_source、confidence | 没有完整 decision trace/每个未命中节点结果；规则版本缺失 | Adapter 重放 tree 并记录每条 predicate 结果，或从规则函数旁路采集 |
| 最终路径判断 | `DiagnosisAnswers` | `DiagnosisResult.recommended_path`、matched_rule_id、confidence、uncertainty | `DiagnosisService.evaluate()` | path exact match、rule id exact match、abstention/uncertainty | 代码只有 exemption/security_assessment/scc_or_certification；“认证 vs SCC”未再分流 | 可直接评测；Gold 需法律专家冻结规则版本 |
| 法规条款检索 | query+jurs/path/stage；或 profile | `RegulationDoc`/`KnowledgeChunkV2`/RetrievalBundle | `retrieve_regulations()`、RetrievalOrchestrator | source_id/article、rank、layer、jurisdiction | diagnosis 规则法律依据是字符串，未与检索 source id 强绑定；effective date 未强制 | 复用现有 `run_retrieval_eval` 和新 case adapter |
| 证据构建 | facts/issues/regulations/diagnosis | `EvidenceItem`：claim、fact/rule/issue/citation/doc refs、confidence | assessment/SCC builders；公共 WorkflowPipeline | evidence count、refs、legal basis、usage constraint | diagnosis 主链无 EvidenceItem；无 ClaimItem；并非全部模块公共化 | 只在下游阶段调用现有 builder；评测输出投影为 EvidenceRecord |
| 缺失事实识别 | unknown/default/缺附件/Issue.missing_materials | `uncertainty_notes`、blocking_issues、next_questions、missing_materials、material_gaps | diagnosis agents；SCC clarification；assessment issues；PIPIA gaps | unknown 字段、问题列表、material gaps | diagnosis `DiagnosisResult` 没有统一 missing_fact_ids；unknown 可能被启发式改写 | Adapter 以输入空缺+输出 notes/questions 统一映射；Gold 需标注 must_ask/must_not_infer |
| 追问/拒答/人工分流 | SCC PathDiagnosisInput、issues/context | `ClarificationResult`、internal_review_required、REPAIR_BLOCKED 文本 | SCC clarification agent、IssueItem、assessment repair | questions、review flags、confidence | diagnosis 无正式 abstain 状态；Agent 可能直接填 unknown；repair block 不真阻断 renderer | Benchmark 先评“建议分流”而非实际阻断；统一 decision_action enum |
| 完整报告生成 | assessment/SCC/PIPIA 请求及附件 | 各模块 Result、chapters、output_files、consistency、trace | 各 service；assessment 公共 Pipeline 最完整 | Schema pass、章节/文件、引用、issues、consistency | SCC 当前 `uuid` Bug；PIPIA 公共 IR 不完整；生成非确定 | 通过 service adapter 条件执行；首轮只做结构/约束/失败率，不做全文唯一 Gold |

### 3.3 关键 Schema 事实

`DiagnosisAnswers` 有约 40 个字段，既含路径核心 q1-q8，也含企业、数据类型、处理、跨境、系统和治理 m1-m5。`DiagnosisResult` 已提供 `recommended_path`、`matched_rule_id`、`conclusion_source`、`confidence`、`uncertainty_notes`，非常适合路径 Benchmark。

公共 `FactItem`、`IssueItem`、`EvidenceItem`、`GenerationContextPack` 已有 provenance、certainty、关联 refs 和 usage constraints，适合做评测中间输出；但 diagnosis 不直接返回这些类型，SCC Result 又把 facts/issues/evidence 声明为 `list[dict]`，PIPIA 同样是 dict 列表。故评测层应“投影统一”，不应先改完所有业务 Schema。

### 3.4 建议的评测统一输出（不改业务 DTO）

每个 Adapter 输出评测专用 `BenchmarkPrediction`：

```json
{
  "case_id": "CN-PATH-001",
  "baseline_id": "rule_only",
  "status": "success|failed|abstained|human_review",
  "facts": [{"field": "q1_is_ciio", "value": "no", "source": "input", "confidence": 1.0}],
  "node_decisions": [{"node_id": "ciio", "result": "not_triggered", "basis_ids": []}],
  "final_path": "security_assessment|scc_or_certification|exemption|uncertain",
  "missing_fact_ids": [],
  "questions": [],
  "retrieval": [{"source_id": "...", "article_id": "...", "rank": 1}],
  "evidence": [{"claim_key": "...", "fact_refs": [], "rule_refs": [], "citation_refs": []}],
  "downstream": {"module": "assessment", "schema_valid": true, "artifact_types": []},
  "usage": {"latency_ms": 0, "prompt_tokens": null, "completion_tokens": null, "cost": null},
  "errors": []
}
```

该类型只属于 Harness，不取代产品 Schema。

## 4. 现有评测能力与指标可行性

### 4.1 指标分级

| 指标 | 当前可获得数据 | 计算类型 | 额外要求 | 当前可靠性 |
|---|---|---|---|---|
| 路径准确率 / Macro-F1 | DiagnosisResult.final path | 确定性计算 | 法律专家 Gold path、规则版本 | 高（有 Gold 后） |
| 节点级准确率/覆盖率 | matched_rule_id；输入 q 字段 | 确定性计算 | Gold node labels；补 decision trace | 中；当前只充分记录命中节点 |
| 边界准确率 | q3/q4 数值和 rule id | 确定性计算 | 成对边界 cases | 高 |
| 事实抽取 Precision/Recall/F1 | FactItem/normalized answers | 确定性计算 | Gold facts、字段对齐与容差规则 | 中高 |
| 缺失事实召回率/精确率 | unknown、questions、missing_materials | 确定性计算 | Gold missing_fact_ids/must_ask | 中；需统一投影 |
| 追问适当率 | ClarificationResult/questions | LLM Judge + 人工 | 问题必要性/不重复/信息增益 rubric | 低至中 |
| 拒答/人工分流准确率 | confidence、review flags、abstained | 确定性 + 专家 | Gold decision_action | 当前无统一 abstain，需 Adapter |
| Recall@K/MRR/nDCG/Precision@K | RAG datasets + ranked hits | 已可确定性计算 | 固定 corpus/index version | 高；现有实现 |
| Cross-jurisdiction/layer leakage | chunk metadata | 已可确定性计算 | 固定 policy | 高 |
| Citation source/article coverage | required source ids、CitationItem | 确定性计算 | Gold citation ids | 中高 |
| Citation relevance | query/claim/citation text | LLM Judge 或专家 | judge rubric/专家抽查 | 中 |
| Citation faithfulness/entailment | 最终 claim 与条文 | LLM Judge + 法律专家 | Claim 切分；当前无 ClaimItem | 当前无法可靠全量计算 |
| Evidence graph coverage | Issue/Evidence refs | 确定性计算 | Gold required edges 或完整性规则 | 中 |
| Schema 通过率 | Pydantic/JSON schema | 已可确定性计算 | 固定 schema version | 高 |
| 一致性问题数/密度 | consistency_issues | 已可计数 | 统一分类；避免把 warning 当 error | 中 |
| Unsupported-claim rate | must_not_claim substring | 现有确定性弱指标 | Claim splitter + judge/专家 | 当前仅启发式 |
| 章节/模板覆盖 | chapter ids/sections | 确定性计算 | Gold required sections | 高 |
| 文件交付成功率 | output_files + exists/hash | 确定性计算 | 隔离输出目录 | 高 |
| 运行时延 | runner wall clock、trace timestamps | 确定性计算 | Harness 统一计时 | 高；历史 manifest 不完整 |
| Token | LLM metadata | 确定性计算 | 所有调用统一采集/聚合 | 中低；历史 response 多只有 content |
| 调用成本 | token×price | 确定性计算 | provider/model price snapshot | 当前不可可靠历史回算 |
| 失败率/重试率 | status/error/attempts | 确定性计算 | 稳定 error taxonomy | 高（新运行） |
| 法律正确性/时效性 | path、basis、report | 法律专家 | 冻结 as_of_date、法域、版本、双人复核 | 必须专家 |
| 报告可用性 | 文本/文件 | 专家 + 用户评审 | rubric：完整、准确、可操作、边界 | 不能只用 LLM Judge |

### 4.2 指标计算原则

- 第一轮主指标必须尽量 deterministic：path exact match、matched rule、missing fact F1、Recall@K、schema pass、artifact success、latency、failure rate。
- LLM Judge 只用于不能直接比较的解释质量、追问信息增益、引用相关性和报告可读性；Judge 结果必须保存 prompt、model、temperature 和原始判定。
- 法律专家必须决定 Gold path、规则节点、适用/不适用条款、是否应追问/分流，以及报告中的高风险法律结论。LLM Judge 不得替代此部分。
- 任何报告总分必须保留分层子指标，避免“文风好”抵消路径错误或引用污染。

## 5. Baseline 可运行性

### 5.1 统一输入

六个 Baseline 应读取同一 `BenchmarkCase.input`。Adapter 可派生 `DiagnosisAnswers`、检索 query 和下游 payload，但必须保存映射结果与丢失字段，禁止为某个 baseline 人工补充额外事实。

### 5.2 Baseline 对比

| Baseline | 复用组件 | 轻量适配 | 统一输出 | 成本 | 主要风险/可运行性 |
|---|---|---|---|---|---|
| Rule-only | `DiagnosisService._normalize_answers()`、`decision_tree.json`、`_rule_match()`；禁用 LLM | 独立 RuleOnlyAdapter，确保 unknown 不触发 LLM；记录 predicate trace | BenchmarkPrediction | 极低、确定性 | 最易运行；要区分 normalize heuristics 与纯原始规则 |
| Direct LLM | `LLMClient.chat_with_metadata()` + `DiagnosisResult` JSON schema | 新增一个评测 prompt adapter；不提供 RAG/规则结果 | 同上 | 中；每 case 1 次调用 | Prompt/模型敏感；需严格 JSON repair 和 invalid 计分 |
| Basic RAG | `retrieve_regulations()` + LLMClient | query builder；把 top-k 文本直接拼 prompt | 同上 | 中；检索+1 LLM | 当前 HashingEmbedder；检索结果可能缺 diagnosis 所需事实逻辑 |
| Structured Prompt + RAG | DiagnosisAnswers 字段说明、RetrievalOrchestrator、结构化 JSON output | structured adapter；显式 facts/nodes/path/missing/citations | 同上 | 中高 | 最有研究价值；不能偷用 rule result，否则与完整系统边界混淆 |
| 当前完整 DataComplyFlow | `DiagnosisService` + downstream assessment/SCC/PIPIA service + trace | FullSystemAdapter 串联并隔离输出 | 同上 + artifacts | 高、多次 LLM/文件 | diagnosis/assessment 可跑；SCC 当前 Bug；下游 route 自动编排不存在 |
| 后续增强版本 | 修复后的系统+Claim/Rule version/Verifier | 与 Full Adapter 相同接口，只换 version | 同上 | 最高 | 作为未来 treatment；本轮不实现，不预设优于当前版本 |

### 5.3 公平性要求

1. 固定 case、as_of_date、knowledge snapshot、top_k、provider/model、temperature、max tokens。
2. Rule-only 需明确两种口径：`raw_rule`（不做 Agent）和 `normalized_rule`（允许现有 normalize heuristics）。否则对比不公平。
3. Direct LLM 不得看到 Gold、rule result 或 retrieval；Structured RAG 不得调用系统 path rule；Full system 才允许完整编排。
4. 所有 LLM baseline 至少运行 3 seeds 或 3 重复；Rule-only 运行一次。
5. 失败、超时、invalid schema 必须计入分母，不能只比较成功案例。

## 6. 最小评测 Harness 方案

### 6.1 目录结构

建议下一轮新增，当前不实施：

```text
qa/benchmark/
  README.md
  schemas/
    case.schema.json
    prediction.schema.json
    run_manifest.schema.json
  datasets/
    cn_path_smoke_v1/
      dataset.jsonl
      gold.private.jsonl
      attachments/
      DATA_CARD.md
  adapters/
    rule_only.py
    direct_llm.py
    basic_rag.py
    structured_rag.py
    datacomplyflow.py
  metrics/
    path.py
    facts.py
    missing_facts.py
    retrieval.py
    evidence.py
    runtime.py
  runner.py
  report.py
  results/                 # gitignored or只提交脱敏汇总
```

若希望最小化新增顶层目录，也可将代码放 `backend/benchmark/`，数据保留 `qa/benchmark/`。不建议把 Harness 塞进现有 `backend/common/rag/eval.py`，因为本项目标已超出 RAG。

### 6.2 Case Schema

```json
{
  "case_id": "CN-PATH-SMOKE-001",
  "dataset_version": "cn_path_smoke_v1",
  "jurisdiction": "cn",
  "task": "cross_border_path_diagnosis",
  "as_of_date": "YYYY-MM-DD",
  "source_type": "synthetic|expert_authored|deidentified_real|derived",
  "source_case_ids": [],
  "sensitivity": "public|internal|restricted",
  "input": {"diagnosis_answers": {}, "free_text": "", "attachment_refs": []},
  "gold": {
    "facts": [],
    "node_decisions": [],
    "final_path": null,
    "matched_rule_id": null,
    "missing_fact_ids": [],
    "decision_action": "answer|clarify|human_review|refuse",
    "must_retrieve_source_ids": [],
    "must_retrieve_article_ids": [],
    "must_not_cite_source_ids": [],
    "downstream_module": null,
    "required_report_sections": []
  },
  "annotation": {"status": "unlabeled|single|adjudicated", "annotator_roles": [], "notes": ""}
}
```

公开 dataset.jsonl 可不含 private Gold；runner 在本地按 case_id 合并 `gold.private.jsonl`。

### 6.3 Runner 与 Adapter

Runner 职责：加载并校验数据→解析 baseline config→为每个 case 创建隔离工作目录→计时→调用 Adapter→捕获异常→校验 prediction→计算 metrics→写 manifest/JSONL/Markdown。

Adapter 统一接口：

```text
prepare(case, run_config) -> PreparedInput
run(prepared) -> BenchmarkPrediction
collect_artifacts(prediction) -> ArtifactManifest
```

不要求业务模块实现统一接口；Adapter 负责：字段映射、禁用/启用 LLM、调用现有 service、将各模块 Result 投影为 BenchmarkPrediction、拷贝或引用输出文件。

### 6.4 Metric 与错误分类

第一版 metric modules：

- `path.py`：path accuracy、macro-F1、rule-id accuracy、boundary pair consistency。
- `facts.py`：exact/normalized match、micro/macro F1、unsupported inferred fact count。
- `missing_facts.py`：missing fact precision/recall、must-ask coverage、unsafe answer rate。
- `retrieval.py`：Recall@K、MRR、nDCG、jurisdiction/layer leakage。
- `evidence.py`：required citation coverage、fact-rule-evidence ref completeness；faithfulness 暂仅抽样专家评。
- `runtime.py`：success/failure/timeout/invalid-schema、latency、tokens、calls、cost（有价格表时）。

错误 taxonomy：

```text
INPUT_SCHEMA_ERROR
ADAPTER_MAPPING_ERROR
AUTH_ERROR
RULE_EXECUTION_ERROR
RETRIEVAL_EMPTY / RETRIEVAL_CONTAMINATION
LLM_TRANSPORT_ERROR / LLM_INVALID_JSON / LLM_REFUSAL
OUTPUT_SCHEMA_ERROR
CONSISTENCY_ERROR
RENDER_ERROR / ARTIFACT_MISSING
TIMEOUT / CANCELED
KNOWN_PRODUCT_BUG
GOLD_UNAVAILABLE / GOLD_DISPUTED
```

### 6.5 Result Manifest

每次运行至少记录：run_id、dataset/version/hash、Git commit/dirty status、baseline id/version、adapter version、Python/package lock hash、OS、start/end/duration、random seed、provider/model/API base（不含 key）、temperature/top_k、knowledge index version/hash、rule file hash、case totals、error counts、token/cost、artifact paths、metric version、judge config。

现有 TraceRecorder 可作为 case-level raw trace，但其 manifest 不足以替代 Benchmark run manifest。

### 6.6 报告输出

最小输出：

- `predictions.jsonl`：逐 case 标准化结果。
- `errors.jsonl`：错误 taxonomy、stack summary、阶段。
- `run_manifest.json`：版本/环境/成本。
- `metrics.json`：总体、按 case type、按 baseline、按路径分组。
- `report.md`：对比表、失败案例、混淆矩阵、边界对、成本/时延。
- `artifacts/<case>/<baseline>/`：只保存允许留存的报告和 trace。

## 7. 当前系统缺口与优先级

### 7.1 Bug

| 缺口 | 影响 | 第一轮前 |
|---|---|---|
| SCC `generate_report()` 使用 `uuid` 但未导入 | Full baseline 的 SCC 下游全部失败 | 若 Smoke 包含 SCC 报告，必须修复；只测 path 可暂缓 |
| CN Flow `_build_context_pack()` 不接受 `per_issue_rag` | CN Flow service/v0 失败 | 本轮中国出境主线不依赖，可延后；全产品 benchmark 前必须修复 |
| v0 DPIA payload 映射返回 400 | v0 baseline 不完整 | 非首轮中国主线，可延后 |
| assessment 两个上下文/检索回归失败 | Structured/Full 输出可比性受影响 | 应在 assessment 下游纳入前定位 |
| knowledge review SQLite teardown 17 errors | 测试污染、Windows 重复执行不稳定 | Harness 本身不依赖；但 CI 可信度建设应修复 |

### 7.2 接口/数据契约问题

- diagnosis 不输出 normalized facts 或完整 decision trace；需 Adapter 重放/投影。
- diagnosis path 只到 `scc_or_certification`，没有最终区分 SCC 与认证。
- 没有统一 downstream handoff executor；评测需显式选择 assessment/SCC/PIPIA。
- SCC/PIPIA facts/issues/evidence 是 dict 列表，assessment 使用公共 Pydantic 类型。
- async API 与测试鉴权预期冲突，不能直接用未认证 TestClient 作为统一 Runner。
- v0 gateway 支持模块不全，不能作为所有 baseline 的唯一入口。

### 7.3 评测基础设施缺失

- 无产品级 Case Schema、Prediction Schema、run manifest、统一 Adapter/Runner/error taxonomy。
- 无 dataset card、license、provenance、sensitivity、lineage、annotation status。
- 无路径 Gold、节点 Gold、missing facts Gold 和人工分流 Gold。
- 无统一 token/cost aggregator；历史 trace 不足以回算。
- 无重复 LLM runs/seed 管理/置信区间。
- 无 gold disagreement/adjudication 记录。

### 7.4 影响 Benchmark 有效性的风险

1. **数据泄漏**：测试案例可能已进入 L3 testcase index；虽 UsagePolicy 禁止 production external report 使用 L3，但 benchmark adapter 必须确认 baseline 看不到对应 Gold/testcase。
2. **同源重复**：知识案例、前端 dev cases、后端 tests 可能是改写版本；随机切分会造成 train/holdout 泄漏。
3. **规则即 Gold**：若 Gold 直接复制 `decision_tree.json` 输出，只能评代码一致性，不能证明法律正确性。必须由专家按 as_of_date 独立确认。
4. **法律时效**：规则与 source metadata 有效期未统一强制；案例必须冻结日期和法规 corpus。
5. **非确定生成**：Markdown hash 不适合作为 LLM 报告主指标；应使用结构/约束/引用/专家 rubric。
6. **来源不明 Trace**：不可把历史运行当真实用户分布估计。

### 7.5 第一轮必须与可延后

第一轮必须：确定 canonical 数据目录；建立 Case/Prediction/Manifest schema；专家标注 12—20 cases；修复涉及的 product blockers；隔离 L3 testcase；记录版本与成本；对 sensitive assets 禁用默认复用。

可以延后：全模块 Schema 统一、ClaimItem 平台化、完整人工审批状态机、云端分布式 runner、报告全文 claim-level 自动验证、全部 170 个知识文件的完整数据审计、CN Flow/非中国模块纳入。

## 8. 建议的 16 案例 Smoke Benchmark

### 8.1 范围

主任务为中国企业数据出境路径诊断；下游只验证 route handoff 和最小报告结构。建议 16 个案例，全部先用专家编写或对现有合成案例去重改写，不直接使用来源不明上传材料。

### 8.2 案例设计

| ID | 类型 | 关键输入变化 | 需专家标注的 Gold 字段 | 可运行 Baseline | 最小检查 |
|---|---|---|---|---|---|
| 01 | 不含 PI/重要数据 | q5、q2 与材料描述一致 | facts、nodes、path、rule、basis、action | 1—5 | path/rule/schema |
| 02 | 合同履行必要 | q6=contract，阈值低，非 CIIO | 同上+是否需补充事实 | 1—5 | path、missing facts |
| 03 | 跨国 HR | q6=HR、receiver=intra-group | 同上 | 1—5 | path、node |
| 04 | 紧急保护 | q6=emergency | 同上 | 1—5 | path、basis retrieval |
| 05 | 法定义务 | q6=legal_duty | 同上 | 1—5 | path、rule |
| 06 | CIIO | q1=yes，其余低风险 | 强制路径、短路节点、下游 module | 1—5 | path、node、handoff |
| 07 | 重要数据 | q2=yes 或专家给出行业事实 | Gold fact、是否人工复核、路径 | 1—5 | fact/path/human review |
| 08 | PI 阈值下界 | q3=999,999 | path、rule、basis | 1—5 | boundary consistency |
| 09 | PI 阈值命中 | q3=1,000,000 | path、rule、basis | 1—5 | boundary consistency |
| 10 | SPI 阈值下界 | q4=9,999 | path、rule、basis | 1—5 | boundary consistency |
| 11 | SPI 阈值命中 | q4=10,000 | path、rule、basis | 1—5 | boundary consistency |
| 12 | SCC/认证默认 | 非豁免、非强评阈值 | path、后续需标注 SCC/认证选择条件 | 1—5 | path/handoff |
| 13 | unknown 重要数据 | q2=unknown，描述模糊 | missing facts、must_ask、decision_action | 1—5 | unsafe answer、question recall |
| 14 | unknown CIIO/冲突 | q1=unknown，企业描述冲突 | human_review/clarify、禁止确定结论 | 1—5 | abstention/safety |
| 15 | 表单—附件冲突 | 表单称无 SPI，材料摘要含 SPI | fact conflict、winner/ask、path provisional | 2—5；Rule-only记录局限 | fact conflict、missing/ask |
| 16 | 下游交付 | 选一个安全评估 case 和一个 SCC/认证 case 作为组合子任务 | downstream module、required sections/citations/artifacts | Full system；1—4仅输出 handoff | schema、artifact、citation、failure |

“1—5”分别指 Rule-only、Direct LLM、Basic RAG、Structured Prompt+RAG、当前完整 DataComplyFlow；增强版本暂不运行。案例 16 可用两个 subcase 执行，但统计时保持一个场景家族，避免总样本假增。

### 8.3 每案数据字段

至少包含：case metadata、q1-q8、必要 m1/m3/m4 字段、自由文本、附件摘要（可选）、as_of_date、source_type、sensitivity、lineage。Gold 至少包含：normalized facts、节点标签、final path、matched rule、missing facts、decision action、must/must-not retrieval source/article、downstream module、required output sections。

本文件不生成任何法律 Gold。路径、法条、unknown 是否可推断、是否需人工分流均由法律专家标注。

### 8.4 最小指标与预期输出

Smoke 阶段最低报告：

- path accuracy / macro-F1；rule-id accuracy；4 个阈值边界 pair consistency；
- fact micro-F1；missing fact recall；unsafe-answer rate；
- Recall@5/MRR、跨法域/层泄漏；
- prediction schema pass、downstream artifact success；
- latency p50/p95、失败率、LLM call/token（能采集时）；
- 每个 baseline 的逐案 prediction、error class、trace path。

不设“必须达到某分数”的伪目标；第一轮的成功标准是 16 案例可重复执行、失败被分类、Gold 可追溯、Baseline 输入一致且结果可比较。

## 9. 实施顺序与工作量判断

### 阶段 A：数据与规则冻结

选择 `_evaluation` 为 canonical；建立 CN Smoke dataset card；对 16 cases 做 lineage 去重；冻结 decision tree hash、法规 corpus/index hash、as_of_date。法律团队双人标注并裁决。

### 阶段 B：最小 Harness

先实现 Case/Prediction/Manifest schema、RuleOnlyAdapter、DirectLLMAdapter、Runner、path/fact/missing/runtime metrics。随后复用现有 retrieval eval 形成 Basic/Structured RAG adapter。

### 阶段 C：Full system

先接 diagnosis；再接 assessment。修复 SCC blocker 后接 SCC/PIPIA handoff。报告阶段只评分结构、约束、引用和失败，不用全文 hash 作为法律质量。

### 阶段 D：扩展

增加真实脱敏案例、重复 runs、专家报告 rubric、claim/citation faithfulness、其他法域和模块。

## 10. 文档结尾要求：行动清单

### 10.1 当前可以直接复用的资产

1. `DiagnosisAnswers`、`DiagnosisResult` 和 `decision_tree.json`，用于 Rule-only 与路径指标。
2. 公共 `FactItem`、`IssueItem`、`EvidenceItem`、`GenerationContextPack`，用于评测投影字段。
3. 300+80 RAG CSV、31 条分层 JSONL、`backend/common/rag/eval.py` 及已运行 v2 回归结果。
4. 7 条 v0 sample/expected、29 条前端 dev cases、10 份知识案例文档，作为候选池而非直接 Gold。
5. 78 个测试文件/约 308 个测试函数，用于提取边界与回归断言。
6. TraceRecorder、25 个历史 manifest 和 facts/issues/evidence/context/chapter traces，用于设计结果结构和错误分析。
7. CitationRegistry、citation map、Pydantic schemas 和现有 renderer checks。

### 10.2 第一轮必须修复的问题

1. 修复 SCC 缺少 `uuid`（若纳入 SCC 下游）；定位 assessment 两项回归失败。
2. 冻结 canonical evaluation 目录并避免 L3 testcase 泄漏。
3. 建立 case id、lineage、source type、sensitivity、as_of_date 和 annotation status。
4. 建立统一 Prediction/Manifest/error taxonomy，确保失败计入分母。
5. 给 Rule-only 明确 raw/normalized 两种口径；统一 LLM baseline 输入与配置。
6. 将 Benchmark 输出隔离到专用临时目录，避免污染 `storage/` 和 Git。

### 10.3 最小 Benchmark 实现方案

以 16 个专家标注 CN path cases 为 v1；实现 5 个 baseline adapters；主评分为 path、node、facts、missing facts、retrieval、schema、failure、latency；仅对代表性安全评估/SCC或认证案例做下游结构和 artifact smoke。新增独立 `qa/benchmark/`，不重构业务模块。

### 10.4 需要法律团队提供的材料

1. 按明确 `as_of_date` 审定的路径规则表及每个节点法律依据。
2. 16 个案例的 Gold facts、node decisions、final path、missing facts、decision action。
3. 每案必须/可选/禁止引用的 source/article ids。
4. SCC 与认证二次分流条件，以及哪些场景必须人工判断。
5. 报告质量 rubric、严重错误清单和专家裁决流程。
6. 可用于内部 Benchmark 的脱敏真实案例及使用授权说明。

### 10.5 需要研究团队进一步调研的问题

1. 如何避免规则输出作为 Gold 造成循环验证；如何设计独立专家 Gold。
2. 同源案例去重、场景家族切分和数据泄漏检测方法。
3. Claim-level citation entailment 的人工/LLM Judge 一致性与校准。
4. 法规版本变化下的 temporal benchmark 和失效规则测试。
5. 小样本下的置信区间、重复运行方差和模型成本—质量曲线。
6. 报告级用户效用指标与法律专家指标如何分层，而非合成单一分数。

### 10.6 下一轮建议修改的文件和任务（本轮不实施）

- 新增 `qa/benchmark/` 下 dataset、schema、adapter、metric、runner、report。
- 修复 `backend/modules/scc/service.py` 的 `uuid` 导入。
- 若扩展到 CN Flow，修复 `backend/modules/cn_flow/service.py` 的 Pipeline 参数契约及 `module_generator.py` 中错误法域 prompt。
- 为 diagnosis 增加只读 decision trace 导出方式；优先通过 Adapter，不先改公共 API。
- 为 LLMClient/Runner 增加聚合 usage/cost 记录，但不得写入 API key。
- 给 `doc/knowledge/_evaluation` 建 DATA_CARD，并将重复 `evaluation/` 标记为历史镜像或移除。
- 新增 Benchmark smoke CI：Rule-only 必跑；LLM baselines 作为显式凭据/预算条件任务。

本轮到此为止，不实施上述代码、规则、Prompt、Gold 或 Benchmark Runner 修改。

---

## 11. 关键证据索引

- 项目事实基线：`docs/handoff/AI4Law_项目事实基线与真实系统理解.md`
- 路径 Schema/规则/服务：`backend/modules/diagnosis/schema.py`、`service.py`、`decision_tree.json`
- 下游：中国 assessment/SCC/PIPIA 的 `schema.py`、`service.py`、fact/issue/evidence builders
- 公共 IR：`backend/common/workflow/`
- RAG 评测：`backend/common/rag/eval.py`、`run_eval.py`、`doc/knowledge/_evaluation/`、`qa/`
- 测试：`backend/**/test_*.py`
- Demo/fixtures：`frontend/src/lib/dev-test-cases.ts`、`demoPayloads.ts`、`dev-presets.ts`
- 历史运行：`storage/traces/`、`storage/reports/`、`storage/uploads/`
- 引用/Trace/LLM：`backend/common/citation/`、`backend/common/trace/`、`backend/common/llm/`
