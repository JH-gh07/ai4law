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


---
“知识库中心”在当前代码里不是一个单独服务文件，而是一套分层模块，核心分布在两个目录：

- 知识定义与治理：`backend/common/knowledge/*`
- 检索、索引、编排：`backend/common/rag/*`

如果按逻辑流程来讲，当前相关代码基本可以分成 7 个模块层次。

**1. 知识模型层**
这一层先定义“知识对象长什么样”。

- [backend/common/knowledge/v2.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/common/knowledge/v2.py:5)
  定义了整个 v2 分层体系的核心类型：
  `SourceRegistryEntry`、`KnowledgeChunkV2`、`RetrievalRequest`、`RetrievalBundle`、`UsageScopedContext`
- 这里把知识分成 `L1/L2/L3/L4`
  - `L1_regulatory_evidence`：法规、指南、标准条款，允许正式法源绑定
  - `L2_business_rule`：业务规则，只能内部判断和解释
  - `L3_testcase`：测试案例，只能评测/few-shot
  - `L4_template`：模板，只能结构控制或内部起草
- 这一层的意义是：后面所有模块都不再传“裸文本”，而是传带 policy 的 chunk

**2. 知识治理层**
这一层决定“哪些知识源存在、归哪个模块、默认查哪些索引”。

- [backend/common/knowledge/registry.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/common/knowledge/registry.py:15)
  负责 `source_registry` 和 `module_catalog`
- [doc/knowledge/registry/source_registry.v1.json](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/doc/knowledge/registry/source_registry.v1.json:1)
  是知识源清单，描述 source_id、法域、authority、allowed_usage
- [doc/knowledge/registry/module_catalog.v1.json](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/doc/knowledge/registry/module_catalog.v1.json:1)
  是模块目录，描述 `cn_assessment / eu_bcr / us_privacy_review` 各自能用哪些 index、支持哪些 stage
- `load_module_catalog()` 和 `ensure_source_registry()` 的逻辑是：
  - 仓库里有静态种子就直接读
  - 没有才从 `sources.csv` 重建
- 这一层解决的是“知识库中心怎么被管起来”，不是“怎么检索”

**3. Chunk 构建层**
这一层负责把原始材料变成结构化 chunk。

- [backend/common/knowledge/builders_v2.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/common/knowledge/builders_v2.py:48)
  是当前最核心的构建模块
- 它现在分别构建：
  - `build_legal_chunks_cn/eu/us()`：法规、指南、规范条文
  - `build_workflow_chunks_cn/eu/us()`：业务规则 chunk
  - `build_standard_clause_chunks_cn/eu/us()`：标准条款比对专用 chunk
  - `build_template_chunks_cn/eu/us()`：模板 chunk
  - `build_testcase_chunks_cn/eu/us()`：评测案例 chunk
- 它的逻辑不是统一切分，而是按知识用途切：
  - 法规按条切
  - workflow 按一个判断步骤切
  - standard clause 按一条标准义务切
  - template 按 section/slot 切
  - testcase 按一个案例切
- 这一层是“知识入库前的结构化工厂”

**4. 索引生成层**
这一层把 chunk 变成可检索资产。

- [backend/common/rag/ingest.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/common/rag/ingest.py:89)
  `build_multi_index_v3()` 会把各类 chunk 输出成：
  - `storage/rag/v3/*.jsonl`
  - `storage/rag/v3/*.vector.json`
- 旧版单法规索引构建还保留在同文件的 `build_regulation_index()`
- 当前索引资产是多索引：
  - `legal_index_*`
  - `workflow_index_*`
  - `standard_clause_index_*`
  - `template_index_*`
  - `testcase_index_*`
- 这一层本质上做两件事：
  - 写 authoritative jsonl
  - 写向量索引 payload

**5. Usage Policy 层**
这一层是分层 RAG 的硬闸门，决定“检到了也不一定能用”。

- [backend/common/knowledge/usage_policy.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/common/knowledge/usage_policy.py:6)
  `UsagePolicyFilter.filter()` 是统一入口
- 核心规则现在已经写死：
  - `external_report` 只允许 `L1`
  - `legal_grounding` 只允许可引用的 `L1`
  - `internal_review` 才允许 `L1 + L2`
  - `structure_control` 只允许 `official_template`
  - `production` 下直接禁用 `L3_testcase`
  - 如果法域不匹配，直接 reject
- 这一层的作用非常关键：
  它防止“多库虽然拆了，但生成时还是混用”

**6. 检索编排层**
这一层决定“查哪个库、查多少、先查什么、后查什么”。

- [backend/common/rag/orchestrator.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/common/rag/orchestrator.py:95)
  `RetrievalOrchestrator` 是整个知识库中心的调度器
- 它接收 `RetrievalRequest(module, task_stage, query, facts, jurisdiction, path...)`
- 然后按模块和阶段走不同逻辑：
  - `cn_diagnosis`：先 workflow，再按 `reference_ids` 回查 legal
  - `cn_assessment`：`issue_discovery/legal_grounding/report_generation/evaluation` 分段查不同索引
  - `cn_review`：`issue_discovery/clause_compare/report_generation/evaluation` 分段走
  - `eu_* / us_*` 也是同样的 stage-based routing
- 这个编排器最终返回 `RetrievalBundle`
  里面已经分成：
  - `legal_grounding`
  - `workflow_rules`
  - `standard_clauses`
  - `templates`
  - `testcases`
- 这一步之后，下游业务模块拿到的就不是“一个召回列表”，而是“分流后的上下文包”

**7. 兼容检索层**
旧链路没有被删，而是被保留成兼容入口。

- [backend/common/rag/retriever.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/common/rag/retriever.py:234)
  这里是旧的 `RegulationRAGService`
- [backend/common/rag/retriever.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/common/rag/retriever.py:369)
  `retrieve_regulations()` 还是老入口
- 它的逻辑是：
  - vector 检索
  - lexical 打分
  - heuristic rerank
  - jurisdiction/path/doc_type filter
- 这个模块现在的角色更像：
  - 旧代码兼容层
  - fallback 检索层
  - 单法规检索工具
- 新主路径已经逐步由 orchestrator 接管，但旧接口还活着

**8. 业务消费层**
知识库中心本身不直接生成报告，它被 assessment 和 review 消费。

- [backend/modules/assessment/retriever.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/modules/assessment/retriever.py:14)
  `AssessmentRetriever.search()` 先走 orchestrator，再兼容合并旧法规命中
- [backend/modules/assessment/service.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/modules/assessment/service.py:130)
  `_build_context_pack()` 把结果拆成：
  `legal_grounding_context / workflow_rule_context / template_context / evaluation_context`
- [backend/modules/assessment/legal_grounding.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/modules/assessment/legal_grounding.py:351)
  `build_legal_grounding()` 只允许 `L1` 进正式 citation 绑定
- [backend/services/review_service/rag_provider.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/services/review_service/rag_provider.py:11)
  `LocalRegulationKnowledgeBase.lookup()` 是 review 侧知识接入门面
- [backend/services/review_service/clause_reviewer.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/services/review_service/clause_reviewer.py:54)
  `ClauseReviewer` 消费 `workflow_rules + standard_clause_candidates + structured_citations`
- [backend/services/review_service/standard_clause.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/services/review_service/standard_clause.py:17)
  标准条款链单独拆出来了：
  `StandardClauseLocator` + `StandardClauseDiffer`

**9. 外部 API 增强层**
这一层不是 authoritative source，而是增强检索补充。

- [backend/services/legal_api_service.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/services/legal_api_service.py:10)
  现在封装的是 `DeliLegalService`
- 它提供：
  - `search_laws()`
  - `search_cases()`
- 这类 API 当前主要用于：
  - assessment 某些 high/blocker issue 的补充法条/案例
  - review 侧额外补 citation/case reference
- 它不是当前知识库中心的主数据源，而是外围增强层

**10. 评测回归层**
最后一层负责验证知识库中心没有乱用知识。

- [backend/common/rag/eval.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/common/rag/eval.py:74)
  `run_retrieval_eval()`
- [backend/common/rag/eval.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/common/rag/eval.py:322)
  `run_generation_eval()`
- [backend/common/rag/run_eval.py](/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/backend/common/rag/run_eval.py:9)
  命令行总入口
- 这里验证的不是“能不能检到”，而是：
  - 有没有召回错误法域
  - 有没有把 testcase/template 当法规用
  - 正式引用是不是只来自允许的 `L1`
  - 标准条款差异有没有识别出来

一句话总结当前逻辑流程：

`source_registry/module_catalog`
→ `builders_v2` 把原始材料变成分层 chunk
→ `ingest.py` 生成多索引资产
→ `RetrievalOrchestrator` 按模块和 stage 编排检索
→ `UsagePolicyFilter` 做 usage/jurisdiction 强约束
→ `assessment/review` 按分流结果消费
→ `eval.py` 做 retrieval/generation 回归验收

如果你愿意，我下一步可以继续给你画一版更细的“模块调用链图”，直接按下面三条分别讲：
1. `assessment` 从请求到报告的完整调用链  
2. `review_service` 从上传文档到 issue 输出的完整调用链  
3. “新增一类知识源”时到底要改哪些模块、先后顺序是什么