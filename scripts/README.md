# Scripts

`scripts/` 只保存当前可执行的仓库级命令入口。业务实现归 `backend/`，评测实现与数据归 `benchmarks/`；脚本只做参数解析、调用编排或可重复的数据构建。

## 当前入口

| 用途 | 命令 | 输出或效果 |
| --- | --- | --- |
| 生成法规条款数据 | `uv run --frozen python scripts/build_regulation_articles.py` | 更新法规条款 JSONL |
| 构建本地 RAG 索引 | `uv run --frozen python scripts/build_rag_vector_index.py` | 更新当前配置使用的本地索引 |
| 构造检索数据集 | `uv run --frozen python scripts/build_rag_retrieval_dataset.py` | 更新 `benchmarks/datasets/rag_retrieval/queries.csv` |
| 构造困难负例 | `uv run --frozen python scripts/build_rag_hard_negatives.py` | 更新 `benchmarks/datasets/rag_retrieval/hard_negatives.csv` |
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
