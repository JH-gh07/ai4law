# DataComplyFlow Backend 后端目录全面审查与治理结果

> 审查日期：2026-07-17
> 状态：结构治理与最终回归均已完成
> 范围：`backend/` 的目录职责、测试布局、依赖方向、法域模块、公共能力、资源与评测边界。
> 原则：先确认消费者，再删除或移动；保持 URL、Schema、规则、Prompt 与业务行为不变。

## 1. 治理结论

本轮完成的是后端目录和依赖边界收敛，不是业务重写。当前生产代码统一分为 API 装配、公共能力、核心基础设施、法域实现、外部集成、数据模型、仓储、Schema 和应用服务九类。不存在散落在生产目录旁的 `test_*.py`，也不存在旧 `backend/modules/` 或 `backend/data/` 活动目录。

当前后端共有 450 个 Python 文件、85 个后端测试文件；另有 1 个 RAG 评测测试位于 `benchmarks/tests/`。目录统计如下：

| 目录 | 文件 | Python | 测试 | 治理后职责 |
|---|---:|---:|---:|---|
| `api` | 38 | 37 | 13 | 版本路由、平台公共 Endpoint、API 回归测试 |
| `common` | 89 | 89 | 17 | 跨法域可复用能力 |
| `core` | 13 | 13 | 4 | 配置、容器、数据库、资源路径 |
| `domains` | 274 | 267 | 48 | CN/EU/US 法域业务实现 |
| `integrations` | 2 | 2 | 0 | 外部系统适配 |
| `models` | 6 | 6 | 0 | 数据库实体 |
| `repositories` | 5 | 5 | 0 | 数据访问 |
| `schemas` | 11 | 11 | 0 | 跨模块公共 API Schema |
| `services` | 16 | 16 | 3 | 应用级编排与平台服务 |

## 2. 当前权威目录

```text
backend/
├── main.py                         # ASGI 暴露入口
├── app.py                          # 完整应用工厂和版本路由注册
├── api/
│   ├── v0/                         # 历史任务网关兼容边界
│   ├── v1/
│   │   ├── endpoints/              # 平台公共 v1 Endpoint
│   │   └── router.py               # v1 路由聚合
│   └── tests/                      # API 与路由回归
├── common/                         # 真正跨法域的公共能力
├── core/                           # 基础设施和组合根
├── domains/
│   ├── cn/
│   ├── eu/
│   └── us/
├── integrations/                   # 第三方接口适配
├── models/                         # ORM 实体
├── repositories/                   # 数据访问
├── schemas/                        # 跨模块公共 DTO
└── services/                       # 应用级服务
```

## 3. 已执行修改

### 3.1 测试归位

- v0 API 集成测试统一位于 `backend/api/v0/tests/`；v1 Endpoint 测试统一位于 `backend/api/v1/tests/`；跨版本路由装配测试位于 `backend/api/tests/`；
- `backend/core/test_time.py` 迁入 `backend/core/tests/`；
- 3 个 `backend/services/test_*.py` 迁入 `backend/services/tests/`；
- 当前 `backend/` 下没有位于 `tests/` 目录之外的测试文件；
- RAG 评测测试迁至 `benchmarks/tests/test_rag_eval.py`，避免生产包承载评测职责。

这些文件均为有效测试，不是旧文件；本轮只调整物理位置。

### 3.2 API 层收敛

- 平台公共 v1 Endpoint 统一迁至 `backend/api/v1/endpoints/`；
- `backend/api/v1/router.py` 继续聚合平台 Endpoint 和法域 Router；
- `backend/api/v0/` 只保留兼容任务网关，不复制到 v1；
- Artifact 注册能力迁至 `backend/services/artifact_registry.py`，消除 Domain 对 API 层的反向依赖；
- 修改后路由快照仍为 104 条，`HTTP method + path` 无重复；
- `backend/api/tests/route_baseline.json` 已按真实应用重新生成，URL、Method、route name 和 operation ID 未改变，仅 Endpoint 模块归属变化。

### 3.3 CN Document Review 归位

- `backend/services/review_service/` 迁入 `backend/domains/cn/document_review/`；
- Review Router 从公共 Endpoint 迁入该法域模块；
- `config/module_registry.json` 的实现包同步为 `backend.domains.cn.document_review`；
- Review 规则文件迁至 `resources/rules/cn/review_rulebook.json`；
- 原 `backend/data/` 因已空而删除。

该修改只修正领域身份和物理归属，`/api/v1/review` 契约保持不变。

### 3.4 Common、Integration 与 Benchmark 边界

- 删除无生产消费者的 `backend/common/observability/`；
- 删除无生产消费者的 `backend/common/schema/`；
- DeliLegal 外部法律 API 从应用 Service 迁至 `backend/integrations/delilegal.py`；
- RAG 评测实现迁至 `benchmarks/smoke_eval.py` 与 `benchmarks/rag_retrieval_eval.py`；
- RAG 评测命令迁至 `scripts/run_smoke_benchmark.py` 与 `scripts/run_rag_retrieval_benchmark.py`；
- `backend/common/knowledge/builders_v2.py` 不再反向导入 CN Review 具体实现，而是通过资源路径读取规则数据。

### 3.5 Core 依赖方向

- `backend/core/runtime_settings.py` 不再直接导入法域 Router；
- 运行时客户端重绑定移至 `backend/services/runtime_client_refresher.py`；
- `backend/app.py` 在组合应用时调用该应用级服务。

现有 Router 模块级 Service 单例仍被兼容性重绑定；本轮仅把该行为移出 Core，未冒险重写全部依赖注入机制。

### 3.6 资源归位

- 法域规则统一从 `resources/rules/{jurisdiction}/` 解析；
- CN 安全评估官方模板及 Schema 统一位于 `resources/templates/cn/`；
- `backend/core/resource_paths.py` 是规则和模板路径解析入口；
- 生产代码不再引用旧 `backend/modules/*/templates` 或 `backend/data/review_rulebook.json`。

## 4. 保留项及理由

| 保留项 | 理由 | 状态 |
|---|---|---|
| `/api/v0/tasks` | 历史测试、QA 与兼容客户端仍可能消费 | `legacy-compatible` |
| `backend/api/v1/endpoints/diagnosis.py` | 会话持久化 API，与权威诊断规则模块不是相同 Method + Path | 保留兼容职责 |
| `backend/domains/cn/transfer_diagnosis/router.py` | 当前诊断规则与推理实现 | 活动实现 |
| `backend/common/*` 其余子包 | 均有外部生产消费者 | 活动公共能力 |
| 大型 Service/Rule Engine | 文件大不等于无用，未发现可无行为风险删除的孤立实现 | 后续逐模块审查 |
| `outputs/`、`storage/traces/` 等 | 属于运行产物且可能含历史审计证据，本轮未获整目录删除授权 | Git 忽略、本地保留 |

## 5. 明确没有实施的事项

- 未修改业务规则、Prompt、请求或响应 Schema；
- 未修改数据库结构；
- 未修改前端调用协议；
- 未把 v0 实现复制进 v1；
- 未为追求目录对称而创建空层；
- 未按文件行数拆分大型业务模块；
- 未删除来源或消费者尚未确认的运行证据。

## 6. 验收门槛

最终回归必须满足：

1. 后端与 Benchmark 测试全部通过；
2. 路由总数为 104，Method + Path 无重复；
3. OpenAPI 正常生成，`/health`、`/api/v0/tasks` 和关键 v1 路由存在；
4. `config/module_registry.json` 可解析且所有实现包可导入；
5. 仓库卫生检查通过；
6. 前端测试与构建通过，证明 API 路径和模块注册未破坏前端契约；
7. 测试后清理 `__pycache__`、`.pytest_cache` 等可再生缓存。

最终测试命令与实际结果已登记于下一节。

## 7. 最终验证结果

执行日期：2026-07-17。

| 验证项 | 命令 | 结果 |
|---|---|---|
| 后端与 Benchmark 全量回归 | `.venv/Scripts/python.exe -m pytest backend benchmarks/tests -q -p no:cacheprovider --basetemp .pytest_cache/backend-unused-cleanup-final` | 当前 `366 passed`；清理前为 374，减少的 8 项均为已删除孤立组件的自测；1 项第三方 TestClient 弃用警告 |
| 仓库卫生 | `.venv/Scripts/python.exe scripts/check_repository_hygiene.py` | 通过，检查 1,380 个仓库文件 |
| 前端测试 | `cd frontend && npm test -- --run` | 2 个测试文件、5 项测试全部通过 |
| 前端构建 | `cd frontend && npm run build` | TypeScript 与 Vite 构建成功；仅有 chunk 大小提示 |
| 路由快照 | `backend/api/tests/test_route_assembly.py` | 104 条路由、无 Method+Path 冲突、OpenAPI 正常 |
| 缓存清理 | 删除 `.pytest_cache/`、`frontend/dist/`、Vitest 缓存 | 已完成 |

测试过程曾出现两类非产品失败，均已查明：一是迁移后测试仍使用旧 `backend.api.auth` 导入及旧 Review 注册表预期，已同步为新权威路径；二是沙箱默认临时目录不可写，最终以仓库内被忽略的 `.pytest_cache/` 作为 pytest basetemp 后全量通过。没有以跳过测试或降低断言的方式规避失败。

## 8. 审查结论

后端目录治理已达到可供人工代码审查的收敛状态：活动入口、版本 API、法域实现、公共能力、外部集成、应用服务、评测代码与资源文件的边界已经明确；已确认无消费者和已空的旧目录已经删除；保留的兼容接口和大型业务文件均有真实消费者或行为风险依据。

这不等于业务功能和法律结论已获得法律 Gold 验证，也不等于所有大型模块均已完成内部设计优化。后续人工审查应从 `backend/app.py` → `backend/api/v1/router.py` → `backend/domains/{cn,eu,us}/` → `backend/common/` 的顺序进行，避免在本次结构基线上再次混入无证据的全量重写。
