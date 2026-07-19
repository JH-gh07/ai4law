# DataComplyFlow 研究与来源材料

本目录保存不参与生产运行的论文、产品设计输入、历史模块说明和来源待确认材料。

- `papers/`：论文 PDF、论文目录和下载记录；
- `product-design-sources/`：早期路径层、功能层设计材料、截图、外部模板及原始统筹文档；
- `module-specs/`：从旧模块知识包迁出的功能说明与历史测试案例，仅用于追溯。

## 使用约束

- 生产代码、运行配置和 RAG 不得读取本目录；
- 来源不明的 DOC/DOCX/PDF/图片不能直接认定为产品权威依据；
- 进入法规知识库的材料必须登记到 `resources/legal/catalog/sources.csv` 并放入法域权威源；
- 成为正式报告模板的材料必须形成审核版本并放入 `resources/templates/`；
- Benchmark Gold 必须进入 `benchmarks/datasets/`，不得混入研究材料；
- 本目录不再建立 `.bak`、模块副本或第二套归档。