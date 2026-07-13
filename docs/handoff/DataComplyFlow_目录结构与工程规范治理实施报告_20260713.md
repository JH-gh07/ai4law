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
