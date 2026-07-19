# AI4Law 项目事实基线与真实系统理解

> 2026-07-17 治理更新：评测目录和执行入口已在事实审计后完成物理收敛。本文保留审计时历史路径用于追溯；当前 Benchmark 权威事实见 `docs/archive/governance/executed-batches/DataComplyFlow_BENCHMARKS评测目录治理契约.md` 与 `benchmarks/README.md`。

> 文档状态：事实审计快照。本文保留审计时点的代码证据，不代表所有结论仍是当前状态。后续已完成的结构治理和修复见 `DataComplyFlow_目录结构与工程规范治理实施报告_20260713.md`；当前工程入口以 `../standards/DataComplyFlow_活动架构与权威源.md` 为准。

> 产品：数规通 DataComplyFlow  
> 审计对象：本地 Git 仓库当前检出版本  
> 审计日期：2026-07-13（Asia/Shanghai）  
> 结论口径：代码与运行证据优先；本文是事实基线，不是法律意见、产品规划或重构方案。

## 1. 文档目的、审计范围与事实认定规则

> 2026-07-17 治理更新：本文所述 `qa/` 等路径是审计时历史事实。当前活动评测唯一入口为 `benchmarks/`，旧 `qa/` 的非重复结果已归档至 `docs/archive/evaluation/legacy-qa/`。

本文用于为后续产品开发、比赛准备、理论研究、Benchmark 建设和论文分析建立共同事实底座。扫描范围包括 `backend/`、`frontend/`、`ai_engine/`、`doc/`、`docs/`、`qa/`、`scripts/`、`storage/`、`paper/` 以及顶层启动、依赖和说明文件，共约 4,158 个受 Git 管理文件。

事实证据优先级依次为：本轮可运行代码/测试结果/真实输出；当前生效配置与入口；主流程真实调用；测试及示例；技术文档；README、注释与规划描述。类名或目录名含 `Agent` 不等于存在自治 Agent；目录存在不等于已接入；fallback、mock、demo、TODO 不计为完整能力。

本文认定标签：**已确认、部分确认、未确认、与文档不一致、需要运行验证**。模块接入状态：**完整接入、部分接入、仅有实现但未接入、占位/Stub、仅文档规划、疑似废弃、需要运行验证**。

本轮执行 `uv run --frozen pytest -q`，结果为 **290 passed、18 failed、17 errors、133 warnings，耗时 166.13 秒**。因此不能认定当前版本“全量稳定可用”。测试在 Python 3.13.3 临时环境执行；本轮生成的 `.venv`、测试 traces、数据库及运行配置改动已清理。

## 2. 一页式项目真实概览

### 2.1 产品事实

数规通不是单纯法律问答机器人。当前代码确实形成了一个以 React 工作台为前端、FastAPI 为后端，组合确定性规则、结构化事实/问题/证据、分层法律知识检索、OpenAI-compatible LLM 调用、引用注册、报告渲染和运行 trace 的多模块数据合规工作台。

但系统成熟度不均衡：安全自评估、DPIA、EO 14117 等模块具有较完整的结构化流水线；通用文档审查有独立数据库任务链；SCC、PIPIA、BCR、TIA、CPRA、EU SCC 等有实质实现和历史 trace，但不同模块复用公共 Schema、引用机制、修复机制的程度明显不同。不存在统一的跨模块 `ClaimItem` 或 `RuleItem`；“事实—规则—证据—结论”链只在部分模块较完整。

### 2.2 最重要的当前事实

1. **主产品实际是 React/Vite + FastAPI，而非 README 所写 Streamlit demo。** `frontend/src/main.tsx`、`frontend/src/App.tsx` 和 `frontend/src/lib/module-adapter.ts` 是真实前端入口；仓库不存在 README 声称的 `app_streamlit/Home.py`。
2. **模块不是空目录。** 后端真实挂载 diagnosis、assessment、SCC、PIPIA、BCR、DPIA、EU SCC、TIA、CN Flow、CPRA、EO 14117、v0 gateway，并有 25 个受版本控制的历史 trace manifest、751 个 trace 文件及 16 份通用审查 DOCX 报告。
3. **当前主干存在可复现断链。** SCC `generate_report()` 使用 `uuid` 但未导入；CN Flow 的 `_build_context_pack()` 未接受公共 Pipeline 传入的 `per_issue_rag`；异步 API 测试与现有鉴权要求冲突；知识审查测试在 Windows teardown 时数据库句柄未释放。

### 2.3 总体认定

| 维度 | 最终认定 | 核心证据 |
|---|---|---|
| 产品形态 | 已确认：证据约束、规则引导、可审计 Legal Agentic RAG 工作台的雏形 | `frontend/src/`；`backend/common/workflow/`；`backend/common/rag/`；`backend/common/citation/` |
| 路径层 | 部分确认：中国路径真实实现；EO 14117 为功能模块内路径；独立 EU 路径未实现 | `backend/domains/cn/transfer_diagnosis/`；`backend/domains/us/eo14117/`；`doc/addition/01_pathway_layer/03_eu_pathway_tbd/README.md` |
| 功能层 | 已确认有 10 类前端任务模板和 11 个模块路由；成熟度不一 | `frontend/src/lib/task-templates.ts`；`backend/main.py` |
| 结构化中间产物 | 部分确认：Fact/Issue/Evidence/ContextPack 存在并被部分模块贯穿；Claim/RuleItem 不存在 | `backend/common/workflow/*.py`；全仓搜索无 `ClaimItem`/`RuleItem` |
| RAG | 已确认：分层、条款/结构化 chunk、本地哈希向量+词法检索+启发式重排；不是语义模型 embedding | `backend/common/rag/`；`storage/rag/v3/` |
| Agent | 已确认有大量条件触发 LLM 包装器；多数是单次结构化 LLM 调用+规则 fallback，不是自治规划循环 | 各模块 `agents/*.py` 与 `service.py` 的 `.run()` 调用 |
| 引用与审计 | 部分确认：CitationRegistry、marker、citation map、trace 均存在；跨模块不统一，Claim 级 faithfulness 不完整 | `backend/common/citation/`；`backend/common/trace/` |
| 可运行性 | 部分确认：290 测试通过，但 18 失败、17 error | 本轮 pytest 实测 |

## 3. 仓库结构与技术栈

| 目录/文件 | 真实作用 | 认定 |
|---|---|---|
| `backend/` | FastAPI、SQLAlchemy、业务模块、规则/RAG/LLM/渲染/任务/trace；约 467 个受控文件 | 当前后端主实现 |
| `frontend/` | React 18 + TypeScript + Vite + Tailwind；含大量 SuperDesign 集成稿及 `.codex-archives` 历史副本；约 2,104 文件 | 当前前端主实现，但混有设计/历史资产 |
| `doc/knowledge/` | 法规原件、快照、规范、测试案例、registry、normalized JSONL、evaluation | 当前知识库资产；存在 `_index`/`index`、`_evaluation`/`evaluation` 双份历史结构 |
| `storage/rag/` | v2 单索引和 v3 多层多法域索引，约 18.9 MB | 可直接加载的本地检索索引 |
| `storage/traces/` | 历史运行中间 JSON 和 manifest | 审计/实验资产；非数据库级完整运行账本 |
| `storage/reports/` | 16 份通用文档审查 DOCX | 真实历史输出，但模块生成输出并非全部受版本控制 |
| `qa/` | RAG baseline、回归评测结果、v0 样本/期望输出 | 已有 Benchmark 雏形 |
| `ai_engine/` | 少量 prompts 和 JSON schema | 与当前 `backend/common/llm/module_generator.py` 并存，未成为统一主入口 |
| `scripts/` | 知识同步/索引/验证等脚本 | 工程辅助入口 |
| `doc/`、`docs/`、`paper/` | 大量开发说明、规划、错误记录、论文稿 | 证据级别低于代码；含重复/历史规划 |

主语言为 Python 3.11+ 与 TypeScript/React。后端依赖见 `pyproject.toml`：FastAPI、Uvicorn、Pydantic v2、SQLAlchemy、httpx、OpenAI SDK、python-docx、pypdf、openpyxl、reportlab、pytest 等。前端依赖见 `frontend/package.json`。

未发现 Dockerfile、Compose、Kubernetes 或 Alembic 配置。数据库默认 SQLite `sqlite:///./storage/ai4law.db`；迁移为 `Base.metadata.create_all()` 加 `_ensure_legacy_columns()` 中的 SQLite `ALTER TABLE`，不是正式迁移体系（`backend/core/db.py`）。异步任务为进程内 `ThreadPoolExecutor`，不是 Celery/RQ/消息队列（`backend/common/tasks/manager.py`）。

历史/重复实现包括：`frontend/.codex-archives/` 多轮前端修复快照、`frontend/tmp/` 比较脚本与运行结果、知识库带下划线和不带下划线的重复目录、v2/v3 RAG 并存、`backend/api/diagnosis.py` 与 `backend/domains/cn/transfer_diagnosis/router.py` 两套诊断 API、`ai_engine/prompts` 与 Python 内嵌 prompt 并存。

## 4. 系统启动方式与运行依赖

### 4.1 当前有效启动

- 后端：`uvicorn backend.main:app --reload --port 8000`。`backend/main.py` 创建 app 并额外挂载模块路由；`backend/app.py:create_app()` 挂载通用 API、初始化数据库、加载运行时配置并启动 SSE 清理协程。
- 前端：在 `frontend/` 执行 `npm run dev`（Vite）；`vite.config.ts` 负责本地开发配置。`frontend/src/main.tsx` → `App.tsx` → BrowserRouter/工作台。
- 健康检查：`GET /health`；前端 `checkBackendHealth()` 每 30 秒探测。

README 的 `streamlit run app_streamlit/Home.py` 与仓库不符：没有 `app_streamlit/`，也没有当前 Streamlit UI 入口。`pyproject.toml` 描述“backend and streamlit demo”已过期。

### 4.2 最小运行条件

本地规则/fallback 模式最低需要 Python 3.11+、项目依赖、可写 `storage/`。完整 LLM 能力需要 OpenAI-compatible provider 配置；支持 generic、SiliconFlow、Tencent Hunyuan（`backend/core/settings.py`、`runtime_settings.py`）。外部法律检索可接 DeliLegal OpenAPI。

重要风险：`backend/core/runtime_settings.py` 内置了 DeliLegal competition app id/secret 常量，并会作为默认配置启用；这是代码级凭据管理问题。`.env.example` 只列前端 API base 与 DeliLegal，未覆盖数据库、RAG、LLM provider 的完整环境变量。`storage/runtime_settings.json` 还可覆盖环境配置。

没有云部署清单，故云端部署状态未确认。没有外部对象存储，文件以本地 `storage/uploads`、`storage/reports`、`storage/traces` 管理。任务状态在内存，进程重启后不能从 TaskManager 恢复；数据库中的通用审查任务是另一套持久化机制。

## 5. 路径层真实实现

### 5.1 中国数据出境路径诊断

真实入口有两套：模块路由 `POST /api/v1/diagnosis/evaluate`、`/diagnosis/report`（`backend/domains/cn/transfer_diagnosis/router.py`），以及通用会话 API（`backend/api/diagnosis.py`）。核心为 `DiagnosisService.evaluate()` 和 `backend/domains/cn/transfer_diagnosis/decision_tree.json`。

规则按文件顺序首次命中：no personal information、合同履行、HR、紧急、法定义务豁免优先，之后 CIIO、重要数据、100 万个人信息、1 万敏感个人信息强制安全评估，默认 SCC 或认证。**规则文件没有 schema version、法规则版本号、生效/失效时间或冲突检测。** 法律依据是规则内字符串。

unknown 处理并非完全保守：`_normalize_answers()` 会依据表单材料推断 q2/q5 和人数；ImportantDataAgent、PIClassifyAgent 可将 unknown 改为 yes/no；当仍信息不足时 `_build_ai_inference_result()` 可形成显式 AI 推测路径。因此“AI 永不影响确定性结果”只对已命中规则后的 `final_explanation` 成立；命中前 Agent 会改变输入事实。规则命中后的解释 prompt 明确“只能解释，不得改判”。

突出边界：豁免规则允许 q1/q2 为 `unknown`，且排在强制规则之前，可能在 CIIO/重要数据未确认时给出豁免；应认定为代码事实和风险，而不能按文档理解为严格保守分流。

路径结果通过 `recommended_path`、legal_basis、action_items 等 DTO 返回；前端模板提供 diagnosis、assessment、pipia，但未发现一个统一编排器自动根据诊断结果创建并执行下游功能任务。存在 handoff DTO（`backend/schemas/diagnosis.py`），接入程度部分确认。

### 5.2 EO 14117 与欧洲路径

EO 14117 不是顶层统一路径诊断，而是 `/api/v1/us_14117/generate` 功能模块内部的规则引擎。`run_rule_engine()` 输出 rule hits、risk matrix、traffic light，并可在不确定分类时调用 `rule_boundary` Agent。规则与报告生成接入真实。

欧洲没有类似中国的统一“路径层”。前端直接提供 EU SCC、BCR、DPIA、TIA 四个任务模板。`doc/addition/01_pathway_layer/03_eu_pathway_tbd/README.md` 文件名即标注 TBD；故欧洲路径判定为**仅文档规划/未实现**。

## 6. 功能层模块真实状态表

| 模块 | 状态 | 入口与输入 | 核心处理与接入 | 实际输出/断链 |
|---|---|---|---|---|
| 通用合同审查 | 部分接入 | `/api/v1/review/*`；上传文件或 preset、ReviewGenerateRequest | 结构化解析→分类→条款切分→规则/专项 reviewer→可选 LLM reviewer→缺失项/一致性/引用相关性→聚合→报告 | SQLite 持久化任务，历史 16 DOCX；独立于公共 WorkflowPipeline；Agent/引用链为专用实现 |
| 中国 SCC 审查 | 部分接入且当前阻断 | `/api/v1/scc/generate(_async)`；SCCRequest、合同/材料 | 路径规则+9 个实际 Agent 调用+Fact/Issue/Evidence+RAG plan+章节+review/clarification/explanation+DOCX | 本轮所有核心 service 测试因 `uuid` 未导入失败；不能认定当前可运行 |
| EU SCC | 部分接入 | `/api/v1/eu_scc/generate(_async)`；SCC 文档、Annex、传输链 | parser+规则引擎+6 个 Agent（结构、链路、语义、TIA、证据、整改）+章节+trace | 11 个 service 测试通过；async 鉴权需另验；有历史 trace，无统一 Fact/Issue/Evidence 公共链 |
| BCR | 部分接入 | `/api/v1/bcr/generate(_async)`；文档驱动，表单 fallback | parser、BCR-C/P 分类、rulebook/checkers、10 个 Agent、法律检索、聚合、渲染 | service 测试通过，async API 401；document-driven 与 legacy fallback 双流程，公共 Schema 未贯穿 |
| CPRA | 部分接入 | `/api/v1/cpra/generate(_async)`；结构化企业/数据/DSR/vendor/UI+附件 | 附件抽取、4 Agent、FactMerger、10 组 if-else rules、法律检索、引用、章节、consistency review | service/rule 测试多数通过，async 401；有 46 事件历史 trace；无统一 Claim 层 |
| 安全自评估 | 部分接入、相对完整 | `/api/v1/assessment/generate(_async)`；AssessmentRequest/附件 | 公共 WorkflowPipeline：profile→diagnosis→facts→分层检索→issues→evidence→per-issue 法律/案例检索→ContextPack→章节→deterministic consistency/alignment→repair→内外部报告 | 结构化与引用最完整；本轮 2 项上下文/检索断言失败；其余大量测试通过；历史多模型 trace |
| CN Flow | 部分接入且当前阻断 | `/api/v1/cn-flow/generate(_async)`；数据清单、实体清单、接收方 | 公共 Pipeline+Fact/Issue/Evidence+RAG+多格式渲染 | `_build_context_pack()` 不接受 `per_issue_rag`，service 和 v0 测试失败；且 `module_generator.py` 中 `cn_flow` system prompt 错写 EO 14117 |
| PIPIA | 部分接入 | `/api/v1/pipia/generate(_async)`；公司、传输、PI 范围、权利、应急、附件 | 专用 service，LLM 章节、RAG/引用/trace，含规则式一致性检查 | service 测试通过，async 401；历史 22 事件 trace；公共 Fact/Issue/Evidence 未贯穿 |
| DPIA | 部分接入、Agent 链较完整 | `/api/v1/dpia/generate(_async)`；项目、处理、风险、措施、附件 | 触发规则→9 Agent（活动、必要性、风险、措施、DPO、内外稿、修复）→公共/专用结构→RAG→渲染 | 20 个 service 测试通过，async 401；v0 DPIA payload 测试 400，网关映射断链 |
| TIA | 部分接入 | `/api/v1/tia/generate(_async)`；工具、出口/进口方、第三国、措施、结论、附件 | route/country/data/measure deterministic assessor+3 Agent+RAG+citation bundle+一致性+多格式渲染 | service 测试通过，async 401；country riskbook 为静态 JSON，无自动法规时效更新证据 |
| EO 14117 | 部分接入、核心规则可测 | `/api/v1/us_14117/generate(_async)`；数据、实体、人员、交易、安全措施 | deterministic rule engine→公共 Pipeline→5 Agent→Fact/Issue/Evidence→RAG→ContextPack→章节/一致性→多格式输出 | 21 个 service 测试通过；历史 41 事件 trace；独立 pathway UI 未与顶层诊断统一 |

“完整接入”在本版本不授予任何模块：全量测试不通过，且没有模块获得本轮端到端真实外部 LLM+法律 API+前端浏览器验证。

## 7. 核心端到端调用链

### 7.1 公共工作流型模块（assessment、CN Flow、EO 14117；部分思路被其他模块复用）

```text
用户在 WorkspacePage/ModuleRunPanel 提交
→ frontend/src/lib/module-adapter.ts 选择 sync/async endpoint
→ FastAPI module router
→ ModuleService.generate_report() / InMemoryTaskManager
→ prepare_run() + TraceRecorder
→ WorkflowPipeline.run()
→ profile/diagnosis/path validation
→ FactItem[]
→ RAG / legal API retrieval
→ IssueItem[]
→ EvidenceItem[]
→ GenerationContextPack
→ generate_chapter() / module agents
→ deterministic consistency + alignment
→ optional repair
→ renderer (MD/DOCX/PDF/XLSX/JSON/ZIP，依模块而异)
→ output_files + trace manifest + citation_map
→ 前端轮询/SSE 展示 timeline、报告和资源
```

### 7.2 通用文档审查

```text
上传文件/创建 Review task
→ backend/api/review.py
→ ReviewService._run_pipeline()
→ StructuredDocumentParser / ClauseSegmenter
→ DocumentClassifier / ScenarioExtractor
→ Rulebook + specialized reviewers + optional ClauseReviewer(LLM)
→ MissingItemChecker / RiskScorer / ConsistencyChecker / CitationRelevanceChecker
→ ReviewAggregator
→ ReviewReportRenderer / AnnotatedDocxBuilder
→ SQLite ReviewTaskModel + ReportArtifact
```

### 7.3 各模块并非真正统一编排

SCC、PIPIA、BCR、DPIA、EU SCC、TIA、CPRA 各自有专用 service；公共 `WorkflowPipeline` 不是全平台唯一执行内核。`v0_task_gateway` 只映射 assessment、PIPIA、BCR、DPIA、TIA、CN Flow、CPRA，不包含 diagnosis、SCC、EU SCC、EO 14117，且其 DPIA/CN Flow 映射在本轮测试失败。

## 8. 结构化中间表示与 Schema

| 结构 | 定义与关键字段 | 创建/消费 | 贯穿性与 Benchmark 价值 |
|---|---|---|---|
| CompanyProfile | `backend/domains/cn/security_assessment/schema.py`；公司、数据、接收方、系统、措施等 | ProfileExtractor→assessment pipeline/generator/renderer | 仅 assessment 主类型；其他模块各有 Profile/Request，存在重复 |
| FactItem | `backend/common/workflow/facts.py`；provenance、value、confidence、evidence_status、外部正向陈述权限 | 各 fact_builder→Issue/ContextPack/renderer | assessment/CN Flow/EO14117 等较真实；适合作 Benchmark，但枚举注释与实际 literal 口径有历史不一致 |
| FactPack/MergeLog | 同文件；facts、来源/证据统计、冲突候选与 winner | CPRA 有独立 `CPRAFactPack`/FactMerger；公共 MergeLog 使用有限 | 可用于 Gold fact extraction，需先统一多套 schema |
| RuleItem | **不存在** | 各规则用 JSON、函数、dict 或 RuleHit | 不能直接作为统一规则 Benchmark schema |
| IssueItem | `backend/common/workflow/issues.py`；category/severity/certainty、fact/rule/evidence refs、action、outputs | issue_builder→Evidence/ContextPack/renderer | 公共流水线较适用；其他模块多用 Finding/Problem/GapItem |
| EvidenceItem/EvidencePack | `backend/common/workflow/evidence.py`；claim、conclusion、fact/rule/citation/document refs、strength/status | evidence_builder→ContextPack/prompt/renderer | 部分模块真实进入 prompt；可做 evidence attribution 数据集 |
| ClaimItem | **不存在** | SCC 中 `_extract_claims()` 使用普通 `dict`；EvidenceItem 含 claim 字符串 | 无统一 claim 拆分、claim-level 验证与 gold schema |
| Diagnosis | 各模块独立：`DiagnosisResult`、`PathDiagnosisResult`、US14117RuleEngineResult 等 | 规则/Agent→下游 | 多套重复，不是统一类型 |
| GenerationContextPack | `backend/common/workflow/context_pack.py`；facts/regulations/issues/evidence、risk、path、策略、引用 registry 等 | Pipeline build→chapter/consistency/renderer | 核心公共 IR；assessment 最完整，其他模块覆盖不一 |
| Citation | `CitationItem` dataclass；source/chunk/article/quote、关联 fact/issue/evidence、置信/权威/用途 | Citation builder/registry→prompt marker→postprocess/renderer/map | 可做 citation benchmark；非 ORM，跨模块使用不一致 |
| Audit/Trace | `TraceRecorder` JSON event+manifest；CitationAuditLog ORM；RunEvent/SSE | service/task→前端 timeline/API | 可用于过程数据；manifest 仅 created_at/event list，无统一 module/task/status/duration |
| Report Section | 各模块 Chapter 类型、assessment template schema、通用 review AggregatedReview | generator→renderer | 多套重复，无统一 ReportSection 基类 |

数据库实体仅覆盖用户/会话、诊断 session、通用 review task/upload、report artifact、workspace state、knowledge documents/chunks、citation audit。大多数模块任务在内存，不落统一任务表。

## 9. 规则引擎真实实现

当前不是单一规则引擎，而是多种机制并存：

- 中国路径：有序 JSON 决策表 + `_rule_match()` if-else，首次命中。
- 中国 SCC：`evaluate_hard_thresholds()`、`determine_path()` Python 函数。
- EO 14117：Python rule engine，输出 `US14117RuleHit`、risk matrix、traffic light。
- EU SCC：`scc_rule_engine.py` 对模块、条款、附件、TIA 做确定性检查。
- CPRA：`gap_rules.py` 10 组 if-else 规则。
- BCR：`bcr_rulebook.json` + loader + checklist/条款/TIA/责任/后续传输 checkers。
- TIA/DPIA：静态 riskbook/规则 assessor + Agent 辅助。
- 通用合同审查：`resources/rules/cn/review_rulebook.json` + `backend/domains/cn/document_review/` specialized reviewers。

规则和法规依据多数绑定在同一 JSON/Python 常量中，未形成统一“条件—例外—法律效果—优先级—版本”的 RuleItem。中国 diagnosis 有显式顺序优先级，其他模块主要由调用顺序隐式决定。普遍缺少：统一版本管理、effective date gating、规则冲突求解、未命中解释、可重放规则版本快照。缺失事实能通过 unknown、missing materials、Issue certainty 表达，但非全模块统一。

AI 冲突处理不统一：中国 diagnosis 在确定性命中后不允许解释 Agent 改判，但命中前 Agent 可修改 unknown；EO 14117 `rule_boundary` 可返回 overrides；BCR Agent 可调整类型/评级和新增 finding；CPRA Agent 与 rule gaps 合并。不存在平台级“规则优先于 AI”的强制策略。

## 10. 法规知识库与 RAG 真实实现

### 10.1 数据与索引

`doc/knowledge/` 包含 170 PDF、162 Markdown、90 HTML、29 DOCX、14 JSONL、9 CSV、8 JSON 等。来源目录覆盖 CN assessment/diagnosis/PIPIA/review、EU BCR/DPIA/SCC/TIA、US EO14117/CPRA。`normalized/regulation_articles.jsonl` 与 source registry/catalog 提供 article、status、effective_date、source_url 等 metadata。

`storage/rag/` 已提交约 18.9 MB 索引：v2 `regulation_index_v2.json`；v3 按 CN/EU/US 和 legal/workflow/standard_clause/template/testcase 分层的 JSONL + vector JSON。`MULTI_INDEX_SCHEMA_VERSION = "v3.1"`。

### 10.2 检索机制

- embedding 是 `HashingEmbedder`（384 维稀疏哈希词向量），不是外部神经 embedding 模型。
- 本地向量存储为 JSON；PostgreSQL 时可选 pgvector，但依赖未列入 `pyproject.toml`，默认 SQLite 不使用。
- 有词法打分、query 规则改写、metadata/jurisdiction/path filter、RRF fusion、SQLite FTS5、启发式 reranker。
- reranker 不是 cross-encoder/LLM reranker；query rewrite 主要是规则字符串扩展，不是通用 LLM rewrite（个别模块另有 rag_planning/reformulation Agent）。
- `retrieve_regulations()` 优先 v3 orchestrator，随后本地 v2，并可在结果不足时调用 DeliLegal `search_laws()`；assessment 对 HIGH/BLOCKER issue 还调用 laws + cases。
- UsagePolicy 能阻止 L3 testcase 进入 production external report，并限制 L4 template、法律证据和内部用途。

检索粒度应认定为 **以条款级/结构化 chunk 级为主，兼有文档元数据与标准条款/工作流 chunk**。中国法规构建标记 `article_split`，chunker 支持章/节/条/款/项层次；但并非所有 170 个原始文档都证明已高质量解析为条件/例外级原子规则。不能认定为完整“条件/例外级法律检索”。

版本与有效期 metadata 存在，但检索阶段未发现统一的“仅当前有效版本”强制过滤逻辑；`SourceRegistryEntry.is_current_version/status` 更多是数据字段。外部 DeliLegal 结果 `article` 可为空，定位质量低于本地条款数据。失败 fallback 为本地索引/启发式结果或空结果，章节生成器仍可能以无引用模式生成。

## 11. Agent / LLM 调用清单

### 11.1 LLM 基础设施

`backend/common/llm/client.py:LLMClient` 通过 OpenAI-compatible `/chat/completions` 调用 provider，提供 JSON 解析、usage/trace 和失败 fallback。`module_generator.py:generate_chapter()` 是通用单次章节生成调用，system prompt+章节 instruction+context+引用 marker，无多轮自主规划。

### 11.2 主流程实际调用的模块 Agent

| 模块 | 实际 service 调用的 Agent | 性质/触发 |
|---|---|---|
| diagnosis | important_data、pi_classify、exemption | unknown/other 条件触发；可修改或补充路径输入；单次 LLM+规则 fallback |
| SCC | path_diagnosis、data_classification、contract_review、legal_basis_review、evidence_verification、rag_planning、report_review、clarification、explanation | 顺序管线；无自治循环；部分 Agent 结果直接改变 diagnosis/finding/plan |
| BCR | type_reasoning、actor_role、coverage、onward_transfer、evidence_coverage、incorrect_status、tia_reasoning、legal_grounding、approval_risk、remediation | 文档驱动条件触发；新增 finding/改评级；单次调用+规则 fallback |
| DPIA | dpia_need、processing_activity、necessity_proportionality、risk_assessment、mitigation_mapping、dpo_consultation、external_draft、internal_review、consistency_repair | 多阶段链；repair 是一次修复阶段，非开放循环 |
| EU SCC | document_structure、transfer_chain、clause_semantic、tia_effectiveness、evidence_review、remediation | 规则结果增强和 patch；部分纯规则、部分可选 LLM |
| TIA | rag_planning、attachment_review、dpo_review | 检索计划、证据冲突、二审；fallback 固定结构 |
| CPRA | fact_extraction、spi_sharing_risk、vendor_contract、consistency_review | 附件事实增强、风险合并、最终一致性；无状态 |
| EO 14117 | rule_boundary、rag_reformulation、evidence_priority、repair_check、chapter_consistency | 不确定边界、检索、证据排序、完整性和章节一致性；单次 calls |
| assessment | `agents/` 下 attachment_parsing、data_classification、document_planning、expression_calibration、input_normalization、legal_citation、controlled_repair | 由 profile/generation/repair 子组件调用，公共 pipeline 编排；不是自治 agent graph |
| 通用 review | scenario_facts、data_sensitivity、SCC mandatory clause、privacy matrix、cross-doc semantic、legal binding、revision drafting、review boundary、report QA | `ReviewService` 的专用审查链按场景/候选调用 |

仓库中 Agent 文件数量不能等同运行 Agent 数量。所有已查实现均以 service 顺序编排，状态主要通过普通 Python 对象/trace 传递；未发现 ReAct 工具循环、动态计划执行器、长期记忆或多 Agent 自主协商。工具使用主要是 service 在 Agent 前后调用 parser/RAG/rule，并非模型原生 function-calling tool loop。故更准确称为“Agent 命名的结构化 LLM 专家步骤”。

## 12. Evidence、Claim、Citation 和审计链路

公共链路设计为：FactItem → IssueItem（fact_refs/rule_refs）→ EvidenceItem（claim/conclusion/fact/rule/citation/document refs）→ GenerationContextPack → prompt/renderer。assessment、CN Flow、EO 14117 等确实把 evidence block 放入章节 context；不是纯文档宣称。

但完整性有限：

- 没有 `ClaimItem` 类，无法把最终报告稳定拆成 claim 并逐 claim 校验。SCC `_extract_claims()` 返回普通 dict；EvidenceItem 的 `claim` 是生成前证据陈述，不等价于最终文本 claim。
- CitationRegistry 是每次报告的内存注册表，能生成 `{{CIT-...}}` prompt marker、分配全局脚注、输出 citation map；CitationItem 可关联 issue/fact/evidence。
- 引用主要在生成前提供允许列表，生成后由 postprocess 转脚注；部分 legacy 模块仅把引用字符串附到章节或由 `ensure_paragraph_citations()` 补充，严格性不同。
- citation API/前端 drawer/popover 支持查看 source/article/quote；能否跳转法规原网页取决于 source_url，外部结果及本地快照并非全量有 URL。
- assessment 有 internal/external report 隔离、external_report_allowed 与低置信引用过滤；不是全模块统一“双视图”。
- `citation_relevance_checker.py`、assessment citation quality、BCR legal grounding Agent 等提供相关性检查，但没有全平台统一 entailment/faithfulness verifier。

最终认定：**已形成可审计证据链骨架，部分模块真实贯穿；尚未形成报告 Claim 级、全模块一致的可验证法律论证图。**

## 13. Verifier、一致性检查、修复和人工分流

| 类型 | 真实实现 | 边界 |
|---|---|---|
| Schema 校验 | Pydantic request/result/IR；JSON schema validator | 主要校验结构，不验证法律真实性 |
| 确定性一致性 | assessment `ConsistencyChecker`、common alignment、CN Flow/TIA/PIPIA checks、review consistency/missing item | 模块规则不统一；有的只检查附件/引用是否存在 |
| LLM 审稿 | SCC report_review、DPIA internal_review/DPO、TIA DPO、CPRA consistency、EO chapter_consistency、review QA | 单次 prompt 自检/二审；不能等同形式化 verifier |
| 证据/引用检查 | evidence verification、citation relevance/quality、BCR legal grounding | 局部实现；无统一 unsupported-claim detector |
| 修复 | 公共 Pipeline `repair_chapters`；assessment repair pass；DPIA consistency_repair；EO repair_check | 公共 pipeline 只执行一次修复，不是多轮至收敛；多数模块无阻断 |
| 阻断/人工 | assessment repair 可置 `REPAIR_BLOCKED`，但代码随后仍调用 renderer；issues 可建议 legal escalation | 没有统一审批队列/人工确认后再发布的强制状态机；knowledge review queue 仅用于知识审核 |

公共 `WorkflowPipeline` 注释称“fix → recheck → block”，实际 `repair_chapters` 只调用一次；`repair_blocked` 时向 `consistency_issues` 添加文本，但仍继续 `render_artifacts()`。因此“修复失败自动阻断文件交付”与代码行为不完全一致。

## 14. 可观测性、运行记录和输出文件

`TraceRecorder` 为每一步写 `NNN_name.json`，内容含 name、seq、created_at、payload，并生成 manifest。SSEManager 将 trace 转 RunEvent；前端当前由 `RunTranscript`、`TraceNodeView`、`GlobalTaskWatcher` 等活动组件展示运行事件；未接入入口的 `ExecutionTimeline` 与 `LiveRunConsole` 已在前端结构治理中移除。

受控历史资产：`storage/traces` 约 751 文件、25 个原始 manifest（本轮测试前），覆盖 assessment、BCR、CN Flow、CPRA、diagnosis、DPIA、EU SCC、PIPIA、SCC、TIA、EO14117；事件包括 facts、retrieval hits、issues、evidence、context pack、chapters、consistency、repair 和少量 llm request/response。`storage/reports` 有 16 份通用审查 DOCX。

局限：manifest 仅 `created_at/event_count/events`，没有 module、task id、最终状态、输入 digest、代码 commit、规则/知识版本、总耗时、token、cost。单个 LLM trace 可带 usage，但未形成每次运行总 token/cost 聚合。InMemoryTaskManager 的状态不持久；cancel 只改状态，不能终止已运行线程。不存在通用 replay 命令；可依据中间 JSON 人工重建部分运行，但不能保证一键重放。

可直接转 Benchmark 的资产：facts/issues/evidence/context_pack JSON、retrieval hits、rule result、chapter output、consistency issues、multi-provider assessment traces、SCC 多企业 traces。使用前必须去除潜在用户数据/凭据、区分测试生成与真实运行，并补充 commit/config/model/knowledge version 标签。

## 15. 测试、样本与 Benchmark 现状

仓库有 78 个 `test_*.py` 文件，覆盖 API、auth、citation、knowledge、RAG、workflow、storage、tasks、trace、各业务模块和通用 review。测试函数统计约 308 个，本轮 pytest 最终收集/执行口径表现为 290 pass + 18 fail + 17 error。

关键失败类别：

1. SCC 5 个 service 测试及 async 流程受 `NameError: uuid is not defined` 阻断（`backend/domains/cn/scc_review/service.py:generate_report`）。
2. CN Flow service/async/v0 失败：`_build_context_pack()` 与 `WorkflowPipeline` 的 `per_issue_rag` 参数不兼容。
3. BCR/CPRA/DPIA/PIPIA/TIA 等 async API 测试预期 200，但现路由要求 auth，返回 401；属于测试与接口契约不一致，不能直接等同业务逻辑失败。
4. v0 DPIA 返回 400，表明 gateway payload 映射与当前 schema 不一致。
5. assessment 两项 prompt/retriever 断言失败。
6. knowledge review 17 个 error 均为 Windows teardown 删除 SQLite temp db 时文件仍占用；功能断言可能已通过，但资源释放有缺陷。

Benchmark 资产不是“只有 demo”：`qa/rag_baseline_v1.json`、`qa/rag_eval_v2.json`、两轮 regression JSON/MD、`qa/baseline/v0_sample_dataset.json` 与 expected outputs；`doc/knowledge/_evaluation` 包含 CN/EU/US retrieval/generation eval JSONL、RAG query CSV、hard negatives；`backend/common/rag/eval.py` 可运行 retrieval/generation eval。

但尚不能称为成熟统一 Benchmark：缺统一数据版本/许可证/去重说明；generation cases 数量小；缺跨模型稳定的人评标注、Claim-level faithfulness、规则路径准确率混淆矩阵、法律时效正确率、成本/延迟、端到端文件质量和人工复核一致性指标。当前更准确为“RAG Benchmark 雏形 + 模块 fixtures/demo/regression cases”。

## 16. 技术文档与代码差异表

| 文档宣称/暗示 | 代码状态 | 运行状态 | 最终认定 | 证据 |
|---|---|---|---|---|
| Streamlit demo 可按 README 启动 | 当前前端为 React/Vite；不存在 `app_streamlit/Home.py` | 未运行 Streamlit | 与文档不一致 | `README.md`；`frontend/package.json`；`frontend/src/main.tsx` |
| 12 模块/完整业务体系 | 后端有 11 业务模块+v0 gateway，前端 10 个任务模板；CN SCC 不在前端模板单列，CN Flow 不在任务模板但在 adapter | 多模块有 trace；全测失败 | 部分确认 | `backend/main.py`；`task-templates.ts`；`module-adapter.ts` |
| 统一 Fact/Issue/Evidence/ContextPack 全平台贯穿 | 公共 schema 存在，但 BCR、PIPIA、TIA、EU SCC、CPRA、review 多用专用 Finding/Gap/DTO | traces 只在部分模块含公共 IR | 与文档不一致/部分实现 | `backend/common/workflow/` 与各模块 schema/service |
| Agentic 系统 | 大量 Agent 实际调用，但多数为单次 LLM JSON 调用+fallback，无自治循环/工具规划 | 有 agent trace | 部分确认 | 各 `agents/*.py`、`.run()` 调用 |
| 修复失败阻断交付 | Pipeline 标记 REPAIR_BLOCKED 后仍执行 renderer | 未见统一阻断测试 | 与文档不一致 | `backend/common/workflow/pipeline.py` |
| EU 路径层 | 只有 EU 功能模块，路径文件标记 TBD | 无统一 EU path API | 仅文档规划 | `doc/addition/01_pathway_layer/03_eu_pathway_tbd/README.md` |
| 可稳定运行 | 290 tests pass，但 18 fail/17 error | 当前全量测试不通过 | 与稳定可用描述不一致 | 本轮 pytest |
| CN Flow 为中国数据流检查 | service/Schema 如此命名，但通用 LLM system prompt 是 EO 14117 | 当前 service 参数断链 | 与文档/模块语义不一致 | `module_generator.py:SYSTEM_PROMPTS['cn_flow']`；CN Flow test failure |
| 完整可追溯引用 | 有 Registry/marker/map/audit，但无 ClaimItem，跨模块不统一 | 部分历史产物可回溯 | 部分确认 | `backend/common/citation/`；全仓无 ClaimItem |

## 17. 已实现 / 部分实现 / 未实现能力矩阵

| 能力 | 状态 | 说明 |
|---|---|---|
| 中国出境确定性路径规则 | 部分实现 | 真实可测；无规则版本/有效期；unknown 可被 Agent/启发式改写 |
| EO 14117 红黄绿判断 | 部分实现 | 规则+Agent+IR+报告均有；不是统一路径层 |
| EU 统一路径判断 | 仅文档规划 | 前端直接选功能模块 |
| 安全自评估报告 | 部分接入 | 公共 IR/引用/内外报告/repair 较完整；测试仍有 2 失败 |
| 通用合同审查 | 部分接入 | 独立持久化链和历史 DOCX；未统一到公共 workflow |
| CN SCC | 部分接入/当前不可运行 | 代码流程丰富，但 `uuid` 断链导致核心测试失败 |
| EU SCC/BCR/DPIA/TIA | 部分接入 | 服务与测试/trace 均有；async 鉴权与统一审计不足 |
| PIPIA/CPRA | 部分接入 | 服务、规则/Agent、报告存在；公共 IR 覆盖有限 |
| CN Flow | 部分接入/当前不可运行 | 参数断链且 prompt 法域错误 |
| Fact/Issue/Evidence/ContextPack | 部分接入 | 核心公共 schema 真实存在，非全模块 |
| ClaimItem/统一 RuleItem | 未实现 | 无类定义 |
| 混合 RAG | 部分实现 | 哈希向量+词法+RRF+启发式重排；非神经 embedding/reranker |
| 引用注册与 citation map | 部分实现 | 核心机制真实；跨模块不统一 |
| 自动 Verifier/修复循环 | 部分实现 | 确定性+LLM checks；通常单轮，无统一硬阻断 |
| 运行 trace/timeline | 部分实现 | JSON+SSE+前端展示；缺总成本、版本、状态、replay |
| 文件交付 | 已确认实现 | DOCX/MD/PDF/XLSX/JSON/ZIP 依模块；历史受控报告主要为 review DOCX |
| Benchmark | 部分实现 | 有 RAG/v0 baseline 和 eval 脚本；非统一产品 Benchmark |
| Docker/生产部署 | 未实现/未确认 | 仓库无部署清单 |

## 18. 当前主要技术债和断链

### 18.1 已由运行确认

- `backend/domains/cn/scc_review/service.py` 缺少 `import uuid`，SCC 主链直接失败。
- `CNFlowService._build_context_pack()` 与 `WorkflowPipeline.run()` 参数契约不一致。
- v0 gateway 对 DPIA payload 映射失败；支持模块集合也不完整。
- 异步 API 鉴权契约与多模块测试不一致。
- knowledge review 测试未释放 SQLite 资源，Windows 下 teardown error。
- assessment prompt context/retriever query 有两项回归断言失败。

### 18.2 由代码确认

- CN Flow system prompt 错配 EO 14117，可能造成法域污染。
- `runtime_settings.py` 内置外部 API 凭据；环境配置与 runtime JSON 双源。
- 多套诊断 API、Schema、任务模型、Agent base、引用和报告类型并存。
- InMemoryTaskManager 不持久、cancel 不实际停止线程、进程重启丢状态。
- trace manifest 缺运行身份、代码/规则/知识/模型版本、耗时/成本/终态。
- 规则版本和法条有效期没有统一执行约束。
- 无 ClaimItem，无法完成最终文本 claim-level unsupported/faithfulness 验证。
- 公共 repair “block”不真正阻止 renderer。
- README、pyproject 描述、前端实际架构不一致；仓库包含大量历史 archive/tmp/运行产物。

## 19. 可直接用于比赛展示的真实能力

在不夸大稳定性的前提下，可展示：

1. React 工作台中的多法域任务选择、结构化输入、异步执行时间线、资源/报告中心。
2. 中国出境路径首次命中规则、法律依据、unknown/Agent 辅助说明（应同时展示其边界）。
3. 安全自评估或 EO 14117 的 Fact→Issue→Evidence→ContextPack→章节→检查→文件链路，以及 trace JSON。
4. 分层知识库（法律证据、业务规则、标准条款、模板、测试案例）和 production usage guard。
5. CitationRegistry、脚注、citation map、法规详情 drawer。
6. 通用文档审查的条款级问题、建议修订和 annotated DOCX 历史产物。

比赛前必须避开或先修复 SCC、CN Flow 当前断链，并明确演示是否使用真实 LLM/DeliLegal 或 fallback。

## 20. 可直接用于理论研究和 Benchmark 的现有资产

- `doc/knowledge/normalized/regulation_articles.jsonl`、source registry/catalog：法规条款、来源、状态和有效期元数据。
- `storage/rag/v3/*.jsonl`：按法域/层级构建的 chunk corpus；适合检索消融与污染隔离实验。
- `doc/knowledge/_evaluation/*`：query、hard negative、CN/EU/US retrieval/generation cases。
- `qa/rag_eval_v2.json` 与 regression：已有回归基线。
- `qa/baseline/v0_sample_dataset.json`、expected outputs：可转 Gold Cases，但数量和覆盖有限。
- `storage/traces/*`：过程监督、错误分析、Agent/fallback/模型比较素材。
- 公共 Fact/Issue/Evidence/ContextPack schema：适合结构化标注原型。
- 多模块 tests 与 fixtures：适合构建规则边界、输入缺失、API contract regression。

直接用于论文/公开 Benchmark 前需完成：来源授权核查、PII/商业材料脱敏、重复样本清理、生成数据/真实数据标识、版本冻结、gold 标注与双人复核。

## 21. 后续最需要补充验证的问题

1. 在修复已知断链后，逐模块使用**无外部服务、真实 LLM、真实 DeliLegal**三种配置做端到端对照；本轮未改代码，故未完成。
2. 前端浏览器全流程、文件上传/预览/下载、SSE 断线恢复和登录态尚未做 E2E。
3. `storage/runtime_settings.json` 当前实际 provider 是否有效、外部 API 凭据是否仍可用，本轮未发起网络调用。
4. 历史 traces 中哪些来自真实用户、开发 demo、pytest 或多模型实验，缺统一 provenance，需人工确认。
5. 170 个原始知识文件与 normalized/article index 的覆盖率、解析损失、法规现行性尚需单独数据审计。
6. 中国路径阈值/豁免顺序及 EO14117/CPRA/BCR/TIA 静态规则的法律有效性需由法律专家按版本复核；本文只确认代码事实。
7. 报告 citation 的 claim-level entailment、引用跳转完整率、外部/内部视图隔离需建立可量化测试。
8. 当前 SQLite 数据库中的历史任务/审计日志是否可与文件 traces 一一对应，尚未建立关联核验。

## 22. 项目事实基线结论

当前 DataComplyFlow 已超出概念性 demo：具有真实多模块 API、React 工作台、规则与 LLM 混合处理、结构化中间产物、分层本地法律知识库、引用注册、报告文件和可观测 trace。其最有研究与产品价值的基础是公共 Fact/Issue/Evidence/GenerationContextPack 思路、分层知识使用策略、法规条款索引与丰富历史运行资产。

同时，它还不是一个统一、稳定、可证明正确的 Legal Agent 平台。模块间存在多套实现，Agent 多为单次 LLM 专家调用，Claim/Rule 统一层缺失，规则时效和引用 faithfulness 没有平台级约束，任务/trace/replay 也不完整。本轮实测进一步证明当前主干存在 SCC、CN Flow、v0 gateway、鉴权测试契约和 Windows 资源释放等断链。

因此事实基线应表述为：**一个已具备可运行组件、真实输出和研究资产，但集成一致性与验证闭环尚未完成的证据约束型、规则引导型、可审计 Legal Agentic RAG 工作台原型。** 后续开发、比赛、论文或 Benchmark 应以本文件列出的“已确认/部分确认/未确认”边界为起点，不应直接采用规划文档中的完整能力叙述。

---

### 证据索引（关键文件）

- 入口与路由：`backend/main.py`、`backend/app.py`、`backend/api/v0/router.py`、`backend/api/v1/router.py`、`frontend/src/main.tsx`、`frontend/src/App.tsx`、`frontend/src/lib/module-adapter.ts`
- 模块选择：`frontend/src/lib/task-templates.ts`
- 公共 IR/流水线：`backend/common/workflow/`
- LLM：`backend/common/llm/client.py`、`backend/common/llm/module_generator.py`
- RAG/知识：`backend/common/rag/`、`backend/common/knowledge/`、`doc/knowledge/`、`storage/rag/`
- 引用与 trace：`backend/common/citation/`、`backend/common/trace/`、`storage/traces/`
- 规则：`backend/domains/cn/transfer_diagnosis/decision_tree.json`、各模块 `rule_engine.py`/`gap_rules.py`/rulebook
- 测试与评测：`backend/**/test_*.py`、`qa/`、`doc/knowledge/_evaluation/`
- 部署与配置：`pyproject.toml`、`.env.example`、`backend/core/settings.py`、`backend/core/runtime_settings.py`、`backend/core/db.py`
