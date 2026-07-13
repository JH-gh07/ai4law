# DataComplyFlow AI 辅助开发与代码规范

## 1. 目的与适用范围

本规范用于约束 DataComplyFlow 的人工开发和 AI 辅助开发。目标是形成可维护、可测试、可审计且具有明确业务语义的代码，而不是通过机械改名、无意义改写或代码混淆规避任何检测。

本规范适用于后端、前端、Prompt、规则、RAG、评测、脚本和配置。AI 生成内容在合入前必须由开发者理解、修改并验证；AI 输出不能替代作者确认、法律复核或测试证据。

## 2. 架构边界

新功能遵循以下依赖方向：

```text
API / UI
→ Application Service / Use Case
→ Domain Rule / Workflow
→ RAG / LLM / External Tool
→ Verifier / Quality Gate
→ Repository / Renderer / Trace
```

约束：

1. Router 只负责鉴权、协议转换、调用用例和响应映射，不拼接 Prompt、不直接读写业务文件。
2. 确定性法律规则属于 Domain/Rule 层；LLM 不得静默覆盖确定性规则结论。
3. LLM、RAG、Citation、Trace、文件渲染优先复用 `backend/common/` 或后续对应的 platform 层。
4. 模块不得复制一套仅改名称的 LLM Client、任务状态机或引用注册表。
5. `Agent` 名称仅用于确有独立职责、明确输入输出并真实参与流程的组件；单次普通模型调用优先命名为 generator、extractor、reviewer 或 client method。
6. fallback 必须可观测，记录触发原因、降级结果和 trace；不得以空结果或模板文本伪装成功。

## 3. 法域与模块标识

### 3.1 法域代码

- `cn`：中国法域；
- `eu`：欧盟法域；
- `us`：美国法域；
- `shared`：不包含法域法律判断的公共能力。

### 3.2 稳定模块 ID

模块 ID 是 API、Trace、Benchmark、前端任务模板和运行清单之间的稳定关联键。目录可以迁移，模块 ID 不应随内部重构改变。

```text
cn.transfer_diagnosis
cn.security_assessment
cn.scc_review
cn.pipia
cn.data_flow
eu.scc_review
eu.bcr_review
eu.dpia
eu.tia
us.eo_14117
us.cpra
```

禁止新增 `new_service`、`final_v2`、`assessment2`、无前缀 `scc` 等缺少业务或法域语义的稳定标识。

### 3.3 代码命名

- Python 包、函数、变量、JSON 字段：`snake_case`；
- Python/TypeScript 类和类型：`PascalCase`；
- 常量：`UPPER_SNAKE_CASE`；
- API 路径：小写 `kebab-case`；
- 法律通用缩写可以保留：SCC、DPIA、TIA、PIPIA、BCR、CPRA；
- 同一概念在 Schema、Trace、前端和 Benchmark 中使用同一英文术语。

## 4. API 规范

1. 现有 `/api/v0`、`/api/v1` 是兼容接口，不得原地破坏性改名。
2. 新的统一接口使用 `/api/v2/{jurisdiction}/{resource}`。
3. URL 表达资源，不新增 `/generate_async` 一类动作加执行模式的路径；同步/异步通过明确任务资源或请求选项表达。
4. 每次请求应能关联 `request_id`；异步执行应返回 `task_id`，运行记录应包含 `trace_id`。
5. 错误响应至少包含稳定 `code`、用户可读 `message` 和可选 `details`，不得把 Python 异常文本直接作为稳定 API 契约。
6. API Schema 变更必须更新后端测试、前端 Adapter、OpenAPI 示例和 Benchmark Adapter。
7. 兼容路由必须声明弃用状态、替代路由和计划移除条件。

## 5. Schema 与领域数据规范

1. API DTO、领域对象、数据库实体和渲染模型分离，禁止为了省事全流程共用一个可变字典。
2. `unknown`、`not_applicable`、缺失值和否定结论必须区分。
3. 法律结论至少关联规则/依据标识；生成性结论应关联 Evidence/Citation 或明确标记未支持。
4. 时间采用带时区 ISO 8601；法规数据应保留法域、版本、发布日期、生效日期和来源定位。
5. Pydantic 模型禁止使用语义不明的 `data: dict` 作为主要业务契约；确需扩展字段时应说明版本策略。
6. 新增公共 Schema 前先检索 `backend/common/schema`、`backend/schemas` 和模块 Schema，避免同义重复。

## 6. 规则、RAG、LLM 与 Prompt

### 6.1 规则

- 规则必须区分条件、例外、法律效果、优先级和缺失事实；
- 规则命中和未命中应可解释并写入 Trace；
- 法规版本变化不得直接覆盖旧规则，应保留版本边界和生效时间；
- AI 与确定性规则冲突时，默认保留规则结果并转人工复核，除非业务规范另有明确规定。

### 6.2 RAG

- 原始法规和清洗数据是源资产，向量索引和全文索引是可重建生成物；
- Retrieval 输入、Top-K、过滤条件、索引版本和返回来源必须进入运行清单；
- 不允许把检索失败静默替换为模型常识；
- RAG 改动必须运行固定评测集，至少记录 Recall@K、失败率和时延。

### 6.3 LLM 与 Prompt

- Prompt 必须声明模块 ID、法域、任务、版本、输入字段和输出 Schema；
- Prompt 不得散落在 Router 中；模块内 Prompt 应集中管理并可追踪版本；
- JSON/Schema 解析失败必须显式失败或进入可记录修复流程；
- 模型、温度、超时、重试和成本配置来自运行配置，不得硬编码凭据；
- 修改 Prompt 必须补充或更新回归样本，不能只凭单次演示结果验收。

## 7. 测试与质量门禁

每个行为改动至少具备与风险相称的验证：

1. 规则和纯函数：单元测试，包括缺失、边界、例外和冲突；
2. API：鉴权、成功、校验失败、业务失败和兼容契约测试；
3. Workflow：隔离外部模型的确定性集成测试；
4. RAG/Prompt：固定数据集回归，不用普通单元测试假装法律正确性；
5. 前端：TypeScript 构建，关键用户流应逐步增加自动化测试；
6. 合入前运行仓库卫生检查、后端全量测试和前端生产构建。

禁止通过删除断言、放宽生产鉴权、无条件 mock 或吞异常让测试变绿。

## 8. AI 辅助代码验收清单

提交 AI 辅助代码前，开发者必须确认：

- 我能解释每个新增类、字段和分支的业务必要性；
- 已检索并复用现有公共实现，没有复制同义 Schema/Client/Workflow；
- 命名体现具体法域和业务，不使用模板化占位词；
- 不存在虚构工具调用、伪 Agent、静默 fallback 或无依据结论；
- API、Schema 和异常行为有测试；
- Prompt/规则改动有版本和回归证据；
- 外部代码、模板和数据已记录来源与许可；
- 删除的资产可通过 Git 或批准的备份恢复；
- 提交只包含一个清晰目标，可独立回滚。

## 9. 提交和评审规范

推荐提交类型：`docs`、`chore`、`fix`、`refactor`、`test`、`feat`。清理、Bug 修复、目录迁移、依赖升级和算法改动不得混在同一提交。

评审说明至少包含：目的、事实依据、改动范围、兼容影响、验证命令、回退条件和尚未验证事项。

## 10. 当前迁移约束

当前 `backend/modules/` 仍采用历史平铺结构，`scc`、`assessment`、`diagnosis` 等名称尚未物理迁移。新代码应使用稳定模块 ID；物理目录迁移必须逐模块进行，并保留 `/api/v0`、`/api/v1` 和前端 Adapter 的兼容测试，禁止一次性全量改名。
