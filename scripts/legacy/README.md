# Legacy scripts

本目录保存已经退出当前产品入口、但仍具有历史追溯价值的脚本。它们可能引用已不存在的 `app_streamlit/`、`doc/v3/`、`doc/v2/plan.md` 或 `.venv311`，因此不得用于当前启动、测试、知识入库或比赛发布。

当前权威入口：

- 后端：`uv run uvicorn backend.main:app --reload --port 8000`
- 前端：`cd frontend && npm ci && npm run dev`
- 测试：`uv run --frozen pytest -q`
- RAG 数据构建与评测：使用 `backend/common/rag/` 与现行 `scripts/build_*`、`scripts/qa_rag_eval_v2.py`

保留这些文件只用于理解历史实现，不代表其中的路径、依赖或输出仍然有效。若需要恢复某项能力，应基于当前 Schema 和依赖重新建立独立脚本并配套测试，不应直接重新启用本目录内容。
