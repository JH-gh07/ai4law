# DataComplyFlow v0.1 至 v1.0 升级与新增资料处置方案

> 文档性质：经仓库与原始资料交叉核对的实施版（v2）
> 编制日期：2026-08-07
> 代码基线：`new` 分支，`3389011`
> 软件基线：后端与前端版本均为 `0.1.0`
> 资料范围：`resources/new/` 下 219 个物理文件
> 前置规范：`status/todo/DataComplyFlow_思诚资料与权威源规范化入库方案_20260806.md`

## 〇、结论与决策摘要

`resources/new/` 是一批混合的产品、法律、评测和研究资料，不是可以整包导入的“v1.0 升级包”。成熟的升级路径应当是：

```text
先冻结当前 10 个活动模块 + 1 个兼容模块的真实基线
→ 完成 219 份资料的不可变登记与权利/效力复核
→ 裁决黄金标准正文与 50 个种子案例的任务分类冲突
→ 复用现有 Schema、HTTP、浏览器和 CLI harness 门禁建立可信基线
→ 新法域按“候选→影子索引→专家验收→生产”逐个晋级
```

v1.0 不应默认承诺一次上线 8 个新法域。建议把 v1.0 定义为“现有中/欧/美 10 个产品任务的契约稳定、黄金标准基线和可审计知识入库闭环”；8 个新法域作为独立发布列车，v1.0 最多纳入 1 个影子试点，不对外宣称生产可用。

| 决策 | 建议 | 理由 |
|---|---|---|
| v1.0 业务范围 | 锁定现有 CN/EU/US 10 个正式任务 | 代码已有对应实现，但业务质量尚未通过新 Gold 证明 |
| 历史 `cn_flow` | 仅保留兼容，不计为第 11 个业务任务 | 其实际身份是 `us.eo_14117_flow_review` |
| 50 个种子案例 | 先隔离、映射和专家复核，不直接转成 CI Gold | 其中 20 例的任务名与 Gold 正文/功能规格冲突 |
| 8 个新法域 | 逐法域晋级，建议新加坡先做影子试点 | 技术可解析不等于法律可上线 |
| 知识库改造 | 在现有公开 API 内收敛为单一配置驱动管道 | 避免 `builders_v2`/`builders_v3` 长期双轨漂移 |
| 发布时间 | Phase 2 完成后再锁日期 | 当前关键路径是资料冲突裁决和法律复核，不是纯工程工时 |

## 一、事实审计与原方案修正

### 1.1 资料盘点

2026-08-07 以 `find` 对 `resources/new/` 按物理文件复核：

| 项目 | 实测数量 | 说明 |
|---|---:|---|
| 全部文件 | 219 | 含隐藏文件和 Office 临时文件 |
| `知识库补充/` | 67 | 51 PDF + 5 Markdown + 5 HTML + 6 `.DS_Store` |
| `数规通功能路径描述.../` | 90 | 功能说明、流程、案例和 Reference 混合 |
| `数规通黄金标准与种子案例/` | 57 | 包含 50 个案例 DOCX、1 个 XLSX 及基准材料 |
| 根目录单文件 | 5 | PRD、诊断说明、实务手册、2 份 GB/T 文件 |
| 扩展名分布 | 111 PDF / 89 DOCX / 1 DOC / 1 XLSX / 1 PNG / 5 MD / 5 HTML / 6 DS_Store | 1 个 `~$...docx` Office 临时文件包含在 89 个 DOCX 内 |
| 明确噪声 | 7 | 6 个 `.DS_Store` + 1 个 Office 临时文件，不是“约 56 个杂项” |

知识库补充实际涉及 8 个新法域/地区，共 51 个 PDF 候选件：

| 法域 | VN | JP | KR | SG | HK | MO | TW | MY | 合计 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PDF 物理文件 | 6 | 9 | 7 | 6 | 7 | 3 | 5 | 8 | 51 |

这是物理文件数，不等于 51 部独立、现行、可引用法律。同一法律的新旧版本、修正法、生效公告、监管指引和本地 HTML/Markdown 索引页必须分开定性。

### 1.2 四类版本号必须分开

| 版本对象 | 当前事实 | v1.0 处理 |
|---|---|---|
| 软件 | `pyproject.toml` 和 `frontend/package.json` 均为 `0.1.0` | 由发布负责人在门禁通过后升为 `1.0.0` |
| PRD | 原件标注 `Version: 0.1.0` | 作为需求来源，不代替软件版本 |
| 黄金标准正文 | 原件名称为“v1.0 正式版” | 登记为 `gold-rubric-1.0`，不能倒推软件已满足 v1.0 |
| 案例/知识/索引 | 暂无统一可复现版本 | 分别建立 `dataset_version`、`kb_snapshot`、`index_build_id` |

每个评测运行必须记录软件提交、PRD 版本、Gold 版本、Dataset 版本、知识快照、索引构建 ID、Provider/模型和配置哈希。否则“v1.0 评测结果”无法复现。

### 1.3 当前代码并非“大量模块从零实现”

`config/module_registry.json` 已登记 11 个稳定身份：10 个 `active` + 1 个 `legacy-compatible`。

| 任务 | 当前实现包 | 身份状态 |
|---|---|---|
| CN 合规路径诊断 | `backend/domains/cn/transfer_diagnosis` | active |
| CN 安全评估 | `backend/domains/cn/security_assessment` | active |
| CN PIPIA/认证与标准合同评估 | `backend/domains/cn/pipia` | active，与资料任务 3 仍需语义对齐 |
| CN 文档审查 | `backend/domains/cn/document_review` | active |
| EU SCC | `backend/domains/eu/scc_review` | active |
| EU BCR | `backend/domains/eu/bcr_review` | active |
| EU DPIA | `backend/domains/eu/dpia` | active |
| EU TIA | `backend/domains/eu/tia` | active |
| US EO 14117 | `backend/domains/us/eo14117` | active |
| US CPRA | `backend/domains/us/cpra` | active |
| 历史 `cn_flow` | `backend/domains/us/eo14117_flow_review` | legacy-compatible，实际是 US EO 14117 流程审查 |

已有阶段验收记录表明：26 个前端案例可通过真实 HTTP 契约，11 个浏览器主路径可跑，15 个 CLI 案例在 `--no-llm` 下具有 259 条强断言。这些只能证明契约、离线规则和结构链路，不证明新 Gold 的法律正确性、真实 LLM/RAG/外部法律 API、Token/Time 或报告内容质量。

### 1.4 新资料内部存在 P0 任务分类冲突

功能路径规格和黄金标准正文相互一致，但 50 个种子案例的目录分类在 4 个任务上与之冲突：

| 任务号 | 功能规格 + Gold 正文 | 50 个种子案例目录 | 影响 |
|---|---|---|---|
| CN 任务 4 | 文档专项智能审查 | 豁免情形诊断 | 5 例不能自动归入 `cn.document_review` |
| EU 任务 6 | BCR 审核 | TIA 审查 | 5 例不能自动归入 `eu.bcr_review` |
| EU 任务 7 | DPIA 草案生成 | GDPR 合规诊断 | 5 例属于新能力或前置子任务 |
| EU 任务 8 | TIA 草案生成 | BD ROD 判断 | 缩写和产品边界未定，5 例保持 `unmapped` |

因此至少 20/50 个种子案例在产品负责人和法律负责人裁决前必须保持 `quarantined`。不允许通过改文件夹名、复制模块或放宽断言来制造“50/50 可执行”。

### 1.5 知识库存在两条管道和注册表漂移

当前知识层同时存在：

1. `builders_v2.py` → `backend/common/rag/orchestrator.py` 的 15 个静态 CN/EU/US 索引；
2. `IngestionPipeline` 的文件上传、解析、分块和数据库存储路径，当前对任意 `jurisdiction` 都使用 `ChineseLegalChunker`。

同时，`config/module_registry.json` 中的产品模块与 `backend/common/knowledge/registry.py` 的 `DEFAULT_MODULE_CATALOG` 不对齐：后者缺少 `cn.pipia`、`us.cpra` 和历史流程身份，却保留 `us_vendor_review`/`us_privacy_review` 等非产品注册身份。在该漂移消除前扩展 8 个新法域，会把一个已存在的双轨问题扩大。

### 1.6 原方案审核结果

| 问题 | 级别 | 成熟方案的修正 |
|---|:---:|---|
| 新法域、PDF、噪声文件数错误 | P0 | 以物理清单为准，法律效力另行复核 |
| 代码基线过期，把 BCR/DPIA/TIA/EO14117 判为未实现 | P0 | 改以 `module_registry.json` + 实现包 + 现有门禁为事实基线 |
| Gold 正文与种子案例冲突未识别 | P0 | 增加任务交叉表、冲突登记和人工裁决门禁 |
| 将 50 例直接转 pytest 并全过否决 | P0 | 分离确定性硬门禁、专家 Rubric 和校准后的 LLM Judge |
| 新建 `tests/gold_standard/` | P1 | 复用 `backend/tests/harness` 与现有 `benchmarks/datasets/`，不建第二套 runner |
| 新增 `builders_v3.py` 并让 v2/v3 长期并存 | P1 | 保持现有公开行为，逐步将 builder 与 chunker 参数化，完成等价性验证后删除特例 |
| 默认每法域生成 5 类索引 | P1 | 按 `asset_class` 和模块消费需求建索引，法律 PDF 不自动生成模板/案例索引 |
| 边移文件边清理原件 | P1 | 先生成 manifest/哈希/重复报告，再按版权和体积策略归档 |
| 在法律复核前宣称新法域可生产使用 | P0 | 使用法域晋级状态机，生产晋级必须有签字审批 |
| 8-12 周时间承诺无人力/复核前提 | P1 | Phase 2 后以实测基线和人力锁定发布日期 |

## 二、v1.0 发布定义

### 2.1 必须交付

1. 软件版本升级到 `1.0.0`，包含可复现的 release manifest 和回滚点。
2. 现有 CN/EU/US 10 个正式任务保持 Schema、HTTP、CLI 和浏览器门禁稳定。
3. PRD/Gold/功能规格/种子案例与 `module_id` 之间存在可机器统计的映射，冲突不被隐藏。
4. 219 个物理文件全部登记，但只有获得授权与复核的资产进入活动目录。
5. 已裁决和通过法律复核的 Gold 子集可机器执行；未决案例明确标记 `quarantined` 或 `unmapped`。
6. 每个法律结论可追溯至 `source_id` 和条款定位；待复核、已失效或未生效来源不进入当前结论。
7. 真实 Provider 受控验收覆盖 LLM、RAG、法律检索 API（如得理在验收环境已配置）、引用、Token/Time 和 Markdown/DOCX/PDF 输出。
8. 至少 1 个新法域完成影子索引试点和回滚演练；是否进入生产由独立发布决策确定。

### 2.2 明确不属于 v1.0 默认范围

- 一次上线 VN/JP/KR/SG/HK/MO/TW/MY 全部功能；
- 因“文件来自官方网站”就自动标记为现行、必须性或可二次分发；
- 把 PRD、实务手册、Gold 答案或测试案例放入生产法律索引；
- 在未完成专家复核和真实 Provider 测试时宣称“法条引用错误率为 0”或“判定准确率达 95%”；
- 为满足名称对齐而新增空模块、复制 API 或新建平行测试引擎。

## 三、单向治理架构

### 3.1 资料与生产知识分离

```text
resources/new/                         # 只读接收隔离区
  → manifest.intake.v1.json          # 219 份接收事实，不可变
  → decisions.v1.jsonl               # 去重、版权、效力、映射和审批的追加日志
  → approvals/                       # legal / product / data-security 三类审批
      ├─ legal_authority → resources/legal/catalog/sources.csv
      ├─ runtime_template → resources/templates/
      ├─ benchmark_gold  → benchmarks/datasets/
      └─ research_reference → resources/research/
```

任何运行时代码、RAG、报告渲染器或测试 runner 都不得直接读取 `resources/new/`。

### 3.2 法律知识的晋级状态机

```text
received
  → rights_cleared
  → source_verified
  → legal_verified
  → normalized
  → indexed_shadow
  → retrieval_accepted
  → production
  → superseded / withdrawn
```

跳级无效。`production` 必须同时具有：原文哈希、发布机关、官方 URL、版本/生失效日期、法律复核人、授权范围、原文/翻译区分、可引用条款定位、候选索引评测结果和回滚目标。

### 3.3 知识索引单向发布

```text
sources.csv（来源事实主表）
  → generated source_registry
  → parser + jurisdiction strategy
  → candidate chunks + validation report
  → versioned shadow index
  → retrieval/citation/temporal evaluation
  → atomic alias promotion
  → production index
```

生产切换必须使用版本化索引和原子别名，不得在活动索引上就地覆盖。回滚是将别名切回上一个已验证版本，不是重新解析一批 PDF。

## 四、分阶段实施计划

### Phase 0：基线冻结（0.5-1 天）

**工作**

- 记录分支、提交、Python/Node 依赖锁和当前索引哈希；
- 复验 Schema、26 HTTP 案例、11 浏览器主路径、15 CLI 案例和全量测试；
- 形成 `baseline-manifest.json` 和失败清单；
- 禁止在本阶段移动 99 MiB 左右的原始资料。

**Gate 0**：基线可重放，失败已区分为新增前就存在与本批引入两类。

### Phase 1：接收盘点与安全隔离（2-4 个工程日，审批时间另计）

**工作**

1. 为 219 份文件记录路径、MIME、大小、SHA-256、来源包和初始 `asset_class`。
2. 生成同 Hash 重复、同名异 Hash、加密/损坏文件、低文本提取率和 MIME/扩展名不一致报告。
3. 对 DOC/DOCX/XLSX/PDF 执行恶意内容、宏/外链、密钥/隐私信息和版权范围检查。
4. 从规范化候选集中排除 6 个 `.DS_Store` 和 1 个 Office 临时文件；原始接收快照只记录不作运行消费。
5. 在版权和 Git 体积策略决定前，不把全量二进制原件重复提交到新目录。

**Gate 1**：manifest 覆盖率 219/219；哈希可复算；每份资产都有处置状态；敏感/未知或版权待定资产未进入 Git 活动资产。

### Phase 2：需求、Gold 和模块契约裁决（3-5 个工程日 + 产品/法律复核）

**权威顺序**

1. `config/module_registry.json` 决定当前软件稳定身份；
2. PRD 和功能路径规格决定候选产品要求；
3. Gold 正文决定候选 Rubric，不直接改写 API；
4. 种子案例和分数汇总是待复核证据，不自动压过前三者。

**产出**

- `module-mapping.v1.json`：外部任务到稳定 `module_id` 的 `exact/partial/unmapped/conflict` 映射；
- `requirement-traceability.v1.csv`：PRD 章节→规格→Schema→代码→测试→Gold 条目；
- `conflict-register.v1.jsonl`：至少覆盖任务 4/6/7/8 冲突；
- `release-scope.v1.md`：明确 v1.0 交付与非目标；
- 产品、法律、工程三方审批记录。

**Gate 2**：任务 4/6/7/8 已裁决，或明确从 v1.0 Gold 中排除；未裁决项不得进入后续自动评分。

### Phase 3：Gold 规范化与可信评测（1-2 周 + 专家标注）

**实施原则**

- 原始 DOCX/XLSX 作为只读证据，规范化案例进入现有 `benchmarks/datasets/`；
- 复用 `backend/tests/harness/runner.py` 的 11 个 ModuleAdapter 和 `validators.py` 断言语义，不创建第二套 runner；
- 保留 `backend/tests/<alias>/cases/` 作为快速确定性回归，Gold 通过薄适配器调用同一服务与断言引擎；
- 评测集不进入 `testcase_index_*` 或任何生产 RAG，防止答案泄漏。

**案例状态**

```text
raw → extracted → mapped → dual_reviewed → adjudicated → published
                   └→ quarantined / rejected
```

**三层评分**

| 层 | 内容 | CI 地位 |
|---|---|---|
| 确定性契约 | Schema、枚举、必填字段、路径/风险级别、必须/禁止引用、输出产物 | 硬门禁，100% 通过 |
| 专家 Rubric | D1-D6、关键否决项、事实完整性、法律应用与职业表述 | 关键否决项为硬门禁；总分基于冻结基线设棘轮 |
| LLM-as-Judge | 规模化辅助评分 | 校准前仅 advisory，不能单独阻断发布 |

至少两名对应法域复核人独立标注，分歧由第三人裁决。LLM Judge 必须在隔离校准集上记录一致率、关键项假阴性和假阳性；达到预先登记阈值后才能升级为辅助门禁。

**Gate 3**：所有发布案例可追溯至原始资产、复核人和法律来源；评测不读取生产答案索引；确定性硬门禁全通过。

### Phase 4：知识管道收敛与影子索引（1-2 周）

**先收敛而非先扩展**

1. 使 `config/module_registry.json` 成为模块身份主表，知识模块目录由它加知识策略生成或检查；
2. 为 `sources.csv` 补充 `--write/--check` 单向生成命令，禁止人工同时维护两份来源注册表；
3. 把法域差异实现为窄接口策略（结构标记、编码、OCR、语言和条款定位），先尝试配置表，只在行为真正不同时新增类；
4. 保持 `build_chunk_sets()` 等现有消费端接口，用等价性测试逐步替换内部硬编码；
5. 法律、工作流、模板、标准条款和测试案例按资产性质分开。新法域不因一批法律 PDF 就当然拥有 5 类索引。

**新加坡影子试点**

- 仅使用获得授权、官方来源和法律复核的文件；
- 先做英文原文结构化，翻译仅为检索辅助，不替代引用原文；
- 构建版本化 `legal` 影子索引，不自动构建 template/testcase 索引；
- 使用专门的检索评测集测量 Recall@k、引用定位正确率、权威源命中率、时态正确性和被拒绝来源泄漏；
- 完成别名切换和回滚演练后才能申请生产晋级。

**Gate 4**：旧 CN/EU/US 索引等价性验证通过；模块目录漂移为 0；新加坡影子索引可重建、可评测、可回滚且不被默认生产流量读取。

### Phase 5：以 Gold 失败驱动产品修复（2-4 周，以基线结果为准）

不再凭目录或搜索结果判定“模块从零实现”。将已发布 Gold 子集逐个跑过当前服务，失败必须归类为：

| 类别 | 示例 | 处理 |
|---|---|---|
| 契约缺口 | Schema/枚举/文件上传不兼容 | 修 Builder、Schema 或明确版本迁移 |
| 规则缺口 | 路径、阈值、豁免、否决项错误 | 法律复核后修规则并增回归 |
| 知识缺口 | 应命中条款未召回或引用旧版 | 修来源/分块/检索/时态策略 |
| 生成缺口 | 结构、引用、Markdown 或报告类型错误 | 修渲染链并运行质量门禁 |
| Gold 缺陷 | 期望互相矛盾、无法绑定权威源 | 退回裁决，不修产品去迎合错误答案 |

每个缺陷必须记录案例 ID、期望/实际、根因、代码文件+行号/函数、修复提交、新增断言和复验证据。

**Gate 5**：确定性 Gold 全通过；关键否决项无失败；非确定性分数不低于锁定基线的棘轮阈值；新增修复未破坏 26 HTTP/11 E2E/15 CLI 现有门禁。

### Phase 6：真实 Provider 与输出验收（3-5 个工程日）

在隔离的验收环境中使用受控密钥和费用上限，至少每个正式任务运行 1 个代表案例和 1 个边界/失败案例。记录：

- LLM Provider/模型、请求次数、成功/降级路径、Token 用量与计费口径；
- 总耗时与阶段耗时，区分排队、检索、模型、渲染和文件 I/O；
- RAG query、候选数、重排结果、最终采用来源和报告引用的对应关系；
- 法律检索 API（包括得理，如启用）的调用条件、命中、未使用原因、超时与 fallback；
- Markdown 解析、表格/列表/标题、引用跳转、DOCX/PDF 导出和下载的一致性；
- 超时、限流、无 RAG 命中、无外部 API 和 Provider 不可用时的明确降级表现。

**Gate 6**：每次运行的 input/output/trace/manifest/截图齐全；Token 守恒、阶段耗时可解释；引用可跳转且原文定位一致；外部服务使用/未使用均有证据；不在日志和截图中泄露密钥或敏感输入。

### Phase 7：发布、封存与回滚演练（2-3 个工程日）

- 生成 release manifest、迁移说明、已知限制、人工复核队列和证据索引；
- 从干净环境重放安装、索引构建和验收命令；
- 演练软件回滚、数据库迁移回滚/前进修复、索引别名回切和配置回滚；
- 评测输入、用户数据和密钥不进入发布包；
- 仅在所有强制门禁绿色后更新软件版本和发布标签。

**Gate 7**：干净环境可复现；回滚演练通过；发布签字完整；未决法律/资料项未被标为已完成。

## 五、门禁矩阵

| Gate | 强制证据 | 责任人 | 失败时处理 |
|---|---|---|---|
| G0 基线 | 提交/依赖/索引快照，全量测试结果 | Release Owner | 停止迁移，先解决基线不可重放 |
| G1 资料 | 219/219 manifest、哈希、MIME、重复/安全/版权报告 | Data Steward | 资产保持隔离 |
| G2 映射 | 10 任务/11 身份交叉表、4 类冲突裁决 | Product + Legal | 冲突案例不发布 |
| G3 Gold | 来源、双人复核、裁决、确定性断言和泄漏检查 | Benchmark Owner + Legal | 退回标注，不调产品迎合 |
| G4 知识 | 来源注册、分块报告、影子索引评测、回滚演练 | Knowledge Owner + Legal | 候选索引不晋级 |
| G5 产品 | Schema/HTTP/CLI/E2E + Gold 棘轮 + 质量门禁 | Backend/Frontend | 修根因并增回归 |
| G6 真实链路 | LLM/RAG/API/Token/Time/引用/报告证据包 | QA + Provider Owner | 禁止发布或显式降级范围 |
| G7 发布 | 干净重放、签字、版本、回滚、已知限制 | Release Owner | 不打标签、不切生产 |

任何“待人工复核”都不得以空字符、默认通过或只有文档勾选代替。签字记录至少包含范围、结论、复核人、时间、依据版本和审计标识。

## 六、风险清单

| 编号 | 风险 | 等级 | 控制 |
|---|---|:---:|---|
| R1 | 资料中的法律名称、生效日期、阈值或效力层级未独立核验 | 高 | 全部初始为 `pending_legal_review`，未签字不生产 |
| R2 | Gold 正文与种子案例任务冲突 | 高 | 冲突登记 + 三方裁决 + 隔离 |
| R3 | 评测答案进入 RAG 造成 Benchmark 泄漏 | 高 | Gold 与生产知识物理/逻辑分离，门禁扫描 |
| R4 | 未授权标准、论文或指引进入 Git/对外报告 | 高 | 版权/用途审批，必要时只保留哈希和外部 URI |
| R5 | DOC/DOCX/XLSX/PDF 含恶意内容、密钥、PII 或客户信息 | 高 | 隔离扫描、脱敏、最小权限和拒收日志 |
| R6 | 原文、译文和研究摘要混用 | 高 | 语言/翻译来源元数据，结论默认引原文 |
| R7 | 两条入库管道、两份模块目录继续漂移 | 高 | 单向生成 + `--check` 门禁 + 等价性测试 |
| R8 | OCR/多语言分块静默丢条款或页码 | 高 | 条款数/页码覆盖、低提取率隔离、人工样本复核 |
| R9 | 候选索引覆盖活动索引无法回滚 | 高 | 不可变构建 + 原子别名切换 |
| R10 | LLM Judge 自由评分造成不稳定阻断 | 中 | 校准前 advisory，确定性否决项单独断言 |
| R11 | 只跑离线模式却宣称 LLM/RAG/得理/Token 可用 | 高 | 独立受控真实链路门禁 |
| R12 | 全量二进制重复提交造成 Git 体积和合规风险 | 中 | LFS/对象存储决策，活动副本去重 |
| R13 | 将 8 个新法域绑到一个发布日期 | 高 | 每法域独立晋级、独立回滚、独立审批 |
| R14 | 历史 `cn_flow` 命名造成法域/引用混淆 | 中 | 仅保留 API 兼容，UI/日志/评测使用真实 module_id |
| R15 | 时间和准确率目标无样本/环境口径 | 中 | 先基线，再设棘轮阈值，报告给出样本和置信边界 |

## 七、人力、排期与关键路径

### 7.1 建议最小团队

| 角色 | 最小投入 | 主要责任 |
|---|---:|---|
| Release/Product Owner | 0.5 FTE | 范围、冲突裁决、发布签字 |
| Backend/Knowledge Engineer | 1 FTE | harness、来源注册、解析/索引、服务修复 |
| Frontend/QA Engineer | 1 FTE | HTTP/E2E、真实链路证据、输出验收 |
| CN 法律复核 | 按案例/来源 | CN 来源、Gold、否决项 |
| EU/US 法律复核 | 按案例/来源 | EU/US 来源、Gold、否决项 |
| 新法域复核/翻译 | 按法域 | 原文、效力、译文与生产签字 |
| Data/Security Steward | 0.2 FTE | 版权、PII、恶意文件、存储策略 |

### 7.2 条件化估算

| 范围 | 前提 | 参考时间 |
|---|---|---:|
| v1.0 工程基础 + 现有 10 任务 Gold 基线 | 2 名工程师 + 复核人按时可用 | 6-10 周 |
| 新加坡影子试点 | 来源/版权/法律复核已通过 | 额外 2-4 周，可与部分 Gold 工作并行 |
| 其余 7 个新法域 | 每法域单独评估 | 不纳入 v1.0 统一承诺 |
| 单人全栈实施 | 复核资源仍按时可用 | 约 12-20 周，不含等待法律审批 |

关键路径为 `任务冲突裁决 → Gold 复核 → 产品基线 → 修复 → 真实 Provider 验收`。新法域影子索引可并行，但不能替代当前 10 任务的发布证据。

## 八、Git 与文件规范

1. 每个 Phase 在动工前记录基线提交，通过本 Phase 门禁后再做一个原子提交。
2. `git add` 使用显式文件路径，不使用 `git add .`；不把用户的无关改动带入提交。
3. 原始大文件、生成索引、`runs/`、截图和临时解析物按仓库规范或对象存储管理，不因“可追溯”就全部提交 Git。
4. 证据文档记录命令、退出码、时间、提交和产物哈希；截图必须脱敏且使用相对路径引用。
5. 迁移原件前必须先校验 manifest 和备份；删除活动副本前必须有 `duplicate_of` 或归档记录。
6. `status/todo/` 保留尚未全部实施的方案；阶段完成后在 `status/check/` 生成独立验收报告，不直接把计划改成“已完成”。

## 九、可复现检查

### 9.1 已存在命令

```bash
# 资料盘点复算
find resources/new -type f | wc -l
find resources/new -type f -print | sed 's/.*\.//' | tr '[:upper:]' '[:lower:]' | sort | uniq -c | sort -nr
du -sh resources/new

# 现有产品门禁
uv run --frozen python scripts/check_case_parity.py
uv run --frozen python -m backend.tests.harness.runner all --no-llm
uv run --frozen pytest -q
npm --prefix frontend test -- --run
npm --prefix frontend run test:dev-cases:api
npm --prefix frontend run build
npm --prefix frontend exec -- playwright test
git diff --check
```

### 9.2 实施中需新增或补齐的薄门禁

| 脚本 | 用途 |
|---|---|
| `scripts/check_resource_intake.py` | manifest、哈希、重复、审批与处置状态 |
| `scripts/check_module_material_mapping.py` | 10 任务、11 稳定身份、Gold/种子案例映射和冲突 |
| `scripts/build_source_registry.py --write/--check` | `sources.csv` 到 source registry 的单向生成 |
| `scripts/check_knowledge_catalog_parity.py` | 产品注册表与知识策略目录的对齐 |
| `scripts/check_benchmark_provenance.py` | 案例来源、状态、复核、引用和 RAG 泄漏 |
| `scripts/check_index_promotion.py` | 影子索引评测、别名切换和回滚元数据 |

上述脚本当前是实施交付物，不得在脚本存在前将对应门禁写成“已通过”。

## 十、待决策项

| 编号 | 待决策 | 默认建议 | 最晚时点 |
|---|---|---|---|
| D1 | v1.0 是否包含 8 个新法域生产功能 | 不包含；仅 SG 影子试点 | Phase 0 |
| D2 | 任务 4/6/7/8 以哪份资料为准 | 以已批准产品规格为准，种子案例重新映射或退回 | Phase 2 |
| D3 | 原始二进制文件进 Git LFS 还是对象存储 | 大文件/限制资料进受控存储，Git 留 manifest | Phase 1 |
| D4 | LLM Judge 是否作为 v1.0 硬门禁 | 否；校准前仅 advisory | Phase 3 |
| D5 | SG 何时从影子索引晋级生产 | 不与 v1.0 自动绑定，单独签字 | Phase 4 后 |

## 十一、完成定义

v1.0 只有在以下条件同时成立时才可发布：

```text
基线可重放
且 219 份资料全部可追溯
且资料中的任务冲突已裁决或隔离
且现有 10 个正式任务的四层契约门禁通过
且已发布 Gold 子集的确定性与关键否决项通过
且每个可用法律结论可追溯至已复核来源
且候选知识未越权进入生产索引
且真实 LLM/RAG/外部 API/Token/Time/引用/输出验收通过
且干净环境重放与回滚演练通过
且产品、法律、工程和发布负责人完成签字
```

如果未裁决案例、未核验法律资料或新法域仍处于影子阶段，应当在发布说明中明确列出，不影响已限定范围的 v1.0 发布，也不得被包装为“全法域已完成”。

## 附录 A：主要事实证据

| 事实 | 仓库证据 |
|---|---|
| 后端软件版本 `0.1.0` | `pyproject.toml:3` |
| 前端软件版本 `0.1.0` | `frontend/package.json:4` |
| 11 个稳定模块身份与生命周期 | `config/module_registry.json:1` |
| `cn_flow` 是 US EO 14117 历史兼容身份 | `config/module_registry.json:39` |
| harness 使用产品注册表并检查覆盖漂移 | `backend/tests/harness/runner.py:262` |
| CLI 案例数、前端案例数与断言下限 | `config/case_inventory.json:1` |
| 当前 RAG 为 CN/EU/US x 5 的 15 静态索引 | `backend/common/rag/orchestrator.py:32`、`backend/common/rag/orchestrator.py:569` |
| 上传入库管道当前固定使用 ChineseLegalChunker | `backend/common/knowledge/ingestion_pipeline.py:102` |
| 知识默认模块目录与产品注册表不同源 | `backend/common/knowledge/registry.py:20` |
| 26 HTTP/11 浏览器契约验收的语义边界 | `status/check/DataComplyFlow_Schema契约防漂移阶段验收_20260807.md` |
| 15 CLI/259 断言的实施和语义边界 | `status/todo/DataComplyFlow_案例体系统一与强断言方案_20260806.md` |

## 附录 B：法律与日期声明

本文档对新增法律文件只做仓库层面的数量、路径、格式和交叉关系审计，没有独立确认各法律文件的现行效力、生失效日期、权威层级、官方来源或版权授权。原资料中的相关表述均视为待法律复核声明，不得因本方案引用而自动升级为生产事实。
