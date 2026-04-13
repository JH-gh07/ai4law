# part1&5 -> main 可安全迁移清单

更新时间：2026-04-03
对比分支：`main` vs `part1&5`

## 1. 差异结论（先看这个）

1. 提交差异：`main` 领先 `17` 个提交，`part1&5` 领先 `2` 个提交。
2. 文件差异规模（`main..part1&5`）：`197 files changed`，其中 `A 55 / D 131 / M 11`。
3. `part1&5` 的主要增量集中在子目录 `1&5/`，是一个相对独立的模块化实现；`main` 是当前集成主干。
4. 不建议直接整分支 merge（会带来大量删除/回退主干能力）。

## 2. part1&5 的核心能力增量

核心价值在“模块5 双模式合同审查（REPORT + REDLINE）”的链路完整化，主要新增了：

1. `clause_revision_planner.py`：基于问题严重度生成修订指令。
2. `clause_rewriter.py`：按指令改写条款并补充建议。
3. `document_parser.py`：文件解析封装。
4. `document_recomposer.py`：修订后正文/附录重组。
5. `review_report_builder.py`：结构化报告对象组装。
6. `revision_diff_builder.py`：原文-修订 diff 结构化输出。

## 3. 可安全迁移（低风险，建议优先）

这些文件是“纯新增能力”，可以先迁入主干但不立刻接入 API：

1. `1&5/backend/services/review_service/clause_revision_planner.py`
2. `1&5/backend/services/review_service/clause_rewriter.py`
3. `1&5/backend/services/review_service/document_parser.py`
4. `1&5/backend/services/review_service/document_recomposer.py`
5. `1&5/backend/services/review_service/review_report_builder.py`
6. `1&5/backend/services/review_service/revision_diff_builder.py`

迁入方式建议：

1. 先落到主干的 `backend/services/review_service/`（保持文件名）。
2. 不修改现有 `service.py` 的执行路径（先保证主功能不回归）。
3. 增加最小单测，验证这些新增类可独立运行。

## 4. 联动后才能生效（中风险）

如果要真正开启 REDLINE 双模式，需要联动以下层：

1. Schema 层：`backend/schemas/review.py`
   - 新增 `ReviewMode / ContractType / ReviewStance / RevisionAction` 等。
2. Model 层：`backend/models/review.py`
   - 新增字段：`review_mode/contract_type/review_stance/custom_rule_text/custom_rule_ids_json/workspace_json/diff_json`。
3. Repository 层：`backend/repositories/review_repository.py`
   - `create_task` 需支持可选字段写入。
4. API 层：`backend/api/review.py`
   - `POST /tasks` 需接收任务创建参数；新增 `GET /tasks/{id}/revised-contract` 和 `GET /tasks/{id}/diff`。
5. Service 层：`backend/services/review_service/service.py`
   - 增加 `PARSING/PLANNING/REWRITING/RECOMPOSING` 阶段和双模式分支。

## 5. 不建议直接迁移的内容（高风险/收益低）

1. 整个 `1&5/backend` 子工程直接覆盖主干 `backend`。
2. 用 `part1&5` 的 `app_streamlit` 覆盖主干当前前端。
3. 把 `part1&5` 作为“真源”替换主干 `doc/knowledge` 与 QA 体系。

原因：会回退主干当前已完成的 v2 模块、RAG 评测、知识库和交付链路。

## 6. 推荐迁移顺序（执行版）

### Phase A（1天）

1. 仅迁移第3节的 6 个新增类文件。
2. 补 `tests/review_service/test_redline_components.py` 基础单测。
3. 不改 API，不改数据库。

验收：主干现有审查流程不变，新增类可被 import 并通过单测。

### Phase B（1~2天）

1. 扩展 `schemas/review.py` 与 `service.py`，引入 REDLINE 逻辑分支（开关受控）。
2. 保持 `REPORT` 默认路径不变。

验收：`REPORT` 回归通过；`REDLINE` 能输出修订文档和 diff JSON（先不开放前端入口）。

### Phase C（1天）

1. 更新 `models/review.py` + 数据库迁移脚本。
2. 更新 `api/review.py` 开放双模式接口。
3. 再补端到端测试。

验收：`POST /tasks` 可指定 `review_mode`；`/revised-contract` 与 `/diff` 可下载/可查询。

## 7. 一句话建议

不要整分支合并；采用“能力抽取 + 分阶段接入”的方式，把 `part1&5` 的双模式审查能力按最小风险并入 `main`。
