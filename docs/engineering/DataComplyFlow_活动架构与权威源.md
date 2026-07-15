# DataComplyFlow 活动架构与权威源

## 当前活动入口

- 后端：`backend.main:app`；
- 前端：`frontend/src/main.tsx`，React/Vite；
- 后端应用工厂及版本前缀：`backend/app.py`；
- v0 路由聚合：`backend/api/v0/router.py`；
- v1 公共及业务路由聚合：`backend/api/v1/router.py`；
- 业务模块 API：`backend/modules/*/router.py`；
- 前端模块映射：`frontend/src/lib/module-adapter.ts`；
- 前端任务定义：`frontend/src/lib/task-templates.ts`。

## 权威源

| 内容 | 当前权威位置 | 说明 |
|---|---|---|
| Python 依赖 | `pyproject.toml`、`uv.lock` | 锁文件必须与项目配置同步 |
| 前端依赖 | `frontend/package.json`、`frontend/package-lock.json` | 不提交 `node_modules` 和 `dist` |
| 运行配置定义 | `backend/core/settings.py`、`backend/core/runtime_settings.py` | 本地覆盖文件不进入 Git |
| 模块目录 | `backend/modules/` | 当前实现位置；稳定业务 ID 见模块注册表 |
| LLM 公共入口 | `backend/common/llm/` | `docs/archive/legacy/ai_engine/` 为历史资产，不是活动入口 |
| RAG 公共入口 | `backend/common/rag/service.py` | 业务模块使用 Facade；v3、真实 v2 与 compatibility API 必须由 `RetrievalManifest` 区分，默认回退语义仍需专项治理 |
| 法律知识源 | `doc/knowledge/` | `_index`、`_registry` 是唯一索引和注册表源 |
| RAG 评测数据 | `doc/knowledge/_evaluation/` | 不使用已删除的 `evaluation/` |
| 报告模板 | `doc/v2/assets/templates/` | 名称历史化但仍被活动代码调用，暂不能删除 |
| 运行 Trace/报告/上传 | `storage/` 本地目录 | 运行产物，不作为产品源码提交 |
| 工程规范 | `docs/engineering/` | 当前工程约束权威入口 |
| 事实审计 | `docs/handoff/` | 结论以当前代码和测试为准 |

## 兼容与历史边界

- `/api/v0` 的 `v0_task_gateway` 仍被前端文件上传和兼容流程使用，不能按版本名直接删除；
- `/api/v1` 是当前主 API，未来规范化 API 应新增版本而不是原地破坏；
- backend/modules/diagnosis/ 是唯一诊断规则与推理实现；backend/api/diagnosis.py 仅保留会话持久化兼容契约，由 backend/services/diagnosis_session_service.py 转调权威评估器；
- `doc/v2/` 中模板仍为运行依赖；
- storage/rag/v3/ 是业务首选索引，regulation_index_v2.json 仅作为 Facade 的受控 fallback；兼容 API 不得由业务模块直接 import；
- `scripts/legacy/` 只用于历史追溯，不是启动或发布入口。
