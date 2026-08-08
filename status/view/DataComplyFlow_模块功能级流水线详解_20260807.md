# DataComplyFlow 模块功能级流水线详解

> 审计日期：2026-08-07  
> 审计分支：`new`  
> 审计方法：逐模块阅读 `service.py`、`agents/*.py`、`rule_engine.py`、`renderer.py`，追踪真实调用链  
> 结论口径：本文描述的是代码真实实现，不是规划或期望

---

## 1. 系统总览

DataComplyFlow 的 11 个业务模块分布在 3 个法域（CN/EU/US）下，共享一套公共基础设施，但各模块复用程度不一：

```
backend/
├── common/               ← 公共基础设施
│   ├── workflow/         ← WorkflowPipeline + Fact/Issue/Evidence/ContextPack
│   ├── llm/              ← LLMClient + module_generator (章节生成)
│   ├── rag/              ← RegulationRAGService (分层法律检索)
│   ├── citation/         ← CitationRegistry (引用注册与脚注)
│   ├── trace/            ← TraceRecorder (运行事件记录)
│   └── tasks/            ← InMemoryTaskManager (异步任务)
├── domains/
│   ├── cn/               ← 中国法域 (4 模块)
│   ├── eu/               ← 欧盟法域 (4 模块)
│   └── us/               ← 美国法域 (3 模块)
└── integrations/         ← 外部集成 (DeliLegal)
```

**模块与公共基础设施的使用关系：**

```
                    WorkflowPipeline 使用者
                    ┌──────────────────┐
                    │ assessment       │ ← 完整使用，含 repair
                    │ eo14117          │ ← 完整使用
                    │ eu_scc           │ ← 使用但部分函数内联
                    │ cn_flow          │ ← 使用但参数断链
                    └──────────────────┘

                    独立 Pipeline（专用实现）
                    ┌──────────────────┐
                    │ document_review  │ ← 8 阶段专用链
                    │ diagnosis        │ ← 规则树 + Agent
                    │ pipia            │ ← 专用 service
                    │ dpia             │ ← 9 Agent 链
                    │ bcr              │ ← 双模式 (文档驱动/表单驱动)
                    │ tia              │ ← 确定性评估 + Agent
                    │ cpra             │ ← 规则引擎 + 4 Agent
                    └──────────────────┘
```

---

## 2. 公共基础设施层

### 2.1 WorkflowPipeline — 公共报告生成流水线

**定义位置**：`backend/common/workflow/pipeline.py`

这是 assessment、eo14117、eu_scc、cn_flow 四个模块共享的主执行内核。它是一个**依赖注入的模板方法**，由各模块传入 15 个 Callable 来定制行为。

**18 步执行链：**

```
Step  1: trace.record(request_event_name, payload)
Step  2: profile = extract_profile(payload)                    ← 模块注入
Step  3: diagnosis = evaluate_diagnosis(payload)               ← 模块注入
Step  4: path_warning = validate_path(payload, path, rationale) ← 模块注入
Step  5: facts = build_facts(payload, profile, diagnosis)      ← 模块注入
Step  6: regulations = retrieve_regulations(profile)           ← 模块注入
Step  7: attachment_notes = build_attachment_notes(profile)     ← 模块注入
Step  8: issues = build_issues(facts, diagnosis, regs, notes)  ← 模块注入
Step  9: issues, evidence = build_evidence(facts, issues, regs, diagnosis) ← 注入
Step 10: [可选] per_issue_rag = retrieve_per_issue(issues, profile, regs)
Step 11: context_pack = build_context_pack(...所有中间产物...)   ← 模块注入
Step 12: chapters = generate_chapters(profile, regs, context_pack) ← 模块注入
Step 13: consistency_issues = check_consistency(profile, chapters, pack)
Step 14: alignment_issues = check_alignment(report_content, profile)
Step 15: [可选] chapters, issues, blocked = repair_chapters(...)
Step 16: manifest = trace.write_manifest()
Step 17: outputs = render_artifacts(...)
Step 18: return WorkflowRunResult
```

**关键实现细节**：

- 每一步都有 `trace.record()`，形成完整事件链
- Step 15 的 repair 只执行**一次**，不是迭代至收敛：`repair_blocked` 标记后仍继续调用 `render_artifacts()`，注释称"fix → recheck → block"但代码行为是"fix → recheck → render 仍然执行"
- `per_issue_rag`（Step 10）是可选注入，用于对高风险 issue 触发第二次检索

**使用此 Pipeline 的模块对比**：

| 模块 | 使用程度 | 关键差异 |
|------|---------|---------|
| assessment | 完整 | 注入 `retrieve_per_issue` (HIGH/BLOCKER issue → DeliLegal)，注入 `repair_chapters` |
| eo14117 | 完整 | 注入 `retrieve_per_issue` (每 issue → RAG reformulation agent) |
| eu_scc | 使用但内联 | `_build_issues`/`_build_evidence` 依赖外部 `rule_result` |
| cn_flow | 使用但断链 | `_build_context_pack()` 不接受 `per_issue_rag`，参数不兼容 |

---

### 2.2 LLM 客户端 — 统一 LLM 调用门面

**定义位置**：`backend/common/llm/client.py`

```
LLMClient(settings)
  ├── 通过 LLMProviderRegistry 获取活跃 provider
  ├── 支持 OpenAI-compatible /chat/completions
  ├── 内置 JSON 解析 + usage/trace
  └── 失败时返回 _FALLBACK_MESSAGE
```

**Provider 链路**：`Settings → LLMProviderRegistry → get_active_provider() → OpenAI client`

启用条件：`provider.enabled AND api_key 非空 AND openai 包已安装`。任一条件不满足即 fallback。

### 2.3 module_generator — 通用章节生成

**定义位置**：`backend/common/llm/module_generator.py`

```
generate_chapter(
    module_name,       # "assessment" / "eu_scc" 等
    chapter_slug,      # "chapter_1_profile"
    instruction,       # 生成指令
    user_context,      # 事实/法规/上下文
    citation_registry, # 引用注册表
    task_id,           # 任务 ID
    trace,             # TraceRecorder
    module_templates,  # 模板映射
) → str (Markdown 章节正文)
```

内部流程：
1. 从 `SYSTEM_PROMPTS` dict 查找对应模块的 system prompt
2. 拼接 `instruction + user_context + citation 前置列表`
3. 调用 `LLMClient.chat()`
4. 返回 Markdown 文本

**已知 bug**：`SYSTEM_PROMPTS['cn_flow']` 的内容是 EO 14117 的 system prompt（法域污染）。

### 2.4 RAG 检索系统

**定义位置**：`backend/common/rag/retriever.py`

```
RegulationRAGService.retrieve(
    query, jurisdiction, path, filters, top_k
)
```

**检索层次**（从快到慢）：

```
1. SQLite FTS5 → 本地全文索引（最快）
2. 词法检索   → 关键词匹配 + 法域/path 过滤
3. 哈希向量   → HashingEmbedder (384 维稀疏哈希，非神经 embedding)
4. RRF fusion → 多路结果融合重排
5. 启发式重排 → 条款相关性 + jurisdiction boosts
6. [可选] 远程 → DeliLegal search_laws() (本地结果不足时)
```

**特殊处理**（`_rewrite_query`）：
- 中文离题查询本应返回空，但当前实现未有效拦截
- EU 精确条款（如"GDPR Article 35"）首屏命中率低
- 模板 chunk 在排名中可能排在法律原文前

**多层索引架构**（v3.1）：
```
storage/rag/v3/
├── cn/legal/        ← 中国法规条款
├── cn/workflow/     ← 工作流/模板
├── cn/standard_clause/ ← 标准条款
├── eu/legal/        ← 欧盟法规
├── eu/workflow/
├── us/legal/        ← 美国法规
├── us/workflow/
└── testcase/        ← 测试案例（L3，production 禁止使用）
```

### 2.5 CitationRegistry — 引用注册与脚注系统

**定义位置**：`backend/common/citation/registry.py`

```
CitationRegistry 生命周期（每次报告运行时新建，内存态，不持久化）：
  1. register(citation_item) → "CIT-001" 标记 ID
  2. 生成 prompt 时输出引用允许列表（含 CIT ID + 来源 + 条款摘要）
  3. LLM 生成章节后在正文插入 {{CIT-001}} marker
  4. postprocess 将 marker 转为脚注编号
  5. assign_footnote_number() 为每个 CIT ID 分配全局唯一序号
  6. build_citation_map_section() → JSON (citation_map.json)
  7. build_external_citation_map_section() → 外部视图（过滤低置信/内部引用）
```

**CitationItem 关键字段**：
- `source`：来源文档名称
- `article_id`：条款标识
- `quote`：引文原文
- `source_url`：法规原文链接（本地快照多为空）
- `confidence`：HIGH/MEDIUM/LOW
- `purpose`：legal_evidence / supporting / template
- `associated_issue_ids` / `associated_fact_ids`：关联的 Issue/Fact

**引用跳转能力**：
- `can_jump=true` 需满足：`article_id` 精确匹配 + `source_url` 不为空
- 当前 precision 约 14.3%（安全评估 7 条引用中仅 1 条可精确跳转）

### 2.6 中间结构 (Fact → Issue → Evidence → ContextPack)

**定义位置**：`backend/common/workflow/`

完整链路设计（实际贯穿程度因模块而异）：

```
FactItem (facts.py)
  ├── field_path: str          # 字段路径 "company_name"
  ├── value: Any               # 字段值
  ├── provenance: FactSource   # USER_INPUT / RULE_DERIVED / LLM_INFERENCE
  ├── confidence: str          # HIGH / MEDIUM / LOW
  ├── evidence_status: str     # CONFIRMED / UNVERIFIED / DISPUTED
  └── legal_implication: str   # 法律含义

IssueItem (issues.py)           ← 基于 Fact 和法规识别
  ├── issue_id: str
  ├── category: str             # 风险类别
  ├── severity: str             # BLOCKER / HIGH / MEDIUM / LOW
  ├── certainty: str            # CONFIRMED / LIKELY / POSSIBLE
  ├── fact_refs: list[str]      # 关联 Fact field_path
  ├── regulation_refs: list[str] # 关联法规引用
  ├── description / finding / recommendation
  └── action_items: list

EvidenceItem (evidence.py)      ← 为每个 Issue 构建证据
  ├── evidence_id: str
  ├── claim: str                # 断言陈述
  ├── conclusion: str           # 证据结论
  ├── fact_refs / rule_refs / citation_refs
  ├── document_refs: list[DocumentRef]
  ├── strength: str             # STRONG / MODERATE / WEAK
  └── status: str               # VERIFIED / UNVERIFIED

GenerationContextPack (context_pack.py) ← 聚合所有中间产物
  ├── task_id, facts, regulations[], issues[], evidence_chain[]
  ├── diagnosis, path_warning
  ├── attachment_notes[]
  ├── per_issue_rag (dict)
  └── citation_registry (CitationRegistry)
```

**贯穿程度对比**：

| 模块 | FactItem | IssueItem | EvidenceItem | ContextPack |
|------|:---:|:---:|:---:|:---:|
| assessment | ✅ | ✅ | ✅ | ✅ |
| eo14117 | ✅ | ✅ | ✅ | ✅ |
| eu_scc (管线内) | ✅ | ✅ | ✅ | ✅ |
| cn_flow | ✅ | ✅ | ✅ | ✅ |
| pipia | 专用 schema | 专用 schema | 专用 schema | ❌ |
| dpia | 专用 DTO | 专用 Finding | ❌ | ❌ |
| bcr (文档驱动) | ❌ | ❌ | ❌ | ❌ |
| bcr (表单驱动) | 专用 Problem/Finding | ❌ | ❌ | ❌ |
| tia | 专用 context dict | ❌ | ❌ | ❌ |
| cpra | CPRAFactPack | CPRAGapItem | ❌ | ❌ |
| diagnosis | DiagnosisFacts | ❌ | ❌ | ❌ |
| document_review | ❌ | ReviewIssues | ❌ | ❌ |

---

## 3. 中国法域模块详解

### 3.1 transfer_diagnosis — 中国数据出境路径诊断

**入口**：`POST /api/v1/diagnosis/evaluate`  
**核心文件**：`backend/domains/cn/transfer_diagnosis/`

#### 3.1.1 完整调用链

```
DiagnosisService.evaluate(answers, trace)
│
├─ 1. _resolve_answers(answers)
│     ├─ _normalize_answers()     ← 将 "unknown"/缺失值转为枚举
│     ├─ Agent(important_data)    ← q2_has_important_data == "unknown" 时调用
│     │                             可能改写答案为 yes/no
│     ├─ Agent(pi_classify)       ← q5_no_personal_info == "unknown" 时调用
│     │                             可能改写答案为 yes/no
│     └─ Agent(exemption)         ← q6_scenario == "other" 时调用
│                                   分析是否遗漏豁免场景
│
├─ 2. _validate_fact_consistency(answers)
│     └─ 检查：
│        ├─ 声明"包含个人信息"但 quantity=0 → 冲突
│        ├─ CIIO 标记 vs 行业冲突
│        └─ 敏感数据标记 vs 数量冲突
│     └─ 若冲突 → 直接返回 "needs_human_review"
│
├─ 3. DiagnosisRuleEngine.evaluate(facts)
│     └─ 逐条匹配 decision_tree.json 中的 9 条规则
│        规则按文件顺序执行，首次命中即停止：
│
│        Rule 0: no_personal_info       → 不涉及个人信息，无出境义务
│        Rule 1: exemption_contract     → 合同履行必要，豁免
│        Rule 2: exemption_hr           → 人力资源管理，豁免
│        Rule 3: exemption_emergency    → 紧急情况，豁免
│        Rule 4: exemption_legal_duty   → 法定义务，豁免
│        Rule 5: ciio                   → 关键信息基础设施运营者 → 安全评估
│        Rule 6: important_data         → 包含重要数据 → 安全评估
│        Rule 7: pii_threshold          → ≥100万个人信息 → 安全评估
│        Rule 8: spi_threshold          → ≥1万敏感个人信息 → 安全评估
│        default                        → SCC 或认证 (scc_or_certification)
│
├─ 4. [条件] _needs_ai_inference(answers)
│     └─ 当 answers 包含 unknown 且默认规则命中时：
│        _build_ai_inference_result()
│          └─ Agent(clarification)  ← 综合所有信息做 AI 推断
│             prompt 强调"只能解释，不得改判"
│             但输出仍可能影响 final_explanation 内容
│
├─ 5. _attach_fact_metadata()  ← 添加事实来源标记、
│    不确定性说明、Action Items 等
│
└─ 6. 返回 DiagnosisResult
      ├── recommended_path: security_assessment | scc_or_certification | exemption
      ├── risk_level: HIGH | MEDIUM | LOW
      ├── conclusion_source: "rule" | "ai_inference"
      ├── confidence: HIGH | MEDIUM | LOW | UNCERTAIN
      ├── legal_basis: list[str]
      ├── action_items: list[str]
      ├── uncertainty_notes: list[str]
      └── requires_human_review: bool
```

#### 3.1.2 关键设计决策与边界

| 项目 | 行为 |
|------|------|
| 规则顺序 | 豁免规则排在强制规则前，可能在 CIIO/重要数据未确认时误给豁免 |
| unknown 处理 | Agent 可将 unknown 改写为 yes/no，但 confidence 标记为 LOW |
| AI 边界 | 确定性规则命中后 prompt 要求"只能解释，不得改判" |
| 无版本管理 | 规则文件无 schema version、法规版本号、生效/失效时间 |
| 冲突检测 | 有事实一致性校验，冲突时直接触发 human_review |

#### 3.1.3 4 个 Agent 详解

| Agent | 触发条件 | 输入 | 输出能力 |
|-------|---------|------|---------|
| `important_data` | q2 = "unknown" | 行业、数据描述、数据类型 | 建议 yes/no，可改写答案 |
| `pi_classify` | q5 = "unknown" | 数据描述、PI 类型、行业 | 建议 yes/no 于"是否含个人信息" |
| `exemption` | q6 = "other" | 场景、目的、接收方类型、数量 | 分析是否遗漏豁免场景 |
| `clarification` | 存在 unknown + 默认规则命中 | 所有 answers + agent_notes | 综合推理解释（影响 text，不改路径） |

---

### 3.2 security_assessment — 数据出境安全自评估

**入口**：`POST /api/v1/assessment/generate` (sync) / `generate_async`  
**核心文件**：`backend/domains/cn/security_assessment/`

#### 3.2.1 完整调用链

```
AssessmentService.generate_report(payload, task_id, trace)
│
├─ 1. 构造 AssessmentRequest → 拆解为 DiagnosisAnswers
│     _to_diagnosis_answers(payload)
│       ├── _to_yes_no_unknown()          ← bool 转枚举
│       ├── _infer_transfer_scenario()    ← 推断传输场景
│       ├── _infer_receiver_type()        ← 推断接收方类型
│       └── _build_data_type_lists()      ← 构建数据分类列表
│
├─ 2. _build_pipeline() → WorkflowPipeline(15 个 Callable)
│     ├── extract_profile:   → payload 本身即 profile
│     ├── evaluate_diagnosis: → DiagnosisService.evaluate() 用拆解后的 answers
│     ├── validate_path:     → 检查 payload 声明的路径 vs 诊断结果
│     ├── build_facts:       → 从 payload + profile + diagnosis 构建 FactItem[]
│     │                        含 CompanyProfile、数据处理规模、接收方信息等
│     ├── retrieve_regulations: → RegulationRAGService.retrieve()
│     │                        中国数据出境法规、个保法、数安法等
│     ├── build_attachment_notes: → 解析附件中的条款/义务/缺失项
│     ├── build_issues:      → 基于 facts + regulations 构建 IssueItem[]
│     │                        每 issue 关联具体法条和事实
│     ├── build_evidence:    → 为每个 issue 构建 EvidenceItem[]
│     │                        含 fact/rule/citation/document 引用
│     ├── retrieve_per_issue: → 对 HIGH/BLOCKER issue 调 DeliLegal
│     │                        laws(3) + cases(2) per issue
│     ├── build_context_pack: → 聚合所有中间产物为 GenerationContextPack
│     ├── generate_chapters:  → module_generator.generate_chapter() × 8 章
│     │                        ┌─────────────────────────────────┐
│     │                        │ Ch1: 企业及数据处理概况          │
│     │                        │ Ch2: 数据出境链路与接收方        │
│     │                        │ Ch3: 法律依据与合规分析          │
│     │                        │ Ch4: 风险评估与影响分析          │
│     │                        │ Ch5: 安全措施与技术保障          │
│     │                        │ Ch6: 数据主体权利保护            │
│     │                        │ Ch7: 应急响应与整改方案          │
│     │                        │ Ch8: 综合结论与建议              │
│     │                        └─────────────────────────────────┘
│     ├── check_consistency:  → 检查章节间事实一致性
│     │                        legacy_chapter / context_pack_references /
│     │                        report_against_context 三重检查
│     ├── check_alignment:   → 检查报告正文 vs profile 对齐度
│     ├── repair_chapters:   → 修复一次（非迭代至收敛）
│     └── render_artifacts:  → AssessmentReportRenderer.render()
│
└─ 3. 产物输出 AssessmentReportRenderer
      ├── internal_markdown     ← 内部详细分析稿
      ├── official_markdown     ← 官方自评估报告格式
      ├── docx / pdf            ← Word/PDF 正式报告
      ├── evidence_chain_json   ← 证据链 JSON
      ├── citation_map_json     ← 引用映射
      ├── material_checklist_xlsx ← 材料清单
      ├── facts_json / issues_json
      ├── risk_matrix / mitigation_plan
      └── zip                   ← 全量打包
```

#### 3.2.2 产物清单

| 产物 role | 格式 | 说明 |
|-----------|------|------|
| `internal_markdown` | md | 内部详细分析，含 LLM 内部推理 |
| `official_markdown` | md | 对外正式报告，过滤内部标记 |
| `docx` / `pdf` | docx/pdf | 正式交付文档 |
| `citation_map_json` | json | 引用注册表 |
| `evidence_chain_json` | json | 完整证据链 |
| `material_checklist_xlsx` | xlsx | 材料完整度检查清单 |
| `risk_matrix_xlsx` | xlsx | 风险矩阵表 |
| `mitigation_plan_xlsx` | xlsx | 整改措施计划 |
| `facts_json` | json | 事实提取结果 |
| `zip` | zip | 全量打包 |

#### 3.2.3 已知问题

- `repair_blocked` 标记后 `render_artifacts()` 仍执行，不一致
- 报告内部标记可能泄露（`ISSUE-xxx`、`【待核验】`）
- 风险等级在同一报告中可能自相矛盾（HIGH → MEDIUM → HIGH）
- Markdown 表格渲染、换行破坏问题

---

### 3.3 pipia — 个人信息保护影响评估

**入口**：`POST /api/v1/pipia/generate`  
**核心文件**：`backend/domains/cn/pipia/`

#### 3.3.1 完整调用链

```
PIPIAService.generate_report(payload, task_id, trace)
│
├─ 1. 表单验证
│     ├── route_type 必须为 scc_filing / certification
│     ├── company_name / company_uscc 必填
│     ├── purpose / recipient 必填
│     └── attachment_role 校验（scc_filing 路径需 scc_contract）
│
├─ 2. _extract_attachment_evidence()  ← 解析 SCC 合同附件
│     └── FileParser → 条款提取 → 关键义务清单
│
├─ 3. _build_facts()  ← 从表单字段构建结构化事实
│     ├── 公司概况（名称、USCC、行业、CIIO）→ CompanyProfile
│     ├── 数据处理规模（pii_count, spi_count, subject_volume）
│     ├── 传输细节（目的、频率、接收方、国家）
│     ├── 法律依据与合规论证
│     ├── 权利保护机制（告知、同意、DSAR、保留）
│     └── 安全与应急（加密、访问控制、SLA、升级路径）
│
├─ 4. _build_structured_issues()  ← 规则式 Issue 生成
│     └── 基于 checklist 检查：
│         ├── 告知机制是否完整
│         ├── 同意机制是否单独+留痕
│         ├── DSAR 渠道是否可用
│         ├── 保留期限是否合理
│         └── 接收方保障是否充分
│
├─ 5. _build_evidence_chain()  ← 为每个 issue 构建证据
│     └── 关联事实引用、法规引用、附件证据
│
├─ 6. _assess_filing_readiness()  ← 备案准备度评估
│     └── 检查：标准合同是否签署、PIPIA 报告是否完整、
│            备案材料是否齐全、是否需补正
│
├─ 7. LLM 章节生成  ← 通过 generate_chapter() 生成报告正文
│
└─ 8. 产物渲染
      ├── pipia_report.md / docx / pdf
      ├── filing_readiness_report
      └── evidence_chain (json)
```

#### 3.3.2 与公共 Pipeline 的关系

PIPIA **不使用** `WorkflowPipeline`，有独立 service。不使用公共 `FactItem`/`IssueItem`/`EvidenceItem`，但有语义等价的专用 schema。不使用 `GenerationContextPack`。

---

### 3.4 document_review — 通用文档智能审查

**入口**：`POST /api/v1/review/*`（多端点，含文件上传与会话管理）  
**核心文件**：`backend/domains/cn/document_review/`

#### 3.4.1 完整调用链

```
ReviewService._run_pipeline(task_id, user_id)
│
├─ Stage 0: PREPARING (0-10%)
│   ├── StructuredDocumentParser.parse(file) → 结构化文档对象
│   │     提取：plain_text + tables + appendix_fields
│   ├── DocumentClassifier.classify(text) → 文档类型
│   │     (合同/隐私政策/用户协议/SCC/数据处理协议/其他)
│   └── ScenarioExtractor.extract(text) → 场景上下文
│         自动提取：当事人、数据类型、义务条款、管辖法域
│
├─ Stage 1: SEGMENTING (10-25%)
│   └── ClauseSegmenter.segment(text) → 条款列表
│        按条款号/标题/段落结构切分
│
├─ Stage 2: CLASSIFYING (25-45%)
│   └── ClauseClassifier.classify(clause) → 条款类型+审查优先级
│        (定义/义务/权利/责任/争议解决/其他)
│
├─ Stage 3: MISSING_CHECK (45-55%)
│   └── MissingItemChecker.check(classified, doc_type, scenario)
│        检查：必备条款缺失、关键定义缺失、签署要件缺失
│
├─ Stage 4: REVIEWING (55-80%) ← 核心审查
│   └── 按场景并行调用审查器：
│       ├── DataProtectionReviewer    → 数据保护条款审查
│       ├── DataTransferReviewer      → 跨境传输条款审查
│       ├── SCCMandatoryReviewer      → SCC 强制条款审查
│       ├── PrivacyPolicyReviewer     → 隐私政策审查
│       ├── UserAgreementReviewer     → 用户协议审查
│       ├── ContractTermsReviewer     → 合同条款审查
│       ├── [可选] ClauseReviewer(LLM) → LLM 增强审查
│       │   (仅对高价值条款，max_llm_clauses≤20)
│       └── 每个审查器输出 ReviewIssue{title, severity, finding, recommendation}
│
├─ Stage 5: CROSS_DOC_CHECK (80-85%)
│   └── CrossDocumentChecker → 跨文档一致性检查
│        (仅 enable_cross_document_check=true 时)
│
├─ Stage 6: AGGREGATING (85-95%)
│   ├── RiskScorer → 风险评分与排序
│   ├── ConsistencyChecker → 审查结论一致性
│   ├── CitationRelevanceChecker → 引用相关性
│   └── ReviewAggregator → 聚合所有审查结果
│
├─ Stage 7: RENDERING (95-100%)
│   ├── ReviewReportRenderer → 审查报告 (MD)
│   ├── AnnotatedDocxBuilder → 批注版文档 (DOCX)
│   └── ReportArtifact → SQLite 持久化
│
└─ 每阶段通过 WebSocket 向客户端推送进度
```

#### 3.4.2 与公共 Pipeline 的关系

完全独立。有专用 SQLite 任务持久化、专用审查链、专用 Agent 体系。不使用 `FactItem`/`IssueItem`/`EvidenceItem`。

#### 3.4.3 专用 Agent

| Agent | 触发时机 | 功能 |
|-------|---------|------|
| `scenario_facts` | PREPARING | 场景事实增强提取 |
| `data_sensitivity` | REVIEWING | 数据敏感度判定 |
| `scc_mandatory` | REVIEWING | SCC 强制条款对照 |
| `privacy_matrix` | REVIEWING | 隐私合规矩阵 |
| `cross_doc_semantic` | CROSS_DOC_CHECK | 跨文档语义一致性 |
| `legal_binding` | REVIEWING | 法律约束力评估 |
| `revision_drafting` | AGGREGATING | 修订建议撰写 |
| `review_boundary` | REVIEWING | 审查边界判定 |
| `report_qa` | AGGREGATING | 报告质量审计 |

---

## 4. 欧盟法域模块详解

### 4.1 eu_scc — 欧盟标准合同条款审查

**入口**：`POST /api/v1/eu_scc/generate`  
**核心文件**：`backend/domains/eu/scc_review/`

#### 4.1.1 完整调用链

```
EU_SCCService.generate_report(payload, task_id, trace)
│
├─ 1. 文件预处理
│     └── _use_uploaded_scc_document() → 解析上传的 SCC 文档
│         ├── StructuredDocumentParser → 条款结构化
│         └── 提取：Module 选择、Annex 数据、签署方信息
│
├─ 2. scc_rule_engine.run_eu_scc_rule_engine()  ← 确定性规则引擎
│     ├── validate_module_selection()    → 检查 Module 选择是否匹配实际条款
│     ├── compare_standard_clauses()     → 与 SCC 2021 标准条款逐条对比
│     │     检测：条款偏离、措辞修改、条款遗漏
│     ├── review_annexes()              → Annex I/II/III 完整性审查
│     ├── review_tia_and_measures()      → 传输影响评估与补充措施审查
│     └── score_scc_risk()              → 风险评分 (HIGH/MEDIUM/LOW)
│
├─ 3. _build_pipeline(rule_result) → WorkflowPipeline + 6 Agent
│     ├── document_structure Agent    → 文档结构完整性
│     ├── transfer_chain Agent        → 传输链路分析
│     ├── clause_semantic Agent       → 条款语义合规性
│     ├── tia_effectiveness Agent     → TIA 措施有效性评估
│     ├── evidence_review Agent       → 证据支撑度审查
│     └── remediation Agent           → 整改建议生成
│
├─ 4. 章节生成
│     └── _generate_chapters_from_pack()
│         ├── 模块与条款总览
│         ├── 传输链路评估
│         ├── 条款逐项审查
│         ├── TIA 与补充措施
│         ├── 证据与引用
│         └── 整改路线图
│
└─ 5. 产物
      ├── eu_scc_report.md / docx / pdf
      ├── rule_engine_result.json
      ├── findings.json
      ├── citation_map.json
      └── zip
```

#### 4.1.2 已知断链

`generate_report()` 中使用 `uuid` 但未 `import uuid`，导致 `NameError`。这是代码级 bug。

---

### 4.2 bcr — 有约束力的公司规则审查

**入口**：`POST /api/v1/bcr/generate`  
**核心文件**：`backend/domains/eu/bcr_review/`

#### 4.2.1 双模式架构

```
BCRService.generate_report(payload, task_id, trace)
│
├─ 若 payload 含文件上传 → _run_document_driven_review()
├─ 否则 → _run_form_driven_review()
```

**模式 A：文档驱动审查 (`_run_document_driven_review`)**

```
1. 解析 BCR 文档 → 提取全文文本
2. BCRTypeClassifier.classify(text, declared_type)
     → BCR-C (Controller) 或 BCR-P (Processor) 分类
3. BCRRuleEngine 加载 bcr_rulebook.json
     → 逐项检查：结构完整性、约束力、第三方受益人权利、
       责任承担、透明度、培训审计、监管合作、数据保障、
       第三国评估、政府访问、更新机制、定义质量
4. 10 个 Agent 并行/顺序运行：
   ├── type_reasoning        → BCR 类型推理
   ├── actor_role            → 各方角色判定
   ├── coverage              → 覆盖范围分析
   ├── onward_transfer       → 后续传输控制
   ├── evidence_coverage     → 证据充分性
   ├── incorrect_status      → 错误状态检测
   ├── tia_reasoning         → TIA 关联推理
   ├── legal_grounding       → 法律基础验证
   ├── approval_risk         → 审批风险评估
   └── remediation           → 整改方案
5. 聚合 → BCRProblems + BCRFindings
6. 法律检索 → BCRLegalRetriever
7. 报告生成
```

**模式 B：表单驱动审查 (`_run_form_driven_review`)**

```
1. 基于用户填写的 20+ 字段直接构造上下文
2. 调用 BCRRuleEngine 检查
3. LLM 生成审查章节
4. 生成简化报告
```

#### 4.2.2 与公共 Pipeline 的关系

不使用 WorkflowPipeline。专用 schema（BCRProblem、BCRFinding）。有专门的 legal retriever。`bcr_rulebook.json` 是静态规则文件。

---

### 4.3 dpia — 数据保护影响评估

**入口**：`POST /api/v1/dpia/generate`  
**核心文件**：`backend/domains/eu/dpia/`

#### 4.3.1 完整调用链

```
DPIAService.generate_report(payload, task_id, trace)
│
├─ 1. 附件解析
│     └── FileParser → 提取数据流图、制度文件等
│
├─ 2. 触发规则判断
│     └── dpia_need Agent → 判断是否需要 DPIA
│         输入：数据类型、处理规模、新技术使用、弱势群体等
│         输出：{dpia_required: true/false, trigger_reasons: [...]}
│
├─ 3. 9 Agent 链式执行 (按 GDPR DPIA 要求编排)
│
│     Step A: processing_activity Agent
│       → 数据处理活动描述与分类
│       输出：ProcessingActivity {data_categories, subjects, scale, ...}
│
│     Step B: necessity_proportionality Agent
│       → 必要性评估 + 比例性分析
│       输出：{lawful_basis, necessity_statement, proportionality_statement}
│
│     Step C: risk_assessment Agent
│       → 风险识别与评估
│       输出：RiskItem[] {risk_id, description, likelihood, impact}
│
│     Step D: mitigation_mapping Agent
│       → 缓解措施映射
│       输出：MitigationItem[] {id, description, target_risks, status}
│
│     Step E: dpo_consultation Agent
│       → DPO 意见征询
│       输出：{dpo_opinion, consulted_parties, concerns}
│
│     Step F: external_draft Agent
│       → 外部发布稿生成
│
│     Step G: internal_review Agent
│       → 内部审阅（"二审"）
│
│     Step H: consistency_repair Agent
│       → 一致性修复（单次）
│
├─ 4. RAG 检索
│     └── RegulationRAGService.retrieve(GDPR, DPIA 相关条款)
│
├─ 5. 产物渲染
│     ├── dpia_report.md / docx / pdf
│     ├── need_assessment.json (是否需要 DPIA)
│     ├── risk_matrix.xlsx
│     ├── mitigation_plan.xlsx
│     └── zip
│
└─ 6. 引用构造
      └── 引用 GDPR Art 35, Art 5, Art 6, Art 9 等
```

#### 4.3.2 与公共 Pipeline 的关系

不使用 WorkflowPipeline。有独立的 9 Agent 编排。不使用公共 FactItem/IssueItem，有专用 DTO。

---

### 4.4 tia — 传输影响评估

**入口**：`POST /api/v1/tia/generate`  
**核心文件**：`backend/domains/eu/tia/`

#### 4.4.1 完整调用链

```
TIAService.generate_report(payload, task_id, trace)
│
├─ 1. 确定性评估层 (不依赖 LLM)
│     ├── route_assessor      → 传输路径评估 (SCC/BCR/derogation)
│     ├── country_risk_assessor → 目的国法律风险评估
│     │     └── country_riskbook (静态 JSON) ← 不自动更新
│     ├── data_sensitivity_assessor → 数据敏感度分级
│     └── measure_assessor    → 补充措施充分性评估
│
├─ 2. 3 Agent 辅助
│     ├── rag_planning Agent  → 检索计划制定
│     ├── attachment_review Agent → 附件审查
│     └── dpo_review Agent    → DPO 二审
│
├─ 3. 法规检索
│     └── RegulationRAGService.retrieve(EU 法规 + 目的国法律)
│
├─ 4. _check_consistency()  ← 一致性检查
│     检查：路径 vs 工具、国家风险 vs 措施、数据敏感 vs 保护
│
├─ 5. _build_tia_citation_bundle()  ← 引用束构造
│     └── CitationRegistry → register → marker → footnote
│
└─ 6. 产物
      ├── tia_report.md / docx / pdf
      ├── country_risk_assessment
      ├── transfer_assessment
      └── citation_map.json
```

#### 4.4.2 关键边界

- country_riskbook 是静态 JSON，无自动法规时效更新
- 不使用 WorkflowPipeline，有独立的 context dict
- 无 EvidenceItem 体系

---

## 5. 美国法域模块详解

### 5.1 eo14117 — EO 14117 行政令合规评估

**入口**：`POST /api/v1/us_14117/generate`  
**核心文件**：`backend/domains/us/eo14117/`

#### 5.1.1 完整调用链

```
US14117Service.generate_report(payload, task_id, trace)
│
├─ 1. run_rule_engine(payload)  ← 确定性规则引擎 (核心)
│     ├── 数据分类 (DataClassification)
│     │     ├── 精确地理位置 / 生物识别 / 基因组 / 健康 / 金融
│     │     ├── 个人标识符 / 人口统计 / 政府相关
│     │     └── 敏感度标记 → {prohibited, restricted, exempt}
│     ├── 实体评估 (EntityAssessment)
│     │     ├── 关注国家匹配 (China/Cuba/Iran/North Korea/Russia/Venezuela)
│     │     ├── 政府控制/投资检测
│     │     └── 所有权结构分析
│     ├── 交易评估 (TransactionAssessment)
│     │     ├── 供应商协议 / 雇佣协议 / 投资协议
│     │     ├── 体量（≥US person 阈值）
│     │     └── 必要性论证
│     ├── 安全措施差距分析 (SecurityGapReport)
│     │     ├── 逻辑隔离 / 静态加密 / 传输加密 / 访问控制
│     │     ├── 数据最小化 / 假名化 / 审计日志
│     │     └── 措施覆盖率 → 每项 COMPLIANT/MISSING/PLANNED/PARTIAL
│     └── 红黄绿灯判断
│           ├── RED    = 禁止交易 (prohibited 数据 + 关注国家)
│           ├── YELLOW = 受限交易 (需 DOJ 审查)
│           └── GREEN  = 豁免/低风险
│
├─ 2. _build_pipeline(rule_result) → WorkflowPipeline
│     ├── facts:    从 payload + rule_result 构建 FactItem[]
│     ├── regulations: retrieve (EO 14117 文本 + 实施条例 + DOJ 指南)
│     ├── issues:   基于 rule hits 构建 IssueItem[]
│     ├── evidence: 每 issue → EvidenceItem[]
│     ├── retrieve_per_issue: 5 Agent 参与
│     │     ├── rule_boundary Agent       → 不确定分类时补判
│     │     ├── rag_reformulation Agent   → 检索 query 改写
│     │     ├── evidence_priority Agent   → 证据优先级排序
│     │     ├── repair_check Agent        → 完整性自检
│     │     └── chapter_consistency Agent → 章节一致性
│     └── context_pack → chapters → consistency → render
│
├─ 3. 章节生成 (6 章)
│     ├── 数据项分类与敏感度
│     ├── 接收方实体评估
│     ├── 交易风险评估
│     ├── 安全措施差距
│     ├── 后续传输分析
│     └── 综合结论与红黄绿灯
│
└─ 4. 产物 (10+ 文件)
      ├── us14117_report.md / docx / pdf / xlsx
      ├── rule_engine_result.json
      ├── facts.json
      ├── risk_matrix
      ├── citation_map.json
      └── zip
```

#### 5.1.2 规则引擎详细逻辑

`run_rule_engine()` 约 1100 行，是系统中**最大最完整的确定性规则引擎**：

```
for each data_item:
  ├── 匹配 prohibited 关键词 → 标记
  ├── 匹配 restricted 关键词 → 标记
  └── 匹配 exempt 关键词 → 标记

for each recipient_entity:
  ├── 国家匹配 → 关注国家列表
  ├── 政府控制检测 → 关键词匹配
  └── 所有权结构 → 模式匹配

for each security_measure:
  ├── 按 req_id 匹配预设措施模板
  └── 判定状态 COMPLIANT/MISSING/PLANNED/PARTIAL

最终判定:
  ├── ANY data_item.prohibited AND entity in country_of_concern → RED
  ├── ANY data_item.restricted → YELLOW
  └── ALL exempt → GREEN
```

---

### 5.2 cn_flow (eo14117_flow_review) — 中国数据流审查

**入口**：`POST /api/v1/cn-flow/generate`  
**核心文件**：`backend/domains/us/eo14117_flow_review/`

#### 5.2.1 完整调用链

```
CNFlowService.generate_report(payload, task_id, trace)
│
├─ 1. 数据解析
│     ├── data_inventory CSV → 数据项清单
│     │     每行：数据名称、类别、敏感标记、数量、目的
│     ├── entity_inventory CSV → 实体清单
│     │     每行：实体名、国家、角色、限制方标记
│     └── applicant_info → 申请主体信息
│
├─ 2. _build_pipeline() → WorkflowPipeline (但断链)
│     关键断链：_build_context_pack() 不接受 per_issue_rag 参数
│
├─ 3. 事实/Issue/Evidence 链
│     ├── 数据流事实提取
│     ├── 实体风险评估
│     └── 流向合规性审查
│
├─ 4. 章节生成 (5 章)
│
└─ 5. 产物
      ├── cn_flow_report.md / docx / pdf / xlsx / zip
      └── flow_diagram (数据流图)
```

#### 5.2.2 已知断链

- `_build_context_pack()` 与 `WorkflowPipeline.run()` 参数不一致
- `module_generator.py` 中 cn_flow system prompt 错误使用了 EO 14117 的 prompt（法域污染）

---

### 5.3 cpra — 加州隐私权法合规评估

**入口**：`POST /api/v1/cpra/generate`  
**核心文件**：`backend/domains/us/cpra/`

#### 5.3.1 完整调用链

```
CPRAService.generate_report(payload, task_id, trace)
│
├─ 1. 附件提取
│     └── CPRAAttachmentExtractor.extract(attachment)
│         每附件并行 → fact_extraction Agent 增强
│         输出：CPRAFactPack[] {data_items, vendors, consent_ui, ...}
│
├─ 2. CPRAFactMerger.merge(payload, fact_packs)
│     └── 合并原始 payload + 附件提取事实 → enhanced_payload
│
├─ 3. run_all_rules(enhanced_payload)  ← 10 组 if-else 规则
│     ┌─────────────────────────────────────────────┐
│     │ Domain 1: Notice & Transparency             │
│     │ Domain 2: Consumer Rights (Access/Delete/Correct) │
│     │ Domain 3: Opt-out of Sale/Sharing           │
│     │ Domain 4: Sensitive PI Limits              │
│     │ Domain 5: Data Minimization                 │
│     │ Domain 6: Purpose Limitation                │
│     │ Domain 7: Vendor/Contract Management        │
│     │ Domain 8: Consent UI Requirements           │
│     │ Domain 9: Data Retention                    │
│     │ Domain 10: Security Safeguards              │
│     └─────────────────────────────────────────────┘
│     → CPRAGapItem[] {domain, gap, risk_level, legal_basis, recommendation}
│
├─ 4. [fallback] 非结构化输入 → _build_legacy_gap_items()
│     └── 当 applicability is None 且无 data_items 时启用
│
├─ 5. 3 个附加 Agent
│     ├── spi_sharing_risk Agent   → 敏感信息共享风险评估
│     ├── vendor_contract Agent    → 供应商合同合规审查
│     └── consistency_review Agent → 差距审查一致性（最终审阅）
│
├─ 6. 法规检索
│     └── CPRALegalRetriever.retrieve()
│         CPRA 法条 + CCPA 修正案 + California AG 指南
│
├─ 7. _build_enhanced_context()  ← 构造 LLM 上下文
│     含：company profile、gap items、法规引用、spi review、vendor review
│
├─ 8. _generate_chapters_from_context()  ← LLM 生成 6 章
│     Ch1: 企业概况与 CPRA 适用性
│     Ch2: 告知与同意机制
│     Ch3: 消费者权利响应
│     Ch4: 数据出售/共享与 Opt-out
│     Ch5: 供应商与合同管理
│     Ch6: 综合差距分析与整改路线图
│
├─ 9. _attach_gap_citations()  ← 为每个 gap 附加引用
│     └── CitationRegistry.register() → 分配 CIT ID → 生成引用映射
│
└─ 10. 产物 (6+ 文件)
       ├── cpra_report.md / docx / pdf / xlsx
       ├── gap_items.json
       ├── citation_map.json
       └── zip
```

#### 5.3.2 与公共 Pipeline 的关系

不使用 WorkflowPipeline。有独立的 `CPRAFactPack`、`CPRAGapItem`。无 `EvidenceItem` 体系。使用 `CitationRegistry`（与其他模块共享同一 Registry 类）。

---

## 6. 异步任务系统

### 6.1 InMemoryTaskManager

**定义位置**：`backend/common/tasks/manager.py`

```
InMemoryTaskManager(module)
├── submit(fn, *args, **kwargs) → task_id
│     └── ThreadPoolExecutor.submit()
├── get_status(task_id) → {status, progress, result, error}
├── cancel(task_id) → 修改状态标志位（不终止线程）
└── 进程重启后所有状态丢失
```

**使用此管理器的模块**：assessment、pipia、bcr、dpia、tia、cpra、cn_flow、us_14117

**不使用**（独立异步实现）：diagnosis、eu_scc、document_review

### 6.2 通用审查的独立任务系统

document_review 使用 SQLite 持久化的 `ReviewTaskModel` + WebSocket 推送进度。任务状态跨进程重启可恢复。

---

## 7. 模块间复用程度总表

| 公共组件 | assessment | eo14117 | eu_scc | cn_flow | pipia | dpia | bcr | tia | cpra | diagnosis | review |
|----------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| WorkflowPipeline | ✅ | ✅ | ✅ | ✅⚠ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| FactItem 公共 schema | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| IssueItem 公共 schema | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| EvidenceItem 公共 schema | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| GenerationContextPack | ✅ | ✅ | ✅ | ✅⚠ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| CitationRegistry | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| TraceRecorder | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| RegulationRAGService | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | 专用 |
| module_generator | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | 专用 |
| InMemoryTaskManager | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | SQLite |
| LLMClient | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

图例：✅ = 完整复用，⚠ = 使用但有问题，❌ = 专用实现

---

## 8. 总结：模块成熟度分级

| 层级 | 模块 | 特征 |
|------|------|------|
| **L1 — 公共 Pipeline 贯穿** | assessment | 15 个 Callable 全量注入，repair+per_issue_rag 齐全，Fact→Issue→Evidence→ContextPack 完整，23 项产物 |
| | eo14117 | 同上，规则引擎最大最完整（1100行），红黄绿灯判断，5 Agent per_issue |
| **L2 — 公共 Pipeline 但有伤** | eu_scc | 部分函数依赖外部 rule_result，uuid 断链 |
| | cn_flow | context_pack 参数断链，system prompt 法域污染 |
| **L3 — 专用链，Agent 编排完善** | dpia | 9 Agent 链，按 GDPR 要求编排 |
| | cpra | 10 规则 + 4 Agent + 附件提取，引用系统完整 |
| | pipia | 独立 service，附件证据+备案准备度 |
| **L4 — 专用链，双模式** | bcr | 文档驱动/表单驱动双线，10 Agent |
| | tia | 确定性评估+3 Agent，country riskbook 静态 |
| **L5 — 独立体系** | diagnosis | 9 规则决策树 + 4 Agent，路径判断不调用 WorkflowPipeline |
| | document_review | 8 阶段独立 Pipeline，SQLite 持久化，9 专用 Agent，WebSocket 进度推送 |

---

> **文档维护**：本文档基于代码实现编写，与 `CURRENT_AI4Law_项目事实基线与真实系统理解.md` 和 `CURRENT_DataComplyFlow_全功能运行验证与问题汇报_20260805.md` 形成互补——基线条目化、验证报告侧重功能状态与问题、本文侧重代码级逻辑链路。
