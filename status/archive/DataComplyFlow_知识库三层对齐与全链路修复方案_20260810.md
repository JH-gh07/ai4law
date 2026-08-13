# DataComplyFlow 知识库三层对齐与全链路修复方案

> 版本：v2.0（审核修订版）
> 制定日期：2026-08-10
> 适用分支：`new`
> 代码基线：`2a3527e`
> 方案状态：待执行
> 范围：来源治理、RAG/证据链、报告引用与 Markdown 交付
> 不包含：浏览器截图、远程服务器、远程部署

---

## 一、核心结论

本轮不能继续用“索引条目数”“脚注表长度”“Markdown 行数”作为主要成功指标。

真正要解决的是三件事：

```text
第一层：来源是否真实、分类正确、可追溯
第二层：业务问题是否检索并绑定了正确依据
第三层：报告是否把依据放在对应结论旁边并正确交付
```

最核心的一句话：

**让每个对外结论都能从报告反查到结构化问题、证据绑定、规范条文和权威来源；任何统计都不能脱离这条链路单独判定通过。**

---

## 二、三层职责和边界

### 2.1 第一层：来源与规范条文层

职责：回答“这是什么资料、是否权威、能否引用、真实定位是什么”。

```text
resources/legal/catalog/sources.csv
  → 来源元数据、官方 URL、类型、用途、法域

resources/legal/registry/source_registry.v1.json
  → 运行时来源契约，由 sources.csv 确定性生成

resources/legal/registry/regulation_articles.jsonl
  → 规范化条文、真实 locator、正文、source_id
```

这一层不得包含：

- 报告章节；
- LLM 输出；
- 脚注编号；
- 前端排序逻辑；
- 运行时任务状态。

### 2.2 第二层：检索与证据层

职责：回答“当前业务问题用了哪些依据、为什么使用”。

```text
canonical source/article
  → builders_v2.py
  → storage/rag/v3（可重建产物）
  → RetrievalOrchestrator
  → IssueItem / EvidenceItem / CitationBinding
```

这一层的核心对象不是“脚注”，而是：

```text
业务问题 issue_id
  → legal_basis[]
  → source_id + locator + quote + usage_reason
```

### 2.3 第三层：报告与展示层

职责：回答“用户看到的结论是否和第二层证据一致”。

```text
Issue/Evidence/DocumentIR
  → report compiler
  → inline citation marker
  → citation map
  → Markdown / DOCX / PDF
  → KnowledgeContentRenderer
```

前端知识库 catalog 是第一层数据的用户投影，不是新的权威数据源。它可以展示未进入业务 RAG 的参考资料，但必须明确状态和用途。

---

## 三、当前真实基线

### 3.1 已完成并有提交证据

| 能力 | 状态 | 提交/证据 |
|---|---|---|
| canonical module 统一为 `us_14117` | 已完成 | `f06d375` |
| effective source URL 统一解析 | 已完成 | `256f46b` |
| CPRA 人工 `-NN` locator 移除并保留迁移表 | 阶段完成 | `e378cf4` |
| 前端统一 `KnowledgeContentRenderer` | 已完成 | `932ec65` |
| 临时目录索引构建和 manifest | 已完成 | `d9000cd` |
| 11 模块、33 条检索 benchmark | 已完成 | `b987db1` |
| `cn_pipia` 加入 ModuleKey | 已完成 | `f20b58e` |
| CitationBinding 公共转换和三个 evidence builder 接入 | 已完成 | `58d9b26` |
| catalog 过滤无 V3 chunk 来源 | 已完成但设计需调整 | `f06d375` / `58d9b26` 当前代码 |

### 3.2 不能继续当作已完成的事项

| 原方案说法 | 当前事实 | 修订结论 |
|---|---|---|
| 9 条 CN 幽灵来源已改为 reference、module 清空 | 当前 `sources.csv` 仍保留原 path/module，`58d9b26` 未修改该文件 | 未完成，且不应简单清空 module |
| BCR/DPIA/CPRA 脚注只需末尾补齐 | 末尾补齐不能证明结论使用了法规 | 原方案作废 |
| PIPIA 生产环境可继续输出占位 | 会让不可交付报告进入完成状态 | 原方案作废 |
| cn_flow 位于 `backend/domains/cn/cn_flow/` | 实际位于 `backend/domains/us/eo14117_flow_review/` | 路径和问题描述需重查 |
| 国际来源是空壳 | 33 个来源已有 1347 条规范化条文，只是没有业务索引 | 应定义为“有条文、未接业务模块” |
| 行数和 footnote_map 数量足以验收 | 两者都可以在不改善法律逻辑的情况下变绿 | 只能作为辅助指标 |

### 3.3 当前工作区约束

制定本方案时，以下文件存在用户未提交修改：

```text
backend/domains/cn/pipia/service.py
backend/domains/cn/security_assessment/report_renderer.py
backend/domains/cn/security_assessment/service.py
backend/domains/cn/security_assessment/task_state.py
backend/domains/eu/scc_review/scc_rule_engine.py
backend/domains/us/eo14117/service.py
resources/templates/us/4.2_us_14117_compliance_template_v0.md
```

实施时必须先确认这些修改的归属和目标，不能覆盖、回退或混入其他任务提交。

---

## 四、剩余问题与正确修复方法

## P0-1：catalog 与业务 RAG 被错误绑定

### 当前逻辑

`backend/services/knowledge_projection.py:211-225`：

```python
rows = [
    _summarize_source(entry, by_source[entry.source_id])
    for entry in registry_entries
    if entry.source_id in by_source
]
```

只有进入 V3 索引的来源才显示在前端。因此 33 个国际来源虽然有 1347 条规范化条文，仍被完全隐藏。

### 问题

```text
没有业务 RAG chunk
  ≠ 没有内容
  ≠ 不应出现在知识库
```

catalog 和业务 RAG 是两个不同能力：

- catalog 负责浏览和来源说明；
- RAG 负责具体模块的业务检索。

### 预期逻辑

catalog 按“可用性”展示，而不是按“是否有 V3 chunk”一刀切：

```text
来源目录
  ├─ 有规范条文 → article_available=true
  ├─ 有可读快照 → preview_available=true
  ├─ 有业务索引 → rag_available=true
  └─ 都没有      → hidden / needs_repair
```

建议 API 增加：

```json
{
  "availability": "indexed|article_only|preview_only|metadata_only",
  "article_count": 13,
  "rag_available": false,
  "citation_available": true,
  "usage_notice": "可浏览和引用，暂不参与业务模块检索"
}
```

### 验收标准

- [ ] 有规范条文的国际来源能在 catalog 中检索和打开。
- [ ] 未进入业务 RAG 的来源明确显示“暂不参与模块分析”。
- [ ] 真正 metadata-only 且无预览的来源不进入用户列表。
- [ ] catalog 排序使用显式 `jurisdiction_order`，不依赖字符串编码顺序。
- [ ] CN/EU/US 主法域可以默认优先展示，但不得删除其他法域。

---

## P0-2：来源类型和用途没有完成治理

### 当前问题

以下资料被原方案统称为“幽灵”：

- 官方申报指南；
- 官方答记者问；
- 申报联系方式；
- 技术规范；
- 使用手册；
- 模板和样例。

它们不是同一种数据，也不应通过统一清空 module 处理。

### 预期分类

| 类型 | 示例 | 可用于 legal_grounding | 可进入对外报告 | 可用于内部审查/结构 |
|---|---|:---:|:---:|:---:|
| `law_article` | 法律、行政法规 | 是 | 是 | 是 |
| `official_guide` | CAC 申报指南 | 辅助 | 可解释说明 | 是 |
| `official_qa` | 答记者问 | 辅助 | 需标明性质 | 是 |
| `procedure` | 联系方式、操作流程 | 否 | 仅行动清单 | 是 |
| `technical_standard` | 金融/汽车数据规范 | 按约束力 | 按约束力 | 是 |
| `template` | 隐私政策样例 | 否 | 否 | 仅结构控制 |
| `test_fixture` | 测试材料 | 否 | 否 | 仅 eval |

### 修复方法

1. 逐项核对 source_kind、authority、binding_force、allowed_usage。
2. 保留真实 module 关联，但让 UsagePolicy 控制用途。
3. 不以 `path=reference` 代替完整分类。
4. 生成 `reference_source_audit.json`，记录每项决定和证据。

### 验收标准

- [ ] 102 个 registry 来源全部有明确 source_kind。
- [ ] `can_be_cited=true` 与 allowed_usage 语义一致。
- [ ] 模板和测试夹具不能进入 legal_grounding。
- [ ] 官方指南可以辅助论证，但不能冒充强制条文。
- [ ] 所有分类决定可回溯到 `sources.csv` 和审计文件。

---

## P0-3：脚注统计和法律依据绑定被混为一谈

### 废止方案

禁止采用以下逻辑：

```text
registry 中有引用
  → 正文没用
  → 报告末尾统一追加
  → footnote_map 变成 100%
```

这只证明“检索过这些法规”，不能证明“这些法规支持正文结论”。

### 预期数据契约

每个需要法律依据的业务对象必须携带：

```json
{
  "issue_id": "ISSUE-001",
  "claim": "该处理活动需要开展 DPIA",
  "legal_basis": [
    {
      "source_id": "EU-LAW-001",
      "locator": "35",
      "quote": "Where a type of processing ...",
      "usage_reason": "支持高风险处理需开展 DPIA 的判断",
      "verification_status": "verified"
    }
  ]
}
```

报告编译器执行：

```text
Issue.claim
  → 在对应段落生成 citation marker
  → registry 分配编号
  → citation map 只收录实际 marker
  → 脚注内容从 CitationBinding 生成
```

### 正确指标

| 指标 | 计算方法 | 门槛 |
|---|---|---:|
| 必须引用问题覆盖率 | 有 verified legal_basis 的 required issues / required issues | 100% |
| 引用可解析率 | 可跳转 marker / 全部 marker | 100% |
| claim-binding 一致率 | marker 对应 binding 与所在 claim 匹配 | 100% |
| 未使用检索结果 | registry 中无正文 marker 的项目 | 不进入 footnote_map |
| 不支持引用 | citation 与 claim 无语义关系 | 0 |

### 模块接入顺序

1. assessment：修复空 CitationRegistry，但只预注册候选，不自动视为已引用。
2. DPIA：从 risk/mitigation/DPO structured blocks 绑定依据。
3. BCR：每个 finding/remediation 绑定 BCR/GDPR 条款。
4. CPRA：每个 gap/domain 绑定准确 section。
5. PIPIA：每个风险和整改项绑定 PIPL/标准合同办法。
6. us_14117：每个 traffic-light reason 和 measure 绑定 28 CFR。
7. eu_scc：每个 clause finding 绑定 SCC/GDPR。

### 验收标准

- [ ] 不存在 `_inject_footnote_appendix` 式的全量补齐函数。
- [ ] required issue 的 verified legal_basis 覆盖率为 100%。
- [ ] `footnote_map` 集合等于正文实际 marker 集合。
- [ ] 删除任一正文 marker 后，对应引用不得继续出现在 footnote_map。
- [ ] 检索到但未使用的法规保留在 trace/debug，不进入正式脚注。

---

## P0-4：LLM 不可用时任务状态和报告语义不明确

### 废止方案

禁止根据 `app_env` 决定是否输出占位报告：

```text
development → fallback
production  → “LLM未配置，此处占位”
```

相同输入不能因为环境名不同而改变法律内容和完成状态。

### 预期状态机

```text
输入校验失败
  → FAILED_VALIDATION

规则/证据足够，LLM 可用
  → COMPLETED

规则/证据足够，LLM 不可用
  → DEGRADED
  → 使用确定性结构化 fallback
  → 明确列出未执行的生成步骤

规则/证据不足，LLM 不可用
  → FAILED_DEPENDENCY
  → 不生成伪完整报告
```

### deterministic fallback 要求

fallback 只能使用：

- 已验证事实；
- 规则命中；
- structured issues；
- verified CitationBinding；
- 固定模板。

禁止：

- 输出空洞占位句；
- 虚构分析；
- 用字符数判定“内容完整”；
- 把 DEGRADED 返回成 COMPLETED。

### 验收标准

- [ ] PIPIA、DPIA、CPRA、14117 等模块使用统一降级状态语义。
- [ ] 无 LLM 测试断言 state、degraded_reasons、skipped_steps。
- [ ] fallback 中没有 `LLM未配置，此处为占位内容`。
- [ ] production/dev 对相同依赖状态产生相同业务状态。
- [ ] 前端能够读取状态字段，但本方案不执行浏览器截图。

---

## P1-1：cn_flow 委托链路需要按真实路径复验

### 当前代码

真实位置：

```text
backend/domains/us/eo14117_flow_review/service.py
```

当前委托已经传递：

```python
canonical_service.generate_report(
    compatibility.canonical_request,
    task_id=run_task_id,
    trace=trace,
)
```

因此不能预设“没有传 output_dir/citation_registry”。canonical service 应拥有自己的输出和引用生命周期。

### 需要验证的问题

- 旧 cn_flow 输入是否被无损映射；
- 同 task_id 是否只产生一套 canonical 产物；
- trace 是否记录 compatibility loss；
- 返回包装是否指向 canonical 报告和 citation map；
- 同一事实经两入口得到相同规则结论、引用集合和产物类型。

### 验收标准

- [ ] 不新增第二套 citation registry。
- [ ] cn_flow 与 us_14117 的 rule IDs、traffic light、citation IDs 一致。
- [ ] 旧响应结构只做包装，不复制业务逻辑。
- [ ] 产物目录没有重复报告和孤立 citation map。

---

## P1-2：Markdown 质量不能只用行数验收

### 原指标问题

```text
行数 > 30
单行 < 300 字符
脚注单独一行
```

这些只能发现部分格式问题，不能证明报告结构和引用正确。Markdown 合法地允许长段落，脚注 marker 应当位于支持的 claim 旁边，而不是单独成行。

### 预期结构门禁

使用 Markdown AST 或现有解析器检查：

- H1 数量符合模板；
- 必需 H2/H3 章节存在；
- 表格列数稳定；
- 列表项未被拼成单行；
- 不存在未闭合 marker；
- citation marker 位于文本节点或表格单元格内；
- 不存在占位符和模板变量；
- 渲染后的 HTML 结构可解析。

行长保留为 warning，不作为单独失败依据。

### 模块重点

| 模块 | 必须验证 |
|---|---|
| us_14117 | 红黄绿结论、实体清单、数据分布、风险矩阵、措施表 |
| eu_scc | clause finding、原文、问题、依据、建议分块 |
| BCR | finding 与 remediation 对应，不泄漏模板变量 |
| PIPIA | 风险、整改、依据、材料缺口完整 |
| DPIA | risk matrix、mitigation、DPO decision |

---

## P1-3：国际法域能力边界必须先定再建索引

### 当前事实

33 个国际来源已有规范化条文，但当前没有对应业务模块和检索契约。

### 本轮推荐策略

先作为“知识资料能力”开放，不立即新增 `intl_*` 业务 RAG：

```text
catalog 浏览：允许
条文详情：允许
引用跳转：允许
业务模块 RAG：暂不允许
对外报告自动引用：暂不允许
```

原因：没有模块 Schema、业务输入、检索 benchmark、报告模板和责任边界时，单独增加索引文件只是半成品。

### 将来转为正式业务能力的前置条件

- canonical module 定义；
- 输入/输出 Schema；
- 至少 3 条业务检索 fixture；
- allowed_usage 和 authority policy；
- 引用跳转测试；
- 报告模板和免责声明。

---

## P1-4：验收报告和 manifest 不一致

当前 `status/check/DataComplyFlow_知识库剩余问题最终验收_20260810.md` 与 `status/check/knowledge-index-manifest.json` 在部分索引数量和模块分布上不一致。

例如最终报告记录的若干 index 数量，不应再手工维护。正确方式：

```text
构建脚本
  → manifest.json
  → Markdown 报告从 manifest 生成统计表
```

验收报告不得手抄：

- chunk 数；
- module 分布；
- canonical row 数；
- test pass 数；
- Git commit。

---

## 五、预期整体架构

```text
┌──────────────────────────────────────────────────────────┐
│ 第一层：Source Governance                                │
│ sources.csv → source_registry → regulation_articles      │
│ 输出：来源分类、真实条文、locator、authority、usage       │
└──────────────────────────┬───────────────────────────────┘
                           │ compile
┌──────────────────────────▼───────────────────────────────┐
│ 第二层：Retrieval & Evidence                             │
│ builders → V3 index → orchestrator → issue/evidence      │
│ 输出：IssueItem + verified CitationBinding               │
└──────────────────────────┬───────────────────────────────┘
                           │ render
┌──────────────────────────▼───────────────────────────────┐
│ 第三层：Report & Delivery                                │
│ DocumentIR → citation compiler → Markdown/DOCX/PDF       │
│ 输出：claim 旁引用、citation map、可跳转来源              │
└──────────────────────────────────────────────────────────┘

前端 catalog = 第一层投影
前端报告 = 第三层投影
storage/rag/v3 = 可重建产物，不是事实源
```

### 依赖方向

```text
领域模块 → 公共 evidence/citation compiler → 知识契约
前端页面 → 共享 renderer → API 契约
```

禁止公共层反向依赖具体模块，禁止每个模块复制 footnote 注入函数。

---

## 六、实施顺序

## Phase 0：冻结事实基线

1. 保存当前未提交业务代码状态，不纳入本方案提交。
2. 在干净 worktree 或明确 commit 上运行基线。
3. 生成机器可读：

```text
source-audit.json
knowledge-index-manifest.json
retrieval-benchmark.json
module-output-baseline.json
```

验收：所有文件带 commit、generated_at、命令和退出码。

## Phase 1：来源和 catalog 治理

1. 为 102 个来源补 source_kind/allowed_usage。
2. 生成 availability 状态。
3. catalog 改为按 availability 展示。
4. 国际来源以 article_only 进入浏览，不进入业务 RAG。
5. 修复显式 jurisdiction_order。

Checkpoint：来源分类无空值；真正 metadata-only 不展示；article_only 可查看。

## Phase 2：公共 claim-evidence-citation 契约

1. 定义 required claim 和 CitationBinding 校验。
2. CitationRegistry 只负责稳定编号，不负责判断引用是否相关。
3. citation compiler 从 structured binding 生成 inline marker。
4. footnote_map 仅包含实际 marker。
5. 增加删除 marker/错误 locator/错误 source 的负向测试。

Checkpoint：公共契约和负向测试全部通过后，才允许改模块。

## Phase 3：模块逐个接入

顺序：

```text
assessment
→ DPIA
→ BCR
→ CPRA
→ PIPIA
→ us_14117
→ eu_scc
→ cn_flow parity
```

每个模块独立完成：

- structured issue binding；
- inline citation；
- citation map equality；
- Markdown AST 门禁；
- 无 LLM 降级状态测试；
- 原子提交。

不得多个模块一起修改后再统一测试。

## Phase 4：索引和检索回归

1. 从临时空目录构建 15 个现有索引。
2. 两次构建 manifest 必须一致。
3. 运行 11 模块、33 fixture benchmark。
4. 增加 source availability 和 claim-binding 门禁。
5. 不在本轮新增 `intl_*` 业务索引。

## Phase 5：报告一致性和最终本地门禁

```bash
git diff --check
uv run python scripts/check_citation_source_integrity.py --verbose
uv run python scripts/check_case_parity.py
uv run pytest backend/common backend/services backend/api -q
uv run pytest backend/common/rag/tests/test_module_retrieval_benchmark.py -q
cd frontend && npm test
cd frontend && npm run build
```

领域模块测试必须单独列出哪些需要 LLM、哪些使用 deterministic fake。不能用“需要 LLM”作为永久排除 domain tests 的理由。

---

## 七、可验核指标

| 编号 | 指标 | 通过条件 |
|---|---|---|
| G1 | 来源分类完整率 | 102/102 |
| G2 | 可引用来源 effective URL | 100% |
| G3 | metadata-only 用户可见数 | 0 |
| G4 | article_only 来源详情可访问率 | 100% |
| G5 | required issue legal_basis 覆盖率 | 100% |
| G6 | citation marker 可解析率 | 100% |
| G7 | footnote_map 与正文 marker 集合 | 完全相等 |
| G8 | unsupported citation | 0 |
| G9 | placeholder/template residue | 0 |
| G10 | 无 LLM 假 COMPLETED | 0 |
| G11 | 15 索引可重复构建 | 15/15，连续两次一致 |
| G12 | 模块检索 benchmark | 33/33 |
| G13 | cn_flow/canonical parity | 规则、引用、产物一致 |
| G14 | Markdown 必需结构 | 每模块全部通过 AST 门禁 |
| G15 | 文档与 manifest 数字差异 | 0 |

脚注数量、Markdown 行数、超长行数量只记录为辅助诊断，不再作为核心 DoD。

---

## 八、证据产物

最终放入 `status/check/`：

```text
DataComplyFlow_知识库三层对齐最终验收_20260810.md
knowledge-source-audit.json
knowledge-index-manifest.json
knowledge-retrieval-benchmark.json
claim-citation-gate.json
module-output-quality.json
test-summary.txt
```

每项必须包含：

- Git commit；
- 输入案例；
- 命令；
- 退出码；
- 统计口径；
- 失败样本；
- 产物相对路径。

旧报告保留，但文件头标记“历史快照”和替代文件，禁止删除审计历史。

---

## 九、Git 存档规则

建议提交序列：

```text
docs(check): record three-layer repair baseline
refactor(knowledge): classify source availability and usage
refactor(citation): compile claim-bound legal citations
fix(assessment): bind issues to verified legal basis
fix(dpia): bind risks and mitigations to verified legal basis
fix(bcr): bind findings and remediations to verified legal basis
fix(cpra): bind compliance gaps to canonical sections
fix(pipia): add deterministic degraded report contract
fix(us14117): compile structured report citations
fix(scc): compile clause-level legal citations
test(cn-flow): verify canonical report and citation parity
test(knowledge): gate three-layer alignment end to end
docs(check): record final local three-layer verification
```

每次只提交一个逻辑增量。禁止 `git add -A`，禁止提交 `storage/`、`tmp/`、`outputs/`。

---

## 十、最终 DoD

- [ ] 第一层每个来源都有明确类型、用途、权威级别和可用性。
- [ ] 第二层每个 required issue 都绑定 verified legal basis。
- [ ] 第三层每个正式脚注都能反查到所在 claim 和 CitationBinding。
- [ ] 未使用检索结果不会被塞进正式脚注。
- [ ] LLM 不可用时不会返回假 COMPLETED 或占位报告。
- [ ] catalog 不再隐藏有真实条文的来源，也不展示真正空壳。
- [ ] 11 模块检索 benchmark 全部通过。
- [ ] cn_flow 与 us_14117 仅保留一套业务和引用逻辑。
- [ ] Markdown 结构门禁通过，模板残留为 0。
- [ ] 最终报告数字全部由机器产物生成，无手抄漂移。
- [ ] 浏览器截图和远程部署仍保持未执行，等待用户单独授权。

---

## 十一、一句话执行策略

**先把来源分清，再把问题与依据绑定，最后由统一编译器生成引用和报告；不隐藏真实资料、不追加无关脚注、不用环境变量掩盖失败，也不再用行数和脚注数量冒充质量。**
