# Legacy QA 评测资产归档

> 状态：archive
> 归档日期：2026-07-17

本目录保存原顶层 `qa/` 中仍有事实追溯价值、但已经没有活动代码或脚本消费者的评测资产。当前唯一活动评测入口是仓库根目录的 `benchmarks/`。

## 归档内容

- `baseline/`：7 个旧 v0 模块样本和基于文件类型、Markdown Hash 的历史期望输出；
- `rag/rag_baseline_v1.json`：17 个 query 的旧 RAG v1 结果；
- `rag/rag_eval_v2_20260403.*`：2026-04-03 的旧 RAG v2 回归结果与报告；
- `rag/rag_eval_v2_20260404.*`：2026-04-04 的旧 RAG v2 回归结果与报告。

原 `qa/rag_eval_v2.json` 与 `qa/regression/rag_eval_v2_20260404.json` 的 SHA-256 完全相同，归档时仅保留一份并采用日期化名称。

## 使用边界

这些文件不是当前 Gold，不参与默认测试发现，也不能证明当前实现仍能复现历史 Hash 或指标。需要重放时应先建立显式 Adapter，并将新结果写入被忽略的 `outputs/benchmarks/`，不得直接覆盖本归档。
