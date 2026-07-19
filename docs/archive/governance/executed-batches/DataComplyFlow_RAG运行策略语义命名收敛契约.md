# DataComplyFlow RAG 运行策略语义命名收敛契约

## 1. 治理目标

本批次只收敛 RAG 运行时策略和测试文件的语义命名，消除 `v2`、`v3`、`legacy` 被误解为“可任意删除的旧实现”的风险。遵循“先正确、再简洁、最后补强”，不改变检索算法、Fallback 次序、索引格式、业务接口或输出结构。

## 2. 修改前事实基线

- 基线分支：`codex/repository-structure-governance-20260713`
- 基线提交：`b3c22bd6ccfeeb1ee913dd00318abe06d0d6cca2`
- RAG 专项测试：`20 passed`
- 可回退备份：`.repo-backups/DataComplyFlow_pre_rag_strategy_naming_20260717.zip`
- 统一门面：`backend/common/rag/service.py`

当前三种运行策略不是三份等价重复代码：

| 修改前名称 | 真实职责 | 修改后名称 |
|---|---|---|
| `orchestrator_v3` | 面向法域与资料类型的多索引编排检索 | `multi_index` |
| `legacy_v2` | 直接使用单索引 `RegulationRAGService` | `single_index` |
| `compatibility_api` | 通过公共兼容 API 执行本地检索及可选增强 | `enriched_compatibility` |

## 3. 修改边界

本批次允许：

- 修改 `RetrievalBackend` 的内部枚举字符串；
- 修改对应私有字段、私有函数和测试名称；
- 将测试文件重命名为基于职责的名称；
- 更新当前权威治理文档中的策略名称。

本批次禁止：

- 修改 `retrieve_with_fallback()` 的执行顺序或命中条件；
- 合并或删除三种真实检索路径；
- 修改 `v3.1` 多索引 Schema；
- 重命名现有持久化索引目录或文件；
- 将 `backend/common/knowledge/v2.py`、`builders_v2.py` 误判为 RAG 旧实现；
- 修改业务模块、API、Prompt、前端或数据模型。

## 4. 验收门槛

1. RAG 专项测试全部通过；
2. 后端全量回归不得出现新增失败；
3. 前端测试与构建不得出现新增失败；
4. 仓库卫生检查与 `git diff --check` 通过；
5. 活动代码中不再使用三个旧策略名称；
6. Fallback 的返回内容、顺序和触发条件保持不变。

## 5. 后续边界

Fallback 是否应长期保留三层，需在本批次后依据 Trace 覆盖率、失败样本和索引可用性另行审计。未经运行证据，不在语义命名批次中删除任何检索路径。

## 6. 执行结果（2026-07-17）

- 三种运行策略已完成职责化命名；
- 测试文件已重命名为 `test_multi_index_orchestrator.py` 与 `test_single_index_retriever.py`；
- 活动代码中的旧策略字符串已清零；
- RAG 专项测试：`20 passed`；
- 后端全量回归：`374 passed, 1 warning`；
- 前端测试：`5 passed`；生产构建成功；
- 仓库卫生检查：`1377 repository files checked`，通过；
- `git diff --check`：通过，仅有 Git 行尾转换提示；
- 本批次未修改检索顺序、索引格式、API、业务模块或前端协议。

结论：本批次验收通过。后续 Fallback 收敛须另立契约，不与本批次混合。