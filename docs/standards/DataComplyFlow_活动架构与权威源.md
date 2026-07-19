# DataComplyFlow 活动架构与权威源

本文只描述当前活动入口、稳定身份和单一事实来源。历史设计与阶段报告不覆盖当前代码和测试事实。

## 1. 活动入口

| 范围 | 当前入口 |
|---|---|
| 后端 ASGI | `backend.main:app` |
| 应用工厂与版本装配 | `backend/app.py` |
| v0 / v1 Router | `backend/api/v0/router.py`、`backend/api/v1/router.py` |
| 法域业务 | `backend/domains/{cn,eu,us}/` |
| 公共能力 | `backend/common/` |
| 第三方服务 | `backend/integrations/` |
| 前端入口 | `frontend/src/main.tsx`、`frontend/src/App.tsx` |
| 前端接口 | `frontend/src/api/` |
| 前端任务与模块身份 | `frontend/src/lib/task-templates.ts`、`frontend/src/lib/module-registry.ts` |
| 产品评测 | `benchmarks/`、`scripts/run_*_benchmark.py` |

## 2. 权威源

| 内容 | 权威位置 | 边界 |
|---|---|---|
| Python 依赖 | `pyproject.toml`、`uv.lock` | `.venv` 可重建，不提交 |
| 前端依赖 | `frontend/package.json`、`frontend/package-lock.json` | `node_modules`、`dist` 不提交 |
| 运行配置定义 | `backend/core/settings.py`、`backend/core/runtime_settings.py` | 密钥只进入环境变量或被忽略的本地配置 |
| 模块稳定身份 | `config/module_registry.json` | 不生成 FastAPI Router |
| 后端业务实现 | `backend/domains/{cn,eu,us}/` | 不恢复历史 `backend/modules/` |
| LLM / RAG | `backend/common/llm/`、`backend/common/rag/service.py` | 模块不得复制公共 Client 或 Retriever |
| 法规来源与条款语料 | `resources/legal/` | Benchmark 数据不得进入生产索引 |
| 静态规则 | `resources/rules/` | 当前 `cn/review_rulebook.json` 被生产代码读取 |
| 报告模板 | `resources/templates/{cn,eu,us}/` | 通过资源路径函数解析 |
| 合成评测输入 | `benchmarks/sample-inputs/` | 不等同于 `storage/uploads/` 运行上传件 |
| 评测数据与执行 | `benchmarks/datasets/`、`benchmarks/*_eval.py` | 评测结果写入 `outputs/benchmarks/` |
| 本地运行状态 | `storage/` | 仅 README 与脱敏示例配置允许提交 |
| 模块输出 | `outputs/` | 按运行生成，不是源码事实源 |
| 当前开发规范 | `docs/standards/` | 本目录是唯一活动规范入口 |
| 有日期的事实材料 | `docs/handoff/` | 与当前代码冲突时以代码和测试为准 |

## 3. 模块与法域身份

模块 ID 是 API、Trace、Benchmark 和前端任务之间的稳定关联键。目录可以调整，稳定 ID 不随内部重构改变。

| module ID | 实现包 | v1 API |
|---|---|---|
| `cn.transfer_diagnosis` | `backend.domains.cn.transfer_diagnosis` | `/api/v1/diagnosis` |
| `cn.security_assessment` | `backend.domains.cn.security_assessment` | `/api/v1/assessment` |
| `cn.document_review` | `backend.domains.cn.document_review` | `/api/v1/review` |
| `cn.scc_review` | `backend.domains.cn.scc_review` | `/api/v1/scc` |
| `cn.pipia` | `backend.domains.cn.pipia` | `/api/v1/pipia` |
| `eu.scc_review` | `backend.domains.eu.scc_review` | `/api/v1/eu_scc` |
| `eu.bcr_review` | `backend.domains.eu.bcr_review` | `/api/v1/bcr` |
| `eu.dpia` | `backend.domains.eu.dpia` | `/api/v1/dpia` |
| `eu.tia` | `backend.domains.eu.tia` | `/api/v1/tia` |
| `us.eo_14117` | `backend.domains.us.eo14117` | `/api/v1/us_14117` |
| `us.cpra` | `backend.domains.us.cpra` | `/api/v1/cpra` |
| `us.eo_14117_flow_review` | `backend.domains.us.eo14117_flow_review` | `/api/v1/cn-flow` |

`cn_flow` 是历史前端键和 API 兼容名，真实法域身份属于美国 EO 14117。中国 SCC、欧盟 SCC 以及两个 EO 14117 流程具有不同 Schema 和输出，不得仅因名称相似直接合并。

## 4. 兼容边界

- `/api/v1` 是当前主 API；`/api/v0` 仍承担文件上传和历史任务网关兼容，不按版本号直接删除或复制成 v1。
- `backend/domains/cn/transfer_diagnosis/` 是诊断规则实现；会话型兼容入口转调该实现。
- RAG 统一经 `backend/common/rag/service.py` 进入；索引版本名不等于业务入口版本。
- `backend/integrations/delilegal.py` 是活动第三方法律 API 适配器，不属于可删除的空集成目录。
- 研究材料不参与生产运行；其去留按来源与归档价值判断，不得作为法规、模板或 Gold 的替代权威源。

## 5. 变更要求

修改模块身份、路径或权威源前，必须同步检查代码消费者、API、前端、Trace、Benchmark、文档和测试。不得建立第二注册表、第二运行配置源或第二套同义实现。
