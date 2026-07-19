# Config 静态契约

本目录只保存需要被多个技术栈共同读取、适合提交到 Git 的静态契约。它不是后端运行配置目录，也不得存放密钥、本地路径或运行产物。

## `module_registry.json`

该文件是模块稳定身份的跨语言权威清单，供前端映射、后端契约测试和治理工具读取。后端 Router 仍由 `backend/api/v1/router.py` 显式装配；前端不得通过本文件生成或控制后端路由。

字段职责：

- `module_id`：跨前后端、Trace 与 Benchmark 使用的稳定业务身份；
- `jurisdiction`：`cn`、`eu` 或 `us` 法域；
- `frontend_key`：现有前端兼容键；
- `task_template_id`：前端任务模板身份；
- `implementation_package`：当前可导入的后端实现包；
- `v1_api_prefix`：已发布的 v1 业务路径前缀；
- `lifecycle`：`active` 或 `legacy-compatible`；
- `note`：仅用于解释无法从字段本身表达的兼容边界。

修改本文件后必须运行：

```bash
uv run --frozen pytest -q backend/core/tests/test_module_registry.py
cd frontend && npm test -- src/lib/module-registry.test.ts
```

禁止将运行时 LLM、数据库或外部服务凭据写入本目录；相关变量样例只允许以空值形式出现在仓库根目录 `.env.example`。
