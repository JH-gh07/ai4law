# DataComplyFlow 事实与交接材料

本目录保存有明确审计时间边界的事实报告。它不是工程规范目录；当报告与当前代码或测试冲突时，以当前代码和测试为准。

## 当前保留文档

| 文档 | 状态 | 主要用途 | 阅读注意 |
|---|---|---|---|
| `AI4Law_项目事实基线与真实系统理解.md` | `snapshot` | 项目全貌、真实调用链和能力基线 | 后续治理已修复其中部分缺口，结合最新实施报告阅读 |
| `DataComplyFlow 评测资产与 Benchmark 实现可行性分析.md` | `snapshot` | 评测资产、指标和最小 Harness 可行性 | 法律 Gold 和正式 Benchmark 尚不能由规划文字替代 |
| `DataComplyFlow_目录结构与工程规范治理实施报告_20260713.md` | `current implementation record` | 记录 2026-07-13 起的结构治理和后续增量验证 | 章节中的早期数字是历史快照，以最后一节和当前测试为准 |
| `DataComplyFlow_理论前沿与DataComplyBench-CN研究基线_20260713.md` | `retained research baseline` | 理论研究、DataComplyBench-CN 构念与后续 Benchmark 设计支撑 | 不是当前已实现能力或法律 Gold；使用时须与代码事实基线区分 |
| `DataComplyFlow_产品能力补强与后续工作清单_20260719.md` | `current product backlog snapshot` | 保存治理收口后经实测确认的 RAG、生成、Gold、Verifier 与工程补强任务 | 是后续任务依据，不代表补强已经实现；指标须结合数据与 Gold 边界解释 |
| `DataComplyFlow_本地new功能迁移验收报告.md` | `current implementation record` | 记录本地原始 new 功能迁入远程 domains 重构底版的逐项处置与测试证据 | 历史原文只从固定 Git blob 追溯；真实浏览器检查仍是人工合并项 |

上述理论研究基线已由项目负责人明确决定纳入治理并长期留存；治理只登记其身份与版本，不得把研究设想写成当前代码事实，也不得在人工审查前执行 Git 提交。

## 已归档材料

- 原《DataComplyFlow 仓库治理与结构收敛方案》已经被实际实施记录和新的分阶段治理计划替代；
- 第一版《仓库治理与代码优化实施报告》已被内容更完整的目录结构与工程规范治理实施报告替代；
- 旧 Superpowers 设计与实施计划依赖已经变化的路由和目录结构，仅保留历史追溯。

以上材料位于 `../archive/`，不得据此新增活动入口或恢复旧依赖。
