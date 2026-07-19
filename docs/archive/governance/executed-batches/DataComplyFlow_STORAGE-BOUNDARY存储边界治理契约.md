# DataComplyFlow STORAGE-BOUNDARY 存储边界治理契约

## 1. 治理目标

本批只治理 `storage/` 的源码边界、可重建性、敏感性和消费者契约，不修改数据库 Schema、业务工作流、RAG 算法或用户数据。

## 2. 修改前事实

- `storage/` 共约 365 MB；只有 `runtime_settings.example.json` 被 Git 跟踪。
- 本地 SQLite 约 85 MB，包含 11 张表和真实运行/测试混合记录。
- `traces/` 有 31,423 个 JSON、约 247 MB，覆盖大量随机任务和同步运行；当前没有完整 replay runner 或自动保留期限。
- `rag/` 约 19 MB，包含 `regulation_index_v2.json` 和 v3.1 多索引派生文件；缺失时可以由现行代码重建。
- `uploads/`、`reports/`、`drafts/` 来源混合，可能含用户材料或敏感信息，不能按时间或名称批量删除。
- `runtime_settings.json` 当前存在非空 LLM API key；文件已被忽略，但必须继续视为凭据资产。
- 前端开发预设和 Demo payload 硬编码了被忽略的 `storage/uploads/` 文件；新克隆环境不可复现，其中一个本地 DOCX 名称还可能涉及源码材料。

## 3. 权威边界

Git 只允许：

- `storage/README.md`；
- `storage/runtime_settings.example.json`，且所有凭据字段必须为空。

其他 `storage/*` 一律属于本地运行状态，不得进入版本控制。生产法规和模板归 `resources/`，评测数据与合成 Fixture 归 `benchmarks/`，运行输出归 `outputs/` 或 `storage/`。

## 4. 本批处理

- 将 `.gitignore` 收敛为关闭式 `storage/*` 规则，仅反向放行 README 和示例配置。
- 将仓库卫生门禁改为 storage allowlist，防止未来新类型运行文件被强制提交。
- 新增 storage 权威说明和数据删除边界。
- 新增脱敏合成 Fixture，并将开发预设/Demo payload 从本地上传路径迁出。
- 不删除现有数据库、上传、报告、草稿、Trace 或索引；其来源和所有权不足以支持安全自动删除。

## 5. 暂缓问题

- Trace 保留期限、压缩归档和 replay runner。
- 数据库正式迁移、备份与清理命令。
- 上传/报告的用户级生命周期和删除审计。
- `regulation_index_v2.json` 与 `rag/v3` 的命名收敛；当前两者均有真实消费者。
- 本地 `runtime_settings.json` 的密钥加密和管理员 RBAC。

## 6. 验收门禁

1. Git 只能识别 storage README 和示例配置。
2. 所有活动源码不再引用 `storage/uploads/` 具体文件。
3. 合成 Fixture 不含真实名称、密钥或法律 Gold 结论。
4. 前端测试与构建、存储/RAG/资源路径测试通过。
5. 仓库卫生检查和 `git diff --check` 通过。

## 7. 执行结果（2026-07-17）

- Git 可见的 storage 文件严格为 `README.md` 与 `runtime_settings.example.json`；实际配置、数据库、索引、Trace、报告、草稿和上传继续被忽略。
- 活动源码对 `storage/uploads/` 具体文件的引用由 12 处降为 0；开发预设改用 4 个可提交的合成 Fixture。
- 未删除约 365 MB 本地数据，也未读取或输出实际 API key 值。
- 发现 `backend/conftest.py` 无消费者却在 pytest 收集期导入默认应用，导致真实运行配置每次测试都被重写；该文件已删除。
- 8 个创建应用或容器的测试文件显式使用 `tmp_path/storage`，不再共享仓库运行目录。
- 测试隔离复验：35 passed；真实 `runtime_settings.json` 的 Hash 和修改时间均保持不变。
- storage/RAG/资源/Benchmark 回归：83 passed；真实运行配置保持不变。
- 前端：6 tests passed，生产构建通过。
- FastAPI TestClient 仍有上游弃用警告，不属于本批行为问题。

- 最终仓库卫生检查通过，共检查 1,011 个仓库文件；`git diff --check` 通过。
- 本轮生成的前端构建目录、pytest cache 和源码 bytecode cache 已清理，数量为 0。
