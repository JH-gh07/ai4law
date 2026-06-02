以下是 BCR 模块当前全部 30 个文件、3 层架构（数据层 +
  规则层 + Agent 层）的逐模块逻辑流程汇报。

  ---
  BCR 约束性公司规则审查 — 全线模块逻辑流程

  文件总览（30 个文件，3 层架构）

  backend/modules/bcr/
  │                                   
  ├── 📦 数据层
  │   ├── schema.py                        ← 17 个模型 +
  8 个枚举
  │   └── data/bcr_rulebook.json           ← 22 条规则 +
  12 条 DSL + 6 条条件规则
  │
  ├── 🔧 规则层（14 个文件）
  │   ├── bcr_rulebook_loader.py           ← 规则书加载器
  │   ├── bcr_type_classifier.py           ← 类型判定
  │   ├── bcr_document_parser.py           ← 文档解析
  │   ├── bcr_scenario_extractor.py        ← 场景抽取
  │   ├── bcr_checklist_checker.py         ← 5
  状态强制要素检查
  │   ├── bcr_tia_checker.py               ← TIA 专项
  │   ├── bcr_onward_transfer_checker.py   ← Onward
  Transfer 专项
  │   ├── bcr_liability_checker.py         ← 责任 +
  第三方受益人专项
  │   ├── bcr_clause_reviewer.py           ← 条款级审查
  │   ├── bcr_legal_retriever.py           ← 法规检索
  │   ├── bcr_risk_aggregator.py           ← 风险评分
  │   ├── bcr_report_renderer.py           ← 11 章报告
  │   ├── service.py                       ← 总调度器
  │   └── router.py                        ← API 端点
  │
  ├── 🤖 Agent 层（11 个文件）
  │   └── agents/
  │       ├── __init__.py                  ← BCRAgentBase
  + create_agents()
  │       ├── type_reasoning_agent.py      ← Agent 1
  │       ├── coverage_agent.py            ← Agent 2
  │       ├── actor_role_agent.py          ← Agent 3
  │       ├── onward_transfer_agent.py     ← Agent 4
  │       ├── tia_reasoning_agent.py       ← Agent 5
  │       ├── evidence_coverage_agent.py   ← Agent 6
  │       ├── incorrect_status_agent.py    ← Agent 7
  │       ├── legal_grounding_agent.py     ← Agent 8
  │       ├── approval_risk_agent.py       ← Agent 9
  │       └── remediation_agent.py         ← Agent 10
  │
  └── 🧪 测试层
      └── tests/
          ├── test_service.py              ←
  旧表单驱动测试
          ├── test_async_api.py            ← 异步 API
  测试
          └── test_document_review.py      ←
  文档驱动回归（3 案例）

  ---
  📦 数据层

  模块 1：schema.py — 数据模型

  文件：backend/modules/bcr/schema.py

  25 个定义（17 个 Pydantic 模型 + 8 个 Literal
  枚举），按 4 层组织：

  枚举层（8 个）：
    BCRCode, BCRScore, BCRDocumentRole, BCRTypeLabel,
  BCRConsistency,
    BCRRating, BCRRiskLevel, BCRReviewDepth

  表单驱动模型（2 个）：
    BCRReviewItem  → {code, title, score, finding,
  legal_basis, recommendation, evidence}
    BCRAttachment   → {file_name, file_format,
  storage_uri}

  文档驱动模型（5 个）：
    BCRUploadedDocument   → {file_id, file_name,
  file_type, file_path, document_role}
    BCRTypeClassification → {declared_bcr_type,
  actual_bcr_type, type_consistency, risk_level,
  evidence[], recommendation}
    BCRScenarioContext    → {company_name,
  headquarters_country, eu_liable_entity,

  processes_on_behalf_of_clients, third_countries[],
  auto_extracted_facts}
    BCRReviewConfig       → {review_depth,
  max_llm_clauses, enable_cross_document_check}
    BCRFinding            → {finding_id, requirement_id,
  location, clause_excerpt, title,
                              risk_level, risk_score,
  finding, legal_basis[], recommendation,
                              suggested_revision,
  facts_uncertain, review_confidence}

  输入输出模型（4 个）：
    BCRRequest     → {company_name, review_items[]?,
  uploaded_documents[]?,
                       scenario_context?, review_config?}
    BCRProblem     → 旧路径输出
    BCRChapter     → {chapter_no, title, content,
  citations[], risk_level}
    BCRResult      → {report_path, output_files, rating,
  problems?, chapters?,
                       findings?, missing_requirements?,
  bcr_type_classification?, review_metadata}

  关键设计决策：BCRRequest.review_items
  从必填改为默认空列表，uploaded_documents
  新增——同一个请求模型同时服务两条路径。

  ---
  模块 2：bcr_rulebook.json — 规则书

  文件：backend/modules/bcr/data/bcr_rulebook.json

  6 个顶层 section：

  ① bcr_type_classification
     ├─ bcr_c_signals: 12 个 BCR-C 信号词
     ├─ bcr_p_signals: 16 个 BCR-P 信号词
     └─ module_mismatch_rules: 3 条标题/BODY 模式冲突规则

  ② bcr_c_requirements: 14 条
  ③ bcr_p_requirements: 5 条
  ④ shared_requirements: 3 条

     每条 requirement 含有：
       requirement_id, title, source, gdpr_basis,
  severity_if_missing,
       check_keywords: string[],
       check_structure: string[],
       coverage_thresholds: {keywords_min,
  structure_match},
       dsl_checks: [{id, pattern, pattern_type, severity,
  title, finding, recommendation}]

  ⑤ document_structure_checklist
     ├─ bcr_c_required_sections: 16 个章节名
     └─ bcr_p_required_sections: 11 个章节名

  ⑥ risk_weights + severity_weights
     ├─ risk_weights: 24
  条权重映射（BCR_TYPE_MISMATCH=10, 14 条 BCR-C + 5 条
  BCR-P + 3 条 shared + OTHER）
     └─ severity_weights: HIGH=10, MEDIUM=5, LOW=2

  6 条核心 requirement 已配置 DSL checks（共 12 条）：

  ┌────────────┬───────┬────────────┬───────────────┐
  │ Requiremen │ 条件  │ pattern_ty │   示例规则    │
  │     t      │  数   │     pe     │               │
  ├────────────┼───────┼────────────┼───────────────┤
  │ BCR-C-1.1  │       │ match +    │ 空洞承诺检测  │
  │ 约束力     │ 2     │ missing    │ / 缺法律文书  │
  │            │       │            │ 检测          │
  ├────────────┼───────┼────────────┼───────────────┤
  │ BCR-C-1.2  │       │            │ 未赋予可执行  │
  │ 第三方受益 │ 1     │ missing    │ 权利          │
  │ 人         │       │            │               │
  ├────────────┼───────┼────────────┼───────────────┤
  │ BCR-C-1.3  │       │ missing +  │ 未指定欧盟实  │
  │ EU责任主体 │ 2     │ missing    │ 体 /          │
  │            │       │            │ 未承诺赔偿    │
  ├────────────┼───────┼────────────┼───────────────┤
  │ BCR-C-1.6  │ 2     │ missing +  │ 时限模糊 /    │
  │ 投诉       │       │ match      │ 模糊措辞      │
  ├────────────┼───────┼────────────┼───────────────┤
  │ BCR-C-1.8  │ 2     │ missing +  │ 未列保护工具  │
  │ Onward     │       │ match      │ / 标准模糊    │
  ├────────────┼───────┼────────────┼───────────────┤
  │ BCR-C-1.9  │       │ match +    │ 弱化措辞 /    │
  │ TIA        │ 3     │ missing +  │ 缺方法论 /    │
  │            │       │ missing    │ 缺定期更新    │
  └────────────┴───────┴────────────┴───────────────┘

  ---
  🔧 规则层
  
  模块 3：BCRRulebookLoader — 规则书加载器

  文件：backend/modules/bcr/bcr_rulebook_loader.py

  类：BCRRulebookLoader

  逻辑：

  构造时：
    ① 加载 bcr_rulebook.json
    ② _validate() 检查 7 个必备 section 是否存在

  对外暴露 9 个查询方法：
    get_bcr_c_signals()              → 12 个 BCR-C 信号词
    get_bcr_p_signals()              → 16 个 BCR-P 信号词
    get_mismatch_rules()             → 3 条混淆规则
    get_requirements(bcr_type)       → BCR-C: 14 条 /
  BCR-P: 5 条
    get_shared_requirements()        → 3 条共享
    get_all_requirements(type)       → 特定 + 共享
    get_required_sections(type)      → 必需章节名列表
    get_risk_weight(req_id)          → 整数权重
    get_severity_weight(severity)    → 10 / 5 / 2

  被依赖方：TypeClassifier、ChecklistChecker、ClauseRevie
  wer、RiskAggregator。

  ---
  模块 4：BCRTypeClassifier — 类型判定
  
  文件：backend/modules/bcr/bcr_type_classifier.py

  方法：classify(text, declared_type) → 
  BCRTypeClassification

  逻辑：

  ① 提取标题区（前 500 字）+ 正文区（前 8000 字）

  ② 加权信号评分：
     - 信号词在标题区出现 → 权重 ×2
     - 信号词仅在正文区出现 → 权重 ×1
     - c_score = sum(2.0 if s in title_t else 1.0 for s
  in c_hits)
     - p_score = sum(2.0 if s in title_t else 1.0 for s
  in p_hits)

  ③ actual_bcr_type 判定（6 级优先级）：
     c_score ≥ p_score + 1.0 → BCR-C
     p_score ≥ c_score + 1.0 → BCR-P
     c_score > 0, p_score = 0  → BCR-C
     p_score > 0, c_score = 0  → BCR-P
     都不满足 → unknown

  ④ 一致性判断：
     declared == actual → consistent (LOW)
     actual == unknown  → uncertain (MEDIUM)
     declared != actual → mismatch (HIGH)

  ⑤ 生成 evidence[]（匹配到的信号词列表）+ recommendation

  输出示例：
  {declared: "BCR-C", actual: "BCR-P", consistency:
  "mismatch", risk: "HIGH",
   evidence: ["BCR-P信号: on behalf of, Article 28"],
   recommendation: "文档标题为BCR-C但内容检测为BCR-P"}

  ---
  模块 5：BCRDocumentParser — 文档解析

  文件：backend/modules/bcr/bcr_document_parser.py

  类：BCRDocumentParser、BCRStructuredDocument、BCRStruct
  uredChapter

  方法：parse(file_id, file_path) → BCRStructuredDocument

  逻辑：

  ① 根据扩展名路由：
     .docx → python-docx 逐段逐表提取
     .pdf  → pypdf 逐页提取
     其他  → UTF-8 直接读取

  ② _extract_metadata() 提取 3 个字段：
     title:         匹配 "Binding Corporate Rules" /
  "BCR" 标题行
     version:       匹配 "Version X.X" / "V X.X"
     effective_date: 匹配英文日期格式

  ③ _segment_chapters():
     - 正则切分 "Section X / Chapter X / Article X / X.
  Title"
     - 每段 ≥ 80 字才保留
     - 提取 heading（首行前 100 字）
     - heading 映射到 18 个已知章节名（definitions,
  scope, binding,
       third party, liable, rights, complaint,
  cooperation, onward,
       TIA, audit, update, termination, government,
  breach, security,
       liability, data protection）
     - 检测 Annex / Appendix 标题

  输出：BCRStructuredDocument {
      file_id, filename, plain_text, title, version,
  effective_date,
      chapters[]: [{chapter_no, title, content}],
      appendix_titles[]
  }

  ---
  模块 6：BCRScenarioExtractor — 场景抽取

  文件：backend/modules/bcr/bcr_scenario_extractor.py

  方法：extract(text, doc, user_context) → 
  BCRScenarioContext

  逻辑：

  ① 公司名称提取（正则 "Company/Group/Entity..." +
  用户优先）
  ② EU 责任主体提取（正则 "EU entity / European /
  established in / located in"）
  ③ 处理者角色检测：
     正则 on_behalf_of_clients /
  according_to_instructions / Article_28 / as_a_processor
     → processes_on_behalf_of_clients: bool
  ④ 第三国检测：
     遍历 53 个国家名列表，逐个在文本中正则匹配
     合并用户手动指定的国家
  ⑤ 填充 auto_extracted_facts：
     has_eu_entity, processes_for_clients,
  third_country_count, document_title

  输出：BCRScenarioContext

  ---
  模块 7：BCRChecklistChecker — 5 状态强制要素检查
  
  文件：backend/modules/bcr/bcr_checklist_checker.py

  方法：check(doc, bcr_type) → (findings[], missing[])

  逻辑：

  ① 加载该类型全部审查要求（BCR-C: 17 条 = 14+3, BCR-P: 8
  条 = 5+3）

  ② 逐条调 _check_requirement() — 5 状态判断：

     Step A: 先执行 DSL checks
       pattern_type="match" + pattern 命中 → 直接返回
  VAGUE
       pattern_type="missing" + pattern 未命中 → 返回
  PARTIALLY_COVERED

     Step B: 关键词 + 结构匹配统计
       kw_count      = check_keywords 中有多少个出现在
  plain_text
       struct_matched = 任一 check_structure
  出现在章节标题

     Step C: 5 状态判定
       kw_count ≥ keywords_min AND struct_matched →
  FULLY_COVERED
       kw_count ≥ 1 OR struct_matched → PARTIALLY_COVERED
       都不满足 → MISSING

  ③ 非 FULLY_COVERED 的 → 生成 BCRFinding
     MISSING → 同时记录到 missing[]

  输出：list[BCRFinding] + list[str] missing

  Finding 标题示例：

  MISSING:    "缺失 Third-party beneficiary rights"
  PARTIALLY:  "EU liable entity designation 覆盖不完整"
  VAGUE:      "Complaint handling mechanism 表述模糊"

  ---
  模块 8-10：三个专项 Checker
  
  文件: bcr_tia_checker.py
  类: BCRTiaChecker
  检查项数: 5
  核心逻辑: 正则匹配
    "TIA/EDPB/periodic/supplementary/suspend" —
    未命中→MEDIUM finding
  ────────────────────────────────────────
  文件: bcr_onward_transfer_checker.py
  类: BCROnwardTransferChecker
  检查项数: 3
  核心逻辑: 正则匹配
  "SCC/adequacy/restrict/authorisation"
    — 未命中→HIGH/MEDIUM
  ────────────────────────────────────────
  文件: bcr_liability_checker.py
  类: BCRLiabilityChecker
  检查项数: 4
  核心逻辑: 正则匹配 "EU/liable/third party/compensate" —

    未命中→HIGH/MEDIUM

  三个 checker 均接收 BCRStructuredDocument，返回
  list[BCRFinding]。

  ---
  模块 11：BCRClauseReviewer — 条款级审查
  
  文件：backend/modules/bcr/bcr_clause_reviewer.py

  方法：review_clause(clause_text, requirement, bcr_type,
  legal_refs) → list[BCRFinding]

  4 层检查：

  ① 英文模糊表述（6 种正则）：
     as appropriate / where feasible / reasonable efforts
  /
     to the extent possible / as soon as reasonably
  practicable /
     substantially similar / essentially equivalent
     → MEDIUM finding

  ② 中文模糊表述（6 种正则）：
     及时 / 尽快 / 尽可能 / 合理努力 / 适当情况下 /
  在法律允许范围内
     → MEDIUM finding

  ③ BCR 专项 DSL 规则（7 条）：
     每条 = (pattern, pattern_type, severity, check_id,
  title, finding, recommendation)

     subprocessor_auth:      缺书面授权 → HIGH
     tia_incomplete:         TIA 方法不完整 → MEDIUM
     complaint_timeline:     投诉时限未明确 → MEDIUM
     gov_access_weak:        政府访问条款过宽 → MEDIUM
     binding_vague:          缺法律约束力文书 → HIGH
     dp_measures_vague:      数据保护措施模糊 → MEDIUM
     subprocessor_notice:    缺子处理者变更通知 → MEDIUM

  ④ 核心关键词缺失检查：
     取 requirement.check_keywords 前 3 个
     全不在 clause_text → MEDIUM: "{title} 描述不够具体"

  ---
  模块 12：BCRLegalRetriever — 法规检索
  
  文件：backend/modules/bcr/bcr_legal_retriever.py

  方法：retrieve(requirement_id, bcr_type, clause_text) →
  list[dict]

  逻辑：

  ① _build_query():
     "{bcr_type} {requirement_id} {clause_text[:200]}"
     例: "BCR-C BCR-C-1.2 third party beneficiary
  rights..."

  ② retrieve_regulations(query, top_k=3,
  jurisdiction="eu", path="all")

  ③ 转换：每个命中 → {source, section, snippet}

  ---
  模块 13：BCRRiskAggregator — 风险评分

  文件：backend/modules/bcr/bcr_risk_aggregator.py

  方法：aggregate(findings, missing, type_classification)
  → dict

  逻辑：

  ① 逐条评分：
     risk_score = requirement_weight × severity_weight
     例: BCR-C-1.2(权重9) × HIGH(10) = 90

  ② 综合评分：
     avg_score = 所有 finding 平均
     missing_penalty = 缺失项中 HIGH severity × 10
     overall_score = min(avg_score + missing_penalty,
  100.0)

  ③ 评级：
     type_consistency=mismatch + risk=HIGH →
  高风险（直接判定）
     overall_score ≥ 60 → 高风险
     overall_score ≥ 30 → 部分缺失
     其他 → 基本合规

  ④ 风险因子：
     - 所有 HIGH finding.title
     - 若类型判定为 HIGH: 追加 "BCR类型判定:
  {consistency}"

  输出：{overall_rating, overall_score, risk_factors[]}

  ---
  模块 14：BCRReportRenderer — 11 章报告
  
  文件：backend/modules/bcr/bcr_report_renderer.py

  方法：build_sections(type_class, findings, missing, 
  rating, score, metadata) → list[(title, lines)]

  11 个章节：

  一、报告摘要              → 类型 + 一致性 + 评级(分数)
  + 问题数/缺失数
  二、BCR 类型与适用路径判断 → 声明类型 / 检测类型 /
  一致性 / 风险 / 证据 / 建议
  三、文档结构完整性检查     → 缺失强制要素逐条列出
  四、第47条强制要素审查     → HIGH/MEDIUM/LOW 计数
  五、TIA + 政府访问请求     → TIA / government 相关
  findings
  六、Onward Transfer 审查   → onward / transfer 相关
  findings
  七、条款级问题清单         → 每条 finding
  完整展开（编号/要素/等级/发现/依据/建议/置信度）
  八、核心风险与整改优先级   → HIGH + MEDIUM 项分列
  九、法规与监管依据汇总     → 所有 legal_basis 去重排序
  十、建议补充材料           → 5 项固定建议
  十一、审查边界说明         → 限制 + 完成时间 + 审查模式
  + 范围

  ---
  模块 15：BCRService — 总调度器
  
  文件：backend/modules/bcr/service.py

  构造函数注入 16 个组件：

  规则层（12 个）：
    self.rulebook             ← BCRRulebookLoader
    self.type_classifier      ←
  BCRTypeClassifier(rulebook, llm)
    self.doc_parser           ← BCRDocumentParser
    self.checklist_checker    ←
  BCRChecklistChecker(rulebook)
    self.clause_reviewer      ← BCRClauseReviewer(llm,
  rulebook)
    self.scenario_extractor   ← BCRScenarioExtractor
    self.legal_retriever      ← BCRLegalRetriever
    self.risk_aggregator      ←
  BCRRiskAggregator(rulebook)
    self.report_renderer      ← BCRReportRenderer
    self.tia_checker          ← BCRTiaChecker
    self.onward_checker       ← BCROnwardTransferChecker
    self.liability_checker    ← BCRLiabilityChecker

  Agent 层（1 个字典含 10 个 Agent）：
    self.agents               ← create_agents(llm)

  旧组件（2 个）：
    self.parser               ← FileParser
    self.tasks                ←
  InMemoryTaskManager(module="bcr")

  入口路由：

  generate_report(payload)
    ├─ payload.uploaded_documents 非空
    │     → _run_document_driven_review()   ← 新路径
    │
    └─ payload.uploaded_documents 为空
          → _run_form_driven_review()        ← 旧兼容路径

  ---
  新路径：文档驱动 — 6.5 阶段完整调度
  
  ┌──────────────────────────────────────────────────────
  ────────┐
  │ Stage 1: PARSING
        │
  │
         │
  │ ⑩ BCRDocumentParser.parse() × 每个上传文件
         │
  │   → list[BCRStructuredDocument]
        │
  │ ⑪ combined_text = "\n".join(plain_text)
        │
  │ ⑫ main_doc = sdocs[0]
        │
  ├──────────────────────────────────────────────────────
  ────────┤
  │ Stage 2: TYPE_CHECKING
        │
  │
         │
  │ ⑬ BCRTypeClassifier.classify(combined_text,
  declared_type)  │
  │   → BCRTypeClassification (BCR-C / BCR-P / mismatch)
        │
  │ ⑭ actual=unknown → fallback "BCR-C"
        │
  │
         │
  │ 🤖 Agent 1: type_reasoning (触发条件: actual=unknown)
         │
  │   输入: text + declared_type + c_score/p_score +
  evidence   │
  │   输出: type_judgment + confidence + risk_level
        │
  │   作用: 修正 fallback，返回 "BCR-C"/"BCR-P"/"mixed"
         │
  ├──────────────────────────────────────────────────────
  ────────┤
  │ Stage 3: SCENARIO_EXTRACTION
        │
  │
         │
  │ ⑮ BCRScenarioExtractor.extract(combined_text, doc,
  ctx)     │
  │   → BCRScenarioContext (company, eu_entity,
  countries...)   │
  │
         │
  │ 🤖 Agent 3: actor_role (触发条件: 始终)
         │
  │   输入: text + entities list
        │
  │   输出: entities[] + eu_liable_entity + has_clear_eu
        │
  │   作用: 补充正则未能识别的 EU 责任主体
          │
  ├──────────────────────────────────────────────────────
  ────────┤
  │ Stage 4: CHECKLIST_CHECKING
        │
  │
         │
  │ ⑯ BCRChecklistChecker.check(main_doc, bcr_type)
        │
  │   → 5 状态逐条检查 (FULLY / PARTIALLY / VAGUE /
  MISSING)    │
  │   → (checklist_findings[], missing_reqs[])
        │
  ├──────────────────────────────────────────────────────
  ────────┤
  │ Stage 4.5: SPECIALIZED CHECKERS + AGENTS
        │
  │
         │
  │ ⑰ BCRTiaChecker.check(main_doc)          → 5 项 TIA
  检查    │
  │ ⑱ BCROnwardTransferChecker.check(main_doc) → 3 项 OT
  检查   │
  │ ⑲ BCRLiabilityChecker.check(main_doc)    → 4
  项责任检查     │
  │
         │
  │ 🤖 Agent 2: coverage (触发: PARTIALLY/VAGUE + HIGH
  severity) │
  │   输入: requirement + matched_clauses + legal_basis
        │
  │   输出: coverage_status + missing_elements +
  finding_text    │
  │   作用: 判断"实质满足"而非"关键词出现"
          │
  │
         │
  │ 🤖 Agent 4: onward_transfer (触发: 含 onward 章节)
         │
  │   输入: clause_text +
  has_scc/has_adequacy/has_derogation   │
  │   输出: protection_adequate + finding_type +
  recommendation  │
  │   作用: 判断"实质等同保护"而非"出现关键词"
          │
  │
         │
  │ 🤖 Agent 5: tia_reasoning (触发: 含 TIA 章节)
         │
  │   输入: tia_section + gov_access_section + legal_refs
         │
  │   输出: tia_completeness + 5 个 bool +
  finding_summary       │
  │   作用: 判断 TIA 是完整可执行流程，而非空洞承诺
          │
  ├──────────────────────────────────────────────────────
  ────────┤
  │ Stage 5: CLAUSE_REVIEWING
        │
  │
         │
  │ ⑳ 遍历 main_doc.chapters × requirements
        │
  │   每个 chapter 与 requirement.check_keywords[:3] 匹配
         │
  │   匹配 → BCRLegalRetriever.retrieve() +
        │
  │          BCRClauseReviewer.review_clause()
         │
  │    4 层检查: 英文模糊词 → 中文模糊词 → 7条DSL →
  关键词缺失   │
  ├──────────────────────────────────────────────────────
  ────────┤
  │ 去重
        │
  │ ⑳ 按 finding.title 去重
        │
  ├──────────────────────────────────────────────────────
  ────────┤
  │ Stage 6: AGGREGATING + RENDERING
        │
  │
         │
  │ ⑳ BCRRiskAggregator.aggregate(findings, missing,
  type_class) │
  │   → rating + score + risk_factors
        │
  │
         │
  │ 🤖 Agent 9: approval_risk (触发: 评分完成后)
         │
  │   输入: findings + rating + score + type_consistency
         │
  │   输出: approval_blockers + rating_adjustment
         │
  │   作用: 复核是否存在审批阻断项，必要时上调评级
         │
  │
         │
  │ ⑳ BCRReportRenderer.build_sections() → 11 章
        │
  │ ⑳ 渲染 docx + md + zip
        │
  │ ⑳ 返回 BCRResult
        │
  └──────────────────────────────────────────────────────
  ────────┘

  ---
  旧路径：表单驱动 — 保留完整的旧 6 步骤

  ① _extract_problems()      → score≠compliant →
  BCRProblem[]（HIGH/MEDIUM）
  ② _resolve_rating()        → non_compliant≥2→高风险 /
  ≥1→部分缺失 / 0→基本合规
  ③ _check_consistency()     → 10 个 code 完整性 +
  附件缺失 + 高风险提醒
  ④ retrieve_regulations()   → 固定查询 "GDPR BCR Article
  47 onward transfer liability"
  ⑤ _generate_chapters()     → 4 章（LLM
  仅用于"报告摘要"和"风险优先级与整改建议"）
  ⑥ _render()                → docx + md + zip

  ---
  🤖 Agent 层
  
  Base Agent

  文件：backend/modules/bcr/agents/__init__.py

  类：BCRAgentBase

  属性：
    agent_name: str = "base"
    temperature: float = 0.1
    max_tokens: int = 600

  方法：
    enabled → bool           (llm_client 存在且 enabled)
    _call_llm(prompt) → dict | None  (解析 JSON，失败返回
  None)
    run(**kwargs) → dict     (子类实现)

  system prompt：
    "You are an EU data protection lawyer specializing in
  BCR review
     under GDPR Article 47 and EDPB Recommendations
  1/2022 and 2/2022.
     Output ONLY valid JSON."

  工厂方法：create_agents(llm_client) → dict[str, 
  BCRAgentBase]，返回 10 个 Agent 实例。

  10 个 Agent 逐个逻辑

  #: 1
  Agent 文件: type_reasoning_agent.py
  Prompt 核心问题: 判定 BCR-C vs   
    BCR-P，当规则分数接近时介入
  输入: text(3000字) + declared_type + c_score/p_score +
    evidence
  输出结构: {type_judgment, confidence, 
  reasoning_summary,
     recommended_path, risk_level}
  ────────────────────────────────────────
  #: 2
  Agent 文件: coverage_agent.py
  Prompt 核心问题: 判断 requirement
    是否实质满足，而非仅关键词出现
  输入: requirement + matched_clauses + coverage_status +

    legal_basis
  输出结构: {coverage_status, missing_elements[],
    risk_level, should_generate_finding,  finding_text,
    recommendation}
  ────────────────────────────────────────
  #: 3
  Agent 文件: actor_role_agent.py
  Prompt 核心问题: 从实体列表中识别 EU
    责任主体、数据输出方等角色
  输入: text(5000字) + entities[{name, context}]
  输出结构: {entities[{name, location, roles[],
    evidence}], eu_liable_entity, has_clear_eu}
  ────────────────────────────────────────
  #: 4
  Agent 文件: onward_transfer_agent.py
  Prompt 核心问题: 判断 Onward Transfer
    保护水准是否实质足够
  输入: clause_text(800字) +
    has_scc/has_adequacy/has_derogation
  输出结构: {protection_adequate, finding_type,
    risk_level, finding, recommendation}
  ────────────────────────────────────────
  #: 5
  Agent 文件: tia_reasoning_agent.py
  Prompt 核心问题: 判断 TIA 是否为完整可执行流程
  输入: tia_section(1500字) + gov_access_section +
    legal_refs
  输出结构: {tia_completeness, 5 has_* flags,
    missing_elements[], risk_level,  finding_summary,
    recommendation}
  ────────────────────────────────────────
  #: 6
  Agent 文件: evidence_coverage_agent.py
  Prompt 核心问题: 区分正文 vs 附件的证据来源
  输入: requirements + file_roles + body/annex text_len
  输出结构: {coverage_map[{requirement_id, 
    coverage_source, assessment, risk}]}
  ────────────────────────────────────────
  #: 7
  Agent 文件: incorrect_status_agent.py
  Prompt 核心问题: 检测"写了但写错"的条款
  输入: clause(800字) + requirement + bcr_type +
    mismatch_signals
  输出结构: {coverage_status, finding, risk_level,
    recommendation}
  ────────────────────────────────────────
  #: 8
  Agent 文件: legal_grounding_agent.py
  Prompt 核心问题: 分类引用是
  primary/supporting/discarded
  输入: finding_title + finding_text + citations +
    requirement_id
  输出结构: {primary_basis[], supporting_basis[],
    discarded_basis[], grounding_adequate}
  ────────────────────────────────────────
  #: 9
  Agent 文件: approval_risk_agent.py
  Prompt 核心问题: 复核是否存在审批阻断项
  输入: findings + rating + score + type_consistency
  输出结构: {approval_blockers[], rating_adjustment, 
    adjustment_reason, critical_missing[],
    overall_assessment}
  ────────────────────────────────────────
  #: 10
  Agent 文件: remediation_agent.py
  Prompt 核心问题: 生成可执行修改建议（条款草案）
  输入: finding + legal_basis + existing_text
  输出结构: {fix_type, insert_location, 
    suggested_text(300词), rationale,  key_elements[]}

  已集成的 Agent（5 个，有明确 pipeline 位置）：1, 2, 3,
  4, 5, 9

  按需调用的 Agent（4 个）：6, 7, 8, 10（已在 self.agents
  字典中，可在任何位置显式调用）

  Agent 失败处理：_call_llm() 返回 None 时使用结构化
  fallback（默认 JSON）静默降级，不阻塞 pipeline。

  ---
  完整数据流总图

  BCRRequest { company_name, uploaded_documents[]?,
  review_items[]?, ... }
    │
    ├─ uploaded_documents 非空
    │
    │     Stage 1: PARSING              BCRDocumentParser
  × N 文件
    │     Stage 2: TYPE_CHECKING
  BCRTypeClassifier  ──→ Agent 1 (if uncertain)
    │     Stage 3: SCENARIO_EXTRACTION
  BCRScenarioExtractor ──→ Agent 3 (actor roles)
    │     Stage 4: CHECKLIST_CHECKING
  BCRChecklistChecker (5-state)
    │     Stage 4.5: SPECIALIZED         TiaChecker +
  OnwardChecker + LiabilityChecker
    │                + AGENTS            ──→ Agent 2
  (coverage) + Agent 4 (onward) + Agent 5 (TIA)
    │     Stage 5: CLAUSE_REVIEWING
  BCRClauseReviewer (4-layer) + BCRLegalRetriever
    │     Stage 6: AGGREGATING
  BCRRiskAggregator  ──→ Agent 9 (approval risk)
    │               RENDERING
  BCRReportRenderer (11-chapter)
    │                                       ↓
    │                                    BCRResult {
  findings[], missing[], rating, type_class, ... }
    │
    └─ uploaded_documents 为空
          ──→ 旧 6 步骤表单驱动 ──→ BCRResult {
  problems[], rating, ... }

  回归状态

  Case 1 (BCR-C basic):      2/3 ✓  (complaint vague +
  TIA incomplete)
  Case 2 (BCR-C high risk):  4/4 ✓  (third party + EU
  entity + binding + onward)
  Case 3 (BCR mismatch):     type=mismatch, actual=BCR-P
  ✓
  旧表单驱动:                 PASS ✓
