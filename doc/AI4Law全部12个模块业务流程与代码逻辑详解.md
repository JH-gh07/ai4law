# AI4Law 全部12个模块业务流程与代码逻辑详解

> **目的**：逐一拆解后端每个模块的 `generate_report()` 方法，讲清楚它做什么、怎么做、输入输出什么、每一步的代码逻辑。

---

## 目录

- [系统两层架构总览](#系统两层架构总览)
- [第一层：路径层](#第一层路径层)
  - [模块1：中国路径诊断（diagnosis）](#模块1中国路径诊断diagnosis)
  - [模块2：美国EO14117适用性判断（us_14117）](#模块2美国eo14117适用性判断us_14117)
- [第二层A：合同审查类](#第二层a合同审查类)
  - [模块3：通用文档审查（review）](#模块3通用文档审查review)
  - [模块4：中国标准合同审查（SCC）](#模块4中国标准合同审查scc)
  - [模块5：欧盟SCC审查（eu_scc）](#模块5欧盟scc审查eu_scc)
  - [模块6：BCR审核（bcr）](#模块6bcr审核bcr)
- [第二层B：填表格类](#第二层b填表格类)
  - [模块7：CPRA合规（cpra）](#模块7cpra合规cpra)
- [第二层C：草案模板生成类](#第二层c草案模板生成类)
  - [模块8：安全自评估（assessment）](#模块8安全自评估assessment)
  - [模块9：CN Flow（cn_flow）](#模块9cn-flowcn_flow)
  - [模块10：PIPIA（pipia）](#模块10pipiapipia)
  - [模块11：DPIA（dpia）](#模块11dpiadpia)
  - [模块12：TIA（tia）](#模块12tiatia)
- [汇总对比表](#汇总对比表)

---

## 系统两层架构总览

所有 12 个模块按业务分为两层三类：

```
第一层：路径层
  模块1: diagnosis     — 判断中国合规路径
  模块2: us_14117      — 判断美国EO14117适用性

第二层：功能层
  A. 合同审查类（审已有文本，给修改建议）
     模块3: review     — 通用文档合规审查
     模块4: scc        — 中国标准合同审查
     模块5: eu_scc     — 欧盟SCC审查
     模块6: bcr        — BCR审核
  
  B. 填表格类（用户描述进来，合规清单出去）
     模块7: cpra       — 加州CPRA合规全景诊断
  
  C. 草案模板生成类（用户输入事实，系统按模板生成文书）
     模块8: assessment — 数据出境安全自评估
     模块9: cn_flow    — 数据流合规检查
     模块10: pipia     — 个人信息保护影响评估
     模块11: dpia      — 数据保护影响评估
     模块12: tia       — 传输影响评估
```

---

## 第一层：路径层

---

### 模块1：中国路径诊断（diagnosis）

**一句话定位**：交互式问答，判断企业该走安全评估、标准合同备案还是认证路径。

**核心入口**：`DiagnosisService.evaluate(answers) -> DiagnosisResult`

**业务流程（5层递进）**：

```
第1层：数据规范化（_normalize_answers）
    → 6条自动校正规则
    → 从用户详细模块推断简答字段的不确定项

第2层：AI代理辅助澄清（3个Agent，条件触发）
    → ImportantDataAgent：q2==unknown时，启发式评分+LLM精化
    → PIClassifyAgent：q5==unknown时，3层标识符检测+LLM
    → ExemptionAgent：q6=="other"时，4类信号检测+LLM

第3层：决策树规则匹配（9条规则，逐条匹配）
    → 豁免规则1-5优先，安全评估规则6-9其次

第4层：AI推测兜底（_needs_ai_inference条件触发）
    → 关键字段大量unknown + 缺乏结构化信号
    → LLM推测，置信度LOW，注明"需人工复核"

第5层：AI生成专业解释（_build_rule_explanation）
    → LLM将简短规则描述扩展为2-3句专业中文解释
```

**输入数据结构**：`DiagnosisAnswers`（7个核心判断题 + 5个扩展模块字段）

**输出数据结构**：`DiagnosisResult`（11个字段：推荐路径、法律依据、理由、行动建议、风险等级、结论来源、置信度、匹配规则编号、最终解释、不确定性说明）

**关键设计决策**：
- 主判断来自规则引擎，不由AI直接决定
- 豁免规则排在安全评估规则前面（先看能否免，不能免再看是否强制申报）
- 豁免规则对CIIO/重要数据用 `["no", "unknown"]`（从宽），安全评估规则用 `["yes"]`（从严）
- AI代理失败静默降级为启发式结论

**输出文件**：HTML + PDF 诊断报告

---

### 模块2：美国EO14117适用性判断（us_14117）

**一句话定位**：判断特定数据交易是否受美国第14117号行政令管辖。

**核心入口**：`US14117Service.generate_report(payload) -> US14117Result`

**业务流程**：

```
第1步：规则引擎先行（run_rule_engine）
    → 逐项判断：每个实体是否"受覆盖主体"
    → 逐项判断：每类数据是否触及批量阈值
    → 判断交易类型是否属于受限制类别
    → 给出交通灯信号（红/黄/绿）

第2步：AI边界复核（rule_boundary Agent）
    → 对置信度<85%的受覆盖主体判定做复核
    → 对阈值边界±10%的数据类别做复核
    → 对"其他"交易类型做复核

第3步：接入标准WorkflowPipeline
    → 规则引擎结果作为特殊的"诊断结果"
    → 事实提取 → 法规检索 → 问题构建 → 证据构建 → 上下文包 → AI生成4章 → 一致性校验 → 输出

第4步：RAG检索时AI改写查询（rag_reformulation Agent）
    → 将规则命中摘要+数据类别+交易类型组合
    → 生成精准的法规检索查询语句
```

**输出**：交通灯信号、风险矩阵、规则命中清单、4章合规报告（MD + DOCX + PDF + XLSX + ZIP）

**关键特点**：同时具备"路径判断"（规则引擎）和"合规报告生成"（流水线）两种能力，在当前系统中实际运行在功能层流水线上。

---

## 第二层A：合同审查类

**共同特征**：用户上传已有合同/条款文本，系统审查原文并给出修改建议。

---

### 模块3：通用文档审查（review）

**一句话定位**：上传任意数据保护相关文档，系统自动识别文档类型并逐条审查。

**核心入口**：`ReviewService._run_pipeline(task_id, user_id)`

**业务流程（8阶段流水线）**：

```
阶段0：PREPARING（0-10%）
    → 文档分类（DocumentClassifier）：判断上传的是隐私政策/DPA/SCC/数据安全协议
    → 场景提取（ScenarioExtractor）：从文档中提取处理活动、数据流向、参与方角色
    → 结构化解析（StructuredDocumentParser）：提取表格、附录字段

阶段1：SEGMENTING（10-25%）
    → 条款拆分（ClauseSegmenter）：将文档按条款结构拆为独立审查单元

阶段2：CLASSIFYING（25-45%）
    → 条款分类（ClauseClassifier）：逐条款判断属于哪类合规要求
    → 分类依据：规则手册中的条款类型定义+关键词匹配+LLM辅助

阶段3：MISSING_CHECK（45-55%）★ 新增
    → 缺失项检查（MissingItemChecker）：判断必要条款是否完全缺失
    → 根据文档类型检查必备条款清单

阶段4：REVIEWING（55-80%）— 核心阶段
    → 风险触发的LLM选择：
      - 高优先级类型（跨境传输/敏感个人信息等）→ 必用LLM
      - 中优先级类型+文本≥120字 → 用LLM
      - 包含高风险短语（"香港法院""责任总额不超过"等）→ 最高优先级
      - deep模式 → 全部条款用LLM
    → 调用ClauseReviewer逐条审查
    → 规则层面：专项审查器（隐私政策/SCC/DPA/数据安全协议）各有专属审查规则
    → LLM层面：规则引擎标记的模糊/高风险条款送LLM深度分析
    → 引用相关性校验（CitationRelevanceChecker）：判断引用的法规是否真正适用

阶段5：CROSS_DOC_CHECK（80-85%）★ 新增
    → 交叉文档一致性检查（CrossDocConsistencyChecker）
    → 仅当上传多份文档+启用此功能时执行
    → 检查不同文档中对同一概念的定义是否一致

阶段6：AGGREGATING（85-92%）
    → 结果聚合（ReviewAggregator）：合并审查发现+缺失项+一致性警告
    → 风险评分（RiskScorer）：给出综合风险评级

阶段7：RENDERING（92-100%）
    → 报告渲染（ReviewReportRenderer）：生成审查报告DOCX
    → 批注版文档（AnnotatedDocxBuilder）：在原DOCX上叠加批注（仅DOCX输入）
```

**输出**：审查报告DOCX + 批注版DOCX（每个源文件一个）

**关键设计**：
- LLM不是审所有条款，而是只审高风险条款（max_llm_clauses上限=20）
- 批注版文档是best-effort（失败不阻断主流程）
- 交叉文档一致性检查是可选的（enable_cross_document_check开关）

---

### 模块4：中国标准合同审查（SCC）

**一句话定位**：审查用户上传的标准合同草案是否符合《个人信息出境标准合同办法》的要求。

**核心入口**：`SCCService.generate_report(payload) -> SCCResult`

**业务流程（13阶段 + 9个Agent）**：

```
阶段1：提取企业画像
    → 从请求中提取所有字段+解析上传文件（FileParser）

阶段2：路径诊断Agent（P0）★
    → 基于CIIO/重要数据/规模/接收方/行业等重新判断路径
    → 即使用户选了SCC模块，Agent仍会独立判断实际应走哪条路径
    → 路径不匹配时在报告中标记风险

阶段3：数据分类Agent（P0）
    → 逐数据字段审查：是否构成个人信息/敏感个人信息
    → 审查出境必要性

阶段4：合同审查Agent（P0）★ 最核心
    → 从上传文件中提取合同正文（优先匹配含scc/contract/合同/协议/dpa的文件名）
    → 逐条审查合同必备条款是否完整、表述是否规范

阶段5：合法性基础审查Agent（P1）
    → 审查企业主张的每项合法性基础是否成立
    → 交叉验证：隐私政策摘要 vs 合同摘要 vs 员工手册 vs 集体协议 vs 同意记录

阶段6：证据核验Agent（P1）
    → 针对每项用户主张检查是否有对应材料支撑
    → 从请求中提取用户声明（如"已取得80万人同意"）→ 逐条核验

阶段7：事实/问题/证据构建
    → fact_builder：基于请求+画像+Agent结果构建事实清单
    → issue_builder：基于事实+路径诊断+分类结果+合同发现+合法性审查+证据核验构建问题清单
    → RAG检索规划Agent（P2）：为每个问题生成精准法规检索查询
    → 按Agent规划的查询逐条检索法规（retrieve_regulations）
    → 用检索到的法规重新构建问题清单
    → evidence_builder：构建证据链

阶段8：上下文块构建
    → 拼接企业信息+路径诊断+问题清单+证据链+法规参考

阶段9：LLM生成4章报告
    → 审查依据说明 → 总体合规评级 → 条款级问题清单 → 修订建议与行动计划

阶段10：对齐检查
    → check_cn_alignment：检查报告中是否提及接收方国家

阶段11：报告审稿Agent（P1）
    → 审稿复核：结论是否有依据、建议是否具体、是否有遗漏风险点

阶段12：澄清Agent（P2）
    → 生成影响最大的3-5个后续问题

阶段13：解释Agent（P2）
    → 将内部trace/事实/问题/证据转换为人类可读的"生成逻辑说明"

阶段14：输出渲染
    → MD报告 + DOCX报告 + 批注版DOCX（可选）
```

**输出**：MD + DOCX + 批注版DOCX（可选）

**关键设计**：
- Agent失败静默降级，不阻断主流程
- 路径诊断Agent独立判断，即使与用户选择矛盾也标记出来
- 批注版DOCX通过DocxComment在原文上直接标注问题和修改建议

---

### 模块5：欧盟SCC审查（eu_scc）

**一句话定位**：审查欧盟标准合同条款（SCC）文件的完整性和合规性。

**核心入口**：`EU_SCCService.generate_report(payload) -> SCCReviewResult`

**业务流程**：

```
前置阶段（流水线前）：
    ① SCC文档解析（parse_scc_document）：识别模块类型、导出方/导入方角色、条款内容
    ② 文档结构Agent：从原文推断缺失字段（导出方/导入方角色等）
    ③ 传输链路构建（_build_transfer_chain）：构建数据逐跳传输链路图
    ④ 传输链路Agent：分析链路合理性，给出风险提示
    ⑤ EU SCC规则引擎（run_eu_scc_rule_engine）：
       - 审查必要条款是否完整
       - 检查可选条款的选用是否合理
       - 判断模块选择是否正确（模块一/二/三/四）
       - 检查TIA是否已包含、补充措施是否充分
    ⑥ 条款语义比较Agent：对比文档条款与标准SCC条款的语义差异
    ⑦ TIA有效性Agent：评估传输影响评估和补充措施的充分性
    ⑧ 重新评分：根据Agent发现更新综合评级

流水线阶段（WorkflowPipeline）：
    事实提取 → 法规检索(GDPR) → 附件解析 → 问题构建 → 证据构建 → 上下文包 → AI生成4章

后置阶段（流水线后）：
    ⑨ 证据审查Agent：回顾性检查facts/issues/evidence与findings的对齐
    ⑩ 整改生成Agent：为每条finding生成具体的条款修改建议文本
```

**输出**：MD报告 + 占位DOCX + findings.json + rule_engine_result.json + issues.json + evidence.json + 批注版DOCX（可选）+ citation_map.json

**关键差异**：DOCX目前仅为空壳（touch创建），实际报告内容在MD中。

---

### 模块6：BCR审核（bcr）

**一句话定位**：审查跨国公司的约束性公司规则（BCR）文件是否符合GDPR第47条要求。

**核心入口**：`BCRService.generate_report(payload) -> BCRResult`

**业务流程（双轨道）**：

**轨道A：文档驱动审查（用户上传了BCR文档）**

```
阶段1：文档解析（BCRDocumentParser）
    → 解析文档的章节结构、条款内容、附件列表

阶段2：BCR类型识别（BCRTypeClassifier）
    → 关键词+结构特征判断BCR-C（控制者版）还是BCR-P（处理者版）
    → 类型不确定时 → 类型推理Agent分析全文
    → 用户声明与实际不一致 → 标记风险

阶段3：场景提取（BCRScenarioExtractor）
    → 提取集团公司名称、数据传输范围、欧盟责任实体
    → 角色识别Agent：正则无法定位时从上下文推断EU liable entity

阶段4：清单式逐项审查 ★ 核心
    → 规则手册内置GDPR第47条全部必备要素（BCR-C 10项核心要求）
    → 每个要求判定：完全覆盖/部分覆盖/模糊覆盖/缺失
    → 三个专项检查器并行：
      - TIA检查器：第三国法律环境评估是否充分
      - 再转移检查器：再转移保护标准是否充分
      - 责任分配检查器：责任和赔偿条款是否清晰

阶段4.5：Agent深度审查（5个Agent并行触发）
    → 覆盖分析Agent：部分覆盖的高严重度要求→深度阅读判断
    → 再转移推理Agent：保护标准偏弱→判断是否需补充SCC
    → TIA完整性推理Agent：检查TIA是否涵盖政府访问/Schrems II/EDPB
    → 证据覆盖Agent：关键义务在正文还是仅在附件（附件约束力弱于正文）
    → 条款不匹配Agent：检测BCR-C中是否混入了BCR-P的处理者条款

阶段5：法规检索+风险聚合+渲染输出
```

**轨道B：表单驱动审查（用户没上传文档）**
    → 用户填写企业基本信息和数据流转情况
    → 基于规则手册做简化清单检查
    → 生成基础审查报告

**输出**：MD + DOCX + ZIP（文档驱动模式下额外包含更详细的审查发现）

---

## 第二层B：填表格类

---

### 模块7：CPRA合规（cpra）

**一句话定位**：企业描述业务情况，系统生成合规差距表和整改清单。

**核心入口**：`CPRAService.generate_report(payload) -> CPRAResult`

**业务流程**：

```
第1步：附件事实提取
    → CPRAAttachmentExtractor：从隐私政策/数据地图/供应商清单中提取结构化事实
    → fact_extraction Agent：AI增强——判断附件完整性、识别未覆盖领域

第2步：事实合并（CPRAFactMerger）
    → "用户表单填写" + "附件提取" → 统一事实视图
    → 冲突时表单优先

第3步：规则引擎差距分析（run_all_rules）
    → 对4个领域做确定性检查：
      告知与同意 / 消费者权利 / Opt-out机制 / 供应商管理
    → 逐项判断：满足/不满足/部分满足
    → 输出：CPRAGapItem列表（含领域、风险等级、差距描述、法律依据、整改建议、整改阶段）

第4步：回退规则
    → 如果结构化输入缺失 → _build_legacy_gap_items()
    → 用关键词检测做4条简化规则

第5步：SPI风险评估Agent
    → 敏感信息共享风险分析：哪些SPI被哪些供应商访问？是否存在未声明路径？
    → 输出gap候选项 → gap_merger合并

第6步：供应商合同审查Agent
    → 检查每个供应商是否有DPA、合同条款是否满足CPRA要求
    → 输出gap候选项 → gap_merger合并

第7步：法规引用匹配（CPRALegalRetriever）
    → 逐差距精准检索 → 领域级兜底检索
    → 构建CitationBundle（引用注册表+引用编号+法规全文）

第8步：综合评分（_resolve_overall_level）
    → 有HIGH→整体HIGH；无HIGH有MEDIUM→整体MEDIUM；全LOW→整体LOW

第9步：AI生成6章全景报告
    → 执行摘要 → 适用性与范围 → 数据处理合规分析 → 消费者权利保障 →
      敏感信息与第三方管理 → 行动清单与优先级

第10步：一致性审查（consistency_review Agent）
    → 检查报告结论是否与事实一致、HIGH差距是否充分强调、章节间评级是否一致

第11步：渲染输出
    → MD + DOCX + PDF + XLSX整改路线图 + ZIP + citation_map.json
```

**输出**：MD + DOCX + PDF + XLSX（含domain/risk_level/gap/legal_basis/recommendation/phase/evidence_source 7列）+ ZIP

---

## 第二层C：草案模板生成类

**共同特征**：用户只有业务事实，系统从零按固定模板生成完整合规文书。

**共同的流水线模式**（通过 WorkflowPipeline 编排）：

```
提取画像 → 路径诊断 → 路径校验 → 事实构建 → 法规检索 → 附件解析
→ 问题构建 → 证据构建 → 逐问题RAG(可选) → 上下文包组装
→ AI生成章节 → 一致性检查 → 对齐检查 → 修复轮次 → 渲染输出
```

---

### 模块8：安全自评估（assessment）

**一句话定位**：生成符合《数据出境安全评估办法》要求的《数据出境风险自评估报告》。

**核心入口**：`AssessmentService.generate_report(payload) -> AssessmentResult`

**业务流程**：

```
步骤1：提取企业画像（ProfileExtractor）
    → AssessmentRequest中的结构化字段 → CompanyProfile对象

步骤2：路径诊断 ★ 注意：这里调用的是真实的DiagnosisService
    → 将AssessmentRequest字段映射为DiagnosisAnswers
    → 行业/目的/接收方关键词推断出境场景和接收方类型
    → 数据资产清单提取个人信息/敏感信息/重要数据类型
    → 调用DiagnosisService.evaluate()做完整的5层路径诊断
    → 得到推荐路径+风险等级

步骤3：路径校验
    → 如果诊断推荐的不是安全评估路径→根据path_check_mode处理
    → generate_only: 生成但加入警告
    → warn_only: 生成但加入警告（默认）
    → block_on_mismatch: 阻断（除非force_override_path=true）

步骤4：构建事实清单（build_assessment_facts）
    → 将请求+画像+诊断结果→20+条FactItem

步骤5：法规检索（AssessmentRetriever）
    → 检索中国工作流规则+法律条文+模板+测试用例
    → 合并V3编排器结果+兜底检索结果
    → 提取RetrievalBundle中的四层知识

步骤6：提取附件备注（_attachment_notes_from_profile）
    → 从画像的attachment_metadata中提取6种文件类型的结构化信息
    → 合同条款覆盖情况/认证信息/同意记录/审计报告/数据清单/政策文件

步骤7：构建问题清单（build_assessment_issues）
    → 基于规则引擎：逐项检查CIIO/重要数据/规模门槛/材料缺失等

步骤8：构建证据链（build_assessment_evidence）
    → 为每个问题建立事实→法规→结论的推理链
    → 完成后回填问题的evidence_refs

步骤9：逐问题RAG（可选，_retrieve_per_issue）
    → 对HIGH/BLOCKER问题调用DeliLegal API补充法规和案例
    → search_laws(问题标题+描述, 3条) + search_cases(同上, 2条)

步骤10：组装生成上下文包 ★ 最复杂的步骤
    → 模板检索（RetrievalOrchestrator二次调用，检索安全评估模板章节结构）
    → 法律依据构建（build_legal_grounding）：三阶段评分
    → 写作策略构建（build_writing_strategy）：每个问题的对内/对外表述
    → 合规推理构建（build_compliance_reasoning）：8个维度的成熟度评估
    → 生成基础包（build_generation_basis_pack）：按章节分组的section_packs
    → 引用注册表（CitationRegistry）：注册所有法规引用+分配全局编号

步骤11：AI生成8章报告（AssessmentChapterGenerator）
    → 每章从上下文包中筛选相关facts/issues/evidence/regulations/writing_strategies
    → 构建章节专属context_block → 拼接strict_constraints → 调用LLM
    → 后处理：引用标记替换（{{CIT-xxx}}→[1][2][3]）

步骤12：一致性检查（ConsistencyChecker）
    → 维度1：上下文包内部引用完整性（fact_refs/rule_refs/evidence_refs是否存在）
    → 维度2：报告内容与上下文包的一致性（HIGH问题是否被提及、缺失材料是否写了"齐备"）
    → 维度3：报告内容与用户输入的对齐（check_cn_alignment）

步骤13：修复轮次（run_repair_pass）
    → 将问题+受影响章节→LLM针对性修改→重新检查
    → 最多3轮 → 3轮后仍有问题→标记REPAIR_BLOCKED

步骤14：渲染输出（AssessmentReportRenderer）
    → 内部风险分析报告MD+DOCX
    → 官方自评估报告MD+DOCX
    → 问题清单JSON+XLSX
    → 证据链JSON+XLSX
    → 材料清单XLSX+JSON
    → 事实/路径判断/法律依据/写作策略JSON
    → ZIP打包
```

**输出**：内部MD+DOCX + 官方MD+DOCX + 3个XLSX + 10个JSON + ZIP + trace manifest

**关键特点**：
- 是所有模块中中间产物最完整的一个
- 唯一的"双报告"模块（内部审查版+官方提交版）
- 唯一的"完整引用注册表+标记替换"模块

---

### 模块9：CN Flow（cn_flow）

**一句话定位**：检查数据流场景是否满足合规要求，给出风险评级。

**核心入口**：`CNFlowService.generate_report(payload) -> CNFlowResult`

**业务流程**：

```
步骤1：直接使用请求对象作为画像（无ProfileExtractor）

步骤2：诊断（_evaluate_diagnosis）
    → _build_risk_items()：规则引擎——检查3个触发条件
      ① 敏感数据标记 → HIGH风险"存在敏感数据跨境流动"
      ② 接收方为受限主体 → HIGH风险
      ③ 传输链路含subprocessor/第三方 → MEDIUM风险
      ④ 以上都不触发 → LOW风险"暂未识别高风险"
    → _resolve_overall_level()：有HIGH→整体HIGH

步骤3：接入WorkflowPipeline
    事实构建 → 法规检索（retrieve_regulations, US法域）→ 附件解析
    → 问题构建 → 证据构建 → 上下文包 → AI生成4章
    → 一致性检查 → 渲染输出（MD+DOCX+PDF+XLSX+ZIP+中间产物JSON）
```

**输出**：MD + DOCX + PDF + XLSX风险清单 + ZIP + issue_list.json + evidence_chain.json + facts.json

**关键特点**：
- 诊断是轻量的规则检查，不需要外部诊断服务
- 风险矩阵可视化为"实体×数据类别"的交通灯表
- 文件名中有"14117"字样（历史遗留），但模块名已经是cn_flow

---

### 模块10：PIPIA（pipia）

**一句话定位**：生成中国《个人信息保护法》要求的个人信息保护影响评估报告。

**核心入口**：`PIPIAService.generate_report(payload) -> PIPIAResult`

**业务流程**（最简架构）：

```
1. 解析上传文件（FileParser）
2. 检索法规（retrieve_regulations）
3. 构建事实（从请求直接拼接）
4. 构造上下文块（企业信息+法规检索结果+数据字段分类）
5. LLM生成7章PIPIA报告
6. 渲染输出（MD+DOCX+ZIP）
```

**输出**：MD + DOCX + ZIP

**关键特点**：
- 最简模块，未接入WorkflowPipeline
- 没有fact_builder/issue_builder/evidence_builder
- 没有trace留痕
- 没有中间产物JSON输出

---

### 模块11：DPIA（dpia）

**一句话定位**：生成GDPR要求的数据保护影响评估报告。

**核心入口**：`DPIAService.generate_report(payload) -> DPIAResult`

**业务流程**（9-Agent架构 + WorkflowPipeline）：

```
前置Agent阶段（流水线前）：
    DPIA Need Agent：判断是否需要DPIA
    Processing Activity Agent：描述处理活动
    Necessity & Proportionality Agent：必要性比例性分析
    Risk Assessment Agent：风险识别与评估
    Mitigation Mapping Agent：风险缓解措施映射
    DPO Consultation Agent：DPO咨询建议

流水线阶段：
    事实提取 → 法规检索(GDPR) → 附件解析 → 问题构建 → 证据构建
    → 上下文包 → AI生成7章

后置Agent阶段：
    External Draft Agent：对外报告草稿
    Internal Review Agent：内部审查
    Consistency/Repair Agent：一致性修复

渲染输出：
    MD报告 + 问题清单JSON/XLSX + 证据链JSON/XLSX + 风险矩阵JSON/XLSX
    + 缓解计划JSON/XLSX + DPIA需要评估JSON + 法律依据/写作策略/生成基础包JSON
    + 引用映射JSON + trace manifest + 一致性报告JSON + ZIP
```

**输出**：MD + 3个XLSX + 9个JSON + ZIP

**关键特点**：
- Agent数量最多（9个）
- 中间产物JSON仅次于assessment
- 但没有DOCX和PDF输出

---

### 模块12：TIA（tia）

**一句话定位**：生成GDPR要求的传输影响评估报告。

**核心入口**：`TIAService.generate_report(payload) -> TIAResult`

**业务流程**（5个确定性组件 + 3个Agent）：

```
确定性组件（流水线前）：
    TIACountryRiskAssessor：评估接收国数据保护水平
    TIADataSensitivity：评估数据敏感度
    TIAMeasureSufficiency：判断合同和技术措施是否充分
    TIARouteDecider：判断传输路径可行性
    TIAAttachmentEvidence：从附件中提取证据

Agent（条件触发）：
    Attachment Review Agent：审查附件证据
    DPO Review Agent：DPO视角审查
    RAG Planning Agent：规划法规检索

流水线：
    事实提取 → 法规检索(GDPR) → 附件解析 → 问题构建 → 证据构建
    → 上下文包 → AI生成6章 → 渲染输出（MD+DOCX+ZIP）
```

**输出**：MD + DOCX + ZIP

**关键特点**：
- 中间产物相对较少（无独立JSON/XLSX）
- 基于 export_profile + transfer_tool 命名输出文件（而非 company_name）

---

## 汇总对比表

| 模块 | 流程模式 | Agent数量 | 接入WorkflowPipeline | Fact/Issue/Evidence | 中间产物 | 输出文件 |
|------|---------|----------|---------------------|-------------------|---------|---------|
| diagnosis | 5层递进 | 4 | ❌ | ❌ | ❌ | HTML + PDF |
| us_14117 | 规则引擎+Pipeline | 5 | ✅ | ✅ | 3 JSON | MD+DOCX+PDF+XLSX+ZIP |
| review | 8阶段 | 0(内嵌LLM) | ❌(自有阶段) | ❌(自有类型) | ❌ | DOCX+批注DOCX |
| scc | 13阶段+Agent | 9 | ❌(自有顺序) | ✅ | ❌ | MD+DOCX+批注DOCX |
| eu_scc | 前置+流水线+后置 | 6 | ✅ | ✅ | 4 JSON | MD+占位DOCX+批注DOCX |
| bcr | 6阶段文档驱动 | 10 | ❌(自有阶段) | ❌(自有类型) | ❌ | MD+DOCX+ZIP |
| cpra | 11步递进 | 4 | ❌(自有顺序) | ✅(合并器) | 1 JSON | MD+DOCX+PDF+XLSX+ZIP |
| assessment | 14步Pipeline | 8(内置) | ✅ | ✅ | 10 JSON+3 XLSX | 内部MD+DOCX+官方MD+DOCX+ZIP |
| cn_flow | Pipeline | 0 | ✅ | ✅ | 3 JSON | MD+DOCX+PDF+XLSX+ZIP |
| pipia | 最简架构 | 0 | ❌ | ❌ | ❌ | MD+DOCX+ZIP |
| dpia | 9-Agent+Pipeline | 9 | ✅ | ✅ | 3 XLSX+9 JSON | MD+ZIP |
| tia | 5组件+3Agent+Pipeline | 3 | ❌(自组装) | ❌ | ❌ | MD+DOCX+ZIP |

**流程模式说明**：
- "Pipeline" = 调用 `WorkflowPipeline().run()` 走标准14步流水线
- "自有阶段" = 模块有自己的执行顺序，不经过WorkflowPipeline
- "5层递进" = diagnosis独有的规范化→Agent→决策树→AI推测→AI解释
