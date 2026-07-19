# DataComplyFlow 模块身份与法域契约

> 状态：active
> 跨前后端机器可读权威源：`config/module_registry.json`

## 1. 标识职责

| 字段 | 职责 |
|---|---|
| `module_id` | Trace、Benchmark 和跨前后端使用的稳定业务身份 |
| `jurisdiction` | `cn`、`eu` 或 `us` 法域 |
| `frontend_key` | 当前前端状态和兼容调用键 |
| `task_template_id` | 前端任务模板身份 |
| `implementation_package` | 当前真实后端实现包 |
| `v1_api_prefix` | 已发布 v1 业务路径前缀 |
| `lifecycle` | `active` 或 `legacy-compatible` |
| `note` | 解释无法由结构字段表达的兼容边界 |

注册表是静态身份契约，不生成或控制 FastAPI Router。后端路由由 `backend/api/v1/router.py` 显式装配，前端请求由 `frontend/src/lib/module-adapter.ts` 显式定义。

## 2. 当前法域实现

| module ID | 实现包 | API 前缀 |
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

## 3. 兼容边界

- `cn_flow` 是历史 frontend key 和 API 兼容名，真实身份属于美国 EO 14117；
- `cn_flow` 与 `us_14117` 的 Schema、规则深度和输出不同，当前不得直接合并；
- `review` 当前属于中国法域文档审查实现；
- 中国 SCC 与欧盟 SCC 是独立模块，不得共用模块 ID 或任务模板；
- `backend/modules/` 已退役，不得重新创建兼容包。

## 4. 变更门禁

模块改名、移动、合并或删除前必须同时满足：

1. 注册表身份和法域已经确认；
2. HTTP 方法与完整 URL 保持兼容或有明确新版本；
3. 前端 Adapter、任务模板和恢复映射同步；
4. Trace、Citation、RAG 和 Benchmark 标识已有迁移方案；
5. 实现包可导入，登记前缀已真实挂载；
6. 后端模块身份、路由和前端注册表测试通过；
7. 每个模块单独形成可回退批次。
