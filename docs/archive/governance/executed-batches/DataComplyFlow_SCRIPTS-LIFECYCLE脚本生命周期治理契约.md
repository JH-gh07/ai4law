# DataComplyFlow SCRIPTS-LIFECYCLE 脚本生命周期治理契约

## 1. 治理目标

本批只治理 `scripts/` 的入口身份和生命周期，不修改后端业务逻辑、RAG 算法、Benchmark 指标或 API 契约。

治理遵循“正确、简洁、再补强”：只有在代码引用、配置入口、文档命令和可执行条件均已核查后，才删除无消费者且已失效的脚本。

## 2. 权威分类

| 类别 | 定义 | 处置规则 |
| --- | --- | --- |
| active | 当前开发、构建、运行或仓库门禁的正式入口 | 保留在 `scripts/` 根目录并写入入口清单 |
| benchmark | 构造评测数据、运行评测或保存回归快照 | 保留在 `scripts/` 根目录；评测实现和数据仍归 `benchmarks/` |
| compatibility | 验证仍受支持的历史 API 契约 | 保留，但必须明确不是产品启动入口 |
| obsolete | 无现行消费者，且依赖已删除目录、环境或输出契约 | 删除；历史事实由 Git 和治理记录追溯 |

## 3. 修改前事实

- `scripts/` 共 26 个文件，其中 6 个位于 `legacy/`。
- `legacy/` 脚本引用已删除的 `app_streamlit/`、`doc/v2`、`doc/v3`、`.venv311` 或旧发布目录，不能在当前仓库按原命令运行。
- `eval_runner.py`、`eval_payloads.py` 和 `eval_checkers/` 没有被配置、测试、现行文档或其他代码调用；其读取的 `outputs/{module}/{run}/outputs` 旧产物布局也不是当前评测权威入口。
- `qa_v0_baseline.py` 虽有 `qa/baseline/` 数据集，但实跑 7 个模块全部发生 Markdown Hash 漂移，并受 LLM fallback 影响，不能作为确定性兼容门禁。
- `qa_v0_baseline.sh` 与 `qa_v0_smoke.sh` 固定调用 `.venv311`，且后者引用治理前的模块测试路径，属于失效包装器。
- `cloud_studio_start.sh` 仍由 `.vscode/preview.yml` 调用，属于 active。

## 4. 本批决策

### 保留

- 法规与索引构建：`build_regulation_articles.py`、`build_rag_vector_index.py`。
- Benchmark 数据构建：`build_rag_retrieval_dataset.py`、`build_rag_hard_negatives.py`。
- Benchmark 执行与快照：`run_smoke_benchmark.py`、`run_rag_retrieval_benchmark.py`、`snapshot_rag_retrieval_benchmark.py`。
- 开发与治理：`cloud_studio_start.sh`、`check_repository_hygiene.py`。

### 删除

- 整个 `scripts/legacy/`：文件均退出当前入口并依赖失效路径；保留目录本身会形成“似乎仍可启用”的错误信号。
- `eval_runner.py`、`eval_payloads.py`、`eval_checkers/`：无真实消费者，且已由 `benchmarks/` 的现行评测入口取代。
- `qa_v0_baseline.py`、`qa_v0_baseline.sh`、`qa_v0_smoke.sh`：旧基线实跑 7 个模块全部 Hash 不一致，且受 LLM fallback 影响；v0 兼容契约由 `backend/api/v0/tests/test_task_gateway.py` 和路由测试验证，不伪造或覆盖 expected 数据。

## 5. 不在本批修改

- `regulation_index_v2.json` 的文件名和运行时配置。它仍是 `backend/core/settings.py` 的真实默认索引，重命名属于后续 `storage/` 与 RAG 数据契约治理。
- v0 API 的保留或迁移。
- Benchmark 数据内容、Gold 合法性和指标设计。
- Cloud Studio 的部署策略。

## 6. 验收门禁

1. 剩余 Python 脚本全部通过语法编译。
2. 所有保留 CLI 的 `--help` 或等价只读入口可加载。
3. v0 兼容测试、RAG/知识构建相关测试和 Benchmark 测试通过。
4. `bash -n scripts/cloud_studio_start.sh` 通过（环境提供 Bash 时）。
5. 仓库卫生检查通过，且不存在对已删除脚本的活动引用。

## 7. 执行结果（2026-07-17）

- 修改前 26 个脚本文件收敛为 9 个活动命令文件和 1 份入口说明。
- 退役 17 个文件：旧离线评估器、无消费者 checker、失效 Shell 包装器、一次性知识迁移/入库脚本和旧 v0 基线。
- 活动代码与当前文档对退役脚本的引用为 0；历史说明仅保留在执行归档中。
- Python 脚本语法编译与保留模块导入通过；`run_smoke_benchmark.py --help` 通过。
- 相关回归测试：93 passed；覆盖 v0、路由、知识、RAG、资源路径和 Benchmark。
- 最终仓库卫生检查：通过，检查 1005 个仓库文件。
- `qa_v0_baseline.py` 实跑完成 7 个模块但 7 个 Hash 全部漂移，并因 SOCKS 依赖缺失使用 LLM fallback；未更新 expected，脚本据此退役。
- Bash 语法检查因当前 Windows 环境只有未配置发行版的 WSL 占位入口，标记为环境不可验证；`cloud_studio_start.sh` 仍由 `.vscode/preview.yml` 使用并保留。
- 本次实跑生成的 7 个输出目录和单次报告已按精确 task ID 删除；未清理既有 `storage/` 用户数据。
