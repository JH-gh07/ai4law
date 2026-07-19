# DataComplyFlow 目录结构与工程规范治理实施报告

## 1. 实施结论

本轮在不进行全量业务模块重写、不破坏 `/api/v0` 和 `/api/v1` 兼容契约的前提下，完成了目录卫生、法域模块标识、知识源单一化、AI 辅助开发规范和已确认历史资产归档。

最终验证：

- 后端全量测试：323 passed，0 failed，0 errors；
- 知识、Citation、RAG 和知识 API 回归：82 passed；
- 空存储 RAG v3 索引重建：通过；
- 前端 `npm run build`：通过，449 modules transformed；
- 仓库卫生检查：通过，1,396 个跟踪文件；
- `git diff --check`：通过。

本轮没有物理移动全部法域业务模块。当前采用“稳定模块 ID + 现有实现包兼容映射”，避免一次性修改数百处 import、API、前端 ModuleKey、Trace 和 Fixture。

## 2. 基线与备份

- 工作分支：`codex/repository-structure-governance-20260713`；
- 治理前提交：`6fc976a3b0d4c8a8dde6021bfdcfd04b1663073e`；
- 基线标签：`baseline/pre-structure-governance-20260713`；
- 本地备份：`.repo-backups/DataComplyFlow_pre_structure_governance_20260713.zip`；
- 备份大小：89.32 MB；
- SHA-256：`45002918CFCB51AD9034D236313B58A382F864B525D9FEFD88F2016D26AA6E58`。

备份目录已加入 `.gitignore`，不进入远程仓库。备份包含历史上传件、Trace 和配置，只能作为本机回退材料，不应公开分发。

## 3. 工程规范

新增 `docs/engineering/`，作为当前工程规范权威入口：

- `DataComplyFlow_AI辅助开发与代码规范.md`；
- `DataComplyFlow_活动架构与权威源.md`；
- `README.md`。

规范覆盖 API 到领域、RAG/LLM、Verifier 和存储的依赖方向，法域和模块命名，API、Schema、规则、Prompt、fallback、Trace、测试以及 AI 辅助代码的人工验收。

规范不承诺任何 AIGC 检测结果，也不采用机械改名或代码混淆。目标是减少模板化复制，使代码体现 DataComplyFlow 的领域设计和可追溯人工决策。

## 4. 法域与模块结构

治理早期曾新增 Python Catalog 作为稳定模块 ID 视图；该重复视图已在第 29 节退役，当前唯一权威源为 `config/module_registry.json`：

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

每项记录 jurisdiction、frontend_key、当前实现包、当前 `/api/v1` 前缀和未来 target package。新增 13 项测试验证 ID、前端 key、实现包和 API 前缀。

法律业务实现现已逐模块迁入 `backend/domains/{cn,eu,us}/`，API 兼容网关已归入 `backend/api/v0/`，历史 `backend/modules/` 在第 29 节完成退役。

## 5. `.gitignore` 与仓库卫生

根 `.gitignore` 现在覆盖：

- 任意层级 `node_modules`、`dist`、`build`、`.vite`、`*.tsbuildinfo`、coverage；
- Python cache、pytest、ruff、mypy、coverage；
- `.env.*`，但保留 `.env.example`；
- DB、SQLite WAL/SHM、Trace、报告、上传、草稿、RAG 生成索引；
- 前端实验临时目录；
- `.claude`、`.streamlit`、`.superpowers` 和个人 VS Code 设置；
- 日志、临时文件、操作系统元数据和本机备份目录。

`scripts/check_repository_hygiene.py` 同步扩展，防止运行资产、生成文件、旧知识路径、旧 `ai_engine` 和根目录历史文档再次进入 Git。

本轮不仅增加 ignore，还把已经被跟踪的文件从 Git 索引移除；本地副本仍保留。

## 6. 退出版本控制的资产

本轮从 Git 移除 1,014 个本地、运行或生成文件，包括：

- `frontend/tmp/` 模型比较脚本、运行 Trace、上传件和报告；
- `storage/traces/`、`reports/`、`uploads/`、`drafts/`；
- `storage/ai4law.db`；
- `storage/rag/` v2/v3 生成索引；
- `.claude/settings.local.json`；
- `.streamlit/config.toml`；
- `.superpowers/` 工具历史；
- `.vscode/settings.json`。

该提交净删除约 665,500 行。删除表示退出源代码版本控制，不表示本机备份和工作区运行数据被销毁。

## 7. 明确废弃项和历史归档

以下无活动 import 的资产迁入 `docs/archive/`，保留 Git 重命名历史：

- 根目录 `architecture.html`、`docknowledge.md`、`IMPLEMENTATION_VERIFICATION.md`、`planv0.md`；
- 旧 `ai_engine` Prompt/Schema；
- `doc/error/` 历史错误记录。

`docs/archive/README.md` 明确归档材料不是活动入口、运行配置或 Prompt 权威源。

前端删除由 TypeScript 编译产生、无代码引用的 `vite.config.js` 和 `vite.config.d.ts`。`tsconfig.node.json` 增加 `noEmit: true`，生产构建后确认两文件没有再次生成。

## 8. Streamlit 退役

当前活动系统为 FastAPI + React/Vite，活动代码没有 Streamlit import。本轮从 `pyproject.toml` 删除 Streamlit，联网更新 `uv.lock`，移除 `.streamlit` 配置跟踪，并将 FastAPI 标题更新为 `DataComplyFlow Backend`。锁文件同步移除了仅由 Streamlit 引入的传递依赖，后端全量测试通过。

## 9. 知识目录单一事实源

对旧、新目录完成哈希与主键覆盖核验：

- 旧 `sources.csv` 的 19 个 source ID 全部包含在新文件的 93 个 ID 中；
- 旧 source registry 的 15 个 ID 全部包含在新文件的 93 个 ID 中；
- 旧、新 practice cases 均为 12 个 case，旧 ID 无缺失；
- module catalog 文件哈希完全一致；
- `normalized` 的 schema 和 JSONL 与 `_registry` 对应文件哈希完全一致。

因此删除 `doc/knowledge/index/`、`registry/` 和 `normalized/`。当前唯一源为：

```text
doc/knowledge/_index/
resources/legal/registry/
doc/knowledge/_evaluation/
```

同步修改 `backend/common/knowledge/paths.py`、`builders_v2.py` 和 Citation loader，取消活动代码 fallback。

## 10. 治理过程发现并修复的 RAG Bug

移除生成索引后增加空存储回归测试，发现 `RetrievalOrchestrator` 从 `storage_dir/rag/v3` 读取，而构建器向 `rag_v3_dir` 写入。默认路径碰巧相同，但覆盖配置时会断链。本轮将 `settings.rag_v3_dir` 确立为唯一 v3 索引路径。

测试还发现 `builders_v2.py` 硬编码旧 `index/normalized` 路径。切换为 `_index/_registry` 后，知识与 RAG 回归 82 项通过。

## 11. 未执行的高风险迁移

以下项目仍保留，不能根据名称直接删除：

- `backend/api/v0/task_gateway`：前端文件上传和兼容测试仍调用；
- `doc/v2/assets/templates`：多个活动报告渲染器直接读取；
- `/api/v1` 模块路由：当前前端主调用契约；
- 两套 Diagnosis 契约：尚未完成输入、状态、报告和 handoff 对齐；
- RAG v2 服务：多个业务模块仍通过 `retrieve_regulations` 使用；
- `doc/tmp`：仍被 SCC、DPIA 等活动代码的设计注释引用，暂不处理；原 `doc/addition` 已于 2026-07-15 迁入 `resources/research/product-design-sources/`。

物理法域目录迁移应作为独立阶段，每次迁移一个模块并保留兼容测试。

## 12. 依赖审计

前端只读审计结果：

- npm vulnerability：1 low、4 moderate、1 high，共 6；
- React 当前 18.3.1，latest 19.2.7；
- React Router 当前 6.30.3，latest 7.18.1；
- Tailwind 当前 3.4.19，latest 4.3.2；
- Vite 当前 5.4.21，latest 8.1.4；
- TypeScript 当前 5.9.3，latest 7.0.2。

这些大版本升级可能包含破坏性变化。本轮没有执行 `npm audit fix --force`，也没有将依赖升级与目录清理混在同一提交。前端构建仍有单个 JavaScript chunk 超过 500 kB 的警告，应在独立性能优化批次处理。

## 13. 剩余测试警告

最终 125 条警告主要来自 Starlette TestClient/httpx 弃用提示、未注册的 `pytest.mark.slow` 和 SQLAlchemy 默认值使用 `datetime.utcnow()`。它们没有造成当前测试失败，但应作为独立技术债处理。

## 14. 回退方式

1. 回退单一提交；
2. 从 `baseline/pre-structure-governance-20260713` 创建恢复分支；
3. 从 `.repo-backups` 压缩包恢复未进入 Git 的本地运行材料；
4. 恢复前核对备份 SHA-256，不将备份直接推送到远程。

## 15. 最终状态与下一阶段

本阶段已实现工程规范、法域稳定标识、运行资产退出源代码控制、历史资产归档、Streamlit 退役、RAG 路径 Bug 修复和知识单一事实源。

下一阶段建议按独立提交推进：Diagnosis 双入口契约收敛、`/api/v2` 与 v1 兼容适配、逐模块法域目录迁移、RAG v2/v3 调用收敛、前端依赖安全升级与拆包、Benchmark Harness 骨架。

用户现有未跟踪文件 `docs/handoff/DataComplyFlow_理论前沿与DataComplyBench-CN研究基线_20260713.md` 未被修改或纳入本轮提交。

## 16. 后续安全修复与结构收敛实施结果

本节记录 2026-07-13 在前述治理基线之上继续完成的低风险修复。历史章节中的依赖和警告数量是修复前快照，以本节验证结果为当前状态。

### 16.1 前端依赖与开发服务器

- React Router DOM 升级到 6.30.4；
- PostCSS 升级到 8.5.10 以上的锁定解析版本；
- Vite 升级到 8.1.4，@vitejs/plugin-react 升级到 6.0.3；
- 默认开发服务器监听地址从 0.0.0.0 收紧为 127.0.0.1；
- scripts/cloud_studio_start.sh 仍通过显式 host 参数保留受控远程开发入口；
- 未执行强制 audit 修复；
- npm audit 从 6 个漏洞降为 0 个漏洞。

前端生产构建通过。路由级懒加载后，首屏主 JavaScript 从约 1,315.77 kB（gzip 375.39 kB）下降到约 289.40 kB（gzip 94.47 kB）。Workspace、SuperDesign、报告、证据和法规查看等页面成为独立 chunk。SuperDesign chunk 仍略高于 500 kB，属于后续局部拆分事项。

### 16.2 Diagnosis 契约与确定性规则边界

新增 backend/domains/cn/transfer_diagnosis/，作为中国数据出境路径诊断的法域领域层：

- `models.py` 定义实际接入规则流程的 `DiagnosisFacts`、路径枚举与事实来源；未被生产代码消费的 `DiagnosisDecision` 预设抽象已在 GATE-001 收敛中删除；
- adapters.py 显式映射会话 API 与模块 API 的两套字段和枚举；
- rule_engine.py 从模块 Service 中提取纯确定性规则表匹配器；
- 12 个决策树回归组合覆盖豁免、CIIO、重要数据、普通/敏感个人信息阈值、边界值和 unknown 默认路径；
- 模块 Service 已使用领域规则引擎；Agent 可辅助补全 unknown 事实，但其来源会被标记为 llm_inference，依赖该事实命中的规则结论降为中等置信度并强制人工复核。

本轮没有强行合并两套公开 API，也没有修改数据库中既有 JSON。当前会话 Service 与模块决策树在“紧急或法定义务场景同时达到高数量阈值”时存在结论优先级差异；在法律团队确认 Gold 前保留两者，不将任一结果静默认定为权威结论。

### 16.3 RAG 统一调用边界

新增 backend/common/rag/service.py：

- LegalRetrievalService 为业务模块和 Benchmark Adapter 提供稳定入口；
- 默认调用 `multi_index` 策略（实现为 `RetrievalOrchestrator`）；
- `single_index` 策略直接调用 `RegulationRAGService.retrieve`，`enriched_compatibility` 单独保留公共 `retrieve_regulations` 的兼容增强行为；二者按职责命名，不再按代码代际混称；
- 每次调用返回 RetrievalManifest，记录实际后端、模块、阶段、查询、法域、路径、top-k、命中数、索引 Schema 版本、真实 fallback 原因和耗时；显式选择兼容后端不再伪装成 fallback。

本轮没有批量修改现有模块，旧 retrieve_regulations 仍保留。后续可以按模块迁移并通过同一 Manifest 做 v2/v3 shadow 对比。

### 16.4 UTC、测试和兼容性

- 新增 backend/core/time.py；
- Trace 时间改为带 +00:00 的 timezone-aware ISO-8601；
- 既有 SQLAlchemy DateTime 字段继续写入 naive UTC，避免在没有生产数据库迁移的情况下改变存储契约；
- 注册 pytest slow marker；
- datetime.utcnow() 警告已清零；
- 后端全量测试为 351 passed, 1 warning；
- 唯一剩余警告是 Starlette TestClient/httpx 兼容弃用提示，不能通过未经验证地安装 httpx2 处理。

### 16.5 尚未在本轮实施

- API v2 公开契约及 v1 deprecation；
- SuperDesign 与 Workspace 的二级组件拆包；
- React 19、React Router 7、Tailwind 4、TypeScript 7；
- 生产数据库 timezone 字段迁移；
- 法域目录物理搬迁和 Legacy 模块删除。

这些事项均需要独立验收或法律 Gold，不应与本轮已通过测试的安全修复混成一次高风险改动。

### 16.6 2026-07-14 复核修正

本次复核不是新的架构迁移，而是对 16.2—16.4 中已发现风险的进一步收敛：

- 删除 Diagnosis 归一化中把用户显式 third_party 静默改写成 intra_group 的逻辑；
- DiagnosisResult 增加 fact_provenance、missing_facts 和 requires_human_review；
- 用户值、默认值、确定性派生值、估算值和 LLM 推断值不再统一标记为 user；
- q5_no_personal_info=yes 与个人信息、敏感个人信息或重要数据事实冲突时，自动结论被阻断并返回 manual_review；
- 规则表加载时拒绝未知条件键，避免字段拼写错误被静默忽略；
- 会话 API 的 hit_rules 作为说明文本进入 rule_explanations，不再冒充稳定规则 ID；
- RAG Facade 明确区分 v3、真实 v2 和兼容 API；该 Facade 仍未批量接入业务模块，状态仍为“已实现边界、部分接入”；
- 前端声明 Vite 8 所需 Node 版本 ^20.19.0 || >=22.12.0，新增 .nvmrc，并为懒加载路由增加中文错误边界和重载入口；
- 前端生产构建通过，npm audit 为 0；主入口 chunk 约 289.91 kB（gzip 94.68 kB），SuperDesign chunk 仍为 506.40 kB；
- 后端全量回归为 351 passed、1 个既有 Starlette/httpx 弃用警告；Diagnosis 领域与模块专项 27 passed，RAG Facade 专项 2 passed。

两套 Diagnosis 入口已按“模块版为最新权威实现”的工程决策统一；法律 Gold 改为最终评测与法规口径校验事项，不再阻塞代码收敛。

### 16.7 Diagnosis 收敛、RAG 业务迁移与最终验证

- 删除旧 `backend/services/diagnosis_service.py` 中的重复判断逻辑和已无引用的 `backend/data/diagnosis_citations.json`；
- 新增 `DiagnosisSessionService` 作为会话、报告、handoff 和数据库持久化兼容层，其判断统一委托给最新模块版 `DiagnosisService`；
- 保留 `/api/v1/diagnosis/sessions/*`、`DiagnosisSessionModel` 和 `DiagnosisRepository`，因为个人任务列表、项目历史删除和现有会话 API 仍真实依赖这些契约；
- Assessment、BCR、CN Flow、CPRA、DPIA、EU SCC、PIPIA、CN SCC、TIA、EO 14117 和通用 Review 已迁移至统一 RAG Facade；生产业务模块不再直接调用 `retrieve_regulations`；
- 真实回退链为 v3 Orchestrator → v2 `RegulationRAGService` → compatibility API，并在 Manifest 中记录实际后端、原因和总耗时；
- 前端增加 Vitest、Testing Library 和懒加载错误边界回归测试。

最终验证：后端 353 passed、1 个既有 Starlette/httpx 弃用警告；前端 1 test passed；前端构建通过；npm audit 为 0；`git diff --check` 通过。

后续更新（2026-07-19）：经人工确认，该目录仅为临时设计稿预览、不属于正式产品能力，已连同 `/superdesign/002` 路由、承载页面和专用 JSX 类型声明整体删除；来源审计记录保留在治理文档与 Git 历史中。

## 16.8 FastAPI 路由装配收敛

当前工作树已把版本路由装配集中到应用工厂：`backend/main.py` 仅暴露 `create_app()` 的结果；`backend/app.py` 统一挂载 `/api/v0` 和 `/api/v1`；`backend/api/v0/router.py`、`backend/api/v1/router.py` 分别聚合版本路由。公共 Diagnosis 会话契约与模块版 Diagnosis 业务接口均保留，完整 Method + Path 不冲突。

新增 `backend/api/tests/route_baseline.json` 和 `test_route_assembly.py`。基线包含 104 个显式 Method + Path：`/health` 1 个、v0 7 个、v1 96 个；测试覆盖完整应用、重复路由、operation ID、版本前缀、Diagnosis 兼容路径、lifespan、健康检查和 OpenAPI 生成。该变更属于路由组织与测试收敛，不改变业务处理函数、请求响应 Schema 或前端协议。
## 17. 2026-07-15 文档体系收敛

本批次仅治理文档，不修改业务逻辑：

- 新增 `docs/README.md`，作为文档唯一总入口；
- 新增 `docs/handoff/README.md`，区分事实快照、评测分析和当前实施记录；
- 新增 `docs/governance/DataComplyFlow_仓库规范化分阶段治理计划.md`，将缓存、API 版本、RAG 回退、依赖注入、任务状态和法域迁移拆成独立阶段；
- 修正治理入口中已经失效的 `doc/knowledge/normalized/` 权威路径；
- 将已被替代的旧治理方案、第一版实施报告和 2026-06 Superpowers 设计/计划移入 `docs/archive/`；
- 没有删除字节唯一的历史材料，也没有修改或提交未受跟踪的理论研究文档。

本节记录 2026-07-15 当时的文档分层。2026-07-19 收敛后，现行规范与治理知识资产统一以 `docs/standards/` 为准，有日期的事实报告以 `docs/handoff/` 为准，旧 `engineering/`、`governance/` 文档已移入 `docs/archive/governance/replaced-active-docs-20260719/`。

## 18. GATE-001 现有工作树收敛审查

2026-07-15 按路由、Diagnosis、RAG、通用基础设施、前端和文档六组审查当前工作树。治理原则是删除无消费者抽象、保留真实兼容边界、暂停无独立验收条件的扩改。

本批唯一业务源码收敛是删除未被生产代码消费的 `DiagnosisDecision`、`ConclusionSource`、`decision_from_module()` 及其孤立测试；实际主流程继续使用 `DiagnosisFacts`、`FactSource`、`DiagnosisPath`、`facts_from_module()` 和确定性规则引擎，没有新增替代层。

验证结果：分组专项 38 passed、1 warning；后端全量 356 passed、1 warning；前端 1 test passed；前端生产构建通过；仓库卫生与 `git diff --check` 通过。测试总数从 357 变为 356，原因仅为删除上述孤立测试，不是功能测试丢失。

RAG 组仅认定为“统一边界及业务迁移已接入”：多数消费者仍只取 `.documents`，Manifest 未形成完整业务审计链；issue-discovery 非 legal bundle、异常 fallback、后端固定配置和缓存刷新仍属于阶段 D，不得写成治理完成。前端依赖升级、懒加载和开发服务器安全也必须按不同提交目标审查。

## 19. `/api/v0` 安全与生命周期只读审计

2026-07-15 在 GATE-001 基线上完成只读专项审计，没有修改 Router、Service、Schema、前端协议或业务逻辑。

- 动态加载完整应用后，OpenAPI 正常生成 102 个 path；7 条 `/api/v0` 路由的 FastAPI dependency 列表均为空；
- 前端只直接调用 `POST /api/v0/files/upload`，虽发送 Bearer header，但后端不解析；上传响应中的物理 `path` 被继续传给 v1 业务模块；
- v0 task/status/cancel/artifacts/download/audit 没有检出当前前端调用，消费者为模块兼容测试、QA 脚本及历史 demo；
- 网关 `_task_refs`、`_file_index`、`_artifact_index` 不记录用户，任务和产物仅凭 ID 访问；
- 未注册的 attachment ID 会被当作本地文件路径，下游文件解析器可读取受支持格式；上传实现没有大小和类型控制，并一次性读入内存；
- 网关索引及底层 `InMemoryTaskManager` 都是进程内状态，重启和多 worker 行为不可持续；
- `runtime_settings.py` 仍反向 import Router 的模块级 v0 Service，是后续退役前必须解除的真实运行消费者。

最终认定：v0 不是应立即复制或整体删除的“旧版本”，而是含一个前端活动上传入口及一组测试/脚本兼容任务入口的安全债边界。专项验证还发现 2.2/4.1 共 4 个活动报告模板曾被历史提交 `d6e882d` 删除而代码引用仍保留；Assessment/CN Flow 的 v0 测试孤立执行失败，CN Flow 模块测试存在全局模板路径污染。下一批必须先做 API-C0：从可追溯历史恢复活动模板并修复测试隔离；通过后再进入 API-C1 的鉴权、对象 owner、拒绝未注册本地路径及相应回归测试。上传协议去物理路径、状态持久化和 v0 退役必须分别实施。完整证据、风险分级、验收与非目标记录在 `docs/archive/governance/replaced-active-docs-20260719/DataComplyFlow_仓库规范化分阶段治理计划.md` 第 8 节。

### 19.1 API-C0 活动模板恢复与测试隔离

按审计门禁完成独立的基线修复：从 `d6e882d^`（`3e09a3c594550ccef6c548b9aaea080b939f042e`）原样恢复 `doc/v2/assets/templates/` 下 2.2 与 4.1 的 md/docx 四个文件；其 SHA-256 已记录在分阶段治理计划 8.6 节。CN Flow 的同步和异步测试改用 `tmp_path + monkeypatch`，不再污染模块全局模板常量或固定输出目录。

孤立验证为 4 passed、1 warning；全量后端为 356 passed、1 warning。本批只恢复活动运行资产和测试隔离，不修改模板内容、业务 Service、API、Schema 或法律判断。测试新增的 52 个输出目录、1 个上传文件和 pytest 临时目录均已清理。


## 20. 资源路径与研究材料收敛

2026-07-15 按“运行资源与研究材料分离、先验证引用再移动”的原则完成低风险物理收敛：

- 新增 `backend/core/resource_paths.py`，集中定义项目根、当前知识库兼容位置和报告模板根；活动后端不再直接硬编码 `doc/knowledge` 或 `doc/v2/assets/templates`；
- 13 个活动报告模板按 `cn`、`eu`、`us` 迁入 `resources/templates/`，迁移前后 Git 对象 Hash 逐项一致；没有伪造仓库中缺失的 PIPIA 和 EO 14117 DOCX 模板；
- 原 `paper/` 的 14 个文件迁入 `resources/research/papers/`，原 `doc/addition/` 的 28 个文件迁入 `resources/research/product-design-sources/`；42 个文件迁移前后 Git 对象 Hash 逐项一致；
- `resources/research/README.md` 明确研究材料不是法规、Prompt、模板、Fixture 或运行配置入口；路径测试阻止活动后端读取该目录；
- `doc/tmp` 因仍被 SCC、DPIA 等活动源码的设计注释引用而保留；`docs/archive/` 因承担历史追溯且仍被现行文档链接而保留；`doc/开发文档/` 本批只完成无运行消费者认定，未与资源迁移混合删除。

本批验证：资源路径及 EO 14117 报告相关测试 38 passed；仓库卫生检查通过（1,368 个已跟踪文件）；`git diff --check` 通过。研究材料移动不改变业务代码、知识索引、API、Schema 或报告内容。
## 21. DOC-ROOT 第一批：活动知识资源与评测数据迁移

2026-07-16 依据 `DataComplyFlow_DOC-ROOT文档与知识资源收敛执行契约.md` 完成第一批物理收敛：

- 472 个 `doc/knowledge/` 文件迁入 `resources/legal/`，迁移前后 SHA-256 集合一致；
- 原 `_evaluation/` 独立为 `benchmarks/datasets/retrieval/`，原 `_index/`、`_registry/` 分别更名为 `catalog/`、`registry/`；
- 活动资源根和评测数据根由 `backend/core/resource_paths.py` 统一提供；
- 知识 builder、RAG 评测脚本、前端开发用例和当前治理文档已切换到新路径；
- 删除无消费者的 `scripts/migrate_knowledge_base.py`，QA 结果改写入 `outputs/benchmarks/`；
- `doc/knowledge/` 已不存在，但 `doc/` 根目录尚未删除，剩余 130 个文件（含此前统计遗漏的根目录 12 个文件）必须在下一批按现行文档、历史材料、运行资产、法律资产和测试资产分类。

本批验证：专项 88 passed；后端六组回归共 376 passed；前端 5 passed；前端生产构建成功；仓库卫生检查通过。条款注册表仍有 12 个只存在于 `regulation_articles.jsonl` 的历史 source ID 指向缺失的 `doc/v3` 快照，因权威来源注册缺失而未猜测修复，已列入下一阶段数据完整性事项。
## 22. DOC-ROOT 第二批：消除历史 `doc/` 根目录

2026-07-16 完成剩余资产的逐文件 Hash 审计与分类。执行前 `doc/` 真实包含 130 个文件；先前 118 的数字只统计了三个子目录，遗漏根目录 12 个文件，本节以备份复核结果纠正。

- 65 个法规或模板副本已有相同 SHA-256 的权威副本，删除后不损失内容；
- 24 个唯一案例和功能说明原件按 `cn/eu/us/shared` 迁入 `benchmarks/source-materials/`，明确标记为待清洗、待专家标注的来源材料而非 Gold；
- 40 个唯一历史开发记录、系统说明和模块设计依据迁入 `docs/archive/legacy-*`；
- 1 个空 Markdown 删除；
- 活动源码注释和前端开发用例引用已同步到新路径；
- 顶层 `doc/` 已不存在，卫生检查已将整个 `doc/` 设为禁止跟踪和禁止活动引用的路径。

迁移后从备份复核全部 130 个内容 Hash，缺失为 0；64 个迁移文件全部可回溯到备份。验证结果：后端 376 passed；前端 5 passed；前端生产构建成功；仓库卫生检查和 `git diff --check` 通过。本批没有修改业务判断、API、Schema、Prompt、RAG 算法或法律内容。
## 23. 美国法域模块物理收敛

2026-07-16 将 CPRA 与 EO 14117 从 `backend/modules/` 迁入 `backend/domains/us/`，新权威实现包分别为 `backend.domains.us.cpra` 和 `backend.domains.us.eo14117`。旧包已删除且未保留兼容转发层。

41 个源文件在反向归一化 import 后逐项一致；路由基线只改变 8 个 endpoint module，HTTP 方法、URL、route name 和 operation ID 不变。权威模块注册表、Router、运行配置注入、v0 兼容网关、模块目录和跨模块引用均已更新。测试公共鉴权 fixture 从 `backend/modules/conftest.py` 提升到 `backend/conftest.py`，仅修正 pytest 目录继承范围。

验证结果：迁移前后专项均为 63 passed；后端完整分组回归 376 passed；前端 5 passed；生产构建成功；仓库卫生检查扩展为覆盖已跟踪和未暂存文件后通过。本批没有修改业务逻辑、API、Schema 字段、规则、Prompt、RAG 或数据库。
## 24. 欧盟法域模块物理收敛

2026-07-16 将 EU SCC、BCR、DPIA、TIA 从 `backend/modules/` 迁入 `backend/domains/eu/`，权威包分别为 `scc_review`、`bcr_review`、`dpia` 和 `tia`。旧目录已删除且未保留兼容转发层。

98 个源文件反向归一化 import 后逐项一致；欧盟 16 条路由仅 endpoint module 改变，HTTP 方法、URL、route name 和 operation ID 不变。权威注册表、Router、运行设置注入、v0 兼容网关及测试均已更新。迁移前后专项均为 62 passed；后端完整回归 376 passed；前端 5 passed；生产构建成功；104 条路由无重复 Method+Path。

本批没有修改业务逻辑、Schema 字段、规则、Prompt、RAG、数据库或前端协议。EU SCC/TIA 复用美国 CPRA Citation DTO 的耦合已记录，但未在目录迁移中顺带重构。
## 25. 中国法域第一批模块物理收敛

2026-07-16 将安全评估、PIPIA 和中国 SCC 从 `backend/modules/` 迁入 `backend/domains/cn/`，权威包分别为 `security_assessment`、`pipia` 和 `scc_review`。旧目录已删除且未保留兼容转发层。

81 个源文件反向归一化 import 后逐项一致；中国模块 12 条路由只改变 endpoint module，HTTP 方法、URL、route name 和 operation ID 不变。权威注册表、版本 Router、运行设置注入、v0 兼容网关、模块目录与跨模块引用已更新。迁移前后专项均为 96 passed；后端完整回归最终为 376 passed；前端 5 passed；生产构建成功；104 条路由无重复。

全量后端首轮曾出现知识搜索用例 1 次非确定性失败，单测复跑和第二次全量均通过，已作为测试共享状态风险记录，不与本批物理迁移混同。本批未处理 Diagnosis 双层结构；`cn_flow` 经注册表确认属于美国 EO 14117 兼容流，也未迁入中国法域。
## 26. 中国路径诊断实现包物理收敛

2026-07-16 将分散于 `backend/domains/cn/transfer_diagnosis/` 与 `backend/domains/cn/transfer_diagnosis/` 的同一诊断实现收敛到后者。迁移前领域适配器反向依赖模块 Schema，而模块 Service 又依赖领域规则核心；迁移后 Schema、Service、Router、Renderer、Agents、规则表与测试均位于唯一权威包，旧实现目录已删除。

备份中的 20 个非重复文件归一化 import 后内容一致，重复的空包入口删除；唯一必要测试调整是让迁入 `tests/` 的规则测试从权威包读取 `decision_tree.json`。模块注册表、Router、运行设置、Diagnosis Session Service、Assessment 消费者与测试引用已同步。

专项迁移前后均为 44 passed；后端完整回归 376 passed；前端 5 passed，生产构建成功。104 条路由无新增、删除或重复，只有 `/api/v1/diagnosis/evaluate` 与 `/api/v1/diagnosis/report` 的 endpoint module 改变。公共会话型 Diagnosis API 完整保留，本批没有修改 Schema、规则、法律结论、Prompt、数据库或前端协议。
## 27. EO 14117 兼容流物理归位

2026-07-16 对历史 `cn_flow` 与完整 `us_14117` 实现完成差异审计。前者是较轻量的对华数据流风险审查，使用 8 个 `CNFlow*` Schema、4.1 模板及独立输出；后者具有 13 个 `US14117*` Schema、规则引擎、5 个 Agent、4.2 模板和交通灯结论。两者不是可直接合并的重复代码。

本批将兼容流从 `backend/domains/us/eo14117_flow_review/` 迁入 `backend/domains/us/eo14117_flow_review/`，10 个文件归一化 import 后逐项一致。module ID `us.eo_14117_flow_review`、frontend key `cn_flow`、任务模板、Trace 标识和 `/api/v1/cn-flow` 接口保持不变；注册表当前包和目标包已经统一。

迁移前后专项均为 52 passed；后端完整回归 376 passed；前端 5 passed，生产构建成功。104 条路由无新增、删除或重复，兼容流四条路由只改变 endpoint module。本批没有修改业务逻辑、法律判断、Schema、Prompt、RAG、模板、输出协议或完整 EO 14117 模块。
## 28. v0 任务网关 API 层物理归位

2026-07-16 将 `v0_task_gateway` 从业务模块目录迁入 `backend/api/v0/task_gateway/`。审计确认该包负责上传、统一任务创建、状态、产物、下载和审计封装，并将 v0 请求适配到七个下游法域模块，属于 API 兼容适配层而非法律业务模块。

5 个文件归一化 import 后逐项一致；`backend/api/v0/router.py`、运行设置注入和路由基线已更新。迁移前后专项均为 11 passed；后端完整回归 376 passed；前端 5 passed，生产构建成功。104 条路由无新增、删除或重复，7 条 v0 路由只改变 endpoint module。

本批没有复制 v0 到 v1，也没有修改上传、任务、Schema、状态、产物或前端协议。此前确认的鉴权、owner、本地路径、上传资源控制、内存状态和 Router 单例注入问题继续按 API-C1 至 API-C4 独立治理。
## 29. 重复 Module Catalog 与历史 modules 目录退役

2026-07-16 审计确认 `backend/modules/catalog.py` 没有生产消费者，仅被自身测试导入；其 12 条 `ModuleDefinition` 与 `config/module_registry.json` 重复，且 JSON 还包含 task template、lifecycle 和 note。将该副本原样迁入 Core 会延续双重事实源，因此本批直接退役 Python Catalog。

新增 `backend/core/tests/test_module_registry.py`，直接读取 JSON 权威源并验证 ID/frontend key 唯一性、法域、API prefix、生命周期、迁移目标及 12 个 implementation package 的可导入性。旧 Catalog、测试和 README 删除后，`backend/modules/` 已完全退出并加入卫生禁止路径。

原 Catalog 专项为 17 passed；新注册表与路由专项为 19 passed，其中注册表测试 15 项。后端完整回归为 374 passed；相对此前 376 减少 2 项，是将“未知 ID”“JSON 对照”等重复 Catalog 断言合并到直接权威源验证，不是业务能力测试丢失。前端 5 passed，生产构建成功；API 路由未发生变化。本批没有修改任何模块身份、API、Schema 或业务逻辑。

## 31. 结构治理收口复核（2026-07-17）

本轮以当前检出代码和回归结果覆盖报告中的早期路径描述。

### 31.1 当前活动结构

- 后端：`backend/api/`（版本与公共接口）、`backend/domains/{cn,eu,us}/`（法域业务）、`backend/common/`（公共能力）、`backend/core/`（配置与运行基础设施）；
- 前端：`frontend/src/`；
- 模块身份：`config/module_registry.json`；
- 运行资源：`resources/legal/`、`resources/templates/{cn,eu,us}/`；
- Benchmark：`benchmarks/`；
- 文档：唯一根 `docs/`，历史材料仅在 `docs/archive/`；
- 本地产物：`outputs/` 与 `storage/{rag,reports,traces,uploads}/`，均不作为源码权威源。

原 `doc/`、`paper/`、`ai_engine/`、`backend/modules/` 已退出活动结构。目录卫生检查会阻止旧 `backend/modules/` 重新出现。

### 31.2 RAG 本轮结论

RAG 的三类真实职责没有被错误合并。统一 Facade 的运行策略已改为 `multi_index`、`single_index` 与 `enriched_compatibility`；持久化索引的 `v2` 文件名和 `v3.1` Schema 仍代表真实数据格式，继续保留。专项测试 20 项通过，全量后端 374 项通过。

第三层兼容增强调用内部可能重新尝试本地检索，但它同时承担可选外部法律服务补充；现有业务大多只消费文档而未完整持久化 Manifest。缺少运行 Trace 统计时，直接删除该层会改变失败场景行为，因此列入后续可观测性与 Fallback 专项，不在结构治理中处理。

### 31.3 验收与剩余边界

- 后端：`374 passed, 1 warning`；
- 前端：`5 passed`，生产构建成功；
- RAG 专项：`20 passed`；
- 仓库卫生：`1377 repository files checked`，通过；
- `git diff --check`：通过；
- 运行生成的 RAG pytest 临时目录与 Python `__pycache__` 已清理；根 `.pytest_cache` 因当前文件系统拒绝访问而仍存在，但已被 `.gitignore` 排除，不属于源码。

当前不能完成 staging/commit/tag：执行环境对 `.git` 为只读。正式 Git 收口必须在可写环境中完成 rename 识别、分批提交和最终 tag；在此之前不得继续叠加无关结构变更。
## 32. Docs 活动文档与历史归档收敛（2026-07-17）

本节记录 2026-07-17 当时的四类文档结构。2026-07-19 已进一步将活动规范和治理知识合并到 `docs/standards/`，并将被替代文档移入 `docs/archive/governance/replaced-active-docs-20260719/`；已完成批次仍位于 `docs/archive/governance/executed-batches/`。

旧系统讲解、旧开发记录、旧测试报告、旧 Superpowers 计划、旧 Prompt/Schema 和历史 UI 二进制文档共 51 个文件已删除。12 份设计来源材料作为代码与业务构想的 provenance 全部保留，并统一放入 `docs/archive/design-provenance/`；其中 8 份无扩展名文本补充 `.md`，27 个 Python 文件中的 28 行引用只更新文档路径，没有业务行为变化。

治理后 `docs/` 从 93 个文件、约 3.65 MB 收敛为 47 个文件、约 0.73 MB。活动 Markdown 本地断链为 0，旧设计路径引用为 0；仓库卫生检查、SCC/DPIA Python 编译及 28 项定向测试通过。