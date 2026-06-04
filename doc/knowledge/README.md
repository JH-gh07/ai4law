# AI4Law 知识库

更新日期：2026-06-05

这套目录现在进入“模块化知识库”阶段。目标不是只保留旧的法规索引，而是把现有业务说明、测试案例、原始依据文件、正文快照、全局索引、条文注册表、评测集一起纳入统一知识库工程。

## 目录结构

```text
doc/knowledge/
├── _index/        # 全局索引：sources.csv / practice_cases.csv / module_catalog
├── _registry/     # 全局注册表：source_registry / regulation_articles / schema
├── _evaluation/   # 评测与回归数据集
├── cn-diagnosis/  # 模块知识包
├── cn-assessment/
├── cn-review/
├── cn-pipia/
├── eu-scc/
├── eu-bcr/
├── eu-dpia/
├── eu-tia/
├── us-14117/
└── us-cpra/
```

每个模块目录当前统一包含：

- `spec.md`
- `test-cases.md`
- `references/`
- `snapshots/`

## 当前状态

第一轮全量迁移已经执行，迁移摘要见：

- `doc/knowledge/_index/migration_summary.json`

已完成的内容：

- 从 `doc/数规通功能路径描述（含reference）、流程描述、测试案例` 提取 10 个模块的业务说明和测试案例
- 把旧 `doc/knowledge/raw/*` 快照复制归位到对应模块 `snapshots/`
- 把旧 `doc/knowledge/index/*`、`registry/*`、`normalized/*`、`evaluation/*` 复制到 `_index/_registry/_evaluation`
- 重写新的 `sources.csv / practice_cases.csv` 中的 `snapshot_path`，指向模块目录

## 运行原则

- 后端优先读取新结构：`_index / _registry / _evaluation`
- 仍兼容旧结构：`index / registry / normalized / evaluation`
- 迁移完成前，不直接删除旧目录，避免现有链路中断

## 关键脚本

- `scripts/migrate_knowledge_base.py`
  - 建立新骨架
  - 提取 `spec.md / test-cases.md`
  - 复制 `references/` 与 `snapshots/`
  - 生成 `_index` 下的新索引文件

- `scripts/build_regulation_articles.py`
  - 从当前生效的 `sources.csv` 重建 `_registry/regulation_articles.jsonl`

- `scripts/build_rag_vector_index.py`
  - 从当前生效的 `regulation_articles.jsonl` 重建 RAG 向量索引

## 仍需继续落实

1. 不是所有来源都已经完成“精确模块归属”，目前部分快照采用第一轮规则分配。
2. `sources.csv` 还是旧字段集，后续要补 `module/category/summary/suitable_for/report_usage`。
3. `source_registry.v1.json` 目前是旧版本复制过来的，后续需要基于新 `_index/sources.csv` 重建。
4. 旧目录仍保留，等全链路验证通过后再决定是否彻底切换。
