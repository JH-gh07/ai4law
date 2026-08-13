# frontend/src 目录结构与命名规范详解

> 本文件是 `frontend/src` 的「自解释地图」：讲清楚每个目录为什么存在、目录之间**有什么区别**、每个文件**该怎么命名**、以及「我新写一个文件该放哪」。

---

## 0. 一句话总纲

`frontend/src` 是 React + TypeScript 单页应用（SPA）的全部源码，采用**「按职责分层」**的目录组织，而不是「按功能/页面」组织。

核心思想：**一个文件的物理位置，由它「是什么类型的东西」决定，而不是由它「属于哪个业务功能」决定。**

| 层 | 目录 | 一句话职责 | 是否含 UI（JSX） |
|---|---|---|---|
| 入口 | `main.tsx` / `App.tsx` | 应用启动、路由装配 | ✅ |
| 路由页面 | `pages/` | 一个 URL = 一个页面 | ✅ |
| 可复用 UI 组件 | `components/` | 页面里被组合的「零件」 | ✅ |
| 功能业务逻辑 | `features/` | 某个功能专属的**纯逻辑/类型** | ❌（纯 `.ts`） |
| 通用工具与状态 | `lib/` | 跨功能复用的纯函数/类型/hooks/Context | 少数（Provider） |
| 网络请求边界 | `api/` | 与后端 HTTP 接口一一对应的封装 | ❌ |
| 样式 | `styles/` | CSS（设计令牌 + 应用样式） | — |

---

## 1. 目录职责与命名规范

### 1.1 `pages/` —— 路由级页面（「一屏一页」）

**职责**：与 React Router 的路由一一对应，是「一个 URL 对应的完整一屏」。

**命名规范**：
- 文件名：`PascalCase + Page` 后缀，例如 `HomePage.tsx`、`WorkspacePage.tsx`、`ReportCenterPage.tsx`。
- 导出：**具名导出**组件函数，如 `export function WorkspacePage()`。
- 子目录按「业务域」分，如 `pages/auth/LoginPage.tsx`（登录/注册）。

**为什么有 `Page` 后缀**：为了让「页面」和「同名组件」一眼区分。例如 `ReportCenterPage`（路由页）和 `components/report-center/`（该页内部拆出的零件）不会混淆。

**判断标准**：一个文件如果「独占一个路由、由 Router 直接渲染」，就放 `pages/`。

```
pages/
├── HomePage.tsx           # 首页（路由 /）
├── JurisdictionHubPage.tsx # 法域枢纽（路由 /jurisdiction）
├── WorkspacePage.tsx      # 工作台（路由 /workspace/:id）
├── ReportCenterPage.tsx   # 报告中心
├── EvidenceCenterPage.tsx # 知识库中心
├── LawViewerPage.tsx      # 法律条文查看
├── TaskSpacesPage.tsx     # 任务空间列表
├── ProfilePage.tsx        # 个人中心
├── SettingsPage.tsx       # 设置
├── DocsPlaceholderPage.tsx # 文档占位
└── auth/
    ├── LoginPage.tsx      # 登录页
    └── RegisterPage.tsx   # 注册页
```

---

### 1.2 `components/` —— 可复用 UI 组件（「页面里的零件」）

**职责**：可被多个页面/模块复用的**展示型组件**。它们是「零件」，本身不定义路由、不发起业务编排。

**命名规范**：
- 文件名：`PascalCase.tsx`（**无** `Page`/`Component` 后缀），如 `PdfViewer.tsx`、`ModalShell.tsx`。
- 子目录按「用途/领域」分组，**不是**按页面分组。

**子目录与命名区别**（这是本目录的关键）：

| 子目录 | 放什么 | 例子 |
|---|---|---|
| `common/` | **全局通用**的基础组件、被所有人复用 | `TopNav.tsx`、`ModalShell.tsx`、`PdfViewer.tsx`、`AppIcons.tsx`、`LazyRouteErrorBoundary.tsx` |
| `auth/` | 认证相关组件 | `ProtectedRoute.tsx`（路由守卫）、`UserMenu.tsx`（用户菜单） |
| `citation/` | 法律引用渲染相关 | `CitationMarkdownRenderer.tsx`、`CitationPopover.tsx`、`KnowledgeContentRenderer.tsx` |
| `workspace/` | 工作台工作区内部面板/组件 | `WorkspaceShell.tsx`、`ModuleRunPanel.tsx`、`RunTranscript.tsx`、`TraceNodeView.tsx`、`TaskEventBridge.tsx` |
| `report/` | 报告**文档**渲染（结构化报告体） | `ReportDocumentView.tsx`、`ClauseTree.tsx`、`FindingView.tsx` |
| `report-center/` | 报告**中心页**的侧栏 | `ReportTaskTreeSidebar.tsx` |
| `landing/` | 落地页 | `LandingPage.tsx` |
| `modals/` | 各类弹窗 | `CreateWorkspaceModal.tsx`、`ModeSelectModal.tsx`、`QuickStartModal.tsx`、`OpenQuestModal.tsx` |
| `onboarding/` | 新手引导 | `OnboardingOverlay.tsx` |

**命名区别关键点**：
- `report/` vs `report-center/`：`report/` 是**报告文档的渲染组件**（怎么画一份报告），`report-center/` 是**报告中心页面专属的辅助组件**（页面侧边栏）。前者面向「报告内容」，后者面向「报告列表页」。
- `modals/` vs `common/ModalShell.tsx`：`ModalShell` 是**弹窗的壳（通用骨架）**，放 `common/`；而**具体业务弹窗**（创建空间、选择模式等）放 `modals/`。

---

### 1.3 `features/` —— 功能业务逻辑（「无 UI 的领域层」）

**职责**：某个**具体功能**专属的业务逻辑、类型、payload 构建。**关键特征：纯 `.ts`，不含任何 JSX**，因此可被单测直接覆盖。

**命名规范**：
- 目录名：`kebab-case` 功能名，如 `module-runner`、`resource-explorer`。
- 文件内：纯函数用 `kebab-case.ts`（如 `file-path.ts`、`input-resources.ts`），类型文件用 `types.ts`/`contracts.ts`。

**两个功能域**：

```
features/
├── module-runner/            # 「运行合规模块」的表单与 payload 构建逻辑
│   ├── model.ts              # 各模块的步骤配置/表单定义
│   ├── types.ts              # 结果/进度/选项类型
│   └── payload-builders/     # 把表单值 → 后端请求体
│       ├── index.ts          # 统一出口（re-export）
│       ├── common.ts         # 三法域共用校验/拆分工具
│       ├── cn.ts             # 中国模块 payload
│       ├── eu.ts             # 欧盟模块 payload
│       └── us.ts             # 美国模块 payload
└── resource-explorer/        # 「资源浏览器」的输入/输出资源归类逻辑
    ├── contracts.ts          # 资源相关类型契约
    ├── config.ts             # 扩展名/角色标签配置
    ├── file-path.ts          # 文件名/路径处理
    ├── path-tree.ts          # 路径树构建
    ├── input-resources.ts    # 用户输入文件收集
    └── output-artifacts.ts   # 输出产物归类
```

**`features/` 与 `components/` 的区别（核心）**：
- `components/` 是「**怎么画**」（含 JSX 的展示层）。
- `features/` 是「**怎么算**」（无 JSX 的业务逻辑/类型/转换函数）。
- 一个功能往往「`features/` 算逻辑 + `components/` 画 UI」配合：`features/module-runner/payload-builders/` 产出请求体，`components/workspace/ModuleRunPanel.tsx` 负责展示运行结果。

---

### 1.4 `lib/` —— 通用工具与全局状态（「跨功能的纯逻辑」）

**职责**：**跨功能复用**的纯函数、纯类型、通用 hooks、全局 Context/Store。和 `features/` 的区别在于：`features/` 是「某个功能专属」，`lib/` 是「谁都能用」。

**命名规范**（非常规律）：
- 纯函数/工具/类型：`kebab-case.ts`，如 `legal-locator.ts`、`run-state.ts`、`trace-adapter.ts`、`report-adapter.ts`、`artifact-selection.ts`、`fallback-markdown.ts`。
- React Hook：`use` 前缀，如 `useTaskEvents.ts`、`use-report-ir.ts`。
- Context + Provider：`XxxContext.tsx` 或直接 `language.tsx`（内含 `LanguageProvider`）。
- 领域核心类型：`domain.ts`（`ModuleKey`、`TaskSpace`、`ModuleRun` 等全局领域模型）。
- 常量/注册表：`module-registry.ts`、`task-templates.ts`、`i18n.ts`、`trace-i18n.ts`。

**关键文件解析**：

| 文件 | 作用 | 命名含义 |
|---|---|---|
| `domain.ts` | 全局领域类型（`Jurisdiction`/`ModuleKey`/`TaskSpace`） | 领域模型，全局共享 |
| `module-registry.ts` | 模块标识映射（frontendKey ↔ jurisdiction ↔ templateId） | 注册表模式 |
| `app-store.tsx` | 全局应用状态（`AppStoreProvider` + `useAppStore`） | Store |
| `language.tsx` / `i18n.ts` | 语言上下文 / 中英文文案字典 | 国际化 |
| `run-state.ts` | 运行生命周期状态归一化（idle/running/success/failed） | 状态机辅助 |
| `trace-adapter.ts` | 后端事件 → 前端 TraceNode 的适配 | 适配器模式 |
| `report-adapter.ts` | 报告快照/trace 链接构建 | 适配器模式 |
| `workspace.ts` | 从 response 抽取报告指标/洞察 | 提取器 |
| `legal-locator.ts` | 法规定位符格式化 | 展示格式化 |
| `document-ir.ts` / `use-report-ir.ts` | 结构化报告 IR（段落/声明/列表块）类型 + 获取 hook | 报告中间表示 |
| `auth/` | `AuthContext.tsx`（认证上下文）+ `types.ts` | 认证状态 |

**`lib/` 与 `features/` 的区别（核心）**：
- `lib/` = **横切、跨功能通用**（谁都能 import）。
- `features/` = **纵向、某功能专属**（只有那个功能用它）。
- 判断口诀：如果两个不相关功能都要用它 → 放 `lib/`；如果只有某个功能用它 → 放 `features/<功能>/`。

**`lib/` 与 `api/` 的区别（核心）**：
- `api/` = **网络 I/O 边界**（只负责发请求、收响应、定义请求/响应类型）。
- `lib/` = **纯计算/纯类型/状态**（不碰网络）。
- 例如 `api/auth.ts` 负责「发登录请求」，`lib/auth/AuthContext.tsx` 负责「前端登录状态管理」。

---

### 1.5 `api/` —— 网络请求边界（「后端的镜像」）

**职责**：与后端 HTTP 接口**一一对应**的请求封装。**只做「发请求 + 收响应 + 类型定义」，不做业务计算，不含 UI。**

**命名规范**：
- 文件名：按**后端资源**命名，`kebab-case.ts`，如 `auth.ts`、`modules.ts`、`reports.ts`、`artifacts.ts`、`citations.ts`、`knowledge.ts`、`events.ts`、`me.ts`、`copilot.ts`、`system-settings.ts`。
- 基础设施文件：`client.ts`（统一 `apiFetch`）、`api-contract.ts`（请求契约类型）、`generated/openapi.d.ts`（OpenAPI 生成的类型声明）。

**关键文件解析**：

| 文件 | 作用 |
|---|---|
| `client.ts` | **唯一**的 `apiFetch` 封装（超时/错误类型 `HttpStatusError`/`HttpTimeoutError`） |
| `api-contract.ts` | 把 `ModuleKey` ↔ 提交端点映射，类型从 OpenAPI 推导 |
| `generated/openapi.d.ts` | 由后端 OpenAPI 规范自动生成的类型声明（`.d.ts` = 纯声明，无实现） |
| `auth.ts` | 登录/登出/token 管理 + 本地存储 token |
| `modules.ts` | 模块列表/健康检查 |
| `artifacts.ts` / `reports.ts` / `citations.ts` / `knowledge.ts` / `events.ts` / `me.ts` / `copilot.ts` / `system-settings.ts` | 各资源域请求 |

**为什么 `api/` 要独立**：项目有一条**架构约束**（`api-boundary.test.ts` 强制校验）——后端 URL 只能出现在 `api/` 目录内，其它目录禁止直接 `fetch`。这样所有网络调用收敛到一处，方便统一加鉴权头、错误处理、请求合并（`request-coalescing.ts`）。

---

### 1.6 `styles/` —— 样式（「设计令牌 + 应用样式」）

**职责**：全局 CSS。分层为「设计令牌（tokens）」与「应用样式（app）」。

**命名规范**：
- `tokens.css`：Tailwind 入口 + 设计令牌（字体、主题变量）。
- `app.css`：应用样式的**总入口**，用 `@import` 汇总 `app/` 下各分区。
- `app/*.css`：按**区域/页面**拆分的样式，`kebab-case.css`。

```
styles/
├── tokens.css            # 设计令牌 + Tailwind 指令
├── app.css               # 入口（@import 汇总下面所有 app/ 分区）
└── app/
    ├── base.css          # 基础组件（导航、弹窗、工具栏）
    ├── landing.css       # 落地页
    ├── pages.css         # 通用页面外壳
    ├── workspace.css     # 工作台
    ├── report.css        # 结构化报告文档视图
    └── product-pages-and-overrides.css  # 产品页 + 覆盖样式
```

---

## 2. 文件命名后缀规范（速查）

| 后缀 | 含义 | 例子 |
|---|---|---|
| `.ts` | TypeScript，**不含 JSX**（纯逻辑/类型/hook） | `lib/run-state.ts`、`features/.../config.ts` |
| `.tsx` | TypeScript + JSX（React 组件） | `pages/HomePage.tsx`、`components/common/PdfViewer.tsx` |
| `.test.ts` / `.test.tsx` | Vitest 单测，**与被测文件同名并排** | `lib/run-state.ts` ↔ `lib/run-state.test.ts` |
| `.d.ts` | 纯类型声明（无实现，多为生成产物） | `api/generated/openapi.d.ts` |
| `.css` | 样式表 | `styles/app/workspace.css` |

**命名大小写规则**：
- **组件文件**（含 JSX）：`PascalCase.tsx`（`PdfViewer`、`WorkspaceShell`）。
- **纯逻辑/类型/hook 文件**：`kebab-case.ts`（`run-state`、`legal-locator`、`use-task-events`）。
- **特殊固定名**：`index.ts`（目录出口）、`types.ts`（类型集合）、`config.ts`（配置）、`contracts.ts`（契约类型）。

> 为什么组件用 PascalCase、工具用 kebab-case？因为 React 组件是「可实例化的类（组件即类）」，类名首字母大写是 JSX 语法的硬性要求（`<PdfViewer />` 首字母大写才会被当组件）；而普通函数/模块是「值」，惯例用小写连字符。

---

## 3. 「新写一个文件该放哪」决策表

| 我写的是… | 放哪 | 命名 |
|---|---|---|
| 一个独占路由的整屏页面 | `pages/` | `XxxPage.tsx`（PascalCase + Page） |
| 一个可复用的展示组件（按钮/面板/渲染器） | `components/<域>/` | `PascalCase.tsx` |
| 一个通用基础组件（弹窗壳/导航/PDF 查看） | `components/common/` | `PascalCase.tsx` |
| 某个功能专属的纯逻辑/类型/payload 构建 | `features/<功能>/` | `kebab-case.ts` / `types.ts` |
| 跨功能通用的纯函数/类型/hook | `lib/` | `kebab-case.ts` / `useXxx.ts` |
| 全局状态/Context/Provider | `lib/` | `XxxContext.tsx` / `app-store.tsx` |
| 调后端某个接口的封装 | `api/` | `资源名.ts`（kebab-case） |
| 全局 CSS | `styles/` | `tokens.css` / `app/*.css` |
| 某文件的单测 | 与被测文件同目录并排 | 同名 + `.test.ts(x)` |

---

## 4. 目录全景（速览）

```
frontend/src/
├── main.tsx                 # 入口：挂载 React，按 URL 参数决定渲染 App 或 TraceProbe
├── App.tsx                  # 应用根组件：路由装配 + 全局 Provider + 顶层布局
├── TraceProbe.tsx           # Trace 调试探针（?trace_probe=1 时独立渲染，用于 trace 可视化调试）
├── api/                     # 网络请求边界（后端镜像）
│   ├── client.ts            #   唯一 apiFetch 封装
│   ├── api-contract.ts      #   模块↔端点契约
│   ├── generated/openapi.d.ts # OpenAPI 生成类型
│   └── *.ts                 #   各资源域请求封装
├── components/              # 可复用 UI 组件（按用途分子目录）
│   ├── common/ auth/ citation/ workspace/ report/ report-center/ landing/ modals/ onboarding/
├── features/                # 功能业务逻辑（纯 .ts，无 UI）
│   ├── module-runner/       #   合规模块运行：表单模型 + payload 构建
│   └── resource-explorer/   #   资源浏览器：输入/输出资源归类
├── lib/                     # 通用工具与全局状态
│   ├── domain.ts            #   全局领域类型
│   ├── app-store.tsx        #   全局状态 Store
│   ├── language.tsx / i18n.ts # 国际化
│   ├── *.ts                 #   纯函数/hook/适配器
│   └── auth/                #   认证上下文 + 类型
├── pages/                   # 路由级页面
│   ├── *.tsx                #   XxxPage.tsx
│   └── auth/                #   LoginPage / RegisterPage
└── styles/                  # 样式
    ├── tokens.css           #   设计令牌
    ├── app.css              #   入口
    └── app/*.css            #   分区样式
```

---

## 5. 三个最易混淆的「区别」总结

1. **`components/` vs `features/`**：前者是「怎么画」（含 JSX），后者是「怎么算」（纯 `.ts`）。
2. **`lib/` vs `features/`**：前者是「跨功能通用横切」，后者是「某功能专属纵向」。
3. **`lib/` vs `api/`**：前者是「纯计算/状态」，后者是「网络 I/O 边界」。

> 一句记忆法：**`pages` 是壳，`components` 是零件，`features` 是脑，`lib` 是工具箱，`api` 是电线，`styles` 是油漆。**
