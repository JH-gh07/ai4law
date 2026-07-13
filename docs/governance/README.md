# DataComplyFlow 仓库治理入口

本目录是仓库治理、软件著作权材料准备和代码来源追溯的权威入口。产品事实仍以 `docs/handoff/` 的审计文档和当前代码、测试结果为准。

## 权威边界

- 活动后端：`backend.main:app`、`backend/app.py`、`backend/api/`、`backend/modules/`、`backend/common/`
- 活动前端：`frontend/src/`；`frontend/src/integrations/superdesign002/` 有真实路由，属于活动生成式 UI 集成，不得直接删除
- 活动法规评测：`doc/knowledge/_evaluation/`
- 活动知识源：`doc/knowledge/normalized/` 与 `_registry/`
- 活动 RAG：CN v3 优先、v2 兼容回退
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

- `软件著作权与代码来源治理.md`
- `../handoff/AI4Law_项目事实基线与真实系统理解.md`
- `../handoff/DataComplyFlow 评测资产与 Benchmark 实现可行性分析.md`
- `../handoff/DataComplyFlow 仓库治理与结构收敛方案.md`
