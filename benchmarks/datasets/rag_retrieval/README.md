# RAG Retrieval 数据集

- `queries.csv`：主数据集，300 行（240 正例、60 负例）。
- `hard_negatives.csv`：扩展困难负例，80 行。

数据由 `scripts/build_rag_retrieval_dataset.py` 和 `scripts/build_rag_hard_negatives.py` 生成，属于合成评测数据，不是法律案例 Gold。执行入口为 `scripts/run_rag_retrieval_benchmark.py`。