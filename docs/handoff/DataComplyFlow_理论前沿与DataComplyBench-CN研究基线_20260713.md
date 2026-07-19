# DataComplyFlow 理论前沿与 DataComplyBench-CN 研究基线

> 文档状态：`retained research baseline`。已纳入仓库治理留存；不代表当前代码已实现能力，也不替代法律 Gold 或当前事实基线。

**面向中国企业数据出境合规路径诊断的 Deep Research 调研报告**

- 版本 V1.0｜2026 年 7 月 13 日
- 事实依据：最新 Codex 项目事实基线；研究口径：产品—理论双驱动、评价居中

---

## 执行摘要

本报告以最新 Codex 源码事实基线为唯一产品事实依据，对 2024—2026 年 Legal RAG、监管合规 Benchmark、Claim/Citation、版本感知推理、过程评价与人工复核等方向进行了重新检索和分级分析。当前 DataComplyFlow 的真实优势不是“Agent 数量多”，而是已经具备规则判断、Fact/Issue/Evidence/GenerationContextPack、分层法规检索、引用注册、报告生成和 Trace 等可继续评价与演进的系统骨架；真实短板则是模块不统一、Claim/Rule 统一层缺失、规则与法规版本约束不足、引用忠实性尚未形成平台级验证、评测资产尚未汇聚为统一 Benchmark。

本轮检索**未发现一个可以直接用于中国企业数据出境合规路径诊断的公开 Benchmark**。现有研究分别解决了合规样本构造、最小法律证据检索、端到端错误分解、缺失事实识别、Claim 级验证、多级法规引用闭包、过程评价和人工复核等局部问题。因此，DataComplyBench-CN 不应照搬某一个数据集，而应组合这些经过验证的方法，并以真实业务任务和当前代码结构为约束。

本报告提出的核心研究对象是：

> **在事实不完整、规则具有条件与例外、法规存在版本约束的情况下，系统能否形成证据充分、可追问、可转人工、可复核的中国企业数据出境合规路径诊断。**

第一版 Smoke Benchmark 建议只覆盖五类任务：事实结构化、节点级规则适用、最终路径与选择性行为、最小/充分法律证据检索、缺失事实与人工分流。Claim 级长报告审计和人工复核效率作为第二阶段任务。先跑 Rule-only、Direct LLM、当前 Basic RAG、Structured RAG、当前完整 DataComplyFlow 五个基线，再根据稳定错误选择论文方法进行最小迁移。

---

## 一、研究目的与边界

### 1.1 当前研究目的

本轮理论调研不是为产品“寻找先进名词”，也不是提前证明某个论文创新成立，而是为以下三件事提供可靠理论依据：

1. 确定 DataComplyBench-CN 应测量什么，而不是只测最终报告观感；
2. 确定当前 DataComplyFlow 的错误如何分解到事实、规则、检索、证据、生成与分流阶段；
3. 确定哪些论文方法值得进入最小验证，哪些应暂缓。

### 1.2 产品事实约束

依据最新 Codex 事实基线，当前系统可作为研究起点的真实资产包括：

- 中国数据出境路径诊断规则与三态输入；
- 部分模块真实贯穿的 FactItem、IssueItem、EvidenceItem、GenerationContextPack；
- 法规条款级/结构化 Chunk、哈希向量与词法混合检索、RRF 和启发式重排；
- CitationRegistry、引用 Marker、Citation Map 和运行 Trace；
- Assessment、EO 14117 等相对完整的公共流水线；
- qa、知识库 evaluation、fixtures、历史 traces 和报告产物。

当前不能作为既成能力使用的内容包括：

- 统一 ClaimItem、RuleItem；
- 全平台一致的 Claim-level Faithfulness Verifier；
- 强制规则版本和法规时效执行；
- 统一硬阻断和人工审批状态机；
- 全模块统一公共 Workflow；
- 已经成熟的 DataComplyBench-CN。

### 1.3 本报告不做什么

- 不直接给出中国数据出境法律 Gold；
- 不替代法律专业队员对规则、路径和人工分流条件的确认；
- 不要求 Codex 立即重构全部模块；
- 不把预印本结果当作已被充分验证的工程事实；
- 不把单次产品失败直接包装成理论缺口。

---

## 二、Deep Research 方法与证据分级

### 2.1 检索范围

本轮优先检索以下来源：

- ACL Anthology、NeurIPS Proceedings、ACM Digital Library；
- arXiv 原始论文页面及作者开放代码；
- 论文官方 GitHub；
- 与监管合规、Legal RAG、法律 Agent、Claim/Citation、时间法律推理直接相关的 2024—2026 工作。

### 2.2 证据等级

| 等级 | 含义 | 在本项目中的用法 |
|---|---|---|
| A | 正式会议/期刊论文，来源和方法清晰 | 可作为评测方法和工程设计的重要依据 |
| B | 高相关预印本，开放数据或代码，方法可复核 | 可进入候选迁移卡和最小实验 |
| C | 观点性、商业性或缺少公开实现的工作 | 仅作为线索，不决定产品改造 |

### 2.3 Benchmark 构念效度约束

NeurIPS 2025 对 445 篇 LLM Benchmark 论文的系统审查指出，Benchmark 需要明确“要测量的现象”、任务是否代表该现象、指标是否真正对应目标以及结论是否超出证据。[R1] 对 DataComplyBench-CN 来说，这意味着不能把“路径准确率高”直接等同于“产品法律上可靠”，也不能把“报告有引用”直接等同于“证据充分”。

因此，本项目必须先定义核心现象：

> **证据约束的合规路径诊断能力，而不是泛法律知识、文本生成质量或 Agent 复杂度。**

---

## 三、与 DataComplyFlow 最相关的理论前沿

## 3.1 合规 Benchmark 的构造：AIReg-Bench

AIReg-Bench 采用“LLM 生成可信虚构技术文档片段—法律专家复核与标注”的两阶段流程，形成 120 个 EU AI Act 合规样本，并开放数据与评测代码。[R2]

### 可迁移价值

- 支持“小规模合成场景 + 法律专家 Gold”的启动方式；
- 支持围绕具体法规条款生成边界案例；
- 提醒合成数据必须标注来源，不能与真实案例混淆；
- Benchmark 是特定法律版本的时间快照。

### 不可直接迁移

- 单轮合规分类与 DataComplyFlow 的多节点路径诊断不同；
- EU AI Act 标签不能迁移到中国数据出境；
- 120 个样本的规模和任务设计不能直接证明中国场景构念有效。

### 对本项目的结论

DataComplyBench-CN 可以采用“规则组合生成 + 专家改写 + 双人法律复核”的混合构造方式，但第一批 Gold 必须保留分歧和裁决记录。

---

## 3.2 最小法律证据检索：LegalBench-RAG

LegalBench-RAG 包含 6,858 个法律专家标注的检索问答对和超过 7,900 万字符语料，强调检索“最小且高度相关”的证据片段，而不是大段 Chunk 或文档 ID。[R3]

### 可迁移价值

DataComplyFlow 当前具有条款/结构化 Chunk 和混合检索骨架，适合直接增加：

- Clause Recall@K；
- Minimal Evidence Precision；
- 证据跨度长度；
- 条、款、项定位准确率；
- 错误法域和错误版本率。

### 重要边界

LegalBench-RAG 主要测检索，不测路径节点是否适用，也不处理多条规则共同构成结论的“证据集合充分性”。

### 对本项目的结论

首版 T4 应同时测“最小证据”和“充分证据集合”，二者不能合并成一个 Recall@K。

---

## 3.3 端到端错误分解：Legal RAG Bench 与 RAGChecker

Legal RAG Bench 采用全因子设计，把不同检索器与不同生成模型交叉组合，并通过分层错误分类区分检索失败、推理失败和生成性错误。[R4] RAGChecker 则提供面向检索和生成模块的细粒度诊断框架。[R5]

### 可迁移价值

DataComplyFlow 应避免只比较“旧版本 vs 新版本最终报告得分”，而应至少记录：

1. Fact 是否正确；
2. Rule Node 是否正确；
3. Retriever 是否找到正确证据；
4. Evidence 是否覆盖全部条件与例外；
5. Generator 是否超出 ContextPack；
6. 是否正确追问或转人工。

### 对本项目的结论

Benchmark Harness 必须能够替换 Retriever、LLM 和工作流 Adapter，并保持输入、知识快照和输出 Schema 一致。否则不能归因论文方法的贡献。

---

## 3.4 缺失事实与澄清：ContextLens

ContextLens 面向隐私与 AI 安全合规场景，重点识别已知、未知、模糊和缺失的上下文因素。[R10] 这与当前中国 diagnosis 中 unknown 会被启发式或 Agent 改写的真实问题高度相关。

### 可迁移价值

- 把 unknown 保留为独立事实状态；
- 区分“模型推断事实”和“用户确认事实”；
- 评价 Missing Fact Recall、Ambiguity Detection、Clarification Quality；
- 用问题级输出替代直接将 unknown 填成 yes/no。

### 迁移风险

- 论文任务和中国数据出境路径不同；
- 多模型对缺失因素的识别可能不一致；
- 直接增加多个 Agent 可能提高成本但不提高法律正确性。

### 最小验证

只在 12—20 个 Smoke Case 上比较：

- 当前 normalization/Agent 回填；
- 保留 unknown + 生成澄清问题；
- 规则保守分流。

核心观察是 False Exemption、False Safe Path 和有效澄清率，而不是文本质量。

---

## 3.5 Claim、Citation 与 Evidence：三层概念必须分开

### 引用正确性不等于引用忠实性

ICTIR 2025 的研究指出，模型可能先依据内部知识生成答案，再事后附上看似支持的引用；引用内容正确并不代表生成过程真实依赖该证据。[R7]

### Claim 级评价

ClaimRAG-LAW 提供 317 个专家验证 QA 和 968 个手工验证 Claim，显示法律 Claim 抽取和矛盾检测本身也会产生误差。[R8]

### 引用闭包与逐规则归因

RegOps-Bench/RefWalk 将监管合规视为跨层级规则引用的证据集合闭包问题，要求每个规则结论映射到来源。[R9]

### 对 DataComplyFlow 的直接结论

当前 CitationRegistry 能证明“引用被注册和展示”，但不能证明：

- 最终文本 Claim 被该证据蕴含；
- 适用条件已满足；
- 例外已排除；
- 引用是当前有效版本；
- 证据集合已覆盖所有必要规则。

因此，短期不应宣称“Claim-level Legal Audit 已实现”。Benchmark 可以先在结构化结论层测：

- Evidence Set Completeness；
- Condition Coverage；
- Exception Coverage；
- Rule-to-Evidence Attribution；
- Unsupported Conclusion Rate。

最终报告 Claim 分解留到第二阶段。

---

## 3.6 结构化规则图：GraphCompliance

GraphCompliance 把法规编码为 Policy Graph，把真实场景编码为 Subject-Action-Object 与实体关系构成的 Context Graph，并进行对齐。[R11]

### 适配性

它与 DataComplyFlow 的事实结构化、规则节点和证据链方向高度一致，可能为长期 Rule-Guided Reasoning 提供方法参考。

### 当前不应直接采用的原因

- 当前项目没有统一 RuleItem；
- 法规版本、优先级和冲突处理尚未统一；
- 全量法规图构造成本高，且需要法律专家校验；
- 当前尚未通过 Baseline 证明主要错误来自规则结构，而非 Bug、检索或缺失事实。

### 正确使用方式

把 GraphCompliance 列为 P2 候选。只有当节点级错误分析稳定显示“文本 RAG 找到了法条但无法处理条件、例外或交叉引用”时，才开展小规模规则图实验；先选 5—10 个路径节点，不做全平台重构。

---

## 3.7 Agent 过程评价：LegalAgentBench

LegalAgentBench 是 ACL 2025 正式论文，包含 17 个法律语料库、37 个工具和 300 个任务，并通过中间关键词计算 Progress Rate。[R6]

### 可迁移价值

DataComplyFlow 已有结构化 Trace，因此无需复制关键词 Progress Rate，而可以定义更可靠的步骤完成率：

```text
facts_built
→ rules_checked
→ retrieval_completed
→ evidence_built
→ path_decided
→ consistency_checked
→ output_rendered
```

### 不能直接迁移的部分

- LegalAgentBench 测通用中文法律 Agent，不测数据合规路径；
- 工具数量和 Agent 数量不是产品价值；
- 当前 DataComplyFlow 多数 Agent 是顺序编排的单次 LLM 专家步骤，不应包装成自治 Agent。

---

## 3.8 版本感知法律推理

2026 年的时间法律 Benchmark 区分两类错误：使用已被修订的旧规则，以及错误地用新规则回答历史时点问题。[R14] 相关工作进一步强调版本化法条索引和时间约束检索。[R15]

### 与项目事实的对应

DataComplyFlow 知识库已有 status、effective_date 等元数据，但当前没有统一强制“适用时点—法规版本”过滤；Trace Manifest 也缺少规则和知识版本。

### 第一阶段最小建设

每个 Benchmark Case 增加：

- `case_at`；
- `legal_snapshot_id`；
- `rule_version`；
- `knowledge_snapshot`；
- `expected_effective_sources`。

首版只要求“当前时点正确版本”，历史时点推理可以后置。

---

## 3.9 LLM Judge 与法律专家评价

LeMAJ 强调法律评价需要贴近律师的分析过程，通用 LLM-as-a-Judge 在无可靠参考时并不稳定。[R13] 因此，LLM Judge 在 DataComplyBench-CN 中只能承担：

- 格式和表达初筛；
- Claim/Evidence 候选分类；
- 人工复核前的排序；
- 低风险、已校准维度的自动扩展。

不能独立承担：

- 最终路径真值；
- 法条适用性真值；
- 是否必须转人工；
- Gold 的争议裁决。

---

## 3.10 人工复核导向评价

2026 年关于违约判决审查的受控研究显示，带引用的 AI 辅助可以在逐项法律要求审查中改善准确率并缩短时间。[R16] 虽然任务与数据出境不同，但其评价设计对产品十分重要：

- 不只测系统独立得分；
- 测专家是否更快发现问题；
- 测专家接受、修改和驳回哪些建议；
- 测高风险要求的漏审是否下降。

这类指标应在比赛专业验证阶段进入小规模用户研究，而不应由模型自动估计。

---

## 四、前沿工作迁移矩阵

| 方向/工作 | 解决的问题 | 与当前代码的对应 | 迁移成本 | 当前优先级 | 结论 |
|---|---|---|---:|---|---|
| 构念效度 [R1] | Benchmark 是否真正在测目标能力 | 当前缺统一产品 Benchmark | 低 | P0 | 立即采用为设计约束 |
| AIReg-Bench [R2] | 合成合规案例 + 专家 Gold | 已有 fixtures、规则和历史 Trace | 中 | P0 | 采用构造流程，不照搬标签 |
| LegalBench-RAG [R3] | 最小法律证据检索 | 已有条款 Chunk 和混合检索 | 低—中 | P0 | 立即进入 T4 指标 |
| Legal RAG Bench [R4] | 检索/模型贡献归因 | 当前缺统一 Adapter 和 Harness | 中 | P0 | 采用全因子与错误分解 |
| RAGChecker [R5] | RAG 过程诊断 | Fact/Issue/Evidence/Trace 可利用 | 中 | P0 | 迁移指标思想 |
| ContextLens [R10] | 缺失、模糊事实识别 | diagnosis 的 unknown 处理有风险 | 中 | P0 | 第一轮最小实验候选 |
| LegalAgentBench [R6] | 过程级 Agent 评价 | 已有 Trace 和阶段事件 | 低 | P1 | 改造为结构化 Step Rate |
| ClaimRAG-LAW [R8] | Claim 抽取和验证 | 当前无统一 ClaimItem | 中—高 | P1 | 基线后再做 |
| Citation Faithfulness [R7] | 事后贴引用与真实依赖 | 有 CitationRegistry，无因果/干预验证 | 高 | P1 | 先测支持性，忠实性后置 |
| RefWalk [R9] | 多层级规则引用闭包 | 当前规则与引用未统一 | 高 | P1 | 小规模证据闭包实验 |
| 时间法律推理 [R14][R15] | 法规版本适用 | 有元数据，无统一执行门禁 | 中 | P1 | 先加入快照字段 |
| GraphCompliance [R11] | 法规结构与场景结构对齐 | 无统一 RuleItem/Graph | 高 | P2 | 暂缓全量迁移 |
| LLM Judge/LeMAJ [R13] | 低成本自动评价 | 可作为辅助 Judge | 中 | P1 | 必须专家校准 |
| 人工复核研究 [R16] | 实际工作效率与质量 | 比赛要求专业验证 | 中 | P1 | 设计小规模专业测试 |

---

## 五、DataComplyBench-CN 的推荐任务定义

### 5.1 核心现象

> **Evidence-Constrained Compliance Path Diagnosis under Incomplete Facts and Versioned Rules**

中文定义：

> 在企业事实可能缺失、模糊或冲突，法律规则具有条件、例外与版本约束的情况下，系统是否能够形成正确的合规路径判断、充分的法律证据、必要的澄清问题和适当的人工分流。

### 5.2 第一阶段任务层

#### T0：Case 与法律快照治理（非模型任务）

确保每个案例可重放：

- 案例来源和脱敏状态；
- 案例适用日期；
- 规则版本；
- 法规知识快照；
- Gold 标注人和裁决记录。

#### T1：事实结构化

输出主体、数据类型、PI/SPI/重要数据、数量、目的、接收方、传输方式、豁免事实，以及缺失/冲突字段。

#### T2：节点级规则适用

逐节点输出 `applicable / not_applicable / unknown / conflict`，并关联必要事实。

#### T3：最终路径与选择性行为

输出路径，同时决定：

- 可以形成结论；
- 必须追问；
- 暂时保留意见；
- 必须人工复核。

#### T4：法律证据检索

同时评价：

- 最小证据片段；
- 完整必要证据集合；
- 法域、版本、效力层级；
- 条件与例外覆盖。

#### T5：证据充分性

判断当前事实与法律证据是否足以支持路径结论；不足时说明缺口和下一步动作。

### 5.3 第二阶段任务

- T6：最终报告 Claim—Evidence Audit；
- T7：人工复核效率与修改量；
- T8：下游安全自评估/合同审查扩展。

---

## 六、Gold Case Schema 建议

```json
{
  "case_id": "CN-XB-0001",
  "case_at": "2026-07-01",
  "source_type": "expert_authored | rule_composed | deidentified_real",
  "scenario_text": "...",
  "attachments": [],
  "fact_gold": {},
  "missing_facts": [],
  "conflicting_facts": [],
  "node_labels": [
    {
      "node_id": "...",
      "label": "applicable | not_applicable | unknown | conflict",
      "required_facts": [],
      "rationale": "..."
    }
  ],
  "path_gold": ["security_assessment"],
  "acceptable_alternatives": [],
  "required_clarifications": [],
  "escalation_required": false,
  "rule_snapshot_id": "...",
  "evidence_primary": [],
  "evidence_alternatives": [],
  "minimum_evidence_set": [],
  "prohibited_claims": [],
  "annotators": [],
  "disagreement_log": [],
  "adjudication": {}
}
```

### 6.1 为什么需要替代性证据集合

CanLegalRAGBench 指出，自动评价可能把另一份同样相关的法律材料错误判为失败。[R18] 因此 T4 不应只有一个唯一 Passage ID，而应允许：

- Primary evidence；
- Equivalent/alternative evidence；
- Required evidence set；
- Background-only evidence。

### 6.2 为什么需要争议日志

法律 Gold 本身可能遗漏或存在分歧。法定调查 Benchmark 的后续复核发现，部分模型“错误”实际是专家 Gold 的遗漏。[R17] 因此，Gold 不是不可修改的神谕，应保留版本和裁决过程。

---

## 七、指标体系

## 7.1 T1 事实指标

- 字段级 Macro-F1；
- Missing Fact Recall；
- Conflict Detection F1；
- Provenance Accuracy；
- Unsupported Fact Introduction Rate。

## 7.2 T2 节点指标

- Node Macro-F1；
- Unknown Preservation Rate；
- High-risk False Negative Rate；
- False Exemption Rate；
- Rule–Fact Alignment Accuracy。

高风险错误应单独计权，不能只看总体 Accuracy。

## 7.3 T3 路径与分流指标

- Exact Path Accuracy；
- Set-valued Path Accuracy；
- Clarification Precision / Recall；
- Escalation Recall；
- Selective Coverage–Risk Curve；
- Overconfident Decision Rate。

## 7.4 T4 检索指标

- Clause Recall@K；
- Evidence Span Precision；
- Minimality；
- Evidence-set Completeness；
- Condition Coverage；
- Exception Coverage；
- Current-version Accuracy；
- Wrong-jurisdiction Rate；
- Authority-level Accuracy。

## 7.5 T5 证据充分性指标

- Sufficiency Classification Accuracy；
- Missing Premise Recall；
- Unsupported Conclusion Rate；
- Correct Action under Insufficient Evidence；
- Human Agreement。

## 7.6 产品与工程指标

- P50/P95 时延；
- Token 用量；
- 单案例成本；
- 成功率与超时率；
- 结果可重放率；
- Trace 完整率；
- 模型与知识快照记录率。

## 7.7 第二阶段 Claim 与人工指标

- Claim Support Rate；
- Unsupported Claim Rate；
- Citation Correctness；
- Citation Support Accuracy；
- 专家接受率；
- 修改条目数；
- 复核时间；
- 高风险问题漏审率。

“Citation Faithfulness”若要严格测量，需要证据移除、证据替换或内部归因干预，不能仅依靠语义蕴含分数。

---

## 八、Baseline 与实验设计

### 8.1 五个首轮 Baseline

| Baseline | 目的 |
|---|---|
| Rule-only | 验证确定性规则在完整结构化事实下的上限和边界 |
| Direct LLM | 测量无外部法规和无规则约束的模型能力与风险 |
| Basic RAG | 复用当前哈希向量 + 词法 + RRF + 启发式重排 |
| Structured RAG | 使用 Fact/Issue/Evidence/ContextPack，但不加入额外高级方法 |
| Current DataComplyFlow | 保留当前完整工作流作为固定产品基线 |

增强版本只能一次加入一个主要变量，例如“保留 unknown 并生成澄清问题”或“神经 Embedding + Reranker”。

### 8.2 输入公平性

所有 Baseline 必须固定：

- 原始案例；
- 法律知识快照；
- 适用日期；
- 模型版本和温度；
- 最大上下文和输出 Schema；
- 重试策略；
- 外部 API 是否启用。

Rule-only 可使用 Gold Facts 和 Predicted Facts 两种模式，分别区分规则能力与事实抽取误差。

### 8.3 分层错误分类

```text
E0 Infrastructure/Bug
E1 Fact Extraction
E2 Missing/Conflict Detection
E3 Rule Applicability
E4 Retrieval
E5 Evidence Sufficiency
E6 Generation/Overclaim
E7 Citation/Attribution
E8 Clarification/Escalation
E9 Rendering/Delivery
```

E0 必须先作为工程问题修复，不进入理论贡献统计。

### 8.4 数据规模

- Smoke：12—20 例，只验证 Harness、Schema 和标注可行性；
- Gold v0.1：30—50 例，可服务比赛和内部回归；
- 研究版：建议逐步达到 100—150 个经专家复核案例，并保留私有测试集。

小数据并不天然无效；关键是任务覆盖、Gold 质量、边界设计和结论克制。[R1]

---

## 九、当前最值得探索的三项理论假设

### H1：保留 unknown 并进行澄清，能否降低危险路径误判

**现实对应**：当前 diagnosis 可通过启发式或 Agent 把 unknown 改为 yes/no。

**最小实验**：

- A：当前处理；
- B：unknown 保留 + 规则保守分流；
- C：unknown 保留 + 澄清问题。

**指标**：False Exemption、High-risk FN、Clarification Recall、Coverage。

### H2：最小证据检索与证据集合充分性应分开优化

**现实对应**：当前检索以条款 Chunk 为主，但尚未证明条件与例外集合完整。

**最小实验**：

- 当前混合检索；
- 增加条款结构/元数据过滤；
- 增加多段证据集合扩展。

**指标**：Clause Recall@K、Minimality、Evidence-set Completeness、Condition/Exception Coverage。

### H3：结构化中间表示是否真正提升路径稳定性和可诊断性

**现实对应**：Fact/Issue/Evidence/ContextPack 已在部分模块存在。

**最小实验**：

- Direct LLM；
- Basic RAG；
- Structured RAG；
- Current Workflow。

**指标**：Path Accuracy、错误可归因率、Unsupported Conclusion、Trace 完整度、成本。

这三项假设均能利用现有产品资产，不要求先构建统一 Claim 平台或全量规则图。

---

## 十、暂不建议进入产品的方向

### 10.1 全量 Policy Graph / Context Graph 重构

高成本，且尚未证明当前主要瓶颈来自规则结构。

### 10.2 自治多 Agent 与复杂反思循环

当前系统已有大量顺序 LLM 专家步骤，但 Agent 数量不是技术价值。应先证明新增步骤能降低哪类稳定错误。

### 10.3 端到端模型训练或强化学习

比赛阶段数据量、评测稳定性和工程成本均不足，优先做工作流、数据与评价。

### 10.4 全平台 ClaimItem/RuleItem 统一

长期有价值，但应在 Assessment 或 Diagnosis 的小范围研究分支先验证 Schema 和指标，再决定是否平台化。

### 10.5 单一 LLM Judge 自动给法律分数

只能作为辅助，不可替代 Gold 与专家。

---

## 十一、与 Codex 和法律组的汇合方式

### 11.1 等待 Codex 返回的关键内容

- 当前评测资产清单；
- 可复用 Schema；
- Baseline Adapter 可行性；
- Trace 和版本字段缺口；
- 第一轮必须修复的 Bug；
- Smoke Harness 最小实现方案。

### 11.2 等待法律组返回的关键内容

- 目标用户与核心业务任务；
- 节点级法律判断；
- 规则版本和证据；
- 信息不足时应追问/转人工的条件；
- 10—15 个种子案例；
- Gold 分歧处理方式。

### 11.3 三方汇合后冻结的文档

> 《DataComplyBench-CN v0.1 设计规范》

该规范应由法律任务、代码可行性和本报告的理论方法共同决定，任何一方不能单独完成。

---

## 十二、下一步研究路线

### 阶段 A：评测立项

- 完成法律任务冻结；
- 完成 Codex 评测资产审计；
- 冻结 Benchmark 构念、任务和 Gold Schema。

### 阶段 B：Smoke Harness

- 实现 Case Schema、Adapter、Runner、Metric、Manifest；
- 运行五个 Baseline；
- 形成错误分类和第一版报告。

### 阶段 C：论文迁移卡

仅针对 Smoke 中稳定出现的错误深读对应论文，形成“问题—方法—代码—数据—指标—成本—结论”。

### 阶段 D：最小实验

一次只改一个主要变量，保留当前产品版本作为 Baseline。

### 阶段 E：比赛证据与论文判断

- 比赛：形成核心技术测试报告、专业验证记录、时延/Token/成本和典型案例；
- 论文：只有跨案例稳定、现有方法仍有局限且可形式化时，才抽象研究贡献。

---

## 十三、结论

本轮重新检索后的最重要结论不是“应该引入某一篇论文”，而是：

1. DataComplyFlow 已经拥有构建过程级 Benchmark 的真实结构和运行资产；
2. 目前最缺的不是更多 Agent，而是明确构念、法律 Gold、统一 Harness 和错误归因；
3. DataComplyBench-CN 应把事实不完整、规则条件/例外、法律证据集合、选择性回答和版本快照作为核心；
4. 现有论文可以分别提供数据构造、检索指标、错误分解、Claim/Citation、引用闭包、时间约束和人工评价方法，但没有任何单一工作可以直接覆盖本项目；
5. 第一轮理论—实践结合应从 Baseline 和错误分布开始，而不是先重构代码；
6. 当前最优先的三个最小研究假设是 unknown/澄清、最小证据与充分证据分离、结构化 IR 的真实增益。

因此，当前理论工作的正确定位是：

> **为 DataComplyBench-CN 和首轮最小实验建立可靠方法基线，并让评价结果决定下一轮产品修改，而不是为既有产品寻找包装性论文。**

---

## 参考文献与开放资源


- **[R1] Measuring What Matters: Construct Validity in Large Language Model Benchmarks**. NeurIPS 2025 Datasets and Benchmarks Track. 系统审查 445 篇 Benchmark 论文并提出构念效度检查清单。 资源：https://papers.nips.cc/paper_files/paper/2025/file/1967e0fc3aa6cbbace562f5cb8e3954e-Paper-Datasets_and_Benchmarks_Track.pdf

- **[R2] AIReg-Bench: Benchmarking Language Models That Assess AI Regulation Compliance**. arXiv 2025，开放数据与代码. 以 120 个可信合成技术文档片段为样本，由法律专家复核并标注 EU AI Act 合规标签。 资源：https://arxiv.org/abs/2510.01474

- **[R3] LegalBench-RAG: A Benchmark for Retrieval-Augmented Generation in the Legal Domain**. arXiv 2024，开放数据. 6,858 个法律专家标注的检索问答对，强调最小且高度相关的法律证据片段。 资源：https://arxiv.org/abs/2408.10343

- **[R4] Legal RAG Bench: an end-to-end benchmark for legal RAG**. arXiv 2026，开放代码与数据. 4,876 个 passages、100 个专家复杂问题；全因子设计和分层错误分解。 资源：https://arxiv.org/abs/2603.01710

- **[R5] RAGChecker: A Fine-grained Framework for Diagnosing Retrieval-Augmented Generation**. NeurIPS 2024 Datasets and Benchmarks Track. 分别诊断检索与生成模块，适合构建过程级评测。 资源：https://arxiv.org/abs/2408.08067

- **[R6] LegalAgentBench: Evaluating LLM Agents in Legal Domain**. ACL 2025. 17 个法律语料库、37 个工具、300 个任务；同时评价最终成功率与中间进度。 资源：https://aclanthology.org/2025.acl-long.116/

- **[R7] Correctness is not Faithfulness in Retrieval Augmented Generation Attributions**. ICTIR 2025. 区分引用正确性与引用忠实性，揭示事后贴引用风险。 资源：https://dl.acm.org/doi/10.1145/3731120.3744592

- **[R8] Fine-grained Claim-level RAG Benchmark for Law (ClaimRAG-LAW)**. arXiv 2026. 317 个专家验证 QA、968 个手工验证 Claim，评价 Claim 抽取与验证。 资源：https://arxiv.org/abs/2605.21071

- **[R9] Citation-Closure Retrieval and Per-Rule Attribution for Real-World Regulatory Compliance Question Answering**. arXiv 2026，开放代码. 提出 RegOps-Bench 与 RefWalk，强调多层级规则引用闭包和逐规则归因。 资源：https://arxiv.org/abs/2605.29742

- **[R10] ContextLens: Modeling Imperfect Privacy and Safety Contexts for Compliance Evaluation**. arXiv 2026. 识别隐私与安全场景中的缺失、模糊和未知上下文因素。 资源：https://arxiv.org/abs/2604.12308

- **[R11] GraphCompliance: Aligning Policy and Context Graphs for LLM-Based Regulatory Compliance**. arXiv 2025. 将法规表示为 Policy Graph、场景表示为 Context Graph，并进行结构化对齐。 资源：https://arxiv.org/abs/2510.26309

- **[R12] Grounded Answers from Multi-Passage Regulations (ObliQA-MP)**. NLLP 2025. 多段监管文本检索与回答，采用 Recall@10、MAP、nDCG 等检索指标并强调多段证据。 资源：https://aclanthology.org/2025.nllp-1.10/

- **[R13] LeMAJ (Legal LLM-as-a-Judge): Bridging Legal Reasoning and LLM Evaluation**. NLLP 2025. 强调法律评价需要贴近律师的评审过程，通用 LLM Judge 不能直接充当法律真值。 资源：https://aclanthology.org/2025.nllp-1.23/

- **[R14] Diagnosing and Mitigating Temporal Failure Modes in LLM Legal Reasoning**. arXiv 2026. 构建 312 个专家验证的时间法律问答，区分过时与错误追新两类时效失败。 资源：https://arxiv.org/abs/2605.23497

- **[R15] Can LLMs Time Travel? Enhancing Temporal Consistency in Legal Research**. arXiv 2026. 强调版本化法条索引和时间约束检索。 资源：https://arxiv.org/abs/2605.25920

- **[R16] AI Assistance for Human Review of Default Judgments**. arXiv 2026. 受控研究中，AI 辅助使用者在逐项法律要求审查上更准确且更快，启发人工复核导向评价。 资源：https://arxiv.org/abs/2607.01256

- **[R17] Benchmarking Legal RAG: The Promise and Limits of AI Statutory Surveys**. arXiv 2026. 通过法律条文调查任务揭示检索、规则解释与 Gold 本身遗漏问题。 资源：https://arxiv.org/abs/2603.03300

- **[R18] CanLegalRAGBench: Evaluating Retrieval-Augmented Generation on Canadian Case Law**. arXiv 2026. 专家标注现实查询；指出自动指标可能错误惩罚替代性有效证据。 资源：https://arxiv.org/abs/2605.30497

- **[R19] Regulatory Information Retrieval and Answer Generation / ObliQA**. RegNLP 2025. 27,869 个监管问答及对应 passages，是监管信息检索的重要大规模资源。 资源：https://aclanthology.org/2025.regnlp-1.1/

- **[R20] Legal-DC: Benchmarking Retrieval-Augmented Generation for Legal Documents**. arXiv 2026. 中文法律 RAG 数据，2,475 个条款级引用问答；适合观察中文条款切分与联合评测。 资源：https://arxiv.org/abs/2603.11772
