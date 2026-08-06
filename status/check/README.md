# status/check — 已落实待复核交付物

本目录存放**已完成实施、等待人工复核**的交付物。仍有远端配置或后续阶段未完成的方案继续保留在 `status/todo/`。

## Schema 契约防漂移 · 仓库内阶段验收（2026-08-07）

| 文件 | 内容 |
|------|------|
| `DataComplyFlow_Schema契约防漂移阶段验收_20260807.md` | OpenAPI 类型、单源 Builder、26 案例 HTTP、11 模块浏览器 E2E 的证据与边界 |

对应方案：`status/todo/DataComplyFlow_Schema契约防漂移实施方案_20260806.md`。仓库内 PR 2/3/4 已实现；远端 Actions 首跑、`new` 分支必需检查和发布流程依赖尚未完成，因此方案仍留在 `todo/`。

## 引用跳转闭环治理 · P0 阶段（2026-08-06）

| 文件 | 内容 |
|------|------|
| `DataComplyFlow_P0验收总结_20260806.md` | 执行摘要、指标、后续 P1 计划 |
| `DataComplyFlow_引用跳转闭环治理验收报告_20260806.md` | 逐项修复的验证细节与测试矩阵 |
| `p0_test_results.txt` | pytest 完整输出（68 passed） |
| `p0_git_stats.txt` | 提交历史与文件变更统计 |
| `p0_code_snippets.md` | 6 处核心修复的代码片段 |

对应方案：`status/todo/DataComplyFlow_引用跳转闭环治理方案_20260806.md`（P0 已落实，P1 数据层/前端层未开始）。

提交范围：`db5d466`（基线）→ `61a2fcb`（P0 完成）。

### 复核要点

已验证：
- 7 项 P0 代码修复，68 项自动化测试通过（`python3 -m pytest backend/domains/cn/security_assessment/tests/ backend/common/llm/tests/test_citation_policy_fix.py backend/common/llm/tests/test_postprocess_linebreak.py`）
- 各修复的单元级行为（风险等级单源、TLS 1.3 不被拆分、pipeless 表格补全、章节去重、章节范围 issue 过滤、引用策略正则）

尚未验证，复核时需注意：
- **未跑真实报告生成**。全部结论来自单元/契约测试，没有用真实申报材料端到端生成一份报告再人工检查产物。验收报告里"章节重复 0 处""表格渲染失败 0 次"等指标是测试层面的推断，不是对成品报告的实测。
- **`markdown_lint.py` 尚未接入任何调用方**。组件已写完并可用，但 `report_renderer.py` / `service.py` 都没有调用它，因此它当前不对交付物产生任何约束。接入是 P1 待办。
- **引用跳转本身仍不可用**。P0 只修了后端渲染与引用标记的正确性；角标→悬浮卡→条文抽屉的前端链路、CN-REG-004 条文数据（现仅 9 段网页文本）都在 P1，用户侧体验尚未改变。
- 无截屏。前端链路未实现，没有可截的跳转界面；文本证据（测试输出、git 统计）已归档在本目录。
