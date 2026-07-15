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

新增 `backend/modules/catalog.py`，定义 11 个稳定模块 ID：

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

`backend/modules/README.md` 明确当前目录是兼容实现位置。后续可以逐模块迁往 `backend/domains/{cn,eu,us}/`，但不能绕过注册表新增另一个顶层模块。

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
doc/knowledge/_registry/
doc/knowledge/_evaluation/
```

同步修改 `backend/common/knowledge/paths.py`、`builders_v2.py` 和 Citation loader，取消活动代码 fallback。

## 10. 治理过程发现并修复的 RAG Bug

移除生成索引后增加空存储回归测试，发现 `RetrievalOrchestrator` 从 `storage_dir/rag/v3` 读取，而构建器向 `rag_v3_dir` 写入。默认路径碰巧相同，但覆盖配置时会断链。本轮将 `settings.rag_v3_dir` 确立为唯一 v3 索引路径。

测试还发现 `builders_v2.py` 硬编码旧 `index/normalized` 路径。切换为 `_index/_registry` 后，知识与 RAG 回归 82 项通过。

## 11. 未执行的高风险迁移

以下项目仍保留，不能根据名称直接删除：

- `backend/modules/v0_task_gateway`：前端文件上传和兼容测试仍调用；
- `doc/v2/assets/templates`：多个活动报告渲染器直接读取；
- `/api/v1` 模块路由：当前前端主调用契约；
- 两套 Diagnosis 契约：尚未完成输入、状态、报告和 handoff 对齐；
- RAG v2 服务：多个业务模块仍通过 `retrieve_regulations` 使用；
- `doc/tmp` 和 `doc/addition`：存在设计引用、研究价值或来源待确认。

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
- 默认调用 RetrievalOrchestrator v3；
- legacy_v2 Adapter 直接调用 RegulationRAGService.retrieve，compatibility_api 单独保留旧 retrieve_regulations 行为；两者不再混称为 v2；
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

仍未删除 frontend/src/integrations/superdesign002/：它存在活动路由和治理来源记录，不属于已确认旧冗余资产。其 506.40 kB 独立 chunk 需在确认生成式 UI 的长期产品地位后再拆分或退役。

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

此后，现行规范以 `docs/engineering/` 为准，执行顺序以 `docs/governance/` 为准，有日期的事实报告以 `docs/handoff/` 为准，`docs/archive/` 只用于追溯。

## 18. GATE-001 现有工作树收敛审查

2026-07-15 按路由、Diagnosis、RAG、通用基础设施、前端和文档六组审查当前工作树。治理原则是删除无消费者抽象、保留真实兼容边界、暂停无独立验收条件的扩改。

本批唯一业务源码收敛是删除未被生产代码消费的 `DiagnosisDecision`、`ConclusionSource`、`decision_from_module()` 及其孤立测试；实际主流程继续使用 `DiagnosisFacts`、`FactSource`、`DiagnosisPath`、`facts_from_module()` 和确定性规则引擎，没有新增替代层。

验证结果：分组专项 38 passed、1 warning；后端全量 356 passed、1 warning；前端 1 test passed；前端生产构建通过；仓库卫生与 `git diff --check` 通过。测试总数从 357 变为 356，原因仅为删除上述孤立测试，不是功能测试丢失。

RAG 组仅认定为“统一边界及业务迁移已接入”：多数消费者仍只取 `.documents`，Manifest 未形成完整业务审计链；issue-discovery 非 legal bundle、异常 fallback、后端固定配置和缓存刷新仍属于阶段 D，不得写成治理完成。前端依赖升级、懒加载和开发服务器安全也必须按不同提交目标审查。
