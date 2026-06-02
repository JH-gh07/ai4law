这部分工作现在已经不是停留在“方案说明”了，代码里实际落成的是一条完整的分层 RAG 主链。按流程看，可以分成 5 个阶段：知识治理、分层入库、检索编排、业务消费、评测回归。

**1. 知识治理层：先把“什么知识能干什么”写死到类型里**
核心类型在 [v2.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/common/knowledge/v2.py:5)。这里把整套分层规则固化成了 `SourceRegistryEntry`、`KnowledgeChunkV2`、`RetrievalRequest`、`RetrievalBundle`、`UsageScopedContext`。也就是每个 chunk 天生就带 `layer`、`source_kind`、`allowed_usage`、`can_be_cited`、`can_enter_external_report`，后面所有链路都按这些字段做约束，而不是靠 prompt 约定。
模块与法域目录在 [registry.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/common/knowledge/registry.py:15) 和 [module_catalog.v1.json](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/doc/knowledge/registry/module_catalog.v1.json:1)。这里已经把 `cn_* / eu_* / us_*` 的模块、可用索引、可用 stage、默认 usage scope 固化好了。运行时优先读仓库种子，缺失才重建，避免每次跑出不同结果。

**2. 分层入库层：按 layer 分流建 chunk，不再混成一个大库**
构建逻辑在 [builders_v2.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/common/knowledge/builders_v2.py:48)。
现在是五类知识分别建：
- `L1 legal`：法规/指南/规范性依据，CN/EU/US 都有，法规按条切；EU/US 会按 source registry 的 `modules` 展开到对应模块。
- `L2 workflow`：业务规则，一个判断步骤一个 chunk，比如 BCR 的 `WF-EU-BCR-BINDING` 明确要求先查 binding effect、enforceable rights、liability、complaint handling，[builders_v2.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/common/knowledge/builders_v2.py:611)。
- `L1 standard_clause`：标准条款专库，不当普通法规处理。比如 BCR/SCC/TIA 都有各自的标准义务 chunk，[builders_v2.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/common/knowledge/builders_v2.py:685)。
- `L4 template`：模板分 `official_template` 和 `example`，只有官方模板能进正式结构控制，[builders_v2.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/common/knowledge/builders_v2.py:255)。
- `L3 testcase`：评测/回归专用，默认不进生产生成链路，[builders_v2.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/common/knowledge/builders_v2.py:446)。

**3. 检索编排层：统一决定“查哪个库、什么时候查、查完给谁用”**
入口在 [orchestrator.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/common/rag/orchestrator.py:95)。`RetrievalOrchestrator.retrieve()` 会按 `module + task_stage` 路由，而不是“所有索引都查一遍”。
真正的硬边界在 [usage_policy.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/common/knowledge/usage_policy.py:6)：
- `external_report` 只能吃 `L1`
- `legal_grounding` 只能吃可引用的 `L1`
- `internal_review` 才能吃 `L1 + L2`
- `structure_control` 只能吃 `L4 official_template`
- `production` 下直接封死 `L3 testcase`
- 还加了 jurisdiction hard gate，防止跨法域串召回

你关心的 `eu_bcr` 在这里的真实流程是：
- `issue_discovery`：先查 `workflow_index_eu`，拿到 BCR 业务规则；
- 同时查 `legal_index_eu`，再按 workflow 的 `reference_ids` 回查法源；
- 如果是条款比对场景，再查 `standard_clause_index_eu`；
- 最终 bundle 分成 `workflow_rules / standard_clauses / legal_grounding / templates / testcases`，不会混成一坨。
对应实现就在 [orchestrator.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/common/rag/orchestrator.py:287)。

**4. 业务消费层：assessment 和 review 已经都改成底层统一委托 orchestrator**
`assessment` 的入口在 [retriever.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/modules/assessment/retriever.py:14)。`AssessmentRetriever.search()` 先走 orchestrator 的 `cn_assessment + legal_grounding`，拿到分层后的 `L1/L2` 结果，再和旧 `retrieve_regulations()` 做兼容合并，外部签名没变。
随后在 [service.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/modules/assessment/service.py:130)，`_build_context_pack()` 会把结果显式拆成：
- `legal_grounding_context`
- `workflow_rule_context`
- `template_context`
- `evaluation_context`
再交给 [build_legal_grounding()](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/modules/assessment/legal_grounding.py:351) 和 [build_generation_basis_pack()](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/modules/assessment/generation_basis.py:91)。
这里最关键的是：`build_legal_grounding()` 明确只接受可引用的 `L1`，如果 binding 不是 `L1_regulatory_evidence` 或 `can_be_cited=false`，直接剔除，[legal_grounding.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/modules/assessment/legal_grounding.py:403)。所以 workflow 规则不会再混进正式 citation。

`review_service` 的入口在 [rag_provider.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/services/review_service/rag_provider.py:11) 和 [service.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/services/review_service/service.py:123)。
它的实际流程是：
- `DocumentClassifier` 先判文档类型和法域，[document_classifier.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/services/review_service/document_classifier.py:58)
- `LocalRegulationKnowledgeBase.lookup()` 再解析 `jurisdiction/module/document_type`，分别发起 `issue_discovery` 和 `clause_compare` 两次 orchestrator 检索，[rag_provider.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/services/review_service/rag_provider.py:19)
- `ClauseReviewer.review()` 先跑 DSL 规则，再跑标准条款比对，再跑 specialized reviewer，再走 LLM/规则兜底，[clause_reviewer.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/services/review_service/clause_reviewer.py:84)
- 标准条款链独立成 `StandardClauseLocator + StandardClauseDiffer`，[standard_clause.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/services/review_service/standard_clause.py:17)
- 差异结果会产出三类 issue：`missing_obligations`、`weakened_obligations`、`added_risky_modifications`，再绑定 structured citations，[clause_reviewer.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/services/review_service/clause_reviewer.py:155)

对 `eu_bcr` 来说，当前具体逻辑是：
- 文本里出现 `binding corporate rules` / `bcr` 时，`lookup()` 会把 module 解析成 `eu_bcr`，[rag_provider.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/services/review_service/rag_provider.py:165)
- orchestrator 在 `issue_discovery` 阶段查 BCR 的 workflow 规则和 EU 法源，[orchestrator.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/common/rag/orchestrator.py:287)
- 如果进入标准条款比对，会用 `STD-EU-BCR-RIGHTS` 这类标准 chunk 去比“是否缺 enforceable rights / complaint handling / liability allocation”这几个核心义务，[builders_v2.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/common/knowledge/builders_v2.py:700)

**5. 评测回归层：不是只实现功能，还把 retrieval/generation 两条 eval 跑通了**
评测逻辑在 [eval.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/common/rag/eval.py:74) 和 [run_eval.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/common/rag/run_eval.py:9)。
现在拆成两条：
- `run_retrieval_eval()`：校验 `Recall@K`、`MRR`、`Forbidden-layer retrieval rate`、`Cross-jurisdiction contamination rate`
- `run_generation_eval()`：校验 `Issue recall`、`Citation correctness`、`Forbidden-source leakage rate`、`Unsupported-claim rate`

评测数据也按法域拆了：
- [retrieval_eval_cases_cn.jsonl](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/doc/knowledge/evaluation/retrieval_eval_cases_cn.jsonl:1)
- [retrieval_eval_cases_eu.jsonl](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/doc/knowledge/evaluation/retrieval_eval_cases_eu.jsonl:1)
- [retrieval_eval_cases_us.jsonl](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/doc/knowledge/evaluation/retrieval_eval_cases_us.jsonl:1)
- [generation_eval_cases_cn.jsonl](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/doc/knowledge/evaluation/generation_eval_cases_cn.jsonl:1)
- [generation_eval_cases_eu.jsonl](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/doc/knowledge/evaluation/generation_eval_cases_eu.jsonl:1)
- [generation_eval_cases_us.jsonl](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/doc/knowledge/evaluation/generation_eval_cases_us.jsonl:1)

一句话总结当前实现状态：
现在这套实现的真实流程已经是“分层建模 → 分层入库 → stage 路由 → usage policy 强过滤 → assessment/review 分流消费 → retrieval/generation 双评测闭环”，不是单纯把旧 RAG 拆成几个索引名而已。