# DataComplyFlow 仓库规范化分阶段治理计划

> 状态：active
> 建立日期：2026-07-15
> 适用范围：仓库卫生、API 版本治理、RAG 版本治理、依赖边界、任务持久化和文档同步。
> 约束：每个批次目标单一、可独立验收和回滚；不得把清理、契约修复和算法优化混入同一批次。

## 1. 治理原则

1. 先记录事实基线，再做变更；目录名、版本号和文档宣称不能替代调用证据。
2. 兼容入口在迁移完成前仍是活动代码，不能因为名称为 `v0`、`v2` 或 `legacy` 直接删除。
3. 版本并存不是错误；无明确主版本、调用边界、退役条件和观测信息才是治理问题。
4. 物理移动法域模块、公开 API 迁移、RAG 算法替换和法律规则变化分别实施。
5. 每批必须记录基线、修改文件、兼容影响、测试、回退条件和遗留项。

### 1.1 删繁去简与最小变更门禁

仓库治理不是以增加代码量、移动目录或统一外观为目标。默认选择是保留稳定行为并减少不必要复杂度；任何删除、新增和修改都必须先通过以下门禁：

| 动作 | 允许条件 | 禁止情形 |
|---|---|---|
| 删除 | 已核对 import、Router、前端、测试、脚本、配置和运行时消费者；有测试与回退证据 | 仅因名称含 `old`、`v0`、`v2`、`legacy` 或目录看起来陈旧 |
| 新增 | 现有权威组件无法承担明确职责；新增内容有唯一消费者、测试和生命周期 | 复制已有 Service/Schema/Router；为目录整齐增加空壳；无意义包装 |
| 修改 | 问题、非目标、文件范围和兼容性已明确；可以独立验证和回滚 | 顺手重构相邻模块；混入算法优化；机械改名或格式化全仓 |
| 迁移 | 已确定 canonical source、兼容适配和消费者迁移顺序 | 复制旧实现到新版本后长期双轨运行 |

每个候选变更还必须回答：

1. 不修改会造成什么可验证的问题？
2. 能否通过删除、复用或配置收敛解决，而不是新增实现？
3. 是否改变 URL、Schema、法律判断、报告内容、Trace 或前端协议？
4. 哪项测试证明行为保持不变或缺陷已被修复？
5. 失败时如何恢复，临时兼容层何时退役？

任何一项无法回答，候选变更保持只读审计状态，不进入实施。

## 2. 当前问题分组

| 编号 | 问题类 | 当前事实 | 风险 | 优先级 |
|---|---|---|---|---|
| DOC-001 | 文档权威性 | 现行规范、快照、旧方案曾并列存在 | 开发者引用过时路径或设计 | P0，已完成首轮收敛 |
| HYG-001 | 仓库卫生 | `__pycache__`/`.pyc` 不受 Git 跟踪且已 ignore，但本地仍会由 Python 反复生成 | 本地噪声、误判为源码 | P0 |
| API-001 | 版本边界 | `/api/v1` 是主 API；`/api/v0` 任务网关仍被文件上传和兼容流程调用 | 误删造成前端断链；长期形成双契约 | P1/P2 |
| API-002 | 路由装配 | 应用工厂已向 v0/v1 聚合结构收敛，需由路由基线和重复检测持续保护 | 测试应用与生产应用不一致 | P1，当前批次待形成稳定提交 |
| RAG-001 | 检索版本 | 统一 Facade 可选择 v3、真实 v2 和兼容 API；业务迁移已完成，但默认回退会混用不同检索语义 | Benchmark 不公平、结果难复现 | P1 |
| RAG-002 | 回退正确性 | 回退触发、异常处理、非 `legal_grounding` 结果保留和 Manifest 消费仍需专项验证 | 静默降级或丢失有效检索结果 | P1 |
| ARCH-001 | 依赖边界 | 部分 Router/Service 仍持有模块级状态，运行设置对业务组件存在反向依赖 | 测试隔离、热更新和并发风险 | P2 |
| TASK-001 | 任务状态 | v0 兼容任务/文件状态含内存态实现 | 重启丢失、横向扩展不一致 | P2 |
| DOMAIN-001 | 法域目录 | 已有稳定模块目录和法域 catalog，尚未全量物理迁移到 `domains/{cn,eu,us}` | 认知成本较高，但当前功能可运行 | P3 |

## 2.1 当前执行决议（2026-07-15）

当前分支为 `codex/repository-structure-governance-20260713`，基线 commit 为 `300d9608d684912d4c3a54671cca161a53302f11`。工作树同时包含路由、Diagnosis、RAG、通用基础设施、前端和文档修改，尚未形成可独立回滚的稳定批次。

当前验证证据：

- `uv run --frozen pytest -q`：356 passed，1 个 Starlette/httpx 兼容警告；相较收敛前减少的 1 项是随未接入 `DiagnosisDecision` 一并删除的孤立测试；
- `frontend: npm test`：1 test passed；测试主动抛出的 `chunk load failed` 用于验证错误边界，退出码为 0；
- `frontend: npm run build`：通过，仍有 SuperDesign chunk 超过 500 kB 的非阻断警告；
- 仓库卫生检查和文档链接检查：通过。

因此下一步固定为 `GATE-001 现有工作树收敛`，在其完成前暂停新增治理代码。建议按以下独立边界审查和形成变更批次：

1. FastAPI 路由聚合与路由基线；
2. Diagnosis 权威实现与会话兼容层；
3. RAG Facade、业务迁移与 Manifest；
4. UTC、Citation、Knowledge 等通用基础设施修正；
5. 前端依赖、懒加载和错误边界测试；
6. 文档导航、历史归档和治理门禁。

每组必须单独核对 diff、消费者、测试和兼容性。未受跟踪的理论研究文档不得随治理批次自动纳入。完成上述收敛后，才进入阶段 C 的 v0 安全与生命周期审计；阶段 D 的 RAG fallback 语义治理紧随其后，但二者不得混成一次修改。

### GATE-001 分组审查结论

| 分组 | 当前处理 | 准入结论 | 约束 |
|---|---|---|---|
| FastAPI 路由 | 保留应用工厂、v0/v1 聚合器和 104 条路由基线 | 可形成独立批次 | 不改变 Method、URL、Schema 或 endpoint |
| Diagnosis | 保留最新模块规则实现与会话持久化兼容层 | 可形成独立批次 | 已删除无生产消费者的 `DiagnosisDecision`、`ConclusionSource` 和转换函数；法律 Gold 留待最终验证 |
| RAG | 保留 Facade 和业务调用迁移 | 条件保留，不能宣告治理完成 | Manifest 多数尚未进入业务输出；issue-discovery 的非 legal bundle、异常 fallback 和运行配置仍待阶段 D 处理 |
| 通用基础设施 | 保留 UTC helper、既有数据库 naive UTC 适配、pytest marker 等小范围修正 | 可形成独立批次 | 不迁移数据库字段，不与 Diagnosis/RAG 混合 |
| 前端 | 保留已通过测试和构建的依赖、懒加载、错误边界与本地监听收紧 | 必须继续拆分 | 依赖升级、性能拆包、开发服务器安全是三个提交目标；不升级 React 19 等破坏性大版本 |
| 文档治理 | 保留唯一入口、快照标记、历史归档和最小变更门禁 | 可形成独立批次 | 不自动纳入未受跟踪的理论研究文档 |

GATE-001 安全收敛实际删除的是一组没有生产消费者的预设 Diagnosis 抽象及其孤立测试，没有新增替代代码。分组专项验证为 38 passed、1 个既有 Starlette/httpx 警告。
## 3. 分阶段执行顺序

### 阶段 A：文档和仓库卫生（P0）

目标：建立文档唯一入口；归档被替代材料；清理本地 Python 缓存但不改变运行行为。

验收：

- `docs/README.md` 能导航到所有活动文档；
- 活动文档不再引用已删除的 `doc/knowledge/normalized/`；
- 归档文档不被活动代码导入；
- `git ls-files` 不包含 `__pycache__` 或 `.pyc`；
- 缓存清理后执行测试会重新生成缓存属于正常现象。

### 阶段 B：API 路由装配与基线保护（P1）

目标：`main.py` 仅暴露 ASGI app；`create_app()` 构建完整应用；v0/v1 各自有单一聚合入口；保持 URL、方法和 Schema 兼容。

验收：完整路由快照、`method + path` 无冲突、OpenAPI 可生成、`/health` 保留、关键 URL 无非预期变化、全量后端测试通过。

### 阶段 C：v0 生命周期与安全边界（P1/P2）

目标：先查明 v0 的鉴权、文件所有权、错误响应、状态存储和全部消费者，再决定迁移到新版本还是保留兼容层。

明确禁止“复制 v0 到 v1”。复制会制造第二套实现。正确路径是：确定 canonical service → 新版本只做契约适配 → 前端逐调用点迁移 → 设置弃用窗口 → 删除无消费者的旧路由。

第一轮必须解决：上传文件的访问控制、内部路径暴露、跨用户任务访问和重启行为说明。法律 Gold 不属于本阶段。

### 阶段 D：RAG 回退语义与可复现性（P1）

目标：让每次检索明确记录所用后端、索引版本、触发原因和配置；业务默认模式与 Benchmark 固定模式分离。

验收：

- 显式 `v3-only`、`v2-only`、`compatibility-only` 和受控 fallback 模式可配置；
- fallback 能区分空结果、能力不覆盖和异常，不吞掉未预期异常；
- 有效的 workflow rules、模板或其他非 `legal_grounding` 结果不会被误判为空；
- 业务消费者保留或持久化 `RetrievalManifest`；
- Benchmark 固定 backend/index/config，不把 fallback 混合结果当作同一 Baseline。

### 阶段 E：依赖注入与任务状态（P2）

目标：选择一个模块做 Router → Service → Settings 的显式注入试点；为 v0 任务网关定义可替换状态存储接口。不得一次迁移全部模块。

验收：试点模块无模块级可变单例、测试可独立覆盖依赖、运行设置不反向 import Router、状态后端契约有重启测试。

### 阶段 F：法域目录物理迁移（P3，暂缓）

只有在 API、RAG 和依赖边界稳定后，才按单模块迁移至 `backend/domains/{cn,eu,us}`。每次迁移保持模块 ID、公开路径、Schema、Trace 名称和前端 key 不变。

## 4. 单批执行记录模板

每个治理批次必须在实施报告或 PR 中填写：

```text
批次编号：
目标与非目标：
修改前 commit / dirty status：
事实证据与消费者：
修改文件：
兼容性影响：
验收命令与结果：
路由/Schema/输出差异：
回退条件与方式：
遗留问题：
文档同步位置：
```

## 5. 当前暂停条件

出现以下任一情况必须停止该批次并重新审计：公开 URL 或 Schema 出现非预期变化；法律规则结果改变但没有 Gold/专家确认；历史 Trace 或上传件来源不明；迁移要求同时修改三个以上业务模块；测试依赖外部模型而无法稳定复现；工作树中的用户文件与目标文件发生重叠。

## 6. 完成定义

“仓库规范化完成”不是所有版本号和目录名称消失，而是：每个活动入口有明确权威源；每个兼容层有消费者和退役条件；每次 fallback 可观测且可复现；生成物不进入源码；文档与代码差异能够被测试或治理记录及时发现。

## 7. GATE-001 分批提交与最终基线

| Commit | 单一目标 |
|---|---|
| `7e61dde` | FastAPI v0/v1 路由聚合、完整应用工厂与 104 条路由基线 |
| `e7dcb76` | Diagnosis 最新规则实现、领域事实模型与会话兼容层收敛 |
| `e6cd019` | UTC helper、Trace 时区和既有数据库时间契约适配 |
| `9af18b3` | RAG Facade 与业务检索调用迁移；不宣称 fallback/Manifest 治理完成 |
| `f3e4648` | 前端工具链、Node 版本和本地运行安全基线 |
| `7cb54f3` | 前端路由懒加载、错误恢复边界与测试 |
| `8c52d30` | 文档唯一入口、生命周期、归档与治理门禁 |

提交后最终验证：

- 后端：`uv run --frozen pytest -q` → 356 passed、1 个既有 Starlette/httpx 警告；
- 前端：`npm test` → 1 test passed；测试中的 `chunk load failed` 是主动验证错误边界的模拟异常；
- 前端：`npm run build` → 通过；SuperDesign chunk 506.40 kB 警告保留为后续独立性能事项；
- 仓库卫生：1,421 个受跟踪文件检查通过；
- `git diff 300d960..HEAD --check`：通过；
- 工作树仅保留未受跟踪的理论研究文档，未被任何治理提交纳入。

GATE-001 至此形成可回滚 Git 基线。下一阶段准入项为 `/api/v0` 安全与生命周期只读审计；在形成新的事实与测试计划前，不直接迁移或复制 v0 接口。

## 8. API-001：`/api/v0` 安全与生命周期只读审计（2026-07-15）

### 8.1 审计范围与结论

本批次仅检查路由、Schema、Service、文件解析、运行设置、前端消费者、测试和脚本，没有修改业务代码或公开契约。动态加载 `create_app()` 后确认 OpenAPI 可生成 102 个 path；`/api/v0` 共 7 条路由，FastAPI dependency 列表均为空。

| 路由 | 当前消费者 | 鉴权/所有权 | 状态 |
|---|---|---|---|
| `POST /api/v0/files/upload` | 前端 `module-adapter.ts`；v0 测试 | 无服务端鉴权；文件索引无用户字段 | 活动兼容入口，不能直接删除 |
| `POST /api/v0/tasks` | v0 测试、QA 脚本、历史 demo | 无服务端鉴权；`session_id` 只进入摘要 | 无当前前端调用，待迁移消费者后退役 |
| `GET /api/v0/tasks/{task_id}` | v0 测试、QA 脚本、历史 demo | 仅凭 `task_id` | 同上 |
| `POST /api/v0/tasks/{task_id}/cancel` | 路由基线；可由兼容客户端调用 | 仅凭 `task_id` | 同上 |
| `GET /api/v0/tasks/{task_id}/artifacts` | v0 测试、QA 脚本、历史 demo | 仅凭 `task_id` | 同上 |
| `GET /api/v0/artifacts/{artifact_id}/download` | v0 测试及返回的下载 URL | 仅凭 `artifact_id` | 同上 |
| `GET /api/v0/tasks/{task_id}/audit` | v0 测试、QA 脚本、历史 demo | 仅凭 `task_id` | 同上 |

`frontend/src/lib/module-adapter.ts` 虽发送 Bearer header，但后端路由不消费该 header，因此不能构成访问控制。前端还将上传响应中的物理 `path` 作为业务模块附件路径继续提交；这说明上传契约与 v1 业务输入存在真实耦合，不能把整个 v0 Router 直接移除或机械复制到 v1。

### 8.2 已确认问题与现有控制

| 编号 | 类型 | 事实证据 | 影响 | 认定 |
|---|---|---|---|---|
| V0-SEC-001 | 身份认证 | `v0_task_gateway/router.py` 7 个 endpoint 均未使用 `Depends(get_current_user)`；运行时依赖列表为空 | 未登录请求可上传、创建/查询/取消任务和下载产物 | 已确认，P0 |
| V0-SEC-002 | 对象级授权 | `_task_refs`、`_file_index`、`_artifact_index` 不保存 owner；访问只接收 ID | 知道或获得 ID 的调用者之间没有服务端隔离 | 已确认，P0 |
| V0-SEC-003 | 本地文件读取边界 | `_resolve_attachment_paths()` 对未知 ID 直接当文件系统路径；`_resolve_storage_uri()` 可返回原始 URI/路径；下游 `FileParser` 会读取受支持后缀 | 外部输入可越过上传注册表指向进程可读的本地文档 | 已确认，P0 |
| V0-SEC-004 | 上传资源控制 | `upload.file.read()` 一次性读入内存；无大小、扩展名、内容类型或内容校验 | 内存/磁盘耗尽与非预期文件落盘风险 | 已确认，P0 |
| V0-SEC-005 | 内部路径暴露 | 上传响应 `path`、artifact 响应 `file_path`；前端显式依赖上传 `path` | 暴露部署目录并固化不安全契约 | 已确认，P1；需先迁移消费者 |
| V0-SEC-006 | 错误信息 | `create_task` 将异常类名和原始异常文本作为 422 detail 返回 | 可能泄露文件路径或内部实现信息 | 已确认，P1 |
| V0-LIFE-001 | 状态持久化 | 网关三个索引和各模块 `InMemoryTaskManager._tasks` 均为进程内字典 | 重启后任务/文件 ID/产物 ID 失效；多 worker 状态不一致 | 已确认，P1/P2 |
| V0-ARCH-001 | 依赖方向 | `runtime_settings.py` 反向 import Router 的模块级 `service` 并修改内部 LLM client | 阻碍依赖注入、测试隔离和多实例治理 | 已确认，P2 |

现有控制也必须保留记录：上传文件名使用 `Path(...).name`，可阻断直接通过原始文件名进行的简单目录穿越；产物 ID 使用摘要而非直接路径；公共 v1 artifact API 已有允许根目录和数据库 owner 检查。上述控制不能抵消 v0 的鉴权、对象授权和原始路径问题。

### 8.3 生命周期事实

1. v0 上传是当前前端的活动依赖；v0 任务编排没有检出当前前端消费者，主要由 7 条兼容流程测试、`scripts/qa_v0_baseline.py`、`scripts/qa_v0_smoke.sh` 和 `scripts/legacy/demo_v0.sh` 使用。
2. `session_id` 不是安全主体，只被写入请求摘要；不得用它替代用户身份或对象所有权。
3. 上传文件本体在重启后仍可能留在磁盘，但内存 `file_id → path` 映射丢失；任务管理器和网关 task/artifact 索引同样不可恢复。
4. `runtime_settings.py` 仍直接持有 v0 Router 的模块级 Service，因此删除路由前必须先解除该运行时消费者。

### 8.4 分批修复门禁

本审计不准入“一次完成 v0 迁移”。后续必须拆为可独立回滚批次：

| 批次 | 单一目标 | 最小验收 | 非目标 |
|---|---|---|---|
| API-C0（已完成） | 恢复被历史清理误删但仍由活动代码引用的 2.2/4.1 报告模板，并消除模块测试对全局模板常量的污染 | v0 Assessment/CN Flow 可独立运行；全量与孤立执行结果一致；模板来源 commit/hash 可追溯 | 不修改模板法律内容；不与安全修复混合 |
| API-C1 | 给 7 条 v0 路由增加真实登录要求和对象 owner 绑定；拒绝未注册的本地路径 | 未登录 401；用户 A 不能读/取消/下载用户 B 资源；注册文件正常流转；现有 7 模块流程在带身份下通过 | 不改 URL；不迁移数据库；不建立 v1 副本 |
| API-C2 | 建立受控上传契约：允许类型、大小上限、分块写入、受控根目录、失败清理 | 超限/不支持类型被拒绝；路径越界测试通过；合法六类文档通过 | 不改文件解析算法 |
| API-C3 | 前端从物理 `path` 迁移到 opaque file reference；停止公开 `path/file_path` | 前端测试和构建通过；请求不再包含本地路径；OpenAPI 契约变更有迁移记录 | 不顺手改业务表单 |
| API-C4 | 迁移 QA/兼容消费者并缩减 v0 task Router | `git grep /api/v0` 仅剩经批准兼容项；路由基线明确删除项；全量回归通过 | 不复制实现到 v1 |
| API-C5 | 为任务/文件/产物元数据定义持久状态接口并解除 runtime settings 对 Router 的反向依赖 | 单 worker 重启恢复测试；多 worker 契约测试；依赖可覆盖 | 不一次迁移全部模块的异步执行器 |

API-C1 实施前还必须确定临时 owner 元数据的权威存储。若只把 owner 加入现有内存字典，只能作为单进程过渡控制，不能宣称支持重启恢复或多 worker。API-C3 会改变当前前端协议，必须独立实施，不能混入 C1。

### 8.5 当前验证偏差与下一准入项

本次专项重跑得到两组不同性质的结果：

- 路由装配测试在工作区可写的 `--basetemp` 下为 4 passed、1 个既有 Starlette/httpx 警告；默认临时目录的 `PermissionError` 属于当前执行环境限制，不是路由缺陷；
- v0 兼容测试孤立执行时，Assessment 因 `2.2_risk_assessment_template_v0.docx` 不存在而跳过 DOCX 输出，CN Flow 因 `4.1_cn_flow_compliance_template_v0.md` 不存在而失败；对应 2.2/4.1 的 md/docx 共 4 个文件曾存在于 Git，后被 `d6e882d` 删除，但活动代码引用未同步移除；
- CN Flow 模块测试直接赋值全局 `TEMPLATE_PATH` 而不恢复，存在测试顺序污染，可能掩盖缺失模板。此前“356 passed”仍是当时全量执行记录，但不能替代当前孤立失败事实。

因此下一批先准入 API-C0，而不是直接进入 API-C1。API-C0 只能从删除前可追溯 commit 恢复活动模板，并修复测试隔离；不得自行生成新的法律模板内容。API-C0 通过后，API-C1 必须先建立未登录、跨用户、未知文件引用和合法同用户流程四类回归测试。任何法律判断、报告正文、RAG 算法、Schema 全局重构和 `/api/v1` 复制均不属于这些批次。
### 8.6 API-C0 实施结果

API-C0 已按单一目标完成：从删除提交 `d6e882d` 的直接父版本 `3e09a3c594550ccef6c548b9aaea080b939f042e` 原样恢复 4 个活动模板；没有生成或修改模板法律内容。恢复文件的 SHA-256 为：

| 文件 | SHA-256 |
|---|---|
| `2.2_risk_assessment_template_v0.docx` | `5A5999F5EFFC4A3D17418759758B6A29211FF92154A71A03B15522C4085C1296` |
| `2.2_risk_assessment_template_v0.md` | `8423A2DEF41B43DC410B060A2AEC595E79432FB92560946A95A9CC45C3D46805` |
| `4.1_cn_flow_compliance_template_v0.docx` | `3A142CBD25EA1BD0470E391C685F423D7827A102CD01676A382FAC7563D55E58` |
| `4.1_cn_flow_compliance_template_v0.md` | `D3D40DAB150420BC9C187111EA74E4AA2782FD75CFA803F4DD5A53DF27BAD931` |

`backend/modules/cn_flow/tests/test_service.py` 与 `test_async_api.py` 改用 pytest `tmp_path` 和 `monkeypatch`，测试模板不再写入固定 `outputs/cn_flow/_test_templates`，模块全局模板路径会在测试后恢复。

验收结果：

- CN Flow 两项模块测试 + v0 Assessment/CN Flow 孤立流程：4 passed、1 个既有警告；
- 全量后端：356 passed、1 个既有 Starlette/httpx 警告；
- `git diff --check` 与仓库卫生检查通过；
- 全量测试新增的 52 个输出目录、1 个上传文件和 pytest 临时目录已清理。

API-C0 不改变 URL、Schema、法律规则或 Service 逻辑。下一准入项恢复为 API-C1；API-C1 仍须保持鉴权/owner/本地路径边界单一目标，不混入上传协议和状态持久化迁移。
