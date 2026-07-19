# DataComplyFlow 前端 API 与数据流开发规范

## 1. 目的

本规范用于保证前端请求位置可发现、数据流可追踪、接口变更可验证。它补充通用开发规范，不改变后端 URL、请求响应模型或业务行为。

## 2. 目录职责

```text
frontend/src/
├── api/          # HTTP 传输、接口 URL、请求与响应解析
├── components/   # UI 组件，不直接调用 fetch
├── pages/        # 路由页面，组合组件与业务动作
├── lib/          # 领域类型、状态、纯转换、国际化等非传输能力
└── integrations/ # 有明确边界的外部或生成式界面集成
```

`frontend/src/api/client.ts` 是唯一允许直接调用 `fetch()` 的文件。浏览器原生 `EventSource` 可以由任务事件模块使用，但对应 HTTP fallback 必须通过 `apiFetch()`。

## 3. 请求规则

1. 页面和组件不得直接拼接后端 URL 或调用 `fetch()`。
2. 每类资源在 `frontend/src/api/` 下建立语义明确的接口文件，例如 `artifacts.ts`、`knowledge.ts`、`modules.ts`。
3. 通用超时、AbortSignal 传播和底层网络调用由 `apiFetch()` 处理。
4. 鉴权头由现有认证服务提供，具体接口文件负责声明该请求是否需要鉴权。
5. 接口文件负责 HTTP 状态和响应解析；组件只处理业务成功、业务失败和展示状态。
6. 不在组件中复制 `/api/v0`、`/api/v1` 路径。
7. 模块身份以 `config/module_registry.json` 为权威源；模块动作端点由 `api/modules.ts` 管理，并由契约测试校验其前缀。

## 4. 标准数据流

```text
用户操作
→ Page / Component
→ API resource module
→ apiFetch
→ Vite /api proxy
→ FastAPI v0/v1 Router
→ Domain Service
→ Task / Trace / Report
→ API response、轮询或 SSE
→ Store / Adapter
→ UI
```

排查一次请求时，按上述顺序定位，不从文件名猜测调用关系。

## 5. 文件拆分标准

- UI 组件只负责交互和展示。
- Payload 构造与输入校验应放在对应 feature 或纯函数文件中。
- API 文件不包含 React 状态。
- Store 不直接拼 URL。
- Adapter 只做数据转换；如需请求，应将请求移到 `api/` 后再调用 Adapter。
- 不为了形式统一创建空的 `api.ts`、`service.ts` 或 `types.ts`。

## 6. 变更门禁

每次前端 API 调整至少执行：

```bash
cd frontend
npm test
npm run build
```

同时检查：

```text
HTTP method 不变
完整 URL 不变
请求和响应字段不变
鉴权头不变
超时和错误行为无非预期变化
组件中无新增 fetch 调用
```

## 7. 当前边界

本轮已建立统一 `api/` 目录和底层客户端。后续拆分 `ModuleRunPanel`、`WorkspaceShell` 与全局样式时，应分批处理并先补充模块 Payload、任务状态和文件操作测试，不与后端算法优化混在同一批次。

## 8. 模块运行器边界

模块运行器采用以下职责划分：

```text
features/module-runner/types.ts
  表单字段、表单值、步骤配置和运行状态类型

features/module-runner/model.ts
  步骤配置、默认值、校验、Payload 辅助和结果格式化

components/workspace/ModuleRunPanel.tsx
  React 状态、用户事件、运行编排和 JSX 展示

api/modules.ts
  HTTP 请求、上传、异步任务提交和状态轮询
```

新增模块字段时先判断其属于数据模型、界面状态还是传输协议，不得再次把三类职责集中写回 `ModuleRunPanel.tsx`。纯模型函数应优先补充单元测试；组件拆分不得与接口字段修改放在同一批次。
