# DataComplyFlow 全栈模块功能级流水线详解

> 审计日期：2026-08-07  
> 最近更新：2026-08-13（同步 task061–task069 后的结构变化：`backend/harness/` 独立、`backend/common/reporting/` 统一三格式渲染、11 模块口径、pipia 新增案例）
> 审计分支：`new`  
> 覆盖范围：前端（React/TypeScript/Vite）+ 后端（Python/FastAPI）+ 配置层  
> 结论口径：本文描述代码真实实现，非规划或期望

---

## 第一部分：系统全景架构

### 1.1 物理分层

```
项目根 ai4law/
├── frontend/                  ← React SPA（浏览器端）
│   └── src/
│       ├── main.tsx           ← entry
│       ├── App.tsx            ← BrowserRouter + 全局状态
│       ├── api/               ← HTTP 请求层
│       ├── lib/               ← 状态管理、领域模型、工具
│       ├── components/        ← UI 组件
│       ├── features/          ← 业务功能（module-runner, resource-explorer）
│       └── pages/             ← 路由页面
├── backend/                   ← FastAPI 服务端
│   ├── main.py                ← FastAPI 创建入口
│   ├── app.py                 ← create_app() + 数据库初始化
│   ├── common/                ← 公共基础设施
│   │   ├── workflow/          ← WorkflowPipeline + Fact/Issue/Evidence
│   │   ├── llm/               ← LLMClient + module_generator
│   │   ├── rag/               ← RegulationRAGService
│   │   ├── citation/          ← CitationRegistry
│   │   ├── reporting/         ← 统一三格式同源渲染（render_manifest/renderers/render_profiles）
│   │   └── trace/             ← TraceRecorder
│   ├── domains/               ← 业务模块
│   │   ├── cn/                ← 中国（diagnosis/assessment/pipia/review）
│   │   ├── eu/                ← 欧盟（scc/bcr/dpia/tia）
│   │   └── us/                ← 美国（eo14117/cn_flow/cpra）
│   ├── harness/               ← CLI 白盒执行器（runner/viewer/validators/terminal_trace，2026-08 迁出自 tests/）
│   └── integrations/          ← 外部集成
└── config/
    └── module_registry.json   ← 前后端共享的模块注册表
```

### 1.2 端到端数据流（完整链路）

```text
┌─────────────────────────────────────────────────────────────────────────┐
│  浏览器                                                                │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │ 1. 用户创建 TaskSpace → dispatch(create_task_space) → store │      │
│  │ 2. 导航 /workspace/:taskId → WorkspacePage                   │      │
│  │ 3. ModuleRunPanel 渲染模块表单 → 用户填写字段/上传文件       │      │
│  │ 4. 用户点击"运行" → buildXxxPayload(values, files)           │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                              │  HTTP POST                              │
│                              ▼                                         │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │ modules.ts: runModule()                                      │      │
│  │   → requestJson(syncEndpoint, POST, payload)                 │      │
│  │   → apiFetch() → 前端开发代理 (/api → localhost:8000)       │      │
│  └──────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  FastAPI 服务端 (localhost:8000)                                       │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │ backend/main.py → create_app() → 注册路由                    │      │
│  │   ├── /api/v1/assessment/ → assessment_router                │      │
│  │   ├── /api/v1/pipia/      → pipia_router                     │      │
│  │   ... (11 个模块路由)                                         │      │
│  │   ├── /health             → 健康检查                          │      │
│  │   └── /api/v0/files/upload → 文件上传                        │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                              │                                         │
│                              ▼                                         │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │ Service.generate_report(payload, task_id, trace)             │      │
│  │   ├── 使用 WorkflowPipeline (4个模块)                        │      │
│  │   │   或专用 Service 逻辑 (7个模块)                            │      │
│  │   ├── Agent/LLM 调用 → LLMClient.chat()                      │      │
│  │   ├── RAG 检索 → RegulationRAGService.retrieve()             │      │
│  │   ├── 规则引擎 → 确定性判断                                   │      │
│  │   └── 产物渲染 → MD/DOCX/PDF/XLSX/JSON/ZIP                   │      │
│  └──────────────────────────────────────────────────────────────┘      │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │ 返回：                                                       │      │
│  │   Sync:  直接返回 JSON {output_files: {role: path}, ...}     │      │
│  │   Async: 返回 {task_id}，轮询 /tasks/{task_id} 查状态       │      │
│  └──────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  浏览器（结果回流）                                                    │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │ 5. onRunDone() → dispatch(append_run) + dispatch(append_artifacts) │
│  │ 6. store 更新 → WorkspacePage 重新渲染                        │      │
│  │ 7. ResourcePanel 展示产物文件列表（左侧栏）                   │      │
│  │ 8. RunTranscript 展示执行事件链（运行记录）                   │      │
│  │ 9. 组件展示输出文件预览（MD/DOCX→HTML/PDF/XLSX→CSV）         │      │
│  └──────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 第二部分：前端架构详解

### 2.1 入口与路由

**`main.tsx`**：React 18 + StrictMode。检查 URL 参数 `trace_probe=1` 选择 TraceProbe 调试模式，否则默认加载 App。

**`App.tsx`**：四层 Provider 嵌套：

```text
LanguageProvider          ← 中英文切换
  └─ AuthProvider         ← 鉴权上下文（Bearer token）
      └─ AppStoreProvider ← 全局状态（useReducer + localStorage）
          └─ BrowserRouter
              └─ AppShell
```

**路由表（12 个路由）**：

| 路径 | 页面 | 鉴权 | 说明 |
|------|------|:---:|------|
| `/` | HomePage | 否 | 首页+快速开始入口 |
| `/jurisdictions/:code` | JurisdictionHubPage | 否 | 法域选择 |
| `/login` / `/register` | LoginPage / RegisterPage | 否 | 认证 |
| `/tasks` | TaskSpacesPage | ✅ | 任务空间列表 |
| `/workspace` / `/workspace/:taskId` | WorkspacePage | ✅ | 工作台（核心页面） |
| `/reports` | ReportCenterPage | ✅ | 报告中心 |
| `/evidence` | EvidenceCenterPage | ✅ | 证据中心 |
| `/knowledge/laws/:sourceId` | LawViewerPage | ✅ | 法规阅读器 |
| `/docs` | DocsPlaceholderPage | ✅ | 文档中心 |
| `/settings` | SettingsPage | ✅ | 设置（LLM/得理配置） |
| `/profile` | ProfilePage | ✅ | 个人信息 |
| `*` | → 重定向到 `/` | — | — |

**AppShell 关键行为**：

1. 每 30 秒探测 `GET /health`，失败时显示黄色警告条
2. `createTask()` 函数：生成 `TaskSpace` → dispatch 到 store → navigate 到 workspace
3. 管理 QuickStartModal / ModeSelectModal / CreateWorkspaceModal 三连弹窗
4. 加载 OnboardingOverlay 引导流程

### 2.2 状态管理

**`app-store.tsx`**：使用 React `useReducer` + `localStorage` 持久化。一个 store 管全部应用状态：

```text
AppState = {
  taskSpaces: TaskSpace[]        ← 用户创建的所有工作空间
  moduleRuns: ModuleRun[]        ← 所有运行记录
  artifacts: OutputArtifact[]    ← 产物文件列表
  evidenceHits: EvidenceHit[]    ← 证据匹配
  issues: ConsistencyIssue[]     ← 一致性问题
  systemMessages: SystemMessage[]← 系统消息
  runSessions: RunSession[]      ← 运行对话（RunTranscript 展示用）
  panelState: PanelState         ← 面板展开/折叠/宽度
  onboarding: OnboardingState    ← 新手引导
}
```

**Action 类型**（24 种）：

| 类别 | Action | 触发时机 |
|------|--------|---------|
| 任务空间 | `create_task_space` / `rename_task_space` / `delete_task_space` / `touch_task_space` | 用户操作 |
| 运行结果 | `append_run` | `ModuleRunPanel.onRunDone()` |
| 产物 | `append_artifacts` | 运行完成后解析产物 |
| 远程水合 | `hydrate_remote_state` | 从 `/api/me/state` 恢复 |
| 运行会话 | `begin_run_session` / `stage_running` / `stage_done` / `finish_run_session` | 运行过程 |
| 面板 | `set_panel_state` | 用户拖拽/折叠 |
| 引导 | `set_onboarding` | 引导完成 |

**持久化**：每次 dispatch 后自动保存到 `localStorage[ai4law_app_state_v1]`。同时支持从后端 `/api/me/state` 远程恢复。

### 2.3 API 层

**`api/modules.ts`**：前端与后端通信的核心枢纽。

```
请求链路：
  runModule(module, payload, runMode)
    │
    ├── runMode === "sync":
    │     requestJson(syncEndpoint, POST, payload) → 直接返回 response
    │
    └── runMode === "async":
          1. requestJson(asyncSubmitEndpoint, POST, payload) → task_id
          2. 轮询 requestJson(asyncStatusEndpoint, GET)
             每 1.5 秒查询一次，最多 180-900 秒
          3. FINAL_STATES = {succeeded, completed, failed, cancelled}
             命中终态 → 返回 {response, asyncTaskId, asyncState}
             超时 → 抛 AsyncTaskTimeoutError
```

**11 个模块的 API 注册表**：

| 模块 key | sync Endpoint | async 端点 | 超时(ms) |
|----------|--------------|-----------|---------|
| diagnosis | `/api/v1/diagnosis/report` | ❌ | — |
| assessment | `/api/v1/assessment/generate` | ✅ | 180000 |
| review | `/api/v1/review/generate` | ✅ | 900000 |
| pipia | `/api/v1/pipia/generate` | ✅ | 180000 |
| bcr | `/api/v1/bcr/generate` | ✅ | 180000 |
| dpia | `/api/v1/dpia/generate` | ✅ | 180000 |
| tia | `/api/v1/tia/generate` | ✅ | 180000 |
| cn_flow | `/api/v1/cn-flow/generate` | ✅ | 180000 |
| us_14117 | `/api/v1/us_14117/generate` | ✅ | 180000 |
| eu_scc | `/api/v1/eu_scc/generate` | ✅ | 180000 |
| cpra | `/api/v1/cpra/generate` | ✅ | 180000 |

**文件上传**：`uploadTaskFile(file)` → `POST /api/v0/files/upload` (multipart/form-data) → 返回 `{fileId, fileName, path, ...}`

**运行事件**：`RunEvent` 类型含 `event_id`、`task_id`、`seq`、`event_type`（status/thought/tool_start/tool_result/intermediate/warning/final）、`summary`、`detail`、`level`、`timestamp`。主要通过 SSE 通道接收。

**`api/client.ts`**：底层 fetch 封装。从 `localStorage` 读 token 注入 Authorization header。

**其他 API 文件**：

| 文件 | 暴露接口 |
|------|---------|
| `api/auth.ts` | `login()`, `register()`, `getAuthHeaders()` |
| `api/artifacts.ts` | `fetchArtifactBlob()` — 下载产物文件二进制 |
| `api/citations.ts` | `resolveCitation()` — 查询引用详情 |
| `api/events.ts` | `connectEventStream()` — SSE 连接 |
| `api/me.ts` | `fetchWorkspaceState()`, `saveWorkspaceState()` — 远程状态同步 |
| `api/system-settings.ts` | `saveSettings()` — 持久化设置 |
| `api/knowledge.ts` | `searchLaws()` — 法规搜索 |
| `api/copilot.ts` | `askCopilot()` — AI 助手对话 |
| `api/reports.ts` | 报告管理 |

### 2.4 任务模板系统

**`lib/task-templates.ts`**：定义 10 个任务模板，将模块 key 映射到用户可见的任务名称和工作台样式。

```text
TaskTemplate = { id, jurisdiction, module, workspaceStyle, title, subtitle, inputHint, outputHint }

  cn_diagnosis    → 合规路径诊断    → workspaceStyle: cn_diagnosis
  cn_assessment   → 安全评估路径    → workspaceStyle: cn_assessment
  cn_pipia        → 认证/标准合同    → workspaceStyle: cn_pipia
  cn_document_review → 文档专项审查 → workspaceStyle: cn_document_review
  eu_scc          → SCC 审查       → workspaceStyle: eu_scc
  eu_bcr          → BCR 审核       → workspaceStyle: eu_bcr
  eu_dpia         → DPIA 草案生成   → workspaceStyle: eu_dpia
  eu_tia          → TIA 草案生成   → workspaceStyle: eu_tia
  us_14117        → EO 14117 合规   → workspaceStyle: us_14117
  us_cpra         → CPRA 合规诊断   → workspaceStyle: us_cpra
```

注意：`cn_flow`（中国数据流审查）不在任务模板中，前端通过 module key 直接路由，不经过任务模板选择。

**`lib/module-registry.ts`**：从 `config/module_registry.json` 读取模块注册表，提供 `getModuleJurisdiction()` 和 `getModuleTaskTemplateId()` 映射。

### 2.5 领域模型

**`lib/domain.ts`**：定义所有前端领域类型。

```
核心类型层级：
  Jurisdiction          → "CN" | "EU" | "US"
  ModuleKey             → 11 个模块枚举
  WorkspaceStyleKey     → 10 个工作台样式枚举
  TaskSpace             → {id, name, mode, jurisdiction, module, workspaceStyle}
  ModuleRun             → {id, taskSpaceId, module, runMode, request, response, error, ...}
  OutputArtifact        → {id, taskSpaceId, module, kind, path}
  PanelState            → {leftOpen, rightOpen, leftWidth, ...}
  RunSession            → {id, stages[], isComplete, totalDurationMs}
  StageNode             → {id, name, status, summary, detail}
  TraceNode             → {id, stage, action, tokenInput, tokenOutput, durationMs}
  TraceBlock            → {label, content, language}
```

**`lib/run-state.ts`**：运行状态管理工具集。

```
核心函数：
  isFinalAsyncState(state)   → 判断是否终态 (succeeded/completed/failed/cancelled)
  getRunLifecycleState(run)  → idle | running | success | failed | unreachable
  selectRunningModuleRuns()  → 筛选需要轮询的运行中任务（供 GlobalTaskWatcher）
  mergeRunResults(local, server) → 合并本地和服务端运行记录
  selectPreferredRun(runs)   → 从多条运行记录中选最优（优先运行中 > 按时间倒序）
```

### 2.6 开发测试增强层

**`lib/dev-presets.ts`**：开发加速预设。当 `VITE_ENABLE_DEV_ACCEL=true` 时，注入预填表单值并跳过文件上传（将 `backendFilePaths` 直接作为路径字符串传递给后端，走 `presetFilePaths` 通道而非真实上传）。

```text
DevPresetModule = "assessment"|"pipia"|"dpia"|"tia"|"eu_scc"|"bcr"
                 |"diagnosis"|"document_review"|"us_14117"|"cpra"

ModuleDevPreset = {id, module, title, scenarioDescription, formDefaults, backendFilePaths}

10 个 DEFAULT_PRESET_IDS → 各模块一键运行按钮获取预填数据
```

**`lib/dev-test-cases.ts`**：26 个测试案例。每个案例包含完整 `formDefaults` + `backendFilePaths`，通过 🧪 按钮选择注入。

### 2.7 核心页面

#### WorkspacePage（`pages/WorkspacePage.tsx`）

工作台主页面。从 URL 获取 `taskId` → 查找 `TaskSpace` → 渲染三栏布局。

```text
WorkspacePage 三栏布局：
  ┌──────────┬─────────────────────────────┬──────────────┐
  │ 左侧栏   │     中央主区域               │  右侧栏      │
  │          │                             │              │
  │ResourcePanel  WorkspaceShell           │  空/待实现   │
  │ - 输入文件    ├── ModuleRunPanel         │              │
  │ - 输出产物    │   (表单+执行)            │              │
  │ - 异常/证据   ├── RunTranscript          │              │
  │              │   (运行记录)            │              │
  │              ├── TraceNodeView           │              │
  │              │   (trace 节点)          │              │
  │              ├── AssessmentIntermediatesPanel │         │
  │              └── StageSplitView           │              │
  └──────────┴─────────────────────────────┴──────────────┘
```

左侧栏 (`panelState.leftOpen`) 和运行记录区 (`panelState.topOpen`) 可通过 `set_panel_state` 折叠/展开/拖拽。

#### TaskSpacesPage

列出所有已创建的 `TaskSpace`，支持创建新的（弹出 CreateWorkspaceModal）、重命名、删除。点击进入对应 WorkspacePage。

#### SettingsPage

LLM Provider 配置（Generic/SiliconFlow/Tencent Hunyuan）和得理法搜配置。保存到 `localStorage` 并通过 `POST /api/v0/settings` 发送后端。

#### 其他页面

| 页面 | 功能 |
|------|------|
| HomePage | 产品首页 + 快速开始 |
| JurisdictionHubPage | 按法域浏览功能入口 |
| ReportCenterPage | 报告文件管理 |
| EvidenceCenterPage | 证据条目管理 |
| LawViewerPage | 法规条款阅读（含引用跳转） |

---

## 第三部分：前端 → 后端完整交互流程

### 3.1 表单 → Payload 构建

**`features/module-runner/payload-builders/`**：前端模块运行器的核心业务层。每种模块的表单值转换为后端 API 请求 JSON。

```
前端表单值 (XxxFormValues)  →  payload builders  →  JSON payload  →  HTTP POST
```

**文件组织**：

| 文件 | 构建函数 | 对应模块 |
|------|---------|---------|
| `cn.ts` | `buildDiagnosisPayload()` | diagnosis |
| `cn.ts` | `buildAssessmentPayload()` | assessment |
| `cn.ts` | `buildPipiaPayload()` | pipia |
| `cn.ts` | `buildDocumentReviewPayload()` | review |
| `cn.ts` | `buildCnFlowPayload()` | cn_flow |
| `eu.ts` | `buildEuSccPayload()` | eu_scc |
| `eu.ts` | `buildBcrPayload()` | bcr |
| `eu.ts` | `buildDpiaPayload()` | dpia |
| `eu.ts` | `buildTiaPayload()` | tia |
| `us.ts` | `buildUs14117Payload()` | us_14117 |
| `us.ts` | `buildCpraPayload()` | cpra |
| `common.ts` | `requireText()`, `hasText()`, `uploadFiles()`, ... | 所有模块共享 |

**Payload Builder 的三层职责**：

1. **字段校验**：`requireText(name, minLen)`、`requireAllowedValue(field, [enum])` — 在发送前即拦截无效输入
2. **值转换**：表单的简单字符串 → 后端的嵌套对象（如 pipia 的 `company_profile`/`transfer_context`/`personal_info_scope` 四层结构）
3. **文件处理**：`uploadFiles(files)` → `POST /api/v0/files/upload` → 获取 `{fileId, path}` 嵌入 payload；或开发模式下使用 `presetFilePaths` 直接传路径字符串

**文件上传的两种模式**：

```text
生产模式：File[] → uploadFiles() → POST /api/v0/files/upload → [{path: "storage/uploads/xxx"}]
                                         ↓
                                 payload 中使用返回的 path

开发模式（DEV_ACCEL=true）：presetFilePaths → 直接作为字符串数组传入
                          后端直接读取本地 fixture 路径，跳过 HTTP 上传
```

### 3.2 ModuleRunPanel — 前端执行核心

**`components/workspace/ModuleRunPanel.tsx`**（约 3200 行）：前端最复杂的组件。包含 11 个模块的表单渲染 + 文件上传 + 执行按钮 + 开发测试辅助。

**每模块的 state 集合**（以 pipia 为例）：

```typescript
const [pipiaStepIndex, setPipiaStepIndex] = useState(0);          // 当前步骤
const [pipiaValues, setPipiaValues] = useState<PipiaFormValues>(); // 表单值
const [pipiaFiles, setPipiaFiles] = useState<File[]>();            // 上传的文件
const [pipiaDevFilePaths, setPipiaDevFilePaths] = useState<string[]>(); // 开发模式文件路径
```

**模块切换逻辑**（`useEffect`，监控 `moduleKey`）：

```text
moduleKey 变化 →
  1. 重置所有模块的 stepIndex = 0
  2. 重置 form values 为默认值
  3. 清空 files[]
  4. 若 DEV_ACCEL_ENABLED → 从 getModuleDevPreset() 注入 devFilePaths
  5. 加载对应模块的 devTestCases（26 个案例列表）
```

**执行流程**：

```text
用户点击"运行"按钮
  ↓
execute() → 根据 moduleKey 路由到对应 payload builder
  ↓
buildXxxPayload() → 字段校验 → 文件上传 → 构建 JSON
  ↓
runWithPayload(payload):
  1. setLoading(true)
  2. setError(null)
  3. hasAsync(module)? 选 async: 选 sync
  4. timeoutMs = review/assessment ? 900000 : 180000
  5. runModule(module, payload, runMode, timeoutMs, onProgress, onTaskCreated)
     ├── sync:  HTTP POST → 等待响应（最长 180s-900s）
     └── async: HTTP POST → 获取 taskId → 轮询 status（每 1.5s）
  6. 成功 → setResponseData(result.response)
          → onRunDone({module, runMode, request, response, success: true})
  7. 失败 → setError(message)
          → onRunDone({..., success: false, error})
  8. finally → setLoading(false)
```

**`onRunDone()` 回调**（实际执行者）：

```text
onRunDone({module, runMode, request, response, success, error, ...})
  ↓
1. dispatch(append_run) → store 中记录 ModuleRun
2. dispatch(begin_run_session) → 开始新 RunSession
3. 解析 response 中的产物文件:
   output_files { "markdown": "path/to/report.md", "docx": "path/to/report.docx", ... }
   ↓
   dispatch(append_artifacts) → 每个文件记录为 OutputArtifact
4. 解析 citation_map → dispatch(append_evidence)
5. 解析 consistency_issues → dispatch(append_issues)
6. 推送系统消息
7. dispatch(finish_run_session)
```

### 3.3 资源浏览器（ResourcePanel）

**`components/workspace/ResourcePanel.tsx`** + **`features/resource-explorer/`**：

从 `moduleRuns` 和 `outputArtifacts` 中提取文件列表，按路径树形式展示。

```text
ResourcePanel 数据构建流程：
  store.moduleRuns[] + store.outputArtifacts[]
    ↓
  buildInputEntries(runs, artifacts, lang)
    → collectUserInputFiles(run.request)     ← 扫描 uploaded_files/attachments 字段
    → 去重、排序、提取文件名
  buildOutputTree(artifacts, lang)
    → 按路径层级构建树 → path-tree.ts
    → 支持展开/折叠目录节点
    → PDF/DOCX/MD/XLSX 文件可点击预览（调用 fetchArtifactBlob）
```

**输入文件发现**：`input-resources.ts:collectUserInputFiles()` 递归扫描 payload 中 `INPUT_CONTAINER_KEYS = {"attachments", "uploaded_files"}` 的值，提取所有符合 `USER_INPUT_EXTENSIONS` 白名单的文件路径。

**当前限制**：输入文件仅展示文件名，不支持点击预览（提示"安全预览接口尚未统一，当前仅展示"）。

### 3.4 运行记录系统

#### RunTranscript（运行事件列表）

从后端 SSE 事件或 trace 文件解析运行事件，按时间线展示：

```text
RunEvent[]
  ├── event_type: "status"       → 状态更新（开始/进行中/完成）
  ├── event_type: "thought"     → Agent 思考过程
  ├── event_type: "tool_start"  → 工具调用开始
  ├── event_type: "tool_result" → 工具调用结果
  ├── event_type: "intermediate"→ 中间产物
  ├── event_type: "warning"     → 警告
  └── event_type: "final"       → 最终结果
```

每个事件展示：类型标签、summary、时间戳。可展开查看 detail JSON。

**事件来源**（双通道）：

1. **SSE 实时推送**：`TaskEventBridge.tsx` 监听 SSE → 转为系统消息 → dispatch
2. **Trace 文件读取**：运行完成后读取 `storage/traces/{run}/` 下的 JSON 文件

#### TraceNodeView（Trace 节点树）

将 RunTranscript 的平铺事件转换为树形结构：

```
TraceStage 分类 → 按 Call → Input → Query → Result → Output 构建 TraceBlock
  ├── Task     (任务调度)
  ├── LLM      (LLM 调用：prompt token + completion token)
  ├── RAG      (检索：query → hits)
  ├── Tool     (工具调用)
  ├── Parser   (解析)
  ├── Generator(生成)
  └── Review   (审查)
```

每个节点展示：stage 图标、action 描述、duration、Token 计数（input/output）、可展开的 TraceBlock 内容。

#### GlobalTaskWatcher（全局任务监视器）

**`components/workspace/GlobalTaskWatcher.tsx`**：应用级轮询器。

```
逻辑：
  1. 每 3 秒执行一次
  2. selectRunningModuleRuns() → 筛选出所有 state 非终态且未完成的 ModuleRun
  3. 对每个未完成的任务：
     fetchModuleTaskStatus(module, taskId) → /api/v1/xxx/tasks/{taskId}
     ├── 若已终态 → mergeRunResults(local, server) → dispatch 更新
     │                → clear_run_sessions 清理旧会话
     └── 若仍在运行 → 继续轮询
```

这意味着即使浏览器标签页刷新，之前提交的异步任务仍可被 GlobalTaskWatcher 重新发现并完成。

---

## 第四部分：后端路由注册

**`backend/main.py`** 创建 FastAPI app：

```python
app = create_app()
# 额外挂载模块路由
app.include_router(diagnosis.router, prefix="/api/v1")
app.include_router(assessment.router, prefix="/api/v1")
app.include_router(review.router, prefix="/api/v1")
app.include_router(pipia.router, prefix="/api/v1")
app.include_router(bcr.router, prefix="/api/v1")
app.include_router(dpia.router, prefix="/api/v1")
app.include_router(tia.router, prefix="/api/v1")
app.include_router(cn_flow.router, prefix="/api/v1")
app.include_router(us_14117.router, prefix="/api/v1")
app.include_router(eu_scc.router, prefix="/api/v1")
app.include_router(cpra.router, prefix="/api/v1")
app.include_router(v0.router, prefix="/api/v0")
```

每个模块路由定义 sync + async 端点。以 assessment 为例：

```python
# assessment/router.py
@router.post("/assessment/generate")        # sync
async def generate(body: AssessmentRequest): ...

@router.post("/assessment/generate_async")  # async submit
async def generate_async(body: AssessmentRequest): ...

@router.get("/assessment/tasks/{task_id}")  # async status
async def get_task_status(task_id: str): ...
```

---

## 第五部分：公共基础设施层（后端）

### 5.1 WorkflowPipeline — 18 步报告生成流水线

**位置**：`backend/common/workflow/pipeline.py`

使用 dependency injection 模式，由模块注入 15 个 Callable 函数来定制行为。

```
Step  1: trace.record(request, payload)
Step  2: profile = extract_profile(payload)              ← 模块注入
Step  3: diagnosis = evaluate_diagnosis(payload)         ← 模块注入
Step  4: path_warning = validate_path()                  ← 模块注入
Step  5: facts = build_facts(payload, profile, diagnosis)← 模块注入
Step  6: regulations = retrieve_regulations(profile)     ← 模块注入
Step  7: attachment_notes = build_attachment_notes()     ← 模块注入
Step  8: issues = build_issues(facts, diagnosis, regs)   ← 模块注入
Step  9: issues, evidence = build_evidence()             ← 模块注入
Step 10: [可选] per_issue_rag = retrieve_per_issue()     ← 模块注入
Step 11: context_pack = build_context_pack(...all...)    ← 模块注入
Step 12: chapters = generate_chapters(profile, regs, pack)← 模块注入
Step 13: consistency_issues = check_consistency()        ← 模块注入
Step 14: alignment_issues = check_alignment()            ← 模块注入
Step 15: [可选] chapters, issues, blocked = repair_chapters()
Step 16: manifest = trace.write_manifest()
Step 17: outputs = render_artifacts(...)
Step 18: return WorkflowRunResult
```

**关键细节**：
- 每一步都有 `trace.record()` 形成完整事件链
- Step 15 repair 只执行一次，非迭代至收敛
- `repair_blocked` 标记后仍继续执行 `render_artifacts()`
- `per_issue_rag` 可选注入，用于高风险 issue 的二次检索

**使用者**（4 个模块）：

| 模块 | 完整度 | 差异 |
|------|:---:|------|
| assessment | ✅ | 注入 repair + per_issue_rag(DeliLegal) |
| eo14117 | ✅ | 注入 per_issue_rag(5 Agent) |
| eu_scc | ✅ | 部分函数依赖外部 rule_result |
| cn_flow | ⚠️ | `_build_context_pack()` 参数断链 |

### 5.2 LLM 调用体系

```
LLMClient(settings)
  ├── 通过 LLMProviderRegistry 获取活跃 provider
  ├── .chat(system, user) → 单次 OpenAI-compatible 调用
  ├── .chat_json(system, user) → 返回解析后的 JSON
  ├── 内置 JSON 解析 + usage/token 统计
  └── 失败时返回 fallback 文本
```

**`module_generator.py:generate_chapter()`**：通用章节生成函数。

```python
generate_chapter(module_name, chapter_slug, instruction, user_context,
                 citation_registry, task_id, trace, module_templates) → str
```

内部：
1. 查找 `SYSTEM_PROMPTS[module_name]` 获取 system prompt
2. 拼接 `instruction + user_context + citation 允许列表`
3. `LLMClient.chat()` 调用
4. 返回 Markdown 字符串

**已知 bug**：`SYSTEM_PROMPTS['cn_flow']` 内容为 EO 14117 的 prompt（法域污染）。

### 5.3 RAG 检索系统

**`backend/common/rag/retriever.py`**：

```python
RegulationRAGService.retrieve(query, jurisdiction, path, filters, top_k) → List[RegulationDoc]
```

**6 层检索架构**：
```
1. SQLite FTS5      → 本地全文索引
2. 词法检索         → 关键词匹配 + 法域/path 过滤
3. 哈希向量         → HashingEmbedder (384维稀疏哈希，非神经模型)
4. RRF Fusion       → 多路结果融合
5. 启发式重排       → jurisdiction boosts + 条款相关性
6. [可选] 远程补充  → DeliLegal search_laws()（本地结果不足时）
```

**索引架构 (v3.1)**：
```
storage/rag/v3/
├── cn/legal/     → 中国法规
├── cn/workflow/  → 中国工作流
├── eu/legal/     → 欧盟法规
├── eu/workflow/
├── us/legal/     → 美国法规
├── us/workflow/
└── testcase/     → L3 层（production 禁止使用）
```

**当前弱点**：
- 中文离题查询拦截不足
- EU 精确条款（如 "GDPR Article 35"）首屏命中率低
- 模板 chunk 可能排在法律原文前

### 5.4 CitationRegistry — 引用注册系统

**`backend/common/citation/registry.py`**：

每次报告运行时创建的内存态注册表，不持久化。

```
生命周期：
  1. register(CitationItem) → "CIT-001" 标记 ID
  2. build_marker_list()    → LLM prompt 中的引用允许列表
  3. LLM 生成时插入 {{CIT-001}} marker
  4. postprocess 替换为脚注编号
  5. assign_footnote_number() → 全局唯一序号
  6. build_citation_map_section() → citation_map.json
  7. build_external_citation_map_section() → 外部视图（过滤低置信引用）
```

**CitationItem 关键字段**：`source`, `article_id`, `quote`, `source_url`, `confidence`(HIGH/MEDIUM/LOW), `purpose`(legal_evidence/supporting/template), `associated_issue_ids`, `associated_fact_ids`

**引用跳转**：`can_jump=true` 需 `article_id` 精确匹配 AND `source_url` 非空。当前安全评估 precision 约 14.3%。

### 5.5 中间结构 (Fact → Issue → Evidence → ContextPack)

```
FactItem (facts.py)
  ├── field_path, value, provenance(USER_INPUT/RULE_DERIVED/LLM_INFERENCE)
  ├── confidence(HIGH/MEDIUM/LOW), evidence_status(CONFIRMED/UNVERIFIED/DISPUTED)
  └── legal_implication

IssueItem (issues.py)
  ├── issue_id, category, severity(BLOCKER/HIGH/MEDIUM/LOW)
  ├── certainty(CONFIRMED/LIKELY/POSSIBLE)
  ├── fact_refs[], regulation_refs[]
  └── description, finding, recommendation, action_items[]

EvidenceItem (evidence.py)
  ├── evidence_id, claim, conclusion
  ├── fact_refs[], rule_refs[], citation_refs[]
  ├── document_refs[], strength(STRONG/MODERATE/WEAK)
  └── status(VERIFIED/UNVERIFIED)

GenerationContextPack (context_pack.py)
  ├── task_id, facts[], regulations[], issues[], evidence_chain[]
  ├── diagnosis, path_warning, attachment_notes[]
  ├── per_issue_rag (dict)
  └── citation_registry
```

**模块复用程度**：

| 模块 | FactItem | IssueItem | EvidenceItem | ContextPack |
|------|:---:|:---:|:---:|:---:|
| assessment | ✅ | ✅ | ✅ | ✅ |
| eo14117 | ✅ | ✅ | ✅ | ✅ |
| eu_scc | ✅ | ✅ | ✅ | ✅ |
| cn_flow | ✅ | ✅ | ✅ | ✅⚠ |
| pipia | 专用 | 专用 | 专用 | ❌ |
| dpia | 专用 | 专用 | ❌ | ❌ |
| bcr | 专用 | ❌ | ❌ | ❌ |
| tia | 专用 | ❌ | ❌ | ❌ |
| cpra | CPRAFactPack | CPRAGapItem | ❌ | ❌ |
| diagnosis | DiagnosisFacts | ❌ | ❌ | ❌ |
| review | ❌ | ReviewIssues | ❌ | ❌ |

---

## 第六部分：各模块完整前后端链路

### 6.1 统一交互模式

每个模块的前后端交互遵循以下通用模式：

```text
┌─ 前端 ─────────────────────────────────────────────────────────┐
│ 1. ModuleRunPanel 渲染表单                                      │
│    ├── XxxSteps[] 定义多步表单                                  │
│    ├── 每步有 fields[] + 文件上传区                              │
│    └── 用户点击"上一步"/"下一步"切换步骤                         │
│                                                                  │
│ 2. 表单校验 + Payload 构建                                       │
│    ├── requireText / requireAllowedValue / assertInput           │
│    ├── uploadFiles() → POST /api/v0/files/upload                │
│    └── buildXxxPayload(values, resolvedFilePaths) → JSON        │
│                                                                  │
│ 3. 执行                                                          │
│    ├── execute() → runWithPayload()                             │
│    ├── runModule(module, payload, runMode)                      │
│    └── HTTP POST /api/v1/xxx/generate (sync 或 async)           │
└──────────────────────────────────────────────────────────────────┘
                               │
┌─ 后端 ─────────────────────────────────────────────────────────┐
│ 4. FastAPI 路由接收 request → Pydantic 校验                     │
│                                                                  │
│ 5. Service.generate_report(payload, task_id, trace)             │
│    ├── 规则引擎 → 确定性判断（如果有）                            │
│    ├── RAG 检索 → 相关法规                                      │
│    ├── Agent/LLM 调用 → 分析/生成                                │
│    ├── 章节生成 → Markdown 正文                                  │
│    ├── 一致性检查 + 修复                                         │
│    └── 产物渲染 → MD/DOCX/PDF/XLSX/JSON/ZIP                     │
│                                                                  │
│ 6. 返回 {output_files: {role: path}, ...}                       │
└──────────────────────────────────────────────────────────────────┘
                               │
┌─ 前端回流 ─────────────────────────────────────────────────────┐
│ 7. onRunDone() → dispatch(append_run + append_artifacts)        │
│ 8. ResourcePanel 展示产物文件列表                                │
│ 9. RunTranscript 展示执行事件                                    │
│ 10. 产物文件可点击预览（fetchArtifactBlob → URL.createObjectURL）│
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 diagnosis — 合规路径诊断

**前端**：
```
DiagnosisFormValues → buildDiagnosisPayload()
  ├── 5 步表单 (m1~m5 共 32 个字段)
  ├── 格式：{company_name, answers: {q1..q8, m1..m5}}
  ├── 同步 POST /api/v1/diagnosis/report
  └── 无文件上传
```

**后端**：
```
DiagnosisService.evaluate(answers, trace)
  ├── 4 Agent (important_data → pi_classify → exemption → clarification)
  ├── 9 规则决策树 (decision_tree.json)
  │     Rule 0-4: 豁免规则 (无PI/合同/HR/紧急/法定义务)
  │     Rule 5-8: 强制规则 (CIIO/重要数据/100万PI/1万SPI)
  │     default:  SCC 或认证
  └── → DiagnosisResult {recommended_path, risk_level, confidence, ...}
```

### 6.3 assessment — 安全自评估

**前端**：
```
AssessmentFormValues → buildAssessmentPayload()
  ├── 8 字段 (company_name, industry, is_ciio, pii/spi_count, purpose, country, files)
  ├── 同步/异步 POST /api/v1/assessment/generate
  └── 支持文件上传 + 开发加速预设
```

**后端**：
```
AssessmentService.generate_report(payload, task_id, trace)
  ├── payload → 拆解为 DiagnosisAnswers → 调 DiagnosisService 做路径诊断
  ├── 构造 WorkflowPipeline(15 Callable)
  │     ├── retrieve_regulations → RAG 中国数据出境法规
  │     ├── retrieve_per_issue → HIGH/BLOCKER issue 调 DeliLegal
  │     ├── generate_chapters → 8 章 (公司概况→数据链路→法律分析→
  │     │    风险评估→安全措施→权利保护→应急响应→结论)
  │     ├── check_consistency(+alignment) → 一致性检查
  │     └── repair_chapters → 修复一次
  └── render → 23 项产物 (MD/DOCX/PDF/XLSX/JSON/ZIP + internal/official 双视图)
```

### 6.4 pipia — 个人信息保护影响评估

**前端**：
```
PipiaFormValues → buildPipiaPayload()
  ├── 20+ 字段，结构化为 5 个子对象
  │     company_profile / transfer_context / personal_info_scope
  │     / rights_protection / emergency_plan
  ├── 同步/异步 POST /api/v1/pipia/generate
  └── 文件上传（SCC 标准合同）+ 必填 role=scc_contract
```

**后端**：
```
PIPIAService.generate_report(payload, task_id, trace)
  ├── _extract_attachment_evidence() → FileParser 解析 SCC 合同
  ├── _build_facts() → 结构化事实
  ├── _build_structured_issues() → 规则 checklist 检查
  ├── _build_evidence_chain() → 证据构建
  ├── _assess_filing_readiness() → 备案准备度
  ├── LLM 章节生成 (generate_chapter)
  └── 产物: MD/DOCX/PDF + filing_readiness + evidence_chain
```

**不使用 WorkflowPipeline**，有独立 service。

### 6.5 document_review — 文档智能审查

**前端**：
```
DocumentReviewFormValues → buildDocumentReviewPayload()
  ├── document_type(review_focus + company_name+ 文件)
  ├── 同步/异步 POST /api/v1/review/generate
  └── 必须先 create_task → upload_file → generate
```

**后端**：
```
ReviewService._run_pipeline(task_id, user_id)
  ├── Stage 0: PREPARING (0-10%) → StructuredDocumentParser + DocClassifier + ScenarioExtractor
  ├── Stage 1: SEGMENTING (10-25%) → ClauseSegmenter 条款切分
  ├── Stage 2: CLASSIFYING (25-45%) → ClauseClassifier 条款分类
  ├── Stage 3: MISSING_CHECK (45-55%) → MissingItemChecker 必备条款缺失
  ├── Stage 4: REVIEWING (55-80%) → 8 个审查器并行 (DataProtection/DataTransfer/
  │     SCCMandatory/PrivacyPolicy/UserAgreement/ContractTerms + 可选 LLM ClauseReviewer)
  ├── Stage 5: CROSS_DOC_CHECK (80-85%) → CrossDocumentChecker
  ├── Stage 6: AGGREGATING (85-95%) → RiskScorer + ConsistencyChecker + ReviewAggregator
  ├── Stage 7: RENDERING (95-100%) → ReviewReportRenderer + AnnotatedDocxBuilder
  └── SQLite 持久化任务 + WebSocket 进度推送
```

**完全独立**：不使用 WorkflowPipeline，有 SQLite 持久化任务表，WebSocket 实时推送进度。

### 6.6 eu_scc — 欧盟 SCC 审查

**前端**：
```
EuSccFormValues → buildEuSccPayload()
  ├── transfer_role(c2c/c2p/p2p/p2c) → 自动推断 Module One~Four
  ├── exporter/importer/purpose/data_categories
  ├── 同步/异步 POST /api/v1/eu_scc/generate
  └── 支持 SCC 文档上传
```

**后端**：
```
EU_SCCService.generate_report(payload, task_id, trace)
  ├── scc_rule_engine.run_eu_scc_rule_engine()
  │     ├── validate_module_selection → Module 匹配检测
  │     ├── compare_standard_clauses → 逐条对比 SCC 2021 标准条款
  │     ├── review_annexes → Annex I/II/III 完整性
  │     ├── review_tia_and_measures → TIA 与补充措施
  │     └── score_scc_risk → HIGH/MEDIUM/LOW
  ├── _build_pipeline(rule_result) → WorkflowPipeline + 6 Agent
  └── 产物: MD/DOCX/PDF + findings.json + rule_engine_result.json + citation_map.json
```

**已知 bug**：`generate_report()` 使用 `uuid` 但未 `import uuid`。

### 6.7 bcr — BCR 审查

**前端**：
```
BcrFormValues → buildBcrPayload()
  ├── company_name + 10 项 BCR_REVIEW_ITEMS (每项含 code/title/legal_basis/recommendation)
  ├── 表单字段自动映射为 evidenceTexts → score 计算 → finding
  ├── 同步/异步 POST /api/v1/bcr/generate
  └── 支持 BCR 主文档上传
```

**后端**：
```
BCRService.generate_report(payload, task_id, trace)
  ├── 若含文件 → _run_document_driven_review()
  │     ├── BCRTypeClassifier → BCR-C / BCR-P 分类
  │     ├── BCRRuleEngine(bcr_rulebook.json) → 12 项检查
  │     └── 10 Agent (type_reasoning→actor_role→coverage→onward_transfer
  │           →evidence_coverage→incorrect_status→tia_reasoning
  │           →legal_grounding→approval_risk→remediation)
  ├── 否则 → _run_form_driven_review()
  └── 产物: MD/DOCX/PDF/ZIP
```

### 6.8 dpia — DPIA 草案生成

**前端**：
```
DpiaFormValues → buildDpiaPayload()
  ├── 30+ 字段 (项目信息/触发原因/处理描述/数据类别/风险评估/缓解措施/签署)
  ├── 敏感关键词自动推断 risk likelihood/impact
  ├── 同步/异步 POST /api/v1/dpia/generate
  └── 支持附件上传
```

**后端**：
```
DPIAService.generate_report(payload, task_id, trace)
  ├── dpia_need Agent → 判断是否需要 DPIA
  ├── 9 Agent 链式执行:
  │     processing_activity → necessity_proportionality → risk_assessment
  │     → mitigation_mapping → dpo_consultation → external_draft
  │     → internal_review → consistency_repair
  ├── RAG: GDPR 相关条款检索
  └── 产物: MD/DOCX/PDF + need_assessment.json + risk_matrix.xlsx + mitigation_plan.xlsx + ZIP
```

### 6.9 tia — 传输影响评估

**前端**：
```
TiaFormValues → buildTiaPayload()
  ├── transfer_tool(scc/bcr/derogation) + exporter/importer 信息
  ├── law_assessed + supplementary_measures(技术/合同/组织)
  ├── 同步/异步 POST /api/v1/tia/generate
  └── 附件必填 (attachment_role 限定 4 种)
```

**后端**：
```
TIAService.generate_report(payload, task_id, trace)
  ├── 确定性评估: route_assessor + country_risk_assessor(静态 riskbook)
  │     + data_sensitivity_assessor + measure_assessor
  ├── 3 Agent: rag_planning + attachment_review + dpo_review
  ├── _check_consistency() → 路径 vs 工具、国家风险 vs 措施、数据敏感 vs 保护
  ├── _build_tia_citation_bundle() → CitationRegistry
  └── 产物: MD/DOCX/PDF + country_risk_assessment + transfer_assessment + citation_map.json
```

### 6.10 us_14117 — EO 14117 合规评估

**前端**：
```
Us14117FormValues → buildUs14117Payload()
  ├── company_name + project_name + transaction + data/entity/security_measures
  ├── 同步/异步 POST /api/v1/us_14117/generate
  └── CSV 文件上传 (data_inventory + entity_inventory)
```

**后端**：
```
US14117Service.generate_report(payload, task_id, trace)
  ├── run_rule_engine(payload) ← 约 1100 行，系统最大规则引擎
  │     ├── DataClassification → 数据敏感度标记
  │     ├── EntityAssessment → 关注国家匹配
  │     ├── TransactionAssessment → 交易评估
  │     ├── SecurityGapReport → 安全措施差距
  │     └── 红黄绿灯判断 (RED=禁止, YELLOW=受限, GREEN=豁免)
  ├── _build_pipeline(rule_result) → WorkflowPipeline
  │     ├── retrieve_per_issue → 5 Agent:
  │     │     rule_boundary → rag_reformulation → evidence_priority
  │     │     → repair_check → chapter_consistency
  │     └── generate_chapters → 6 章
  └── 产物: 10+ 文件 (MD/DOCX/PDF/XLSX/ZIP + rule_engine_result + facts + risk_matrix + citation_map)
```

### 6.11 cn_flow — 中国数据流审查

**前端**：
```
CnFlowFormValues → buildCnFlowPayload()
  ├── company_name + transfer_purpose + data_categories + recipient_entities
  ├── CSV 文件上传 (data_inventory + entity_inventory，两者均必填)
  ├── 同步/异步 POST /api/v1/cn-flow/generate
  └── 支持额外接受方行 (additional_recipients) 解析
```

**后端**：
```
CNFlowService.generate_report(payload, task_id, trace)
  ├── _build_pipeline() → WorkflowPipeline
  │     ├── _evaluate_diagnosis → 简单路径判断
  │     ├── _build_facts → 数据流事实提取
  │     ├── _retrieve_regulations → 中国数据出境法规
  │     ├── _build_issues → 基于事实+法规构建
  │     └── generate_chapters → 5 章
  └── 产物: MD/DOCX/PDF/XLSX/ZIP + flow_diagram
```

**已知断链**：
- `_build_context_pack()` 与 `WorkflowPipeline.run()` 参数不兼容
- `SYSTEM_PROMPTS['cn_flow']` 内容错误使用 EO 14117 prompt

### 6.12 cpra — CPRA 合规评估

**前端**：
```
CpraFormValues → buildCpraPayload()
  ├── company_name + business_model + data_lifecycle + notice_and_consent
  ├── consumer_rights_process + opt_out_and_sale_sharing
  ├── privacy_policy_url (满足即可，文件可选)
  ├── 多文件区: privacy_policy / rights_sop / data_map / vendor_list / other
  ├── 同步/异步 POST /api/v1/cpra/generate
  └── URL 满足文件断言，无需上传
```

**后端**：
```
CPRAService.generate_report(payload, task_id, trace)
  ├── CPRAAttachmentExtractor.extract() → fact_extraction Agent 增强
  ├── CPRAFactMerger.merge() → 合并原始+附件事实
  ├── run_all_rules() → 10 组 if-else gap 规则:
  │     Notice&Transparency / Consumer Rights / Opt-out / Sensitive PI
  │     / Data Minimization / Purpose Limitation / Vendor Management
  │     / Consent UI / Data Retention / Security Safeguards
  ├── 3 Agent: spi_sharing_risk + vendor_contract + consistency_review
  ├── CPRALegalRetriever → CPRA 法规检索
  ├── _generate_chapters_from_context() → 6 章
  ├── _attach_gap_citations() → 为每个 gap 注册引用
  └── 产物: MD/DOCX/PDF/XLSX/ZIP + gap_items.json + citation_map.json
```

---

## 第七部分：跨模块对比总结

### 7.1 前后端模块映射

| 前端 moduleKey | 前端表单组件 | Payload Builder | 后端 Service | 后端 Pipeline | 后端 Agent 数 |
|:---|:---|:---|:---|---:|:---:|
| diagnosis | 5 步 wizard | `buildDiagnosisPayload` | `DiagnosisService` | ❌ 专用规则树 | 4 |
| assessment | 整合表单 | `buildAssessmentPayload` | `AssessmentService` | ✅ WorkflowPipeline | 0（15 Callable） |
| pipia | 整合表单 | `buildPipiaPayload` | `PIPIAService` | ❌ 专用 | 0 (规则式) |
| review | 文件+表单 | `buildDocumentReviewPayload` | `ReviewService` | ❌ 8阶段专用 | 0（4 专用审查器） |
| eu_scc | 整合表单 | `buildEuSccPayload` | `EU_SCCService` | ✅ WorkflowPipeline | 6 |
| bcr | 整合表单 | `buildBcrPayload` | `BCRService` | ❌ 双模式专用 | 10 |
| dpia | 整合表单 | `buildDpiaPayload` | `DPIAService` | ❌ 9 Agent链 | 9 |
| tia | 整合表单 | `buildTiaPayload` | `TIAService` | ❌ 确定性+3 Agent | 3 |
| us_14117 | 整合表单 | `buildUs14117Payload` | `US14117Service` | ✅ WorkflowPipeline | 5 |
| cn_flow | 整合表单 | `buildCnFlowPayload` | `CNFlowService` | ⚠️ WorkflowPipeline | 0 |
| cpra | 整合表单 | `buildCpraPayload` | `CPRAService` | ❌ 规则+4 Agent | 4 |

### 7.2 前端表单步骤数

| 模块 | 步骤数 | 文件上传 | 必填文件 |
|------|:---:|:---:|:---:|
| diagnosis | 5 | ❌ | ❌ |
| assessment | 单表单 | ✅ | ✅ (1+) |
| pipia | 单表单 | ✅ | ✅ (1+) |
| review | 文件+表单 | ✅ | ✅ (1+) |
| eu_scc | 单表单 | ✅ | ❌ |
| bcr | 单表单 | ✅ | ❌ |
| dpia | 单表单 | ✅ | ✅ (1+) |
| tia | 单表单 | ✅ | ✅ (1+) |
| us_14117 | 单表单 | ✅ | ❌ |
| cn_flow | 单表单 | ✅ | ✅ (data+entity) |
| cpra | 单表单 | ✅ (5区) | ❌ (URL替代) |

### 7.3 异步任务支持

| 模块 | 异步 | 任务管理器 | 进度推送 | 持久化 |
|------|:---:|------|:---:|:---:|
| assessment | ✅ | InMemoryTaskManager | SSE | ❌ |
| pipia | ✅ | InMemoryTaskManager | SSE | ❌ |
| review | ✅ | SQLite TaskModel | WebSocket | ✅ |
| eu_scc | ✅ | InMemoryTaskManager | SSE | ❌ |
| bcr | ✅ | InMemoryTaskManager | SSE | ❌ |
| dpia | ✅ | InMemoryTaskManager | SSE | ❌ |
| tia | ✅ | InMemoryTaskManager | SSE | ❌ |
| cn_flow | ✅ | InMemoryTaskManager | SSE | ❌ |
| us_14117 | ✅ | InMemoryTaskManager | SSE | ❌ |
| cpra | ✅ | InMemoryTaskManager | SSE | ❌ |
| diagnosis | ❌ | — | — | — |

### 7.4 前端组件复用矩阵

| 组件 | diagnosis | assessment | pipia | review | eu_scc | bcr | dpia | tia | us14117 | cn_flow | cpra |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| ModuleRunPanel | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| ResourcePanel | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| RunTranscript | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| TraceNodeView | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| AssessmentIntermediatesPanel | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| StageSplitView | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### 7.5 成熟度分级

| 层级 | 模块 | 特征 |
|------|------|------|
| **L1 — 公共 Pipeline 贯穿** | assessment | 15 Callable 全注入 + repair + per_issue_rag(DeliLegal) + 23 产物 + 双视图 |
| | eo14117 | 1100行规则引擎 + 红黄绿灯 + 5 Agent per_issue + 10+ 产物 |
| **L2 — 公共 Pipeline 有伤** | eu_scc | 6 Agent + uuid 断链 |
| | cn_flow | context_pack 参数断链 + system prompt 法域污染 |
| **L3 — 专用链，Agent 丰富** | dpia | 9 Agent GDPR 链 |
| | cpra | 10 规则 + 4 Agent + 附件提取 |
| | pipia | 独立 service + 附件证据 + 备案准备度 |
| **L4 — 专用链，双模式** | bcr | 文档驱动/表单驱动双线 + 10 Agent |
| | tia | 确定性评估 + 3 Agent + 静态 riskbook |
| **L5 — 独立体系** | diagnosis | 9 规则决策树 + 4 Agent + 5 步 wizard |
| | review | 8 阶段独立链 + SQLite 持久化 + WebSocket + 4 专用审查器 |

---

## 第八部分：最新进度（2026-08-13 补充）

自 2026-08-07 审计以来，流水线层面的关键结构变化：

### 8.1 新增 `backend/harness/`（task069）

- **迁移**：CLI 白盒执行器的实现代码从 `backend/tests/harness/` 迁出到 `backend/harness/`（`runner.py` / `viewer.py` / `validators.py` / `terminal_trace.py`），`backend/tests/harness/` 只保留 `test_*.py` 测试。
- **倒置依赖已摆正**：生产门禁 `scripts/check_case_parity.py` 由 `from backend.tests.harness.validators import ...` 改为 `from backend.harness.validators import ...`，不再反向依赖 `tests/`。
- **入口变更**：`python -m backend.tests.harness.runner` → `python -m backend.harness.runner`（CI 已同步）。
- **验证**：`pytest backend/tests/harness/ -q` = 88 passed；`scripts/check_case_parity.py` EXIT=0；`python -m backend.harness.runner all --no-llm` = 24 PASS / 2 FAIL（2 失败为 pipia 整改在途，见 8.3）。

### 8.2 新增 `backend/common/reporting/`（task067 / task068）

- 统一三格式（Markdown/DOCX/PDF）同源渲染层：`render_manifest.py`（声明式渲染清单）+ `render_profiles/`（模块画像）+ `renderers/`（渲染器注册表）+ `schema/`（Document IR）+ `shadow_render.py`（新旧对拍）+ `layout_gate.py`（排版门禁）。
- 解决各模块三格式"各自渲染、排版失真"的问题，与 `common/render/` 形成"底层原语 + 上层编排"的分工。

### 8.3 模块与案例口径（最新实测）

- **模块口径**：`config/module_registry.json` 为 **11 个模块**（`cn.scc_review` 已退役），与本文第六/七部分一致。
- **CLI 案例**：`config/case_inventory.json` = **26 CLI 案例 / 603 断言 / 28 前端案例**。
- **pipia 新增案例**：`04_hr_exemption`、`05_certification_eurocert` 已加入，当前 `pipia` 全量 CLI = 3 PASS / 2 FAIL（`02_source_case_missing_scc`、`05_certification_eurocert` 失败，为 pipia 整改在途，非 harness 迁移引入）。
- **全量后端回归**：`pytest backend/` = 1092 passed / 4 failed（4 失败分布见 `DataComplyFlow_项目整体架构说明` §6.6）。

### 8.4 JP/KR 来源隔离（task065）

- 10 个 JP/KR source 标记 `metadata_review_required`，从正式法律结论与条文号引用中隔离（registry / `legal_index_intl` / Evidence Center 三处透传 `can_be_cited=False`）。
- 裁决表 `status/check/task065/jp_kr_source_adjudication.csv`（14 行）与待建 source 提议表（8 行）待法律专家签署后执行第四阶段统一重建；签署前隔离态持续生效。

---

> **文档维护**：本文覆盖前后端全部 11 个模块的完整交互链路。与 `CURRENT_AI4Law_项目事实基线与真实系统理解.md`（基线条目化）和 `CURRENT_DataComplyFlow_全功能运行验证与问题汇报_20260805.md`（功能状态与问题）形成互补；2026-08-13 已同步 task061–task069 后的结构变化（新增第八部分）。
