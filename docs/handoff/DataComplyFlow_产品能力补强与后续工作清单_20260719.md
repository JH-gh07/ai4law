# DataComplyFlow 产品能力补强与后续工作清单

> 文档状态：2026-07-19 治理收口后的产品补强快照
> 证据来源：当前代码、配置、全量测试、Product Smoke、规模化 RAG Benchmark 与治理收口审计
> 使用边界：本文记录事实、问题与候选任务，不代表功能已经实现，不构成法律意见或法律 Gold

## 1. 文档目的

仓库结构治理已经达到收敛条件，后续工作应从“继续整理目录”转向可独立验证的产品能力补强。本文用于保存本轮扫描发现的真实弱项、优先顺序、候选修改范围和验收方法，防止后续把结构治理、算法优化、法律标注和工程补强混在同一批修改中。

事实证据优先级仍为：当前可运行代码和测试 → 当前配置与调用链 → 当前评测结果 → 有日期的事实报告 → 规划文字。

## 2. 当前验收基线

### 2.1 工程基线

| 项目 | 当前结果 | 认定 |
|---|---:|---|
| Python 全量测试 | 372 passed，1 warning | 当前代码与 Benchmark 基础测试通过 |
| 路由、模块注册表、Benchmark 定向门禁 | 28 passed，1 warning | 路由与结构契约通过 |
| 前端测试 | 6 files / 16 tests passed | 前端基础回归通过 |
| 前端生产构建 | 通过 | TypeScript 与 Vite 构建通过 |
| Python 编译检查 | 通过 | 活动 Python 文件可编译 |
| 仓库卫生 | 922 个活动文件检查通过 | 历史目录、缓存、凭据与运行产物边界有效 |
| 活动文档本地链接 | 0 断链 | 活动文档结构有效 |
| API 路由 | 104 个显式 Method + Path | `/health` 1、v0 7、v1 96，无重复 |
| 模块身份 | 12 个 | CN 5、EU 4、US 3；11 active、1 legacy-compatible |

### 2.2 Product Smoke 基线

检索 17 例：Recall@K 1.0、MRR 0.7471、跨法域污染率 0。生成 14 例：Issue Recall 0.7143、Citation correctness 1.0、Forbidden-source leakage 0、Unsupported-claim rate 0。

上述指标只说明固定小样本调用链的确定性回归情况。Citation correctness 当前是期望 source ID 覆盖率；Unsupported Claim 只检查案例列出的禁止性文本，均不等同于完整法律正确性或事实忠实度。

### 2.3 规模化 RAG 基线

数据集包含 240 个合成正例和 140 个合成负例，Top-K 为 5：

| 模式 | Recall@K | Top1 | MRR | SafeReject |
|---|---:|---:|---:|---:|
| vector | 0.150 | 0.133 | 0.140 | 0.243 |
| hybrid | 0.150 | 0.133 | 0.140 | 0.243 |

模块级结果不均衡：BCR、CN Flow、SCC 正例 Recall 为 0；CPRA 为 0.042；Diagnosis 为 0.125。Vector 与 Hybrid 完全相同，当前评测调用链没有显示出可测量的 Hybrid 增益。

## 3. 总体产品判断

当前可以确认：系统入口、路由、模块实现、法律资源、评测 Runner 和确定性 fallback 可以共同运行。当前不能确认：一般化 RAG 质量、完整跨法域 Issue 覆盖、Claim 级事实忠实度、法律 Gold 正确性和生产级拒答能力。

因此后续优先级应为：

```text
先验证评测是否有效
→ 再修复检索和生成真实缺口
→ 再建立专家 Gold
→ 最后补强工程质量与高级 Agent 能力
```

## 4. P0：正式基线冻结

### 4.1 目标

将已经通过测试的治理工作树转化为可追溯 Git 基线，避免产品实验继续叠加在未提交的大规模目录迁移之上。

### 4.2 必做事项

1. 暂存后检查 Git 对移动、删除和新增文件的识别结果；
2. 人工复核所有删除项和敏感/来源不明资产；
3. 按单一目标分批 Commit，不把 RAG 优化或法律内容修改混入治理提交；
4. 复跑全量测试、前端构建、卫生门禁和 `git diff --check`；
5. 创建治理完成 Tag，并记录分支、提交和关键资源 Hash。

### 4.3 验收

工作树清洁；Commit 可独立解释和回滚；测试结果与本文基线一致；Tag 指向最终验收提交。

## 5. P1：评测有效性与 RAG 调用链审计

### 5.1 当前事实

- 小规模 Product Smoke Recall@K 为 1.0，但规模化 Recall@5 仅为 0.150；
- `retrieve_regulations()` 对中国法域优先进入多索引 Orchestrator，并在已有结果时提前返回；
- Vector 与 Hybrid 在本轮规模化评测中结果完全相同；
- Benchmark Gold 来源主要由内部脚本合成，尚未经过法律专家确认；
- 部分模块期望 source ID 可能与当前索引覆盖、模块提示或 path 路由不一致。

### 5.2 需要回答的问题

1. Gold source ID 是否真实存在于当前权威 Registry 和活动索引；
2. 每个模块的 jurisdiction、path、module hint 是否传递正确；
3. Vector 与 Hybrid 是否实际调用了不同检索策略；
4. v3 多索引提前返回是否绕过 mode、score floor 或 fallback；
5. 负例未拒答是阈值问题、索引问题还是 query 分类问题；
6. 数据集是否存在模板化、同源构造或固定标题泄漏，从而高估 Smoke；
7. 当前索引是否由当前法规资源和当前代码版本可重复构建。

### 5.3 候选文件

- `backend/common/rag/retriever.py`
- `backend/common/rag/orchestrator.py`
- `backend/common/rag/service.py`
- `backend/common/rag/fulltext_index.py`
- `benchmarks/rag_retrieval_eval.py`
- `benchmarks/datasets/rag_retrieval/`
- `resources/legal/registry/`
- `scripts/build_rag_vector_index.py`

### 5.4 验收要求

- 先形成 source ID、索引文档和模块路由一致性报告，再修改算法；
- Vector 与 Hybrid 的运行 Manifest 能证明实际执行策略；
- 同一冻结数据集上指标可重复；
- 规模化指标相对本文基线有可解释改进，同时 Product Smoke 不回退；
- 目标阈值由研究团队在数据有效性确认后冻结，不在本文件中任意设定。

## 6. P1：EU/US 生成 Issue 覆盖修复

### 6.1 当前事实

Product Smoke 的 14 个生成案例中，EU SCC、EU BCR、US EO 14117 和 US Privacy 四个案例 Issue Recall 为 0。系统生成了结果，但输出中的 Issue 标识或标题未命中当前案例 Gold。

### 6.2 审计顺序

1. 确认案例 Gold Issue ID/标题是否与当前模块 Schema 一致；
2. 区分“业务没有发现 Issue”和“发现了同义 Issue 但评测无法对齐”；
3. 检查模块输出是否真正包含结构化 Issue，而非只在报告正文中描述；
4. 检查 Issue 是否在适配、聚合或渲染阶段丢失；
5. 经法律专家确认后再修改规则、Prompt 或 Gold。

### 6.3 候选范围

- `benchmarks/smoke_eval.py`
- `benchmarks/datasets/product_smoke/generation_eval_cases_eu.jsonl`
- `benchmarks/datasets/product_smoke/generation_eval_cases_us.jsonl`
- `backend/domains/eu/{scc_review,bcr_review}/`
- `backend/domains/us/{eo14117,cpra}/`

### 6.4 验收

每个失败案例能明确归类为 Gold 契约问题、Schema 适配问题或真实业务漏检；修复后保留原始失败样本作为回归案例，不只修改标题来追求分数。

## 7. P1：法律专家 Gold 建设

### 7.1 法律团队需要提供或确认

- 最终合规路径及适用前提；
- 节点级规则判断；
- 关键事实、缺失事实和必须追问字段；
- 权威法规 source ID、条款号、版本和有效期；
- 预期 Issue、风险等级和人工分流条件；
- 引用是否相关、是否支持 Claim、证据是否充分；
- 对无法确定事项的拒答或保守处理要求。

### 7.2 数据治理要求

Gold 必须记录标注人、复核人、日期、法域、法规版本、来源、分歧和裁决记录。历史 `module-specs/test-cases.md`、产品 Smoke 和合成 RAG 查询只能作为候选素材，不能直接升级为 Gold。

### 7.3 最小建议范围

先围绕中国数据出境路径诊断建立 12—20 个专家案例，覆盖豁免、标准合同/认证、安全评估、重要数据、CIIO、敏感个人信息阈值、信息不足、规则冲突和人工分流，再扩展到下游安全评估与 SCC/PIPIA。

## 8. P2：Evidence、Claim、Citation 与 Verifier

### 8.1 当前缺口

- 不同模块对 Fact、Issue、Evidence 和 Context Pack 的复用程度不一；
- 缺少统一贯穿报告的 ClaimItem；
- Citation correctness 目前不能衡量引用是否真正支持结论；
- Unsupported Claim 不是完整的事实忠实度检测；
- 修复循环、失败阻断和人工复核尚未形成跨模块统一契约。

### 8.2 建议路径

不先全量迁移公共 Workflow。选择中国路径诊断及一个下游模块，建立最小 Claim—Evidence—Citation 映射和确定性校验，再评估能否复用。优先增加可观察字段与评测适配层，不先增加复杂 Agent。

### 8.3 验收

至少能够从一个报告 Claim 回溯到 Fact、Rule/法律依据和 Evidence；无证据 Claim 能被确定性标记；修复失败能进入人工分流而不是静默输出。

## 9. P2：规则版本与不确定事实处理

需要逐步补充规则版本、生效时间、法源版本、优先级、例外、缺失事实和冲突轨迹。重点复核中国路径中 unknown、豁免短路、AI 辅助事实推断与确定性规则之间的边界。

修改规则前必须由法律团队确认，不得把旧设计文档、注释或模型输出当作现行法结论。验收应覆盖节点级命中轨迹、缺失事实列表、保守分流和法规版本记录。

## 10. P2：运行可观测性与成本评测

当前 Trace、Manifest、中间 JSON 和报告输出已经存在，但跨模块记录不统一。后续应优先统一评测所需的最小运行字段：代码版本、配置、模型、Prompt/规则版本、检索 Manifest、耗时、重试、错误类型、Token 与成本。

目标是让同一 Case 可以复跑和比较，而不是先替换现有任务系统或引入新的复杂可观测平台。

## 11. P3：工程质量补强

以下事项有价值，但不应阻塞结构治理提交：

- 将 Ruff 纳入 Python 可执行依赖和 CI 门禁；
- 评估 Mypy 的渐进式引入范围；
- 为前端建立 ESLint 门禁；
- 处理 Starlette TestClient/httpx 弃用警告；
- 建立依赖升级、漏洞扫描和版本更新策略；
- 对本地 `outputs/`、`storage/` 建立容量、归档和保留期限策略。

这些任务应分别提交，不能与法律规则或 RAG 算法调整混合。

## 12. 明确非目标

近期不建议：统一重写所有模块、全量引入 ClaimItem/RuleItem、一次迁移所有 Workflow、重写全部 Prompt、复制 v0 为 v1、删除仍有消费者的外部集成、为了目录整齐拆分大型业务文件、在 Gold 未确认前修改法律结论。

## 13. 推荐实施顺序

```text
P0 Git 基线冻结
→ P1 Benchmark 数据与索引一致性审计
→ P1 RAG 路由/模式/拒答修复
→ P1 EU/US Issue 失败案例归因与回归
→ P1 中国路径专家 Gold
→ P2 Claim/Evidence/Citation 最小试点
→ P2 规则版本与可观测性
→ P3 Lint、依赖与运行数据策略
```

每个阶段必须保持目标单一，记录修改前基线、非目标、验收命令和失败回退条件。任何指标提升都必须同时报告数据版本、运行配置和失败案例，不能只汇报平均分。

## 14. 当前可直接复用的资产

- `config/module_registry.json`：模块稳定身份；
- `backend/api/tests/route_baseline.json`：API 结构基线；
- `benchmarks/datasets/product_smoke/`：固定产品回归案例；
- `benchmarks/datasets/rag_retrieval/`：规模化合成检索数据；
- `benchmarks/schema.py`、`smoke_eval.py`、`rag_retrieval_eval.py`：现有评测实现；
- `resources/legal/registry/`：法规来源注册信息；
- `resources/research/module-specs/`：历史需求和候选案例素材；
- `storage/traces/` 与模块 Manifest：历史运行分析素材；
- `docs/standards/`：活动开发和治理规范。

## 15. 最终结论

仓库结构治理完成后，最重要的后续工作不是继续移动目录，而是验证 Benchmark 的有效性并修复真实产品差距。规模化 RAG 结果和 EU/US Issue 覆盖已经提供了可复现起点；后续应围绕这些基线进行小批量、可归因、可回滚的能力增强，并由法律专家参与 Gold、规则和结论层面的确认。
