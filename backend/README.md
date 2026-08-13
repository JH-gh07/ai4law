# backend 目录结构与命名规范详解

> 本文件是 `backend/` 的「自解释地图」：讲清楚每个目录为什么存在、目录之间**有什么区别**、每个文件**该怎么命名**、以及「我新写一个文件该放哪」。
>
> 后端是 Python + FastAPI 应用，采用**经典的分层架构（Layered Architecture）**，与前端 `frontend/src` 的「按职责分层」思路一致，但层的种类更多、更接近教科书式的 DDD（领域驱动设计）分层。

---

## 0. 一句话总纲

`backend/` 的核心思想：**一个文件属于哪一层，由它「处理什么抽象」决定——是 HTTP 请求？是业务规则？是数据库表？还是跨模块的通用能力？**

| 层 | 目录 | 一句话职责 | 类比 |
|---|---|---|---|
| 入口 | `main.py` / `app.py` | 进程启动、FastAPI 应用工厂 | 大门 |
| 接口层 | `api/` | 解析 HTTP 请求/响应 | 前台 |
| 应用服务层 | `services/` | 跨模块的业务编排 | 调度室 |
| 领域层 | `domains/` | 单个合规模块的业务核心 | 各专业车间 |
| 通用能力库 | `common/` | 跨领域复用的技术能力 | 公共工具箱 |
| 接口契约层 | `schemas/` | API 的请求/响应 DTO | 合同范本 |
| 领域模型层 | `models/` | 数据库表（ORM） | 仓库货架 |
| 数据访问层 | `repositories/` | 数据库读写封装 | 仓库管理员 |
| 应用核心 | `core/` | 配置/容器/DB/依赖注入 | 水电总闸 |
| 外部集成 | `integrations/` | 外部服务客户端 | 外部供应商 |
| CLI 执行器 | `harness/` | 白盒 CLI 运行框架 | 质检流水线 |
| 测试 | `tests/` | 模块级测试与案例 | 验收组 |

---

## 1. 顶层文件

| 文件 | 作用 | 命名含义 |
|---|---|---|
| `main.py` | **进程入口**。只有一行核心：`app = create_app()`，供 `uvicorn main:app` 启动 | uvicorn 约定的 ASGI 入口 |
| `app.py` | **应用工厂** `create_app()`：注册 v0/v1 路由、定义 `lifespan`（DB 初始化、失败任务清理、SSE 清理） | 应用组装 |
| `conftest.py` | pytest 全局 fixture（如 `authenticated_client`，隔离的 SQLite + 已认证用户） | pytest 约定的 fixture 文件 |
| `__init__.py` | 包声明 | Python 包标记 |

> 为什么 `main.py` 和 `app.py` 分开？为了「工厂模式」可测试：`create_app(settings)` 能带不同配置反复创建独立应用（测试用临时 SQLite），而 `main.py` 只负责生产启动。

---

## 2. 十二大目录逐个拆解

### 2.1 `core/` —— 应用核心（「水电总闸」）

**职责**：全局配置、依赖注入容器、数据库引擎、通用工具。**不含业务规则。**

| 文件 | 作用 |
|---|---|
| `settings.py` | `Settings(BaseSettings)`：从环境变量/`.env` 读配置（数据库 URL、目录、LLM provider 等） |
| `container.py` | `AppContainer`：依赖注入容器，实例化并持有所有服务（`llm_client`、`file_service`、`report_service`、`review_service`…） |
| `db.py` | `Base(DeclarativeBase)` + `build_engine` / `build_session_factory` / `init_db`（建表 + 兼容旧列） |
| `dependencies.py` | FastAPI 依赖：`get_db`（会话）、`get_current_user`（认证）、`get_container` |
| `runtime_settings.py` | 运行时配置覆盖（动态切换 provider，无需重启） |
| `resource_paths.py` | 资源模板/规则文件路径解析 |
| `json_utils.py` | JSON 序列化 + LLM 输出 JSON 修复 |
| `time.py` | 统一 UTC 时间工具 |

**命名规范**：`snake_case.py`，职责即文件名（`settings`、`container`、`db`、`dependencies`）。

---

### 2.2 `api/` —— 接口层（「前台」）

**职责**：HTTP 路由 + 请求/响应处理。**只做「接收请求 → 调服务 → 返回响应」，不含业务算法。**

**命名规范**：
- 版本目录：`v0/`、`v1/`（API 版本，v0 是旧 task_gateway，v1 是现行主版本）。
- 横切 API 端点：`api/v1/endpoints/<资源名>.py`，每个文件一个 `APIRouter`，如 `auth.py`、`me.py`、`artifacts.py`、`citations.py`、`knowledge.py`、`events.py`、`system_settings.py`、`reports.py`、`copilot.py`、`workspace_state.py`、`diagnosis.py`。
- 业务模块 API：**路由直接在领域层** `backend/domains/<country>/<module>/router.py`，由 `api/v1/router.py` 统一 `include_router`。

**关键点（重要）**：项目里路由分两处存放——
1. **横切 API**（认证、我的任务、产物、引用、知识库、事件、系统设置…）→ 在 `api/v1/endpoints/`。
2. **业务模块 API**（pipia、dpia、eu_scc、tia、cpra、us_14117、bcr、assessment、cn_flow、document_review…）→ 在各模块自己的 `domains/*/router.py`。

> 判断口诀：**「系统级能力」的接口在 `api/`，「合规业务模块」的接口在 `domains/*/router.py`。**

```
api/
├── v0/                     # 旧版（task_gateway 网关）
│   └── task_gateway/
├── v1/                     # 现行主版本
│   ├── router.py           #   总路由：include 所有 endpoints + 各领域 router
│   └── endpoints/          #   横切 API 端点
│       ├── auth.py         #   认证
│       ├── me.py           #   我的任务/报告/工作区
│       ├── artifacts.py    #   产物预览
│       ├── citations.py    #   引用解析
│       ├── knowledge.py    #   知识库
│       ├── events.py       #   事件（SSE）
│       ├── reports.py      #   报告产物
│       ├── copilot.py      #   智能助手
│       ├── system_settings.py # 系统/运行时设置
│       ├── workspace_state.py # 工作区状态
│       └── diagnosis.py    #   diagnosis 兼容接口
```

---

### 2.3 `domains/` —— 领域层（「各专业车间」）

**职责**：每个**合规业务模块**的完整实现。这是项目的**业务核心**，文件数最多（311 个）。

**命名规范**：
- 一级目录：`cn/`、`eu/`、`us/`（**法域** Jurisdiction）。
- 二级目录：模块名 `snake_case`，如 `cn/transfer_diagnosis`、`eu/scc_review`、`us/eo14117`。
- 每个模块内是**一套固定骨架**：

| 模块内文件 | 作用 | 说明 |
|---|---|---|
| `service.py` | **领域服务** `XxxService.generate_report()` / `evaluate()` | 模块的业务编排入口 |
| `schema.py` | **领域 Pydantic 模型** `XxxRequest` / `XxxResult` | 模块自己的输入/输出契约 |
| `router.py` | **领域路由** `APIRouter` | 该模块的 HTTP 接口 |
| `rule_engine.py` / `scc_rule_engine.py` / `gap_rules.py` | **规则引擎** | 确定性规则判定 |
| `fact_builder.py` / `issue_builder.py` / `evidence_builder.py` | **事实/问题/证据构建器** | 结构化中间产物 |
| `agents/` | **LLM 智能体** `*_agent.py` | 各子任务 LLM 调用 |
| `schema_first.py` | **schema-first 渲染适配器** | 统一 IR 渲染 |
| `tests/` | 该模块的单测 | 与模块代码同仓 |

**11 个模块全景**：

| 法域 | 模块目录 | 别名 |
|---|---|---|
| cn | `transfer_diagnosis` | diagnosis |
| cn | `security_assessment` | assessment |
| cn | `pipia` | pipia |
| cn | `document_review` | review |
| eu | `scc_review` | eu_scc |
| eu | `bcr_review` | bcr |
| eu | `dpia` | dpia |
| eu | `tia` | tia |
| us | `eo14117` | us_14117 |
| us | `eo14117_flow_review` | cn_flow |
| us | `cpra` | cpra |

> **`domains/*/service.py` ≠ `services/`**（见 §4 易混淆点）。

---

### 2.4 `services/` —— 应用服务层（「调度室」）

**职责**：跨模块的业务编排 + 横切能力（认证、会话、报告、文件、任务调度）。**它是 `domains/` 与 `api/` 之间的协调者。**

文件清单与详解见上一份文档（`services/` 专题），核心命名规范：

| 命名 | 例子 | 含义 |
|---|---|---|
| `XxxService` | `AuthService`、`ReportService`、`FileService` | 应用服务类 |
| `XxxManager` | `WebSocketManager` | 连接/资源管理器 |
| `XxxDispatcher` | `TaskDispatcher` | 调度器 |
| `xxx_xxx` 函数集 | `task_access.py`、`runtime_health.py` | 无状态横切函数 |

---

### 2.5 `common/` —— 通用能力库（「公共工具箱」）

**职责**：**跨领域复用**的技术能力，按「能力域」分子目录。**不含任何具体合规模块的业务规则。**

| 子目录 | 能力 | 关键文件 |
|---|---|---|
| `llm/` | LLM 客户端/Provider 注册/上下文 | `client.py`、`provider_registry.py`、`context.py` |
| `rag/` | 检索增强生成 | `retriever.py`、`embedding.py`、`vector_store.py`、`hybrid_retriever.py`、`orchestrator.py` |
| `workflow/` | 通用流水线 | `pipeline.py`、`facts.py`、`issues.py`、`evidence.py`、`context_pack.py` |
| `citation/` | 法律引用 | `registry.py`、`compiler.py`、`locators.py`、`markers.py` |
| `knowledge/` | 知识库索引/入库 | `registry.py`、`ingestion_pipeline.py`、`chunker.py`、`v2.py` |
| `render/` | 报告渲染（HTML/DOCX/PDF/Markdown） | `html_renderer.py`、`docx_renderer.py`、`pdf_renderer.py`、`markdown_renderer.py` |
| `reporting/` | 报告中间表示（IR） | `render_manifest.py`、`layout_gate.py`、`migration.py` |
| `trace/` | 运行追踪 | `recorder.py`、`tracer.py`、`events.py`、`thoughts.py` |
| `events/` | 事件（SSE） | `manager.py`、`store.py` |
| `tasks/` | 任务管理 | `manager.py`（InMemoryTaskManager）、`cancellation.py` |
| `runtime/` | 运行清单 | `run_manifest.py`、`module_run.py` |
| `quality/` | 质量门禁 | `markdown_lint.py`、`alignment.py` |
| `risk/` | 风险评分 | `scoring.py` |
| `storage/` | 文件解析 | `file_parser.py` |

> 注：`common/observability/`、`common/schema/` 目前是**空目录**（历史预留，未投入使用），可忽略。

---

### 2.6 `models/` —— 领域模型层（「仓库货架」）

**职责**：SQLAlchemy ORM 模型，**一一映射数据库表**。

**命名规范（最严格）**：类名 = `XxxModel(Base)`，文件名 = `snake_case.py`（去掉 Model 后缀）。

| 文件 | 类名 | 映射表 |
|---|---|---|
| `auth.py` | `UserModel` / `AuthSessionModel` | users / auth_sessions |
| `diagnosis.py` | `DiagnosisSessionModel` | diagnosis_sessions |
| `report.py` | `ReportArtifactModel` | report_artifacts |
| `review.py` | `ReviewTaskModel` / `UploadedFileModel` | review_tasks / uploaded_files |
| `task.py` | `TaskOwnershipModel` | task_ownerships |
| `workspace.py` | `WorkspaceStateModel` | workspace_states |
| `event.py` | `RunEventModel` / `StreamTokenModel` | run_events / stream_tokens |
| `async_task.py` | `AsyncTaskModel` | async_tasks |

> `XxxModel` 后缀 = **它是数据库表**，与 Pydantic 的 `XxxRequest`/`XxxResponse` 明确区分。

---

### 2.7 `repositories/` —— 数据访问层（「仓库管理员」）

**职责**：封装对 `models/` 的 SQL/ORM 读写，供 `services/` 和 `domains/` 调用。**仓储模式（Repository Pattern）**。

**命名规范**：类名 = `XxxRepository`，文件名 = `snake_case.py`。

| 文件 | 类名 | 管哪张表 |
|---|---|---|
| `auth_repository.py` | `AuthRepository` | users / auth_sessions |
| `diagnosis_repository.py` | `DiagnosisRepository` | diagnosis_sessions |
| `report_repository.py` | `ReportRepository` | report_artifacts |
| `review_repository.py` | `ReviewRepository` | review_tasks / uploaded_files |

> **为什么要仓储层**：把「SQL 细节」隔离在 `repositories/`，业务代码只调 `repo.list_by_user(...)` 而不写裸 SQL，换数据库实现时只改仓储。

---

### 2.8 `schemas/` —— 接口契约层（「合同范本」）

**职责**：**横切 API** 的 Pydantic 请求/响应 DTO（数据传输对象）。

**命名规范**：类名带**语义后缀**，一眼看出用途：
- `XxxRequest`：请求体（`LoginRequest`、`RegisterRequest`）
- `XxxResponse`：响应体（`AuthResponse`、`MyTasksResponse`）
- `XxxItem`：列表元素（`MyTaskItem`、`MyReportItem`）
- `XxxPayload`：负载（`WorkspaceStatePayload`）
- `XxxConfig`：配置（`LLMConfig`、`DeliLegalConfig`）
- `XxxEnum` / 枚举：`DiagnosisOutcome(str, Enum)`

| 文件 | 例子 |
|---|---|
| `auth.py` | `AuthUser`、`LoginRequest`、`AuthResponse` |
| `me.py` | `MyTaskItem`、`MyTasksResponse`、`RecoveredModuleRun` |
| `diagnosis.py` | `DiagnosisAnswerSet`、`DiagnosisResult` |
| `workspace.py` | `WorkspaceStatePayload`、`WorkspaceStateResponse` |
| `citation.py` / `copilot.py` / `knowledge.py` / `review.py` / `system_settings.py` | 各资源域契约 |

---

### 2.9 `integrations/` —— 外部集成（「外部供应商」）

**职责**：外部服务的客户端封装。当前只有**得理法搜（DeliLegal）**。

| 文件 | 作用 |
|---|---|
| `delilegal.py` | `DeliLegalService`：得理法搜法律检索 HTTP 客户端 |

> 命名规范：目录名 `integrations`（复数），文件按服务名 `snake_case.py`，类名 `XxxService`。

---

### 2.10 `harness/` —— CLI 执行器（「质检流水线」）

**职责**：白盒 CLI 运行框架，**在进程内直接调用各模块 service**，跑案例 + 断言 + 落运行清单。详见 `status/view/20260813_各模块CLI功能代码流程逻辑原理与数据运行真实情况.md`。

| 文件 | 作用 |
|---|---|
| `runner.py` | 执行器（`_ADAPTER_DEFINITIONS` + `_generic_invoke`/`_diagnosis_invoke`/`_review_invoke`） |
| `validators.py` | 11 个声明式断言操作符 |
| `terminal_trace.py` | 终端 trace 输出 |
| `viewer.py` | 运行清单查看器 |

> 注意：`harness/` 是**执行器本体**，而 `tests/harness/` 是**执行器自己的测试**（`test_harness.py` 等）。

---

### 2.11 `tests/` —— 模块级测试与案例（「验收组」）

**职责**：各模块的 CLI 案例、测试 fixture、跨模块契约测试。

```
tests/
├── <module>/              # 每个模块一个目录
│   ├── cases/             #   CLI 白盒案例（case 定义 + scenario/expected 引用）
│   └── fixtures/          #   测试夹具（golden IR、示例文档）
├── fixtures/              # 全局夹具（cn/eu/us 分法域）
├── contracts/             # 跨模块契约测试（schema-first 适配器）
├── harness/               # harness 执行器自身的测试
├── test_citation_single_source.py  # 顶层专项测试
└── *_browser_app.py       # 浏览器/前端联调用支持脚本
```

---

## 3. 文件/类名命名规范速查

| 位置 | 类名规范 | 文件规范 |
|---|---|---|
| `models/` | `XxxModel(Base)` | `snake_case.py` |
| `schemas/` | `XxxRequest` / `XxxResponse` / `XxxItem` / `XxxPayload` / `XxxConfig` | `snake_case.py` |
| `repositories/` | `XxxRepository` | `snake_case.py` |
| `services/` | `XxxService` / `XxxManager` / `XxxDispatcher` | `snake_case.py` |
| `domains/*/` | `XxxService` / `XxxRequest` / `XxxResult` / `XxxRuleEngine` / `*_agent` / `*_builder` | `snake_case.py` |
| `core/` | `Settings` / `AppContainer` / 工具函数 | `snake_case.py` |
| `common/<能力>/` | 按能力域，无固定类后缀 | `snake_case.py` |
| `api/endpoints/` | `APIRouter` 实例 | `<资源名>.py` |
| `integrations/` | `XxxService` | `snake_case.py` |

**测试文件约定**：与被测文件同目录，命名 `test_<被测名>.py`（`backend/tests/harness/test_validators.py`、`backend/domains/eu/scc_review/tests/test_service.py`）。

---

## 4. 四个最易混淆的「区别」

### ① `models/` vs `schemas/` vs `domains/*/schema.py`（最容易混！）

| 目录 | 是什么 | 基类 | 后缀 | 用途 |
|---|---|---|---|---|
| `backend/models/` | **数据库表** | `Base(DeclarativeBase)` | `XxxModel` | 持久化（SQLAlchemy ORM） |
| `backend/schemas/` | **横切 API 的 DTO** | `BaseModel` | `XxxRequest/Response` | HTTP 输入/输出契约 |
| `backend/domains/*/schema.py` | **领域模块的 DTO** | `BaseModel` | `XxxRequest/Result` | 模块内部的输入/输出契约 |

> 记忆：**`models` = 数据库（表），`schemas` = 横切 API 契约，`domains/*/schema.py` = 领域模块契约。** 三者都是「数据形状」但处于不同抽象层级。

### ② `services/` vs `domains/*/service.py`

| | `backend/services/` | `backend/domains/*/service.py` |
|---|---|---|
| 定位 | **应用服务层**（跨模块编排 + 横切能力） | **领域层**（单个模块业务核心） |
| 例子 | `AuthService`、`ReportService`、`FileService` | `EU_SCCService`、`DPIAService` |
| 关注 | 用户/会话/任务/报告/文件的系统能力 | 某个合规模块怎么算 |
| 依赖方向 | 可依赖 `domains/` | 依赖 `common/`，不依赖 `services/` |

### ③ `common/` vs `core/`

| | `backend/common/` | `backend/core/` |
|---|---|---|
| 定位 | **跨领域复用能力库**（LLM/RAG/渲染/引用/流水线…） | **应用核心基础设施**（配置/容器/DB/依赖注入） |
| 颗粒度 | 大而全（160 文件，按能力域分 14 子目录） | 小而精（15 文件，全局单例） |
| 是否含业务 | 通用技术能力，无具体模块业务 | 无业务，纯工程骨架 |

### ④ `api/v1/endpoints/` vs `domains/*/router.py`

| | `api/v1/endpoints/` | `domains/*/router.py` |
|---|---|---|
| 定位 | **横切系统 API** | **业务模块 API** |
| 例子 | auth / me / artifacts / knowledge / events | pipia / dpia / eu_scc / cpra |
| 归属 | 系统能力 | 领域模块 |

---

## 5. 分层依赖方向（单向向下）

```
main.py → app.py（工厂）
             ↓ 组装
           api/（接口层）
             ↓ 调
        services/（应用服务层）────────────────┐
             ↓ 调                               │ 调
        domains/（领域层）                       │
             ↓ 用                               ↓ 用
        common/（通用能力库）  ←  both 都复用 ──┘
             ↓ 用
        repositories/（数据访问）←→ models/（ORM）
             ↑
        core/（容器/DB/配置，贯穿所有层）
```

**铁律**：
- `api/` 依赖 `services/` + `domains/`，**不被任何层依赖**。
- `domains/` 依赖 `common/` + `repositories/` + `models/`，**不依赖 `services/` 和 `api/`**。
- `common/` 是**最底层通用能力**，不依赖 `api/services/domains`。
- `core/` 是**贯穿性基础设施**，被各层依赖，但它自己只依赖配置。

---

## 6. 「新写一个文件该放哪」决策表

| 我写的是… | 放哪 | 命名 |
|---|---|---|
| 一个新的合规业务模块 | `domains/<country>/<module>/` | `service.py` + `schema.py` + `router.py` + `*_builder.py` + `agents/` |
| 某模块的 LLM 子任务 | `domains/<module>/agents/` | `xxx_agent.py` |
| 某模块的确定性规则 | `domains/<module>/rule_engine.py` | `rule_engine.py` |
| 一张新的数据库表 | `models/` | `XxxModel(Base)`，文件名 `xxx.py` |
| 该表的读写封装 | `repositories/` | `XxxRepository` |
| 一个横切 API 的请求/响应 | `schemas/` | `XxxRequest` / `XxxResponse` |
| 一个横切 HTTP 端点 | `api/v1/endpoints/` | `<资源名>.py` |
| 一个跨模块的应用服务 | `services/` | `XxxService` |
| 一个跨领域通用能力（LLM/RAG/渲染…） | `common/<能力>/` | `snake_case.py` |
| 一个外部服务客户端 | `integrations/` | `XxxService` |
| 全局配置/依赖注入 | `core/` | `snake_case.py` |
| 某文件的单测 | 与被测文件同目录 | `test_<被测名>.py` |

---

## 7. 目录全景（速览）

```
backend/
├── main.py                  # uvicorn 入口（app = create_app()）
├── app.py                   # FastAPI 应用工厂 + lifespan
├── conftest.py              # pytest 全局 fixture
├── api/                     # 接口层
│   ├── v0/task_gateway/     #   旧网关
│   └── v1/
│       ├── router.py        #   总路由
│       └── endpoints/       #   横切 API
├── core/                    # 应用核心（配置/容器/DB/DI/工具）
├── services/                # 应用服务层（跨模块编排）
├── domains/                 # 领域层（cn/eu/us 分法域 × 11 模块）
├── common/                  # 通用能力库（14 个能力域）
├── models/                  # ORM 数据库表（XxxModel）
├── repositories/            # 数据访问层（XxxRepository）
├── schemas/                 # 横切 API 契约（XxxRequest/Response）
├── integrations/            # 外部集成（得理法搜）
├── harness/                 # CLI 白盒执行器
└── tests/                   # 模块测试 + cases + fixtures + contracts
```

---

## 8. 一句话记忆法

**`main/app` 是门，`api` 是前台，`services` 是调度室，`domains` 是车间，`common` 是工具箱，`models` 是货架，`repositories` 是管理员，`schemas` 是合同，`core` 是水电总闸，`integrations` 是外部供应商，`harness` 是质检线，`tests` 是验收组。**
