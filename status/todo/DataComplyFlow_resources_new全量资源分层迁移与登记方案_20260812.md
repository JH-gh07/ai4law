# DataComplyFlow `resources/new` 全量资源分层迁移与登记方案

> 日期：2026-08-12
> 状态：待用户审核；仅制定本地迁移方案，尚未执行本轮文件移动、删除或远程部署
> 源目录：`resources/new/`
> 依据：`resources/README.md`、`resources/legal/README.md`、`resources/research/README.md`、`benchmarks/README.md`、`docs/README.md`、`config/README.md`

## 一、结论先行

`resources/new/` 不是一种资源，而是混合了六种职责完全不同的材料：

1. 法规与监管文件原件；
2. 官方/参考模板和测试输入样件；
3. 功能说明、流程说明和历史测试案例原件；
4. 产品需求说明书；
5. 黄金标准与 50 个种子案例；
6. 本轮迁移 intake 清单和决策日志。

不能把整个目录整体搬到 `resources/legal/`、`resources/research/` 或 `docs/`。正确目标是按消费者和权威级别拆分：

```text
法规原件                    → resources/legal/sources/<jurisdiction>/references/
法规来源元数据              → resources/legal/catalog/ + registry/
经审核的活动报告模板        → resources/templates/<jurisdiction>/
原始需求与产品设计输入      → resources/research/product-design-sources/
历史功能说明的可读转换版    → resources/research/module-specs/
测试案例/样件原件           → benchmarks/source-materials/
结构化共享案例              → benchmarks/cases/
50 个种子案例数据集         → benchmarks/datasets/seed-cases-v1/
当前维护版需求差异快照      → docs/handoff/
迁移完成证据                → docs/archive/governance/executed-batches/
机器 intake 历史台账        → resources/research/migration-ledger/
```

`docs/` 会参与，但只接收经过核实、需要仓库维护者长期阅读的 Markdown 规范/事实快照和最终迁移证据，不接收法规 PDF、原始 DOCX、测试附件或 Gold 数据。`docs/README.md` 已明确规定业务法规、研究来源和 Benchmark 数据分别位于 `resources/` 与 `benchmarks/`，不得重新放入 `docs/`。

## 二、当前真实盘点与迁移进度

### 2.1 当前磁盘数量

2026-08-12 实际盘点：

| 顶层类别 | 有效文件 | 说明 |
|---|---:|---|
| `数规通功能路径描述（含reference）、流程描述、测试案例/` | 90 | CN 35、EU 39、US 16 |
| `知识库补充/` | 61 | 51 个区域法规 PDF + 10 个重复格式目录文件 |
| `数规通黄金标准与种子案例/` | 51 | 黄金标准 1 + 任务 1-10 各 5 个种子案例 |
| 根目录 PRD | 1 | `《数规通（DataComplyFlow）需求说明书》.docx` |
| 根目录重复诊断说明 | 1 | 与嵌套版本 SHA-256 相同 |
| intake/analysis/decisions | 3 | 2026-08-07 的阶段台账 |
| **有效资产合计** | **207** | 不含 6 个 `.DS_Store` |

旧 `manifest.intake.v1.json` 记录 218 个文件，是 2026-08-07 快照。其后 A001-A008 已迁出 8 类资产，当前磁盘总数已经变化，因此不能继续用 218 作为本轮迁移分母。

### 2.2 状态定义

| 状态 | 定义 |
|---|---|
| `MOVED` | 源文件已从 `resources/new` 移出，目标 Hash 已验证 |
| `COPIED_HASHED` | 规范目录已有同 SHA-256 文件，但旧副本和旧路径引用仍在 |
| `INGESTED_NOT_CANONICAL` | 内容已进入 CSV/JSONL/索引的一部分，但原件、Schema、元数据或前端可见性未闭环 |
| `PENDING` | 尚未进入最终目标，或仍需人工裁决 |
| `COMPLETE` | 目标文件、登记、消费者切换、测试、验收和源退出全部完成 |

### 2.3 当前进度

| 状态 | 当前文件数 | 占当前 207 | 事实依据 |
|---|---:|---:|---|
| `COPIED_HASHED` | 89 | 43.0% | 62 个 Reference 原件 + 22 个功能/案例/清单原件 + 5 个 Review 文件，均能在现有规范目录找到同 SHA-256 文件 |
| `INGESTED_NOT_CANONICAL` | 51 | 24.6% | 区域法规 PDF 已由 `ingest_regional_laws.py` 部分写入 `sources.csv`/JSONL，但原件仍在 `new/`，元数据和 V3 检索不完整 |
| `PENDING` | 67 | 32.4% | 10 个目录文件、50 个种子案例、Gold 1、PRD 1、重复诊断说明 2、旧台账 3 |
| `COMPLETE` | 0 | 0% | 当前代码/案例/脚本仍直接引用 `resources/new`，目录尚不能退出 |

可以说已有 140/207 个文件发生过物理复制或下游处理，但不能说迁移完成 67.6%。真正的安全退出完成率仍为 `0/207`，因为任何一类完成都必须包括引用切换和源文件退出。

`COPIED_HASHED=89` 的复算式是：

```text
62（CN/EU/US Reference 原件）
+ 22（23 个功能说明、案例和清单原件中已有同 Hash 的部分）
+  5（Review 的 4 个输入附件和 1 个预期输出原件）
= 89
```

23 个功能说明、案例和清单原件中唯一未计入 `COPIED_HASHED` 的文件，是新版诊断功能说明。它与 `benchmarks/source-materials/cn/legacy-docx/` 中现有同名文件 Hash 不同，必须先版本化并人工裁决，不能按文件名覆盖。

### 2.4 已经完成且不在当前 207 中的历史迁移

`resources/new/decisions.v1.jsonl` 记录 A001-A008：

- 3 份 Benchmark 论文和 1 份 Benchmark 整理文档 → `resources/research/benchmarks/`；
- 数据出境实务手册 → `resources/manuals/`；
- 2 份国标 → `resources/standards/`；
- 种子案例分数汇总表 → `benchmarks/datasets/seed-cases-v1/_source/`。

这些文件当前已不在 `resources/new`，不应再次迁移。

## 三、现有目录职责和禁止混放规则

### 3.1 `resources/legal/`

生产法规资源。原件按法域只保存一份；模块适用关系通过 `catalog/sources.csv`、`source_registry.v1.json` 和 `module_catalog.v1.json` 表达，不复制法规文件。

迁入后必须：

- 分配或核对稳定 `source_id`；
- 在 `sources.csv` 登记 `jurisdiction`、`doc_type`、权威机关、效力、日期、URL、`snapshot_path`/原件路径和 `origin_path`；
- 生成标准 Schema 的 `regulation_articles.jsonl` 条目；
- 重建 `source_registry.v1.json` 和 V3 索引；
- 通过引用完整性、检索和前端条文访问测试。

### 3.2 `resources/templates/`

只保存经审核、当前报告生成器可以消费的活动交付模板。Reference 包里的官方 DOCX 先作为来源原件进入 `resources/legal/sources/.../references/`；只有完成占位符、章节、样式和渲染契约审核后，才形成版本化模板进入 `resources/templates/`。

迁入后必须登记模板版本、来源 Hash、适用模块、占位符 Schema、维护者、审核状态和 renderer 测试。禁止把“看起来像模板”的来源 DOCX直接改名后投入生产。

### 3.3 `resources/research/`

保存原始产品设计输入、可读的历史模块说明和迁移机器台账，不进入生产 RAG。生产代码不得读取该目录。

### 3.4 `benchmarks/`

保存测试来源、结构化 Scenario、数据集和 Gold。`source-materials/` 中的 DOCX 只是来源证据，不自动成为 Gold；`datasets/` 中的 expected 必须经过法律专家确认。

### 3.5 `docs/`

`docs/README.md` 将文档分为：

- `standards/`：当前开发必须遵循的活动规范；
- `handoff/`：有日期边界的事实快照和交接材料；
- `archive/`：历史证据，不约束当前实现。

因此本轮只产生两类 docs 文件：

1. `docs/handoff/DataComplyFlow_需求基线与当前实现映射_20260812.md`：从 PRD、功能说明和当前代码抽取的维护版事实快照；
2. `docs/archive/governance/executed-batches/DataComplyFlow_RESOURCES-NEW全量迁移执行记录_20260812.md`：迁移完成后的决策、Hash、测试和旧路径退出证据。

原始 PRD DOCX 放 `resources/research/product-design-sources/`，不放 docs；否则 docs 会同时出现“原始要求”和“当前事实”两个权威源。

#### `docs/` 是否适用的逐类判定

| 材料 | 是否进入 `docs/` | 证据与理由 |
|---|---:|---|
| 法规、指南、标准原件 | 否 | `docs/README.md:33` 明确将业务法规归入 `resources/`；生产消费者也是 legal catalog、registry、JSONL 和索引，而不是 docs |
| 测试输入 DOCX/PDF/PNG、案例答案、Gold | 否 | `docs/README.md:33` 将 Benchmark 数据归入 `benchmarks/`；`benchmarks/README.md` 又区分 `source-materials/` 与经确认的 Gold |
| 原始 PRD DOCX、历史功能说明来源 | 否 | `resources/research/README.md` 明确由 `product-design-sources/` 和 `module-specs/` 保存这类不参与生产运行的来源材料 |
| 当前需求与实现映射 Markdown | 是，进入 `docs/handoff/` | `docs/README.md:10` 将有审计日期的事实快照归入 handoff；`docs/handoff/README.md` 明确它不是工程规范，冲突时以当前代码和测试为准 |
| 已执行迁移的 Hash、测试、退出证据 | 是，进入 `docs/archive/governance/executed-batches/` | `docs/archive/README.md` 明确该目录保存已完成治理批次；仓库已有多份同类资源迁移契约可沿用 |
| 本方案或尚未执行的迁移计划 | 暂不进入 | 当前仍属于 `status/todo/`；只有实施完成、证据固定后，才形成新的 archive 执行记录，避免把计划写成事实 |
| PRD 中拟升级为强制工程规则的条款 | 条件适用 | 只有经人工批准并与当前代码/测试核实后，才修改现有 `docs/standards/`；不得直接把整份 PRD 提升为活动规范 |

因此，“可能放入 `docs/`”不是按文件格式判断，而是按语义职责判断：可维护的当前事实和已执行历史证据进入 docs，原始来源与可执行评测资产不进入 docs。

### 3.6 `config/`

只保存多技术栈共同读取的静态契约。它不是资源存放目录。迁移中只更新资源路径字段和案例来源路径，不把 PDF、DOCX 或迁移报告放进 `config/`。

## 四、207 个当前文件的完整目标映射

以下映射规则按源路径可唯一确定目标，覆盖当前全部 207 个有效文件；不使用“其他”兜底分类。

### 4.1 功能路径包：90 个

#### A. CN/EU/US Reference 原件：62 个

| 源文件组 | 数量 | 目标 | 当前状态 |
|---|---:|---|---|
| `.../中国数据出境路径reference库/...reference文件库/*` | 21 | 法规/指南/原始模板按 basename 对应 `resources/legal/sources/cn/references/`；两份 GB/T PDF 纠正到 `resources/standards/` | `COPIED_HASHED` |
| `.../欧盟数据出境路径Reference库/...reference文件库/*` | 30 | 按去除无意义 `(1)` 后的 basename 对应 `resources/legal/sources/eu/references/` | `COPIED_HASHED` |
| `.../美国数据出境路径Reference库/...reference文件库/*` | 11 | 按规范 basename 对应 `resources/legal/sources/us/references/` | `COPIED_HASHED` |

这 62 个 Reference 原件已存在同 Hash 规范副本，不再复制。迁移动作是核对目标 Hash、更新来源路径和删除旧副本；其中 5 个 Review 输入附件另按 4.1-C 处理，不计入这 62 个 Reference 原件。

#### B. 功能说明、测试案例和 Reference 清单原件：23 个

| 法域 | 源文件 | 数量 | 目标原件目录 | 转换版目录 | 当前状态 |
|---|---|---:|---|---|---|
| CN | 4 个功能说明 + 任务 1-3 的 3 个独立测试案例 + 1 个三路径流程 + 1 个 Reference 清单 | 9 | `benchmarks/source-materials/cn/legacy-docx/` | `resources/research/module-specs/cn/<module>/` | Review 测试预期在附件子目录，单列 4.1-C；其余需逐版核对 |
| EU | SCC/BCR/DPIA/TIA 各功能说明和测试案例 + EU Reference 清单 | 9 | `benchmarks/source-materials/eu/legacy-docx/` | `resources/research/module-specs/eu/<module>/` | 9 个同 Hash |
| US | 14117/CPRA 各功能说明和测试案例 + US Reference 清单 | 5 | `benchmarks/source-materials/us/legacy-docx/` | `resources/research/module-specs/us/<module>/` | 5 个同 Hash |

这里按文件实际合计为 23 份来源原件；另一个顶层重复诊断说明见 4.4。迁移时：

- 原始 DOCX 保存在 `benchmarks/source-materials/`，作为案例来源；
- `spec.md`、`test-cases.md`、`reference-catalog.md` 是可读转换版，保存在 `resources/research/module-specs/`；
- 两者 Hash/转换来源写入各模块 README 或 source-material manifest；
- 不将功能说明或测试预期加入法规 RAG。

#### C. Review 测试输入样件：5 个

源目录：

`中国数据出境路径/任务4.../“文档专项智能审查”测试案例及预期输出/`

逐文件目标：

| 文件 | 目标 |
|---|---|
| `数据安全及保密协议（模板） (1).docx` | `benchmarks/source-materials/cn/review/fixtures/数据安全及保密协议模板.docx` |
| `隐私政策样例.PNG` | `benchmarks/source-materials/cn/review/fixtures/隐私政策样例.png` |
| `数据处理协议样例.pdf` | `benchmarks/source-materials/cn/review/fixtures/数据处理协议样例.pdf` |
| `个人信息出境标准合同【模板】.docx` | `benchmarks/source-materials/cn/review/fixtures/个人信息出境标准合同模板.docx` |
| `“文档专项智能审查”测试案例及预期输出.docx` | `benchmarks/source-materials/cn/legacy-docx/“文档专项智能审查”测试案例及预期输出.docx` |

前四个当前在 `resources/legal/sources/cn/references/` 有同 Hash 副本，但它们在该场景中的真实职责是 Benchmark 输入附件，不是法律依据。迁移时先更新 `review` Scenario/fixture 路径，再决定法律来源目录是否仍需为其他合法用途保留；禁止同一测试附件同时冒充法规来源。

### 4.2 区域法规：61 个

#### A. 51 个 PDF 原件

| 法域 | 数量 | 当前源目录 | 最终目标目录 |
|---|---:|---|---|
| SG | 6 | `知识库补充/新加坡/*.pdf` | `resources/legal/sources/sg/references/` |
| VN | 6 | `知识库补充/越南/*.pdf` | `resources/legal/sources/vn/references/` |
| MY | 8 | `知识库补充/马来西亚/*.pdf` | `resources/legal/sources/my/references/` |
| JP | 9 | `知识库补充/日韩/日本/*.pdf` | `resources/legal/sources/jp/references/` |
| KR | 7 | `知识库补充/日韩/韩国/*.pdf` | `resources/legal/sources/kr/references/` |
| HK | 7 | `知识库补充/港澳台/香港/*.pdf` | `resources/legal/sources/hk/references/` |
| MO | 3 | `知识库补充/港澳台/澳门/*.pdf` | `resources/legal/sources/mo/references/` |
| TW | 5 | `知识库补充/港澳台/台湾/*.pdf` | `resources/legal/sources/tw/references/` |

所有 PDF 保留原始 basename，先 `git mv`，后更新 `sources.csv` 的原件/快照路径。越南网络安全法 17.2 MB，先核对仓库大文件政策；只有 Git 服务确实配置 LFS 时才使用 LFS，不能只写 `.gitattributes` 假装已解决。

当前状态是 `INGESTED_NOT_CANONICAL`，原因包括：

- `ingest_regional_laws.py` 仍硬编码读取 `resources/new/知识库补充`；
- 区域 JSONL 条目只有约 5 个字段，缺 `article_id` 等标准字段；
- `build_source_registry_from_sources_csv()` 明确过滤非 CN/EU/US；
- V3 只有 `legal_index_cn/eu/us`，区域法条不能进入统一检索；
- `sources.csv`/手工 registry 中部分标题、版本和实际 2025/2026 PDF 名称需要逐文件复核，不能假设已一一对应。

#### B. 10 个目录文件

每个地区包的 `.html` 和伪 `.md` 文件 SHA-256 完全相同，且 `file` 均识别为 HTML。逐组只保留 `.html`：

| 源文件对 | 目标 |
|---|---|
| `新加坡相关法规目录.{html,md}` | `resources/legal/catalog/source-packets/regional/sg.html` |
| `日韩相关法规目录.{html,md}` | `resources/legal/catalog/source-packets/regional/jp_kr.html` |
| `港澳台相关法规目录.{html,md}` | `resources/legal/catalog/source-packets/regional/hk_mo_tw.html` |
| `越南相关法规目录.{html,md}` | `resources/legal/catalog/source-packets/regional/vn.html` |
| `马来西亚相关法规目录.html` + `马来西亚相关法规目录md.md` | `resources/legal/catalog/source-packets/regional/my.html` |

HTML 只作为来源核验包和 URL 追溯证据；生产查询仍以 `sources.csv` 和 registry 为准。重复扩展名副本在 Hash 验证后退出。

### 4.3 黄金标准与种子案例：51 个

#### A. 黄金标准定义文件：1 个

源：`数规通黄金标准与种子案例/数规通黄金标准（v1.0 正式版） .docx`

目标原件：

`benchmarks/datasets/seed-cases-v1/_source/数规通黄金标准_v1.0.docx`

迁入后不得直接把文档里的文字当自动断言。需要形成：

- `benchmarks/datasets/seed-cases-v1/rubric.v1.json`；
- `rubric-provenance.json`，记录原件 Hash、段落/表格定位、转换者和法律审核状态；
- `README.md`，明确 Gold 边界和未确认字段。

#### B. 50 个种子案例 DOCX

每个任务 5 例，目标规则：

```text
resources/new/.../任务N.../任务N_案例M_测试结果.docx
→ benchmarks/datasets/seed-cases-v1/_source/taskNN/taskNN_caseM.docx
```

结构化产物：

```text
benchmarks/datasets/seed-cases-v1/
├── _source/task01...task10/       # 50 个原始 DOCX
├── inputs/taskNN_caseM.input.json # 从“一、用户输入”抽取
├── expected/                      # 法律审核后才允许写入
├── manifest.json
├── rubric.v1.json
└── README.md
```

现有 `scripts/build_seed_case_inputs.py` 已设计为只抽取 input，且明确 `0 published / 50 pending_authoring`，但当前输出目录只有已迁移的分数汇总表，尚未生成 50 个 inputs。脚本必须先改用新 `_source/` 路径，再执行 `--write`。任务 4、6、7、8 的 `module_id`/业务命名存在冲突，未裁决前不得接入正式测试 runner。

### 4.4 顶层 5 个文件，以及功能包内 1 个关联重复文件

本节有 6 行处置记录，但不会给 207 重复计数：其中嵌套诊断说明已经计入 4.1-B 的 23 个文件；本节只额外计入根目录 PRD 1、根目录重复诊断说明 1 和台账 3，共 5 个顶层文件。

| 当前文件 | 目标/处置 | 理由 |
|---|---|---|
| `《数规通（DataComplyFlow）需求说明书》.docx` | `resources/research/product-design-sources/00_index/99_ORIGINAL_003_DataComplyFlow需求说明书.docx` | 原始产品设计输入，不是当前代码事实 |
| 根目录 `“合规路径诊断”功能说明...docx` | 与嵌套同 Hash；保留一个版本化来源原件，另一个 `DEDUP_DROP` | 避免两个“canonical”原件 |
| 嵌套 `任务1/.../“合规路径诊断”功能说明...docx` | `benchmarks/source-materials/cn/legacy-docx/“合规路径诊断”功能说明与路径描述_117a0267.docx` | 当前已有同名文件 Hash 不同，不能覆盖；必须并列版本化并裁决 |
| `manifest.intake.v1.json` | `resources/research/migration-ledger/resources-new-20260807/` | 历史机器盘点，不是运行配置 |
| `analysis.phase1.json` | 同上 | 历史分析证据 |
| `decisions.v1.jsonl` | 同上 | 保留 A001-A008 决策链 |

PRD 迁移后另外形成 `docs/handoff/DataComplyFlow_需求基线与当前实现映射_20260812.md`，但该 Markdown 是重新核对代码后的维护版，不是 DOCX 的复制粘贴版。

## 五、目标目录迁移后的必做工作

### 5.1 `resources/legal/sources/<jurisdiction>/references/`

- [ ] 每个原件有 SHA-256、来源 URL、权威机关、发布日期、生效日期、状态和语言；
- [ ] `sources.csv` 的 `snapshot_path`/原件路径和 `origin_path` 不再指向 `resources/new`；
- [ ] 同一法规只保留一个 source_id；修订版用状态和版本关系表达；
- [ ] 模板、指南、法律、条例、标准的 `source_kind`/`doc_type` 不混淆；
- [ ] 区域 51 个 PDF 与 CSV/registry 一对一对账，多行或缺行均失败。

### 5.2 `resources/legal/catalog/` 和 `registry/`

- [ ] 扩展 `build_source_registry_from_sources_csv()`，不能再静默过滤 8 个区域法域；
- [ ] 区域条文补齐 `article_id`、`path`、`doc_type`、日期、状态、来源路径、layer 和 priority；
- [ ] `regulation_articles.jsonl` 全量通过 `regulation_article.schema.json`；
- [ ] registry 改为 CSV 单向生成，退出手工追加双权威状态；
- [ ] source catalog、registry、JSONL 的 source_id 集合建立一致性门禁；
- [ ] 重新生成来源 manifest，禁止把运行时向量文件提交为资源原件。

### 5.3 RAG 与前端知识库

先明确产品策略：区域法域是“可浏览条文”还是“可参与模块法律 grounding”。在策略确认前，不得把全部区域法律塞进 CN/EU/US 索引。

推荐第一阶段：

- 建立 `legal_index_intl`，保存区域条文；
- Evidence Center 按 `jurisdiction` 浏览和搜索；
- 现有 11 模块默认索引不自动加入 `legal_index_intl`；
- 模块明确请求第三国法/TIA 时，按目标国家有条件检索；
- 增加区域法域检索 benchmark 和 hard negatives。

### 5.4 `resources/templates/`

- [ ] 对每个候选原始模板建立 provenance：原件路径、Hash、适用法规版本；
- [ ] 与 `official_template_schema.json` 或模块模板 Schema 对齐；
- [ ] 校验 DOCX 占位符、Markdown 占位符和 Report IR 字段；
- [ ] DOCX/PDF/Markdown 同源渲染和视觉验收通过后才标记 active；
- [ ] 原始官方模板和项目生成模板不得互相覆盖。

### 5.5 `resources/research/`

- [ ] 更新 `resources/research/README.md` 和 product-design source catalog；
- [ ] 为 PRD 写来源日期、Hash、权威性和“不得作为当前实现事实”说明；
- [ ] module-specs 的 Markdown 记录转换来源 Hash和转换日期；
- [ ] 生产代码/RAG 搜索不得出现 `resources/research` 消费者；
- [ ] migration ledger 的旧路径只作历史证据，不参与零引用门禁。

### 5.6 `benchmarks/source-materials/`

- [ ] 为迁移后的全目录 30 份有效来源原件建立 `source-materials-manifest.csv`：当前 24 份 + 新增 1 份异 Hash 诊断版本 + 5 份 Review 文件；本轮 23 份功能/案例/清单中已有 22 份属于当前 24 份，不能重复计数；
- [ ] 字段至少含 `asset_id`、法域、模块、source_path、canonical_path、SHA-256、版本、用途和敏感信息状态；
- [ ] 所有 `benchmarks/cases/*/scenario.json` 的 `provenance.file` 改为规范来源路径；
- [ ] 后端 CLI `source_doc_path`、前端 E2E fixture、`config/dev_case_catalog.json` 同步切换；
- [ ] Review 附件角色、文件名和 Hash 与 Scenario 一致；
- [ ] 运行 `check_case_parity.py`，修改任何来源路径都不能改变业务事实。

### 5.7 `benchmarks/datasets/seed-cases-v1/`

- [ ] 50 个原件数量和 Hash 完整；
- [ ] 50 个 input JSON 可重复生成；
- [ ] expected 继续为空或 `pending_authoring`，直到法律专家逐例签署；
- [ ] 任务 4/6/7/8 的模块映射冲突有显式裁决；
- [ ] placeholder、乱码、短输出和 prompt 污染标记保留；
- [ ] 不把原作者输出直接宣称为系统 Gold；
- [ ] 数据集 Schema、manifest 和执行器测试通过后才接入 CI。

### 5.8 `docs/`

- [ ] `handoff` 需求映射逐条标注 `implemented/partial/not_implemented/obsolete/conflict`，并附代码和测试地址；
- [ ] 若 PRD 中某条规则要升级为活动工程规范，必须单独人工批准后更新现有 `docs/standards/`，不得新增重复规范；
- [ ] 完成后在 `archive/governance/executed-batches/` 保存执行记录；
- [ ] `docs/README.md` 和 `docs/handoff/README.md` 增加导航；
- [ ] docs 不保存 207 个原始二进制副本。

## 六、代码和配置的路径切换清单

当前活动依赖仍包括：

- `scripts/ingest_regional_laws.py`；
- `scripts/build_seed_case_inputs.py`；
- `scripts/phase1_generate_intake_manifest.py`、`phase1_analyze_manifest.py`；
- 13 个后端 CLI case JSON；
- 22 个共享 Scenario；
- `config/dev_case_catalog.json`；
- `frontend/tests/e2e/pipia-shared-cases-local.e2e.ts`；
- `frontend/src/lib/dev-test-cases.ts` 中的来源说明。

切换顺序：

1. 先创建/核对目标文件并固定 Hash；
2. 修改脚本消费者；
3. 修改 Benchmark/CLI/前端来源路径；
4. 运行定向和全量测试；
5. `rg "resources/new"` 只允许命中迁移历史文档；
6. 再移除旧副本和空目录。

禁止先删除 `resources/new` 再修测试，因为大量 Scenario 和 CLI case 会立即失去来源证据。

### 6.1 可定位的代码证据

| 事实 | 当前代码证据 | 迁移含义 |
|---|---|---|
| 区域入库仍以旧目录为源 | `scripts/ingest_regional_laws.py:23-26` 将 `PDF_BASE` 固定为 `resources/new/知识库补充` | 51 个 PDF 移动前必须先让脚本读取规范法域目录或 manifest，随后做 51/51 dry-run 对账 |
| registry 会丢弃区域法域 | `backend/common/knowledge/registry.py:195-205` 只接受 `cn/eu/us` | 只移动 PDF 不会让区域来源进入可重建 registry；必须先扩 Schema 和模块映射策略 |
| 前端知识检索只查询三法域索引 | `backend/services/knowledge_projection.py:413-425` 固定 `legal_index_cn/eu/us` | 需要明确 `legal_index_intl` 或按法域动态索引的 API 行为，并增加前端浏览回归 |
| V3 只构建已注册的固定索引集合 | `backend/common/rag/ingest.py:96-105` 遍历 `INDEX_NAMES`，当前 registry/orchestrator 仅定义 CN/EU/US legal index | 区域 JSONL 已存在不等于 V3 可检索，必须补 builder、manifest、索引新鲜度和检索测试 |
| Seed 脚本仍读取旧目录 | `scripts/build_seed_case_inputs.py:37-39` | 原件归位后必须先切换 `SRC_DIR`，否则 50 个输入无法重建 |
| Seed 输出不是法律 Gold | `scripts/build_seed_case_inputs.py:22-24,138-142,178,202-206` | 只能生成 input 和质量标记；expected 必须继续经法域法律审核签署 |
| source-materials 当前为 24 份 | `benchmarks/README.md:7-10`，并可由磁盘清单复算 | 迁移后应为 30 份，而不是把本轮 28 份简单追加成 52 份；manifest 必须按 Hash 去重 |
| `docs/` 不是资源仓库 | `docs/README.md:29-33` | docs 只保存事实快照和历史执行证据，不能成为法规、Gold 或测试附件的新消费者 |

行号用于本方案审计日期下的定位；正式执行记录应同时保存 commit/blob 或文件 Hash，避免后续代码移动导致行号失效。

## 七、分阶段实施计划

### Phase 0：冻结与新台账

- 生成当前 207 文件的 `manifest.v2.json`：路径、大小、MIME、SHA-256、asset_class、target、status；
- 将 2026-08-07 三份旧台账移入 migration ledger；
- 对 89 个同 Hash 文件记录 `COPIED_HASHED`，不重复复制；
- 对 diagnosis 两个同 Hash 原件和现有不同 Hash 目标做版本裁决。

验收：207/207 均有唯一 disposition；分类数量总和严格等于 207。

### Phase 1：规范副本引用切换

可并行按 CN/EU/US 三组执行：

- 法规/模板来源路径切换；
- 22 个共享 Scenario 和 13 个 CLI case 路径切换；
- Review fixture 职责纠正；
- `config/dev_case_catalog.json` 更新。

验收：89 个已有规范副本不再依赖 `resources/new`，Hash 不变，case parity 全过。

### Phase 2：区域法规原件归位和 Schema 修复

8 个法域可并行搬原件、核对 metadata；公共 Schema、registry builder 和索引设计必须先统一后串行合并。

验收：51/51 原件归位；CSV、registry、JSONL 一致；区域浏览/搜索 benchmark 通过。

### Phase 3：Gold 与 50 个种子案例

- 迁移 51 个原件；
- 更新并运行 `build_seed_case_inputs.py`；
- 生成 input/manifest；
- 法律审核按法域并行，expected 逐例发布。

验收：原件 50、input 50、Hash 50；Gold 发布数按真实签署数量报告，不要求用伪 expected 凑 50。

### Phase 4：PRD、研究材料和 docs 维护版

- PRD 原件进入 research；
- 生成功能/需求到当前模块、API、表单、规则、产物和测试的映射；
- 更新 module-specs 和 source catalogs；
- 形成 handoff 快照。

验收：每条需求有状态和代码/测试证据；原始需求不得覆盖当前事实。

### Phase 5：旧目录退出

- 全量路径扫描；
- 全量测试、RAG/引用/Benchmark/前端构建；
- 核对最终 manifest 和目标 Hash；
- 删除 6 个 `.DS_Store`、已验证重复副本和空目录；
- 写入 status/check 验收和 docs/archive 执行记录。

验收：`resources/new` 不再被活动代码、配置、测试或脚本读取；目录为空后才允许删除。

## 八、验证矩阵

| 层 | 必须验证 |
|---|---|
| 文件 | 数量、MIME、SHA-256、无覆盖、无静默丢失 |
| 目录契约 | `backend/core/tests/test_resource_paths.py`、README 路径一致 |
| 法规 catalog | CSV/registry/JSONL source_id 集合和 Schema 一致 |
| RAG | V3 manifest、区域检索 benchmark、引用 source_id 可解析 |
| 模板 | Schema/占位符、Report IR、多格式和视觉验收 |
| Benchmark | 22 Scenario、26 CLI cases、case parity、附件 Hash |
| Seed cases | 50 inputs 可重复生成、expected 未经签署不得发布 |
| 前端 | dev cases、上传、引用、知识库浏览、构建 |
| 文档 | docs 导航、事实时态、无重复活动规范 |
| 退出 | 活动范围 `rg "resources/new"` 为 0，历史证据除外 |

建议命令必须使用项目环境：

```bash
uv run --frozen python ...
uv run --frozen pytest -q ...
```

本机裸 `python` 当前会在中文工作目录触发 Anaconda site 初始化的 ASCII `UnicodeDecodeError`，不能作为迁移脚本执行入口。

## 九、关键风险和禁止操作

1. 禁止 `mv resources/new/* resources/legal/`：会把 PRD、测试答案和 Gold 污染生产 RAG。
2. 禁止按文件名覆盖：诊断说明已经存在同名不同 Hash 版本。
3. 禁止把 50 个作者输出直接命名为 `expected.json`：现有脚本明确要求法律签署。
4. 禁止保留手工 registry 与 CSV 双权威：重新生成会丢失区域条目。
5. 禁止将区域法规无条件加入所有模块 RAG：会造成法域污染。
6. 禁止把原始 PRD 放入 `docs/standards/`：它包含目标要求，不等于当前工程规范或实现事实。
7. 禁止用 `git add .` 提交：当前工作区存在大量其他并行改动和生成产物。
8. 禁止在用户确认前远程部署；本方案全部验收先在本地完成。

## 十、完成定义

- [ ] 当前 207 个有效文件逐一有最终 disposition 和目标；
- [ ] 89 个同 Hash 资产完成消费者切换并退出旧副本；
- [ ] 51 个区域法规原件规范归位，metadata/Schema/registry/V3/前端闭环；
- [ ] 10 个重复目录文件只保留 5 个规范 HTML 来源包；
- [ ] PRD、Gold、50 个种子案例和 3 个旧台账进入正确职责目录；
- [ ] 50 个 seed input 生成完成，expected 只按法律签署发布；
- [ ] 所有 Scenario、CLI、E2E 和 catalog 不再引用 `resources/new`；
- [ ] `resources/new` 为空且无活动消费者后删除；
- [ ] `status/check/` 有逐批验收，`docs/archive/` 有最终执行记录；
- [ ] 未连接远程、未部署，远程动作继续等待用户明确授权。
