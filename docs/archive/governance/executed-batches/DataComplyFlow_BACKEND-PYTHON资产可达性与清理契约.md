# DataComplyFlow Backend Python 资产可达性与清理契约

> 日期：2026-07-17
> 状态：已完成
> 原则：只删除已确认没有生产消费者、动态注册、脚本入口或外部契约的代码；测试不能单独证明产品接入。

## 1. 分层边界

- `backend/api/v0/`、`backend/api/v1/` 是 HTTP 版本适配层；
- `backend/domains/{cn,eu,us}/` 是版本无关的法律业务实现，不属于 v1；
- v1 通过 `backend/api/v1/router.py` 挂载法域资源 Router；
- v0 Task Gateway 是跨法域兼容编排，不属于单一法律法域，因此保留在 `backend/api/v0/`；
- 版本前缀只由 `backend/app.py` 注册。

## 2. 测试目录契约

```text
backend/api/
├── tests/            # 跨版本应用装配、路由基线
├── v0/tests/         # v0 API 集成测试
└── v1/tests/         # v1 Endpoint/API 集成测试
```

法域和公共能力单元测试继续就近放在各自 `tests/`，测试不会在开发完成后删除。

## 3. 本批删除范围

以下组件没有生产调用者，也没有配置、动态导入或脚本入口：

1. `backend/common/llm/adapter.py`：旧确定性 v0 模板适配器；
2. `backend/common/rag/pgvector_store.py`：未被当前 RAG 工厂或 Retriever 调用；
3. `backend/domains/cn/document_review/agents/`：工厂 `create_review_agents()` 没有消费者；
4. CN Security Assessment 未接入 Agent：input normalization、data classification、attachment parsing、document planning、expression calibration、legal citation、controlled repair；
5. `backend/domains/cn/security_assessment/citation_quality.py`：唯一消费者是未接入 LegalCitationAgent。

孤立测试只验证未接入类本身，不构成产品消费者；删除上述类时同步删除对应孤立测试用例。

## 4. 本批明确保留

以下知识入库文件虽然没有进入当前 API 主流程，但仍通过公共包导出且存在 Chunker 测试，本批不按“完全无使用”删除：

- `chinese_legal_patterns.py`；
- `chunker.py`；
- `document_parser.py`；
- `storage_manager.py`；
- `ingestion_pipeline.py`。

项目负责人已确认保留该知识入库链。当前状态统一认定为“实现存在但尚未接入生产 API”；后续接入时必须补齐上传入口、入库集成测试和 RAG 索引同步，不得将其描述为当前已可用能力。

## 5. 符号级清理规则

- 扫描全部顶层函数、类和类方法；
- 检查生产代码、脚本、Benchmark、测试、导入别名和字符串动态名称；
- 排除 FastAPI/Pydantic/ORM 装饰器、魔术方法、协议回调及框架注册；
- 名称相同但无法证明具体绑定关系时保守保留；
- 只删除零消费者且无框架回调语义的高置信度符号。

## 6. 验收

- 修改前后路由 Method、Path、Schema 不变；
- API 测试按 v0、v1、跨版本三类归位；
- 活动代码不得引用本批删除模块；
- 后端与 Benchmark 全量测试通过；
- 前端测试、构建和仓库卫生检查通过。

## 7. 执行结果

- API 测试已分为 `api/v0/tests/`、`api/v1/tests/` 和跨版本 `api/tests/`；
- 文件级清理删除 21 个没有生产消费者的 Python 文件，约 2,000 行；
- 符号级清理扫描 `backend/`、`benchmarks/`、`scripts/` 的 AST 名称、属性、导入别名和字符串引用，两轮共删除 22 个零引用顶层符号、23 个零引用普通类方法及 4 个随之失效的导入，共减少约 319 行符号实现；
- 删除模块和符号的活动代码、配置、脚本与测试引用为 0；二次复扫只剩明确保留的 `IngestionPipeline`、`IngestionPipeline.ingest()` 和 `DocumentParser.parse_path()`；
- 可达性复核后，剩余非主应用可达文件只有 5 个明确保留的知识入库文件及 pytest 的 `backend/conftest.py`；
- 后端与 Benchmark：`366 passed`；相较上一基线减少的 8 项均为被删除孤立组件的自测；
- 当前应用包含 103 个 `/api/*` Method + Path、5 个框架/健康检查 Method + Path；OpenAPI 正常生成，重复 Method + Path 为 0；
- 仓库卫生检查通过（1,362 个仓库文件），前端 5 项测试和生产构建均通过。

本轮“零引用”是仓库内静态可证明结论，不扩张为第三方在仓库外直接导入内部 Python 符号的兼容承诺。知识入库链属于项目负责人明确指定的保留例外，不能因未接入生产 API 而继续级联删除。
