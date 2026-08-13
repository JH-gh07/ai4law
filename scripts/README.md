# Scripts

`scripts/` 只保存当前可执行的仓库级命令入口。业务实现归 `backend/`，评测实现与数据归 `benchmarks/`；脚本只做参数解析、调用编排或可重复的数据构建。

## 当前入口

| 用途 | 命令 | 输出或效果 |
| --- | --- | --- |
| 生成法规条款数据 | `uv run --frozen python scripts/build_regulation_articles.py` | 更新法规条款 JSONL |
| 重建 EO 14117 条文 | `uv run --frozen python scripts/reingest_us_fed_001.py --dry-run` | 从离线快照校验 `US-FED-001` 的 28 CFR Part 202 精确条号；显式加 `--refresh` 才访问 eCFR |
| 构建本地 RAG 索引 | `uv run --frozen python scripts/build_rag_vector_index.py` | 更新当前配置使用的本地索引 |
| 区域法域源码对账 | `uv run --frozen python scripts/reconcile_regional_sources.py [--write] [--check]` | 对账 51 个区域法域 PDF 与 sources.csv `snapshot_path`，可选回写 |
| 构造检索数据集 | `uv run --frozen python scripts/build_rag_retrieval_dataset.py` | 更新 `benchmarks/datasets/rag_retrieval/queries.csv` |
| 构造困难负例 | `uv run --frozen python scripts/build_rag_hard_negatives.py` | 更新 `benchmarks/datasets/rag_retrieval/hard_negatives.csv` |
| Seed Level B 请求转换 | `uv run --frozen python scripts/build_seed_case_requests.py [--write]` | 对 50 个 Level A 抽取记录裁决 `gap/rejected/converted`，写入 `benchmarks/datasets/seed-cases-v1/levelb-disposition.v1.json` |
| JP/KR 来源身份裁决初稿 | `uv run --frozen python scripts/build_jp_kr_adjudication.py [--write] [--check]` | 生成 `status/check/task065/jp_kr_source_adjudication.csv` 人工审核表初稿（保留专家签署列） |
| JP/KR 来源身份门禁 | `uv run --frozen python scripts/check_regional_source_identity.py [--json]` | 只读检查 JP/KR 来源一对一绑定、孤立 PDF、可抽取文本、隔离执行与处置合法性 |
| JP/KR 待建 source 提议 | `uv run --frozen python scripts/build_jp_kr_pending_source_proposals.py [--write] [--check]` | 生成 `status/check/task065/jp_kr_pending_source_proposals.csv`（8 份真实 PDF 的待建 source/版本/附件提议，保留专家签署列） |
| 产品 Smoke Benchmark | `uv run --frozen python scripts/run_smoke_benchmark.py --mode all --target cn` | 输出评测结果 |
| RAG 检索 Benchmark | `uv run --frozen python scripts/run_rag_retrieval_benchmark.py` | 写入 `outputs/benchmarks/` |
| 保存检索回归快照 | `uv run --frozen python scripts/snapshot_rag_retrieval_benchmark.py` | 写入 `outputs/benchmarks/regression/` |
| 仓库卫生检查 | `uv run --frozen python scripts/check_repository_hygiene.py` | 只读检查受治理文件 |
| 本地 new 迁移完整性 | `uv run --frozen python scripts/check_local_new_parity.py --require-complete` | 核对固定 Git 增量、56 项处置证据和实体目标 |
| Cloud Studio 启动 | `bash scripts/cloud_studio_start.sh` | 由 `.vscode/preview.yml` 调用 |

## 生命周期规则

- 新脚本必须有明确消费者、输入、输出和可重复执行方式，并同步更新本文件。
- 一次性迁移脚本完成使命后应删除；迁移事实写入 `docs/archive/governance/executed-batches/`，不长期建立 `legacy/` 代码仓。
- 不在脚本中复制业务规则、Prompt、Schema 或评测算法。
- 不固定写入个人虚拟环境、绝对路径或已经退役的目录名。
- 生成文件写入 `storage/` 或 `outputs/`，不得混入源码目录。
