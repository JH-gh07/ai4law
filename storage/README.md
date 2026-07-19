# Local runtime storage

`storage/` 是 DataComplyFlow 的本地运行区，不是源码、Fixture、Benchmark 数据集或知识权威源。除本文件和 `runtime_settings.example.json` 外，本目录内容均被 Git 忽略。

## 目录边界

| 路径 | 内容 | 生命周期 | 是否可重建 |
| --- | --- | --- | --- |
| `ai4law.db` | 本地 SQLite 用户、任务、引用和报告元数据 | 持久本地数据 | 可以初始化空库，不可恢复既有记录 |
| `runtime_settings.json` | 管理界面写入的本地 API/LLM 配置，可能含密钥 | 持久本地配置 | 需人工重新配置 |
| `uploads/` | 用户上传和开发运行文件 | 持久本地数据 | 通常不可重建 |
| `reports/` | 生成报告 | 运行输出 | 只有保留输入和配置时才可能重建 |
| `drafts/` | 本地草稿 | 临时或用户数据 | 不保证可重建 |
| `traces/` | 工作流事件和 manifest | 运行审计产物 | 不能据此完整重放；当前没有正式 replay runner |
| `rag/` | 单索引和多索引的派生文件 | 可重建缓存 | 可由法规资源自动或显式重建 |

## 新环境行为

- `AppContainer` 自动创建 `storage/`、`uploads/` 和 `reports/`。
- FastAPI lifespan 通过 `init_db()` 创建空数据库表。
- Trace recorder 在首次写入时创建任务目录。
- RAG 在索引缺失或 Schema 版本不匹配时由现行构建逻辑重建。
- `runtime_settings.json` 是可选本地覆盖；可从 `runtime_settings.example.json` 复制后填写，但不得提交真实密钥。

## 数据治理规则

- 不在源码、前端预设或测试中依赖 `storage/` 内的具体文件。
- 可提交测试材料必须是合成或已脱敏 Fixture，并放入 `benchmarks/fixtures/`。
- 删除数据库、上传、报告、草稿或 Trace 前必须由数据所有者确认；目录被忽略不等于可以自动删除。
- 当前没有自动保留期限或磁盘清理任务。长期运行环境需要另行制定归档、备份和删除策略。
- RAG 索引可安全删除后重建，但删除会增加下一次检索的首次构建耗时。
