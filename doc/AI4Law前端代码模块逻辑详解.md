# AI4Law 前端代码模块逻辑详解

> **目标读者**：开发者、想深入了解前端实现的技术人员。
> **编写原则**：以每个代码文件为单元，解释它的职责、核心数据结构、关键函数、与其它模块的协作关系。

---

## 目录

- [一、代码文件总览与分层](#一代码文件总览与分层)
- [二、基础架构层（lib/）](#二基础架构层lib)
  - [2.1 领域类型：domain.ts](#21-领域类型domaints)
  - [2.2 全局状态管理：app-store.tsx](#22-全局状态管理app-storetsx)
  - [2.3 模块运行编排器：module-adapter.ts](#23-模块运行编排器module-adapterts)
  - [2.4 实时事件钩子：useTaskEvents.ts](#24-实时事件钩子usetaskeventsts)
  - [2.5 运行生命周期：run-state.ts](#25-运行生命周期run-statets)
  - [2.6 工作流步骤推导：workflow.ts](#26-工作流步骤推导workflowts)
  - [2.7 响应解析器：workspace.ts](#27-响应解析器workspacets)
  - [2.8 事件→轨迹转换：trace-adapter.ts](#28-事件轨迹转换trace-adapterts)
  - [2.9 产物预览：artifact-preview.ts](#29-产物预览artifact-previewts)
  - [2.10 Markdown 兜底规范化：fallback-markdown.ts](#210-markdown-兜底规范化fallback-markdownts)
  - [2.11 任务模板：task-templates.ts](#211-任务模板task-templatests)
- [三、页面层（pages/）](#三页面层pages)
  - [3.1 入口与路由：App.tsx](#31-入口与路由apptsx)
  - [3.2 任务空间页：TaskSpacesPage.tsx](#32-任务空间页taskspacespagetsx)
  - [3.3 工作台页面：WorkspacePage.tsx](#33-工作台页面workspacepagetsx)
- [四、工作区组件层（components/workspace/）](#四工作区组件层componentsworkspace)
  - [4.1 三栏布局：WorkspaceShell.tsx](#41-三栏布局workspaceshelltsx)
  - [4.2 模块运行面板：ModuleRunPanel.tsx](#42-模块运行面板modulerunpaneltsx)
  - [4.3 事件桥接器：TaskEventBridge.tsx](#43-事件桥接器taskeventbridgetsx)
  - [4.4 全局任务轮询器：GlobalTaskWatcher.tsx](#44-全局任务轮询器globaltaskwatchertsx)
  - [4.5 执行记录回放：RunTranscript.tsx](#45-执行记录回放runtranscripttsx)
- [五、引用渲染层（components/citation/）](#五引用渲染层componentscitation)
  - [5.1 带引用的 Markdown 渲染：CitationMarkdownRenderer.tsx](#51-带引用的-markdown-渲染citationmarkdownrenderertsx)
  - [5.2 悬浮预览卡片：CitationPopover.tsx](#52-悬浮预览卡片citationpopovertsx)
- [六、完整数据流：一次模块运行的全代码路径](#六完整数据流一次模块运行的全代码路径)

---

## 一、代码文件总览与分层

前端代码在 `frontend/src/` 下，按职责分为 5 层：

```
第5层：页面（pages/）          ← 路由对应的完整页面
第4层：工作区组件（workspace/） ← 三栏布局、模块运行、时间线、Copilot
第3层：业务组件（citation/等）  ← 引用渲染、弹窗、导航
第2层：基础架构（lib/）        ← 状态管理、API适配、事件监听、类型定义
第1层：入口                    ← main.tsx → App.tsx → Provider 嵌套
```

**数据流向**：

```
后端 HTTP/SSE  ──→  lib/module-adapter.ts（HTTP）
              ──→  lib/useTaskEvents.ts（SSE/轮询）
                        │
                        ▼
              lib/app-store.tsx（全局状态 reducer）
                        │
                        ▼
              各组件通过 useAppStore() 读取状态并渲染
```

---

## 二、基础架构层（lib/）

### 2.1 领域类型：domain.ts

**文件职责**：定义整个前端共享的 TypeScript 类型。所有组件和 lib 文件都从这里导入类型。

**核心类型及其设计意图**：

```typescript
// 法域 — 三个字面量，不允许拼写错误
type Jurisdiction = "CN" | "EU" | "US"

// 启动模式 — 对应前端的三种工作流风格
type LaunchMode = "rapid" | "draft" | "matrix"

// 12个模块的唯一标识
type ModuleKey = "diagnosis" | "assessment" | "review" | "scc" |
                 "pipia" | "bcr" | "dpia" | "tia" |
                 "cn_flow" | "cpra" | "us_14117" | "eu_scc"

// 任务空间 — 用户创建的一个合规项目
interface TaskSpace {
  id: string                    // 唯一编号
  name: string                  // 用户命名的任务名
  mode: LaunchMode              // 模式
  jurisdiction: Jurisdiction    // 法域
  taskTemplateId: string        // 关联的模板编号
  module: ModuleKey             // 关联的模块
  workspaceStyle: string        // 工作区样式键
  createdAt: string             // ISO时间戳
  updatedAt: string
}

// 模块运行记录 — 每次点击"运行"产生一条
interface ModuleRun {
  id: string
  taskSpaceId: string           // 属于哪个任务空间
  module: ModuleKey
  runMode: "sync" | "async"
  startedAt: string
  finishedAt?: string
  success: boolean
  request?: unknown             // 用户提交的原始表单数据
  response?: unknown            // 后端返回的完整结果
  error?: string
  errorCode?: string
  asyncTaskId?: string          // 异步模式下的任务编号
  asyncState?: string           // 异步状态：running/succeeded/failed
}

// 输出产物 — 运行产生的文件
interface OutputArtifact {
  id: string
  taskSpaceId: string
  module: ModuleKey
  kind: string                  // 类型：report/markdown/docx/json/xlsx/zip
  path: string                  // 文件在服务器上的路径
  createdAt: string
}

// 运行会话 — 一次运行中的实时阶段追踪
interface RunSession {
  id: string
  taskSpaceId: string
  taskId: string
  module: string
  startedAt: string
  stages: StageNode[]           // 每个阶段的执行记录
  isComplete: boolean
  collapsed: boolean            // UI 折叠状态
}

interface StageNode {
  id: string
  name: string                  // 阶段名（如"法规检索"）
  status: "pending" | "running" | "done" | "blocked"
  startedAt: string
  completedAt?: string
  summary?: string
  detail?: Record<string, unknown> | null
  command?: string              // 底层命令（如"RetrievalOrchestrator"）
  icon: string
}

// 面板布局 — 工作台三栏的尺寸和可见性
interface PanelState {
  leftOpen: boolean
  rightOpen: boolean
  leftWidth: number             // 220-520px
  rightWidth: number            // 260-560px
  focusMode: string             // "split" | "focus-left" 等
  stageLayout: string
  primaryPlugin: string
  secondaryPlugin: string
}
```

---

### 2.2 全局状态管理：app-store.tsx

**文件职责**：整个前端的数据中枢。所有需要跨组件共享的状态都在这里。

**核心设计**：

```typescript
// 全局状态对象
type AppState = {
  taskSpaces: TaskSpace[]       // 所有任务空间
  moduleRuns: ModuleRun[]       // 所有运行记录
  artifacts: OutputArtifact[]   // 所有输出产物
  evidenceHits: EvidenceHit[]   // 所有法规命中
  issues: ConsistencyIssue[]    // 所有一致性问题
  systemMessages: SystemMessage[]
  runSessions: RunSession[]     // 实时运行会话
  panelState: PanelState        // 面板布局
  onboarding: OnboardingState   // 引导覆盖层
}
```

**Action 类型（约 20 个）**：`create_task_space`、`delete_task_space`、`append_run`、`append_artifacts`、`begin_run_session`、`stage_running`、`stage_done`、`finish_run_session`、`hydrate_remote_state`、`set_panel_state` 等。

**三个生命周期函数**：

1. **`loadState()`** — 页面首次加载时，从 `localStorage` 读取上次保存的状态。对每个字段做严格的数据校验（检查类型、枚举值、必填字段），防止因 localStorage 被污染导致应用崩溃。

2. **`reducer()`** — 所有状态变更的唯一入口。每个 `dispatch({type, payload})` 调用都会经过这个函数，返回全新的 state 对象（不可变更新）。关键逻辑：

   - `append_run` 的**合并逻辑**：当同一个异步任务先后收到两次 `append_run`（第一次是提交时的占位记录，第二次是轮询得到的终态），不创建两条记录，而是合并为一条。合并规则是"服务端终态数据优先覆盖本地运行中状态"。
   
   - `delete_task_space` 的**联动清理**：删除任务空间时，同时清理所有关联的 moduleRuns、artifacts、evidenceHits、issues、runSessions。这是为了保证删除后没有"孤儿数据"残留。

   - `hydrate_remote_state` 的**多源融合**：从四个来源（后端工作区快照、我的任务、我的报告、运行恢复）合并任务空间和运行记录，使用"先本地后远程，ID 去重"的策略。

3. **`persistState()`** — 每次状态变更后，自动写入 `localStorage`，确保页面刷新不丢数据。

**远程同步**：

```
页面加载
  → fetchWorkspaceState()  // 后端快照
  → fetchMyTasks()         // 用户的所有模块任务
  → fetchMyReports()       // 用户的所有报告产物
  → fetchWorkspaceRecovery() // 异步任务的恢复数据
  → 四路结果 mergeTaskSpaces() + dedupeById()
  → dispatch(hydrate_remote_state)
```

**保存到后端**：以 500ms 防抖延迟，在状态变更后自动调用 `saveWorkspaceState()` 将状态推送到后端。这意味着用户换设备登录，任务空间不会丢失。

**为什么用 Context + useReducer 而不是 Redux？**

状态量小（几十个任务空间、几十个产物），Redux 的中间件和 devtools 优势体现不出来。Context + useReducer 零依赖、够用。

---

### 2.3 模块运行编排器：module-adapter.ts

**文件职责**：前端与后端模块 API 的唯一通信层。所有"运行模块"的操作都经过这里。

**核心数据结构**：

```typescript
// 12个模块的后端端点注册表
const MODULES: ModuleDefinition[] = [
  {
    key: "assessment",
    label: "Assessment",
    jurisdiction: "CN",
    syncEndpoint: "/api/v1/assessment/generate",
    asyncSubmitEndpoint: "/api/v1/assessment/generate_async",
    asyncStatusEndpoint: (taskId) => `/api/v1/assessment/tasks/${taskId}`,
    asyncRetryEndpoint: (taskId) => `/api/v1/assessment/tasks/${taskId}/retry`
  },
  // ... 其余11个模块类似
]
```

**`runModule()` 函数** — 核心运行逻辑：

```
runModule(moduleDef, payload, runMode, timeoutMs, onProgress, onTaskDiscovered)

if (同步模式):
    → POST moduleDef.syncEndpoint  →  等待响应  →  返回 {response, runMode: "sync"}

if (异步模式):
    → POST moduleDef.asyncSubmitEndpoint  →  获得 taskId
    → 立即回调 onTaskDiscovered(taskId)  （让调用方马上知道 taskId）
    → 进入轮询循环：
        while (未超时):
            → GET moduleDef.asyncStatusEndpoint(taskId)
            → 回调 onProgress(state, progress)
            → if state in ["succeeded","completed","failed","cancelled"]:
                → 终态到达，返回结果
            → sleep(1500ms)  // 每1.5秒问一次
    → 超时 → 抛出超时错误
```

**错误处理的三级分类**：

```typescript
class BackendConnectionError extends Error {
  code: "backend_unreachable"    // 后端根本连不上
      | "backend_http_empty"     // 后端返回空响应
      | "backend_http_error"     // 后端返回错误（含 HTTP status）
  status?: number
  url?: string
}
```

这个分类让前端能区分"网络故障"和"业务错误"，在 UI 上给用户不同的提示。

**`requestJson()` 辅助函数** — 所有 HTTP 请求的统一封装：

- 自动附加 JWT 认证头部
- 捕获网络错误并转换为 `BackendConnectionError`
- 解析 HTTP 错误响应体中的 `detail` 字段作为错误消息
- 支持 JSON 解析失败的兜底提示

**`fetchModuleTaskStatus()`** — 单次状态查询，处理 404 错误（任务过期）：

```typescript
if (error instanceof BackendConnectionError && error.status === 404):
    → 抛出 AsyncTaskNotFoundError
    → 上层捕获后，将任务标记为 failed，错误信息为"异步任务状态不存在"
```

---

### 2.4 实时事件钩子：useTaskEvents.ts

**文件职责**：建立前端与后端的实时事件通道，支持 SSE（服务器推送事件）和 HTTP 轮询两种方式。

**全局注册表**（模块级单例）：

```typescript
const eventSources = new Map<string, EventSource>()    // 每个 taskId 一个 SSE 连接
const listeners = new Map<string, Set<callback>>()     // 每个 taskId 一组监听回调
const eventBuffers = new Map<string, RunEvent[]>()     // 每个 taskId 的事件缓冲区
```

**SSE 连接**：

```typescript
function connectSSE(taskId):
    es = new EventSource(`/api/v1/events/task/${taskId}/stream`)
    es.onmessage = (e) => {
        解析 JSON → 推入 eventBuffers[taskId]
        → 通知所有 listeners[taskId] 中的回调函数
    }
    es.onerror = () => {
        // 不手动关闭！让浏览器自动重连
        // 仅在 readyState === CLOSED 时才从 registry 中移除
    }
```

**降级策略（关键设计）**：

```
方案1：SSE 初始化
    → 连接 /api/v1/events/task/{taskId}/stream

方案2：3 秒后检查
    if SSE 的 buffer 为空（3秒内没收到任何事件）:
        → 启动 HTTP 轮询（每1.5秒 GET /api/v1/events/task/{taskId}/events?since=N）
    else （SSE 正常工作过）:
        → 每5秒检查一次 SSE readyState
        if SSE 已 CLOSED:
            → 从最后一个已知序列号开始 HTTP 轮询
```

这个双通道设计保证了：SSE 正常时低延迟实时推送，SSE 不可用时自动降级为轮询。

**Token 用量提取**：

```typescript
function extractTokenUsage(events: RunEvent[]):
    扫描所有事件中的 llm_chat 调用
    → 按 channel 分为 "workflow" 和 "copilot" 两类
    → 累加 prompt_tokens, completion_tokens, total_tokens
    → 在 Copilot 面板中展示用量
```

---

### 2.5 运行生命周期：run-state.ts

**文件职责**：判断一个 `ModuleRun` 当前处于什么状态。

**终态常量**：

```typescript
TERMINAL_ASYNC_STATES = ["succeeded", "completed", "failed", "cancelled"]
SUCCESS_ASYNC_STATES = ["succeeded", "completed"]
FAILED_ASYNC_STATES = ["failed", "cancelled"]
```

**状态判断函数**：

```typescript
isRunInProgress(run):
    异步任务 && 有 asyncTaskId
    && asyncState 不处于终态
    && 没有 finishedAt

isRunSuccessful(run):
    asyncState ∈ SUCCESS_ASYNC_STATES
    || (不在运行中 && 有 finishedAt && success === true)

isRunFailed(run):
    asyncState ∈ FAILED_ASYNC_STATES
    || (不在运行中 && 有 finishedAt && success === false && 不是 unreachable)

isRunUnreachable(run):
    不在运行中 && 有 finishedAt && errorCode === "backend_unreachable"
```

**`selectPreferredRun(runs)`** — 从多次运行中选出"当前最相关"的那次：

```
优先级：
1. 正在运行的（取最新的）
2. 最近完成的（按 finishedAt 降序）
```

**`selectRunningModuleRuns(runs)`** — 筛选出所有需要轮询的运行：

```
条件：
- asyncTaskId 存在
- asyncState 不是终态
- finishedAt 未设置
```

这是 `GlobalTaskWatcher` 的数据源。

---

### 2.6 工作流步骤推导：workflow.ts

**文件职责**：根据运行状态、产物、证据、问题，推导出 5 步工作流的每步状态。

```typescript
function deriveWorkflowSteps(taskSpace, latestRun, artifacts, evidence, issues):
    返回 [
        { key: "input_validation",   status: 有运行记录 ? done : pending },
        { key: "execution",          status: 运行中 ? running : 成功 ? done : blocked },
        { key: "evidence_binding",   status: 有证据命中 ? done : 成功但无证据 ? blocked : pending },
        { key: "consistency_check",  status: 有问题 ? blocked : 成功 ? done : pending },
        { key: "report_export",      status: 有产物 ? done : 运行中或成功 ? running : pending }
    ]
```

**设计意图**：这个 5 步模型是对所有模块的通用抽象。不是每个模块都严格按这 5 步执行（诊断模块可能跳过证据绑定），但它提供了一个统一的状态视图，前端基于这个视图渲染"画布"标签页中的进度条。

---

### 2.7 响应解析器：workspace.ts

**文件职责**：从后端返回的原始 JSON 中提取结构化数据。

**三个提取函数**：

1. **`extractInsight(response)`**：从响应中提取报告路径、输出文件列表、风险等级、推荐路径、一致性问题、法规引用摘要。兼容多种响应格式（有的模块把数据放在 `response.result` 中，有的直接放在顶层）。

2. **`extractArtifacts(taskSpaceId, module, response)`**：从响应的 `output_files` 字典中提取所有文件路径，转换为 `OutputArtifact[]` 列表。去重逻辑：按路径去重（`seenPaths` Set）。

3. **`extractEvidenceHits(taskSpaceId, module, response)`**：从响应的 `regulations` 数组和 `chapters` 数组的 `citations` 中提取法规命中。每条命中包含：来源类型（regulation/citation）、标题、摘要。

4. **`extractConsistencyIssues(taskSpaceId, module, response)`**：从响应的 `consistency_issues` 数组中提取问题，自动判断严重度（包含 "high" → high，否则 medium）。

---

### 2.8 事件→轨迹转换：trace-adapter.ts

**文件职责**：将原始的 `RunEvent[]` 流转换为语义化的 `TraceNode[]` 树。

**为什么要转换？** 后端推送的原始事件是扁平的、无结构的（`tool_start`、`tool_result`、`intermediate` 等），前端需要把它们组织成"用户能理解的步骤"。

**语义映射**：

| 原始事件类型 | 映射到哪个阶段 | 阶段含义 |
|------------|-------------|---------|
| `status` | Task | 任务状态更新 |
| `thought` | LLM | AI 的推理摘要 |
| `tool_start` | Tool | 工具调用开始 |
| `tool_result` | Tool | 工具调用结果 |
| `intermediate` | Review | 中间产物产出 |
| `warning` | Review | 警告 |
| `final` | Task | 工作流完成 |
| `final_brief` | Review | 客户简报 |

**内容格式化**：对每种 detail 类型有专门的格式化函数——数组截取前 3 项、对象提取 title/name/id、长文本截断到 120 字、白空格规范化。

---

### 2.9 产物预览：artifact-preview.ts

**文件职责**：从后端获取产物的预览内容。

```typescript
function fetchArtifactPreview(path: string): Promise<ArtifactPreview>
    → GET /api/v1/artifacts/preview?path={encodeURIComponent(path)}
    → 返回 { path, file_name, kind, render_mode, content, file_url }
```

`render_mode` 有四种：
- `"html"` — 以 HTML 片段渲染（用 iframe 嵌入）
- `"pdf"` — 以 PDF 嵌入预览
- `"text"` — 以纯文本/Markdown 渲染
- `"download"` — 不预览，直接触发下载

---

### 2.10 Markdown 兜底规范化：fallback-markdown.ts

**文件职责**：当后端返回的不是合法 Markdown（比如纯文本、带中文标点的类 Markdown），前端自己把它转成合法的 Markdown。

**关键转换规则**：
- 检测 `第X章`、`数字+顿号`、`全角括号数字` 等中文标题模式 → 转为 `#` `##` `###`
- 检测管道符分隔的行 → 转为 Markdown 表格
- 处理 `数字)` 格式 → 转为 `数字.` 格式
- 清理多余空行、规范化空白

这个文件的存在意义：后端有些旧模块返回的不是规范 Markdown，而这个兜底逻辑确保前端始终能渲染出可读的报告。

---

### 2.11 任务模板：task-templates.ts

**文件职责**：定义 10 个预定义任务模板，每个模板指定了模块、法域、工作区风格、双语输入提示和输出提示。

```typescript
const TEMPLATES = [
  {
    id: "cn_diagnosis",
    title: { zh: "合规路径诊断", en: "Compliance Path Diagnosis" },
    module: "diagnosis",
    jurisdiction: "CN",
    workspaceStyle: "diagnosis",
    inputHint: { zh: "填写企业基本信息和数据处理情况...", en: "..." },
    outputHint: { zh: "系统将输出推荐合规路径、法律依据...", en: "..." },
  },
  // ... 其余 9 个
]
```

三个辅助函数：
- `findTaskTemplate(id)` — 按编号查找模板
- `getDefaultTaskTemplate(jurisdiction)` — 获取某法域的默认模板
- `getTaskTemplateTitle(id)` — 获取模板的当前语言标题

---

## 三、页面层（pages/）

### 3.1 入口与路由：App.tsx

**文件职责**：应用的根组件，负责 Provider 嵌套、路由注册、全局模态框管理。

**Provider 嵌套顺序**（从外到内）：

```
LanguageProvider          ← 国际化，使所有子组件可用 useLang()
  AuthProvider            ← 认证状态，使所有子组件可用 useAuth()
    AppStoreProvider      ← 全局业务状态，使所有子组件可用 useAppStore()
      BrowserRouter       ← 路由
        AppShell          ← 实际内容
```

**AppShell 的 5 个职责**：

1. **后端健康检查**：每 30 秒 ping `/health`，后端不通时顶部显示红色横幅
2. **全局模态框栈**：管理"模式选择 → 创建任务空间"的二步弹窗流程
3. **新手引导**：管理 QuickStartModal 和 OnboardingOverlay 的显示/关闭
4. **路由表**：14 个 Route 定义，受保护页面包裹 `ProtectedRoute`
5. **挂载全局组件**：`<GlobalTaskWatcher />` 始终存在，不依赖任何页面

**`createTask()` 函数**：创建任务空间的完整流程：

```
1. 生成唯一编号：task-{时间戳}
2. 按模板编号查找模板 → 获取 module 和 workspaceStyle
3. dispatch(create_task_space) → 写入全局状态
4. 关闭弹窗
5. navigate(`/workspace/${id}`) → 跳转到新任务的工作台
```

---

### 3.2 任务空间页：TaskSpacesPage.tsx

**文件职责**：管理所有合规项目的 CRUD 页面。

**核心交互**：

- **快速创建卡片**：三块法域卡片（CN/EU/US），每块列出该法域可用的模板按钮。点击按钮弹出配置弹窗。
- **任务列表**：搜索框 + 法域筛选 + 文本搜索。每个任务行显示最近一次运行的状态（绿色对勾/黄色旋转/红色叉号/灰色闲置）。
- **内联重命名**：双击任务名进入编辑模式，回车确认，Escape 取消。
- **删除**：点击删除 → 确认弹窗 → 调用后端 `deleteProjectHistory()` 清理所有关联文件 → dispatch 更新状态。

**运行状态指示**：每个任务行调用 `getRunLifecycleState(run)` 获取四种状态（idle/running/success/failed），渲染对应颜色和图标。

---

### 3.3 工作台页面：WorkspacePage.tsx

**文件职责**：工作台的路由调度器。

```typescript
// 从 URL 参数获取 taskId → 查找 TaskSpace
const taskSpace = state.taskSpaces.find(item => item.id === taskId)

// 如果找不到，重定向到最近更新的任务空间
if (!taskSpace) {
    const latest = state.taskSpaces[0]
    if (latest) navigate(`/workspace/${latest.id}`)
    return
}

// 渲染 WorkspaceShell
return <WorkspaceShell taskSpace={taskSpace} />
```

这个页面的逻辑很简单——它只负责"找到正确的 TaskSpace 并传给 Shell"。所有复杂交互都在 WorkspaceShell 中。

---

## 四、工作区组件层（components/workspace/）

### 4.1 三栏布局：WorkspaceShell.tsx

**文件职责**：系统最大最复杂的组件（~1605 行），实现 IDE 风格的三栏工作区。

**布局状态**：

```typescript
// 三栏宽度限制
LEFT_PANEL_MIN=220  LEFT_PANEL_MAX=520
RIGHT_PANEL_MIN=260 RIGHT_PANEL_MAX=560
CENTER_PANEL_MIN=360
RESIZER_WIDTH=10

// 从 app-store 读取布局偏好
const { state } = useAppStore()
const panelState = state.panelState  // leftOpen, rightOpen, leftWidth, rightWidth, focusMode
```

**拖拽调整宽度**：

```typescript
// 监听 pointerdown → pointermove → pointerup
const onResizerPointerDown = (side: "left" | "right") => (event) => {
    event.target.setPointerCapture(event.pointerId)
    
    const onMove = (moveEvent) => {
        const delta = moveEvent.clientX - event.clientX
        const newWidth = clamp(panelWidth + delta, MIN, MAX)
        dispatch({ type: "set_panel_state", payload: { [side + "Width"]: newWidth } })
    }
    
    const onUp = () => {
        event.target.releasePointerCapture(event.pointerId)
        removeListeners()
    }
}
```

**标签页系统**：

```typescript
// 6个固定标签页
const WORKSPACE_TABS = [
    { id: "details",   closable: false },   // 默认：模块运行面板
    { id: "canvas",    closable: true  },   // 工作流画布
    { id: "docs",      closable: true  },   // 模块文档
    { id: "terminal",  closable: true  },   // 运行日志
    { id: "report",    closable: true  },   // 报告预览
    { id: "timeline",  closable: true  },   // 执行时间线
]

// 动态资源标签页（从左侧栏点击打开）
type ResourcePreviewTab = {
    id: string
    label: string
    resource: OpenedResource
}
```

**标签页切换逻辑**：

```
运行开始时：
    → 自动切换到 "timeline" 标签页
运行完成后：
    → 自动切换到 "report" 标签页
用户点击左侧栏文件：
    → 创建新的 ResourcePreviewTab → 切换到该标签页
```

**报告预览**：当 `activeTab === "report"` 时，渲染逻辑分三步：

1. **检查是否有 preferred artifact**（优先 html > report > markdown > md > docx > pdf）
2. **如果有**：调用 `fetchArtifactPreview(path)` 获取预览内容
3. **如果没有**：从 `run.response` 中提取章节内容，用 `buildFallbackPreviewSections()` 构造报告预览

**报告预览的分节提取**（`buildFallbackPreviewSections`）：
- 执行摘要（从 `result.summary`）
- 命中规则与判断依据（从 `result.hit_rules`）
- 详细审查结果（从 `response.findings` 或 `response.problems` 构造 Markdown 表格）
- 引用法规与条文（从 `result.citations`）
- 建议下一步（从 `result.next_actions`）
- 一致性提示（从 `response.consistency_issues`）

**左侧栏与中央区域的联动**：

```typescript
// 左侧栏 ResourcePanel 通过 onOpenResource 回调通知 Shell
const handleOpenResource = (target: ResourceOpenTarget) => {
    // 创建 OpenedResource
    const resource: OpenedResource = { kind, name, path, fileType }
    // 创建或切换到此资源的标签页
    const tabId = getResourceTabId(resource)
    const existingTab = resourceTabs.find(tab => tab.id === tabId)
    if (existingTab) {
        setActiveTab(tabId)  // 切换到已有标签页
    } else {
        setResourceTabs([...resourceTabs, { id: tabId, label, resource }])
        setActiveTab(tabId)  // 创建新标签页并切换
    }
}
```

---

### 4.2 模块运行面板：ModuleRunPanel.tsx

**文件职责**：为 12 个模块提供统一的表单界面和运行逻辑。

**表单值管理**：

```typescript
// 每个模块有自己的表单值接口
interface DiagnosisFormValues {
    company_name: string
    q1_is_ciio: "yes" | "no" | "unknown"
    // ...
}

interface AssessmentFormValues {
    company_name: string
    is_ciio: boolean
    pii_count: number
    // ...
}

// 表单值状态
const [formValues, setFormValues] = useState<Record<string, unknown>>({})
```

**字段配置**：每个模块有一个 `steps` 数组，每个步骤包含多个 `fields`，每个字段定义：`key`（字段名）、`label`（显示标签）、`type`（输入类型：text/number/select/boolean/multiselect/file/fileGroup/textarea）、`required`（是否必填）、`options`（枚举选项）。

**运行触发**：

```typescript
const handleRun = async (runMode: "sync" | "async") => {
    // 1. 组装请求体
    const payload = buildRequestPayload(module, formValues)
    
    // 2. 调用 module-adapter
    const result = await runModule(
        moduleDef, payload, runMode, 180000,
        onProgress,           // 进度回调
        onTaskDiscovered,     // 获得 taskId 后立即回调
    )
    
    // 3. 回调父组件
    onRunDone({
        module: moduleDef.key,
        response: result.response,
        runMode: result.runMode,
        asyncTaskId: result.asyncTaskId,
    })
}
```

**开发者预设**：每个模块有一个 `devPresets` 数组，包含预配置的测试数据。选择预设后自动填充表单。

---

### 4.3 事件桥接器：TaskEventBridge.tsx

**文件职责**：将后端的实时事件流转换为全局状态中的运行会话更新。这是一个**零 UI 渲染**的组件（返回 `null`），只做数据桥接。

**核心逻辑**：

```typescript
function TaskEventBridge({ taskId, taskSpaceId, moduleLabel }) {
    const events = useTaskEvents(taskId)   // 订阅事件
    const { dispatch } = useAppStore()
    
    useEffect(() => {
        for (const event of newEvents) {
            switch (event.event_type) {
                case "status":
                    // 创建运行会话
                    dispatch(begin_run_session, { sessionId: `run-${taskId}`, ... })
                    break
                    
                case "tool_start":
                    // 开始一个新阶段
                    dispatch(begin_run_session, { stages: [{ status: "running", ... }] })
                    pendingStages.push(stageId)
                    break
                    
                case "tool_result":
                    // 结束当前阶段
                    const stageId = pendingStages.pop()
                    dispatch(stage_done, { sessionId, stageId, summary, detail })
                    break
                    
                case "final":
                    // 运行完成
                    dispatch(finish_run_session, { sessionId, completedAt, totalDurationMs })
                    break
            }
        }
    }, [events])
    
    return null  // 不渲染任何 UI
}
```

**阶段名称提取**：从事件的 `detail.agent` 或 `detail.tool` 中提取代理名称（如"重要数据分析 Agent 完成"），如果都没有就用 `summary` 截断到 12 字符。

**为什么用 `pendingStagesRef`？** `tool_start` 和 `tool_result` 不一定配对（某些事件流中可能缺一个），用栈机制保证 `tool_result` 总是关掉最近一个 `tool_start` 开启的阶段。

---

### 4.4 全局任务轮询器：GlobalTaskWatcher.tsx

**文件职责**：一个全局组件（挂在 `App.tsx` 中，不依赖任何页面），持续轮询所有异步任务的完成状态。

**轮询逻辑**：

```typescript
function GlobalTaskWatcher() {
    const { state, dispatch } = useAppStore()
    const stateRef = useRef(state)     // 用 ref 避免频繁重建 interval
    
    useEffect(() => {
        const INTERVAL = 5000  // 每5秒
        
        const poll = async () => {
            const runningRuns = selectRunningModuleRuns(stateRef.current.moduleRuns)
            if (runningRuns.length === 0) return
            
            // 并行查询所有运行中的任务
            const promises = runningRuns.map(async (run) => {
                const status = await fetchModuleTaskStatus(moduleDef, run.asyncTaskId)
                
                if (isFinalAsyncState(status.state)) {
                    // 终态到达 → dispatch 更新
                    dispatch(append_run, {
                        ...run,
                        finishedAt: now,
                        success: isSuccessAsyncState(status.state),
                        response: status.result,
                        asyncState: status.state,
                    })
                }
            })
            await Promise.allSettled(promises)
        }
        
        poll()                           // 挂载时立即执行一次
        const timer = setInterval(poll, INTERVAL)
        return () => clearInterval(timer)
    }, [dispatch])  // 只依赖 dispatch（稳定引用）
    
    return null
}
```

**错误处理**：如果任务过期（`AsyncTaskNotFoundError`），自动标记为失败并记录错误。

**防重复轮询**：`inFlightRef` 保证同一个 taskId 不会同时有多个请求在飞。

---

### 4.5 执行记录回放：RunTranscript.tsx

**文件职责**：将 `RunSession` 中的阶段列表渲染为可视化的执行时间线。

**渲染逻辑**：

```
对于每个 stage：
    ├── 渲染阶段图标（🔧 工具调用 / 📊 中间产物 / ⚠️ 警告 / ● 其他）
    ├── 渲染阶段名称 + 耗时
    ├── 可展开：点击查看 detail 内容
    │   ├── JSON → 格式化显示
    │   ├── 数组 → 截取前 N 项列表
    │   └── 长文本 → 截断 + "显示更多"
    └── 自动滚动：新阶段出现时自动滚到底部
```

---

## 五、引用渲染层（components/citation/）

### 5.1 带引用的 Markdown 渲染：CitationMarkdownRenderer.tsx

**文件职责**：将报告 Markdown 渲染为 HTML，同时让其中的法规引用变成可交互的标签。

**核心流程**：

```typescript
function CitationMarkdownRenderer({ markdown, taskId, moduleKey }) {
    // 1. 从后端获取引用映射
    const citationMap = await fetchCitationMap(taskId)
    // 返回：{ "CIT-REG-001": { source_id, title, article_no, snippet, can_jump, ... } }
    
    // 2. 解析 Markdown 中的引用标记
    // 支持的格式：
    //   - 【依据：法规标题 第X条】
    //   - [1], [2] 脚注格式
    //   - {{CIT-REG-001}} 占位符格式
    
    // 3. 自定义 ReactMarkdown 的渲染组件
    <ReactMarkdown
        components={{
            // 自定义段落渲染：检测并替换引用标记
            p: ({ children }) => {
                // 扫描段落文本
                // 匹配到【依据：...】→ 替换为可点击的 CitationBadge
                // 匹配到 [N] → 替换为脚注链接
            },
            // 自定义链接渲染：法规引用链接使用特殊样式
            a: ({ href, children }) => {
                if (href?.startsWith("/knowledge/laws/")) {
                    return <CitationLink sourceId={...}>{children}</CitationLink>
                }
                return <a href={href}>{children}</a>
            },
        }}
    />
}
```

**引用点击行为**：

```typescript
const handleCitationClick = (citation: CitationDetail) => {
    // 1. 优先：如果知识库中有该来源且有条文锚点
    const knowledgeUrl = buildFallbackKnowledgeUrl(citation)
    if (knowledgeUrl) {
        window.open(knowledgeUrl, "_blank")  // 新标签页打开
        return
    }
    
    // 2. 次选：在侧边抽屉中展示引用原文
    setDrawerCitation(citation)
    setDrawerOpen(true)
    
    // 3. 兜底：如果来源完全不详，无反应
}
```

**中文数字转阿拉伯数字**：内置了一个中文数字转换器，能将"第四条"转换为数字 4，用于匹配知识库中的条文编号。

---

### 5.2 悬浮预览卡片：CitationPopover.tsx

**文件职责**：鼠标悬浮在引用标记上时，弹出轻量预览卡片。

```typescript
function CitationPopover({ citation, anchorEl }) {
    return (
        <div className="citation-popover" style={{ position: "absolute", top, left }}>
            <div className="popover-header">
                {citation.source_title}
            </div>
            <div className="popover-article">
                {citation.article_no && `第${citation.article_no}条`}
            </div>
            <div className="popover-snippet">
                {citation.snippet?.slice(0, 200)}
            </div>
            <div className="popover-meta">
                <span>来源类型：{citation.source_kind}</span>
                <span>约束力：{citation.binding_force}</span>
                <span>用途：{citation.usage_note}</span>
            </div>
        </div>
    )
}
```

悬浮卡片出现后，点击卡片外部或按下 Escape 键关闭。

---

## 六、完整数据流：一次模块运行的全代码路径

以用户在"星辰支付-安全评估"任务空间中点击"开始生成"为例，追踪代码执行路径：

```
1. 用户点击"开始生成"
   ModuleRunPanel.tsx — handleRun("async")

2. 组装 payload 并发送
   module-adapter.ts — runModule(moduleDef, payload, "async", ...)
       → POST /api/v1/assessment/generate_async
       → 获得 taskId = "a7b3c9d1-..."
       → onTaskDiscovered(taskId) 回调

3. WorkspaceShell 收到 taskId
   → 挂载 <TaskEventBridge taskId={taskId} ... />
   → 切换到 "timeline" 标签页

4. 实时事件订阅
   useTaskEvents.ts — connectSSE(taskId)
       → EventSource 连接 /api/v1/events/task/{taskId}/stream
       → 每收到一个事件，推入 eventBuffers[taskId]
       → 通知 listeners[taskId] 中的回调

5. 事件 → 执行时间线更新
   TaskEventBridge.tsx
       → event "tool_start" → dispatch(begin_run_session, stages=[{status:"running"}])
       → event "tool_result" → dispatch(stage_done)
       → app-store.tsx reducer 更新 runSessions
       → WorkspaceShell 重新渲染，时间线显示新阶段

6. 异步轮询检查终态
   module-adapter.ts — 轮询循环
       → 每1.5秒 GET /api/v1/assessment/tasks/{taskId}
       → state === "succeeded" → 返回结果
       → 同时 GlobalTaskWatcher.tsx 每5秒也在轮询（双保险）

7. 运行完成，吸收结果
   WorkspaceShell.tsx — onRunDone(result)
       → extractArtifacts(taskSpaceId, module, response) → dispatch(append_artifacts)
       → extractEvidenceHits(...) → dispatch(append_evidence)
       → extractConsistencyIssues(...) → dispatch(append_issues)
       → dispatch(append_run, { finishedAt, success:true, response })
       → 自动切换到 "report" 标签页

8. 左侧栏文件树更新
   ResourcePanel.tsx — 读取 state.artifacts
       → 过滤 taskSpaceId 匹配的产物
       → 按输入/输出分组渲染
       → 每个文件显示类型图标 + 文件名 + 下载按钮

9. 报告渲染
   WorkspaceShell.tsx — activeTab === "report"
       → 查找 preferred artifact → fetchArtifactPreview(path)
       → 或 fallback: buildFallbackPreviewSections(response)
       → CitationMarkdownRenderer 渲染 Markdown
           → 引用可悬浮预览、可点击跳转

10. 状态持久化
    app-store.tsx — useEffect 监听 state 变化
        → 500ms 防抖 → saveWorkspaceState() → POST 到后端
        → persistState() → 写入 localStorage
```

---

> **文档版本**：2026年6月6日
> **配套文档**：[前端设计体系与交互逻辑详解](AI4Law前端设计体系与交互逻辑详解.md) — 从用户视角讲前端设计，本文档从代码视角讲实现
