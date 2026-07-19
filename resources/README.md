# DataComplyFlow Resources

本目录只保存可复用的仓库资源，不保存运行生成的索引、Trace、上传件或 Benchmark Gold。

| 路径 | 权威职责 | 生产运行是否读取 |
|---|---|---|
| `legal/` | 法规来源、案例目录、来源注册表和条款语料 | 是 |
| `rules/` | 按法域划分的确定性业务规则 | 是 |
| `templates/` | 经审核的报告结构与交付模板 | 是 |
| `research/` | 论文、设计来源、历史模块说明和来源待确认材料 | 否 |

生产代码必须通过 `backend/core/resource_paths.py` 或 `backend/common/knowledge/paths.py` 解析资源路径。模块与法规的多对多关系写入 catalog/registry，不再通过复制同一文件到多个模块目录表达。

生成的向量索引位于 `storage/rag/`，评测数据位于 `benchmarks/datasets/`，两者均不属于本目录的权威源。