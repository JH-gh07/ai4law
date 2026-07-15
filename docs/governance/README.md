# DataComplyFlow 仓库治理入口

本目录是仓库治理、软件著作权材料准备和代码来源追溯的权威入口。产品事实仍以 `docs/handoff/` 的审计文档和当前代码、测试结果为准。

## 权威边界

- 活动后端：`backend.main:app`、`backend/app.py`、`backend/api/`、`backend/modules/`、`backend/common/`
- 活动前端：`frontend/src/`；`frontend/src/integrations/superdesign002/` 有真实路由，属于活动生成式 UI 集成，不得直接删除
- 活动法规评测：`doc/knowledge/_evaluation/`
- 活动知识源：`doc/knowledge/_index/` 与 `doc/knowledge/_registry/`
- 活动 RAG：`backend/common/rag/service.py` 是统一 Facade；v3、真实 v2 和 compatibility API 必须在 Manifest 中区分
- 活动 LLM：`backend/common/llm/` 与模块内 Prompt
- Legacy：`scripts/legacy/`，不得作为启动、发布或知识入库入口
- 本地运行产物：`outputs/`、`storage/traces/`、`storage/reports/`、`storage/uploads/`、本地数据库与 runtime settings，不进入新提交

## 提交前检查

```bash
uv run --frozen python scripts/check_repository_hygiene.py
uv run --frozen pytest -q
cd frontend && npm run build
```

前端构建需要先安装锁定依赖。检查器只处理确定性仓库卫生问题，不判断法律结论、代码原创性比例或软件著作权可登记性。

## 相关文档

- `DataComplyFlow_仓库规范化分阶段治理计划.md`
- `软件著作权与代码来源治理.md`
- `../README.md`
- `../handoff/AI4Law_项目事实基线与真实系统理解.md`
- `../handoff/DataComplyFlow 评测资产与 Benchmark 实现可行性分析.md`
- `../handoff/DataComplyFlow_目录结构与工程规范治理实施报告_20260713.md`

已被替代的治理方案和早期实施记录位于 `../archive/governance/`，只用于历史追溯。
