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
cd frontend
npm test
npm run build
```

根目录的 Python 测试命令同时发现 `backend/` 与 `benchmarks/tests/`；前端测试和构建需在 `frontend/` 中单独执行。

## Repository Layout

- `backend/`：FastAPI 应用、公共能力和按 `cn/eu/us` 划分的法律业务实现；
- `frontend/`：React/Vite 前端；
- `benchmarks/`：唯一活动评测入口、数据集、Fixture 和 Runner；
- `resources/`：生产法规、规则、报告模板与研究材料；
- `config/`：跨语言静态模块身份契约；
- `scripts/`：仓库级活动命令；
- `docs/`：唯一文档根目录；
- `storage/`、`outputs/`：本地运行产物，不作为源码事实源。

`.vscode/preview.yml` 与 `scripts/cloud_studio_start.sh` 共同提供可选的 Cloud Studio 预览入口；它们不参与本地或生产业务配置解析。

当前系统事实、Benchmark 可行性和治理边界见 `docs/handoff/`。当前仓库级命令及其生命周期以 `scripts/README.md` 为唯一入口；失效脚本不在活动代码树中长期保留。

工程架构、命名、API、Schema、测试和 AI 辅助开发要求见 `docs/standards/`。法律业务实现按法域位于 `backend/domains/{cn,eu,us}/`，公共及版本兼容接口位于 `backend/api/`。跨前后端稳定模块身份以 `config/module_registry.json` 为唯一权威源；历史 `backend/modules/` 已退役，禁止重新作为业务实现入口。

运行法规、报告模板与研究材料分别位于 `resources/legal/`、`resources/templates/` 和 `resources/research/`；评测数据和来源材料位于 `benchmarks/`。现行文档入口为 `docs/README.md`，历史材料只在 `docs/archive/` 中追溯。本地数据库、配置、上传、报告、Trace 与派生索引的边界见 `storage/README.md`。
