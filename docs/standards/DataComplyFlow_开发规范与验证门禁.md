# DataComplyFlow 开发规范与验证门禁

本规范约束人工开发和 AI 辅助开发。目标是让代码正确、简洁、可发现、可测试和可追溯，不通过机械改名、无意义拆分或代码混淆制造表面差异。

## 1. 基本开发顺序

```text
先确认真实调用链
→ 复用现有公共能力
→ 做最小行为改动
→ 补充与风险相称的测试
→ 复扫路径和死引用
→ 更新唯一活动规范
```

禁止在同一批次混入目录清理、Bug 修复、Prompt 优化、算法实验和依赖升级。

## 2. 后端边界

```text
API Router
→ Application Service
→ Domain Rule / Workflow
→ RAG / LLM / External Integration
→ Verifier / Renderer / Trace
```

- `backend/main.py` 只暴露 ASGI 应用；`backend/app.py` 创建完整应用并装配 API 版本。
- `backend/api/v{n}/router.py` 是版本路由唯一聚合入口；模块 Router 不写 `/api/v0` 或 `/api/v1`。
- Router 负责协议转换、依赖和响应映射，不拼 Prompt、不实现法律规则、不直接管理业务文件。
- 确定性规则属于领域层；LLM 不得静默覆盖规则结论。
- 公共 LLM、RAG、Citation、Task、Trace 和 Renderer 优先复用 `backend/common/`。
- 第三方 API 放在 `backend/integrations/`，以适配器隔离外部响应和失败。
- `Agent` 只用于确有独立职责、输入输出和主流程影响的组件；普通单次模型调用使用 generator、extractor、reviewer 或 client 等具体名称。

重复路由按 `HTTP method + 完整 path` 判断。路由重构必须保持 URL、方法、Schema、依赖、状态码和 endpoint 行为，并验证 OpenAPI。

## 3. 前端边界与数据流

```text
用户操作
→ Page / Component
→ Feature Model
→ frontend/src/api/*
→ apiFetch
→ FastAPI
→ Store / Adapter
→ UI
```

- `pages/` 是路由入口；`components/` 是组成页面的交互与展示单元。
- 具体 URL、HTTP 状态和响应解析归 `frontend/src/api/`；只有 `api/client.ts` 直接调用 `fetch()`。
- Component 不直接拼 `/api/v0`、`/api/v1`，Store 不负责 HTTP，API 文件不保存 React 状态。
- Payload 构造、默认值和输入校验放在 Feature Model 或纯函数中。
- 模块运行器维持 `types.ts → model.ts → ModuleRunPanel.tsx → api/modules.ts` 的职责边界。
- 不为目录整齐创建空的 `api.ts`、`service.ts`、`types.ts` 或无消费者抽象。

## 4. Schema、规则、RAG 与 LLM

- API DTO、领域对象、数据库实体和渲染模型分离；主要业务契约不用语义不明的可变 `dict`。
- `unknown`、缺失、否定和 `not_applicable` 必须区分。
- 法律结论关联规则或依据标识；生成性结论关联 Evidence/Citation，或明确标识未支持。
- 规则表达条件、例外、法律效果、优先级、版本和缺失事实，命中轨迹可审计。
- RAG 原始来源和条款语料是源资产，`storage/rag` 是可重建索引；检索失败不得伪装成功。
- Prompt 声明模块、法域、版本、输入和输出 Schema，不散落在 Router 中。
- 模型、温度、超时和重试来自运行配置；凭据不得写入代码、配置样例或前端。
- fallback 必须记录触发原因、所用策略和结果。

## 5. 命名规则

- Python 包、变量、函数和 JSON 字段：`snake_case`。
- Python/TypeScript 类与类型：`PascalCase`。
- 常量：`UPPER_SNAKE_CASE`。
- API 资源路径：小写 `kebab-case`；已发布兼容路径不为统一外观原地改名。
- 法域使用 `cn`、`eu`、`us`；`shared` 只用于不含具体法域判断的公共能力。
- 稳定模块 ID 采用 `jurisdiction.business_capability`，不使用 `new`、`final_v2`、`service2` 等阶段性名称。

## 6. CSS 规则

- `main.tsx` 只导入 `tokens.css` 和 `app.css`。
- `app.css` 按固定顺序导入 `base.css`、`landing.css`、`pages.css`、`workspace.css`、`product-pages-and-overrides.css`。
- 分卷之间不相互 `@import`；不因选择器同名直接删除覆盖规则。
- 删除 CSS 前检查组件、动态 class、媒体查询、优先级、源码顺序和实际页面。
- 不用新增 `!important` 掩盖归属不清；CSS 移动、组件重写和视觉改版不在同一批次。

## 7. 测试组织

- 后端 API 版本测试位于 `backend/api/v0/tests`、`backend/api/v1/tests`；跨版本装配测试位于 `backend/api/tests`。
- 领域测试就近放在模块 `tests/`；开发完成后不因“测试不完整”删除有效回归。
- 前端单元测试与源码就近，测试基础设施和跨模块门禁位于 `frontend/tests/`。
- Benchmark 的数据、Runner 和自身测试只位于 `benchmarks/`。
- 运行测试必须写入临时或被忽略目录，不把运行输出反向作为源码依赖。

## 8. 最小验证矩阵

后端行为或结构调整：

```bash
uv run --frozen pytest -q
uv run --frozen python scripts/check_repository_hygiene.py
```

前端调整：

```bash
cd frontend
npm test
npm run build
```

Benchmark 调整：

```bash
uv run --frozen pytest -q benchmarks/tests
uv run --frozen python scripts/run_smoke_benchmark.py --mode all --target all
uv run --frozen python scripts/run_rag_retrieval_benchmark.py
```

Smoke 用于固定产品链路回归，规模化检索用于观察长尾召回、排序、拒答和模式差异；两者不得互相替代。任何 Citation、Issue 或 Recall 指标都必须同时说明数据来源、Gold 状态和指标语义，不得直接解释为法律正确率。

每批同时执行引用复扫、`git diff --check`、临时文件检查，并说明未运行的外部服务或法律人工验证。

## 9. AI 辅助开发验收

合入前由责任人确认：新增结构有实际消费者；没有复制同义 Client、Schema 或 Workflow；命名体现业务；错误与 fallback 可观测；API/Schema 有测试；Prompt/规则有版本与回归证据；外部代码、模板和数据已记录来源；提交目标单一且可回滚。
