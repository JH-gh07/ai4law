accessment详细细节
你这套系统里 assessment 至少有两层含义：“安全评估路径”（业务语义）+ RAG 检索的 path=assessment 过滤/纠偏开关（工程语义）。

1) 业务上：assessment = 走“数据出境安全评估”这条合规路径（确定性规则树）  
在“模块一：合规路径诊断”里，判断逻辑是一个硬规则决策树：  
- Q1 是 CIIO ⇒ 直接判 assessment（必须申报安全评估）  
- Q2 涉及重要数据 ⇒ 判 assessment  
- Q3 累计出境个人信息 ≥ 100万人 ⇒ 判 assessment  
- Q4 累计出境敏感个人信息 ≥ 1万人 ⇒ 判 assessment  
对应文档流程图见：doc/principle4modal/user.md:45（一直到 doc/principle4modal/user.md:66）。  
逻辑原理就是：这些条件在你们文档里被当作“法律明文的阈值触发器”，所以不靠 LLM 做模糊判断，而用状态机/规则引擎保证确定性、低延迟、可解释（同段落见 doc/principle4modal/user.md:77）。

举例：  
- 用户填“不是 CIIO、不是重要数据、累计出境 120 万普通个人信息” ⇒ 直接命中 Q3 ⇒ 结论必走安全评估（assessment）。  
- 用户填“不是 CIIO、不是重要数据、普通 20 万、敏感 2 万” ⇒ 命中 Q4 ⇒ 结论也必走安全评估（assessment）。
  
2) 工程上：path=assessment 在做什么（检索阶段的“强约束 + 强提示”）  
在条文检索 retrieve_regulations() 里，path=assessment 会做三件事：

1. Query rewrite：给查询追加“路径强提示词”，把检索空间往安全评估域拉近  
- 规则在 backend/common/rag/retriever.py:108 到 backend/common/rag/retriever.py:175：  
  - PATH_STRONG_HINTS["assessment"] = ("安全评估","assessment","重要数据","100万","10万敏感")（backend/common/rag/retriever.py:108）  
  - _rewrite_query() 会把这些 hint 拼到 query 后面（backend/common/rag/retriever.py:161）。

举例：  
- 你传入：query="数据出境申报材料清单", path="assessment"  
- 实际用于检索的 rewritten_query 会变成类似：  
  - "数据出境申报材料清单 安全评估 assessment 重要数据 100万 10万敏感"（由 backend/common/rag/retriever.py:161 的追加逻辑产生）  
原理：这相当于一个“手工的、可控的 query expansion”，用强特征词提高召回的路径一致性。

2. Path mismatch 直接拦截：防止用户选了 assessment 但 query 明显在问别的路径  
- 见 backend/common/rag/retriever.py:149 到 backend/common/rag/retriever.py:158，并在入口处直接 return []（backend/common/rag/retriever.py:353）。  
  
举例（为什么你 status_report 里会出现“完全无重叠 token”那类问题的工程根源）：  
- 前端/调用方强行传 path="assessment"，但用户 query 是 "标准合同备案流程"  
- query 里包含 PATH_STRONG_HINTS["scc"] 的强提示（比如“标准合同/备案”）  
- _is_path_mismatch() 判断“query 强烈像 scc，但你却要求 assessment” ⇒ 直接返回空结果，避免“错路由”污染。
  
3. 结果过滤 + 重排序加分：优先保留/提升 path=assessment 的条文  
- 过滤：_passes_filter() 会把 doc.path 不匹配的条文过滤掉（backend/common/rag/retriever.py:178 到 backend/common/rag/retriever.py:187）。  
- 重排序：rerank 时命中 path 会加 metadata_bonus（backend/common/rag/reranker.py:51 到 backend/common/rag/reranker.py:57）。  
原理：先“硬过滤”控制主题域，再“软加分”让同主题内容更靠前。

如果你说的 assessment 指的是“模块二安全评估报告生成”那部分（而不是检索 path），我也可以按你们五步链路把每一步的输入/输出结构、关键判断点（例如 CompanyProfile 抽取哪些字段、怎么驱动检索查询）逐段举例拆开讲；你告诉我你更关心“路径诊断的 assessment”还是“条文检索 path=assessment”还是“报告生成的 assessment 模块二”。

1) 入口与任务形态（同步/异步）
- 同步：POST /assessment/generate → 直接跑完整流程并返回 AssessmentResult（backend/modules/assessment/router.py:26）。
- 异步：POST /assessment/generate_async → 先做路径校验，再把完整流程丢进 InMemoryTaskManager 后台执行，用户用 GET /assessment/tasks/{task_id} 轮询（backend/modules/assessment/router.py:47，backend/modules/assessment/service.py:95）。
  
2) 第一个关键判断：是否“允许生成安全评估报告”（路径校验）
- service 一开始会先调用 DiagnosisService().evaluate(...) 用诊断决策树给出 recommended_path 和 rationale（backend/modules/assessment/service.py:46，backend/modules/diagnosis/service.py:31）。
- 然后 _validate_path() 做硬判断：  
  - 若 recommended_path == "security_assessment"：通过（backend/modules/assessment/service.py:152）。  
  - 否则：
    - force_override_path=false（默认）→ 直接抛错，API 返回 400（backend/modules/assessment/service.py:155）。  
    - force_override_path=true → 不阻断，但会返回一个 warning，后面会被写进结果的 consistency_issues 和报告结论里（backend/modules/assessment/service.py:154，backend/modules/assessment/report_renderer.py:64）。

这一步的“逻辑原理”是：先用确定性的诊断模块判路由；assessment 只服务于“安全评估路径”，防止用户在不满足条件时误生成“安全评估报告”。

3) 企业画像抽取（把输入变成可控上下文）
- ProfileExtractor.extract()：把表单字段原样落到 CompanyProfile，并对 uploaded_files 做一次文本解析，只取每个文件前 160 字做 extracted_notes（失败则记 [parse skipped]）（backend/modules/assessment/profile_extractor.py:9）。
- 这里没有 LLM 判断；属于“把输入结构化 + 可追溯摘要”，给后续检索/写作当上下文。

4) 法规检索（RAG）：把“企业画像”变成 TopK 条文命中
- AssessmentRetriever.search() 拼一个检索 query（行业 + 出境目的 + 接收国家 + CIIO/non-CIIO + important data/personal information），然后调用通用 retrieve_regulations() 拿 8 条（默认）法规命中（backend/modules/assessment/retriever.py:16）。
- 这一步的“判断逻辑”主要在 RAG 内部：可能会做 query rewrite、过滤、打分、重排、低命中时外部补检索等（backend/common/rag/retriever.py:337）。
但注意：当前 AssessmentRetriever.search() 没有传 path="assessment"，所以你在 RAG 里为 PATH_STRONG_HINTS["assessment"] 做的“强路径约束/拦截”在本链路里不会生效（backend/common/rag/retriever.py:108）。

5) 第二个关键判断：总体风险等级（用于章节写作口径 + 最终一致性校验）
- 风险等级由 risk_level() 计算：  
  - is_ciio 或 contains_important_data 或 pii_count>=1_000_000 或 spi_count>=10_000 → HIGH  
  - 否则 pii_count>=100_000 → MEDIUM  
  - 否则 LOW（backend/common/risk/scoring.py:1）。
- 这个等级会写进章节生成的上下文块里（让 LLM 用同一口径写作）（backend/modules/assessment/chapter_generator.py:99）。
  
6) 章节生成（LLM 受控写作 + 引用约束）
- AssessmentChapterGenerator.generate() 会：
  - 用企业画像 + 前 5 条法规 snippet 组装 context_block（backend/modules/assessment/chapter_generator.py:75）。
  - 按 _CHAPTER_PROMPTS 逐章调用 _generate_chapter()（backend/modules/assessment/chapter_generator.py:21）。
- 这里的“判断/分支”是：
  - 若 LLM 配置且启用：走真实生成，并强制“每段末尾至少一个引用”（未满足会后处理补齐）ensure_paragraph_citations()（backend/modules/assessment/chapter_generator.py:131）。  
  - 若 LLM 未启用：直接返回“占位内容”（backend/modules/assessment/chapter_generator.py:144）。

7) 第三个关键判断：一致性与对齐检查（防幻觉/防逻辑矛盾）
- ConsistencyChecker.check()：
  - 任意章节没有 citations → 记 issue（backend/modules/assessment/consistency_checker.py:10）。
  - 若满足“强制安全评估条件”（CIIO/重要数据/PII≥100万）但最后一章 risk_level 不是 HIGH → 记 issue（backend/modules/assessment/consistency_checker.py:14）。
  备注：这里的 high_risk 没包含 spi_count>=10_000，和 risk_level() 的 HIGH 条件不完全一致。
- check_cn_alignment()（文本对齐）：
  - 输入 is_ciio=False 但正文提到 CIIO 且没否定语 → issue
  - 输入 contains_important_data=False 但正文提到重要数据且没否定语 → issue
  - 行业/接收国出现明显不一致 → issue（backend/common/quality/alignment.py:19）。
- 路径不匹配 warning（如果用户强制 override）也会被塞进 issues（backend/modules/assessment/service.py:72）。

8) 报告渲染（把章节“落到模板槽位”，并输出 docx/md/zip）
- AssessmentReportRenderer.render()：
  - 把章节内容映射到 docx/md 模板字段，且会对一些槽位做摘要压缩（比如“合法性基础/安全措施/整改建议/结论”取 1–2 句）并附加引用（backend/modules/assessment/report_renderer.py:42）。
  - 若有 path_warning 或 alignment_warning：会在结论前加醒目提示（backend/modules/assessment/report_renderer.py:64）。
  - 输出 outputs/assessment/...docx、...md、...zip（backend/modules/assessment/report_renderer.py:27）。
    
9) 最终结果怎么形成（AssessmentResult）
- AssessmentService.generate_report() 把上述产物汇总成 AssessmentResult：  
  - profile（结构化画像）  
  - regulations（TopK 命中）  
  - chapters（逐章内容 + risk_level + citations）  
  - consistency_issues（包含一致性、对齐、路径 warning）  
  - report_path/output_files（docx/md/zip 路径）（backend/modules/assessment/service.py:75，backend/modules/assessment/schema.py:46）。
    
下面按 10 个来对比（业务逻辑层面）：

- diagnosis（路径诊断）：输入是问卷，核心是“归一化→规则树命中→必要时 AI 推测兜底→出结论与行动清单”，输出是诊断报告（HTML/PDF）和结构化结论；它不做“生成大段报告章节”的主流水线。见 doc/整体开发文档.md:146。
- assessment（安全评估报告）：目标是《数据出境风险自评估报告》；先做路径校验（不匹配默认 400，可 force_override_path 强制继续并写入告警），再 RAG→章节→一致性/对齐→模板渲染（docx/md/zip）。见 backend/modules/assessment/service.py:46、backend/modules/assessment/service.py:151。
- scc（标准合同备案）：目标是标准合同备案材料（通常含 PIPIA/备案要点），业务重点在“标准合同路径的材料与条款要求”，并且文档里标注它可能生成 annotated_docx（对原 docx 批注）；和 assessment 的差异是输出侧更偏“合同备案/合同文本”。见 doc/整体开发文档.md:186-doc/整体开发文档.md:189。
- pipia（个保影响评估）：目标是《个人信息保护影响评估》类报告，业务重点是“个人信息权益影响+风险控制措施”，和 assessment 的“国家安全/公共利益/网信申报口径”不同（你们在更早的模块说明里也强调了评估重点差异）。
- bcr（BCR/约束性企业规则）：目标是集团内部数据传输治理文件/要点，逻辑会更依赖“集团结构、内部约束机制、统一政策”这类输入信号；不太像 assessment 那样靠门槛触发，而是“跨境内部规则体系”的完备性。
- dpia（GDPR DPIA）：法域偏欧盟，目标是 DPIA（Article 35 语境）；业务逻辑更强调“高风险处理活动识别→必要性比例性→风险与缓解措施”，且 RAG 检索会偏 GDPR/EDPB。
- tia（Transfer Impact Assessment）：目标是 TIA；业务逻辑核心是“目的地国家/接收方环境→法律/实践风险→补充措施”，比 DPIA 更聚焦“第三国传输风险”。
- cn_flow（中国流程型交付包）：你们文档里把它归为“docx+md+pdf+xlsx+zip”的重输出模块之一，业务逻辑更像“把流程、清单、表格化交付物一次性打包”，而不是只生成报告正文。见 doc/整体开发文档.md:189。
- cpra（美国/加州 CPRA）：法域偏美国加州；业务逻辑与欧盟/中国不同，更多是“消费者权利、告知/选择退出、服务商/承包商条款、数据共享/出售定义”等框架下的材料生成；输出同样属于“多格式打包”类（docx/md/pdf/xlsx/zip）。见 doc/整体开发文档.md:189。
- review（文档智能审查）：这是闭环任务系统，不是单次“生成一份模板化报告”。它的业务逻辑是“任务+文件→条款切分→分类→逐条审查→聚合→渲染”，并且会落 SQLite（任务、问题列表、摘要等）。见 doc/整体开发文档.md:193、doc/整体开发文档.md:208-doc/整体开发文档.md:216。



大体上你理解对了：除 diagnosis（路径选择）和 review（文档审查闭环）之外，其它那些“文书生成类模块”本质都是同一条流水线，主要差在“输入字段、检索约束、提示词/章节结构、校验规则、模板与输出格式”。


更精确一点说，它们共同的骨架通常是：

- 附件解析/摘要（deterministic，把文件变成可用上下文片段）
- RAG 检索（按法域/路径/关键词拿 TopK 条文，做 citations）
- LLM 生成（按模块 prompts/章节 schema 产出内容；LLM 不可用则降级占位以保证可跑）
- 一致性/对齐检查（可选，不同模块规则不同）
- 模板渲染与打包（docx/md/pdf/xlsx/zip 组合不同）
- 产物登记（报告中心回溯用）
  

所以差异主要体现在：
- schema：收集哪些事实（比如国家/接收方类型/合同条款/处理活动细节等）
- RAG 参数：jurisdiction、path（以及 query rewrite hints）怎么配
- prompts/章节结构：assessment 是“安全评估自评估报告”8 章口径，DPIA/TIA/CPRA 的章节与结论框架不同
- 质量门禁：像 assessment 有“路径不匹配默认 400（可 override）”，某些模块可能没有这类硬门禁
- 输出覆盖：有的只出 docx+md，有的会额外出 pdf/xlsx/zip

但也要注意一个例外：即便都叫“同一条流水线”，有些模块的关键判断比“换 prompt”更重（例如不同法域的路径门槛/风险评级规则、是否必须生成某些附件清单/表格），只是实现形态仍然挂在这条流水线里。

在 assessment 里，“附件解析/摘要”目前是一个非常轻量、确定性的步骤：把每个附件尽量转成纯文本，然后截取前 160 个字符做预览备注。

1) 在哪里做
- 入口在 ProfileExtractor.extract()：backend/modules/assessment/profile_extractor.py:9

它会遍历 payload.uploaded_files，对每个 file_path 调 FileParser.parse_text()，然后：
- preview = content[:160].replace("\n", " ")
- 记录成一条 note："{file_path}: {preview}"（backend/modules/assessment/profile_extractor.py:11-backend/modules/assessment/profile_extractor.py:15）
- 如果解析失败（文件不存在/格式不支持等），记录："{file_path}: [parse skipped] {exc}"（backend/modules/assessment/profile_extractor.py:16-backend/modules/assessment/profile_extractor.py:17）

这些 notes 最终放在 CompanyProfile.extracted_notes（backend/modules/assessment/schema.py:28）。

2) 能解析哪些类型、怎么解析
FileParser 在 backend/common/storage/file_parser.py:7：
- 支持后缀：.txt .md .json .csv .pdf .docx（backend/common/storage/file_parser.py:8）
- .pdf：用 pypdf.PdfReader 逐页 extract_text()，拼接成全文（backend/common/storage/file_parser.py:26-backend/common/storage/file_parser.py:33）
- .docx：用 python-docx 读取段落 + 表格（按行把单元格用 " | " 拼起来），拼接成全文（backend/common/storage/file_parser.py:36-backend/common/storage/file_parser.py:50）
- 其他文本类：直接 read_text(encoding="utf-8", errors="ignore")（backend/common/storage/file_parser.py:23）
  
3) “摘要”到底是什么
- 不是 LLM 摘要，也不是结构化抽取；就是全文的前 160 字符预览（加上路径），用于可追溯展示/调试。
  
4) 一个重要现状
- assessment 的章节生成上下文 context_block 目前没有使用 extracted_notes（backend/modules/assessment/chapter_generator.py:75-backend/modules/assessment/chapter_generator.py:91 只用表单字段 + 法规 snippet）。  
所以附件解析现在更多是“留痕”，还没真正喂给 LLM 写报告。

“留痕”在你们这里指的是：把附件“解析后的文本预览/失败原因”记录下来，作为可追溯的中间证据，但它不一定参与后续生成/检索。

在 assessment 里具体是这样：

1) 什么叫“留痕”？
ProfileExtractor.extract() 会遍历 uploaded_files，把每个文件：
- 能解析 → 取全文前 160 字符做 preview，拼成一条 note
- 解析失败 → 也记一条 note（包含失败原因）
  
这些 notes 存到 CompanyProfile.extracted_notes（backend/modules/assessment/profile_extractor.py:9，backend/modules/assessment/schema.py:28）。

但注意：assessment 的章节生成上下文目前只用“表单字段 + 法规命中”，没有把 extracted_notes 放进 prompt（backend/modules/assessment/chapter_generator.py:75）。所以它更像“运行痕迹/可解释性材料”，而不是“真正参与推理的输入”。

2) 附件是怎么解析成文本的？
解析器是 FileParser.parse_text()（backend/common/storage/file_parser.py:10）：
- 支持：.txt .md .json .csv .pdf .docx（backend/common/storage/file_parser.py:8）
- .pdf：pypdf.PdfReader 按页 extract_text() 拼接（backend/common/storage/file_parser.py:26）
- .docx：python-docx 读段落 + 表格（A | B | C 形式）拼接（backend/common/storage/file_parser.py:36）
- 其他文本类：直接 read_text(..., errors="ignore")（backend/common/storage/file_parser.py:23）
  
3) 那 RAG 到底是怎么做的？（assessment 这条链路）
assessment 的 RAG 入口在 AssessmentRetriever.search()（backend/modules/assessment/retriever.py:16）：

3.1 先构造 query（不是用附件文本）
它把这些字段拼成 query：
- industry + transfer_purpose + receiver_country + (CIIO/non-CIIO) + (important data/personal information)  
见 backend/modules/assessment/retriever.py:17。

3.2 调用通用检索 retrieve_regulations()
关键参数是：
- jurisdiction="cn"
- path="assessment"（会触发“安全评估路径”的 query rewrite / 路径一致性约束）
- top_k=8（默认）
见 backend/modules/assessment/retriever.py:26-backend/modules/assessment/retriever.py:32。

3.3 retrieve_regulations() 内部的判断与算法骨架
在 backend/common/rag/retriever.py:337：

1. Query rewrite（强提示词追加）  
_rewrite_query(query, jurisdiction, path) 会把法域/路径的 hints 追加到 query 末尾（backend/common/rag/retriever.py:161）。  
path="assessment" 的 hints 在 backend/common/rag/retriever.py:108。

2. 三类硬拦截（直接返回空）  
- off-topic（明显跑题词）→ 空  
- jurisdiction mismatch（query 强烈像 EU/US 但你要求 cn）→ 空  
- path mismatch（query 强烈像 scc/review 但你要求 assessment）→ 空  
见 backend/common/rag/retriever.py:348-backend/common/rag/retriever.py:354。

3. 向量召回 + 词法打分 + 混合分  
RegulationRAGService.retrieve() 会：
- 用 LocalVectorStore.search() 做向量召回（候选池比 top_k 大，rag_candidate_pool_size）（backend/common/rag/retriever.py:249）
- 对每个候选算 lexical_score（规则加分：法名/条号/词重叠/keywords 等）（backend/common/rag/retriever.py:260）
- mode="hybrid" 时 base_score = vector*0.7 + lexical*0.3（backend/common/rag/retriever.py:266）
  
4. 过滤 + 分数门槛 + rerank + 去重  
- _passes_filter() 做 jurisdiction/path/doc_type 过滤（backend/common/rag/retriever.py:258）
- score_floor 低于门槛剔除（backend/common/rag/retriever.py:279）
- HeuristicReranker 结合短语命中/重叠/keyword/metadata（jurisdiction/path）再排一次（backend/common/rag/retriever.py:284，backend/common/rag/reranker.py:51）
- 同一“法规名+条号”去重后输出 top_k（backend/common/rag/retriever.py:292）
  
5. 外部兜底检索（可选）  
如果本地命中 < min_local 且启用 DeliLegalService，会去外部补几条（backend/common/rag/retriever.py:366-backend/common/rag/retriever.py:391）。

6. 可选日志留痕（RAG hits）  
通过环境变量开启会把 query/rewritten_query/命中条文写到 jsonl（backend/common/rag/retriever.py:411）。

如果你想把“附件内容”真正纳入 RAG（而不是只做留痕），一般就是：用 extracted_notes（或更长的附件摘要）参与 AssessmentRetriever.search() 的 query 构造，或做一个“附件→关键词/实体→检索 query”步骤。你希望附件影响检索的方式是“拼到 query”还是“作为额外字段参与 rerank”？

对你们这批“文书生成类模块”，差异基本都落在这 5 类细节里（我用现有代码逐个对齐到具体实现点；assessment 因为拆了多个文件，我也一并对照）：

1) 输入字段（schema）差在哪
核心区别是：有的模块只要“少量表单 + 文件路径列表”，有的模块把事实拆成强结构化对象 + 附件角色，还有的模块输入本身就是“审查清单/差距域”。

- assessment：扁平字段 + uploaded_files: list[str]，并带 force_override_path 这种“路径门禁开关”。见 backend/modules/assessment/schema.py:6。
- scc：扁平字段（接收方、目的、规模、是否已有草案）+ uploaded_files。见 backend/modules/scc/schema.py:4-backend/modules/scc/schema.py:12。
- pipia：强结构化（company_profile/transfer_context/personal_info_scope/rights_protection/emergency_plan）+ attachments[*] 且每个附件有 file_role/file_format/storage_uri。见 backend/modules/pipia/schema.py:52-backend/modules/pipia/schema.py:60。
- bcr：输入会包含“审查项/打分/发现问题”的结构（代码里会把 review_items 抽成 problems，并算综合 rating）。见 backend/modules/bcr/service.py:55-backend/modules/bcr/service.py:57。
- dpia：项目型字段（processing_description、lawful_basis、risk_assessment、residual_risk…）+ 附件列表。见 backend/modules/dpia/service.py:63-backend/modules/dpia/service.py:73（context_block里就是输入字段的直出）。
- tia：传输工具、出口方/进口方画像、第三国评估、补充措施、最终结论 + 附件列表。见 backend/modules/tia/service.py:62-backend/modules/tia/service.py:71。
- cn_flow：输入就是“数据类别、实体清单、传输链、附件”，并内置生成 risk_items（结构化风险清单）。见 backend/modules/cn_flow/schema.py:24-backend/modules/cn_flow/schema.py:60（你之前输出里已截到）。
- cpra：输入是按域拆的合规现状描述（business_model、rights_process、opt_out…）+ 附件（还支持 file_format="url"）。输出会先生成结构化 gap_items。见 backend/modules/cpra/schema.py:17-backend/modules/cpra/schema.py:25、backend/modules/cpra/schema.py:28-backend/modules/cpra/schema.py:35。
  
一句话：有的模块把“事实”交给 LLM写，有的模块先把“差距/风险项”用规则结构化出来再让 LLM写（比如 cpra/cn_flow/bcr）。


---

2) 检索约束（RAG 参数）差在哪
你们的 RAG 统一走 retrieve_regulations(query, jurisdiction, path, top_k, ...)，模块差异主要是：

(a) 法域不同
- CN 系列：assessment/scc/pipia 用 jurisdiction="cn"（assessment 在 backend/modules/assessment/retriever.py:26；scc 在 backend/modules/scc/service.py:80；pipia 在 backend/modules/pipia/service.py:63）。
- EU 系列：dpia/tia/bcr 用 jurisdiction="eu"（backend/modules/dpia/service.py:53，backend/modules/tia/service.py:52，backend/modules/bcr/service.py:63）。
- US 系列：cn_flow/cpra 用 jurisdiction="us"（backend/modules/cn_flow/service.py:54，backend/modules/cpra/service.py:55）。
  
(b) path 过滤/纠偏不同
- assessment：明确传 path="assessment"（backend/modules/assessment/retriever.py:30）。
- scc：传 path="scc"（backend/modules/scc/service.py:81）。
- pipia：根据 route_type 动态选择 path：scc_filing → "scc"，否则 "all"（backend/modules/pipia/service.py:64）。
- dpia/tia/bcr/cn_flow/cpra：当前都用 path="all"（例如 backend/modules/dpia/service.py:54）。
  
(c) query 构造侧重点不同
- assessment：query 来自企业画像（行业、目的、国家、CIIO/重要数据标记等）在 AssessmentRetriever.search() 里拼出来（backend/modules/assessment/retriever.py:17）。
- scc/pipia：query 更“模板化关键词 + 目的 + 国家/地区”（backend/modules/scc/service.py:78，backend/modules/pipia/service.py:61）。
- dpia/tia/bcr/cn_flow/cpra：query 是“该报告类型 + 法规关键词”的固定短语（如 DPIA GDPR Article35 ...、TIA EDPB ...、CPRA CCPA ...、EO 14117 ...），更多是为了把检索锚定在专属语料域（对应 service 里的 retrieve_regulations 调用行）。
  

---

3) 提示词/章节结构差在哪
你们生成章节主要有两种实现形态：

(a) assessment：独立 chapter_generator.py，章节 prompt 字典更“长/严格”
- 章节结构是 8 章且带严格引用约束、缺失写“未提供”等规则（backend/modules/assessment/chapter_generator.py:15-backend/modules/assessment/chapter_generator.py:72）。
  
(b) 其他模块：统一用 generate_chapter(llm, module_key, title, context_block, citations)
- 每个模块在 service.py 里维护自己的 *_CHAPTERS 列表，然后循环调用 generate_chapter（例如 pipia：backend/modules/pipia/service.py:32-backend/modules/pipia/service.py:40 + backend/modules/pipia/service.py:87-backend/modules/pipia/service.py:99）。
- bcr 是个明显例外：有些章节直接 deterministic 写死（“合规评级”“详细审查结果”），只有剩余章节才让 LLM写（backend/modules/bcr/service.py:213-backend/modules/bcr/service.py:221）。
- scc 的 context_block 会把“已上传文件摘要”塞进去（backend/modules/scc/service.py:98），而 assessment 当前并没有把 extracted_notes 喂给章节生成（backend/modules/assessment/chapter_generator.py:80-backend/modules/assessment/chapter_generator.py:91）。
  

---

4) 校验规则差在哪（consistency / alignment / rule-based items）
这块差异最大：有的模块几乎没校验，有的模块校验很“业务化”。

- assessment：有硬门禁（诊断路径不匹配默认 400，允许 override 留告警）+ 一致性检查 + check_cn_alignment() 对齐检查（backend/modules/assessment/service.py:59-backend/modules/assessment/service.py:74，backend/modules/assessment/consistency_checker.py:10-backend/modules/assessment/consistency_checker.py:17）。
- scc/pipia：都会跑 check_cn_alignment()（backend/modules/scc/service.py:132，backend/modules/pipia/service.py:103），并各自有“附件角色”类一致性校验：
  - pipia：route_type == scc_filing 必须有 file_role=="scc_contract"；route_type == certification 必须有 certification_material；SLA>72 小时提示等（backend/modules/pipia/service.py:185-backend/modules/pipia/service.py:199）。
- dpia/tia：风险等级不是用 risk_level() 的门槛，而是用文本关键字把 residual_risk/结论“粗分类”成 HIGH/MEDIUM/LOW（backend/modules/dpia/service.py:157-backend/modules/dpia/service.py:165；backend/modules/tia/service.py:155-backend/modules/tia/service.py:163），并做少量规则一致性（例如合法利益需平衡测试、HIGH 残余风险建议 prior consultation；TIA 需要 country_law_analysis 附件等）。
- cn_flow/cpra/bcr：先生成结构化清单再出报告：
  - cn_flow：先 risk_items → 算 overall level → 再生成章节/渲染（backend/modules/cn_flow/service.py:49-backend/modules/cn_flow/service.py:65）。
  - cpra：先 gap_items → 算 overall level → 再生成章节/渲染（backend/modules/cpra/service.py:50-backend/modules/cpra/service.py:66）。
  - bcr：先 problems + rating（审查清单抽取/评分），再生成章节（backend/modules/bcr/service.py:55-backend/modules/bcr/service.py:72）。
    

---

5) 模板与输出格式差在哪
共性：都走 docx/md 模板映射（render_docx_template/render_markdown_template），但输出组合不同。

- assessment/pipia/bcr/dpia/tia：基本是 docx + md + zip（assessment 在 backend/modules/assessment/report_renderer.py:27；其余在各自 service 的 _render()）。
- scc：docx + md，并且额外支持生成“批注修订版 docx”（render_commented_docx，backend/modules/scc/service.py:15，以及输出路径 outputs/scc/...批注修订版...，backend/modules/scc/service.py:226）。
- cn_flow/cpra：除了 docx + md + zip，还会额外生成 pdf + xlsx 并一起打包（backend/modules/cn_flow/service.py:255-backend/modules/cn_flow/service.py:284；backend/modules/cpra/service.py:270-backend/modules/cpra/service.py:293）。这两者会把“输入摘要/清单摘要/附件解析摘要/各章内容”组装成 sections 用于 render_pdf_report()（backend/modules/cn_flow/service.py:243-backend/modules/cn_flow/service.py:250；backend/modules/cpra/service.py:259-backend/modules/cpra/service.py:266）。


6）业务上的区别
  
  你理解得基本对：在你这份代码里，美国/欧盟这几块“没有做 path 级分流”——它们调用 RAG 时基本都是 path="all"，主要靠 jurisdiction（us/eu）+ 固定 query 关键词来把检索锚定到对应语料域。
  
  - US：cn_flow、cpra 都是 retrieve_regulations(... jurisdiction="us", path="all")（backend/modules/cn_flow/service.py:51，backend/modules/cpra/service.py:52）。
  - EU：bcr、dpia、tia 都是 retrieve_regulations(... jurisdiction="eu", path="all")（backend/modules/bcr/service.py:60，backend/modules/dpia/service.py:50，backend/modules/tia/service.py:49）。
    
  你说“欧盟四个审查”，但当前 backend/modules/ 里欧盟相关的文书生成模块实际是 3 个：bcr/dpia/tia（没有第 4 个模块目录）。如果你指的是别处的“4条欧盟路径/4类审查任务”，你告诉我名字我再对齐。
  
  下面回答“美国两个之间、欧盟三个之间各自区别”：
  
美国两类：cn_flow vs cpra
  - cn_flow（对华数据流动/EO 14117 风险评估）
    - 核心中间产物：先生成结构化 risk_items（风险清单），再算总体风险等级（backend/modules/cn_flow/service.py:49-service.py:51）。
    - 输出形态更重：docx + md + pdf + xlsx + zip，其中 xlsx 是风险清单表格，pdf 还会拼“输入摘要/风险摘要/附件摘要/章节内容”（backend/modules/cn_flow/service.py:243-service.py:284）。
    - 本质：偏“风险矩阵/清单交付”，报告章节是对 risk_items 的解释性包装。
  - cpra（加州 CPRA 合规全景/整改路线图）
    - 核心中间产物：先生成结构化 gap_items（合规差距清单），再算总体风险等级（backend/modules/cpra/service.py:50-service.py:52）。
    - 输出形态同样重：docx + md + pdf + xlsx + zip，其中 xlsx 是整改路线图（gap items），pdf 同样拼 sections（backend/modules/cpra/service.py:259-service.py:293）。
    - 本质：偏“合规差距盘点 + 整改计划”，章节是对差距域（notice/rights/opt-out/vendor等）的说明。
      
  一句话：cn_flow 是“风险项（risk_items）驱动”，cpra 是“差距项（gap_items）驱动”。
  
欧盟三类：bcr vs dpia vs tia
  - bcr（BCR-C 合规审查报告）
    - 输入/产物：围绕 review_items 做审查，先抽 problems、算综合 rating（backend/modules/bcr/service.py:55-service.py:57）。
    - 章节生成是“半自动”：合规评级、详细审查结果 章节直接 deterministic 写死/拼表；其余才走 LLM（backend/modules/bcr/service.py:213-service.py:221）。
    - 本质：更像“对清单逐项审计的审查报告”。
  - dpia（GDPR DPIA 报告）
    - 风险等级算法：不是门槛函数，而是从 residual_risk/risk_assessment 文本里用关键词粗分 HIGH/MEDIUM/LOW（backend/modules/dpia/service.py:157-service.py:165）。
    - 一致性规则：例如没附件会提示、提到合法利益但没平衡测试会提示、高风险建议监管咨询等（backend/modules/dpia/service.py:167-service.py:175）。
    - 本质：典型 DPIA 写作结构（范围→必要性→风险→措施→剩余风险→签署）。
  - tia（EDPB TIA 报告）
    - 风险等级算法：同样是基于 third_country_assessment/final_conclusion 文本关键词粗分（backend/modules/tia/service.py:155-service.py:163），但关键词侧重“不可/不能/条件性”等。
    - 一致性规则：例如必须有 country_law_analysis 附件、transfer_tool 是 SCC 但结论没评估 SCC 会提示、高风险建议暂停传输等（backend/modules/tia/service.py:165-service.py:174）。
    - 本质：围绕“传输工具 + 第三国法律实践 + 补充措施有效性”的评估闭环。
      
  一句话：bcr 是清单审计型；dpia 是处理活动风险评估型；tia 是跨境传输/第三国风险评估型。
  


---

美国两类审查（业务区别）：CPRA vs EO 14117（你们 cn_flow）
1) CPRA（加州隐私合规“全景审查”）
- 评估对象：企业面向消费者的隐私合规体系（告知、权利响应、出售/共享、敏感信息、服务商/第三方管理等）。
- 核心问题：企业现有制度/流程/文档是否满足 CPRA 的义务要求？差距在哪？整改优先级怎么排？
- 关键输入：隐私政策/notice、DSR 流程、数据生命周期、opt-out 机制、供应商管理材料等（证据型输入）。
- 关键输出：差距清单（gap）+ 整改路线图（短中长期）+ 报告（给管理层/合规团队执行）。
- 决策点：是否存在“高风险差距”（例如 sale/sharing 但无 opt-out、notice 不完整、权利 SLA 不明确、敏感信息处理缺约束等）。
  
2) EO 14117（对华数据流动“交易/限制性风险审查”）
- 评估对象：特定跨境数据流/交易行为是否触发美国对“受关注国家/受限交易”的限制（更偏国家安全与交易限制框架）。
- 核心问题：这条数据流在“数据类别 × 接收实体/链路 × 交易类型”上是否落入限制/高风险区？应当禁止、缓释还是可放行？
- 关键输入：数据类别、是否敏感/受限、接收方实体清单、传输链条、用途场景、受限主体筛查结果等（“交易/链路”型输入）。
- 关键输出：风险项清单（risk items）+ 红黄绿结论/处置建议 + 需要补充的控制措施与决策留痕。
- 决策点：是否存在受限主体/受限数据类别/受限交易组合，决定“禁止/高度受限/可控放行”。
  
一句话：CPRA 是“消费者隐私治理差距审计”，EO14117 是“特定跨境数据流的限制性风险裁定”。


---

欧盟三（业务区别）：DPIA / TIA / BCR 
1) DPIA（数据保护影响评估）
- 评估对象：一个具体的数据处理活动（processing operation），尤其是“高风险处理”。
- 核心问题：该处理活动是否必要且比例适当？对数据主体权利自由的风险是什么？措施是否足以把风险降到可接受？
- 关键输出：风险识别→影响分析→控制措施→剩余风险→签署/复核（必要时触发监管咨询）。
- 决策点：剩余风险是否仍高到“不可接受/需 prior consultation/需调整处理”。
  
2) TIA（跨境传输影响评估，第三国风险为核心）
- 评估对象：一次跨境传输安排（transfer arrangement），核心围绕“第三国法律/实践”对保护水平的影响。
- 核心问题：所选传输工具（通常 SCC 等）在目的地国家是否会被政府访问/法律义务等因素削弱？补充措施是否能弥补？
- 关键输出：第三国法律实践分析 + 传输工具有效性结论 + 补充措施包 + 最终是否继续/暂停传输建议。
- 决策点：传输工具是否“有效”；无效时是否必须暂停/更换路径/加强措施。
  
3) BCR（Binding Corporate Rules，集团内部规则审查/建设）
- 评估对象：跨国集团内部的数据传输治理体系（组织规则/约束机制）。
- 核心问题：集团内部规则是否覆盖必要要素（主体适用范围、权利保障、责任与救济、审计与问责、对外转移控制等），能否作为集团内传输的长期机制？
- 关键输出：要素清单审查结果 + 缺口/整改清单 + 形成可提交/可落地的 BCR 文档体系建议。
- 决策点：关键要素是否齐全、责任链是否闭环、可执行性（审计、培训、投诉处理、对外转移约束）是否达标。
  
4)（如果你说的“欧盟第4个”是 SCC 审查/适用性判断）
- 评估对象：对外传输时的合同工具（Standard Contractual Clauses）是否适用、条款是否落地、配套措施是否到位。
- 核心问题：SCC 是否是合适的传输工具？合同条款是否正确选择模块、是否有冲突、是否补齐技术/组织措施与执行机制？
- 关键输出：SCC 使用结论 + 合同差距/修订建议 + 与 TIA/技术措施的配套清单。
- 决策点：能否靠 SCC+措施达到“本质等同保护”；否则需要换工具或停止传输。
  
一句话：DPIA 看“处理活动本身风险”，TIA 看“第三国+传输工具风险”，BCR 看“集团内部治理机制”，SCC 看“合同工具与条款落地”。
你可以把 AI4Law 当成一个“合规工作流工具箱”，目标不是替你做最终法律结论，而是把跨境/隐私合规这类工作拆成可执行的步骤：先判路径、再准备材料、再生成草案、最后做条款审查与整改清单。

下面用“业务在干什么 + 每个功能的逻辑是什么”来解释（尽量按你们现有模块的真实分工）。


---

一句话总览：业务在干什么
企业要做数据出境/隐私合规时，通常要解决两类问题：

1. 我应该走哪条合规路径？（路径判断、豁免判断、门槛判断）  
2. 走这条路径要交什么材料、报告怎么写、合同有没有问题、风险怎么落地整改？（检索法规→生成报告草案→审查合同→输出清单与路线图）
  
你们系统就是把这两类问题拆成模块：

- diagnosis：解决 1（规则树/门槛/豁免）
- 其它“文书生成类”（assessment/scc/pipia/dpia/tia/bcr/cpra/cn_flow）：解决 2（报告/清单/路线图）
- review：对“合同文件”做闭环审查（切条款→分类→逐条问题→报告落库）
  

---

模块 1：diagnosis（路径选择）在干什么？逻辑是什么？
业务目的：回答“这次数据出境/跨境传输，合规上优先走哪条路径？是否可能豁免？”

核心逻辑（确定性为主）：
- 先把问卷里 unknown/缺失 用扩展字段做保守补全（归一化）
- 再按 decision_tree.json 从上到下命中第一条规则（豁免优先、门槛其次、最后默认）
- 只有规则无法收敛时才允许 LLM 给“推测结论”，并降低置信度、标注不确定
  
输出是什么：不是一段话，而是结构化结果：
- recommended_path（安全评估 / SCC或认证 / 豁免等）
- legal_basis（依据）
- rationale（理由）
- action_items（下一步要做什么）
- risk_level（HIGH/MEDIUM/LOW）
  

---

模块 2：assessment（中国“安全评估路径报告”）在干什么？逻辑是什么？
业务目的：当 diagnosis 判定你必须/应当走安全评估路径时，帮你生成《数据出境风险自评估报告》草案（用于申报前准备）。

核心逻辑：
1. 先跑一次 diagnosis 结果校验：  
  - 如果 diagnosis 推荐不是 security_assessment，默认 拒绝生成（400）  
  - 除非你显式 force_override_path=true（会在报告里留警示）
2. 提取企业画像（表单 + 附件解析“留痕”）
3. RAG 检索中国条文（jurisdiction=cn、path=assessment）拿出可引用依据
4. LLM 按“安全评估报告”章节结构生成草案，并强制“每段有依据引用”
5. 做一致性/对齐检查（避免写出和输入矛盾的内容，比如明明不是CIIO却写成CIIO）
6. 套 docx/md 模板输出 + 打包 zip
  

---

模块 3：scc（中国“标准合同备案/合同审查”）在干什么？逻辑是什么？
业务目的：当你走的是“标准合同备案/配套材料”路径时，输出一份“标准合同相关的合规审查/行动建议”类文书（并支持批注版 docx）。

核心逻辑：
- RAG 用 path=scc（更靠近标准合同/备案/PIPIA语境）
- 把“是否已有合同草案”“接收方信息”“规模”等塞进上下文
- 生成固定几个章节（依据说明/评级/问题清单/行动计划）
- 可生成 annotated_docx（对合同做批注修订版输出）
  

---

模块 4：pipia（个人信息保护影响评估）在干什么？逻辑是什么？
业务目的：为“标准合同备案或认证”这类路径，生成 PIPIA（个人信息保护影响评估）草案及配套结论。

核心逻辑：
- 输入更结构化（公司画像、出境背景、权利保障、应急计划、附件角色）
- 会做“附件角色一致性校验”（例如走 scc_filing 但没提供 scc_contract 就给问题）
- RAG：route_type=scc_filing 时偏 path=scc，否则 path=all
- 输出 docx/md/zip
  

---

欧盟侧：dpia / tia / bcr 分别在干什么？逻辑是什么？
它们解决的是 GDPR 体系下不同“合规工件”的问题：

- dpia（DPIA）：评估某个处理活动的风险与必要性比例性
逻辑：输入项目描述/合法性基础/风险与措施 → 生成 DPIA 报告结构 → 给一致性提示（比如高残余风险是否需要咨询监管）
- tia（TIA）：评估跨境传输到第三国后，传输工具+补充措施是否有效
逻辑：输入 transfer tool、第三国法律实践评估、补充措施、结论 → 生成 TIA 报告 → 校验是否有“国家法律分析附件”等
- bcr（BCR）：集团内部跨境传输规则体系的要素审查/评级
逻辑：更像“对清单审计”，会先形成问题清单与评级，再生成报告
  
你提到“欧盟四个审查”，业务上常见第4个是“EU SCC审查/适用性”，但你们当前代码里还没单独做一个 EU_SCC 模块；现阶段欧盟模块就是上面这三个。


---

美国侧：cpra / cn_flow 在干什么？逻辑是什么？
- cpra：加州隐私合规全景审查
逻辑：先产出 gap_items（差距清单）→ 排优先级 → 输出整改路线图（含 xlsx/pdf）
- cn_flow（14117）：EO14117 对华数据流动/交易限制风险评估
逻辑：先产出 risk_items（风险项清单）→ 红黄绿总体结论 → 输出清单与报告（含 xlsx/pdf）
  

---

review（文档审查闭环）在干什么？逻辑是什么？
业务目的：对一份合同/协议做“逐条款审查”，并把结果可追溯地存起来（任务、进度、问题清单、最终报告）。

核心逻辑：
1. 保存文件并抽取全文（落库）
2. 条款切分（SEGMENTING）
3. 条款分类（CLASSIFYING，基于关键词规则书）
4. 逐条审查（REVIEWING）  
  - 重要条款最多挑 8 条用 LLM 深审  
  - 其余用规则审（缺要素就打问题）
  - 同时用 RAG（path=review）给每条问题补法规依据
5. 聚合评级（AGGREGATING：按 HIGH/MEDIUM/LOW 统计出总体结论）
6. 渲染 docx 报告（RENDERING），落库并可查询/复盘
  

---

你现在“没理解”的关键点通常是这两个
1. 模块不是“都在做同一件事”：  
  - diagnosis：做“路由判定”（规则引擎）  
  - review：做“条款级审查闭环”（任务系统）  
  - 其它模块：做“某个合规工件/交付物的草案生成”（报告/清单/路线图）
2. 同是生成类模块，也分两种思路：  
  - “章节写作型”（assessment/dpia/tia/pipia）：上下文 + 法规 → 生成章节  
  - “清单驱动型”（cpra/cn_flow/bcr）：先生成 gap/risk/problems 再写报告
    
你可以把 AI4Law 当成一个“合规工作流工具箱”，目标不是替你做最终法律结论，而是把跨境/隐私合规这类工作拆成可执行的步骤：先判路径、再准备材料、再生成草案、最后做条款审查与整改清单。

下面用“业务在干什么 + 每个功能的逻辑是什么”来解释（尽量按你们现有模块的真实分工）。


---

一句话总览：业务在干什么
企业要做数据出境/隐私合规时，通常要解决两类问题：

1. 我应该走哪条合规路径？（路径判断、豁免判断、门槛判断）  
2. 走这条路径要交什么材料、报告怎么写、合同有没有问题、风险怎么落地整改？（检索法规→生成报告草案→审查合同→输出清单与路线图）
  
你们系统就是把这两类问题拆成模块：

- diagnosis：解决 1（规则树/门槛/豁免）
- 其它“文书生成类”（assessment/scc/pipia/dpia/tia/bcr/cpra/cn_flow）：解决 2（报告/清单/路线图）
- review：对“合同文件”做闭环审查（切条款→分类→逐条问题→报告落库）
  

---

模块 1：diagnosis（路径选择）在干什么？逻辑是什么？
业务目的：回答“这次数据出境/跨境传输，合规上优先走哪条路径？是否可能豁免？”

核心逻辑（确定性为主）：
- 先把问卷里 unknown/缺失 用扩展字段做保守补全（归一化）
- 再按 decision_tree.json 从上到下命中第一条规则（豁免优先、门槛其次、最后默认）
- 只有规则无法收敛时才允许 LLM 给“推测结论”，并降低置信度、标注不确定
  
输出是什么：不是一段话，而是结构化结果：
- recommended_path（安全评估 / SCC或认证 / 豁免等）
- legal_basis（依据）
- rationale（理由）
- action_items（下一步要做什么）
- risk_level（HIGH/MEDIUM/LOW）
  

---

模块 2：assessment（中国“安全评估路径报告”）在干什么？逻辑是什么？
业务目的：当 diagnosis 判定你必须/应当走安全评估路径时，帮你生成《数据出境风险自评估报告》草案（用于申报前准备）。

核心逻辑：
1. 先跑一次 diagnosis 结果校验：  
  - 如果 diagnosis 推荐不是 security_assessment，默认 拒绝生成（400）  
  - 除非你显式 force_override_path=true（会在报告里留警示）
2. 提取企业画像（表单 + 附件解析“留痕”）
3. RAG 检索中国条文（jurisdiction=cn、path=assessment）拿出可引用依据
4. LLM 按“安全评估报告”章节结构生成草案，并强制“每段有依据引用”
5. 做一致性/对齐检查（避免写出和输入矛盾的内容，比如明明不是CIIO却写成CIIO）
6. 套 docx/md 模板输出 + 打包 zip
  

---

模块 3：scc（中国“标准合同备案/合同审查”）在干什么？逻辑是什么？
业务目的：当你走的是“标准合同备案/配套材料”路径时，输出一份“标准合同相关的合规审查/行动建议”类文书（并支持批注版 docx）。

核心逻辑：
- RAG 用 path=scc（更靠近标准合同/备案/PIPIA语境）
- 把“是否已有合同草案”“接收方信息”“规模”等塞进上下文
- 生成固定几个章节（依据说明/评级/问题清单/行动计划）
- 可生成 annotated_docx（对合同做批注修订版输出）
  

---

模块 4：pipia（个人信息保护影响评估）在干什么？逻辑是什么？
业务目的：为“标准合同备案或认证”这类路径，生成 PIPIA（个人信息保护影响评估）草案及配套结论。

核心逻辑：
- 输入更结构化（公司画像、出境背景、权利保障、应急计划、附件角色）
- 会做“附件角色一致性校验”（例如走 scc_filing 但没提供 scc_contract 就给问题）
- RAG：route_type=scc_filing 时偏 path=scc，否则 path=all
- 输出 docx/md/zip
  

---

欧盟侧：dpia / tia / bcr 分别在干什么？逻辑是什么？
它们解决的是 GDPR 体系下不同“合规工件”的问题：

- dpia（DPIA）：评估某个处理活动的风险与必要性比例性
逻辑：输入项目描述/合法性基础/风险与措施 → 生成 DPIA 报告结构 → 给一致性提示（比如高残余风险是否需要咨询监管）
- tia（TIA）：评估跨境传输到第三国后，传输工具+补充措施是否有效
逻辑：输入 transfer tool、第三国法律实践评估、补充措施、结论 → 生成 TIA 报告 → 校验是否有“国家法律分析附件”等
- bcr（BCR）：集团内部跨境传输规则体系的要素审查/评级
逻辑：更像“对清单审计”，会先形成问题清单与评级，再生成报告
  
你提到“欧盟四个审查”，业务上常见第4个是“EU SCC审查/适用性”，但你们当前代码里还没单独做一个 EU_SCC 模块；现阶段欧盟模块就是上面这三个。


---

美国侧：cpra / cn_flow 在干什么？逻辑是什么？
- cpra：加州隐私合规全景审查
逻辑：先产出 gap_items（差距清单）→ 排优先级 → 输出整改路线图（含 xlsx/pdf）
- cn_flow（14117）：EO14117 对华数据流动/交易限制风险评估
逻辑：先产出 risk_items（风险项清单）→ 红黄绿总体结论 → 输出清单与报告（含 xlsx/pdf）
  

---

review（文档审查闭环）在干什么？逻辑是什么？
业务目的：对一份合同/协议做“逐条款审查”，并把结果可追溯地存起来（任务、进度、问题清单、最终报告）。

核心逻辑：
1. 保存文件并抽取全文（落库）
2. 条款切分（SEGMENTING）
3. 条款分类（CLASSIFYING，基于关键词规则书）
4. 逐条审查（REVIEWING）  
  - 重要条款最多挑 8 条用 LLM 深审  
  - 其余用规则审（缺要素就打问题）
  - 同时用 RAG（path=review）给每条问题补法规依据
5. 聚合评级（AGGREGATING：按 HIGH/MEDIUM/LOW 统计出总体结论）
6. 渲染 docx 报告（RENDERING），落库并可查询/复盘
  

---

你现在“没理解”的关键点通常是这两个
1. 模块不是“都在做同一件事”：  
  - diagnosis：做“路由判定”（规则引擎）  
  - review：做“条款级审查闭环”（任务系统）  
  - 其它模块：做“某个合规工件/交付物的草案生成”（报告/清单/路线图）
2. 同是生成类模块，也分两种思路：  
  - “章节写作型”（assessment/dpia/tia/pipia）：上下文 + 法规 → 生成章节  
  - “清单驱动型”（cpra/cn_flow/bcr）：先生成 gap/risk/problems 再写报告
对，你现在的理解已经很接近了：你们系统产出的多数是**“企业自评/自查的草案或审查结论”。但在真实合规流程里，这些材料有两类用途：对外申报/备案要交的，以及企业内部留存/自我决策用的**。很多文件是“先内部生成 → 律师/合规复核 → 再对外提交”。

下面按你们模块对应的业务，把“要不要提交给官方/谁看”说清楚（以中国/欧盟/美国分别讲）。


---

一、中国（网信体系）：哪些通常要对外提交/备案？
1) assessment（安全评估路径）
- 系统生成的《数据出境风险自评估报告》：通常属于申报安全评估材料包里的核心文件之一（对外提交用，但必须人工复核后再交）。
- 其它附件/材料（合同、数据清单、影响说明等）：往往也要随申报材料一起提交（你们系统可辅助生成草案/清单，但企业需要补齐真实业务证据与盖章件）。
  
结论：assessment 更偏“要走官方流程时的申报材料草案”。

2) scc（标准合同备案） + pipia（PIPIA）
- 标准合同备案本身是要向省级网信部门备案的（对外动作）。
- 通常会涉及：
  - 标准合同文本（企业与境外接收方签署）
  - PIPIA（个人信息保护影响评估报告）（实践中经常作为配套材料/留档要求，备案材料体系里会用到；你们系统的 pipia 就是在帮生成这一块草案）
结论：scc/pipia 更偏“备案/留档材料 + 内部合规留痕”，其中标准合同备案是对外动作，PIPIA 通常既可能用于对外配套，也用于内部留档与问责。

3) diagnosis（路径诊断）
- 不提交官方。它是企业内部用来决定“走哪条路”的依据与留痕（也可给领导/律师看）。
  

---

二、欧盟（GDPR）：哪些要交监管？哪些主要内部留存？
1) dpia（DPIA）
- DPIA通常是企业内部文件：证明你做过风险评估与措施设计。
- 一般不主动提交给监管，但在检查/审计时可能需要出示；若残余风险很高且无法降低，可能涉及“事前咨询”（那是另一条流程）。
结论：DPIA 主要内部留存与问责。

2) tia（TIA）
- TIA也是内部合规证明材料：证明你评估过第三国风险以及补充措施。
- 通常不“申报”，但可能在监管/诉讼/客户尽调时被要求出示。
结论：TIA 主要内部留存 + 对客户/监管解释。

3) bcr（BCR）
- BCR如果走正式路径，会涉及监管审批/协作（较重）。
- 你们模块更像“BCR要素审查/缺口清单”，这通常也是内部准备材料，用于后续正式推进。
结论：BCR相关材料 前期内部为主，真正对外是后续正式机制。


---

三、美国：基本是“内部合规/整改”，不是“对外申报”
1) cpra（合规全景/整改路线图）
- 主要是内部整改与对外应对能力建设（应对消费者请求、监管问询、诉讼举证）。
- 一般不是“向政府提交一份报告”，而是“你必须能证明你做到了”。
结论：CPRA 内部自查/整改为主。

2) cn_flow（EO14117 风险评估）
- 也是偏“内部风险评估 + 决策留痕 + 管控措施”，用于决定业务能不能做、怎么做、怎么降风险。
结论：14117 内部决策与风控留痕为主。


---

review（合同/文档审查）算哪类？
- 它输出的是“逐条问题清单 + 修改建议 + 依据引用”的内部审查报告。
- 不直接交官方；它是用来把合同改到更合规、更可执行，然后你的对外材料（合同、备案材料）才更可靠。
结论：review 是内部审查/整改工具。


---

关键结论（用一句话记）
- 中国安全评估/标准合同备案：更偏“会进入官方流程”的方向，所以系统生成的报告草案更可能成为对外材料的一部分（但要人工复核）。  
- 欧盟/美国：更多是“内部问责与证据链”，不一定有“提交官方”这一步，但要能随时拿得出证据。
  
如果你告诉我你们产品的目标客户场景是“主要做中国出境合规”，还是“主要做欧盟/美国合规”，我可以把“每个模块产物 → 典型使用者（法务/合规/安全/业务）→ 是否对外 → 何时触发”整理成一张更易用的对照表。


---

如果你愿意，我可以用一个“典型用户从 0 到交付”的业务故事串起来（比如“中国公司要把客户数据传到新加坡”：先 diagnosis → 走 assessment 还是 scc/pipia → 最后用 review 审合同），这样你会更直观。你想用“中国数据出境”的故事串，还是用“欧盟传输（DPIA+TIA）”或“CPRA整改”串？

---

如果你愿意，我可以用一个“典型用户从 0 到交付”的业务故事串起来（比如“中国公司要把客户数据传到新加坡”：先 diagnosis → 走 assessment 还是 scc/pipia → 最后用 review 审合同），这样你会更直观。你想用“中国数据出境”的故事串，还是用“欧盟传输（DPIA+TIA）”或“CPRA整改”串？

---

如果你把你们产品里“欧盟四个审查”和“美国两个审查”的具体业务名称（页面/菜单文案）贴一下，我可以把上面这套业务定义对齐成你们自己的产品话术（每个模块一句话定位 + 3个关键输入 + 3个关键输出 + 1个典型用户场景）。

---

如果你想把这些差异“落到你现在正在看的 assessment 代码旁边”去理解，我建议你用同样的视角对照两个代表模块：
- 轻量型：backend/modules/dpia/service.py:48（输入基本直灌 context → RAG → 章节 → 模板）
- 结构化清单型：backend/modules/cpra/service.py:49（先 gap_items 规则化 → 再让 LLM 写解释性章节 → 输出 pdf/xlsx）

路径选择详细细节
diagnosis（路径选择）模块的“细节”可以按 输入 → 归一化 → 规则树命中 →（可选）AI 推测兜底 → 结构化结果 → 报告渲染 这条链路理解。

下面我按代码把每一步的判断逻辑讲清楚。


---

0) 它对外提供两类能力（接口形态）
- 只要结论：POST /api/v1/diagnosis/evaluate
直接返回结构化 DiagnosisResult（backend/modules/diagnosis/router.py:25）。
- 结论 + 报告文件：POST /api/v1/diagnosis/report
先 evaluate() 再渲染 outputs/diagnosis/*.html 和 *.pdf（backend/modules/diagnosis/router.py:30，backend/modules/diagnosis/report_renderer.py:434）。
  

---

1) 输入长什么样（为什么这么多字段）
输入主体是 DiagnosisAnswers（backend/modules/diagnosis/schema.py:27）：

(1) 4 个核心阈值字段（决定“安全评估 vs 其他”）
- q1_is_ciio（yes/no/unknown）
- q2_has_important_data（yes/no/unknown）
- q3_pii_count（近12个月出境个人信息人数）
- q4_spi_count（近12个月出境敏感个人信息人数）
这些是硬门槛判断的主信号。

(2) 额外 4 个“豁免/场景”字段（决定“可豁免 vs 仍需走路径”）
- q5_no_personal_info：是否“不含个人信息且不涉重要数据”（schema.py:35）
- q6_scenario：合同履行/HR/紧急/法定义务/其他（schema.py:12-schema.py:19）
- q7_receiver_type：集团内/第三方（schema.py:21-schema.py:25）
- q8_purpose：目的文本（给 AI 解释用）
  
(3) 大量 m1_* ~ m5_* 扩展问卷
这些不直接决定阈值，但会用于 “输入归一化（补全 unknown/缺失）”，以及给 AI 推测与报告解释提供事实背景（schema.py:52 起）。


---

2) 第一步关键逻辑：输入归一化（把“unknown/缺失”变成可判定信号）
DiagnosisService.evaluate() 开头第一句就是：
- answers = self._normalize_answers(answers)（backend/modules/diagnosis/service.py:31-service.py:32）
  
_normalize_answers() 的核心思想是：优先用问卷的结构化细节去“保守补全”关键位，避免因为 q* 没填/填 unknown 就误触发 AI 推测。

你能直接看到的补全策略包括（节选逻辑在 service.py:72 起）：
- 如果 m3_* 明确表明“涉及重要数据/个人信息类型”：
  - q2_has_important_data == unknown 会被改成 yes/no（service.py:88-service.py:91）
- 如果 m3_data_volume_range 选了区间但 q3_pii_count 还是 0：
  - 用 _estimate_pii_count() 把区间估算成人数（service.py:61-service.py:70）
- 如果个人信息类型里出现敏感关键词（身份证、人脸、健康、金融、未成年人等）：
  - has_sensitive_info 会被认为 true（service.py:56-service.py:58，service.py:82）
    
归一化的“原理”是：把“表单勾选/类型列表/区间选择”提升为可用于规则树的确定信号，减少不确定性。


---

3) 第二步关键逻辑：规则树按优先级从上到下命中（命中即停）
归一化之后，进入主流程：

for rule in self._tree["rules"]:
  if self._rule_match(rule["when"], answers):
    return self._build_rule_result(...)

见 backend/modules/diagnosis/service.py:33-service.py:37。

规则定义在 backend/modules/diagnosis/decision_tree.json，文件头注释写得很明确：
- “按优先级从上到下匹配，命中第一条即返回。豁免规则优先于强制申报规则。”（decision_tree.json 顶部）
  
3.1 豁免类规则（最先匹配）
例如：
- no_personal_info：只要 q5_no_personal_info == yes → path="exemption"（你截到的 decision_tree.json 开头就有）
- exemption_contract：场景是合同履行 + 未触发门槛 + 非CIIO/无重要数据 → 也 path="exemption"（同文件开头）
  
这就是为什么它强调“豁免优先”：即使规模没填清楚，也会先尝试用场景规则给出“可豁免”的结论（当然前提是未触发门槛）。

3.2 强制安全评估类规则（后面才轮到）
典型就是你们一直说的四个门槛：CIIO/重要数据/100万人/1万敏感。规则树里会对应到 security_assessment 路径（在 service._RATIONALE_I18N 也能看出有这些理由文案，service.py:11-service.py:16）。

3.3 默认规则（啥都没命中时）
如果没命中任何 rule，也没触发 AI 推测兜底，就走 default：
- path = self._tree["default"]["path"]
- confidence="MEDIUM"
- matched_rule_id="default"
见 backend/modules/diagnosis/service.py:44-service.py:53。


---

4) 第三步关键逻辑：什么时候会启用 AI 推测兜底？
只有在规则树没命中后，才会判断 _needs_ai_inference()（backend/modules/diagnosis/service.py:38-service.py:43）。

触发信号（backend/modules/diagnosis/service.py:212-service.py:229）：
- 关键布尔位存在 unknown：q1/q2/q5 里有 unknown
- 且规模信号弱：q3==0 and q4==0
- 但如果问卷里已经有足够结构化信号（m3_processes_* 或 types 列表不空）并且不是“规模全为 0”，则不要轻易 AI 推测（service.py:221-service.py:228）。
  
AI 推测输出会显式标注：
- conclusion_source="ai_inference"
- confidence 降级
- uncertainty_notes 给出为什么不确定
见 backend/modules/diagnosis/service.py:231 起（你截到的部分已经覆盖）。

如果 LLM 未启用，它仍会返回一个“保守推测”的结构化结果，并写明“不可作为最终法律意见”（backend/modules/diagnosis/service.py:232-service.py:246）。


---

5) 结果是怎么“结构化”的（不是只给一句话）
DiagnosisResult 字段（backend/modules/diagnosis/schema.py:100）里除了 recommended_path，还有：
- legal_basis：匹配规则自带的法律依据（来自 decision_tree）
- rationale：命中理由（并做中英/模板化映射 _RATIONALE_I18N，backend/modules/diagnosis/service.py:178）
- action_items：不同路径会给不同的行动清单（backend/modules/diagnosis/service.py:185-service.py:196）
- risk_level：用同一个 risk_level() 根据 CIIO/重要数据/人数门槛算 HIGH/MEDIUM/LOW（backend/modules/diagnosis/service.py:179-service.py:184，函数在 backend/common/risk/scoring.py:1）
- matched_rule_id：可追溯“命中哪条规则”
- AI 推测时还会有 uncertainty_notes/final_explanation/confidence 等
  
这就是 diagnosis 的“可解释性”载体：结论不只是路径名，而是“命中规则 + 法律依据 + 行动建议 + 风险等级 + 置信度/不确定性说明”。


---

6) 报告是怎么生成的（HTML/PDF）
POST /diagnosis/report 的渲染逻辑在 DiagnosisReportRenderer.render()：
- 会调用 LLM 生成 2-3 句话的“AI 摘要”（可降级占位）（backend/modules/diagnosis/report_renderer.py:434-report_renderer.py:450）
- 报告 sections 固定包含：
  - 企业回答（answers 格式化）
  - 诊断结果（result 格式化）
  - AI 摘要
  - 模板化报告
  - 机器可读附录（把 answers/result 以 JSON 形式放进去）
见 backend/modules/diagnosis/report_renderer.py:452-report_renderer.py:458。
- 输出落地：
  - outputs/diagnosis/<company>_diagnosis_report.html
  - outputs/diagnosis/<company>_diagnosis_report.pdf
见 backend/modules/diagnosis/report_renderer.py:461-report_renderer.py:469。


---

如果你接下来想更“贴业务”的理解方式：你给我一个真实的 DiagnosisAnswers（哪怕只填 q1~q8），我可以按 decision_tree.json 的顺序逐条模拟“为什么前面的豁免没命中、为什么命中了哪条规则”，并解释 matched_rule_id/legal_basis/risk_level 最终是怎么出来的。

文档审查详细细节
review（文档审查闭环）和“文书生成流水线”最大的不同点是：它不是“生成一份报告就结束”，而是有任务实体（task）+ 文件实体（uploaded_files）+ 状态机 + 进度推送 + 结果落库，形成可追溯闭环。

下面按你们真实代码把每一步细节拆开。

1) 两种使用方式（D7a 快捷 vs D7b 任务式）
- D7a 快捷模式（文件路径式）
  - POST /api/v1/review/generate：同步跑完整闭环（backend/api/review.py:22）
  - POST /api/v1/review/generate_async：异步提交，返回 task_id/state/progress（backend/api/review.py:32）
  - 输入是 ReviewGenerateRequest{ uploaded_files: [path] }（backend/schemas/review.py:105）
  - 关键安全限制：传进来的 path 必须在 storage_dir 下，否则 403（backend/services/review_service/service.py:317-service.py:334）
- D7b 任务模式（显式任务管理）
  - POST /api/v1/review/tasks 创建 task（backend/api/review.py:52）
  - POST /api/v1/review/tasks/{task_id}/files 上传文件（服务端保存+抽取文本）（backend/api/review.py:61，backend/services/review_service/service.py:56）
  - POST /api/v1/review/tasks/{task_id}/analyze 开始跑流水线（backend/api/review.py:72）
  - GET /api/v1/review/tasks/{task_id}/status|issues|report 取状态、问题清单、报告（backend/api/review.py:82 起）
  - WS /api/v1/review/ws/tasks/{task_id} 接收进度推送（backend/api/review.py:112）
    
2) 持久化模型（闭环的“落库”是什么）
落两张表（SQLAlchemy）：
- review_tasks：id/user_id/status/progress/summary_json/issues_json（backend/models/review.py:10）
- uploaded_files：task_id/storage_path/extracted_text（文本抽取结果会存下来，供后续分条款）（backend/models/review.py:27）
  
这就是“闭环”的本质：不是只返回 docx 路径，而是能随时查询任务、问题、摘要。

3) 状态机（流水线阶段）
状态枚举在 backend/schemas/review.py:9：
CREATED → UPLOADED → SEGMENTING → CLASSIFYING → REVIEWING → AGGREGATING → RENDERING → COMPLETED/FAILED

服务里每个阶段都会更新 task.status/task.progress，并通过 websocket 推送（backend/services/review_service/service.py:140-service.py:176，service.py:304-service.py:310）。

4) 核心流水线：从文件到问题清单到报告
真正的业务闭环在 _run_pipeline()（backend/services/review_service/service.py:134）：

1. SEGMENTING（条款切分）  
- 对每个上传文件，用 ClauseSegmenter.segment(file.id, file.extracted_text) 切条款（service.py:140-service.py:144）。
- 切分规则：用正则在“第X条 / 1. / 1、 / 一、”这类标记处做 split（backend/services/review_service/clause_segmenter.py:8）。
- 每个条款会带一个粗略位置：page=1, paragraph=index, clause_number=...（clause_segmenter.py:21-clause_segmenter.py:28）。
  
2. CLASSIFYING（条款分类）  
- ClauseClassifier.classify() 用 backend/data/review_rulebook.json 的关键词命中数决定 clause_type（backend/services/review_service/clause_classifier.py:17-clause_classifier.py:23）。
- ClauseType 范围：处理范围/同意告知/安全措施/跨境/权利/责任/其他（backend/schemas/review.py:21-review.py:28）。
- 这个分类是纯规则的（deterministic），可解释性来自：matched_keywords 会被保留（review.py:51-review.py:54）。
  
3. REVIEWING（逐条款审查：规则 + 可选 LLM + RAG 引用增强）  
- 先过滤“值得审查的条款”（避免目录/编号/太短无信息）：
  - 纯编号/符号且短于 64 → 跳过
  - OTHER 且没关键词且短于 120 → 跳过
  见 backend/services/review_service/service.py:268-service.py:276。
- 再挑出最多 8 条最重要的条款用 LLM 审（其他条款走规则审）：
  - 优先级：跨境 > 告知同意 > 安全措施 > 权利 > 范围 > 责任（service.py:280-service.py:288）
  - 只选 clause_type != OTHER 且文本 ≥80 的（service.py:289-service.py:302）
- 每条款审查入口：ClauseReviewer.review(clause, use_llm=...)（service.py:154）。
  - RAG/引用增强发生在这里：LocalRegulationKnowledgeBase.lookup() 会在满足条件时调用 retrieve_regulations(... jurisdiction="cn", path="review", top_k=3) 来补充 citations（backend/services/review_service/rag_provider.py:33-rag_provider.py:46）。
    - enrich 条件：clause_type != OTHER 且条款文本长度 ≥80（rag_provider.py:32）
    - citations = 规则书自带 citations + RAG 命中 citations 去重合并（rag_provider.py:48-rag_provider.py:51）
    - 若启用外部 DeliLegalService，还会 search_cases 补案例引用或错误信息（rag_provider.py:52-rag_provider.py:68）
  - LLM 审查（仅对选中的 8 条）：
    - 要求输出“JSON 数组”，每个问题含 severity/title/problem_type/risk_analysis/recommendation（backend/services/review_service/clause_reviewer.py:40-clause_reviewer.py:49）
    - 解析失败就降级回规则审（clause_reviewer.py:63-clause_reviewer.py:66）
  - 规则审查（兜底/批量）：
    - 基于 rulebook 的 required_groups：每组至少出现一个关键词，否则记“缺少关键信息”问题（clause_reviewer.py:92-clause_reviewer.py:112）
    - 发现模糊表述（如“尽最大努力/必要时”）记低风险（clause_reviewer.py:113-clause_reviewer.py:130）
    - 严重性规则：告知同意/跨境默认 HIGH；安全措施/权利默认 MEDIUM；其他 LOW（clause_reviewer.py:133-clause_reviewer.py:138）
      
4. AGGREGATING（聚合与总体评级）  
- ReviewAggregator.aggregate() 会：
  - 以 (clause_id, problem_type, title) 去重（backend/services/review_service/review_aggregator.py:35-review_aggregator.py:44）
  - 统计 HIGH/MEDIUM/LOW 数量并给总体评级：
    - 有 HIGH → “高风险”
    - 否则 MEDIUM ≥2 → “中风险”
    - 否则 → “低风险”
    见 review_aggregator.py:12-review_aggregator.py:17。
  - 生成优先整改建议（review_aggregator.py:19-review_aggregator.py:26）
    
5. RENDERING（生成报告并登记产物）  
- ReviewReportRenderer.build_sections() 把聚合结果变成 section 列表（摘要、优先建议、逐条问题清单）（backend/services/review_service/review_report_renderer.py:5-review_report_renderer.py:18）。
- ReportService.create_docx_report(...) 生成 storage/reports/review/<task_id>/review_report.docx 这类产物，并写 preview（overall_rating/summary）（backend/services/review_service/service.py:164-service.py:172）。
- 同时把 issues_json/summary_json 写回 review_tasks（service.py:174-service.py:177），最终状态置 COMPLETED。
  
5) 进度推送与查询
- 每次 _update_task() 都会保存状态并通过 websocket 推送 {task_id,status,progress}（backend/services/review_service/service.py:304-service.py:310，service.py:336-service.py:340）。
- 轮询接口：
  - /tasks/{task_id} 返回 async status（完成时会把 ReviewGenerateResponse 填进去，service.py:104-service.py:110）
  - /tasks/{task_id}/issues 直接读库返回问题列表（service.py:118-service.py:123）
  - /tasks/{task_id}/report 返回 report artifact + summary（service.py:124-service.py:132）
    
如果你想继续深挖，我可以按“一个条款从文本 → 分类 → 触发 required_groups 缺失 → 生成一条 ReviewIssue → 聚合进总体评级”的路径，用你们 review_rulebook.json 里的某个 clause_type 举一个完整、可对照代码的例子。

那我用最典型、也最“高风险优先级”的 CONSENT_NOTICE（同意与告知） 举一个从头到尾的闭环例子（对照代码能一一对应）。


---

例子输入：合同里某段“同意/告知”条款（假设切分后的一条 Clause）
条款文本（示例）：
“甲方同意乙方为提供服务之目的处理相关信息。乙方将采取必要措施保障信息安全。双方另行约定。”

A) SEGMENTING：它怎么变成 Clause
- ClauseSegmenter.segment() 用“第X条/1./一、”这类标记切分（backend/services/review_service/clause_segmenter.py:8）。
- 生成 Clause{clause_id,file_id,text,heading,position(paragraph=idx, clause_number=...)}（clause_segmenter.py:21-clause_segmenter.py:28）。
  

---

B) CLASSIFYING：它为什么会被归类为 CONSENT_NOTICE
- 分类器逐类扫描 review_rulebook.json 的 keywords，选命中数量最多的类型（backend/services/review_service/clause_classifier.py:17-clause_classifier.py:23）。
- CONSENT_NOTICE 的关键词：["同意","告知","境外接收方","联系方式","单独同意"]（backend/data/review_rulebook.json）。
- 这段文本至少命中“同意”，因此很可能被分到 CONSENT_NOTICE（如果其它类型命中更多则另说）。
- 分类结果是 ClassifiedClause，会带上 matched_keywords=["同意"]（backend/schemas/review.py:51-review.py:54）。
  

---

C) REVIEWING：为什么会产出哪些问题（LLM 或规则）
在 _run_pipeline() 里：
- 会先过一遍 _is_reviewable_clause()，文本不是“纯编号/太短 OTHER”等就会进入审查（backend/services/review_service/service.py:268-service.py:276）。
- 然后挑最多 8 条做 LLM 审查（优先跨境、告知同意等），CONSENT_NOTICE 优先级很高（service.py:280-service.py:288，service.py:302）。
  
下面分两种路径：

路径 1：走规则审查（LLM 未启用或没被选中）
ClauseReviewer._review_with_rules() 的核心规则是：对该 clause_type 的每个 required_groups，必须至少出现一组里的任意关键词，否则记“缺少关键信息”（backend/services/review_service/clause_reviewer.py:92-clause_reviewer.py:112）。

CONSENT_NOTICE.required_groups 是（backend/data/review_rulebook.json）：
- ["告知","通知"]
- ["境外接收方","接收方"]
- ["联系方式","联系"]
- ["同意","单独同意"]
  
对照示例条款：
- “同意”命中第 4 组 → OK
- 但没有“告知/通知” → 缺少 1
- 没有“境外接收方/接收方” → 缺少 2
- 没有“联系方式/联系” → 缺少 3
  
所以会生成至少 3 条 ReviewIssue：
- title="缺少关键信息：告知/通知"（或相应组名）
- problem_type="MISSING_REQUIREMENT"
- severity：对 CONSENT_NOTICE 默认是 HIGH（backend/services/review_service/clause_reviewer.py:133-clause_reviewer.py:138）
- citation_sources：来自 rulebook 的 citations +（可能的）RAG enrich（下面说）
- original_excerpt：条款前 240 字（clause_reviewer.py:106）
  
另外，如果条款里出现“尽最大努力/必要时”，会额外打一个“表述存在模糊空间”的 LOW 问题（clause_reviewer.py:113-clause_reviewer.py:130）。

路径 2：走 LLM 审查（被选中且 LLM 启用）
- LLM prompt 会带：
  - 条款类型、条款文本（最多 800 字）
  - “适用法规参考”（citations）
  - 要求输出 JSON 数组（无问题就 []）
见 backend/services/review_service/clause_reviewer.py:40-clause_reviewer.py:49。
- LLM 输出解析失败会回退到规则（clause_reviewer.py:63-clause_reviewer.py:66）。
  

---

D) RAG 是怎么“给条款补法规依据”的（review 专属）
无论走 LLM 还是规则审查，都会先做一次 knowledge_base.lookup(...) 拿 config（backend/services/review_service/clause_reviewer.py:31）。

LocalRegulationKnowledgeBase.lookup() 做两层引用：
1. rulebook 自带 citations（例如 CONSENT_NOTICE 默认带 《个保法》第39条）
2. 可选 RAG enrich（满足条件才做）：
  - clause_type != OTHER
  - 且条款长度 ≥ 80（backend/services/review_service/rag_provider.py:32）
  - 调 retrieve_regulations(... jurisdiction="cn", path="review", top_k=3)（rag_provider.py:34-rag_provider.py:41）
  - 把命中的 title+article 追加到 citations 去重（rag_provider.py:42-rag_provider.py:51）
    
这就是为什么 review 的每条 issue 都能带上 citation_sources：它来自“规则书 + RAG 条文命中 +（可选）外部案例”。


---

E) AGGREGATING：为什么总体评级会变成“高/中/低风险”
所有 issue 生成后：
- 先 dedupe：同一 (clause_id, problem_type, title) 只保留一条（backend/services/review_service/review_aggregator.py:35-review_aggregator.py:44）
- 统计 HIGH/MEDIUM/LOW：
  - 有 HIGH → 总体“高风险”
  - 否则 MEDIUM≥2 → “中风险”
  - 否则 “低风险”
见 review_aggregator.py:12-review_aggregator.py:17。

在我们这个例子里，因为 CONSENT_NOTICE 缺信息默认就是 HIGH，所以总体评级大概率直接变“高风险”。


---

F) RENDERING + 落库：报告与任务闭环怎么形成
- ReviewReportRenderer.build_sections() 把 summary/优先建议/逐条问题清单整理成 sections（backend/services/review_service/review_report_renderer.py:5-review_report_renderer.py:18）。
- ReportService.create_docx_report(..., owner_type="review", owner_id=task_id, filename="review_report.docx") 生成 docx 并登记产物（backend/services/review_service/service.py:164-service.py:172）。
- 同时把 issues_json/summary_json 写进 review_tasks，状态置 COMPLETED（service.py:174-service.py:177）。
  

---

如果你想下一个例子更“贴跨境条款”，我可以再用 CROSS_BORDER_TRANSFER（跨境/境外/存储地点/传输/接收方）举一个：它在 _select_llm_candidates() 里优先级最高（backend/services/review_service/service.py:280），而且默认 severity 也是 HIGH（backend/services/review_service/clause_reviewer.py:133-clause_reviewer.py:138）。你更想看“告知同意”还是“跨境传输”这种场景？