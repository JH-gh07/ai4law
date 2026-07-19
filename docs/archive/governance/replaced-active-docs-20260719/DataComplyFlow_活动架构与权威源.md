# DataComplyFlow 活动架构与权威源

## 当前活动入口

- 后端：`backend.main:app`；
- 前端：`frontend/src/main.tsx`，React/Vite；
- 后端应用工厂及版本前缀：`backend/app.py`；
- v0 路由聚合：`backend/api/v0/router.py`；
- v1 公共及业务路由聚合：`backend/api/v1/router.py`；
- 法域业务模块 API：`backend/domains/{cn,eu,us}/*/router.py`；平台公共 Endpoint 位于 `backend/api/v1/endpoints/`；
- 前端模块映射：`frontend/src/lib/module-adapter.ts`；
- 前端任务定义：`frontend/src/lib/task-templates.ts`。

## 权威源

| 内容 | 当前权威位置 | 说明 |
|---|---|---|
| Python 依赖 | `pyproject.toml`、`uv.lock` | 锁文件必须与项目配置同步 |
| 前端依赖 | `frontend/package.json`、`frontend/package-lock.json` | 不提交 `node_modules` 和 `dist` |
| 运行配置定义 | `backend/core/settings.py`、`backend/core/runtime_settings.py` | 本地覆盖文件不进入 Git；设置 API 要求登录且响应不回传凭据明文 |
| 模块身份注册表 | `config/module_registry.json` | 跨前后端静态身份契约，不生成或控制 FastAPI Router |
| 模块实现目录 | `backend/domains/{cn,eu,us}/` | 法域实现按目录归属；CN Document Review 位于 `backend/domains/cn/document_review/` |
| LLM 公共入口 | `backend/common/llm/` | 历史 `ai_engine` 副本已删除，不存在第二活动入口 |
| RAG 公共入口 | `backend/common/rag/service.py` | 业务模块使用 Facade；运行策略统一命名为 `multi_index`、`single_index` 与 `enriched_compatibility`，并由 `RetrievalManifest` 区分；索引存储版本名称保持不变 |
| 资源路径入口 | `backend/core/resource_paths.py` | 活动代码解析知识库和模板位置的唯一入口 |
| 法律知识源 | `resources/legal/` | 活动法规根；`catalog/` 和 `registry/` 是来源目录与注册表权威源 |
| RAG 评测数据 | `benchmarks/datasets/product_smoke/`、`benchmarks/datasets/rag_retrieval/` | 与生产法规资源隔离，生产 RAG 不得索引 |
| RAG 评测执行 | `benchmarks/smoke_eval.py`、`benchmarks/rag_retrieval_eval.py` 与两个 `scripts/run_*_benchmark.py` | 评测逻辑不进入生产 RAG 包 |
| 外部法律 API | `backend/integrations/delilegal.py` | 第三方接口适配层，不属于公共 RAG 或领域实现 |
| 法域规则数据 | `resources/rules/{cn,eu,us}/` | 规则文件通过 `backend/core/resource_paths.py` 解析 |
| 报告模板 | `resources/templates/{cn,eu,us}/` | 已按法域迁移；活动代码必须通过资源路径入口访问 |
| 研究与产品设计来源材料 | `resources/research/` | 非运行资产；不得作为法规、Prompt、Fixture或配置权威源 |
| 本地运行存储 | `storage/README.md` | 数据库、配置、上传、报告、Trace 与可重建索引均为本地资产；Git 只允许 README 和脱敏示例配置 |
| 工程规范 | `docs/engineering/` | 当前工程约束权威入口 |
| 事实审计 | `docs/handoff/` | 结论以当前代码和测试为准 |

## 兼容与历史边界

- `/api/v0` 的 `v0_task_gateway` 仍是兼容边界：当前前端只直接调用文件上传，并依赖响应中的物理 `path` 继续构造 v1 模块请求；v0 任务接口主要由模块测试、QA 脚本和历史 demo 消费。迁移前不能按版本名直接删除，也不得把旧实现复制成 v1；安全与退役顺序以分阶段治理计划的 API-001 审计为准；
- `/api/v1` 是当前主 API，未来规范化 API 应新增版本而不是原地破坏；
- `backend/domains/cn/transfer_diagnosis/` 是唯一诊断规则与推理实现；`backend/api/diagnosis.py` 保留会话持久化兼容契约，由 `backend/services/diagnosis_session_service.py` 转调权威评估器；
- 报告模板已迁入`resources/templates/{cn,eu,us}/`，`doc/v2/`不再是活动依赖；
- storage/rag/v3/ 是业务首选索引，regulation_index_v2.json 仅作为 Facade 的受控 fallback；兼容 API 不得由业务模块直接 import；
- 仓库级命令以 `scripts/README.md` 为权威清单；一次性迁移和失效脚本不在活动代码树中长期保留。
