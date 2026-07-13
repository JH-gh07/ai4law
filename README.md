# DataComplyFlow（数规通）

面向企业数据合规与跨境数据治理的 Legal Agentic RAG 工作台。当前活动前端为 React/Vite，后端为 FastAPI；历史 Streamlit 入口已退役。

## Run Backend

```bash
uv run uvicorn backend.main:app --reload --port 8000
```

## Run Frontend

```bash
cd frontend
npm ci
npm run dev
```

## Run Tests

```bash
uv run --frozen pytest -q
```

当前系统事实、Benchmark 可行性和治理边界见 `docs/handoff/`。失效但仍有历史参考价值的脚本统一放在 `scripts/legacy/`，不得作为当前启动或发布入口。

工程架构、命名、API、Schema、测试和 AI 辅助开发要求见 `docs/engineering/`。业务模块当前仍保留兼容目录 `backend/modules/`，稳定法域模块 ID 以 `backend/modules/catalog.py` 为准。
