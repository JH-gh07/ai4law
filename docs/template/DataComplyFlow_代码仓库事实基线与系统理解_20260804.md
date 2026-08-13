---
document_type: "repository_facts_and_system_understanding"
schema_version: "1.0.0"
document_status: "Reviewed"
template_profile: "extended"
repo_name: "DataComplyFlow（数规通）"
repo_url_or_path: "/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law"
branch: "new"
tag: "none"
commit: "826e23d"
analysis_date: "2026-08-04"
analysis_scope: "完整仓库直接扫描，覆盖后端FastAPI、前端React/Vite、11个业务模块、公共能力、CLI Harness、评测、配置、安全与运行产物"
visibility: "closed-source"
runtime_verification: "partially_verified"
previous_baseline: "DataComplyFlow_软件功能说明文档 V1.0（2026-07-31）；数规通（DataComplyFlow）软件功能说明文档（详细版）V2.0（2026-08-01）；CODE_CURRENT_STATUS_AND_GAPS.md（2026-07-22）"
change_scope: "基于 Commit 826e23d 建立完整事实基线；2026-08-05 复核并修正架构、路由、产物路径、渲染模型与评测证据等级"
primary_language: "zh-CN"
intended_consumers:
  - "human_reader"
  - "ai_context"
  - "ai_code_review"
  - "downstream_document_generation"
---

# DataComplyFlow（数规通）代码仓库事实基线与系统理解文档

> **Type**：Repository Facts / System Understanding  
> **Status**：Reviewed  
> **Version**：V1.2  
> **Last Updated**：2026-08-05  
> **Scope**：DataComplyFlow `new` 分支（Commit `826e23d`），完整仓库直接扫描  
> **Consumers**：Human / AI / Downstream Documents  

---

## 快速入口

### 核心结论

> **DataComplyFlow 是一套面向企业数据合规与跨境数据治理的 Legal Agentic RAG 工作台。系统以规则引擎承担确定性判断，以大语言模型承担语义理解和报告生成，以 RAG、结构化引用、共享渲染能力和运行追踪保证依据可查、过程可观测、产物可交付。**

仓库按中国、欧盟、美国三个法域组织 11 个注册业务模块，具备 FastAPI 后端、React/Vite 前端、CLI Harness、产品 Smoke 与规模化 RAG 评测、Provider 管理、CitationMap、共享渲染工具、任务归属隔离和运行账本。**同一提交基线的运行验证结果**：后端 528 passed、前端 48 passed、前端生产构建 342 modules、11 模块 CLI Smoke 15 PASS。外部 LLM、得理法律 API、浏览器 E2E、生产部署和法律专家 Gold 未完成真实验证，因此本基线为部分运行验证，不代表生产可用性。

### 当前仓库摘要

| 项目 | 当前事实 |
|---|---|
| 仓库定位 | AI 驱动的数据跨境合规诊断与文书智能生成平台 |
| 目标用户 | 企业法务、合规咨询顾问、法律学习者 |
| 仓库路径 | `/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law` |
| 分支 | `new` |
| 提交基线 | `826e23d`（2026-08-04 03:01:18 +0800） |
| 注册业务模块 | 11 个：CN 4 / EU 4 / US 3 |
| 技术形态 | FastAPI 后端 + React/Vite SPA + SQLite + CLI Harness + Benchmark |
| 核心方法 | 规则引擎 + 大语言模型 + 工作流编排 + 多索引 RAG + 结构化引用 |
| 核心输出 | 路径结论、评估报告、审查报告、批注 DOCX、XLSX 差距清单、CitationMap、RunManifest、Trace |
| API 基线 | 102 个显式 Method + Path：`/health` 1、v0 7、v1 94 |
| 当前运行验证快照 | 后端 528 passed；前端 48 passed；前端构建通过；CLI Smoke 15 PASS |
| 主要风险 | 历史规模化 RAG 快照中 Recall@5 为 0.150、Hybrid 与 Vector 结果一致，且部分模块 Issue Recall 为 0；任务和 SSE 为内存态；外部模型与得理适配存在条件阻断 |

---

## 文档读取与证据约定

### 证据来源

| 来源ID | 来源 | 性质 |
|---|---|---|
| `FACT-01` | 本次直接代码扫描（`backend/`、`frontend/`、`config/`、`benchmarks/`、`resources/`、`scripts/`） | E2 代码证据 |
| `FACT-02` | 2026-08-04 基线建立时的直接运行验证（pytest 528 passed、Vitest 48 passed、CLI Smoke 15 PASS、仓库卫生、编译检查） | E1 运行证据 |
| `FACT-03` | 项目现行规范（`docs/standards/`） | E3 文档证据 |
| `FACT-04` | 项目事实快照（`docs/handoff/`、`CODE_CURRENT_STATUS_AND_GAPS.md`） | E3/E5 补充材料 |
| `FACT-05` | `config/module_registry.json`、`pyproject.toml`、`uv.lock`、`package.json` | E2 配置与契约 |

### 证据类型

| 编号 | 证据类型 | 本次覆盖 |
|---|---|---|
| E1 | 运行证据 | ✅ 后端测试、前端测试、构建、CLI Smoke、仓库卫生、编译检查均在 2026-08-04 基线建立时执行 |
| E2 | 代码证据 | ✅ 后端源码、前端源码、配置、Schema、脚本均按 Commit `826e23d` 读取 |
| E3 | 当前文档证据 | ✅ `docs/standards/`、`docs/handoff/`、`README.md` |
| E4 | 分析推断 | 仅在代码关系推断时使用，明确标注 |
| E5 | 历史信息 | `docs/archive/`、`CODE_CURRENT_STATUS_AND_GAPS.md` 历史切片 |

### 文档中的资产ID

- `REPO-*`：仓库和事实基线；
- `MOD-*`：业务模块和公共能力组件；
- `FLOW-*`：动态执行链；
- `DATA-*`：数据对象、账本和知识资产；
- `API-*` / `CLI-*`：接口与命令；
- `CFG-*`：配置和契约；
- `DEP-*`：外部依赖；
- `VER-*`：验证和评测；
- `LIM-*`：已知限制；
- `OPEN-*`：待确认事项；
- `TD-*`：技术债。

---

## 1. 分析范围与事实基线

> **本章核心问题**：当前文档分析的是哪个项目版本、覆盖哪些资产、事实依据是什么。

### 1.1 仓库身份与分析目的

| 项目 | 内容 |
|---|---|
| Asset ID | `REPO-001` |
| 项目名称 | DataComplyFlow（数规通） |
| 产品副标题 | AI 驱动的数据跨境合规诊断与文书智能生成平台 |
| 业务定位 | 面向企业数据合规与跨境数据治理的 Legal Agentic RAG 工作台 |
| 主要用户 | 企业法务、合规咨询顾问、法律学习者 |
| 本次目的 | 对代码仓库进行直接扫描和运行验证，形成可供团队理解、AI 辅助审查和下游文档编制的仓库事实基线 |
| 仓库路径 | `/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law` |
| 当前分支 | `new` |
| 当前提交 | `826e23d`（2026-08-04 03:01:18 +0800） |
| 远程仓库 | `origin/new` |

### 1.2 分析范围

本文通过直接代码扫描和运行验证覆盖以下资产：

- FastAPI 后端入口（`backend/main:app`）、API 网关（v0/v1）、法域业务包（`backend/domains/{cn,eu,us}/`）、公共能力（`backend/common/`）、核心配置（`backend/core/`）和第三方集成（`backend/integrations/`）；
- React 18 + Vite + TypeScript 前端页面、工作台、引用交互和运行观察组件；
- CN、EU、US 三个法域的 11 个业务模块；
- LLM Provider 管理、本地多索引 RAG、CitationMap、报告渲染、事件追踪、任务和产物管理；
- CLI Harness（`backend/harness/`）、Product Smoke、规模化 RAG 评测；
- 环境变量、模块注册表、认证、任务归属和敏感信息保护；
- 当前测试、构建、路由与知识库，以及带日期的运行产物和历史评测快照。

以下内容本次未覆盖：

- 生产部署拓扑、容器编排或云基础设施；
- 当前线上服务状态；
- 真实 API Key、生产数据库和私有数据；
- 浏览器端到端自动化测试（当前代码仓库中不存在）；
- 法律专家 Gold 验证。

### 1.3 事实冲突与处理

| 主题 | 材料情况 | 本文处理 |
|---|---|---|
| 提交基线 | 旧材料记录 `5c8d1e3`；本次实际 HEAD 为 `826e23d` | 以本次 `git rev-parse HEAD` 结果为准 |
| CLI 命令形式 | 代码中 `uv run --frozen` 与实际运行的 `.venv/bin/pytest` 并存 | 保留 `uv run --frozen` 作为标准复现命令 |
| 业务模块数 | `module_registry.json` 明确 11 个（含 `legacy-compatible`） | 采用 11 |
| 注册模块 vs PDF 产出 | 注册业务模块 11 个；有效 PDF 12/12（含 v0 legacy） | 分开记录 |

### 1.4 术语

| 术语 | 本文含义 | 代码来源 |
|---|---|---|
| Legal Agentic RAG | 将规则、工作流、LLM、法规检索、引用和产物生成组合成受控法律任务链 | — |
| ProviderSnapshot | 异步任务提交时复制的不可变 LLM Provider 快照 | `backend/common/llm/snapshot.py` |
| GenerationContextPack | 安全评估等模块生成前组装的规则结论、法规条文和引用允许列表 | `backend/domains/cn/security_assessment/` |
| CitationMap | 报告引用与来源、条号、片段和解析状态之间的结构化映射 | `backend/common/citation/output.py` |
| CitationResolution | 引用解析类型：`exact_article` / `source_overview` / `external_verified` / `unresolved` | `backend/common/citation/` |
| ReportDocument | `metadata + sections + citations` 结构化语义模型；当前仅部分渲染路径采用 | `backend/common/render/report_model.py` |
| RunManifest | 一次任务的统一运行账本 | `outputs/{module}/{task}/run_manifest.json` |
| Trace Manifest | 记录 workflow node 和 tool call 时间、状态和耗时的技术轨迹 | 应用：`outputs/{module}/{task_id}/trace/manifest.json`；CLI：`runs/{module}/{run_id}/trace/manifest.json` |
| Product Smoke | 固定小样本的产品功能回归评测 | `benchmarks/datasets/product_smoke/` |
| SafeReject | 规模化 RAG 负例中的安全拒答指标 | `benchmarks/` |

---

## 2. 仓库速览与核心资产索引

> **本章核心问题**：仓库整体是什么、如何使用、由哪些关键资产构成。

### 2.1 项目定位与使用链路

DataComplyFlow 面向中国、欧盟和美国的数据合规场景，提供路径诊断、风险评估、合同或规则审查、影响评估和合规差距清单。用户登录后进入任务空间，选择法域和任务，填写业务事实或上传文档；系统执行规则判断、法规检索、风险识别和报告生成，并通过结构化引用提供依据溯源。

```text
用户选择法域和任务
→ 填写结构化事实、自然语言描述或上传文档
→ 规则判断、文件解析或风险识别
→ 本地多索引 RAG 检索
→ 按条件调用外部法律检索或 LLM
→ 形成结构化结论、报告或差距清单
→ 生成 CitationMap、RunManifest、Trace 和多格式产物
→ 前端预览、引用跳转、下载与审计查看
```

### 2.2 技术形态

| 层级 | 当前技术 | 代码证据 |
|---|---|---|
| 后端 | FastAPI / Python 3.11 | `backend/main.py:app`；`pyproject.toml` 锁定 Python ≥3.11 |
| 前端 | React 18 + Vite + TypeScript | `frontend/package.json`；`frontend/src/main.tsx` |
| 数据库 | SQLite（开发阶段） | `backend/core/db.py` 通过 SQLAlchemy 连接 |
| 包管理 | uv / npm | `uv.lock` / `package-lock.json` |
| LLM | OpenAI-compatible Provider | `backend/common/llm/client.py` |
| 法规检索 | 本地多索引 RAG + 得理 API | `backend/common/rag/`（`orchestrator.py`、`service.py`、`retriever.py`、`fulltext_index.py`） |
| 报告输出 | 按模块输出 Markdown / HTML / DOCX / PDF / XLSX / ZIP 等不同格式组合 | `backend/common/render/` + 各领域模块渲染代码 |
| 测试 | pytest / Vitest / CLI Harness | `backend/tests/`、`frontend/src/`（Vitest）、`backend/tests/harness/`（测试）、`backend/harness/`（CLI 实现） |
| 版本控制 | Git | `.git/`，分支 `new`，远程 `origin/new` |

### 2.3 快速入口

| Asset ID | 目的 | 命令 |
|---|---|---|
| `CLI-001` | 启动后端 | `uv run uvicorn backend.main:app --reload --port 8000` |
| `CLI-002` | 安装前端依赖并启动开发服务 | `cd frontend && npm ci && npm run dev` |
| `CLI-003` | 后端全量测试 | `uv run --frozen pytest -q` |
| `CLI-004` | 前端全量测试 | `npm --prefix frontend test -- --run` |
| `CLI-005` | 前端生产构建 | `npm --prefix frontend run build` |
| `CLI-006` | 11 模块离线 CLI Smoke | `uv run --frozen python -m backend.harness.runner all --no-llm` |
| `CLI-007` | 仓库卫生检查 | `uv run --frozen python scripts/check_repository_hygiene.py` |
| `CLI-008` | Python 编译检查 | `uv run --frozen python -m compileall -q backend` |
| `CLI-009` | Product Smoke 评测 | `uv run --frozen python scripts/run_smoke_benchmark.py` |
| `CLI-010` | 规模化 RAG 评测 | `uv run --frozen python scripts/run_rag_retrieval_benchmark.py` |

### 2.4 核心资产索引

| 资产类别 | 主要资产 | Asset ID | 详细位置 |
|---|---|---|---|
| 仓库基线 | `new` 分支、`826e23d`、完整仓库 | `REPO-001` | 第1章 |
| 应用入口 | `backend/main:app`、`frontend/src/main.tsx` | `MOD-100` / `UI-001` | 第3章 |
| 业务模块 | 11 个 CN/EU/US 模块 | `MOD-001`—`MOD-011` | 第5章、附录C |
| 核心运行链 | 启动、任务执行、检索引用、报告生成 | `FLOW-001`—`FLOW-005` | 第4章 |
| 关键数据资产 | 模块注册表、法律库、CitationMap、RunManifest、Trace | `DATA-001`—`DATA-012` | 第6章 |
| 公共能力 | Provider、RAG、Citation、渲染、可观测、任务产物 | `MOD-101`—`MOD-106` | 第5章 |
| 验证资产 | 测试、构建、CLI Smoke、Benchmark | `VER-001`—`VER-009` | 第7章 |
| 已知限制 | RAG、生成覆盖、持久化、外部条件、知识库消歧 | `LIM-001`—`LIM-009` | 第7章 |
| 推荐阅读顺序 | 入口、注册表、路由、领域包、公共能力、测试 | — | 第8章 |

### 2.5 核心事实摘要

| 结论 | 证据 | 边界 |
|---|---|---|
| 系统有 11 个注册业务模块，按 CN 4 / EU 4 / US 3 组织 | [E2] `config/module_registry.json` 实际读取：11 个条目 | 已确认 |
| 模块身份以 `config/module_registry.json` 为唯一权威源 | [E2] `config/module_registry.json` 完整内容；[E3] `docs/standards/DataComplyFlow_活动架构与权威源.md` §2-§3 | 已确认 |
| API 基线为 102 个显式 Method + Path | [E2] `backend/api/tests/route_baseline.json`：102 个 JSON 条目（health 1 / v0 7 / v1 94） | 具体每条路由见 §6.2 |
| 当前提交验证结果：后端 528、前端 48、构建 342、CLI 15 PASS | [E1] 2026-08-04 执行 `pytest -q`、`npm test`、`npm run build`、CLI Smoke 全部通过 | 执行环境：macOS，Python 3.11 |
| 本地法律知识资产为 69 来源、1,672 条登记 | [E2] `resources/legal/registry/regulation_articles.jsonl` 实际行数；[E5] `CODE_CURRENT_STATUS_AND_GAPS.md` §2.4 | 重复定位键 34 组 |
| 历史规模化 RAG 快照中 Recall@5 为 0.150，Vector 与 Hybrid 相同 | [E2] `benchmarks/` 仅确认评测代码与数据集结构；[E5] `docs/handoff/DataComplyFlow_产品能力补强与后续工作清单_20260719.md` §2.3 记录数值 | 本轮未重跑，不作为当前 E1 结果 |

---

## 3. 静态结构与架构组织

> **本章核心问题**：代码和资源如何分层，主要目录承担什么责任，系统边界在哪里。

### 3.1 五层架构

```text
┌─────────────────────────────────────────────────┐
│ 前端层：React/Vite SPA                           │
│ 首页、认证、任务空间、工作台、知识库中心、设置       │
├─────────────────────────────────────────────────┤
│ API 网关层：FastAPI                              │
│ /api/v0 历史兼容；/api/v1 主入口                  │
├─────────────────────────────────────────────────┤
│ 业务领域层                                        │
│ CN 4 模块；EU 4 模块；US 3 模块                   │
├─────────────────────────────────────────────────┤
│ 公共能力层                                        │
│ Provider、RAG、Citation、渲染、事件、任务、产物      │
├─────────────────────────────────────────────────┤
│ 基础设施层                                        │
│ 配置、数据库、文件存储、密钥、健康检查               │
└─────────────────────────────────────────────────┘
```

> **核心结论｜CLAIM**  
> 当前是混合对象组装架构：`AppContainer` 管理应用级基础服务和部分核心业务服务；多数领域路由仍持有模块级长寿命 service，并由运行时刷新器在 Provider 配置变化后重新绑定 LLM 或得理客户端。

> **证据｜EVIDENCE**
> - [E2｜代码] `backend/core/container.py`：`AppContainer` 管理数据库引擎、任务调度器、WebSocket、LLM、文件、报告、会话、得理、诊断和文档审查服务
> - [E2｜代码] `backend/services/runtime_client_refresher.py`：`refresh_runtime_clients()` 导入领域路由中的模块级实例，并覆盖顶层 service、generator、renderer、type classifier、clause reviewer 和 agent 字典中的客户端引用
> - [E2｜代码] `backend/domains/*/*/router.py`：多数领域路由在模块加载时创建并长期持有 service 或 renderer 实例

> **边界｜BOUNDARY**  
> 不应据此推导 RAG、Citation、Renderer 或 Task Manager 全部由 `AppContainer` 统一注入。ProviderSnapshot 的不可变隔离机制已在 9 个异步模块中验证（`ContextVar` 绑定），但文档审查模块使用数据库 dispatcher，尚未完全纳入统一 ProviderSnapshot 体系。

### 3.2 仓库目录

| 目录 | 核心责任 | 代码证据 | 状态 |
|---|---|---|---|
| `backend/main.py` | FastAPI ASGI 导出入口 | 导出 `backend/app.py:create_app()` 创建的 `app` | 活跃 |
| `backend/api/v1/` | v1 主 API 路由（94 条） | `endpoints/` 按模块组织 + `router.py` 汇总 | 活跃 |
| `backend/api/v0/` | 历史兼容网关（7 条路由） | `router.py` + endpoints | 兼容 |
| `backend/domains/cn/` | 中国法域业务 | 4 子目录：transfer_diagnosis、security_assessment、document_review、pipia | 活跃 |
| `backend/domains/eu/` | 欧盟法域业务 | 4 子目录：scc_review、bcr_review、dpia、tia | 活跃 |
| `backend/domains/us/` | 美国法域业务 | 3 子目录：eo14117、eo14117_flow_review、cpra | 活跃 |
| `backend/common/llm/` | LLM Provider 客户端与 postprocess | `client.py`、`postprocess.py` | 活跃 |
| `backend/common/rag/` | RAG 检索体系 | `orchestrator.py`、`service.py`、`retriever.py`、`fulltext_index.py` | 活跃 |
| `backend/common/citation/` | Citation 管理与校验 | `output.py`、tests 114 项 | 活跃 |
| `backend/common/render/` | Markdown/HTML/DOCX/PDF 渲染能力 | 共享模型、适配器、模板工具与渲染器 | 活跃 |
| `backend/common/trace/` | Trace 事件记录 | `recorder.py` | 活跃 |
| `backend/common/events/` | SSE 事件管理 | 内存态事件流管理 | 活跃 |
| `backend/common/tasks/` | 异步任务管理 | 内存态执行、状态、重试和 RunManifest 写入 | 活跃 |
| `backend/common/workflow/` | 工作流编排 | `trace.py` 含 TraceManifest 模型 | 活跃 |
| `backend/common/schema/` | 公共 Schema 定义 | 跨模块共享的数据模型 | 活跃 |
| `backend/common/knowledge/` | 知识库构建 | `builders_v2.py` (1,321 行) | 活跃 |
| `backend/common/storage/` | 文件存储抽象 | 路径管理和文件操作 | 活跃 |
| `backend/common/runtime/` | 通用运行记录 | `module_run.py`、`run_manifest.py` | 活跃 |
| `backend/common/risk/` | 风险评估公共逻辑 | 风险等级定义和计算 | 活跃 |
| `backend/common/observability/` | 可观测性 | OpenTelemetry 适配导出 | 活跃 |
| `backend/core/` | 核心配置与对象组装 | `settings.py`、`runtime_settings.py`、`db.py`、`container.py` | 活跃 |
| `backend/integrations/` | 第三方集成 | `delilegal.py` — 得理法律 API 适配器 | 活跃 |
| `backend/services/` | 跨领域应用服务 | `task_access.py`、`runtime_client_refresher.py`、文件/报告/会话等服务 | 活跃 |
| `backend/repositories/` | 数据访问 | SQLAlchemy repository 模式 | 活跃 |
| `backend/schemas/` | API Schema 定义 | Pydantic 请求/响应模型 | 活跃 |
| `backend/harness/` | CLI 测试框架实现 | `runner.py`、`viewer.py`、`validators.py`、`terminal_trace.py`；测试在 `backend/tests/harness/`，案例位于 `backend/tests/*/cases/` | 活跃 |
| `frontend/src/main.tsx` | React SPA 入口 | Vite dev server 入口 | 活跃 |
| `frontend/src/components/` | UI 组件 | auth、citation、common、landing、modals、onboarding、report-center、workspace | 活跃 |
| `frontend/src/features/module-runner/` | 模块运行器 | 按模块纵向拆分的表单/payload/case | 活跃 |
| `frontend/src/lib/` | 前端公共库 | auth、module-registry、task-templates、useTaskEvents、trace-adapter 等 | 活跃 |
| `frontend/src/api/` | API 客户端 | 后端接口的 TypeScript 调用封装 | 活跃 |
| `config/module_registry.json` | 跨前后端模块身份唯一权威源 | 11 个条目（CN 4 / EU 4 / US 3） | 活跃 |
| `benchmarks/` | 评测体系 | `datasets/`、`smoke_eval.py`、`rag_retrieval_eval.py`、`schema.py` | 活跃 |
| `resources/legal/` | 法律知识库 | registry、catalog、原文快照 | 活跃 |
| `resources/rules/` | 静态规则 | `cn/review_rulebook.json` 被生产代码读取 | 活跃 |
| `resources/templates/` | 报告模板 | 按 cn/eu/us 分法域 | 活跃 |
| `scripts/` | 仓库脚本 | `check_repository_hygiene.py`、`build_rag_vector_index.py`、`run_*_benchmark.py` 等 11 个 py/sh | 活跃 |
| `docs/standards/` | 现行规范 | 6 份活动规范文档 | 活跃 |
| `docs/handoff/` | 有日期事实快照 | 7 份交接材料 | 参考 |
| `docs/archive/` | 历史材料 | 已归档批次和模板 | 历史 |
| `storage/` | 本地运行状态 | SQLite、上传、会话、运行时配置 | 运行时 |
| `outputs/` | 运行产物 | 按 `{module}/{task}/` 组织 | 运行时 |
| `runs/` | CLI 运行记录 | 按 `{module}/{run_id}/` 组织 | 运行时 |

### 3.3 关键入口与契约文件

| Asset ID | 对象 | 作用 | 代码位置 |
|---|---|---|---|
| `MOD-100` | FastAPI app | 后端 ASGI 入口 | `backend/main.py:app` |
| `UI-001` | React SPA | 前端入口 | `frontend/src/main.tsx` |
| `DATA-002` | 模块注册表 | 11 个业务模块身份唯一权威源 | `config/module_registry.json` |
| `CLI-006` | CLI Harness Runner | 单案例与全模块执行 | `backend/harness/runner.py` |
| `CLI-011` | CLI Harness Viewer | 运行汇总和事件查看 | `backend/harness/viewer.py` |
| `CFG-001` | 应用配置 | Settings 类 | `backend/core/settings.py` |
| `CFG-010` | 运行时配置 | Provider 配置与健康状态 | `storage/runtime_settings.json` |

### 3.4 系统边界与不可见部分

**仓库内部承担**：
- 业务事实采集、文件解析、规则判断和模块工作流；
- 本地知识库构建和检索；
- Provider 选择、健康探测和任务快照管理；
- 报告、引用、事件、账本和产物生成；
- 用户认证、任务归属和产物访问控制。

**仓库外部依赖**：
- OpenAI-compatible LLM Provider（腾讯混元等）；
- 得理法律 API；
- 用户提供的业务事实和文件；
- 生产环境的模型额度、网络和外部服务可用性。

**本次未覆盖**：
- 生产基础设施和高可用部署；
- 线上数据库和对象存储方案；
- LLM 和得理的真实调用（外部账号额度依赖）；
- 浏览器端到端自动化测试（当前代码仓库中不存在 E2E 测试）；
- 法律专家 Gold 验证（属于后续 P1 任务）。

---

## 4. 动态执行与数据流

> **本章核心问题**：系统从启动到一次任务完成经历哪些阶段，数据、状态、引用和产物如何流转。

### 4.1 启动与对象组装

`FLOW-001`：应用启动链

```text
backend/main.py — 调用 backend/app.py:create_app()
→ backend/core/settings.py:get_settings() — 读取 .env 环境变量
→ backend/core/container.py:AppContainer — 构建数据库引擎、会话工厂和应用级服务
  ├─ 任务调度器与 WebSocket Manager
  ├─ LLM Client、文件、报告、会话和得理服务
  └─ 诊断与文档审查服务
→ backend/core/runtime_settings.py — 加载并应用 storage/runtime_settings.json 覆盖项
→ backend/services/runtime_client_refresher.py — 将生效客户端重绑到容器和模块级长寿命实例
→ backend/app.py:create_app() — 创建 FastAPI，挂载 v0（7 条）、v1（94 条）及 /health（1 条）
→ FastAPI lifespan 启动 — backend/core/db.py:init_db() 初始化数据库表，并启动 SSE 过期事件清理循环
→ 健康检查就绪（GET /health）
```

> **证据｜EVIDENCE**
> - [E2｜代码] `backend/app.py`、`backend/main.py`、`backend/core/settings.py`、`backend/core/db.py`
> - [E2｜代码] `backend/core/container.py`：`AppContainer` 管理应用级服务
> - [E2｜代码] `backend/services/runtime_client_refresher.py`：刷新模块级长寿命实例持有的客户端
> - [E1｜运行] `uv run uvicorn backend.main:app --reload --port 8000`：启动成功，监听 8000 端口

### 4.2 典型业务任务链

`FLOW-002`：一般 Legal Agentic RAG 任务

```text
用户登录 → 选择法域和业务模块
→ 前端构造请求（ModuleRunPanel → fetch POST /api/v1/{module}）
→ 后端路由鉴权（Depends(get_current_user)）
→ Schema 校验（Pydantic Model）
→ 创建 TaskOwnership（task_id → user_id 持久化）
→ 异步任务提交（复制 ProviderSnapshot 为不可变快照）
→ 模块执行：
  ├─ 规则引擎判断（确定性 true/false）
  ├─ 文件解析（PDF/DOCX/MD → 条款切分）
  ├─ QueryPlan 构造 → 本地多索引 RAG 检索
  ├─ [条件触发] 得理法律 API
  ├─ 上下文组装（规则结果 + 检索结果 + 引用允许列表）
  └─ [需要生成时] LLM 按章节模板生成
→ 引用规范化 → CitationMap 持久化
→ 模块输出结构化结果，并按各自实现直接模板渲染或经 ReportDocument/ContentAdapter 渲染
→ 生成模块支持的 MD/DOCX/PDF/XLSX/ZIP 等产物（格式集合因模块而异）
→ RunManifest 落盘 + Trace 记录
→ SSE 事件推送前端（进度 + Token + 耗时）
→ 产物登记 + 预览/下载入口
```

> **边界**：不同模块不会完整经过所有阶段。`cn.transfer_diagnosis` 的确定性规则判断不调用 LLM；`us.cpra` 主要形成 XLSX 差距清单而非 ReportDocument。

### 4.3 安全评估生成链

`FLOW-003`：`cn.security_assessment`

```text
企业画像和数据处理事实
→ 结构化事实包（FactItem 列表）
→ gap_items 生成 + HIGH/MEDIUM/LOW/BLOCKER 风险分级
→ 本地多索引 RAG（legal + workflow + standard_clause + template + testcase）
→ HIGH/BLOCKER 或低置信度条件触发得理 API 增强
→ GenerationContextPack 组装
   = 规则结论 + 检索结果（条文原文片段） + 引用允许列表（citation_id 白名单）
→ LLM 按章节模板生成（Prompt 约束：只能用允许列表中的 citation_id；不确定=待确认）
→ CitationRegistry 校验 citation_id 有效性
→ CitationMap 持久化（outputs/{module}/{task}/outputs/citation_map.json）
→ 安全评估 ReportRenderer 直接执行模板渲染；ContentAdapter 另生成 ReportDocument 正文视图
→ 输出 Markdown / DOCX / PDF / ZIP 及结构化 JSON/XLSX 附件
→ RunManifest + Trace Manifest 落盘
```

> **证据｜EVIDENCE**
> - [E2｜代码] `backend/domains/cn/security_assessment/` — 完整模块实现
> - [E2｜代码] `backend/common/citation/output.py` — Citation 规范化
> - [E2｜代码] `backend/common/rag/service.py` — RAG 检索入口
> - [E2｜代码] `backend/common/rag/orchestrator.py` — 多索引编排器

### 4.4 RAG 与引用链

`FLOW-004`：检索和引用

```text
用户查询
→ QueryPlan（确定法域、资源类型、检索策略）
→ 分词 + SHA-256 确定性哈希 → 384 维向量
→ 向量相似度检索 + 关键词检索（并行）
→ Reciprocal Rank Fusion 合并排序
→ UsagePolicyFilter 过滤（effective 可用于确定性结论；reference 仅背景）
→ 置信度判断
  ├─ 充分 → 返回本地结果
  └─ 不足 / HIGH 风险 / 最新性要求 → 调用得理 API
     → 来源对齐 + 效力校验 + 去重
→ CitationRegistry 生成 citation_id
→ Injection 到 LLM Prompt（仅允许列表中的 citation_id）
→ LLM 生成正文（使用 [cite:CIT-xxx] 标记）
→ 后处理校验：
  ├─ citation_id 是否在允许列表中？
  ├─ source_id 是否在本地知识库中存在？
  └─ 条号是否唯一可解析？
→ CitationResolution 判定：
  ├─ exact_article → 可精确跳转
  ├─ source_overview → 仅出示法规概览
  ├─ external_verified → 来自得理，标注来源 API
  └─ unresolved → 灰显，不提供跳转
→ CitationMap JSON 持久化 → Citations API → 前端 CitationMarkdownRenderer
```

> **证据｜EVIDENCE**
> - [E2｜代码] `backend/common/rag/`：`orchestrator.py`（多索引）、`retriever.py`（检索器）、`fulltext_index.py`（全文索引）
> - [E2｜代码] `backend/common/rag/orchestrator.py`：`HashingEmbedder` 使用 SHA-256 确定性哈希（原本使用 `hash(token)` 已修复为确定性实现）
> - [E2｜代码] `backend/common/citation/output.py`：CitationResolution 四种类型定义
> - [E2｜配置] 索引 Schema 升至 `v3.2`，记录 `sha256-v1` 版本号和 384 维

> **边界｜BOUNDARY**  
> 历史规模化评测快照中 Vector 与 Hybrid 结果完全一致（Recall@5 均为 0.150）。初步判断 Hybrid 模式在该次评测调用链中未实际启用不同检索策略。该问题属于待复核限制（`LIM-002`）；本轮未重跑规模化评测，第 4.4 节流程图不代表 Hybrid 已被有效验证。

### 4.5 任务状态、异步调度和恢复

`FLOW-005`：任务状态

```text
CREATED
→ RUNNING（Worker 拾取，复制 ProviderSnapshot，ContextVar 绑定）
→ COMPLETED（写 RunManifest + 最终事件 + Trace Manifest）
→ FAILED（应用运行时将错误写入 RunManifest，并写最终失败事件与 Trace Manifest）
→ CANCELED
→ RETRYING（复用原 ProviderSnapshot 和原 runner）
```

CLI Harness 使用独立运行契约：失败时另外写入 `runs/{module}/{run_id}/output/error.json`。该文件不属于应用异步任务的通用失败产物。

已知机制：

- 9 个异步模块提交时复制不可变 `ProviderSnapshot`（frozen dataclass），任务线程通过 `ContextVar` 绑定
- `assert_task_access(current_user, task_id)` 统一校验事件、引用、状态和重试接口
- SSE 实时事件包括 `task_started`、`tool_start/result`、`llm_call`（含 Token，标注 `provider_reported` / `estimated`）、`node_completed`、`task_completed/failed`
- 任务完成时原子写入 `run_manifest.json`（含脱敏 ProviderSnapshot、Token、产物列表、fallback）
- `TraceRecorder` 记录每个 workflow node 和 tool call 的 `queued_at / started_at / ended_at / duration / status`
- 任务执行器和 SSE 事件流为内存态，服务重启后能读取已落盘 RunManifest，但不能恢复运行状态或历史实时事件

> **证据｜EVIDENCE**
> - [E2｜代码] `backend/common/tasks/`：异步任务执行、状态和重试管理
> - [E2｜代码] `backend/models/task.py`、`backend/services/task_access.py`：TaskOwnership 持久化和访问校验
> - [E2｜代码] `backend/common/llm/snapshot.py`：ProviderSnapshot frozen dataclass + sanitized()
> - [E2｜代码] `backend/common/events/`：SSE 事件推送
> - [E2｜代码] `backend/common/trace/recorder.py`：TraceRecorder
> - [E1｜运行] `outputs/` 中确实存在各模块的 `run_manifest.json` 文件

---

## 5. 核心模块与功能拆解

> **本章核心问题**：11 个业务模块和主要公共能力分别承担什么责任，输入输出与当前状态如何。

### 5.1 业务模块组织

业务模块按法域组织。`config/module_registry.json` 是模块身份唯一权威源（本文直接读取确认 11 个条目），API 路由、前端任务模板、前端注册表、CLI 案例和评测数据均使用模块标识绑定。

#### 中国法域

##### MOD-001：`cn.transfer_diagnosis` — 合规路径诊断

| 项目 | 内容 |
|---|---|
| 模块ID | `cn.transfer_diagnosis` |
| 前端键 | `diagnosis` |
| API 前缀 | `/api/v1/diagnosis` |
| 生命周期 | `active` |
| 功能类型 | 路径判断 |
| 核心输出 | 路径结论报告（含命中规则、法规依据、缺失事实） |

该模块是中国数据出境合规链路的入口。规则引擎加载静态规则进行确定性判断（豁免短路、CIIO、重要数据、敏感个人信息阈值），识别安全评估/标准合同认证/豁免路径，输出命中规则列表、法规 source_id 匹配和缺失事实。RAG 用于补充法规依据原文。支持三态输入（结构化字段/自然语言/混合）。

> **证据｜EVIDENCE**
> - [E2｜代码] `backend/domains/cn/transfer_diagnosis/` — 完整模块实现
> - [E2｜配置] `config/module_registry.json` 第 1 条
> - [E1｜运行] `CLI-006`：`diagnosis` 案例通过

##### MOD-002：`cn.security_assessment` — 安全评估

| 项目 | 内容 |
|---|---|
| 模块ID | `cn.security_assessment` |
| 前端键 | `assessment` |
| API 前缀 | `/api/v1/assessment` |
| 生命周期 | `active` |
| 功能类型 | 草案生成 |
| 核心输出 | Markdown / DOCX / PDF 安全评估报告、ZIP 输出包及 JSON/XLSX 结构化附件 |

面向需要申报数据出境安全评估的企业。采集企业画像、境外接收方、数据字段和安全措施，构建事实包和证据链，生成 gap_items 并按 HIGH/MEDIUM/LOW/BLOCKER 分级。HIGH/BLOCKER 风险可触发得理 API 增强检索。通过 GenerationContextPack 组装规则结论、检索结果和引用允许列表后调用 LLM 逐章节生成。

> **证据｜EVIDENCE**
> - [E2｜代码] `backend/domains/cn/security_assessment/` — 完整模块实现
> - [E1｜运行] `CLI-006`：`assessment` 案例通过

##### MOD-003：`cn.document_review` — 文档专项智能审查

| 项目 | 内容 |
|---|---|
| 模块ID | `cn.document_review` |
| 前端键 | `review` |
| API 前缀 | `/api/v1/review` |
| 生命周期 | `active` |
| 功能类型 | 审阅 |
| 核心输出 | 审查报告 + 批注修订版 DOCX |

支持 PDF/DOCX/MD 上传，按条款结构切分，依据数据合规专项规则和法域知识库逐条审查、风险标注和修改建议生成。聚焦数据出境、个人信息保护和安全义务等专项内容。

> **证据｜EVIDENCE**
> - [E2｜代码] `backend/domains/cn/document_review/`
> - [E2｜配置] `resources/rules/cn/review_rulebook.json` 被生产代码读取
> - [E1｜运行] `CLI-006`：`review` 案例通过

##### MOD-004：`cn.pipia` — 个人信息保护影响评估

| 项目 | 内容 |
|---|---|
| 模块ID | `cn.pipia` |
| 前端键 | `pipia` |
| API 前缀 | `/api/v1/pipia` |
| 生命周期 | `active` |
| 功能类型 | 草案生成 |
| 核心输出 | PIPIA 报告草案（MD/DOCX/PDF）+ 报告输出包（ZIP） |

依据《个人信息保护法》第 55-56 条，采集处理目的、方式、信息类型和安全措施，执行风险评估和整改建议生成。报告内容可以承载备案准备度与备案指引，但当前实现不会生成独立的标准合同备案表单或备案材料包。

> **证据｜EVIDENCE**
> - [E2｜代码] `backend/domains/cn/pipia/`
> - [E1｜运行] `CLI-006`：`pipia` 案例通过

#### 欧盟法域

##### MOD-005：`eu.scc_review` — 标准合同条款审查

| 项目 | 内容 |
|---|---|
| 模块ID | `eu.scc_review` |
| 前端键 | `eu_scc` |
| API 前缀 | `/api/v1/eu_scc` |
| 生命周期 | `active` |
| 功能类型 | 审阅 |
| 核心输出 | 审查报告 + 批注修订版 DOCX |

##### MOD-006：`eu.bcr_review` — 约束性公司规则审查

| 项目 | 内容 |
|---|---|
| 模块ID | `eu.bcr_review` |
| 前端键 | `bcr` |
| API 前缀 | `/api/v1/bcr` |
| 生命周期 | `active` |
| 功能类型 | 审阅 |
| 核心输出 | BCR 差距分析和审查报告 |

##### MOD-007：`eu.dpia` — 数据保护影响评估

| 项目 | 内容 |
|---|---|
| 模块ID | `eu.dpia` |
| 前端键 | `dpia` |
| API 前缀 | `/api/v1/dpia` |
| 生命周期 | `active` |
| 功能类型 | 草案生成 |
| 核心输出 | DPIA 报告 |

##### MOD-008：`eu.tia` — 传输影响评估

| 项目 | 内容 |
|---|---|
| 模块ID | `eu.tia` |
| 前端键 | `tia` |
| API 前缀 | `/api/v1/tia` |
| 生命周期 | `active` |
| 功能类型 | 草案生成 |
| 核心输出 | TIA 报告 |

> **证据｜EVIDENCE**（EU 四个模块）
> - [E2｜代码] `backend/domains/eu/{scc_review,bcr_review,dpia,tia}/` — 四个独立领域包
> - [E2｜配置] `config/module_registry.json` 第 5-8 条
> - [E1｜运行] `CLI-006`：4 个 EU 模块案例全部通过

#### 美国法域

##### MOD-009：`us.eo_14117` — EO 14117 风险评估

| 项目 | 内容 |
|---|---|
| 模块ID | `us.eo_14117` |
| 前端键 | `us_14117` |
| API 前缀 | `/api/v1/us_14117` |
| 生命周期 | `active` |
| 功能类型 | 路径判断 + 风险评估 |
| 核心输出 | EO 14117 风险评估报告 |

规则引擎约 1,302 行（`backend/domains/us/eo14117/rule_engine.py`），覆盖六类敏感个人数据、政府相关数据、受关注国家和主体、数据经纪、云服务、投资/雇佣/供应商关系等触发条件。输出禁止交易/受限交易/允许交易等级。

##### MOD-010：`us.eo_14117_flow_review` — EO 14117 数据流审查

| 项目 | 内容 |
|---|---|
| 模块ID | `us.eo_14117_flow_review` |
| 前端键 | `cn_flow`（历史兼容键） |
| API 前缀 | `/api/v1/cn-flow` |
| 生命周期 | `legacy-compatible` |
| 功能类型 | 数据流审查 |
| 核心输出 | 数据流审查报告 |

##### MOD-011：`us.cpra` — CPRA 合规评估

| 项目 | 内容 |
|---|---|
| 模块ID | `us.cpra` |
| 前端键 | `cpra` |
| API 前缀 | `/api/v1/cpra` |
| 生命周期 | `active` |
| 功能类型 | 填表清单 |
| 核心输出 | XLSX 差距清单 + 摘要报告 |

> **证据｜EVIDENCE**（US 三个模块）
> - [E2｜代码] `backend/domains/us/{eo14117,eo14117_flow_review,cpra}/`
> - [E2｜代码] `backend/domains/us/eo14117/rule_engine.py` — 约 1,302 行规则代码
> - [E2｜配置] `config/module_registry.json` 第 9-11 条（`us.eo_14117_flow_review` 标记为 `legacy-compatible`）
> - [E1｜运行] `CLI-006`：3 个 US 模块案例全部通过

### 5.2 公共能力组件

> 以下 `MOD-101`—`MOD-106` 是系统组件 ID，不是 `module_registry.json` 中的业务模块 ID。

#### MOD-101：LLM Provider 管理

核心代码位置：`backend/common/llm/client.py`、`backend/common/llm/snapshot.py`、`backend/common/llm/context.py`、`backend/services/runtime_client_refresher.py`

- 从 `.env` 和 `storage/runtime_settings.json` 读取 Provider 配置
- 保存前两步健康探测：模型列表接口（验证 URL+鉴权）→ 最小生成请求（验证模型可用+额度充足）
- 六类错误分类：模型不存在、余额不足、鉴权失败、限流、超时、网络错误
- 健康结果缓存 15 分钟
- 异步任务提交时复制不可变 `ProviderSnapshot`（frozen dataclass，`ContextVar` 绑定到任务线程）
- 生产环境（`APP_ENV=production`）在任务创建前执行健康门禁，不健康时返回 503
- Key 不进日志、Trace、API 响应和 RunManifest（`sanitized()` 删除 Key，保留 SHA-256 指纹）

#### MOD-102：本地多索引 RAG

核心代码位置：`backend/common/rag/`

- 3 个法域 × 5 类资源，共 15 个逻辑索引（legal/workflow/standard_clause/template/testcase）
- SHA-256 确定性哈希（替换原 Python `hash()` 随机化）映射为 384 维向量
- 向量相似度 + 关键词检索并行 → RRF 融合 → UsagePolicyFilter 过滤
- 中国法域优先多索引，失败时降级到单索引 → 兼容回退
- 得理 API 条件触发：置信度不足 / HIGH-BLOCKER 风险 / 最新法规需求 / 本地版本过期
- 索引版本管理：不兼容自动重建（Schema `v3.2`，`sha256-v1` + 384d）

#### MOD-103：Citation 管理

核心代码位置：`backend/common/citation/`

- LLM 只使用预先批准的 `citation_id` 白名单
- 后处理校验：`citation_id` 是否存在 → `source_id` 在知识库 → 条号唯一解析
- 四种 CitationResolution：`exact_article`（精确条文）/ `source_overview`（来源概览）/ `external_verified`（外部来源）/ `unresolved`（无法解析）
- 34 组重复定位键降级为 `source_overview`，不提供精确跳转
- 历史 CitationMap 累计 650 份文件、16,681 条引用项
- 前后端三层引用交互组件：`InlineCitation` → `CitationPopover` → `CitationArticleDrawer`
- 引用点击统一站内受控交互（非 `window.open` 新开页面）

#### MOD-104：报告渲染

核心代码位置：`backend/common/render/`

- 共享层提供 `ReportDocument`（`metadata + sections[] + citations[]`）、`ContentAdapter`、Markdown/PDF 渲染器和模板渲染工具
- 安全评估等部分路径会构造 `ReportDocument`；PIPIA、BCR、TIA、CPRA 等模块主要直接调用 Markdown/DOCX/PDF 模板渲染工具
- 模块支持的输出格式并不统一，不能把 `ReportDocument → Markdown/HTML/DOCX/PDF` 视为所有业务模块的强制契约
- 12 个模块/路径（含 v0 legacy）均有可打开 PDF（pypdf 验证 `%PDF` 文件头有效）
- 14 个前后端规范化 Golden Cases 确保 Markdown 逐字一致
- 前端使用 `react-markdown` + GFM 渲染，`PdfViewer` 组件管理鉴权 Blob 请求

#### MOD-105：运行可观测

核心代码位置：`backend/common/trace/recorder.py`、`backend/common/events/`

- SSE 事件实时推送：`task_started`、`tool_start/result`、`llm_call`（含 Token，标注来源）、`node_completed`、`task_completed/failed`
- RunManifest 落盘：run_id、状态、耗时、脱敏 ProviderSnapshot、LLM 调用次数+Token、fallback、输入 SHA-256 摘要、产物列表
- Trace Manifest 记录节点和工具调用的 `queued_at / started_at / ended_at / duration / status`
- 可选导出 OpenTelemetry GenAI semantic conventions（版本化适配层）
- 前端双层观察：普通用户视图（进度+结论摘要）vs 审计视图（事件时间线+Token+RAG命中）

#### MOD-106：任务和产物管理

核心代码位置：`backend/common/tasks/`、`backend/models/task.py`、`backend/services/task_access.py`、`backend/api/v1/endpoints/artifacts.py`

- `TaskOwnershipModel` 持久化 `task_id → user_id` 映射
- 产物访问通过 `artifact_id` 查询归属链（artifact → run → task → owner）
- 9 个异步模块事件、引用、重试接口统一经 `assert_task_access` 鉴权
- 物理内容按 `content_hash` 去重；逻辑产物按 `artifact_id / role / format` 保留
- 预览：HTML、PDF、DOCX、MD、TXT、JSON、CSV；下载：XLSX、ZIP
- 产物分组：输入材料 / 过程证据 / 最终报告 / 数据附件

---

## 6. 数据、接口、配置与外部依赖

> **本章核心问题**：系统依赖哪些关键数据对象、接口、配置和外部服务。

### 6.1 核心数据和契约

| Asset ID | 数据/契约 | 位置 | 用途 |
|---|---|---|---|
| `DATA-001` | 法律知识库 | `resources/legal/` | 69 来源、1,672 条登记、法规原文和 RAG 索引 |
| `DATA-002` | 模块注册表 | `config/module_registry.json` | 跨前后端模块身份唯一权威源，11 个条目 |
| `DATA-003` | 路由基线 | `backend/api/tests/route_baseline.json` | 102 条显式路由的契约测试基线 |
| `DATA-004` | ReportDocument | `backend/common/render/report_model.py` | 部分渲染路径采用的共享语义模型；不是全模块强制中间格式 |
| `DATA-005` | CitationMap | `outputs/{module}/{task}/outputs/citation_map.json` | 引用与来源、条号、片段、解析状态的映射 |
| `DATA-006` | RunManifest | `outputs/{module}/{task}/run_manifest.json` | 任务统一运行账本（状态+Token+Provider+产物清单） |
| `DATA-007` | Trace Manifest | 应用：`outputs/{module}/{task}/trace/manifest.json`；CLI：`runs/{module}/{run_id}/trace/manifest.json` | 节点和工具调用的技术轨迹 |
| `DATA-008` | TaskOwnershipModel | `backend/models/task.py`、`backend/services/task_access.py` | `task_id → user_id` 持久化归属及访问校验 |
| `DATA-009` | CLI 案例 | `backend/tests/*/cases/*.json` | 分布在 11 个模块测试目录中的 15 个 JSON 案例 |
| `DATA-010` | Benchmark 数据集 | `benchmarks/datasets/` | Product Smoke (17+14) + 规模化 RAG (380) |
| `DATA-011` | 运行时 Provider 配置 | `storage/runtime_settings.json` | Provider 配置与健康状态，权限 `0o600` |
| `DATA-012` | 规则引擎规则 | `resources/rules/` | `cn/review_rulebook.json` 被生产代码读取 |

### 6.2 API 接口

| Asset ID | 前缀 | 说明 | 代码位置 |
|---|---|---|---|
| `API-001` | `/health` | 健康检查 | `backend/app.py` |
| `API-002` | `/api/v0/` | 文件上传和历史任务兼容，7 条路由 | `backend/api/v0/router.py` |
| `API-003` | `/api/v1/diagnosis` | CN 合规路径诊断 | `backend/domains/cn/transfer_diagnosis/` |
| `API-004` | `/api/v1/assessment` | CN 安全评估 | `backend/domains/cn/security_assessment/` |
| `API-005` | `/api/v1/review` | CN 文档审查 | `backend/domains/cn/document_review/` |
| `API-006` | `/api/v1/pipia` | CN PIPIA | `backend/domains/cn/pipia/` |
| `API-007` | `/api/v1/eu_scc` | EU SCC 审查 | `backend/domains/eu/scc_review/` |
| `API-008` | `/api/v1/bcr` | EU BCR 审查 | `backend/domains/eu/bcr_review/` |
| `API-009` | `/api/v1/dpia` | EU DPIA | `backend/domains/eu/dpia/` |
| `API-010` | `/api/v1/tia` | EU TIA | `backend/domains/eu/tia/` |
| `API-011` | `/api/v1/us_14117` | US EO 14117 风险评估 | `backend/domains/us/eo14117/` |
| `API-012` | `/api/v1/cn-flow` | US EO 14117 流程审查（历史键） | `backend/domains/us/eo14117_flow_review/` |
| `API-013` | `/api/v1/cpra` | US CPRA 合规评估 | `backend/domains/us/cpra/` |
| `API-014` | `/api/v1/system/settings/` | Provider 配置与健康检查 | `backend/api/v1/endpoints/` |
| `API-015` | `/api/v1/events/` | SSE 事件订阅 + RunManifest 读取 | `backend/api/v1/endpoints/events.py` |
| `API-016` | `/api/v1/citations/` | 引用详情查询 | `backend/api/v1/endpoints/citations.py` |
| `API-017` | `/api/v1/artifacts/` | 产物预览和下载 | `backend/api/v1/endpoints/artifacts.py` |

### 6.3 前端页面与交互

| Asset ID | 页面/组件 | 代码位置 | 作用 |
|---|---|---|---|
| `UI-001` | SPA 入口 | `frontend/src/main.tsx` | 前端启动入口 |
| `UI-002` | Landing | `frontend/src/components/landing/` | 平台导览 |
| `UI-003` | 认证 | `frontend/src/pages/auth/`、`components/auth/` | 注册、登录、会话 |
| `UI-004` | 任务空间 | `frontend/src/components/workspace/` | 按法域选择任务 |
| `UI-005` | 工作台 | `frontend/src/components/workspace/` | 资源、运行、AI 对话三栏布局 |
| `UI-006` | 知识库中心 | `frontend/src/components/report-center/` | 法规检索和条文浏览 |
| `UI-007` | 设置 | `frontend/src/components/`（设置组件） | Provider 和得理 API 配置 |
| `UI-008` | InlineCitation | `frontend/src/components/citation/` | 正文引用角标 |
| `UI-009` | CitationPopover | `frontend/src/components/citation/` | hover/focus 摘要卡片 |
| `UI-010` | CitationArticleDrawer | `frontend/src/components/citation/` | 站内条文抽屉（含前后文导航和返回位置） |
| `UI-011` | RunTranscript | `frontend/src/components/workspace/` | 运行时间线和 Token 统计 |
| `UI-012` | ResourcePanel | `frontend/src/components/workspace/` | 输入/产物文件管理 |
| `UI-013` | ModuleRunPanel | `frontend/src/components/workspace/` | 表单填写、运行、结果预览（3,751 行大文件） |
| `UI-014` | PdfViewer | `frontend/src/components/common/` | 鉴权 Blob PDF 预览 |

### 6.4 配置和环境变量

| Asset ID | 变量/文件 | 是否必需 | 代码来源 |
|---|---|---|---|
| `CFG-001` | `APP_ENV` | 否（默认 `development`） | `backend/core/settings.py` |
| `CFG-002` | `LLM_API_KEY` | 生产环境是 | `.env.example` + `backend/core/settings.py` |
| `CFG-003` | `LLM_BASE_URL` | 生产环境是 | `.env.example` |
| `CFG-004` | `LLM_MODEL` | 否 | 前端设置页可选 |
| `CFG-005` | `DELILEGAL_API_KEY` | 条件需要 | `.env.example` |
| `CFG-006` | `DATABASE_URL` | 否（默认 SQLite） | `backend/core/db.py` |
| `CFG-007` | `STORAGE_DIR` | 否（默认 `storage/`） | `backend/core/settings.py` |
| `CFG-008` | `OUTPUTS_DIR` | 否（默认 `outputs/`） | `backend/core/settings.py` |
| `CFG-009` | `.env.example` | 模板 | 仓库根目录 |
| `CFG-010` | `storage/runtime_settings.json` | 运行时 | 权限 `0o600`，含 Provider 配置（密钥脱敏） |

### 6.5 外部依赖

#### DEP-001：OpenAI-compatible LLM Provider

用途：报告生成、语义理解和对话。  
代码位置：`backend/common/llm/client.py` — 统一 `LLMClient` 封装。  
当前状态（2026-08-04）：默认腾讯混元 `hy3-preview` 模型不可用（ENV-BLOCK），其他候选模型遇下线或余额不足。Provider 健康门禁已实现——生产环境下无健康 LLM 时直接返回 503。

#### DEP-002：得理法律 API

用途：在本地检索置信度不足、HIGH/BLOCKER 风险、最新法规/案例需求或本地版本可能过期时增强检索。  
代码位置：`backend/integrations/delilegal.py`。  
已知限制：当前适配器只保留标题、来源、摘要，丢弃了得理返回的稳定 ID、条号、效力状态和原文定位——因此尚不能直接作为可信引用入库来源。该限制已在代码中标注为 P1 待修复项。

### 6.6 权限和敏感信息

- Token-based 认证：前端 `auth/` 模块管理 Token，后端 `Depends(get_current_user)` 校验
- 未登录请求返回 401
- 任务、事件、CitationMap、引用详情、产物按 `TaskOwnershipModel` 做用户级隔离
- 非所有者访问统一 403/404（不泄露任务是否存在）
- API Key 不回显、不进日志、不进 Trace、不进 RunManifest
- `ProviderSnapshot.sanitized()` 删除 Key，仅保留 SHA-256 指纹
- `ProviderSnapshot.__repr__` 禁输出 `api_key` 字段
- `storage/runtime_settings.json` 权限 `0o600`

> **证据｜EVIDENCE**
> - [E2｜代码] `backend/api/v1/endpoints/artifacts.py`：产物访问从路径字符串回退改为 Artifact ID 所有权校验
> - [E2｜代码] `backend/api/v1/endpoints/events.py`：`assert_task_access` 鉴权
> - [E2｜代码] `backend/models/task.py`、`backend/services/task_access.py`：`TaskOwnershipModel` 与归属校验
> - [E1｜测试] 30 项聚焦测试覆盖持久化、重启语义、9 模块提交/状态/重试和双用户隔离

---

## 7. 验证证据、质量状态与当前边界

> **本章核心问题**：当前可重复验证的结果是什么，质量达到什么水平，哪些结论不能被这些数字支持。

### 7.1 自动化验证快照

以下均在 2026-08-04 直接执行并记录结果：

| Asset ID | 验证项 | 命令 | 结果 | 耗时 |
|---|---|---|---|---|
| `VER-001` | 后端全量测试 | `uv run --frozen pytest -q` | 528 passed, 1 warning | 57.76s |
| `VER-002` | 前端单元测试 | `npm --prefix frontend test -- --run` | 48 passed / 15 files | 6.58s |
| `VER-003` | 前端生产构建 | `npm --prefix frontend run build` | 342 modules, 通过 | — |
| `VER-004` | Python 编译 | `uv run --frozen python -m compileall -q backend` | 退出码 0 | — |
| `VER-005` | 仓库卫生 | `uv run --frozen python scripts/check_repository_hygiene.py` | 963 个文件通过 | — |
| `VER-006` | CLI Smoke | `uv run --frozen python -m backend.harness.runner all --no-llm` | 15 PASS / 0 FAIL / 11 modules | ≈2-3 min |

> **边界**：唯一警告为 Starlette TestClient 的 httpx 弃用提示，不影响本轮测试结论；外部 LLM、得理法律 API、浏览器 E2E、生产部署和法律专家 Gold 未完成真实验证，因此 front matter 标记为 `partially_verified`。

### 7.2 Product Smoke 历史快照

以下结果来自项目事实快照，证据等级为 E5 历史信息；本次未重新运行 Smoke 评测脚本，因此不计入 §7.1 的当前 E1 验证结果：

| Asset ID | 维度 | 案例数 | 主要指标 | 结果 |
|---|---|---|---|---|
| `VER-007` | Retrieval | 17 | Recall@K / MRR / 跨法域污染 | 1.0 / 0.7471 / 0 |
| `VER-008` | Generation | 14 | Issue Recall / Citation correctness / Leakage | 0.7143 / 1.0 / 0 |

解释边界：
- Retrieval Smoke 只证明固定案例回归链路（17 个确定案例）；
- Citation correctness 当前 = 期望 source ID 覆盖率，≠ 法律引用完全正确；
- 这些结果不能证明系统在开放真实法律任务上的总体正确性。

### 7.3 规模化 RAG 历史快照

以下结果来自 `docs/handoff/DataComplyFlow_产品能力补强与后续工作清单_20260719.md`，证据等级为 E5 历史信息。本次只静态核对评测代码和 380 条合成数据集结构，没有重新执行规模化评测：

| Asset ID | 数据集 | Top-K | 对比模式 | 关键指标 |
|---|---|---|---|---|
| `VER-009` | 240 正例 + 140 负例（合成数据） | 5 | vector vs hybrid | Recall@5 均为 0.150；MRR 0.140；SafeReject 0.243 |

模块级结果：
- BCR、CN Flow、SCC 正例 Recall 为 0（知识库覆盖或查询-索引不匹配，`OPEN-002`）
- CPRA 为 0.042；Diagnosis 为 0.125
- Vector 与 Hybrid 完全相同（Hybrid 策略可能未生效，`LIM-002`）

> **结论**：历史固定 Smoke 与历史规模化评测之间存在显著落差，提示一般化检索质量不足。由于本轮未重跑，这一判断是待复现的风险信号，不是当前环境的运行证明。

### 7.4 当前能力结论

| 能力 | 结论 | 边界 |
|---|---|---|
| 11 模块离线执行 | 15/15 CLI `--no-llm` 通过 | 不证明外部 LLM 可用 |
| 前后端工程基线 | 528 + 48 测试通过，构建成功 | 未覆盖生产负载和线上可用性 |
| 路由和模块契约 | 102 条无重复路由，`module_registry.json` 为唯一身份源 | 直接读取确认 |
| 引用交互 | 四类 CitationResolution + 站内受控交互 | 34 组重复定位只能降级 |
| 多格式报告 | 12/12 路径的 PDF 回归有效；共享渲染工具已被多模块复用 | ReportDocument 仅用于部分路径，输出格式因模块而异 |
| 数据隔离 | 任务、事件、引用、产物均有归属校验（30 项聚焦测试通过） | 未做渗透测试或并发安全测试 |
| RAG 一般化 | 历史快照 Recall@5 为 0.150 | 本轮未重跑；需先复现，再审计索引、查询和路由 |
| 运行恢复 | RunManifest 可落盘 + 通过 API 安全读取 | 任务执行器和 SSE 为内存态 |

### 7.5 已知限制

| Asset ID | 限制 | 影响 |
|---|---|---|
| `LIM-001` | 历史规模化 RAG 快照 Recall@5 仅 0.150，尚未在本轮复现 | 开放场景检索可靠性存在风险 |
| `LIM-002` | 历史快照中 Vector 与 Hybrid 结果完全一致，尚未在本轮复现 | Hybrid 策略可能未实际生效 |
| `LIM-003` | 历史快照中 EU SCC、EU BCR、US EO 14117、US Privacy 生成案例 Issue Recall 为 0 | 生成问题覆盖和 Gold 对齐存在风险 |
| `LIM-004` | US 三个模块无前端一键填充运行入口 | CLI 可测，但前端体验覆盖不完整 |
| `LIM-005` | 任务执行器和 SSE 为内存态 | 服务重启后不能恢复任务状态和事件时间线 |
| `LIM-006` | 得理适配器丢弃稳定 ID、条号、效力状态和原文定位 | 外部结果不能直接可信入库 |
| `LIM-007` | 34 组重复定位键 | 引用只能降级为 source_overview |
| `LIM-008` | 外部 LLM 模型、额度和网络依赖（ENV-BLOCK） | 生产生成链可能被阻断（代码侧已有健康门禁） |
| `LIM-009` | 2026-08-04 运行目录快照中 `outputs/` 约 720 MB、25,519 文件 | 运行产物持续增长，需要清理和保留策略；该数字不随 Commit 固定 |

### 7.6 未决事项

| Asset ID | 未决事项 | 缺少的证据 |
|---|---|---|
| `OPEN-001` | Hybrid 与 Vector 完全相同的代码根因 | 评测 Runner 调用链审计 |
| `OPEN-002` | BCR、CN Flow、SCC Recall 为 0 的根因 | 数据集、QueryPlan、索引和知识覆盖全面审计 |
| `OPEN-003` | 34 组重复定位的最终消歧 | 法律内容负责人审校 |
| `OPEN-004` | 生产 Provider 当前是否健康 | 真实配置和健康探测 |
| `OPEN-005` | 生产部署拓扑和持久化方案 | 部署配置和运行环境 |
| `OPEN-006` | 浏览器 E2E 测试 | 当前代码仓库中不存在 E2E 测试 |
| `OPEN-007` | 法律专家 Gold 验证 | 需法律团队提供/确认的 Gold 案例 |

### 7.7 后续优先级

```text
P0 已完成：数据隔离、证据真实性（移除机械补引用）、确定性哈希（SHA-256）、Provider 健康门禁
→ P1 Benchmark 数据与索引一致性审计（OPEN-001/002）
→ P1 RAG 路由/模式/拒答修复（LIM-001/002）
→ P1 EU/US Issue 失败案例归因与回归（LIM-003）
→ P1 中国路径专家 Gold：12—20 个案例（OPEN-007）
→ P2 Claim/Evidence/Citation 最小试点
→ P2 任务执行器和事件流持久化（LIM-005）
→ P3 Ruff/Mypy/ESLint lint 工具、依赖升级、outputs 清理策略（LIM-009）
```

---

## 8. 阅读、复用与维护指南

> **本章核心问题**：团队成员或 AI 应按什么顺序理解仓库，修改某类资产需要同步检查什么。

### 8.1 推荐代码阅读顺序

1. `README.md`、`pyproject.toml`、Git 分支和 Commit
2. `config/module_registry.json` —— 理解 11 个模块的身份和路由
3. `backend/app.py` + `backend/main.py` + `backend/core/settings.py` —— 应用工厂、导出入口和配置
4. `backend/api/v1/router.py` —— 路由注册（94 条 v1 路由）
5. `backend/api/v0/router.py` —— 历史兼容路由（7 条 v0 路由）
6. `backend/domains/cn/transfer_diagnosis/` —— 从最简单的中国路径诊断开始
7. `backend/domains/cn/security_assessment/` —— 最完整的 AI 调用链示例
8. 其余 `backend/domains/{cn,eu,us}/` 模块
9. `backend/common/llm/`、`backend/common/rag/` —— 理解 AI 和检索机制
10. `backend/common/citation/`、`backend/common/render/` —— 引用和产物
11. `frontend/src/components/workspace/ModuleRunPanel.tsx` —— 前端核心（3,751 行）
12. `frontend/src/lib/module-registry.ts`、`task-templates.ts`
13. `backend/harness/` —— CLI 和 Smoke 测试实现
14. `benchmarks/` 和 `scripts/`
15. `docs/standards/` → `docs/handoff/` → `docs/archive/`

### 8.2 按目标阅读

| 目标 | 推荐路径 |
|---|---|
| 理解中国路径诊断 | `module_registry.json → API-003 → backend/domains/cn/transfer_diagnosis → resources/rules → RAG` |
| 理解报告生成 | `API-004 → GenerationContextPack → MOD-101(LLM) → MOD-104(Render) → MOD-103(Citation) → DATA-004/005` |
| 理解引用体系 | `resources/legal → MOD-103(Citation) → DATA-005(CitationMap) → API-016 → UI-008/009/010` |
| 理解任务隔离 | `DATA-008(TaskOwnership) → assert_task_access → API-015/016/017 → MOD-106` |
| 理解 Provider 门禁 | `.env + CFG-002/003/004/010 → MOD-101(Health Probe) → ProviderSnapshot → 生产门禁 → RunManifest` |
| 理解评测 | `benchmarks/datasets → smoke_eval.py / rag_retrieval_eval.py → VER-007/008/009` |
| 理解 US 历史兼容 | `module_registry.json → MOD-010(cn_flow legacy) → API-012(/cn-flow) → us.eo_14117_flow_review` |
| 理解前端工作流 | `UI-013(ModuleRunPanel) → UI-005(工作台三栏) → UI-011(RunTranscript) → UI-008/009/010(引用交互)` |

### 8.3 修改影响面

| 变更 | 必须同步检查 |
|---|---|
| 修改模块身份 | `module_registry.json` → API 路由 → `task-templates.ts` → `module-registry.ts` → Harness cases → Benchmark datasets → 测试 |
| 新增业务模块 | 注册表 → 后端领域包（`backend/domains/` 新建子包）→ v1 路由注册 → 前端任务卡+表单+payload → CLI 案例 → 评测 → 权限 |
| 修改法规知识 | `resources/legal/` 原文+条文登记 → 重建 RAG 索引 → CitationResolution 重新校验 → 重复定位消歧 → RAG 评测重跑 |
| 修改 Provider | 配置+健康探测+15min 缓存 → ProviderSnapshot 快照 → 生产门禁 → RunManifest 脱敏 |
| 修改报告语义 | `ReportDocument`/`ContentAdapter` + 各领域模板渲染路径 → 前端 Markdown/PDF 预览 → Golden Cases 一致性 |
| 修改任务状态 | TaskOwnership → 事件流 → 重试 → RunManifest → Trace → `RunTranscript` 前端组件 |
| 修改产物路径 | ArtifactRecord → 所有权校验 → 预览下载 → 内容去重 → 清理策略 |
| 修改检索模式 | QueryPlan → 多索引 Orchestrator → RRF → UsagePolicyFilter → Smoke/规模化评测 |

### 8.4 下游复用

| 下游任务 | 优先读取章节 |
|---|---|
| 软件需求规格说明书（SRS） | 第2、5、6、7章 |
| 方案设计说明书 | 第3、4、5、6章 |
| 具体实现说明书 | 第3、4、5、6章 + 附录A/B/C（直接使用代码路径和对象名） |
| 软件功能说明文档 | 第2、5、6章 + 附录C |
| 系统测试报告 | 第7章 + 附录B |
| AI 技术综合说明 | 第4.3/4.4、5.2、6.1、7章 |
| 项目答辩和计划书 | 快速入口 + 第2章 + 第7章 |
| AI 代码审查 | 全文（优先 E1/E2 证据），审查结论引用代码位置 |
| 代码修改任务 | 第5、6、8.3 |

### 8.5 基线更新规则

1. 代码、配置、测试或运行环境实质变化后，更新 front matter 的 `commit` 和 `analysis_date`；
2. 重新运行 `CLI-003`—`CLI-006` 更新 §7.1 验证快照；
3. 对比 `module_registry.json` 更新附录C；
4. 将不再成立的事实记录到附录E，不直接无痕覆盖；
5. 检查下游文档（需求/设计/实现/测试）是否依赖已失效结论。

---

## 附录A：关键文件与目录索引

| 资产 | 路径 | 说明 |
|---|---|---|
| 后端入口 | `backend/app.py`、`backend/main.py` | `create_app()` 创建应用，`backend.main:app` 对外导出 |
| 前端入口 | `frontend/src/main.tsx` | React SPA 入口 |
| 应用配置 | `backend/core/settings.py` | `Settings` 类，读 `.env` |
| v1 API | `backend/api/v1/` | 94 条路由 |
| v0 API | `backend/api/v0/` | 7 条兼容路由 |
| CN 领域 | `backend/domains/cn/` | 4 个注册模块（transfer_diagnosis/security_assessment/document_review/pipia） |
| EU 领域 | `backend/domains/eu/` | 4 子目录（scc_review/bcr_review/dpia/tia） |
| US 领域 | `backend/domains/us/` | 3 子目录（eo14117/eo14117_flow_review/cpra） |
| US 规则引擎 | `backend/domains/us/eo14117/rule_engine.py` | ~1,302 行 |
| 公共能力 | `backend/common/` | 15 个一级子目录 |
| LLM 客户端 | `backend/common/llm/client.py` | 统一 LLM 客户端 |
| RAG 入口 | `backend/common/rag/service.py` | 检索服务入口 |
| RAG 编排 | `backend/common/rag/orchestrator.py` | 多索引编排 + HashingEmbedder |
| Citation | `backend/common/citation/` | 引用注册、校验、规范化 |
| 报告渲染 | `backend/common/render/` | 共享语义模型、适配器、模板工具和渲染器；各模块采用程度不同 |
| Trace | `backend/common/trace/recorder.py` | TraceRecorder |
| 事件 | `backend/common/events/` | SSE 事件 |
| 异步任务 | `backend/common/tasks/` | 内存态执行、状态、重试和 RunManifest 写入 |
| 任务归属 | `backend/models/task.py`、`backend/services/task_access.py` | TaskOwnership 持久化与访问校验 |
| 运行时容器 | `backend/core/container.py` | AppContainer 应用级对象组装 |
| 运行时刷新 | `backend/services/runtime_client_refresher.py` | 重绑模块级长寿命实例的客户端 |
| 核心配置 | `backend/core/` | settings + db + runtime_settings |
| 得理适配 | `backend/integrations/delilegal.py` | 得理法律 API |
| 模块注册 | `config/module_registry.json` | 11 个条目 |
| 法律资源 | `resources/legal/` | 69 来源、1,672 条登记 |
| 规则资源 | `resources/rules/` | `cn/review_rulebook.json` |
| 报告模板 | `resources/templates/{cn,eu,us}/` | 按法域分 |
| CLI Harness | `backend/harness/`、`backend/tests/*/cases/` | runner + viewer；15 个案例分布在模块测试目录 |
| Benchmark | `benchmarks/` | datasets + smoke_eval + rag_retrieval_eval |
| 前端核心组件 | `frontend/src/components/workspace/ModuleRunPanel.tsx` | 3,751 行 |
| 前端引用组件 | `frontend/src/components/citation/` | InlineCitation/Popover/Drawer |
| 当前规范 | `docs/standards/` | 6 份活动规范 |
| 事实快照 | `docs/handoff/` | 7 份交接材料 |
| 历史材料 | `docs/archive/` | 已归档批次和模板 |
| 本地状态 | `storage/` | SQLite、上传、会话 |
| 业务产物 | `outputs/` | 按 `{module}/{task}/` |
| CLI 运行记录 | `runs/` | 按 `{module}/{run_id}/` |

---

## 附录B：命令索引

```bash
# 后端
uv run uvicorn backend.main:app --reload --port 8000

# 前端
cd frontend && npm ci && npm run dev

# 后端测试
uv run --frozen pytest -q

# 前端测试与构建
npm --prefix frontend test -- --run
npm --prefix frontend run build

# Python 编译
uv run --frozen python -m compileall -q backend

# 仓库卫生
uv run --frozen python scripts/check_repository_hygiene.py

# 全模块 CLI Smoke（离线）
uv run --frozen python -m backend.harness.runner all --no-llm

# 查看 CLI 运行结果
python -m backend.harness.viewer <run_id> --summary
python -m backend.harness.viewer <run_id> --events

# Product Smoke 评测
uv run --frozen python scripts/run_smoke_benchmark.py

# 规模化 RAG 评测
uv run --frozen python scripts/run_rag_retrieval_benchmark.py
```

---

## 附录C：核心资产注册表

### C.1 业务模块

| Asset ID | 模块ID | 法域 | 生命周期 | 功能类型 | 核心输出 | CLI | 前端一键测试 |
|---|---|---|---|---|---|---|---|
| `MOD-001` | `cn.transfer_diagnosis` | CN | active | 路径判断 | 路径结论报告 | ✅ | ✅ |
| `MOD-002` | `cn.security_assessment` | CN | active | 草案生成 | MD/DOCX/PDF + ZIP + JSON/XLSX 附件 | ✅ | ✅ |
| `MOD-003` | `cn.document_review` | CN | active | 审阅 | 审查报告+批注DOCX | ✅ | ✅ |
| `MOD-004` | `cn.pipia` | CN | active | 草案生成 | PIPIA 报告草案（MD/DOCX/PDF）+ ZIP 输出包 | ✅ | ✅ |
| `MOD-005` | `eu.scc_review` | EU | active | 审阅 | 审查报告+批注DOCX | ✅ | ✅ |
| `MOD-006` | `eu.bcr_review` | EU | active | 审阅 | 审查报告 | ✅ | ✅ |
| `MOD-007` | `eu.dpia` | EU | active | 草案生成 | DPIA 报告 | ✅ | ✅ |
| `MOD-008` | `eu.tia` | EU | active | 草案生成 | TIA 报告 | ✅ | ✅ |
| `MOD-009` | `us.eo_14117` | US | active | 路径判断+评估 | 风险评估报告 | ✅ | ❌ |
| `MOD-010` | `us.eo_14117_flow_review` | US | legacy-compatible | 数据流审查 | 数据流审查报告 | ✅ | ❌ |
| `MOD-011` | `us.cpra` | US | active | 填表清单 | XLSX+摘要报告 | ✅ | ❌ |

### C.2 公共能力组件

| Asset ID | 组件 | 核心责任 | 代码位置 |
|---|---|---|---|
| `MOD-101` | Provider 管理 | 配置、探测、快照、门禁、脱敏、运行时重绑 | `backend/common/llm/` + `backend/core/runtime_settings.py` + `backend/services/runtime_client_refresher.py` |
| `MOD-102` | RAG | 多索引、向量/关键词、RRF、使用策略 | `backend/common/rag/` |
| `MOD-103` | Citation | 注册、解析、映射、站内跳转 | `backend/common/citation/` |
| `MOD-104` | Report Rendering | 共享语义模型、内容适配、模板与多格式渲染工具 | `backend/common/render/`；各领域模块含直接模板渲染路径 |
| `MOD-105` | Observability | SSE、RunManifest、Trace、OTel | `backend/common/trace/` + `backend/common/events/` |
| `MOD-106` | Task & Artifact | 任务归属、状态、预览、下载、去重 | `backend/common/tasks/` + `backend/models/task.py` + `backend/services/task_access.py` + `backend/api/v1/endpoints/artifacts.py` |

---

## 附录D：证据账本与未决事项

### D.1 主要证据账本

| 结论 | 证据类型 | 证据位置 |
|---|---|---|
| 11 个业务模块，CN 4/EU 4/US 3 | E2 代码 | `config/module_registry.json` 直接读取 |
| 102 个显式路由（v0 7 + v1 94 + health 1） | E2 配置 | `backend/api/tests/route_baseline.json` |
| 后端 528 passed | E1 运行 | `uv run --frozen pytest -q` 2026-08-04 执行 |
| 前端 48 passed | E1 运行 | `npm --prefix frontend test -- --run` 2026-08-04 执行 |
| 前端构建 342 modules | E1 运行 | `npm --prefix frontend run build` 2026-08-04 执行 |
| CLI Smoke 15 PASS / 11 modules | E1 运行 | `runner.py all --no-llm` 2026-08-04 执行 |
| 仓库卫生 963 文件通过 | E1 运行 | `check_repository_hygiene.py` 2026-08-04 执行 |
| Python 编译通过 | E1 运行 | `compileall -q backend` 2026-08-04 执行 |
| 15 个 RAG 逻辑索引（3 法域×5 类型） | E2 代码 | `backend/common/rag/orchestrator.py` |
| 69 来源、1,672 条登记 | E2 数据 | `resources/legal/registry/regulation_articles.jsonl` |
| CitationMap 650 份/16,681 条 | E5 历史 | `CODE_CURRENT_STATUS_AND_GAPS.md` §2.4 |
| 五层架构（前端→API→领域→公共→基础设施） | E2 代码 | `backend/` 目录结构 + `frontend/` 目录结构 |
| AppContainer 应用级对象组装 | E2 代码 | `backend/core/container.py` |
| 模块级长寿命实例的客户端重绑 | E2 代码 | `backend/services/runtime_client_refresher.py` |
| ProviderSnapshot 不可变快照 | E2 代码 | `backend/common/llm/snapshot.py` + `backend/common/llm/context.py` |
| SHA-256 确定性哈希（替代 Python hash） | E2 代码 | `backend/common/rag/orchestrator.py:HashingEmbedder` |
| TaskOwnershipModel 任务归属 | E2 代码 | `backend/models/task.py` + `backend/services/task_access.py` |
| 产物 Artifact ID 所有权校验 | E2 代码 | `backend/api/v1/endpoints/artifacts.py` |
| Provider 健康探测 + 六类错误分类 | E2 代码 | `backend/common/llm/` |
| 四类 CitationResolution | E2 代码 | `backend/common/citation/output.py` |

### D.2 未决事项

参见第 7.6 节 `OPEN-001`—`OPEN-007`。

---

## 附录E：版本变化记录

| 文档版本 | 日期 | 基线 | 说明 |
|---|---|---|---|
| V1.0 | 2026-08-04 | `5c8d1e3`（材料称） | 依据三份项目材料按模板首次整理 |
| V1.1 | 2026-08-04 | `826e23d` | **直接代码扫描 + 运行验证**：更新全部 Commit、证据类型（E2→E1）、补充完整代码位置、重跑全量测试和 CLI Smoke |
| V1.2 | 2026-08-05 | `826e23d` | **事实一致性复核**：修正混合对象组装架构、路由数量、运行产物路径、ReportDocument 适用范围、PIPIA 输出边界和 Benchmark 证据等级 |

---

> **文档结束**
>
> 本文档 V1.2 以 Commit `826e23d` 的直接代码扫描和部分运行验证为事实基础。后端 528 passed，前端 48 passed，CLI Smoke 15 PASS。E1 结果来自 2026-08-04 实际执行命令；Product Smoke 与规模化 RAG 数值属于未在本轮重跑的 E5 历史快照。外部 LLM、得理法律 API、浏览器 E2E、生产部署和法律专家 Gold 未完成真实验证。
