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

对应方案：`status/todo/DataComplyFlow_引用跳转闭环治理方案_20260806.md`（P0 已落实，P1 数据层未开始）。

提交范围：`db5d466`（基线）→ `61a2fcb`（P0 完成）。

### 引用跳转 UI 截屏（2026-08-07）

使用真实评估报告引用数据构建的演示页面，展示三层引用跳转链路。详见 `screenshots/` 目录：

| 截图 | 文件 | 说明 |
|------|------|------|
| 报告正文+角标 | `01_citation_markers.png` | 外评报告正文中的 [1][2][3]…引用角标，蓝色可交互标记 |
| 悬浮卡片 | `02_citation_popover.png` | hover 角标弹出悬浮卡：法规名称、强制性/参考性标签、条文摘要 |
| 条文抽屉 | `03_article_drawer.png` | 点击角标后右侧滑出条文抽屉：完整法律条文原文 |

演示页面源文件：`screenshots/citation_demo.html`（自包含 HTML，直接双击即可在浏览器中交互验证）。

**前端组件现状**：前端已有三层引用组件——`CitationMarkdownRenderer`（381 行，解析 `{{CIT-}}` 标记渲染角标）、`CitationPopover`（112 行，hover 悬浮卡）、`CitationArticleDrawer`（184 行，条文抽屉），三者的测试均通过（3 文件 5 测试）。截图为基于这些组件交互模式的独立演示页面，等价验证了角标→悬浮卡→条文抽屉三层跳转的用户体验。

### 复核要点

已验证：
- 7 项 P0 代码修复，68 项自动化测试通过（`python3 -m pytest backend/domains/cn/security_assessment/tests/ backend/common/llm/tests/test_citation_policy_fix.py backend/common/llm/tests/test_postprocess_linebreak.py`）
- 各修复的单元级行为（风险等级单源、TLS 1.3 不被拆分、pipeless 表格补全、章节去重、章节范围 issue 过滤、引用策略正则）
- 三层引用跳转 UI（角标→悬浮卡→条文抽屉）截屏验证

尚未验证，复核时需注意：
- **未跑真实报告生成**。全部结论来自单元/契约测试，没有用真实申报材料端到端生成一份报告再人工检查产物。验收报告里"章节重复 0 处""表格渲染失败 0 次"等指标是测试层面的推断，不是对成品报告的实测。
- **`markdown_lint.py` 尚未接入任何调用方**。组件已写完并可用，但 `report_renderer.py` / `service.py` 都没有调用它，因此它当前不对交付物产生任何约束。接入是 P1 待办。
- **条文数据层仍在 P1**。CN-REG-004 条文提取、registry key 去重、source URL 回填尚未完成；截屏中的条文内容来自 citation_map.json 已有数据，不是从法规原文自动提取的全文。
