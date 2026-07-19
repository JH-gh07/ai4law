# DataComplyFlow DOC-ROOT 文档与知识资源收敛执行契约

## 1. 目标

仓库最终只保留 `docs/` 作为人类可读文档根目录，并彻底删除历史 `doc/`。程序读取的法规和模板归入 `resources/`，评测数据归入 `benchmarks/`。本阶段不修改法律规则、业务 Schema、API、Prompt、前端协议或 RAG 算法。

## 2. 当前批次

本批只处理活动知识资源和检索评测数据：

| 当前路径 | 本批目标路径 | 说明 |
|---|---|---|
| `doc/knowledge/` | `resources/legal/` | 活动法规、注册表、语料和模块知识资产 |
| `doc/knowledge/_evaluation/` | `benchmarks/datasets/product_smoke/` 与 `benchmarks/datasets/rag_retrieval/` | RAG 检索与生成评测数据 |
| `doc/knowledge/_index/` | `resources/legal/catalog/` | 来源目录和资产清单 |
| `doc/knowledge/_registry/` | `resources/legal/registry/` | 法规条款和来源注册表 |

模块目录、`raw/`、references 和 snapshots 本批保持相对结构，避免把物理迁移与法规去重、来源重建混成一个不可回滚变更。下一批依据 Hash 和 source ID 去重。

## 3. 非目标

- 不处理 `doc/开发文档/`、`doc/tmp/` 和原始产品资料目录；
- 不开展法域模块物理迁移；
- 不合并 RAG v2/v3 算法；
- 不生成或修改法律 Gold；
- 不删除尚未完成来源核验的唯一文件。

## 4. 基线与回退

- 分支：`codex/repository-structure-governance-20260713`；
- 起始 HEAD：`b3c22bd6ccfeeb1ee913dd00318abe06d0d6cca2`；
- 当前工作树备份：`.repo-backups/DataComplyFlow_pre_doc_root_20260716.zip`；
- 备份 SHA-256：`A5EE72DA1BEEF2A3024CBC55AAE70E383843CA164B959298CC18D01932617C99`；
- 备份大小：257,628,599 bytes。

回退时先验证备份 Hash，再恢复本批迁移路径；不得覆盖用户独立研究文档或本地运行数据。

## 5. 路径契约

- 活动后端只能通过 `backend/core/resource_paths.py` 获取法规根目录；
- 评测代码只能通过公共路径函数获取 retrieval dataset；
- 活动代码不得新增 `doc/knowledge`、`doc/v2` 或 `doc/v3` 字面量；
- 法规注册表中的 snapshot path 必须同步到新物理路径；
- 生成索引仍位于忽略版本控制的 `storage/`，不随知识源进入 Git。

## 6. 验收门禁

1. 迁移前后文件数量和 SHA-256 集合一致；
2. `doc/knowledge/` 不再存在；
3. 活动代码、测试、前端和非 legacy 脚本无旧活动路径；
4. 知识注册表、Citation、RAG 和 Benchmark 路径测试通过；
5. 后端全量测试通过；
6. 前端测试和生产构建通过；
7. 仓库卫生与 `git diff --check` 通过；
8. 任何失败不得通过复制一份旧目录作为 fallback 规避。

## 7. 后续批次

本批通过后依次进行：法规 source ID 去重、历史开发文档筛减、`doc/tmp` 迁移、原始产品资料去重分流，最后删除空的 `doc/`。

## 8. 2026-07-16 执行结果

本批已完成活动知识资源的物理迁移，但不代表整个 `doc/` 根目录已经删除：

- `doc/knowledge/` 已迁入 `resources/legal/`；
- 检索评测数据已独立迁入 `benchmarks/datasets/product_smoke/` 与 `benchmarks/datasets/rag_retrieval/`；
- `_index` 与 `_registry` 已分别收敛为 `catalog/` 与 `registry/`；
- 迁移前后共核对 472 个文件，SHA-256 集合无差异；
- 活动后端、前端和非 legacy 脚本不再引用 `doc/knowledge`、`doc/v2` 或 `doc/v3`；
- 已删除无消费者的一次性迁移脚本 `scripts/migrate_knowledge_base.py`；
- QA 运行结果统一写入被忽略的 `outputs/benchmarks/`，不再写回历史文档或 QA 数据目录。

验证结果：知识/RAG/Citation/API 专项 88 passed；后端按目录分组回归共 376 passed；前端 5 passed；前端生产构建成功；仓库卫生检查通过。单次全量 pytest 曾因 Windows 子进程退出超时未返回，按目录分组运行后全部测试通过，不能将前一次超时记录为断言失败。

### 8.1 已发现但未猜测修复的数据缺口

`resources/legal/registry/regulation_articles.jsonl` 中有 12 个历史 source ID 仍携带已经不存在的 `doc/v3/...` snapshot path：`CN-LAW-007`、`EU-GUIDE-005` 至 `EU-GUIDE-008`、`EU-LAW-002` 至 `EU-LAW-004`、`US-EU-001`、`US-LAW-003` 至 `US-LAW-005`。这些 ID 不存在于当前 `catalog/sources.csv` 或 `registry/source_registry.v1.json`，同名候选文件存在多份或缺失，因此本批没有任意绑定路径。后续必须先补齐 source registry 的权威记录，再按 source ID 修复条款快照引用。

### 8.2 下一批边界

第一批结束时 `doc/` 真实剩余 130 个文件：`开发文档/` 18 个、原始产品路径资料 88 个、`tmp/` 12 个，以及根目录文件 12 个。此前仅按三个子目录统计为 118，遗漏根目录文件，第二批复核时已纠正。下一批只做文档与资料分类：现行规范归入 `docs/`，历史材料归档或在有重复证据时删除，运行/法律/测试资产分别迁入 `resources/` 或 `benchmarks/`。在消费者和 Hash 审查完成前不直接整目录删除。
## 9. 第二批完成状态

第二批已按独立收敛清单完成，`doc/` 根目录现已不存在。历史设计文档归入 `docs/archive/`，唯一案例材料归入 `benchmarks/source-materials/`，重复法规与模板由 `resources/legal/` 中的相同 Hash 副本覆盖。后续不得重新创建顶层 `doc/`。