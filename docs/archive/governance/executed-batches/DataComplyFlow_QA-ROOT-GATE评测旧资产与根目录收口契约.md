# DataComplyFlow QA-ROOT-GATE 评测旧资产与根目录收口契约

> 状态：executed
> 执行日期：2026-07-17

## 1. 批次目标

消除顶层 `qa/` 与 `benchmarks/` 的评测双源，并复核根目录文件、测试发现、Cloud Studio 预览配置和本地产物边界。本批不修改业务逻辑、接口、Schema、Prompt、规则或法律结论。

## 2. 修改前事实

- 顶层 `qa/` 有 8 个被 Git 跟踪的历史文件；
- 活动代码与脚本对这些文件均无引用，只有带时间边界的事实审计文档引用旧路径；
- `qa/rag_eval_v2.json` 与 `qa/regression/rag_eval_v2_20260404.json` 的 SHA-256 相同；
- `benchmarks/README.md` 已声明 `benchmarks/` 为评测权威入口；
- `pyproject.toml` 的 `testpaths` 仅包含 `backend`，根目录 `pytest -q` 不会发现 `benchmarks/tests/`；
- `.vscode/preview.yml` 真实调用 `scripts/cloud_studio_start.sh`，属于可选 Cloud Studio 兼容入口；
- `.agents/`、`.venv/`、`outputs/` 与运行时 `storage/` 已受忽略规则约束。

## 3. 执行结果

- 删除顶层 `qa/` 活动入口；
- 将 7 份非重复历史资产移入 `docs/archive/evaluation/legacy-qa/`；
- 删除 1 份完全重复的 2026-04-04 JSON 快照；
- 在归档 README 中明确其不是当前 Gold、默认回归基线或活动数据集；
- 将 Pytest 根目录发现范围扩展为 `backend` 与 `benchmarks`；
- 在根 README 中固定顶层目录职责、完整测试命令和 Cloud Studio 兼容边界；
- 保留 `.vscode/preview.yml`，因为存在真实脚本消费者关系，不按隐藏文件名称删除。

## 4. 权威源结论

- 活动 Benchmark：`benchmarks/`；
- 历史评测证据：`docs/archive/evaluation/legacy-qa/`；
- Python 依赖：`pyproject.toml` 与 `uv.lock`；
- 本地环境示例：`.env.example`，真实密钥只来自未跟踪环境或受控运行设置；
- Cloud Studio 预览：`.vscode/preview.yml` 与 `scripts/cloud_studio_start.sh`，不属于运行配置权威源。

## 5. 验收与回退

验收应包含：仓库卫生检查、完整 Pytest、Benchmark 测试、前端测试与构建、旧路径活动引用扫描、OpenAPI 生成和依赖锁一致性。任一失败若可归因于本批，应回退对应的最小文件，不回退已经独立验证的其他治理批次。
## 6. 统一回归结果

首次全量回归有 366 项通过、6 项 Setup Error。错误统一来自六个异步 API 测试引用不存在的 `authenticated_user` Fixture，不是业务断言失败。批次以 `backend/conftest.py` 建立无全局副作用的 `authenticated_client`：每个测试使用临时数据库、临时存储、完整 `create_app()` lifespan 和真实注册令牌；六个测试不再在收集阶段导入全局 `backend.main.app`。

最终结果：

- `uv lock --check`：通过；
- 仓库卫生检查：1,013 个文件通过；
- OpenAPI：102 个 Path、104 个 Operation，正常生成；
- 六个受影响异步 API 测试：6 passed；
- Python 全量：372 passed，1 个第三方 TestClient 弃用警告；
- 前端：6 passed；
- 前端生产构建：通过，保留既有大 Chunk 提示。

第三方 `StarletteDeprecationWarning` 与前端 Chunk 大小提示均不影响本轮结构门禁，留待后续依赖升级和性能批次处理。
