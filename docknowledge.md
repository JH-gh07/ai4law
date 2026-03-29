# AI4Law 调研与知识库存放总览（P0 v1）

更新时间：2026-03-29

## 1. 已落地的存放方案

本次已按“可追溯 + 可工程化 + 可评测”落盘：

- 总说明：`doc/knowledge/README.md`
- 法规与信源索引：`doc/knowledge/index/sources.csv`
- 公开实践案例索引：`doc/knowledge/index/practice_cases.csv`
- 原始证据快照：`doc/knowledge/raw/cn_regulations/`、`doc/knowledge/raw/cases/`
- 评测用法：`doc/knowledge/evaluation/case_benchmark_usage.md`
- 条文级结构化 Schema：`doc/knowledge/normalized/regulation_article.schema.json`

## 2. 当前补齐结果（第一轮）

- `sources.csv`：15 条（基础法 + 核心规章 + 申报/备案指南 + 政策问答 + 联系方式）
- `practice_cases.csv`：7 条（官方公开实践、统计口径、司法案例）
- `raw` 快照：法规 15 份，案例 6 份

重点覆盖：

- 《网络安全法》《数据安全法》《个人信息保护法》
- 《数据出境安全评估办法》
- 《个人信息出境标准合同办法》
- 《促进和规范数据跨境流动规定》（2024-03-22）
- 《数据出境安全评估申报指南（第三版）》（2025-06-27）
- 《个人信息出境标准合同备案指南（第二版）》（2024-08-23，天津网信转载中国网信网）
- 2025 年 CAC 政策问答（4 月、5 月）

## 3. 关于“网上实际合同案例是否可用于验证”

结论：可以验证系统可行性与有效性，但需要分层使用。

- 能拿到的公开材料通常是：官方案例叙述、统计口径、办理路径、司法裁判要点。
- 通常拿不到的材料：企业完整已签署跨境合同正文与全套申报底稿。

因此采用两阶段验证：

1. 第一阶段（已可执行）：用公开案例验证“路径判断、法规命中、风险识别、引用正确率”。
2. 第二阶段（后续）：接入企业脱敏合同，验证“条款级审查与修订建议”的可用性。

具体方法已写入：`doc/knowledge/evaluation/case_benchmark_usage.md`。

## 4. 下一步（我建议直接做）

1. 从 `practice_cases.csv` 选 3-5 个 `P0` 案例，生成第一版 `golden_set` 标注。
2. 让现有诊断/评估/SCC 模块跑一轮，产出 `evaluation_run_001.md`。
3. 针对漏检条文和误报风险，回调 RAG 检索参数与 Prompt。
