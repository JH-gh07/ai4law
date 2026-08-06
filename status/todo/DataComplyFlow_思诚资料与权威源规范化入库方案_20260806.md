# DataComplyFlow 思诚资料与权威源规范化入库方案

> 文档性质：资料接收、鉴别、去重、入库和验收的实施方案
>
> 编制日期：2026-08-06
>
> 适用范围：`resources/new/` 下 8 组新增资料，以及由这些资料派生的法规、模板、模块说明和 Benchmark
>
> 关联规范：`docs/standards/DataComplyFlow_仓库治理原则与经验.md`、`docs/standards/DataComplyFlow_活动架构与权威源.md`
>
> 命名说明：本方案沿用需求沟通中的“思诚资料”称呼；已收到的需求说明书版本记录署名为“王思成”。正式登记时以原件署名为准，不据此推断两者是否为同一人。

## 〇、一句话结论

`resources/new/` 只能作为**接收隔离区**，不能被运行代码、RAG 索引或报告生成器直接读取。所有资料必须先完成来源登记、SHA-256 去重、法律效力与版权判断、模块映射和专家复核，再分别进入 `resources/legal/`、`resources/templates/`、`resources/research/` 或 `benchmarks/`。原始 ZIP 与原始文档保留不可变副本，生产侧只消费登记过的规范化资产。

本方案的目标不是把 8 个文件夹“搬整齐”，而是建立一条可审计的单向链路：

```text
接收隔离 → 清单与哈希 → 来源/效力分级 → 去重与版本判断
→ 拆分为法规、模板、模块说明、Benchmark、研究材料
→ 注册表登记 → 索引/运行时接入 → 专家验收 → 封存原始件
```

## 一、必须遵守的边界

### 1.1 权威源只有一套

| 内容 | 唯一运行权威位置 | 不允许的做法 |
|---|---|---|
| 模块稳定身份 | `config/module_registry.json` | 从 ZIP 文件名或模板名临时推导新模块 ID |
| 法规与法条语料 | `resources/legal/`，来源主表为 `resources/legal/catalog/sources.csv` | 把实务手册、案例、产品说明直接当法规引用 |
| 静态规则 | `resources/rules/` | 在 `resources/new/` 中并行维护一份规则 |
| 运行时报告模板 | `resources/templates/{cn,eu,us}/` | 让模块从 `resources/new/` 或研究目录读取模板 |
| 模块需求、流程、来源说明 | `resources/research/module-specs/` | 把需求说明书当生产规则或法条 |
| 评测输入、Gold、断言 | `benchmarks/` | 把 Gold 写入生产法规索引或 `storage/` |
| 原始交接材料 | `resources/research/product-design-sources/` 及其接收子目录 | 原 ZIP 解压后直接覆盖现有活动目录 |

### 1.2 四种事实必须分开

每个可接收入库的文件必须标注以下四种 `asset_class` 之一，禁止仅按扩展名分类：

- `legal_authority`：有明确发布机关、版本、生效日期和可核验来源，可作为法条依据。
- `runtime_template`：经过产品确认、与模块输出契约一致，可以被运行时加载。
- `benchmark_gold`：用于评测或回归，包含输入、期望输出或断言，不是生产知识。
- `research_reference`：需求、手册、案例、流程解释或未核验材料，只能供研究和人工复核。

来源不明、疑似敏感、版权状态不清或同名但版本不明不是第五种资产类别，而是处置状态 `disposition=sensitive_or_unknown`。该状态优先于 `asset_class`，命中后停止自动入库。

### 1.3 接收区的唯一目录结构

本批资料统一使用以下接收结构，不再使用含义不明的“原 ZIP 归档”表述：

```text
resources/research/intake/2026-08-04-sicheng/
├── originals/                 # 原始 ZIP/DOCX/PDF；只读，不被运行时读取
├── extracted-inventory/       # 解压后的清单和哈希，不保存第二份活动资产
├── candidates/                # 待核验、尚未进入权威源的候选资料
├── approvals/                 # 法律、产品、版权/数据安全审批记录
├── manifest.intake.v1.json    # 接收时事实快照，生成后不可修改
├── decisions.v1.jsonl         # 追加式处置、复核和迁移记录
└── module-mapping.v1.json     # 外部任务称呼到现有 module_id 的审计映射
```

`originals/` 只是逻辑归档位置。若版权、敏感性或体积策略不允许原件进入 Git，则目录中只保留 `README.md` 和 manifest，原件进入受控对象存储，manifest 记录 `external_uri`、哈希、访问级别和保管人。不得为了“完整”把受限标准、含个人信息的案例或 87 MiB 原始包直接提交到普通 Git。

## 二、8 组资料的规范化去向

以下路径是建议的最终去向。`resources/new/` 中的原始目录不作为运行时路径；迁移完成前不删除原件。

| 原始资料 | 性质判断 | 规范化去向 | 需要派生的登记/产物 |
|---|---|---|---|
| 《数规通需求说明书》DOCX | PRD、验收口径，不是法规 | 原件放入本批 `originals/`；审核副本归入 `resources/research/product-design-sources/requirements/2026-08-04/` | `docs/handoff/` 形成需求基线；可执行验收项进入 `benchmarks/` 或配置清单 |
| 《数据出境合规实务手册》PDF | 实务参考，不等于法条 | `resources/research/product-design-sources/practice-guides/` | 逐问答拆为带来源指针的研究条目；只有对应官方法规另行进入 `resources/legal/` |
| 黄金标准与种子案例 ZIP | Gold/测试资产 | 原 ZIP 放入本批 `originals/`；只有脱敏、可提交的规范化案例进入 `benchmarks/datasets/{module_id}/` | 每例 `case_id`、输入、期望结构、期望引用、断言、验证状态 |
| 知识库补充 ZIP | 多法域来源混合包 | 原 ZIP 放入本批 `originals/`；按法域拆入 `candidates/{jurisdiction}/`，核验后再进入法规或研究目录 | 每个可用来源建立登记；未核验材料不进生产索引 |
| GB/T 43697-2024 | 国家标准，需确认来源和使用范围 | 候选件进 `candidates/cn/standards/`；获准保存的权威副本进 `resources/legal/sources/cn/references/` | 发布日期、生效日期、标准号、发布机构、官方链接、哈希和版权使用范围 |
| GB/T 45574-2025 | 国家标准，2025-11-01 生效 | 同上，作为独立版本，不覆盖旧版本 | `effective_date=2025-11-01`；运行时按评估日期判断是否适用 |
| 功能路径/reference/流程/测试案例 ZIP | 需求、流程、参考资料和测试混合包 | 原件归研究来源；流程归 `resources/research/module-specs/`；测试归 `benchmarks/`；法规另行登记 | 建立“文件→module_id→用途→权威源”映射，禁止整包作为单一知识库 |
| 合规路径诊断说明 DOCX | 诊断流程说明和参考依据 | `resources/research/module-specs/cn/transfer_diagnosis/` | 形成决策树/字段说明；每个结论所需法条引用单独绑定 `source_id` |

### 2.1 法域与模块映射

规范化时必须使用现有稳定模块 ID，不因黄金标准出现新叫法就自动增设入口：

| 资料中的任务称呼 | 当前模块 ID | 处理原则 |
|---|---|---|
| 中国数据出境诊断 | `cn.transfer_diagnosis` | 进入诊断模块说明、规则和 Benchmark |
| 中国安全评估/自评估 | `cn.security_assessment` | 运行模板以官方自评估结构为唯一活动模板 |
| 中国 PIPIA/文档审查 | `cn.pipia`、`cn.document_review` | 分别映射，不用一个“通用中国模板”覆盖两者 |
| EU SCC/BCR/DPIA/TIA | `eu.scc_review`、`eu.bcr_review`、`eu.dpia`、`eu.tia` | 保持四个独立模块和各自模板/Gold |
| GDPR 合规诊断 | 暂无独立稳定入口 | 作为 `eu.dpia`/`eu.tia` 的流程前置能力或研究别名，先建映射，不直接注册新 API |
| BD ROD 判断 | 暂无独立稳定入口 | 先作为 Benchmark 子任务和研究说明，待确认产品边界后再决定是否成为模块 |
| 美国 EO14117/CPRA | `us.eo_14117`、`us.cpra`、`us.eo_14117_flow_review` | 按现有三个稳定身份映射，不能把历史 `cn_flow` 名称当法域身份 |

`module-mapping.v1.json` 每条必须包含 `external_task_id`、`external_task_name`、`target_module_ids`、`relation`（`mapped`/`partial`/`unmapped`）、`reason`、`source_asset_ids`、`approved_by` 和 `approved_at`。该文件只是外部材料到现有注册表的审计映射，不得反向生成或修改 `config/module_registry.json`。

## 三、统一资料清单与元数据

在移动任何文件前，先生成接收事实快照：

`resources/research/intake/2026-08-04-sicheng/manifest.intake.v1.json`

每个文件至少记录：

```json
{
  "asset_id": "SICHENG-20260804-0001",
  "original_path": "resources/new/数规通需求说明书.docx",
  "sha256": "...",
  "size_bytes": 727719,
  "received_at": "2026-08-06",
  "source_owner": "王思成",
  "source_package": "需求说明书",
  "asset_class": "research_reference",
  "jurisdiction": null,
  "module_ids": [],
  "authority_level": "product_requirement",
  "publication_date": "2026-08-04",
  "effective_date": null,
  "official_url": null,
  "license_or_usage": "待确认",
  "initial_disposition": "intake"
}
```

`manifest.intake.v1.json` 只记录接收时可观察事实，生成后不可改。会变化的目标路径、重复关系、复核结论、审批状态和迁移时间写入 `decisions.v1.jsonl`，每次追加一条带时间、责任人和前序记录哈希的事件。这样既保留原始证据，又允许状态演进；不得反复覆盖同一份 manifest。

法规或标准来源必须额外具备：`source_id`、标题、发布机关、文号/标准号、版本、发布日期、生效/失效日期、官方 URL、原文快照路径、语言、条款解析版本、`can_be_cited`、`allowed_usage`、`supersedes`/`superseded_by` 和复核人。没有这些字段的文件不得进入 `resources/legal/catalog/sources.csv`，也不得进入生产索引。

`resources/legal/catalog/sources.csv` 是来源事实的主表；`resources/legal/registry/source_registry.v1.json` 明确标注 `generated_from`，只能由主表生成，禁止两处手工同时维护。当前仓库缺少显式的 `--check/--write` 注册表生成命令，本批实施应优先补一个薄 CLI（复用 `backend.common.knowledge.registry.build_source_registry_from_sources_csv`），而不是增加第二套来源注册表。

### 3.1 规则的反向追溯

从法规或模块说明派生到 `resources/rules/` 的每条规则必须记录 `rule_id`、适用 `module_id`、`source_ids`、条号、适用条件、生效/失效日期、规则版本、复核人和对应测试案例。规则只能引用已发布来源；来源版本变化时，门禁必须列出受影响规则，不能只重建 RAG 索引而继续沿用旧判断。

## 四、去重与版本处理

### 4.1 同 Hash：只保留一个活动副本

对所有原始文件和解压文件计算 SHA-256。相同 Hash 的文件只选择一个权威存放位置，其余在清单中记录 `duplicate_of=asset_id`，不再复制到多个活动目录。原始 ZIP 仍可作为不可变证据保留，但不作为第二运行源。

### 4.2 不同 Hash：不得按文件名覆盖

同名或内容相似但 Hash 不同的文件必须比较：发布机关、版本号、发布日期、生效日期、语言、页数/条款数和用途。处理规则：

- 新旧法规均保留，但只有当前有效版本标记 `is_current_version=true`。
- 旧版本标记 `status=superseded`，保留 `superseded_by`，用于历史报告复现。
- 同一模板的官方原件、内部可填写版和产品渲染版必须分别标记来源，不得互相覆盖。
- 无法证明是新版本、修订版或不同用途时，标记 `needs_manual_review`，不自动删除。

### 4.3 原始包的生命周期

原始 ZIP/DOCX/PDF 在迁移验收前必须保持只读、可校验、可追溯。验收通过后仍保留其哈希和归档位置；是否从 Git 工作树移出，应由体积、版权和备份策略决定，不能通过“清空 `resources/new`”代替归档。

## 五、模板收敛方案

1. 每个已启用模块最多只能有一个活动模板入口；需要生成固定格式报告的已启用模块必须恰好有一个。没有权威模板的模块应显式标记 `template_status=missing`，不能挂载临时模板后宣称已覆盖。
2. 官方原始模板与产品渲染模板分离：原始件进入研究/来源目录，运行模板进入 `resources/templates/{cn,eu,us}/`，并在模板头部记录 `source_id`、版本和转换方式。
3. `cn` 自评估以官方三大章六小节结构为唯一基准。现有 `2.2_risk_assessment_template_v0.md` 若与其冲突，先迁移消费者和测试，再标记为 `legacy`，不得继续双源并存。
4. `diagnosis`、`document_review`、`PIPIA` 不应被强行包装成同一种报告模板：诊断以决策树 Schema 为主，审查以问题/证据/结论结构为主，PIPIA 以附件逐项映射为主。
5. 缺少权威模板的 EU SCC、DPIA 和中国诊断，不得用“看起来完整”的内部模板冒充官方模板；先登记缺口，模板来源和强制要素确认后再进入运行时。
6. 每个模板必须有最小契约：章节/字段、必填项、输出格式、固定免责声明、水印要求、法条引用位置、版本和测试案例。Markdown 模板可使用 front matter；DOCX/PDF 等二进制模板统一使用同名 `.metadata.json` sidecar，禁止依赖不可机器读取的文件属性。

## 六、Gold 与 评测案例规范化

黄金标准包必须拆成“原始证据”和“机器可执行 Gold”两层：

```text
原始 ZIP/原始文档（只在 intake originals 或受控对象存储）
  → 脱敏且获准提交的 benchmark fixture
  → benchmarks/datasets/{module_id}/case.json
     （输入指针、期望结构、期望引用、禁止引用、断言）
  → runner / parity gate / report
```

每例至少包含：

- 稳定 `case_id`、`module_id`、法域、任务别名和来源资产 ID；
- 脱敏输入文件及其哈希；
- 期望风险级别/路径/章节/输出角色等结构化结果；
- 每条法律结论的 `source_id`、条号和简短摘要；
- `known_defects`、`review_status`（`draft`/`lawyer_verified`/`published`/`rejected`）、复核人和复核日期；
- 规则断言与 LLM 断言分栏，规则断言在 `--no-llm` 下也必须执行；
- 禁止把“结果非空”作为唯一 Gold 断言。

法律复核、产品复核和数据/版权审批分别写入 `approvals/{asset_or_case_id}.{legal|product|data}.json`。每份审批至少记录结论、范围、复核人、时间、依据版本和签名/审计标识。Gold 只有三类审批满足所需范围后才能从 `draft` 升为 `lawyer_verified` 或 `published`。

黄金标准中的任务别名与产品入口不一致时，建立映射表并统计覆盖差距；映射不成立的任务保持 `unmapped`，不能通过复制模块或改名制造“已覆盖”。

## 七、分阶段执行清单

### 阶段 A：冻结与盘点

- [ ] 冻结当前 Git、测试和索引基线，记录提交号。
- [ ] 对 `resources/new` 全量生成路径、大小、MIME、SHA-256 清单。
- [ ] 解压到临时目录进行清单扫描，原始包保持不变。
- [ ] 输出同 Hash 重复表、相似名称表和来源不明表。

### 阶段 B：鉴别与映射

- [ ] 为每个资产填写 `asset_class`、法域、模块 ID、来源、版本和使用范围。
- [ ] 把需求、流程、手册、案例和法规分开，不允许整包入库。
- [ ] 将黄金标准 10 类任务映射到当前注册表中的 11 个稳定模块身份（10 个 `active`、1 个 `legacy-compatible`），标记 `mapped`/`partial`/`unmapped`。
- [ ] 对 GB/T 43697-2024、GB/T 45574-2025 建立版本和生效日期记录。

### 阶段 C：权威源入库

- [ ] 仅将官方可核验法规/标准登记到 `resources/legal/catalog/sources.csv`，再生成 `source_registry.v1.json`。
- [ ] 生成法规快照与条款索引，保留原文哈希和官方 URL。
- [ ] 实务手册和研究资料不得获得 `can_be_cited=true`，除非另有法源确认。

### 阶段 D：模板与规则收敛

- [ ] 为每个需要固定格式报告的运行模块指定唯一活动模板和版本；其余模块显式声明 `not_required` 或 `missing`。
- [ ] 迁移模板消费者、补齐模板契约测试，确认固定水印/免责声明的位置。
- [ ] 对冲突 v0 模板执行“迁移→测试→标记 legacy→删除或归档”，不得继续双源并存。

### 阶段 E：Benchmark 接入

- [ ] 将 Gold 转为 `benchmarks/datasets/` 规范案例，补齐结构化断言和引用绑定。
- [ ] 更新案例清单、模块覆盖统计和已知缺陷清单。
- [ ] 运行离线 harness；不把评测结果写入生产法规索引。

### 阶段 F：封存与清场

- [ ] 全仓扫描代码、配置、测试和文档对 `resources/new` 的引用，结果必须为零或仅限迁移文档。
- [ ] 清除活动目录中的同 Hash 重复副本，保留 manifest 中的 provenance。
- [ ] 将接收区改为只读归档或移出源码工作树，并保留恢复路径。
- [ ] 更新唯一活动规范和 `docs/handoff/` 事实记录；不自动提交 Git，先人工复核变更清单。

## 八、自动验收门禁

入库完成前必须全部满足：

1. `resources/new` 没有运行时消费者，RAG/模板/报告路径不会读取该目录。机器扫描范围为 `backend/`、`frontend/src/`、`config/`、`scripts/` 和活动测试；文档中的历史文字引用不计为运行时消费者。
2. 每个活动法规文件都能追溯到 `source_registry`，具备哈希、来源 URL、版本和生效日期。
3. 活动资产根 `resources/legal/`、`resources/rules/`、`resources/templates/` 和 `benchmarks/datasets/` 中不存在未解释的同 Hash 重复文件；intake 原件和外部归档不计为第二活动副本。
4. 每个已启用模块最多一个活动模板；要求固定格式报告的模块恰好一个。冲突模板有迁移和退役记录。
5. 注册表中的 11 个稳定模块身份、黄金标准 10 类任务和 Benchmark 案例之间的映射可从 `module-mapping.v1.json` 机器统计；其中 1 个 `legacy-compatible` 身份单独显示，缺口显式为 `partial` 或 `unmapped`。
6. 每个 Gold 结论都绑定法规名、条号、摘要和 `source_id`；无法绑定的结论进入人工复核队列，不得伪造引用。
7. `effective_date` 未到时不进入适用规则；已失效来源不能被当前报告引用。
8. 运行测试通过：资源路径/注册表校验、模板契约测试、案例对等门禁、离线 Benchmark、前端构建和 `git diff --check`。
9. 版权、隐私和敏感性未确认的文件不进入 Git 生产资产；至少保留拒收原因和负责人。

### 8.1 可复现检查命令

本批至少执行并记录以下命令。含空格和中文的路径必须使用 NUL 分隔，避免清单漏项：

```bash
find resources/new -type f -print0 | xargs -0 shasum -a 256
rg -n "resources/new" backend frontend/src config scripts
uv run --frozen python scripts/build_regulation_articles.py
uv run --frozen python scripts/check_case_parity.py
uv run --frozen pytest backend benchmarks
npm test --prefix frontend
npm run build --prefix frontend
git diff --check
```

另需新增或补齐以下门禁脚本后再宣布完成：

- `scripts/build_source_registry.py --check/--write`：从 `sources.csv` 单向生成并核对运行注册表；
- `scripts/check_resource_intake.py`：校验 intake manifest、决策链、哈希、重复和审批状态；
- `scripts/check_module_material_mapping.py`：校验 11 个稳定身份、外部任务别名、模板和 Gold 覆盖；
- `scripts/check_template_authority.py`：校验每个已启用模块的活动模板数量、sidecar、版本和来源。

## 九、回滚与责任边界

- 任一步骤失败时，只回滚本批新增的登记和派生文件，不回滚用户已有修改，不覆盖现有活动法规或模板。
- 旧模板只有在消费者迁移、测试通过和回滚路径确认后才能删除或标记退役。
- 法律效力、条款正确性、官方模板逐字一致性和 Gold 结论正确性必须由具备相应权限的人工复核人确认；工程门禁只能证明结构和可追溯性，不能替代律师核验。
- 本方案不承诺“新增资料全部有效”或“所有 11 个入口已满足需求”；它要求把缺口显式化，并阻止未验证资料悄悄进入生产。

## 十、完成定义

当且仅当以下结果同时成立，才可宣布本批资料“规范化入库完成”：

```text
manifest 完整
且 active 资产全部注册
且 resources/new 无运行时引用
且法规/模板/Gold/研究四类边界清晰
且重复与版本关系可解释
且模块与案例映射可统计
且资源、模板、Benchmark、全量测试门禁通过
且人工复核队列中不存在被误标为 published 的条目
```

否则状态只能写为“已盘点”“部分入库”或“待人工复核”，不得写成“已接入知识库”“已满足 PRD”或“法条引用准确率已达标”。
