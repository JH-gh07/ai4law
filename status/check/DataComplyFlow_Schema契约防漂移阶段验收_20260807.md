# DataComplyFlow Schema 契约防漂移阶段验收

> 验收日期：2026-08-07
> 适用分支：`new`
> 验收范围：仓库内 PR 2、PR 3、PR 4 实现
> 结论：仓库内防漂移链路已完成并通过本地复验；远端首跑、分支保护和发布流程强制依赖仍待完成

---

## 一、结论汇总

| 验收域 | 状态 | 证据 | 未覆盖边界 |
|---|---|---|---|
| OpenAPI 类型门禁 | 通过 | 确定性导出、generated diff、11 模块请求类型映射 | 远端 Workflow 首跑未在本地证明 |
| 26 案例单源生成 | 通过 | seed 禁止 payload；`defineDevCases()` 调用纯 Builder | 案例业务真实性不由本门禁判断 |
| 11 个纯 Builder | 通过 | 无 React/DOM 依赖；36 项 Builder 测试 | UI 业务完整性提示仍由组件负责 |
| 26 案例真实 HTTP | 通过 | 26/26 正例；422/422/400 负例 | 不运行后台报告生成 |
| Review upload-first | 通过 | 浏览器真实上传 200、提交 200 | 不验证最终审查内容质量 |
| 11 模块浏览器主路径 | 通过 | Chromium 11/11，52.5 秒 | 异步终态为确定性测试响应 |
| 远端合入治理 | 未完成 | Workflow 文件已提交 | 首跑、必需检查和发布门禁需管理员配置 |

一句话结论：字段与案例不再由三套手写 payload 独立维护，已形成“OpenAPI 类型 + 单源 Builder + 真实 HTTP + 浏览器契约 E2E”四层门禁，但远端强制执行尚未闭环。

---

## 二、实现证据

### 2.1 单源案例与 Builder

- `frontend/src/lib/dev-test-cases.ts:56`：案例 seed 使用 `payload?: never`，禁止手写最终 payload。
- `frontend/src/lib/dev-test-cases.ts:59`：`buildCasePayload()` 将 11 个模块统一路由到纯 Builder。
- `frontend/src/lib/dev-test-cases.ts:92`：`defineDevCases()` 生成强类型 payload。
- `frontend/src/api/api-contract.test.ts:39`：锁定旧枚举、旧字段名和缺少必填字段三类编译期漂移。
- `frontend/src/features/module-runner/payload-builders/eu.ts`：EU SCC、BCR、DPIA、TIA。
- `frontend/src/features/module-runner/payload-builders/cn.ts`：Diagnosis、Assessment、PIPIA、Review、CN Flow。
- `frontend/src/features/module-runner/payload-builders/us.ts`：US 14117、CPRA。
- `frontend/src/features/module-runner/payload-builders/payload-builders.test.ts`：正常路径、必填字段、枚举和适用的扩展名边界测试。

特殊场景没有对最终 payload 做无类型深合并：EU SCC 使用 `project_name_override` / `scc_text_override`，US 14117 使用有类型的嵌套数组 override。

### 2.2 浏览器链路

- `frontend/playwright.config.ts:5`：单 worker、隔离端口、独立临时 Contract 根目录。
- `frontend/playwright.config.ts:20`：失败保留 trace、截图和 video。
- `frontend/tests/e2e/module-main-paths.e2e.ts:16`：11 模块参数化场景清单。
- `frontend/tests/e2e/module-main-paths.e2e.ts:98`：真实 UI 注册、创建项目和进入工作区。
- `frontend/tests/e2e/module-main-paths.e2e.ts:114`：记录运行前结果数并选择真实开发案例。
- `frontend/tests/e2e/module-main-paths.e2e.ts:118`：Review 真实选择文件。
- `frontend/tests/e2e/module-main-paths.e2e.ts:123`：捕获本次提交和上传响应并断言 2xx。
- `frontend/tests/e2e/module-main-paths.e2e.ts:144`：提取本次 task_id，断言运行增量与关联关系。
- `frontend/tests/e2e/module-main-paths.e2e.ts:165`：新项目“生成结果”计数断言为 1。
- `.github/workflows/browser-e2e.yml:3`：每日与手工触发。
- `.github/workflows/browser-e2e.yml:48`：始终上传报告、失败证据和后端日志。

### 2.3 本地复验结果

| 命令/检查 | 结果 |
|---|---|
| `npm test -- --run` | 112 passed，2 skipped |
| Builder 专项 | 36/36 passed |
| `npm run build` | 通过；WorkspacePage 474.88 kB |
| `npm run test:dev-cases:api`（Contract App） | 2/2 测试通过，内部覆盖 26/26 正例与 3 类负例 |
| `npx playwright test` | 11/11 passed，52.5 秒 |
| Review 后端日志 | `/api/v0/files/upload` 200；`/api/v1/review/generate_async` 200 |
| Workflow YAML | Ruby 标准 YAML 解析通过 |
| OpenAPI 重生成 | `openapi.d.ts` 无差异 |
| `git diff --check` | 通过 |

Vitest 输出中的 `Error: chunk load failed` 来自 `LazyRouteErrorBoundary` 对故障页面的预期测试日志，不是失败；最终测试进程退出码为 0。

---

## 三、测试语义边界

浏览器测试的提交请求经过真实前端 Builder、Vite proxy、鉴权、FastAPI 路由和 Pydantic Schema。Review 还经过真实文件上传与 storage path 提交。

Contract App 为防止 CI 调用真实 Provider，按设计不执行后台 runner。异步状态接口在浏览器中返回确定性的 completed 响应，只验证：

1. 前端是否轮询本次 task_id；
2. 终态是否合并到本次运行；
3. 结果树是否产生一个新结果；
4. 提交、上传和状态请求是否为 2xx；
5. 本次运行是否无 error/FAILED。

本报告不据此声称真实 LLM、RAG、Token/Time、得理 API 或 Markdown 报告质量已通过。它们属于受控外部测试和报告质量门禁。

---

## 四、残余问题

| 优先级 | 未完成项 | 责任边界 | 完成标准 |
|---|---|---|---|
| P0 | 远端首次运行 `Validate 26 developer cases` | GitHub Actions | `new` 的实际 run 26/26 通过 |
| P0 | 将检查设为 `new` 必需检查 | 仓库管理员 | 分支保护拒绝绕过失败检查合入 |
| P1 | 发布流程依赖最近一次 Browser E2E | 发布管理员/Workflow | 发布任务显式依赖 11/11 成功结果 |
| P2 | 前端既有依赖漏洞 | 前端升级任务 | 在独立升级中处理 React Router；不使用 `audit fix --force` 混入本改动 |

`npm audit --omit=dev` 当前报告 2 个 moderate，来自既有 React Router 6.x 依赖链；Playwright 是开发依赖，不在该生产漏洞路径中。本阶段没有执行破坏性的主版本自动升级。

---

## 五、Git 存档

| 提交 | 内容 |
|---|---|
| `d64aaaf` ~ `887e8fd` | OpenAPI 导出、生成类型、请求映射和案例强类型 |
| `b346f9b` | EU 四模块 Builder |
| `a9469c8` | 文件/嵌套对象 Builder |
| `fec8805` | 剩余四模块 Builder |
| `4e4b2b3` | Builder 与 UI model 解耦 |
| `d4685b4` | 26 案例改为 Builder 生成 |
| `9e3d0cb` | 11 模块浏览器契约门禁 |
| `72889f4` | EU Builder 契约边界补强 |
| `fd1f5c4` | 三类历史 OpenAPI 漂移编译期哨兵 |

方案文档继续保留在 `status/todo/`，直到远端必需检查和发布流程依赖完成；本文件作为仓库内实现的阶段验收件进入 `status/check/`。
