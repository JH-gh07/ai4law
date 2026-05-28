下面给你一套**设计构想版**，先不落到具体代码，而是把系统应该长什么样、各层职责是什么、为什么这样设计、哪些地方不用 AI、哪些地方用 Markdown 记忆、哪些地方用数据库和规则引擎讲清楚。

核心定位先定死：

> **DataComply Flow 不是“合规问答 + 文档生成器”，而是一个带分层记忆、规则约束、RAG 证据、Agent 编排、质量评分和可追溯交付的合规工作流系统。**

你当前流程已经明确：系统不是用户输入后让 LLM 直接写报告，而是先形成企业事实、路径诊断结果、风险等级、附件摘要、法规依据、问题清单、证据链、模板章节，再交给 LLM 按约束生成报告，并在生成后做一致性检查和模板渲染。

---

# 1. 总体设计：一个“合规项目工作区”

我建议系统抽象成一个核心概念：

```text
Compliance Workspace / 合规工作区
```

每个企业、团队或用户都有一个工作区。工作区里有：

```text
1. 规则
2. 记忆
3. 案件
4. 材料
5. Agent
6. 交付物
7. 审计日志
```

总结构：

```text
DataComply Flow
├─ Workspace 工作区
│  ├─ .datacomply/              # Markdown 规则与记忆
│  ├─ cases/                    # 每个合规案件
│  ├─ artifacts/                # 报告、清单、zip 交付物
│  ├─ uploads/                  # 用户上传材料
│  ├─ indexes/                  # RAG / memory 检索索引
│  └─ logs/                     # 执行日志、审计日志
│
├─ Rule Engine                  # 硬规则判断
├─ RAG Evidence Engine           # 法规与证据检索
├─ Agent Runtime                 # 合规任务编排
├─ Memory System                 # Markdown 分层记忆
├─ Quality & Scoring Engine      # 质检评分
└─ Artifact Renderer             # 文档交付
```

它的核心工作方式：

```text
用户创建一个合规任务
  ↓
系统加载当前工作区规则和记忆
  ↓
根据法域和任务类型召回相关标准
  ↓
Agent 编排规则引擎、RAG、文件解析、文档审查、报告生成
  ↓
每一步生成结构化中间产物
  ↓
质检与评分
  ↓
输出报告、清单、证据包和审计记录
  ↓
用户反馈后形成可审查的 memory patch
```

---

# 2. 最核心的设计原则

这套系统要避免“AI 全能化”。成熟的划分应该是：

| 部分             | 技术选择            | 原因                   |
| -------------- | --------------- | -------------------- |
| 路径判断、阈值判断      | 规则引擎            | 必须确定、可测试、可复核         |
| 法规、指南、模板、历史标准  | RAG             | 需要证据召回，不适合死写进 prompt |
| 多步骤任务推进        | Agent           | 负责拆任务、调工具、补问事实       |
| 报告正文、审查意见、摘要   | LLM             | 适合自然语言组织和草拟          |
| 用户偏好、企业标准、案件笔记 | Markdown Memory | 人可读、可改、可审查、可版本化      |
| 任务状态、权限、索引、版本  | 数据库             | 并发、查询、权限、审计更可靠       |
| 最终交付           | 模板渲染            | 保证格式稳定，不靠模型自由排版      |

一句话：

```text
规则管边界，RAG 管依据，Agent 管流程，LLM 管表达，Memory 管经验，评分管质量，数据库管状态。
```

---

# 3. Markdown 记忆系统设计

你希望采用 Claude Code 的方案，所以这里不要设计成普通“用户画像表”。

Claude Code 的 memory 不是简单聊天历史，而是分成 `CLAUDE.md / rules`、`memdir`、`SessionMemory`、`transcript/sessionRestore` 等层级；它不是 `messages[] = memory`，而是“文件型规则 + 长期记忆 + 会话摘要 + transcript 恢复 + 动态召回”。

映射到 DataComply：

```text
.datacomply/
├─ DATACOMPLY.md
├─ rules/
├─ memory/
├─ team/
├─ cases/
├─ agents/
└─ templates/
```

---

## 3.1 DATACOMPLY.md：工作区总规则

类似 Claude Code 的 `CLAUDE.md`。

作用：

```text
告诉系统这个合规工作区的总体规则。
```

示例：

```markdown
# DATACOMPLY.md

## Workspace Identity

This workspace is used for cross-border data compliance tasks.

## General Principles

- Do not output final legal conclusions without evidence.
- Distinguish statutory requirements from user internal standards.
- Distinguish internal decision materials from external filing materials.
- For every key claim, bind facts, legal basis, issue, and confidence.

## Output Style

Use the structure:

1. confirmed facts
2. missing facts
3. applicable rules
4. diagnosis
5. issues
6. recommendations
7. deliverables
```

用途：

```text
每次任务启动时直接加载。
```

---

## 3.2 rules/：条件规则记忆

类似 `.claude/rules/*.md`，但不按代码路径触发，而按法域、任务、材料类型触发。

例如：

```text
.datacomply/rules/
├─ cn/
│  ├─ path-diagnosis.md
│  ├─ security-assessment.md
│  ├─ pipia.md
│  └─ standard-contract.md
├─ eu/
│  ├─ dpia.md
│  ├─ tia.md
│  ├─ scc.md
│  └─ bcr.md
└─ us/
   ├─ cpra.md
   └─ eo14117.md
```

示例：

```markdown
---
jurisdiction: CN
tasks:
  - cn_diagnosis
  - cn_assessment
activation:
  data_direction: outbound
  data_subject: personal_information
---

# CN Outbound Path Diagnosis Rule

## Rule Boundary

Use RuleEngine for:

- CIIO status
- important data
- personal information count
- sensitive personal information count

LLM may explain but must not override hard rule results.

## Required Facts

- is_ciio
- contains_important_data
- pii_count
- spi_count
- destination_country
- receiver_type
```

这层解决的问题是：

```text
不同任务有不同规则；
不要把所有规则都塞进模型；
只加载当前任务相关规则。
```

Claude Code 里 `.claude/rules` 支持条件加载，避免所有规则无脑进入上下文；你的系统应采用同一思想，只不过条件从 `paths` 换成 `jurisdiction/task/document_type/risk_level`。

---

## 3.3 memory/MEMORY.md：长期记忆索引

Claude Code 的 memdir 采用 `MEMORY.md` 作为索引、具体记忆单独存为 `.md` 文件的形式，避免一个 memory 文件无限膨胀。

DataComply 也应该这样：

```text
.datacomply/memory/
├─ MEMORY.md
├─ user-preferences.md
├─ organization-profile.md
├─ review-standards/
│  ├─ security-measures.md
│  ├─ cross-border-notice.md
│  └─ receiver-obligations.md
└─ feedback/
   ├─ report-conclusion-style.md
   └─ contract-review-feedback.md
```

`MEMORY.md` 只放索引：

```markdown
# Memory Index

## User Preferences

- [Output style](user-preferences.md) — User prefers fact-basis-conclusion-risk-recommendation structure.

## Organization Background

- [Organization profile](organization-profile.md) — Common business scenarios, data types, receivers, risk posture.

## Review Standards

- [Security measures](review-standards/security-measures.md) — Minimum security clause requirements.
- [Cross-border notice](review-standards/cross-border-notice.md) — Required notice and separate consent fields.

## Feedback

- [Conclusion style](feedback/report-conclusion-style.md) — Avoid overstating legal certainty.
```

启动时只加载：

```text
DATACOMPLY.md
+ rules 中命中的规则
+ MEMORY.md 索引
+ team/MEMORY.md 索引
```

具体 memory 文件运行中按需召回。

这和 Claude Code 的策略一致：新会话重新加载规则和 `MEMORY.md` 索引，不自动加载上一轮完整 transcript；只有 resume 才恢复完整现场。

---

## 3.4 cases/<case_id>/SESSION.md：案件会话记忆

类似 Claude Code 的 SessionMemory。

Claude Code 的 SessionMemory 不是长期偏好，而是当前任务的工作笔记，用于上下文变长、compact 后仍保留任务主线。

DataComply 中应该有：

```text
.datacomply/cases/case_2026_001/
├─ CASE.md
├─ SESSION.md
├─ FACTS.md
├─ ISSUES.md
├─ EVIDENCE.md
├─ DECISIONS.md
├─ FEEDBACK.md
└─ artifacts/
```

`SESSION.md` 示例：

```markdown
# Session Memory

## Current Goal

Prepare CN outbound data compliance package for medical data transfer to Singapore cloud platform.

## Confirmed Facts

- Industry: Internet healthcare
- Destination: Singapore
- Receiver type: overseas cloud service provider
- Data: consultation records and image annotation data
- Sensitive personal information: yes
- SPI count: 20,000
- Important data: unknown

## Current Diagnosis

- Likely security assessment path.
- Important data status requires confirmation.

## Open Questions

1. Whether image annotation data is important data.
2. Whether separate consent was obtained.
3. Whether receiver contract includes audit and incident notification.

## User Feedback

- Do not write "definitely compliant".
- Use "risk may be controllable after supplementary measures".
```

作用：

```text
长任务不中断；
Agent 可以接续；
compact 后不丢主线；
resume 时快速恢复案件状态。
```

---

## 3.5 transcript：完整恢复，不等于长期记忆

要明确区分：

```text
memory/*.md
= 长期经验、用户标准、企业背景

SESSION.md
= 当前案件进度摘要

transcript.jsonl
= 某次完整执行现场
```

Claude Code 中 memdir 和 sessionRestore 是两种机制：memdir 记长期背景，sessionRestore 从 transcript 恢复某次具体会话现场。

DataComply 也应分开：

```text
case_runs/
├─ run_001.jsonl      # 每次 agent/tool 调用
├─ run_001.meta.json  # 模型、工具、版本、费用、状态
└─ run_001.context.md # 本轮上下文摘要
```

这样以后能回答：

```text
这份报告是怎么生成的？
当时用了哪些法规？
哪些结论来自规则？
哪些来自用户确认？
哪一版合同被审查？
用户后来改了什么？
```

---

# 4. 工作流执行设计

你的现有流程已经清楚：用户输入不是直接给 LLM，而是经过事实抽取、规则判断、附件解析、RAG、问题识别、证据链、模板章节，再进入 LLM；最终还要做一致性检查和交付渲染。

我建议抽象成一个统一工作流引擎：

```text
Workflow Engine
├─ Intake Stage
├─ Fact Stage
├─ Diagnosis Stage
├─ Evidence Stage
├─ Issue Stage
├─ Draft Stage
├─ Quality Stage
├─ Artifact Stage
└─ Memory Update Stage
```

---

## 4.1 Intake Stage：任务入口

输入：

```text
自然语言描述
表单
上传材料
法域选择
任务类型
已有案件上下文
```

输出：

```text
RawInput
CaseCreated
TaskPlan
```

这里不做法律判断，只做任务识别。

---

## 4.2 Fact Stage：事实抽取

输入：

```text
用户描述
表单
上传文件摘要
历史案件记忆
```

输出：

```json
{
  "jurisdiction": "CN",
  "industry": "internet_healthcare",
  "destination_country": "Singapore",
  "receiver_type": "cloud_provider",
  "data_types": ["consultation_records", "image_annotations"],
  "pii_count": 20000,
  "spi_count": 20000,
  "contains_important_data": "unknown",
  "confirmed_by_user": false
}
```

注意：

```text
LLM 可用于抽取；
但抽取结果必须标注来源和置信度；
不能把推测当确认事实。
```

---

## 4.3 Diagnosis Stage：路径诊断

这里必须以规则引擎为主。

输入：

```text
企业事实
法域规则
用户内部标准
```

输出：

```text
DiagnosisResult
RiskScore
MissingFacts
NextTasks
```

例如：

```json
{
  "recommended_path": "cn_security_assessment",
  "legal_basis": ["CN_SECURITY_ASSESSMENT_SPI_THRESHOLD"],
  "rationale": [
    "spi_count=20000 exceeds threshold"
  ],
  "missing_facts": [
    "important_data_status",
    "separate_consent_status"
  ],
  "user_standard_alerts": [
    "medical data scenario requires conservative review"
  ]
}
```

这里要分清：

```text
法定结论
用户内部预警
模型推断
```

不能混。

---

## 4.4 Evidence Stage：RAG 证据检索

RAG 不直接给最终结论，它只提供候选依据。

流程：

```text
企业事实
  ↓
构造检索 query
  ↓
按 jurisdiction/task/path 过滤
  ↓
检索法规、指南、模板、案例、用户标准
  ↓
适用性打分
  ↓
形成 RegulationHit / StandardHit
```

每条证据都要有：

```json
{
  "source_type": "regulation",
  "jurisdiction": "CN",
  "task": "cn_assessment",
  "title": "...",
  "snippet": "...",
  "applicable_facts": ["spi_count", "cross_border_transfer"],
  "evidence_strength": "high",
  "citation_required": true
}
```

你们业务文档也强调，RAG 证据链不应只是“系统检索法规”，而应表达成：企业事实生成检索问题、检索法律/指南/模板/案例、形成候选依据、将候选依据与企业事实匹配、检查判断是否被依据支持，再输出结论、证据和置信度。

---

## 4.5 Issue Stage：问题识别

输入：

```text
企业事实
附件摘要
法规依据
用户标准
规则检查结果
```

输出：

```text
IssueList
RiskItems
GapItems
```

示例：

```json
{
  "issue_id": "ISSUE_001",
  "type": "notice_and_consent_gap",
  "severity": "HIGH",
  "fact": "privacy_policy_missing_receiver_name",
  "basis": "cross_border_notice_requirement",
  "user_standard_basis": "cross-border-notice.md",
  "recommendation": "补充境外接收方名称、联系方式、处理目的、处理方式、个人信息种类和行权方式"
}
```

问题清单是后续报告、整改清单、评分的核心输入。

---

## 4.6 EvidenceChain Stage：证据链组装

证据链不是所有材料的总称，而是把：

```text
事实 + 法规依据 + 问题 + 结论
```

绑定起来。你的流程文件也明确强调了这一点。

结构：

```json
{
  "claim": "建议进入数据出境安全评估路径",
  "facts": [
    {
      "field": "spi_count",
      "value": 20000,
      "source": "user_form",
      "confirmed": true
    }
  ],
  "rules": [
    "CN_SECURITY_ASSESSMENT_SPI_THRESHOLD"
  ],
  "evidence": [
    {
      "hit_id": "reg_001",
      "strength": "high"
    }
  ],
  "conclusion": "security_assessment_recommended",
  "confidence": 0.92,
  "missing_info": [
    "important_data_status"
  ]
}
```

证据链的用途：

```text
报告引用
审计回溯
质检评分
用户复核
后续争议解释
```

---

## 4.7 Draft Stage：分章节生成

LLM 只在这里做主要写作。

输入不是原始材料，而是：

```text
企业事实
路径诊断
风险等级
附件摘要
法规依据
问题清单
证据链
章节模板
用户输出偏好
```

你的流程文件明确写到，LLM 的任务是“按照模板章节，使用企业事实，引用法规依据，围绕问题清单和证据链，生成报告正文”。

生成方式建议：

```text
不要一次生成全文；
按章节生成；
每章绑定 facts/issues/evidence；
每章生成后做局部检查。
```

---

## 4.8 Quality Stage：质检与评分

这里不是简单查错别字，而是做合规质量控制。

检查项：

```text
1. 路径一致性
2. 风险等级一致性
3. 事实一致性
4. 引用完整性
5. unknown 不得写成 false
6. 用户标准是否被采纳
7. 结论是否过度确定
8. 外部提交材料是否缺少附件
9. 报告章节是否完整
10. 证据链是否覆盖关键结论
```

你的流程文件也明确要求，LLM 写完后不能直接交付，还要检查是否把 non-CIIO 写成 CIIO、是否把 important_data=unknown 写成“不涉及重要数据”、风险等级是否矛盾、有没有缺少引用、有没有出现用户未提供事实等。

评分可分两套：

```text
法定合规评分
用户标准评分
```

示例：

| 维度      | 分数 | 说明            |
| ------- | -: | ------------- |
| 事实完整性   | 78 | 重要数据状态未确认     |
| 法规依据匹配度 | 90 | 关键结论均绑定依据     |
| 风险识别充分性 | 84 | 合同义务缺口识别较完整   |
| 用户标准符合度 | 72 | 政府请求通知机制未充分体现 |
| 交付可用性   | 80 | 可作草案，不建议直接提交  |
| 总分      | 81 | 需人工复核后交付      |

---

## 4.9 Artifact Stage：交付物生成

通过质检后再渲染。

输出：

```text
报告.docx
报告.md
风险清单.xlsx
材料缺口清单.md
证据链.json
审计日志.jsonl
交付包.zip
```

你的流程文件里也写到，最后通过模板渲染输出 docx、md、xlsx、zip 等交付物。

注意：

```text
不是每个任务都生成所有格式；
按业务用途生成。
```

例如：

| 任务       | 默认交付                             |
| -------- | -------------------------------- |
| 路径诊断     | 诊断报告.md/pdf + 后续任务清单             |
| 安全评估     | 自评估报告.docx + 材料清单.xlsx + 证据包.zip |
| 标准合同审查   | 条款对照表.xlsx + 批注版.docx            |
| DPIA/TIA | 报告.docx + 风险矩阵.xlsx              |
| CPRA     | 隐私治理缺口报告 + 权利机制整改清单              |
| EO 14117 | 红黄绿风险结论 + 接收方尽调清单                |

---

# 5. Agent 体系设计

不要一个万能 Agent。建议定义“主 Agent + 专项 Agent”。

Claude Code 的 subagent 不是简单再问一次模型，而是一个独立上下文、独立工具池、独立权限、独立 transcript、可后台化和可恢复的子 Agent 运行时。

DataComply 可以借鉴它的思想。

---

## 5.1 主 Agent：Compliance Coordinator

职责：

```text
理解用户目标
识别法域和任务类型
读取工作区规则与记忆索引
规划执行步骤
调用专项 Agent / Tool
汇总最终结果
```

它不直接做硬判断。

---

## 5.2 专项 Agent

```text
agents/
├─ intake-agent.md
├─ fact-extraction-agent.md
├─ path-diagnosis-agent.md
├─ rag-evidence-agent.md
├─ document-review-agent.md
├─ issue-detection-agent.md
├─ report-writer-agent.md
├─ quality-check-agent.md
├─ scoring-agent.md
└─ memory-curator-agent.md
```

每个 Agent 用 Markdown + frontmatter 定义，类似 Claude Code 的 `.claude/agents/*.md`：frontmatter 负责配置，正文负责角色、目标、边界、输出格式。

示例：

```markdown
---
name: quality-check-agent
description: Use this agent after draft generation to check consistency, citations, unsupported claims, user standard adoption, and deliverable readiness.
tools:
  - FactStore
  - EvidenceStore
  - DraftReader
  - CitationChecker
  - RuleEngine
  - UserStandardRetriever
disallowedTools:
  - ReportWriter
  - MemoryWriter
memory: project
maxTurns: 6
---

# Role

You are a compliance quality check agent.

# Boundaries

- Do not rewrite the whole report.
- Do not create new legal conclusions.
- Check whether the draft is supported by facts, rules, evidence, and user standards.

# Output

Return:

1. blocking issues
2. non-blocking warnings
3. unsupported claims
4. citation gaps
5. user standard adoption gaps
6. delivery readiness score
```

---

## 5.3 Agent 权限隔离

不同 Agent 只能用不同工具。

| Agent               | 可用工具                                      | 禁止                    |
| ------------------- | ----------------------------------------- | --------------------- |
| PathDiagnosisAgent  | FactStore, RuleEngine, RAG                | ReportWriter          |
| RAGEvidenceAgent    | Retriever, CitationStore                  | RuleOverride          |
| DocumentReviewAgent | FileParser, ClauseSplitter, RAG           | FinalConclusionWriter |
| ReportWriterAgent   | DraftStore, EvidenceStore, TemplateEngine | RuleEngineOverride    |
| QualityCheckAgent   | FactStore, EvidenceStore, DraftReader     | MemoryWriter          |
| MemoryCuratorAgent  | FeedbackReader, MemoryPatchWriter         | RuleEngineOverride    |

这样避免：

```text
审查 Agent 擅自改报告；
写作 Agent 擅自改路径；
记忆 Agent 擅自改法律规则。
```

---

# 6. Tool 系统设计

Claude Code 的 Tool 系统是模型和本地真实操作之间的执行层：模型只生成 `tool_use` 意图，本地运行时负责工具注册、参数校验、权限判断、安全检查、工具执行、结果封装和回填上下文。

DataComply 也应该采用这个模式。

工具分为：

```text
Fact Tools
Rule Tools
RAG Tools
File Tools
Review Tools
Draft Tools
Quality Tools
Memory Tools
Artifact Tools
```

建议工具清单：

| 工具                    | 作用                          |
| --------------------- | --------------------------- |
| `ExtractFacts`        | 从输入和附件中抽取结构化事实              |
| `ValidateFacts`       | 检查关键字段缺失和冲突                 |
| `RunRuleEngine`       | 执行法域/任务规则                   |
| `ComputeRiskScore`    | 计算基础风险等级                    |
| `ParseAttachment`     | 解析合同、隐私政策、数据清单              |
| `SplitClauses`        | 条款切分                        |
| `RetrieveRegulations` | 检索法规、指南、模板、案例               |
| `RetrieveMemory`      | 召回用户标准、企业偏好、历史反馈            |
| `DetectIssues`        | 识别风险项、差距项、问题清单              |
| `BuildEvidenceChain`  | 绑定 claim-fact-rule-evidence |
| `GenerateChapter`     | 分章节生成                       |
| `CheckConsistency`    | 检查事实、路径、风险、引用一致性            |
| `ScoreOutput`         | 法定合规分 + 用户标准分               |
| `ProposeMemoryPatch`  | 根据反馈生成 memory patch         |
| `RenderArtifact`      | 生成 docx/pdf/xlsx/zip        |

注意：

```text
Agent 不能直接碰数据库和文件系统；
必须通过 Tool。
```

这样才有权限、日志、可回放。

---

# 7. 数据模型设计

核心数据对象：

```text
Workspace
User
Organization
Case
TaskRun
Fact
DiagnosisResult
RiskScore
Attachment
AttachmentSummary
RegulationHit
MemoryHit
Issue
EvidenceChain
Draft
QualityIssue
ScoreReport
Artifact
Feedback
MemoryPatch
AuditEvent
```

最关键的是中间产物要结构化。

---

## 7.1 Fact

```json
{
  "fact_id": "fact_001",
  "case_id": "case_001",
  "field": "spi_count",
  "value": 20000,
  "source_type": "user_form",
  "source_ref": "form.q4_spi_count",
  "confidence": 1.0,
  "confirmed": true,
  "created_at": "..."
}
```

---

## 7.2 Issue

```json
{
  "issue_id": "issue_001",
  "case_id": "case_001",
  "type": "notice_gap",
  "severity": "HIGH",
  "facts": ["fact_privacy_policy_missing_receiver"],
  "evidence": ["reg_pipl_39"],
  "user_standards": ["memory_cross_border_notice"],
  "recommendation": "补充境外接收方名称、联系方式、处理目的、处理方式、个人信息种类和行权方式",
  "status": "open"
}
```

---

## 7.3 EvidenceChain

```json
{
  "chain_id": "chain_001",
  "claim": "建议进入安全评估路径",
  "facts": ["fact_spi_count"],
  "rules": ["rule_cn_spi_threshold"],
  "evidence_hits": ["reg_cn_001"],
  "issues": ["issue_001"],
  "confidence": 0.92,
  "review_status": "pending"
}
```

---

# 8. 记忆更新机制

不能自动把所有反馈写入长期记忆。

建议四级机制：

```text
临时反馈
  ↓
案件反馈
  ↓
候选记忆补丁
  ↓
用户确认后写入长期记忆
```

流程：

```text
用户修改报告/驳回建议/提出标准
  ↓
FeedbackCollector 记录原话
  ↓
MemoryCurator 判断是否值得沉淀
  ↓
ProposeMemoryPatch 生成 Markdown diff
  ↓
用户确认
  ↓
写入 memory/*.md
  ↓
更新 MEMORY.md 索引
  ↓
重建检索索引
```

示例：

用户说：

```text
以后合同里只写“合理措施”都判为中高风险。
```

系统生成候选 patch：

```markdown
# Security Measure Review Standard

## User Standard

Clauses using only abstract phrases such as "reasonable measures" or "necessary measures" are insufficient.

## Required Items

1. transmission encryption
2. access control
3. operation logs
4. least privilege
5. incident notice
6. audit cooperation
7. subcontractor approval

## Scoring

- Abstract-only clause: medium-high risk
- Missing incident notice: medium risk
- Missing subcontractor approval: medium-high risk
```

用户确认后才写入。

---

# 9. 上下文预算设计

Memory 不是免费的，会占模型上下文。Claude Code 也有上下文预算诊断，会统计 system prompt、tools、custom agents、memory files、skills、messages、free space 等，并通过 `MEMORY.md` 截断、条件 rules、include 深度限制、SessionMemory 长度控制、相关记忆召回数量限制等方式控制上下文。

DataComply 也必须做预算。

建议策略：

```text
启动固定加载：
- DATACOMPLY.md
- 当前法域/任务 rules
- memory/MEMORY.md
- team/MEMORY.md
- 当前 CASE.md / SESSION.md 摘要

按需召回：
- 最多 5 条用户标准
- 最多 8 条法规依据
- 最多 5 条历史反馈
- 最多 3 个相似案例

不直接加载：
- 完整历史 transcript
- 所有上传文件全文
- 所有法规全文
- 所有 memory 文件全文
```

上下文构造顺序：

```text
1. System contract
2. Workspace rule
3. Activated task rules
4. Case session memory
5. Confirmed facts
6. Diagnosis and risk result
7. Retrieved evidence
8. Retrieved user standards
9. Current task instruction
```

---

# 10. 前端产品设计

建议产品结构：

```text
首页
├─ 中国数据出境
├─ 欧盟 GDPR
├─ 美国数据合规
└─ 文档审查

任务空间
├─ 案件列表
├─ 当前任务状态
├─ 材料清单
├─ 记忆/标准
└─ 交付物

工作台
├─ 左侧：资源目录
│  ├─ 用户输入
│  ├─ 上传材料
│  ├─ 事实表
│  ├─ 证据链
│  ├─ 问题清单
│  └─ 交付物
│
├─ 中间：运行面板
│  ├─ 路径诊断
│  ├─ RAG 依据
│  ├─ 问题识别
│  ├─ 报告生成
│  ├─ 质检评分
│  └─ 渲染交付
│
└─ 右侧：Copilot / Agent
   ├─ 当前案件记忆
   ├─ 缺失事实追问
   ├─ 用户标准建议
   └─ memory patch 确认
```

其中“记忆中心”应该单独做：

```text
记忆中心
├─ Workspace Rules
├─ User Memory
├─ Team Memory
├─ Case Memory
├─ Review Standards
├─ Feedback History
└─ Memory Patch Review
```

---

# 11. 后端服务拆分

建议分成这些服务：

```text
api/
├─ workspace_api.py
├─ case_api.py
├─ task_api.py
├─ memory_api.py
├─ artifact_api.py
└─ review_api.py

core/
├─ workflow_engine/
├─ agent_runtime/
├─ tool_runtime/
├─ rule_engine/
├─ rag_engine/
├─ memory_engine/
├─ quality_engine/
└─ artifact_renderer/
```

关键服务职责：

| 服务                 | 职责                     |
| ------------------ | ---------------------- |
| `WorkflowEngine`   | 状态机、任务流转、失败恢复          |
| `AgentRuntime`     | 主 Agent / 子 Agent 执行   |
| `ToolRuntime`      | 工具注册、权限、结果回填           |
| `RuleEngine`       | 硬规则判断                  |
| `RAGEngine`        | 法规和记忆召回                |
| `MemoryEngine`     | Markdown 记忆加载、召回、patch |
| `QualityEngine`    | 一致性检查、评分               |
| `ArtifactRenderer` | docx/pdf/xlsx/zip 生成   |

---

# 12. 状态机设计

复杂任务不能同步一把跑完。建议状态机：

```text
CREATED
→ INTAKE_READY
→ FACT_EXTRACTING
→ FACT_REVIEW_REQUIRED
→ DIAGNOSING
→ EVIDENCE_RETRIEVING
→ ISSUE_DETECTING
→ EVIDENCE_CHAINING
→ DRAFTING
→ QUALITY_CHECKING
→ HUMAN_REVIEW_REQUIRED
→ RENDERING
→ COMPLETED
→ FAILED
```

支持局部重跑：

```text
用户修改事实
→ 从 Diagnosis Stage 重跑

用户上传新合同
→ 从 Attachment Parse / Issue Detection 重跑

用户确认新标准
→ 从 Issue Detection / Quality Stage 重跑

用户只改报告措辞
→ 从 Draft / Quality Stage 重跑
```

这比“失败就全流程重跑”成熟。

---

# 13. 一期到三期落地路线

## 一期：先把“中间产物链路”做实

目标：

```text
不要急着做复杂 Agent 和自动记忆。
先保证合规工作流稳定。
```

范围：

```text
1. Case / Task / Artifact 基础模型
2. 事实抽取
3. 中国路径诊断规则
4. RAG 法规检索
5. 问题清单
6. 证据链
7. 分章节报告生成
8. 一致性检查
9. docx/md/xlsx/zip 交付
```

Memory 只做最小版：

```text
DATACOMPLY.md
memory/MEMORY.md
cases/<case>/SESSION.md
```

---

## 二期：引入 Claude Code 风格 Markdown Memory

目标：

```text
让系统开始积累用户标准和案件经验。
```

范围：

```text
1. .datacomply/rules 条件加载
2. memory/MEMORY.md 索引
3. review-standards/*.md
4. MemoryRetriever
5. MemoryPatchReview
6. 用户确认后写入长期记忆
7. SessionMemory 自动更新
```

---

## 三期：引入 Agent Runtime 和多 Agent 协作

目标：

```text
让系统从流程型系统升级为智能合规作业系统。
```

范围：

```text
1. Agent Markdown 定义
2. Agent 工具权限隔离
3. 主 Agent + 专项 Agent
4. 后台任务
5. 失败恢复
6. 评分 Agent
7. Memory Curator Agent
8. 相似案例和用户标准自动召回
```

---

# 14. 最终设计总图

```text
用户任务
  ↓
Workspace Loader
  ├─ DATACOMPLY.md
  ├─ activated rules
  ├─ MEMORY.md index
  ├─ team MEMORY.md index
  └─ case SESSION.md
  ↓
Compliance Coordinator Agent
  ↓
Tool Runtime
  ├─ ExtractFacts
  ├─ RuleEngine
  ├─ RAGRetriever
  ├─ MemoryRetriever
  ├─ FileParser
  ├─ IssueDetector
  ├─ EvidenceChainBuilder
  ├─ ChapterGenerator
  ├─ QualityChecker
  ├─ ScoreEvaluator
  ├─ ArtifactRenderer
  └─ MemoryPatchWriter
  ↓
Structured Intermediate Artifacts
  ├─ Facts
  ├─ Diagnosis
  ├─ RiskScore
  ├─ AttachmentSummary
  ├─ RegulationHits
  ├─ MemoryHits
  ├─ Issues
  ├─ EvidenceChains
  ├─ Drafts
  ├─ QualityIssues
  └─ ScoreReports
  ↓
Human Review
  ↓
Deliverables
  ├─ docx
  ├─ md
  ├─ pdf
  ├─ xlsx
  ├─ zip
  ├─ evidence.json
  └─ audit.jsonl
  ↓
Feedback
  ↓
Memory Patch
  ↓
Long-term Markdown Memory
```

---

# 15. 这套构想的关键价值

它的价值不在于“用了 RAG、Agent、Memory”，而在于：

```text
1. 合规判断不靠模型猜，而靠规则和证据。
2. 大模型不直接生成最终结论，而是在结构化中间产物约束下写作。
3. 记忆不是聊天偏好，而是 Markdown 化的用户标准、企业背景、案件进度和团队规则。
4. Agent 不是魔法代理，而是有工具、权限、上下文和任务边界的执行单元。
5. 交付物不是聊天文本，而是报告、清单、证据链、评分和审计包。
6. 用户反馈不是临时修改，而是可确认、可审查、可版本化的 memory patch。
```

最终一句话：

> **这套系统应该被设计成“Claude Code 式合规工作区”：用 Markdown 承载规则和记忆，用规则引擎保证硬判断，用 RAG 提供证据，用 Agent 编排工具，用结构化中间产物约束 LLM，用评分和审计保证交付可信，并让用户反馈逐步沉淀成可复用的企业合规标准。**
