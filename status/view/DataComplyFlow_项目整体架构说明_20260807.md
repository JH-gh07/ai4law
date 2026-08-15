# DataComplyFlow 项目整体架构说明

> 生成日期：2026-08-07 · 基于 `new` 分支 HEAD 状态
> 最近更新：2026-08-13 · 同步 task061–task069 落地后的最新代码事实（harness 迁出 tests、统一三格式渲染、JP/KR 来源隔离、11 模块口径、全量测试数）

---

## 一、项目概览

**DataComplyFlow** 是一个多法域数据合规自动化平台，核心能力是：用户上传申报材料 → 系统诊断合规路径 → LLM 驱动的 Agent 流水线生成合规报告 → 多格式导出（DOCX / PDF / Markdown / ZIP）。

**技术栈：**
- **后端**：Python 3.11+ / FastAPI / SQLAlchemy + SQLite / Pydantic v2 / python-docx / openpyxl / jinja2
- **前端**：React 18 + TypeScript / React Router v7 / Vite / react-markdown / framer-motion
- **LLM 接入**：类 OpenAI 兼容 API（通过 provider_registry 支持多模型路由）
- **RAG 检索引擎**：自研混合检索引擎（语义向量 + BM25 全文 + 重排序 + 多索引编排）

**当前支持法域与模块（11 个业务模块，以 `config/module_registry.json` 为准）：**

| 法域 | 模块 key | 功能 |
|------|----------|------|
| 🇨🇳 中国 | `diagnosis` | 合规路径诊断（安全评估 / 标准合同 / 认证） |
| 🇨🇳 中国 | `assessment` | 数据出境安全评估报告（8 章外评 + 3 节官方） |
| 🇨🇳 中国 | `review` | 文档智能审查（SQLite 持久化专项流水线） |
| 🇨🇳 中国 | `pipia` | 个人信息保护影响评估（PIPIA） |
| 🇨🇳 中国 | `cn_flow` | 中国数据出境流程审查（EO 14117 流量向映射，包位于 `us/`） |
| 🇪🇺 欧盟 | `eu_scc` | 欧盟标准合同条款（SCC）审核 |
| 🇪🇺 欧盟 | `bcr` | 有约束力的公司规则（BCR）审核 |
| 🇪🇺 欧盟 | `dpia` | 数据保护影响评估（DPIA） |
| 🇪🇺 欧盟 | `tia` | 传输影响评估（TIA） |
| 🇺🇸 美国 | `us_14117` | EO 14117 数据安全审查 |
| 🇺🇸 美国 | `cpra` | 加州隐私权法案（CPRA）合规 |

> 注：`cn.scc_review` 已退役，不再计入；模块口径以 `config/module_registry.json`（11 个）与 `case_inventory.json`（26 CLI 案例 / 603 断言 / 28 前端案例）为准。

---

## 二、系统整体架构（分层示意）

```
┌─────────────────────────────────────────────────────────────┐
│                    浏览器前端 (React 18 + TS)                  │
│  ┌───────┐ ┌─────────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ Pages │ │ Components  │ │ Features │ │ Lib (state,   │  │
│  │ 12页  │ │ 9组件目录    │ │ 2 feature │ │  auth, domain)│  │
│  └───────┘ └─────────────┘ └──────────┘ └───────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/REST + WebSocket (SSE)
┌──────────────────────┴──────────────────────────────────────┐
│                    FastAPI 后端服务                            │
│                                                               │
│  ┌──────────┐  ┌───────────┐  ┌────────────────────────┐    │
│  │  api/v0  │  │  api/v1   │  │  /health               │    │
│  │ (兼容)   │  │ (主 API)  │  │                        │    │
│  └────┬─────┘  └─────┬─────┘  └────────────────────────┘    │
│       │              │                                        │
│  ┌────┴──────────────┴──────────────────────────────────┐   │
│  │                 core/AppContainer (DI 容器)            │   │
│  │  Settings → Engine → SessionFactory                    │   │
│  │  LLMClient / FileService / ReportService / ...        │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                     │
│  ┌──────────┐  ┌────────┴───────┐  ┌──────────────────┐    │
│  │ domains/ │  │   harness/     │  │   services/       │    │
│  │ (业务域) │  │ (CLI 白盒执行器)│  │   (跨域服务)      │    │
│  └──────────┘  └────────────────┘  └──────────────────┘    │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  common/ (公共基础设施)                 │   │
│  │  citation │ events │ knowledge │ llm │ rag │ render  │   │
│  │  reporting│ quality│ risk      │ runtime│ schema   │   │
│  │  storage  │ tasks  │ trace     │ workflow │ obs    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ models/     │  │ repositories/│  │ integrations/     │   │
│  │ (ORM 模型)  │  │ (数据访问)    │  │ (DeliLegal API)  │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、后端分层详解

### 3.1 入口层 — `backend/app.py` + `backend/main.py`

- `main.py`：`from backend.app import create_app; app = create_app()` — 供 uvicorn 挂载
- `app.py` — `create_app()`：
  1. 读取 `Settings`（环境变量 / `.env`）
  2. 加载运行时覆写 `runtime_settings.json`
  3. 构造 `AppContainer`（DI 容器，持有全部核心依赖）
  4. 创建 FastAPI 实例，挂载 v0 和 v1 路由
  5. `lifespan`：启动时初始化数据库表，启动 SSE 事件后台清理协程

### 3.2 核心容器 — `backend/core/`

| 文件 | 作用 |
|------|------|
| `settings.py` | 配置类 `Settings`，从环境变量 / `.env` 读取全部配置项（DB URL、LLM API key、上传目录等） |
| `container.py` | `AppContainer` — 手工 DI 容器，初始化 Engine、SessionFactory、LLMClient、FileService、ReportService、WebSocketManager、TaskDispatcher 等全部单例 |
| `db.py` | `init_db()` — SQLAlchemy `Base.metadata.create_all()`，启动建表 |
| `dependencies.py` | FastAPI 依赖注入（`get_db` / `get_container` / 当前用户解析等） |
| `resource_paths.py` | 仓库资源与基准数据集的规范路径解析（模板、法律数据、`benchmarks/datasets` 等） |
| `runtime_settings.py` | 运行时动态覆写 Settings（不重启服务即可切换 LLM provider 等） |
| `release_info.py` | 版本/发布信息 |
| `json_utils.py` | JSON 序列化工具（Pydantic/枚举安全序列化等） |
| `time.py` | 显式 UTC 时区时间戳工具 |

> 说明：JWT 令牌生成/验证与密码哈希已移到 `backend/services/auth_service.py`，WebSocket 连接管理在 `backend/services/websocket_manager.py`（两者均不在 `core/`）。

### 3.3 HTTP API 层 — `backend/api/`

**v0（兼容层）：**
- `v0/router.py` + `v0/task_gateway/`：旧版任务网关，按 `module_key` 分发到对应模块运行器

**v1（主 API）：13 个端点文件 + 11 个业务模块路由**

| 端点 | 文件 | 功能 |
|------|------|------|
| `/auth/*` | `endpoints/auth.py` | 注册/登录/JWT 鉴权 |
| `/me/*` | `endpoints/me.py` | 当前用户信息、任务列表、工作区恢复 |
| `/artifacts/*` | `endpoints/artifacts.py` | 产物上传/下载/预览 |
| `/citations/*` | `endpoints/citations.py` | 引用数据查询 API |
| `/copilot/*` | `endpoints/copilot.py` | AI 辅助对话 |
| `/diagnosis/*` | `endpoints/diagnosis.py` | 合规路径诊断 API |
| `/reports/*` | `endpoints/reports.py` | 报告元数据查询 |
| `/workspace-state/*` | `endpoints/workspace_state.py` | 前端工作区状态持久化（taskSpaces、artifacts、runs） |
| `/knowledge/*` | `endpoints/knowledge.py` | 知识库管理（文档上传、检索） |
| `/knowledge/review/*` | `endpoints/knowledge_review.py` | 知识审核 |
| `/events/*` | `endpoints/events.py` | SSE 事件流（模块运行进度推送） |
| `/system/*` | `endpoints/system_settings.py` | 系统设置 |
| `/version/*` | `endpoints/version.py` | 版本信息 |

**业务模块路由：** 每个 `domains/` 下的业务模块通过自己的 `router.py` 暴露 `/run`、`/run/async` 等端点，由 `v1/router.py` 统一挂载。

### 3.4 公共基础设施 — `backend/common/`

这是项目最核心的复用层，共 16 个子包（`citation` / `events` / `knowledge` / `llm` / `observability` / `quality` / `rag` / `render` / `reporting` / `risk` / `runtime` / `schema` / `storage` / `tasks` / `trace` / `workflow`）：

#### 3.4.1 `common/citation/` — 引用系统（本次 P0 治理的核心）

| 文件 | 作用 |
|------|------|
| `models.py` | `CitationItem` 数据模型：citation_id、source_id、title、article_no、quote_text、confidence_score、authority_level、binding_force、allowed_usage 等 |
| `registry.py` | `CitationRegistry` — 全局引用注册表。LLM 生成报告时每发现一个法规引用即注册，自动分配全局脚注编号 [1][2][3]… |
| `id_generator.py` | `CitationIdGenerator` — 生成形如 `CIT-CN-PIPL-ART39-P01` 的全局唯一引用 ID |
| `locators.py` | 引用定位器 — 将引用映射回原文位置（条文/段落/页码） |
| `audit.py` | 引用审计日志 — 记录每个引用的生成、修改、删除历史到 `citation_audit_log` 表 |
| `module_grounding.py` | 模块级引用落地 — 将 CitationItem 绑定到具体业务模块和任务 |
| `output.py` | 引用输出 — `write_citation_map_json()` 将脚注映射写入 JSON 文件 |
| `tests/` | 7 个测试文件：ID 生成、模型序列化、后处理、URL 标准化、注册表、域路径 |

**数据流：** LLM 生成章节时内嵌 `{{CIT-CN-PIPL-ART39-P01}}` → `CitationRegistry.assign_footnote_number()` 分配 [1] → `postprocess.convert_citation_markers()` 替换标记 → 前端 `CitationMarkdownRenderer` 渲染可交互角标

#### 3.4.2 `common/llm/` — LLM 客户端与后处理

| 文件 | 作用 |
|------|------|
| `client.py` | `LLMClient` — 统一 LLM 调用接口，支持 OpenAI 兼容 API、多 provider（SiliconFlow / DeepSeek / 自定义） |
| `provider_registry.py` | 多 Provider 注册与路由，按模型名自动选择 endpoint |
| `context.py` | LLM 上下文构建器 — 将 facts、regulations、issues、evidence 拼装为 system/user prompt |
| `module_generator.py` | 模块化 LLM 生成器 — 驱动单次 module run 的 prompt→completion 流程 |
| `postprocess.py` | **后处理管道（本次 P0 重点修改）**：<br>• `normalize_legal_markdown_structure()` — 法律文书 Markdown 结构标准化<br>• `_repair_pipeless_tables()` — 补全缺失前导 `\|` 的表格行<br>• `_explode_packed_line()` — 拆解挤在一行里的章/节/条目标题<br>• `strip_markdown_inline()` — 剥离 DOCX 不需要的行内格式<br>• `apply_citation_policy()` — 引用合规策略门：检查高风段落是否遗漏法规依据<br>• `convert_citation_markers()` — 将 `{{CIT-xxx}}` 转为 `[1][2]` 脚注 |
| `snapshot.py` | LLM 调用快照存档 |
| `tests/` | 3 个测试文件：引用策略修复（P0-7）、后处理断行、客户端追踪 |

#### 3.4.3 `common/knowledge/` — 知识库引擎

| 文件 | 作用 |
|------|------|
| `models.py` | 知识文档/分块/检索结果的 Pydantic 模型 |
| `document_parser.py` | 文档解析器：PDF / DOCX / TXT → 结构化文本 |
| `chunker.py` | 文本分块器：按章/条/款的中国法律层级结构智能切分 |
| `chinese_legal_patterns.py` | 中国法律文书的正则模式库（"第X条""第X章"等） |
| `ingestion_pipeline.py` | 文档摄入管道：解析 → 分块 → 向量化 → 入库 |
| `storage_manager.py` | 知识库文件存储管理（支持 S3 / 本地） |
| `registry.py` | 知识库注册表 — 记录已摄入文档的元数据 |
| `paths.py` | 知识库文件路径解析 |
| `builders_v2.py` | 知识库索引构建器 v2 |
| `v2.py` | 知识库 API v2 入口 |
| `usage_policy.py` | 知识使用策略 — 限制哪些知识可用于哪些模块的外部报告 |

#### 3.4.4 `common/rag/` — 混合检索引擎

| 文件 | 作用 |
|------|------|
| `embedding.py` | 文本向量化（调用 embedding API） |
| `vector_store.py` | 向量存储（内存 / ChromaDB） |
| `fulltext_index.py` | BM25 全文索引 |
| `retriever.py` | 单索引检索器 — 语义向量检索 |
| `hybrid_retriever.py` | 混合检索器 — 向量 + BM25 加权融合 |
| `reranker.py` | 重排序器 — 对检索结果二次精排 |
| `orchestrator.py` | 多索引编排器 — 同时检索法律库、政策库、案例库并合并去重 |
| `ingest.py` | 索引摄入 — 将文档分块写入向量库和全文索引 |
| `service.py` | RAG 服务门面 — 对上层暴露统一检索接口 |
| `constants.py` | 常量（集合名称、权重等） |

**检索流程：** 用户问题 → HybridRetriever（向量+BM25） → Reranker 重排 → Orchestrator 多库合并 → Top-K 结果返回

#### 3.4.5 `common/render/` — 报告渲染引擎

| 文件 | 作用 |
|------|------|
| `report.py` | 核心渲染工具：`render_markdown_template()` / `render_docx_template()` — Jinja2 模板填充 |
| `summary.py` | 摘要生成：`summarize_for_slot()` / `dedup_if_same()` / `attach_citations()` |
| `markdown_renderer.py` | Markdown 渲染器 — 章节内容 → 格式化 Markdown |
| `content_adapter.py` | 内容适配器 — 章节列表 → 统一文档模型 |
| `pdf_renderer.py` | PDF 渲染器（基于 markdown → HTML → PDF 管道） |
| `artifacts.py` | 产物打包器 — 将报告、证据、问题清单打包为 ZIP |

#### 3.4.6 `common/reporting/` — 统一三格式同源渲染（task067 / task068 新增）

> 这是 2026-08 中旬引入的统一渲染层，解决各模块 Markdown/DOCX/PDF 三格式"各自渲染、排版失真"的问题。与 `common/render/` 的关系：`render/` 提供底层渲染原语（markdown/docx/pdf 转换器 + 模板），`reporting/` 提供**统一 IR → 三格式**的上层编排（render manifest + render profile + renderer registry）。

| 文件/目录 | 作用 |
|------|------|
| `render_manifest.py` | 渲染清单（RenderManifest）——声明式描述"哪个模块 / 哪个产物 / 用哪个 profile / 输出哪三种格式"，单源驱动渲染 |
| `render_profiles/` | 渲染画像——按模块（bcr / 文档审查 / 多模块）区分的排版规则、字段映射与格式参数 |
| `renderers/` | 渲染器注册表——markdown / docx / pdf 渲染器实现，统一入口 |
| `schema/` | 渲染 IR 的 Pydantic schema |
| `compiler/` | IR 编译器——把各模块中间结果编译为统一 Document IR |
| `shadow_render.py` | 影子渲染——新旧渲染链路对拍，用于回归验证 |
| `layout_gate.py` | 排版门禁——校验三格式输出的版式合规性 |
| `migration.py` / `compat.py` | 旧渲染 API 的迁移与兼容层 |
| `tests/` | 渲染器测试（markdown/docx/pdf/manifest/migration） |

#### 3.4.7 其它 common 子包

| 子包 | 核心文件 | 功能 |
|------|---------|------|
| `common/events/` | `manager.py`, `store.py` | SSE 事件管理器 — 模块运行进度实时推送到前端，支持持久化事件日志 |
| `common/workflow/` | `context_pack.py`, `evidence.py`, `facts.py`, `issues.py` | 工作流上下文包 — **GenerationContextPack** 是跨 Agent 的数据传输对象，包含 facts、issues、diagnosis_result、regulations、risk_summary 等 |
| `common/quality/` | `markdown_lint.py`, `alignment.py` | 质量门 — `markdown_lint.py`（本次 P0 新增，9 条规则 L1-L9，内外报告双 profile，尚未接入调用方）；`alignment.py`（事实对齐检查） |
| `common/risk/` | 风险管理模块 | 风险评估通用逻辑 |
| `common/runtime/` | 运行时动态配置 | 支持不重启服务切换 LLM provider |
| `common/schema/` | 共享 Schema | 跨模块共用的 Pydantic 模型 |
| `common/storage/` | 文件存储抽象 | 本地/S3 统一存储接口 |
| `common/tasks/` | 任务调度 | 异步任务执行框架 |
| `common/trace/` | 链路追踪 | 请求追踪与日志关联 |
| `common/observability/` | 可观测性 | 日志/指标/健康检查 |
| `common/templates/` | Jinja2 模板 | 报告模板文件 |

### 3.5 业务域 — `backend/domains/`

每个业务域（中国/欧盟/美国）包含多个业务模块，每个模块遵循统一结构：

```
domains/{jurisdiction}/{module}/
├── __init__.py          # 模块入口，暴露 MODULE_KEY 等常量
├── router.py            # FastAPI 路由（/run, /run/async）
├── schema.py            # 模块专属 Pydantic 模型（请求/响应/内部结构）
├── service.py           # 业务逻辑编排（调用 module_generator + agents）
├── renderer.py / *_generator.py  # 报告渲染器
├── agents/              # 模块专属 LLM Agent prompt 模板
│   ├── field_analyst_agent.py
│   ├── risk_assessor_agent.py
│   └── ...
└── tests/               # 模块测试
```

**以 `cn/security_assessment`（中国安全评估）为例——最复杂模块、本次 P0 重点治理对象：**

| 文件 | 行数 | 功能 |
|------|------|------|
| `__init__.py` | ~20 | 导出 `MODULE_KEY = "cn.security_assessment"` |
| `router.py` | ~80 | 暴露 `/run`（同步）/ `/run/async`（异步 SSE）两个端点 |
| `schema.py` | ~250 | `CompanyProfile`（企业画像 10+ 字段）、`RegulationHit`（法规命中）、`ChapterContent`（章节内容含 citations 和 risk_level）、`SecurityAssessmentPayload`（完整申报载荷）等 Pydantic 模型 |
| `report_renderer.py` | ~700 | **AssessmentReportRenderer**：编排整份报告生成——内部报告（8 章）+ 官方外发报告（3 节）+ DOCX/PDF/Markdown/ZIP 多格式导出。render() 接收 context_pack 后调用 build_official_report_mapping() |
| `external_report_generator.py` | ~250 | **官方报告生成器**：`build_official_report_mapping()` — **P0-1** 强制要求 context_pack 参数；**P0-5** 使用 `used_chapter_ids` 共享集合实现章节去重 |
| `internal_review_generator.py` | ~150 | 内部审核报告生成 |
| `compliance_reasoning.py` | ~100 | 合规推理标注生成 |
| `chapter_generator.py` | ~500 | **章节生成器**：**P0-2** `_resolve_risk_level()` 从 context_pack.risk_summary 单源解析风险等级；**P0-6** 移除全局 HIGH/BLOCKER 回退 |
| `agents/` | ~10 文件 | LLM Agent 的 system prompt 模板（field_analyst、risk_assessor、remediation_advisor 等） |

### 3.6 CLI 白盒执行器 — `backend/harness/`（原 `backend/tests/harness/` 实现迁出）

> `backend/modules/` 层已退役并移除（模块执行逻辑早已并入 `backend/domains/*/service.py`）。当前的"模块 CLI 运行"统一收敛到 `backend/harness/`：

```
backend/harness/
├── __init__.py
├── runner.py            # 白盒执行器：进程内 import 各模块 service+schema，直接调用主方法
├── validators.py        # 声明式断言器（11 个操作符，校验 expected.json）
├── viewer.py            # 运行汇总与事件查看 CLI
├── terminal_trace.py    # 逐事件 trace 终端订阅器
└── README.md            # CLI 输入/输出详解
```

**关键设计（2026-08-13 task069 迁出）：**
- 实现代码从 `backend/tests/harness/` 迁出到 `backend/harness/`，`backend/tests/harness/` 只保留 `test_*.py` 测试。
- 生产门禁 `scripts/check_case_parity.py` 由 `from backend.tests.harness.validators import ...` 改为 `from backend.harness.validators import ...`，不再反向依赖 `tests/`。
- 入口命令：`python -m backend.harness.runner <module> [case_id] [--no-llm] [--quiet] [--verbose-trace]`（CI 已同步）。
- `v0_task_gateway/` 是旧版任务网关分发器（`backend/api/v0/task_gateway/`），按 `module_key` 分发；v1 路由通过 domains 层直接暴露端点，不再经过 v0 gateway。

### 3.7 数据层 — `backend/models/` + `backend/repositories/` + `backend/schemas/`

**三层数据架构：**

| 层 | 目录 | 技术 | 作用 |
|---|------|------|------|
| 接口 Schema | `schemas/` | Pydantic v2 | API 请求/响应的类型定义与校验 |
| 领域 Schema | `domains/*/schema.py` | Pydantic v2 | 业务领域内部模型（CompanyProfile、ChapterContent 等） |
| ORM 模型 | `models/` | SQLAlchemy | 数据库表映射（users、tasks、reports、workspace_states、citation_audit_log 等 13+ 表） |
| 数据访问 | `repositories/` | SQLAlchemy Session | 封装数据库 CRUD 操作 |

### 3.8 跨域服务 — `backend/services/`

| 文件 | 作用 |
|------|------|
| `file_service.py` | 文件上传/下载/存储管理 |
| `report_service.py` | 报告元数据查询与管理 |
| `session_service.py` | 用户会话管理 |
| `diagnosis_session_service.py` | 诊断会话编排（调用 diagnosis runner + 报告生成） |
| `task_dispatcher.py` | 异步任务分发器（线程池 / 后台执行） |
| `runtime_client_refresher.py` | 运行时 LLM Client 热刷新 |
| `review_service/` | 文档审核子服务（含 `agents/` 和 `specialized_reviewers/`） |
| `auth_service.py` | JWT 令牌生成/验证、密码哈希（原 `core/security.py` 迁移至此） |
| `websocket_manager.py` | WebSocket 连接管理（原 `core/websocket_manager.py` 迁移至此） |
| `artifact_registry.py` | 产物注册表 |
| `knowledge_index.py` | 知识索引服务 |
| `knowledge_projection.py` | 知识投影（Evidence Center 前端展示投影，含来源隔离/引用策略） |
| `runtime_health.py` | 运行时健康检查 |
| `task_access.py` | 任务访问控制 |

### 3.9 外部集成 — `backend/integrations/`

| 文件 | 作用 |
|------|------|
| `delilegal.py` | DeliLegal 法律数据 API 客户端 — 查询法规条文、案例、政策问答 |
| `tests/` | 集成层测试 |

---

## 四、前端分层详解

### 4.1 页面层 — `frontend/src/pages/`（12 页）

| 页面 | 文件 | 路由 | 功能 |
|------|------|------|------|
| 首页 | `HomePage.tsx` | `/` | 快速开始、任务入口 |
| 法域中心 | `JurisdictionHubPage.tsx` | `/jurisdictions/:code` | 按国家/地区浏览合规模块 |
| 登录 | `auth/LoginPage.tsx` | `/login` | 用户登录 |
| 注册 | `auth/RegisterPage.tsx` | `/register` | 用户注册 |
| 任务空间 | `TaskSpacesPage.tsx` | `/tasks` | 任务列表管理 |
| 工作区 | `WorkspacePage.tsx` | `/workspace/:taskId` | 核心工作区——报告生成、中间产物浏览、引用查看 |
| 报告中心 | `ReportCenterPage.tsx` | `/reports` | 历史报告浏览 |
| 知识库中心 | `EvidenceCenterPage.tsx` | `/evidence` | **知识库目录浏览器**——展示全部 69 个法规来源（搜索/筛选/条文检索），点击法律以 React state 切换显示，**URL 始终不变**；页面内含指向 LawViewerPage 的条文深链接 |
| 法规条文查阅 | `LawViewerPage.tsx` | `/knowledge/laws/:sourceId` | **单法规深链接视图**——URL 驱动，支持 `?article=N` 精确定位条文；**引用跳转的落地页**，并非用户日常浏览知识库的主界面 |
| 文档 | `DocsPlaceholderPage.tsx` | `/docs` | API 文档占位 |
| 设置 | `SettingsPage.tsx` | `/settings` | 系统设置 |
| 个人中心 | `ProfilePage.tsx` | `/profile` | 个人信息管理 |

### 4.2 核心组件 — `frontend/src/components/`

#### 4.2.1 引用组件 — `components/citation/`（本次 P0 验收对象）

| 文件 | 行数 | 功能 |
|------|------|------|
| `CitationMarkdownRenderer.tsx` | 381 | 引用 Markdown 渲染器——解析 `{{CIT-xxx}}` 标记和 `[n]` 脚注，渲染为可交互蓝色角标 |
| `CitationPopover.tsx` | 112 | 悬浮卡片——hover 角标展示：法规名称、强制性/参考性标签、条文摘要 |
| `CitationArticleDrawer.tsx` | 184 | 条文抽屉——点击角标从右侧滑出完整法律条文原文 |
| `CitationMarkdownRenderer.test.tsx` | ~100 | 组件测试（3 文件 5 测试全部通过） |

**三层交互链：** 报告正文蓝色角标 `[1]` → hover 出悬浮卡（法规名+条文摘要）→ click 打开右侧条文抽屉（完整法律文本）

#### 4.2.2 工作区组件 — `components/workspace/`

| 文件 | 功能 |
|------|------|
| `WorkspaceShell.tsx` | 工作区主框架——Tab 切换（详情/画布/文档/终端/报告/时间线）、报告预览、产物管理面板 |
| `WorkspacePage.tsx` | 工作区页面壳 |
| `AssessmentIntermediatesPanel.tsx` | 评估中间产物面板——展示生成过程中的 facts/issues/evidence 等中间数据 |
| `GlobalTaskWatcher.tsx` | 全局任务监听器——监控后台异步任务状态 |
| `StageSplitView.tsx` | 阶段分屏视图——报告生成的阶段进度可视化 |
| `ReportPreview.tsx` | 报告预览组件 |
| `CreateWorkspaceModal.tsx` | 新建工作区模态框 |

#### 4.2.3 其它组件目录

| 目录 | 内容 |
|------|------|
| `common/` | TopNav（顶栏导航）、LazyRouteErrorBoundary、语言切换器等通用 UI |
| `auth/` | ProtectedRoute（认证路由守卫） |
| `landing/` | 首页落地页组件 |
| `modals/` | CreateWorkspaceModal、ModeSelectModal、QuickStartModal 等模态框 |
| `onboarding/` | 新手引导覆盖层 |
| `report-center/` | 报告中心卡片/列表 |
| `report/` | **统一三格式报告渲染组件（task068 新增）**：`ReportDocumentView.tsx`（报告文档视图）、`ClauseTree.tsx`（条款树）、`FindingView.tsx`（发现视图） |

### 4.3 功能模块 — `frontend/src/features/`

| 目录 | 功能 |
|------|------|
| `module-runner/` | 模块执行器——触发后端 LLM 生成任务、监听 SSE 进度事件、管理运行状态 |
| `module-runner/payload-builders/` | 按模块类型构建不同的 API 请求载荷（assessment / diagnosis / dpia 等各有 builder） |
| `resource-explorer/` | 资源浏览器——输入资源/输出产物的路径树、配置与契约（`path-tree.ts` / `input-resources.ts` / `output-artifacts.ts` 等） |

### 4.4 状态与基础设施 — `frontend/src/lib/`

| 文件 | 功能 |
|------|------|
| `app-store.tsx` | **全局状态管理**（React Context + useReducer）——管理 taskSpaces、moduleRuns、artifacts、evidenceHits、issues；启动时从后端 `/me/workspace` 拉取远程状态并与本地 localStorage 合并 |
| `auth/AuthContext.tsx` | JWT 认证上下文 |
| `domain.ts` | 法域/模块类型定义（Jurisdiction、LaunchMode 等枚举） |
| `language.ts` | 多语言（中/英）切换 |
| `task-templates.ts` | 任务模板定义——每个法域的预设工作流配置 |

### 4.5 API 层 — `frontend/src/api/`

| 目录 | 内容 |
|------|------|
| `generated/` | 从 OpenAPI 规范自动生成的 TypeScript 类型和 API 客户端 |
| 各业务模块 API 文件 | 对后端 REST 接口的封装调用 |

---

## 五、核心数据流（以中国安全评估为例）

```
用户上传申报材料
      │
      ▼
┌─────────────────────────────────────────────────┐
│ 1. 路径诊断 (diagnosis)                          │
│    └─ transfer_diagnosis/service.py              │
│       └─ 调用 LLM Agent 判断适用路径              │
│       └─ 输出: diagnosis_result                  │
│          {recommended_path, risk_level, rationale}│
└──────────────────────┬──────────────────────────┘
                       │
      ┌────────────────┴────────────────┐
      │ 安全评估   │ 标准合同   │ 认证   │
      └────────────────┬────────────────┘
                       │
      ▼
┌─────────────────────────────────────────────────┐
│ 2. 构建 GenerationContextPack                    │
│    └─ workflow/context_pack.py                   │
│       ├─ facts: [FactItem...]  — 提取的事实       │
│       ├─ issues: [IssueItem...] — 识别的问题      │
│       ├─ regulations: [dict...] — 匹配的法规       │
│       ├─ diagnosis_result — 路径诊断结果          │
│       ├─ risk_summary — P0-2 单源风险等级          │
│       ├─ evidence_chain — 证据链条                │
│       └─ citation_registry — 引用注册表           │
└──────────────────────┬──────────────────────────┘
                       │
      ▼
┌─────────────────────────────────────────────────┐
│ 3. LLM Agent 流水线 (domains/cn/security_assessment/agents/) │
│    └─ field_analyst_agent: 分析事实              │
│    └─ risk_assessor_agent: 评估风险              │
│    └─ remediation_advisor_agent: 生成建议         │
│    └─ 每个 Agent 输出带 {{CIT-xxx}} 标记的章节    │
└──────────────────────┬──────────────────────────┘
                       │
      ▼
┌─────────────────────────────────────────────────┐
│ 4. 后处理 (common/llm/postprocess.py)            │
│    ├─ normalize_legal_markdown_structure()       │
│    │   ├─ _repair_pipeless_tables() — P0-4       │
│    │   └─ _explode_packed_line() — P0-3          │
│    ├─ apply_citation_policy() — P0-7 引用策略门   │
│    └─ convert_citation_markers()                 │
│        └─ {{CIT-xxx}} → [1][2][3] 脚注          │
└──────────────────────┬──────────────────────────┘
                       │
      ▼
┌─────────────────────────────────────────────────┐
│ 5. 报告组装 (report_renderer.py)                 │
│    ├─ _build_template_mapping() — Jinja2 变量映射 │
│    ├─ build_official_report_mapping() — P0-1/0-5 │
│    │   ├─ _resolve_risk_level() — P0-2           │
│    │   └─ used_chapter_ids 去重 — P0-5            │
│    └─ chapter_generator._resolve_risk_level()    │
│        └─ context_pack.risk_summary 单源 — P0-2/6 │
└──────────────────────┬──────────────────────────┘
                       │
      ▼
┌─────────────────────────────────────────────────┐
│ 6. 多格式导出                                    │
│    ├─ Markdown（官方外评 + 内部审核两份）          │
│    ├─ DOCX（Jinja2 + python-docx）               │
│    ├─ PDF（Markdown → HTML → PDF）               │
│    ├─ XLSX（问题清单 + 证据链 + 材料清单）          │
│    └─ ZIP（全部产物打包）                          │
└──────────────────────┬──────────────────────────┘
                       │
      ▼
┌─────────────────────────────────────────────────┐
│ 7. 前端工作区 (WorkspaceShell)                   │
│    ├─ CitationMarkdownRenderer 渲染角标           │
│    ├─ CitationPopover hover 悬浮卡               │
│    └─ CitationArticleDrawer 条文抽屉              │
└─────────────────────────────────────────────────┘
```

---

## 六、关键设计模式与原则

### 6.1 DI 容器（AppContainer）
所有核心依赖在启动时一次性构造，通过 `app.state.container` 注入到各路由处理器。避免全局变量和隐式依赖。

### 6.2 GenerationContextPack（跨 Agent 上下文包）
Pydantic 模型，作为 LLM Agent 流水线各阶段的数据传输对象。包含 15+ 字段，从 facts 原始提取到 citation_registry 引用注册表，贯穿整个生成流程。

### 6.3 引用系统的三层分离
- **标识层**（`citation/models.py`）：CitationItem 数据模型
- **注册层**（`citation/registry.py`）：CitationRegistry 全局注册 + 脚注编号
- **渲染层**（`common/render/` + `frontend/components/citation/`）：从 `{{CIT-xxx}}` 标记到可交互 UI

### 6.4 单源真理（P0-2 / P0-6 设计原则）
风险等级由 `context_pack.risk_summary["risk_level"]` 单一来源决定，`_resolve_risk_level()` 方法统一读取，消除了三处相互竞争的 fallback 逻辑。

### 6.5 模块插件化
新增法域/模块只需（`backend/modules/` 已退役，运行器并入 domains）：
1. `backend/domains/{jurisdiction}/{module}/` 创建域模块（router + schema + service + renderer + agents）
2. `backend/harness/runner.py` 的 `_ADAPTER_DEFINITIONS` 登记模块别名 → 包/请求类/服务类映射（供 CLI 白盒执行器使用）
3. `backend/api/v1/router.py` 注册路由
4. `frontend/src/features/module-runner/payload-builders/` 添加载荷构建器

### 6.6 测试分层

| 测试层级 | 位置 | 数量（2026-08-13） | 工具 |
|---------|------|------|------|
| 单元测试 | `common/*/tests/` | 见全量回归 | pytest |
| 契约测试 | `domains/*/tests/` | 见全量回归 | pytest |
| 集成测试 | `api/*/tests/` | 见全量回归 | pytest + httpx |
| 模块端到端 | `backend/tests/{module}/cases/` | 26 CLI 案例（11 模块） | pytest + JSON fixture |
| Harness 测试 | `backend/tests/harness/` | 88 | pytest |
| 前端测试 | `frontend/src/**/*.test.tsx` | 见前端 vitest | vitest |
| 浏览器 E2E | `benchmarks/` | 11 模块浏览器契约 | Playwright |

**全量后端回归（2026-08-13）：** `pytest backend/` = **1092 passed / 4 failed**。4 个失败均不涉及 harness，集中在 `pipia`（2 个，整改在途：`test_scc_evidence_drives_source_findings`、`test_certification_evidence_drives_path_findings`）、`reporting`（1 个，task068 新增 `test_docx_renderer.py::test_render_is_hash_stable`）与 `scc_review`（1 个，`test_uploaded_scc_document_drives_core_review`）。

---

## 七、P0 已完成修复清单

| 编号 | 修复内容 | 涉及文件 | 测试状态 |
|------|---------|---------|---------|
| P0-1 | context_pack 强制传入官方报告映射 | `external_report_generator.py`, `report_renderer.py` | ✅ |
| P0-2 | 风险等级单源解析 `_resolve_risk_level()` | `chapter_generator.py` | ✅ |
| P0-3 | 断行正则避免拆断 TLS 1.3 | `postprocess.py` | ✅ |
| P0-4 | pipeless 表格自动补全前导 `\|` | `postprocess.py` | ✅ |
| P0-5 | `used_chapter_ids` 共享集合去重 | `external_report_generator.py` | ✅ |
| P0-6 | 移除全局 HIGH/BLOCKER 回退 | `chapter_generator.py` | ✅ |
| P0-7 | 引用策略正则修复（允许跨越逗号） | `postprocess.py` | ✅ |

**测试矩阵（P0 当时）：** 68 passed / 0 failed / 3 skipped
**最新全量（2026-08-13）：** 1092 passed / 4 failed（见 §6.6）

---

## 八、P1 待办事项

| 编号 | 内容 | 涉及层 |
|------|------|--------|
| 1 | `markdown_lint.py` 接入 `report_renderer.py` 调用方 | 后端质量门 |
| 2 | CN-REG-004 条文原文提取（当前仅 9 段网页文本） | 数据层 |
| 3 | CitationRegistry key 去重（同一法条多地引用不应重复注册） | 引用系统 |
| 4 | source URL 回填（引用可追溯至原文链接） | 引用系统 |
| 5 | 前端引用跳转完整链路接入实际 API（当前为演示页面） | 前端 |
| 6 | 复制引用按钮（一键复制法条原文） | 前端 |
| 7 | 新规标签（标注 2024+ 新发布/修订的法规） | 数据层+前端 |

### 8.1 最新进度（2026-08-13，task061–task069 落地）

P0/P1 之后，项目按 `status/todo/` 的 task 序号持续推进。截至 2026-08-13 的关键落地：

| Task | 主题 | 状态 |
|------|------|------|
| task061 | SCC 失败展示根因修复 | ✅ 已落地 |
| task062 | Trace 前端显示修复 | ✅ 已落地 |
| task063 | 工作台目录/文件显示点击修复 | ✅ 已落地 |
| task064 | Evidence Center 重构 | ✅ 已落地 |
| task065 | 全模块本地闭环与生产报告质量整改（含 JP/KR 来源身份隔离与裁决） | 🔶 代码门禁已落地，第三/四阶段待法律专家签署 |
| task066 | 前端本地状态持久化超限与恢复治理 | ✅ 已落地 |
| task067 | BCR 三格式专业排版与统一 IR 渲染 | 🔶 渲染层已落地，回归中 |
| task068 | 文档审查及多模块三格式同源渲染与输入追溯 | 🔶 渲染层已落地，回归中（reporting 4 个失败之一待收敛） |
| task069 | harness 实现代码迁出 `backend/tests/`（`backend/harness/` 实现 + `backend/tests/harness/` 测试） | ✅ 已落地（88 passed，生产门禁 EXIT=0） |

> 说明：JP/KR 来源隔离（task065）的 10 个 source 已标记 `metadata_review_required` 并从正式法律结论/条文号引用中隔离；最终裁决与统一重建按方案待法律专家签署，签署前不推进重建。pipia 的 2 个回归失败与 reporting 的 1 个失败属于整改在途，非 harness 迁移引入。

---

## 九、仓库目录总览

```
ai4law/
├── backend/                  # Python FastAPI 后端
│   ├── api/                  # HTTP API (v0/v1)
│   ├── common/               # 公共基础设施（16 子包）
│   │   ├── citation/         # 引用系统 ⭐
│   │   ├── events/           # SSE 事件
│   │   ├── knowledge/        # 知识库
│   │   ├── llm/              # LLM 客户端与后处理 ⭐
│   │   ├── quality/          # 质量门（markdown_lint）
│   │   ├── rag/              # 混合检索引擎
│   │   ├── render/           # 报告渲染（底层转换器 + 模板）
│   │   ├── reporting/        # 统一三格式同源渲染（task067/068）⭐
│   │   ├── risk/             # 风险评估
│   │   ├── runtime/          # 运行时配置
│   │   ├── schema/           # 共享 Schema
│   │   ├── storage/          # 文件存储
│   │   ├── tasks/            # 任务调度
│   │   ├── trace/            # 链路追踪
│   │   └── workflow/         # 工作流上下文 ⭐
│   ├── core/                 # 核心配置与容器
│   ├── domains/              # 业务域（cn/eu/us × 11 模块）
│   ├── harness/              # CLI 白盒执行器（runner/viewer/validators/terminal_trace）⭐
│   ├── integrations/         # 外部 API
│   ├── models/               # ORM 模型
│   ├── repositories/         # 数据访问层
│   ├── schemas/              # API Schema
│   ├── services/             # 跨域服务
│   └── tests/                # 测试（harness/ 仅放测试，案例在 tests/<module>/cases/）
├── frontend/                 # React 18 + TypeScript 前端
│   └── src/
│       ├── api/              # API 客户端
│       ├── components/       # UI 组件（auth/citation/common/landing/modals/onboarding/report/report-center/workspace）
│       │   ├── citation/     # 引用组件 ⭐
│       │   ├── report/       # 统一三格式报告渲染组件 ⭐
│       │   └── workspace/    # 工作区组件 ⭐
│       ├── features/         # 功能模块（module-runner + resource-explorer）
│       ├── lib/              # 状态管理 & 基础设施
│       └── pages/            # 页面（12 页）
├── resources/                # 模板与静态资源
├── scripts/                  # 运维与开发脚本
├── benchmarks/               # 浏览器 E2E 测试
├── config/                   # 配置文件
├── docs/                     # 设计文档
├── storage/                  # 运行时数据（SQLite DB、上传文件、报告产物）
├── outputs/                  # 历史报告产物（按 taskId 分目录）
├── runs/                     # 运行日志
├── status/                   # 项目状态文档
│   ├── todo/                 # 待实施方案
│   └── check/                # 已落实待复核交付物 ⭐
├── pyproject.toml            # Python 项目配置
└── README.md
```

---

> 本文档由 Claude Code 基于 2026-08-07 `new` 分支代码库自动生成，覆盖 200+ Python 文件和 50+ TypeScript 文件；2026-08-13 已同步 task061–task069 落地后的结构变化（新增 `backend/harness/`、`backend/common/reporting/`，模块口径 10→11）。
