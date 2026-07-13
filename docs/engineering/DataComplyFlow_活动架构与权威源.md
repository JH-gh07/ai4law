# DataComplyFlow 活动架构与权威源

## 当前活动入口

- 后端：`backend.main:app`；
- 前端：`frontend/src/main.tsx`，React/Vite；
- 后端公共 API：`backend/api/router.py`；
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
| RAG 公共入口 | `backend/common/rag/` | v2 检索服务与 v3 编排仍处于兼容共存阶段 |
| 法律知识源 | `doc/knowledge/` | `_index`、`_registry` 是唯一索引和注册表源 |
| RAG 评测数据 | `doc/knowledge/_evaluation/` | 不使用已删除的 `evaluation/` |
| 报告模板 | `doc/v2/assets/templates/` | 名称历史化但仍被活动代码调用，暂不能删除 |
| 运行 Trace/报告/上传 | `storage/` 本地目录 | 运行产物，不作为产品源码提交 |
| 工程规范 | `docs/engineering/` | 当前工程约束权威入口 |
| 事实审计 | `docs/handoff/` | 结论以当前代码和测试为准 |

## 兼容与历史边界

- `/api/v0` 的 `v0_task_gateway` 仍被前端文件上传和兼容流程使用，不能按版本名直接删除；
- `/api/v1` 是当前主 API，未来规范化 API 应新增版本而不是原地破坏；
- `backend/api/diagnosis.py` 与 `backend/modules/diagnosis/` 是两套不同契约，收敛前均保留；
- `doc/v2/` 中模板仍为运行依赖；
- `storage/rag/regulation_index_v2.json` 与 `storage/rag/v3/` 均有调用者，完成可重建验证前不得仅按版本号删除；
- `scripts/legacy/` 只用于历史追溯，不是启动或发布入口。
