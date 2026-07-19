# DataComplyFlow BENCHMARKS 评测目录治理契约

> 日期：2026-07-17
> 状态：已完成

## 1. 目标

在不修改法律 Gold、不改变后端业务接口的前提下，使评测目录具备正确指标、明确任务身份、可校验 Case、隔离运行环境和单一执行入口。

## 2. 修改前基线

- `benchmarks/`：40 个文件，约 3.92 MB；
- JSONL Smoke：Retrieval 17 例、Generation 14 例；
- CSV RAG：240 正例、140 负例；
- DOCX 来源材料：24 份，均唯一但尚未清洗为 Gold；
- `benchmarks/tests`：7 passed；
- Smoke 全量表面结果：Retrieval Recall@K=1.0、Generation Issue Recall=1.0；
- 测试会写入共享 `storage/traces`、`outputs/assessment` 和 `storage/ai4law.db`。

## 3. 权威身份

- `datasets/product_smoke/`：小规模产品调用链和模块回归；
- `datasets/rag_retrieval/`：规模化合成 RAG 检索评测；
- `source-materials/`：待清洗来源材料，不是 Gold；
- `benchmarks/smoke_eval.py`：Product Smoke 执行实现；
- `benchmarks/rag_retrieval_eval.py`：RAG Retrieval 执行实现；
- `scripts/run_*_benchmark.py`：只作为 CLI 薄入口。

## 4. 本批修复

1. 修复 Issue Recall、Forbidden-source leakage 和 Unsupported Claim 的名实不符；
2. Forbidden rate 按发生违规的案例数计算，不按命中条目数冒充比例；
3. 空数据集直接失败；
4. 增加 Pydantic Case Schema；
5. Generation 输入由 Runner 硬编码迁入 Case 数据；
6. Benchmark 运行使用隔离临时工作目录和临时数据库；
7. 删除零消费者 import、函数和重复检索调用；
8. 物理区分 Product Smoke 与 RAG Retrieval。

## 5. 明确不处理

- 不新增或修改法律专家 Gold 结论；
- 不增加 LLM Judge；
- 不建立复杂多层 Harness；
- 不修改后端业务 Service、Prompt、规则和 API；
- 不清洗或改写 24 份 DOCX 原件。

## 6. 验收

- Case Schema 对全部数据校验通过；
- Benchmark 测试运行不新增共享 Trace、Report 或 Citation Audit；
- 指标测试覆盖错误语义；
- Product Smoke 与 RAG Retrieval 入口均可执行；
- 后端与 Benchmark 全量测试、仓库卫生和 `git diff --check` 通过。

## 7. 回退条件

出现后端业务行为变化、评测输入丢失、数据集数量变化无解释、共享运行数据继续被污染或现有入口不可执行时，本批不得认定完成。

## 8. 执行结果（2026-07-17）

### 8.1 已完成结构

- Product Smoke 与 RAG Retrieval 已物理拆分；
- 六份 Product Smoke JSONL 迁入 `datasets/product_smoke/`；
- CSV 数据集统一为 `datasets/rag_retrieval/{queries,hard_negatives}.csv`；
- 两套实现分别收敛到 `smoke_eval.py` 与 `rag_retrieval_eval.py`；
- CLI 统一为 `scripts/run_smoke_benchmark.py` 与 `scripts/run_rag_retrieval_benchmark.py`；
- 旧 practice-case baseline 归入 `scripts/legacy/`，不再是活动入口。

### 8.2 已修复问题

1. Generation Case 输入已自包含，不再由 Runner 按 case ID 硬编码；
2. Pydantic Schema 校验字段、法域、输入类型、空数据和重复 ID；
3. Issue Recall 只认可实际 Gold 标识或标题命中，EU/US 不再因“产生任意 Issue”得到 1.0；
4. 检索污染率和来源泄漏率按受影响案例计算，结果限定在 `[0, 1]`；
5. Product Smoke 的报告、Trace 和 SQLite 审计写入隔离运行目录；
6. 引用审计释放临时 SQLAlchemy Engine，修复 Windows 数据库句柄泄漏；
7. CN RAG 检索复用单个只读 Orchestrator，修复规模评测重复加载索引导致的内存耗尽；
8. 清理 475 个可由“评测公司”输出文件名确认的历史测试运行目录、对应 Trace 和 8,084 条 Citation Audit，不触碰其他运行记录。

### 8.3 实测结果

- Benchmark 测试：`9 passed`；
- RAG、Citation、资源路径与 Benchmark 联合回归：`65 passed`（使用仓库内 `--basetemp`，系统临时目录存在历史权限问题）；
- Repository hygiene：通过，扫描 1,366 个仓库文件；
- `git diff --check`：通过，仅有既存 Windows 行尾提示；
- Product Smoke Retrieval：17 例，Recall@K `0.9706`，MRR `0.6951`，三类污染率均为 `0.0`；
- Product Smoke Generation：14 例，Issue Recall `0.7143`，Citation correctness `1.0`，Forbidden-source leakage `0.0`，Unsupported-claim `0.0`；
- RAG Retrieval：240 正例、140 负例；vector/hybrid 当前正例 Recall@K 均为 `0.167`，负例 SafeReject 均为 `0.257`。

### 8.4 结果解释

本批修复后的分数低于修改前“表面满分”，属于指标纠正后的真实结果。EU/US Issue Gold 与运行时 Issue 标识尚未对齐，应由法律团队确认后更新数据，不能通过宽松匹配修饰结果。Citation correctness 和 Unsupported-claim 仍是轻量确定性指标，不代表完整引用蕴含或事实忠实度。
