# DataComplyFlow Schema 契约防漂移实施方案

> 文档性质：实施中技术方案（PR 1A/1B 已完成本地实现，后续阶段待实施）
> 编制日期：2026-08-06
> 方案版本：v2.1（PR 1A/1B 实施回填版）
> 适用分支：`new`
> 当前基线：26 个开发案例真实 HTTP 已修复至 26/26；本方案用于防止再次漂移
> 关联报告：`status/DataComplyFlow_Schema契约修复与复验_20260806.md`

---

## 一、目标与验收口径

### 1.1 要解决的问题

当前请求契约分别维护在：

1. 后端 FastAPI/Pydantic Schema；
2. `frontend/src/lib/dev-test-cases.ts` 的直接 payload；
3. `formDefaults` 经 `ModuleRunPanel` 内 Builder 生成的浏览器 payload；
4. `backend/tests/*/cases/` 的 CLI harness JSON。

后端 Schema 变化不会自动触发前端案例失败，通常要等到人工 POST 或点击“一键体验”才出现 422、400 或客户端前置校验错误。

### 1.2 最终验收标准

| 门禁 | 验收标准 | 失败时应阻止合入 |
|---|---|---|
| OpenAPI 类型门禁 | 后端字段、枚举、必填项变化后，前端旧类型不能继续编译 | 是 |
| 26 案例 HTTP 门禁 | 26/26 请求被真实 FastAPI 路由接受 | 是 |
| 契约执行隔离 | HTTP 门禁不得启动完整报告生成、LLM、RAG 或得理任务 | 是 |
| Builder 单元测试 | 11 个模块的表单 Builder 均有确定性测试 | 是 |
| Review 文件工作流 | 测试必须先上传文件，再提交 storage path | 是 |
| 浏览器关键路径 | 11 个模块可填充、提交并显示结果 | 发布前/定时门禁 |

### 1.3 不作为本方案验收依据的结果

- CLI harness 15/15：它不经过 FastAPI HTTP/Pydantic 路由。
- `npm run build`：没有 OpenAPI 类型约束时，合法 TypeScript 不代表请求符合后端 Schema。
- HTTP 200 但异步任务最终失败：P0 契约门禁只负责输入契约，完整生成由后端业务测试和浏览器 E2E 负责。
- `--no-llm` 结果：不能证明真实 LLM、Token、RAG 或得理 API 正常。

---

## 二、总体实施顺序

```text
PR 1A：测试专用 Contract App + Recording Executor
  ↓ 真实 HTTP 校验不触发完整后台生成
PR 1B：26 案例 HTTP 门禁 + GitHub Actions
  ↓ 已能阻止旧 payload 合入
PR 2：FastAPI OpenAPI → TypeScript 类型
  ↓ 字段、枚举、必填项可在编译期发现
PR 3A：EU 四模块纯 Builder
PR 3B：Review/CN Flow/US 14117 纯 Builder
PR 3C：其余四模块纯 Builder
  ↓ 消除 formDefaults 与浏览器 payload 的独立拼装
PR 4：浏览器 E2E 与发布门禁
  ↓ 覆盖上传、交互、异步轮询和结果展示
```

不得先大规模重构 `ModuleRunPanel.tsx` 再补门禁。先完成 PR 1A/1B，保证后续每个 Builder 批次都有真实 HTTP 回归保护。

---

## 三、PR 1A/1B：隔离执行的真实 HTTP 契约门禁（P0）

### 3.1 目标与边界

CI 启动测试专用 Contract App。Vitest 直接导入现有 `DEV_TEST_CASES`，逐条提交 26 个案例，不创建另一份案例 JSON。

Contract App 必须执行：

- 真实 HTTP 请求解析；
- 真实 Bearer 鉴权；
- 真实 FastAPI 路由匹配；
- 真实 Pydantic request/response 校验；
- Review 的真实文件上传、路径解析和文本提取前置条件。

Contract App 不得执行：

- 完整报告生成；
- LLM、RAG、得理 API 或其他外部 HTTP；
- 规则引擎和渲染器的长耗时链路；
- 写入正式 `outputs/`、`storage/` 或开发数据库。

### 3.2 拟新增或修改文件

| 文件 | 动作 |
|---|---|
| `backend/tests/contract_support.py` | 已新增 Recording Executor、dispatcher patch manifest 和 localhost-only 网络守卫 |
| `backend/tests/contract_app.py` | 已新增测试专用 ASGI App，安装执行隔离和外部访问阻断 |
| `backend/tests/test_contract_support.py` | 已新增执行器、恢复逻辑和网络守卫单元测试 |
| `backend/tests/test_contract_app.py` | 已验证真实异步请求被接受且仅记录提交、不运行 callable |
| `.github/workflows/dev-case-contract.yml` | 已新增 GitHub Actions Workflow |
| `frontend/tests/contract/dev-test-cases.api.test.ts` | 已新增真实 HTTP 集成测试 |
| `frontend/tests/contract/dev-case-api-runner.ts` | 已新增鉴权、上传、提交和响应断言辅助函数 |
| `frontend/package.json` | 新增 `test:dev-cases:api` 命令 |
| `frontend/src/lib/dev-test-cases.test.ts` | 已增加案例数量和关键 Schema 字段门禁 |
| `frontend/tests/contract/dev-case-fixtures.test.ts` | 已增加依赖文件存在性和 Git 跟踪门禁，避免 Node-only 依赖进入生产源码树 |

### 3.3 Contract App 执行隔离设计

当前 BCR、DPIA、TIA、Assessment 等模块的 `submit_async()` 会立即调用 `InMemoryTaskManager._executor.submit()`。因此不能直接用生产 App 提交 26 个案例后立即杀进程。

测试专用执行器定义：

```python
class RecordingExecutor:
    def __init__(self) -> None:
        self.submissions: list[tuple[Callable, tuple, dict]] = []

    def submit(self, func, *args, **kwargs):
        self.submissions.append((func, args, kwargs))
        future = Future()
        future.set_result(None)
        return future
```

Contract App 启动时执行以下替换：

1. 将各模块全局 service 的 `tasks._executor` 替换为 `RecordingExecutor`；
2. 将 `app.state.container.review_service.task_dispatcher` 替换为 `RecordingTaskDispatcher`；
3. 由 `backend.app.create_app(Settings(...))` 创建与生产相同路由的 App，再安装测试替换；
4. 使用临时 SQLite、临时 storage 和临时 report 目录；
5. 将 Contract App 进程工作目录切换到临时目录，使硬编码相对 `outputs/...` 也不会污染仓库；
6. 清空所有 Provider/得理凭据；
7. 安装 outbound HTTP guard，非 localhost 请求立即失败；
8. Diagnosis 保留本地确定性执行，因为其报告端点没有异步 accepted 路径。

需要替换的当前 service manager 目标是：

| 模块 | 当前目标 |
|---|---|
| Assessment | `backend.domains.cn.security_assessment.router.service.tasks._executor` |
| PIPIA | `backend.domains.cn.pipia.router.service.tasks._executor` |
| EU SCC | `backend.domains.eu.scc_review.router.service.tasks._executor` |
| BCR | `backend.domains.eu.bcr_review.router.service.tasks._executor` |
| DPIA | `backend.domains.eu.dpia.router.service.tasks._executor` |
| TIA | `backend.domains.eu.tia.router.service.tasks._executor` |
| CN Flow | `backend.domains.us.eo14117_flow_review.router.service.tasks._executor` |
| US 14117 | `backend.domains.us.eo14117.router.service.tasks._executor` |
| CPRA | `backend.domains.us.cpra.router.service.tasks._executor` |

这 9 个目标必须在 `contract_app.py` 中集中维护并由测试覆盖；以后新增异步模块时，模块注册测试必须要求它加入 Contract App patch manifest。

Recording Executor 只允许存在于 `backend/tests/`，不得增加生产环境变量分支或修改生产执行语义。

必须有自测试证明：提交异步请求后返回合法 `task_id/state`，同时被记录的 runner 调用次数为 0。

### 3.4 模块执行策略

| 模块 | 案例数 | HTTP 策略 | 成功判定 |
|---|---:|---|---|
| Diagnosis | 3 | POST `/api/v1/diagnosis/report` | 2xx，响应包含 `result` |
| Assessment | 2 | POST `/api/v1/assessment/generate_async` | 2xx，包含 `task_id/state` |
| PIPIA | 2 | POST `/api/v1/pipia/generate_async` | 同上 |
| EU SCC | 3 | POST `/api/v1/eu_scc/generate_async` | 同上 |
| BCR | 3 | POST `/api/v1/bcr/generate_async` | 同上 |
| DPIA | 2 | POST `/api/v1/dpia/generate_async` | 同上 |
| TIA | 2 | POST `/api/v1/tia/generate_async` | 同上 |
| US 14117 | 2 | POST `/api/v1/us_14117/generate_async` | 同上 |
| CN Flow | 2 | POST `/api/v1/cn-flow/generate_async` | 同上 |
| CPRA | 3 | POST `/api/v1/cpra/generate_async` | 同上 |
| Review | 2 | 先 `/api/v0/files/upload`，再 `/api/v1/review/generate_async` | 上传与提交均 2xx |
| **合计** | **26** | - | **26/26** |

Review 不允许继续使用“只有元数据的单次 JSON POST”。测试流程必须是：

```text
读取案例 backendFilePaths
  → multipart/form-data 上传真实文件
  → 取得 data.path
  → 克隆案例 payload，并替换 uploaded_files
  → POST review/generate_async
```

### 3.5 API 测试核心结构

```ts
for (const [moduleKey, cases] of Object.entries(DEV_TEST_CASES)) {
  const definition = findModule(moduleKey as ModuleKey);
  const strategy = strategyFor(moduleKey);

  for (const testCase of cases) {
    const result = await strategy.submit(definition, testCase, authToken);
    expect(result.status, formatFailure(moduleKey, testCase, result)).toBeGreaterThanOrEqual(200);
    expect(result.status, formatFailure(moduleKey, testCase, result)).toBeLessThan(300);
  }
}
```

失败信息必须包含：

- module key；
- 测试案例名称；
- 请求 endpoint；
- HTTP status；
- FastAPI `detail`；
- 422 时的字段定位 `loc`、错误类型 `type` 和输入摘要。

### 3.6 CI 环境

CI 不读取开发者本地 Provider，不调用真实外部模型：

```yaml
env:
  AI4LAW_APP_ENV: test
  AI4LAW_LLM_PROVIDER: none
  AI4LAW_LLM_API_KEY: ""
  AI4LAW_SILICONFLOW_API_KEY: ""
  AI4LAW_TENCENT_API_KEY: ""
  AI4LAW_DELILEGAL_APP_ID: ""
  AI4LAW_DELILEGAL_SECRET: ""
  AI4LAW_RAG_AUTO_BUILD_INDEX: "false"
  AI4LAW_DATABASE_URL: sqlite:///${{ runner.temp }}/dev-case-contract.db
  AI4LAW_STORAGE_DIR: ${{ runner.temp }}/storage
  AI4LAW_TASK_MODE: threaded
  NO_PROXY: 127.0.0.1,localhost
```

Workflow 固定执行：

```text
actions/checkout
  → setup-python 3.11
  → setup-node 22
  → 安装 uv
  → uv sync --frozen
  → npm ci --prefix frontend
  → 启动 uvicorn backend.tests.contract_app:app，日志写入 runner.temp
  → 轮询 /__contract__/state，最长 30 秒
  → 在同一 shell step 中安装 EXIT trap，确保终止 Uvicorn
  → npm --prefix frontend run test:dev-cases:api
  → always 上传 backend log
```

Workflow 必须设置 `timeout-minutes`，且同一分支新提交应通过 `concurrency.cancel-in-progress` 取消旧运行。

### 3.7 PR 1A/1B TODO

- [x] 新建 `RecordingExecutor` 和 `RecordingTaskDispatcher`。
- [x] 新建测试专用 Contract App。
- [x] 验证异步请求被接受但 runner 执行次数为 0。
- [x] 验证 Contract App 拒绝非 localhost outbound HTTP。
- [x] 新建真实 HTTP 测试 Runner。
- [x] 测试启动时注册随机测试用户并复用 Bearer Token。
- [x] 为 Review 实现 upload-first 策略。
- [x] 断言案例总数严格等于 26。
- [x] 断言 `backendFilePaths` 指向的文件存在。
- [x] 在 CI/repository hygiene 检查中断言案例文件已被 Git index 跟踪。
- [x] 新建 GitHub Actions Workflow。
- [x] 保留后端日志并在失败时上传。
- [ ] 在 GitHub 分支保护中将 `dev-case-contract` 设置为必需检查。

### 3.8 PR 1A/1B 验收

- [x] 本地命令 26/26 通过。
- [ ] GitHub Actions checkout 后 26/26 通过。
- [x] 26 个案例运行期间没有任何完整报告后台任务。
- [x] 26 个案例运行期间没有任何非 localhost HTTP 请求。
- [x] 工作区正式 `outputs/` 和 `storage/` 不产生新文件。
- [x] 将 `country_region` 改回 `country` 的负向契约测试返回 422。
- [x] 删除 PIPIA `company_uscc` 的负向契约测试返回 422。
- [x] 移除 Review 文件上传的负向契约测试返回 400。
- [x] 无任何真实 LLM/得理 API 请求。
- [ ] PR 门禁耗时目标小于 3 分钟。

### 3.9 PR 1A/1B 实施记录

| 日期 | 提交 | 内容 | 本地证据 |
|---|---|---|---|
| 2026-08-06 | `72937ea` | Recording Executor、dispatcher patch manifest、网络守卫及单元测试 | `backend/tests/test_contract_support.py` 通过 |
| 2026-08-06 | `1055ace` | 隔离 Contract App 及真实异步请求测试 | Contract App 测试通过，提交被记录但 callable 未执行 |
| 2026-08-06 | `8e71f60` | 26 个案例与当前 Schema 对齐，补 Review 可信样例路径 | 前端案例测试 13/13、Review 后端测试 8/8 |
| 2026-08-06 | `2e4a44e` | HTTP Runner、随机用户鉴权、Review upload-first | 26/26 HTTP 2xx；9 个 manager、23 次异步提交 |
| 2026-08-06 | `8d5ec64` | `new` 分支 GitHub Actions 契约门禁 | YAML 本地解析通过，待远端首次运行 |
| 2026-08-06 | `f9ccdfe` | 案例依赖文件存在性和 Git index 门禁 | 前端案例测试 14/14 |
| 2026-08-06 | `6c7333c` | 将 Node-only 卫生测试移出生产源码树；增加三类负向契约与可重复运行计数 | 26/26 正例、422/422/400 负例、前端构建均通过 |

当前唯一需要仓库管理员操作的 P0 项是：Workflow 首次远端通过后，在 GitHub 分支保护中把检查名 `Validate 26 developer cases` 设置为 `new` 分支必需检查。远端运行和分支保护未完成前，不得将 PR 1B 标记为全流程闭环。

---

## 四、PR 2：OpenAPI 自动生成 TypeScript 类型（P1）

### 4.1 目标

FastAPI OpenAPI 成为前端请求字段、枚举和必填项的类型来源。后端 Schema 一旦变化，前端案例或 Builder 未同步时在编译阶段失败。

### 4.2 拟新增或修改文件

| 文件 | 动作 |
|---|---|
| `scripts/export_openapi.py` | 使用隔离 Settings 导出 `app.openapi()` |
| `frontend/src/api/generated/openapi.d.ts` | 提交生成的 OpenAPI TypeScript 类型 |
| `frontend/src/api/api-contract.ts` | 定义 endpoint → request body 类型工具 |
| `frontend/package.json` | 增加 `openapi-typescript` 和生成命令 |
| `frontend/src/lib/dev-test-cases.ts` | 将案例 payload 改为模块级强类型 |
| `.github/workflows/dev-case-contract.yml` | 增加生成结果一致性检查 |

### 4.3 类型映射

```ts
type ModuleRequestMap = {
  diagnosis: PostJsonBody<"/api/v1/diagnosis/report">;
  assessment: PostJsonBody<"/api/v1/assessment/generate_async">;
  review: PostJsonBody<"/api/v1/review/generate_async">;
  pipia: PostJsonBody<"/api/v1/pipia/generate_async">;
  bcr: PostJsonBody<"/api/v1/bcr/generate_async">;
  dpia: PostJsonBody<"/api/v1/dpia/generate_async">;
  tia: PostJsonBody<"/api/v1/tia/generate_async">;
  cn_flow: PostJsonBody<"/api/v1/cn-flow/generate_async">;
  us_14117: PostJsonBody<"/api/v1/us_14117/generate_async">;
  eu_scc: PostJsonBody<"/api/v1/eu_scc/generate_async">;
  cpra: PostJsonBody<"/api/v1/cpra/generate_async">;
};
```

`DevTestCase` 改为泛型，禁止再用无约束 `Record<string, unknown>` 作为正式 payload 类型。案例本身不重复保存 module key，由外层 `defineDevCases()` 推导：

```ts
type DevTestCase<M extends DevCaseModule> = {
  name: string;
  formDefaults: FormValuesByModule[M];
  payload: ModuleRequestMap[M];
  backendFilePaths?: string[];
};

const tiaCases = defineDevCases("tia", [
  /* DevTestCase<"tia">[] */
]);
```

禁止同时在 `DEV_TEST_CASES.tia` 和单个案例的 `module: "tia"` 中维护同一信息。

### 4.4 生成漂移门禁

CI 必须重新生成类型并检查工作树：

```bash
uv run --frozen python scripts/export_openapi.py --output /tmp/openapi.json
npm exec --prefix frontend -- openapi-typescript /tmp/openapi.json -o frontend/src/api/generated/openapi.d.ts
git diff --exit-code -- frontend/src/api/generated/openapi.d.ts
```

### 4.5 PR 2 TODO

- [ ] 增加确定性 OpenAPI 导出脚本。
- [ ] 导出时显式关闭 API Key 和外部 Provider。
- [ ] 增加 `openapi-typescript` 开发依赖。
- [ ] 生成并提交 `openapi.d.ts`。
- [ ] 建立 `ModuleRequestMap`。
- [ ] 建立 `defineDevCases(moduleKey, cases)` 类型辅助函数，不在案例内重复 module key。
- [ ] 将 26 个案例逐模块改为强类型。
- [ ] 将 `api/modules.ts` 的 endpoint 映射与类型映射做一致性测试。
- [ ] CI 增加 generated diff 门禁。

### 4.6 PR 2 验收

- [ ] 修改 Pydantic 枚举后，不更新前端案例，`npm run build` 必须失败。
- [ ] 新增后端必填字段后，不更新 Builder，TypeScript 必须失败。
- [ ] OpenAPI 重复生成字节一致。
- [ ] 不在运行时引入 OpenAPI 解析开销。

---

## 五、PR 3A/3B/3C：分批抽离纯函数 Builder（P1）

### 5.1 目标

将 `ModuleRunPanel.tsx` 中 11 套请求拼装逻辑分三个堆叠 PR 移到纯函数。React 组件只管理表单状态、文件上传和运行状态，不再定义后端请求结构。

三个 PR 必须可以分别评审、测试和回滚。不得用一个总 PR 同时迁移 11 个模块。

### 5.2 目录设计

```text
frontend/src/features/module-runner/payload-builders/
├── common.ts
├── cn.ts
├── eu.ts
├── us.ts
├── index.ts
└── payload-builders.test.ts
```

不按 11 个模块创建 11 个小文件，避免目录碎片化；按法域分为 3 个实现文件。

### 5.3 纯函数边界

正确边界：

```ts
buildTiaPayload(
  values: TiaFormValues,
  resolvedFilePaths: string[],
): ModuleRequestMap["tia"]
```

Builder 内禁止：

- 读取 React state；
- 调用 `setState`；
- 访问 DOM；
- 调用上传 API；
- 读取 `localStorage`；
- 依赖 `DEV_ACCEL_ENABLED`；
- 发起 HTTP 请求。

`ModuleRunPanel` 保留的职责：

```text
File[]
  → uploadTaskFile()
  → resolvedFilePaths[]
  → buildXxxPayload(values, resolvedFilePaths)
  → runModule()
```

### 5.4 测试案例复用方式

普通案例不再同时手写 `formDefaults` 和最终 payload：

```ts
const formDefaults = { /* 唯一场景输入 */ };

defineDevCases("tia", [{
  name: "TIA-1",
  formDefaults,
  backendFilePaths,
  payload: buildTiaPayload(formDefaults, backendFilePaths),
}]);
```

存在特定原始合同文本的 EU SCC 案例，不在最终 payload 上做无类型深合并。应在 Builder 输入中增加显式字段，例如 `sccTextOverride`，并保持其类型可见。

### 5.5 迁移顺序

| PR | 模块 | 原因 | 合入前置 |
|---|---|---|---|
| PR 3A | EU SCC、BCR、DPIA、TIA | 曾出现 Builder 与 Schema 漂移，优先处理 | PR 1A/1B、PR 2 |
| PR 3B | Review、CN Flow、US 14117 | 包含文件或嵌套对象，风险次高 | PR 3A |
| PR 3C | Diagnosis、Assessment、PIPIA、CPRA | 已稳定，但仍需统一 | PR 3B |

每迁移一批都必须运行：

```bash
npm --prefix frontend test -- --run
npm --prefix frontend run build
npm --prefix frontend run test:dev-cases:api
```

每个 PR 只允许修改本批模块、共享辅助函数和对应测试。共享辅助函数若会引起后续大范围机械变更，应在 PR 3A 中先固定接口。

### 5.6 PR 3A/3B/3C TODO

- [ ] 创建纯函数 Builder 目录和公共辅助函数。
- [ ] PR 3A：迁移 EU 四模块并补测试，独立评审和合入。
- [ ] PR 3B：迁移 Review、CN Flow、US 14117 并补测试，独立评审和合入。
- [ ] PR 3C：迁移剩余四模块并补测试，独立评审和合入。
- [ ] 将 Builder 返回类型绑定到 `ModuleRequestMap`。
- [ ] 从 `ModuleRunPanel.tsx` 删除请求对象拼装逻辑。
- [ ] 让开发案例通过 Builder 生成 payload。
- [ ] 对特殊 raw text 场景使用显式 typed override。

### 5.7 每个 Builder PR 的验收

- [ ] 本批 Builder 都能在无 React/DOM 环境下执行。
- [ ] 本批 Builder 均有正常、缺字段、非法枚举测试；涉及文件的 Builder 另加非法扩展名测试。
- [ ] 26 个案例仍为 26/26 HTTP PASS。
- [ ] 本批浏览器测试案例与直接 POST 不再生成不同请求结构。
- [ ] `ModuleRunPanel.tsx` 不再包含本批模块的 `buildXxxPayloadFrom()` 实现。
- [ ] 变更规模保持可审查；超出约 300-500 行实质逻辑时继续拆分。

---

## 六、PR 4：浏览器 E2E 与发布门禁（P2）

### 6.1 目标

覆盖纯 HTTP 门禁无法证明的 UI 行为：测试案例选择、表单回填、文件上传、异步轮询、结果列表和错误展示。

### 6.2 测试范围

每个模块至少一个主路径案例：

```text
登录
  → 创建对应模块项目
  → 记录运行前结果 ID 集合与结果数
  → 选择测试案例/点击一键体验
  → 提交
  → 捕获本次请求返回的新 task_id/run_id
  → 轮询该 task_id，等待其达到 COMPLETED
  → 断言结果数相对运行前增加
  → 断言新增结果明确关联本次 task_id/run_id
  → 断言本次提交、轮询、结果请求均为 2xx
  → 断言本次任务没有 FAILED/error，而非仅检查页面无错误文案
```

禁止仅使用“页面生成结果数 > 0”作为成功条件。历史项目已有结果时，该断言会把本次失败误判为通过。

每个案例使用独立的新用户或独立项目空间；测试结束后只清理本轮创建的数据，不复用人工测试项目。

### 6.3 运行频率

| 测试 | 频率 | 原因 |
|---|---|---|
| 26 案例 HTTP | 每个 PR | 快速、稳定、直接阻止契约漂移 |
| 11 模块浏览器主路径 | 每晚、发布前 | 较慢，覆盖 UI 与生成链 |
| 真实 LLM/得理 API | 手工或预算受控定时任务 | 有成本和外部不稳定性 |

### 6.4 PR 4 TODO

- [ ] 增加浏览器测试运行配置。
- [ ] 建立 11 模块参数化主路径。
- [ ] 每次运行捕获并断言本次 `task_id/run_id`。
- [ ] 断言结果增量及结果与本次运行的关联关系。
- [ ] 失败时保存截图、页面文本、网络错误和后端日志。
- [ ] 将截图作为 CI artifact 上传。
- [ ] 发布流程要求最近一次 11/11 浏览器验证通过。

---

## 七、完整门禁矩阵

| 层级 | 输入 | 校验内容 | 不负责校验 |
|---|---|---|---|
| TypeScript/OpenAPI | Builder 与直接 payload | 字段、类型、枚举、必填项 | 文件存在、Pydantic 自定义 validator |
| Vitest 契约单测 | 26 个案例定义 | 数量、关键字段、文件扩展名、路径存在 | FastAPI 路由行为 |
| 真实 HTTP CI | 26 个案例 | 鉴权、Pydantic、路由、文件前置条件 | 全部异步任务最终质量 |
| Pytest | 后端服务和 API | 规则、RAG、渲染、异步状态、权限 | 浏览器表单行为 |
| 浏览器 E2E | 11 个主路径 | UI、上传、Builder、提交、轮询、结果展示 | 外部 Provider 长期稳定性 |
| 受控外部测试 | 真实 Provider | LLM、Token、得理 API | 普通 PR 快速回归 |

---

## 八、风险与处置

| 风险 | 影响 | 处置 |
|---|---|---|
| CI 继承 `.env` 或真实 API Key | 产生费用或不稳定请求 | Contract App 显式设置 LLM/得理为空、RAG 不建索引，并安装非 localhost outbound guard |
| Contract App 误执行后台任务 | CI 资源浪费、输出污染、结果不确定 | `RecordingExecutor` 自测试；runner 调用次数必须为 0；工作目录切到临时目录 |
| Review fixture 不存在 | 本地通过、CI 失败 | 增加路径存在和 Git index 跟踪门禁 |
| OpenAPI 生成不确定 | generated diff 每次变化 | JSON key 排序，隔离 Settings，固定工具版本 |
| Builder 迁移 PR 过大 | Review 困难、回归面过大 | PR 3A/3B/3C 分批堆叠，每批独立跑全量门禁 |
| 生成类型过宽 | 编译通过但 Pydantic validator 仍拒绝 | 保留真实 HTTP 门禁，不用类型门禁替代运行验证 |
| 特殊案例语义被 Builder 简化 | 案例仍通过但失去业务测试价值 | 使用 typed override，保留案例预期断言 |
| E2E 复用历史结果 | 失败被旧结果掩盖 | 每次创建独立项目，按本次 task/run 做结果关联断言 |

---

## 九、工作量与提交边界

| PR | 预计工作量 | 建议提交数 | 可独立回滚 |
|---|---:|---:|---|
| PR 1A：Contract App + Recording Executor | 0.5-1 天 | 2-3 | 是 |
| PR 1B：26 案例 HTTP + Workflow | 0.5-1 天 | 2-3 | 是 |
| PR 2：OpenAPI 类型 | 0.5-1 天 | 2-3 | 是 |
| PR 3A：EU Builder | 0.5-1 天 | 1-2 | 是 |
| PR 3B：文件/嵌套对象 Builder | 0.5-1 天 | 1-2 | 是 |
| PR 3C：剩余 Builder | 0.5-1 天 | 1-2 | 是 |
| PR 4：浏览器 E2E | 1-2 天 | 2-3 | 是 |

不得在这些 PR 中同时重构后端业务 Schema、规则引擎或报告内容。契约基础设施和业务行为变更需要分开评审。

---

## 十、最终完成定义（Definition of Done）

- [ ] GitHub Actions 中存在必需检查 `Validate 26 developer cases`。
- [x] 26 个案例在面向 `new` 的 PR 和 push 中执行真实 HTTP 验证。
- [x] Contract App 经过真实路由但不执行任何完整后台 runner。
- [x] Contract App 不能调用 LLM、RAG 或得理 API。
- [x] Review 案例使用真实 upload-first 流程。
- [ ] 后端 OpenAPI 能确定性生成 TypeScript 类型。
- [ ] 26 个案例 payload 均受模块级 TypeScript 类型约束。
- [ ] 11 个 Builder 已从 React 组件抽离。
- [ ] 浏览器与直接案例复用同一 Builder 或显式 typed override。
- [ ] 11 模块浏览器主路径均按本次 task/run 关联结果通过。
- [ ] 任何 Schema 漂移都能在 PR 合入前由机器发现。
