# DataComplyFlow 仓库治理与代码优化实施报告（2026-07-13）

> 实施范围：基于三份事实审计，对明确 P0/P1 项进行可回滚治理；未执行高风险架构重写。  
> Pre-governance tag：`baseline/datacomplyflow-pre-governance-20260713` → `d388d44243dc08a4e8f7d6344e1758386f3c4b8d`  
> 完整测试对应代码 HEAD：`bf30528`（本报告提交前）  
> 分支：`new`

## 1. 结果摘要

本轮将测试基线从：

```text
290 passed, 18 failed, 17 errors, 133 warnings
```

提升为：

```text
309 passed, 0 failed, 0 errors, 125 warnings
```

最终命令：`uv run --frozen pytest -q`；Python 3.13.3；耗时 138.03 秒。

前端执行 `npm ci && npm run build` 成功：TypeScript build 与 Vite production build 通过，449 个模块完成转换。构建产物未纳入 Git。

相对 pre-governance tag，报告提交前共有约 **1,788 个文件发生治理变化、418 行新增、605,823 行删除**。主要删除量来自重复前端快照、前端运行副本、Trace/索引副本和字节重复 evaluation 目录，不是删除活动业务模块。

## 2. 已完成治理

### 2.1 基线与可回滚性

- 三份事实审计已提交；
- 创建 annotated pre-governance tag；
- 清理、Legacy、安全、Bug、测试契约、evaluation 和治理文档分别提交；
- 每个关键模块修复可以独立回滚或 cherry-pick。

安全注意：pre-governance tag 和既有 Git 历史位于凭据移除之前，**不得直接推送到公开仓库**。外部凭据必须轮换；如需公开历史，须另行审批历史重写方案。

### 2.2 明确生成物与重复资产

已移除：

- `frontend/.codex-archives/`：135 个无活动引用快照；
- `.vite/`、`.DS_Store`、Python bytecode、Superpowers 本地 server state；
- `frontend/storage/`：1,599 个前端运行副本、索引、数据库和 Trace；
- `frontend/tmp` 中确认包含旧运行配置凭据的单个快照；
- 字节完全一致的 `doc/knowledge/evaluation/`，活动评测统一到 `_evaluation/`。

已新增 ignore：本地 runtime settings、frontend storage、root traces/reports/uploads/database、缓存与 bytecode。既有 root `storage/traces/` 等受跟踪历史资产暂未批量删除，以免未经 provenance 复核丢失 Benchmark 种子。

### 2.3 活动入口与 Legacy

- README 已改为 FastAPI + React/Vite 当前入口；
- 指向不存在 `app_streamlit/`、`doc/v3/`、`doc/v2/plan.md` 或 `.venv311` 的历史脚本移动到 `scripts/legacy/`；
- Legacy README 明确禁止把这些脚本用于当前启动、发布和知识入库。

### 2.4 安全配置

- 删除 `backend/core/runtime_settings.py` 中内嵌比赛 API 凭据默认值；
- 删除受跟踪 `storage/runtime_settings.json` 及前端副本；
- 新增无密钥 `storage/runtime_settings.example.json`；
- 增加回归测试，确认无环境变量时 DeliLegal 不会被内嵌凭据启用；
- 新增 `scripts/check_repository_hygiene.py`，阻止确定性的 runtime/generated/credential 模式重新进入 Git；当前 2,409 个受跟踪文件检查通过。

本地 JSON 运行配置仍是明文文件，只是已被 ignore。生产和比赛部署应改用环境变量或受管 secret store，并限制本地文件权限。

## 3. 已修复 Bug 与契约

| 项目 | 修复 | 验证 |
|---|---|---|
| 中国 SCC | 增加缺失 `uuid` import，恢复报告主链 | SCC service tests 通过 |
| CN Flow | 接受公共 Pipeline 的 `per_issue_rag` 与 renderer `context_pack` 参数 | service/async/v0 通过 |
| Assessment Prompt 测试 | Fake LLM 对齐 `chat_with_metadata` 真实接口 | prompt context 测试通过 |
| Assessment Retriever 测试 | 隔离 v3 orchestrator，测试只验证 query/fallback 契约 | 目标测试通过 |
| v0 DPIA | 显式适配 legacy 字段到当前 DPIARequest；字符串风险/措施结构化 | v0 DPIA flow 通过 |
| DPIA 输出 | 增加实际 DOCX 交付并进入 ZIP | artifact contract 通过 |
| Knowledge Review | `_get_db()` 改为 generator，关闭 Session 并 dispose engine | 原 17 个 Windows teardown errors 清零 |
| Async API tests | 使用依赖覆盖提供已认证用户，保持生产鉴权不变 | 6 个原 401 测试通过 |
| DPIA async state | 测试接受真实并发初始状态 CREATED/RUNNING | 异步测试稳定通过 |
| RAG evaluation | `backend/common/rag/eval.py` 使用 `NEW_EVALUATION_DIR` | RAG 目标测试 15 passed |

## 4. 测试证据

### 4.1 分层验证

- 安全与主要 P1 首轮：`38 passed`；
- RAG/evaluation：`15 passed`；
- 六个鉴权 async flows：`6 passed`；
- 最终全量：`309 passed, 125 warnings`。

### 4.2 前端验证

- `npm ci`：按现有 lock 安装 234 packages；lock 文件未改变；
- `npm run build`：TypeScript 与 Vite 构建成功；
- 产物：CSS 约 242 KB，主 JS 约 1.316 MB（gzip 约 375 KB）；
- Vite 提示主 chunk 超过 500 KB，后续应独立做 route/module code splitting。

### 4.3 仍有 warnings

- Starlette TestClient/httpx2 迁移提示；
- `pytest.mark.slow` 未注册；
- SQLAlchemy 模型仍使用 `datetime.utcnow()`；
- npm audit：1 low、4 moderate、1 high。

warnings 不影响本轮通过结论，但应建立单独依赖与兼容性升级批次，不能与法律算法修改混合。

## 5. 软著与 AIGC 治理

新增：

- `docs/governance/README.md`：活动代码、Legacy、运行物和权威源边界；
- `docs/governance/软件著作权与代码来源治理.md`：来源台账 Schema、初始资产分类、人工复核模板和申报候选门禁；
- `scripts/check_repository_hygiene.py`：可重复的源码卫生检查。

本轮对所谓“AIGC 降重”的处理原则是：

1. 不做机械变量改名、同义替换、无意义拆分或冗余代码注入；
2. 用需求、规则建模、Schema、测试、Benchmark、代码评审与 commit 过程证明独立工程表达；
3. 对 AI 辅助变更保留披露，要求权利人逐项理解、修改/接受并签署人工复核记录；
4. 生成式 UI、外部模板、法规译文、论文和开源依赖单独确认权利基础，不混入自研代码主张；
5. 软著可登记性、权利归属和材料口径最终由权利人及专业机构确认。

## 6. Commit 清单

| Commit | 单一目标 |
|---|---|
| `d388d44` | 冻结三份审计基线 |
| `9a03cdb` | 删除受跟踪生成物和无引用前端快照 |
| `e918dad` | 隔离失效入口脚本 |
| `09a396e` | 移除受跟踪运行凭据和前端运行副本 |
| `78a5ee2` | ignore 本地运行产物 |
| `7fd0114` | 修复 SCC 报告生成 |
| `99374b7` | 对齐 CN Flow Workflow callback |
| `676278e` | 修正 Assessment 测试隔离 |
| `e1723c3` | v0 DPIA 适配和 DOCX 交付 |
| `c9be73e` | 释放 Knowledge Review 数据库资源 |
| `09e9275` | `_evaluation` 成为 canonical 路径 |
| `2ff3d7a` | 建立来源/软著/AIGC 治理资产 |
| `bf30528` | 修正 async API 鉴权测试契约 |

## 7. 未实施与保留风险

为避免高风险混改，本轮未实施：

- Git 历史重写或远端密钥撤销；
- 两套 diagnosis API 合并；
- RAG v2 删除或 v3 全法域迁移；
- 全模块 Fact/Issue/Evidence/Claim 统一；
- 全量 Workflow/Prompt 重写；
- `ai_engine` 删除；
- root `storage/traces/reports/uploads` 的批量删除或 Benchmark fixture 化；
- CN Flow 与 EO 14117 命名/法域最终产品决策；
- Benchmark Harness 实现。

仍需人工优先处理：

1. 立即撤销/轮换曾进入 Git 的所有 API 凭据；
2. 决定是否对共享 Git 历史做敏感数据清理，并协调所有 clone；
3. 审核 root storage、uploads、reports、Trace 的数据所有权和敏感性；
4. 处理 npm high vulnerability，不使用未经评估的 `--force` 升级；
5. 完成第三方依赖许可证、SuperDesign 生成式 UI 条款、模板与法规译文来源确认；
6. 由项目权利人对本轮 AI 辅助 commits 做人工 diff review 并签署接受记录。

## 8. 下一批建议

按独立 commits 继续：

1. `security(deps)`：npm/Python 依赖漏洞与许可证清单；
2. `perf(frontend)`：路由级动态加载和 vendor chunk 拆分；
3. `qa(benchmark)`：新增 `qa/benchmark/` Case/Adapter/Runner/Metric/Manifest 骨架；
4. `docs(prompt)`：只登记 Prompt registry，不重写 Prompt；
5. `test(diagnosis)`：两套 diagnosis 对照契约与 deprecated 标记；
6. `data(provenance)`：将经脱敏、授权的历史 Trace 转成 fixture，其余移出 Git；
7. `release`：人工复核后创建软著候选版本 tag 和 release manifest。

## 9. 工作树说明

报告形成时仅保留一份本轮开始后出现、未纳入任何 commit 的用户/其他任务文档：

`docs/handoff/DataComplyFlow_理论前沿与DataComplyBench-CN研究基线_20260713.md`

本轮没有修改、删除或提交该文件。
