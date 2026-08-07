# DataComplyFlow v0.1 至 v1.0 升级与新增资料处置方案

> 文档性质：经仓库与原始资料交叉核对的实施版（v2）
> 编制日期：2026-08-07
> 代码基线：`new` 分支，`92f47d1`
> 软件基线：后端与前端版本均为 `0.1.0`
> 资料范围：`resources/new/` 下 219 个物理文件
> 前置规范：`status/todo/DataComplyFlow_思诚资料与权威源规范化入库方案_20260806.md`

## 〇、结论与决策摘要

`resources/new/` 是一批混合的产品、法律、评测和研究资料，不是可以整包导入的"v1.0 升级包"。成熟的升级路径应当是：

```text
先冻结当前 10 个活动模块 + 1 个兼容模块的真实基线
→ 完成 219 份资料的不可变登记与权利/效力复核
→ 裁决黄金标准正文与 50 个种子案例的任务分类冲突
→ 复用现有 Schema、HTTP、浏览器和 CLI harness 门禁建立可信基线
→ 新法域按"候选→影子索引→专家验收→生产"逐个晋级
```

v1.0 不应默认承诺一次上线 8 个新法域。建议把 v1.0 定义为"现有中/欧/美 10 个产品任务的契约稳定、黄金标准基线和可审计知识入库闭环"；8 个新法域作为独立发布列车，v1.0 最多纳入 1 个影子试点，不对外宣称生产可用。

| 决策 | 建议 | 理由 |
|---|---|---|
| v1.0 业务范围 | 锁定现有 CN/EU/US 10 个正式任务 | 代码已有对应实现，但业务质量尚未通过新 Gold 证明 |
| 历史 `cn_flow` | 仅保留兼容，不计为第 11 个业务任务 | 其实际身份是 `us.eo_14117_flow_review` |
| 50 个种子案例 | 先隔离、映射和专家复核，不直接转成 CI Gold | 其中部分案例的任务名与 Gold 正文/功能规格冲突 |
| 8 个新法域 | 逐法域晋级，建议新加坡先做影子试点 | 技术可解析不等于法律可上线 |
| 知识库改造 | 在现有公开 API 内收敛为单一配置驱动管道 | 避免 `builders_v2`/`builders_v3` 长期双轨漂移 |
| 发布时间 | Phase 2 完成后再锁日期 | 当前关键路径是资料冲突裁决和法律复核，不是纯工程工时 |

## 一、事实审计与原方案修正

### 1.1 资料盘点

2026-08-07 以 `find` 对 `resources/new/` 按物理文件复核：

| 项目 | 实测数量 | 说明 |
|---|---:|---|
| 全部文件 | 219 | 含隐藏文件和 Office 临时文件 |
| 知识库补充 | 67 | 51 PDF + 5 Markdown + 5 HTML + 6 `.DS_Store` |
| 功能路径描述 | 90 | 功能说明、流程、案例和 Reference 混合 |
| 黄金标准与种子案例 | 57 | 包含 50 个案例 DOCX、1 个 XLSX 及基准材料 |
| 根目录单文件 | 5 | PRD、诊断说明、实务手册、2 份 GB/T 文件 |
| 扩展名分布 | 111 PDF / 89 DOCX / 1 DOC / 1 XLSX / 1 PNG / 5 MD / 5 HTML / 6 DS_Store | 1 个 `~$...docx` Office 临时文件包含在 89 个 DOCX 内 |
| 明确噪声 | 7 | 6 个 `.DS_Store` + 1 个 Office 临时文件 |

知识库补充实际涉及 8 个新法域/地区，共 51 个 PDF 候选件：

| 法域 | VN | JP | KR | SG | HK | MO | TW | MY | 合计 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PDF 物理文件 | 6 | 9 | 7 | 6 | 7 | 3 | 5 | 8 | 51 |

这是物理文件数，不等于 51 部独立、现行、可引用法律。同一法律的新旧版本、修正法、生效公告、监管指引和本地 HTML/Markdown 索引页必须分开定性。

### 1.2 当前代码并非"大量模块从零实现"

`config/module_registry.json` 已登记 11 个稳定身份：10 个 `active` + 1 个 `legacy-compatible`。

| 任务 | 当前实现包 | 身份状态 |
|---|---|---|
| CN 合规路径诊断 | `backend/domains/cn/transfer_diagnosis` | active |
| CN 安全评估 | `backend/domains/cn/security_assessment` | active |
| CN PIPIA | `backend/domains/cn/pipia` | active |
| CN 文档审查 | `backend/domains/cn/document_review` | active |
| EU SCC | `backend/domains/eu/scc_review` | active |
| EU BCR | `backend/domains/eu/bcr_review` | active |
| EU DPIA | `backend/domains/eu/dpia` | active |
| EU TIA | `backend/domains/eu/tia` | active |
| US EO 14117 | `backend/domains/us/eo14117` | active |
| US CPRA | `backend/domains/us/cpra` | active |
| 历史 `cn_flow` | `backend/domains/us/eo14117_flow_review` | legacy-compatible |

现有门禁已验证：26 个前端 HTTP 契约案例、11 个浏览器主路径、15 个 CLI 案例（259 条强断言）可通过。这些证明契约、离线规则和结构链路，不证明新 Gold 的法律正确性、真实 LLM/RAG 或报告内容质量。

### 1.3 知识库存在两条管道

当前知识层同时存在：

1. `builders_v2.py` → `backend/common/rag/orchestrator.py` 的 15 个静态 CN/EU/US 索引；
2. `IngestionPipeline` 的文件上传、解析、分块和数据库存储路径。

同时，`config/module_registry.json` 中的产品模块与 `backend/common/knowledge/registry.py` 的 `DEFAULT_MODULE_CATALOG` 不对齐。在该漂移消除前扩展 8 个新法域，会把已存在的双轨问题扩大。

## 二、v1.0 发布定义

### 2.1 必须交付

1. 软件版本升级到 `1.0.0`，包含可复现的 release manifest 和回滚点。
2. 现有 CN/EU/US 10 个正式任务保持 Schema、HTTP、CLI 和浏览器门禁稳定。
3. PRD/Gold/功能规格/种子案例与 `module_id` 之间存在可机器统计的映射。
4. 219 个物理文件全部登记，但只有获得授权与复核的资产进入活动目录。
5. 已裁决和通过法律复核的 Gold 子集可机器执行。
6. 每个法律结论可追溯至 `source_id` 和条款定位。
7. 真实 Provider 受控验收覆盖 LLM、RAG、引用、Token/Time 和输出。
8. 至少 1 个新法域完成影子索引试点和回滚演练。

### 2.2 明确不属于 v1.0 默认范围

- 一次上线 VN/JP/KR/SG/HK/MO/TW/MY 全部功能；
- 因"文件来自官方网站"就自动标记为现行、必须性或可二次分发；
- 把 PRD、实务手册、Gold 答案或测试案例放入生产法律索引；
- 在未完成专家复核和真实 Provider 测试时宣称"法条引用错误率为 0"。

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

跳级无效。`production` 必须同时具有：原文哈希、发布机关、官方 URL、版本/生效日期、法律复核人、授权范围、可引用条款定位、候选索引评测结果和回滚目标。

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
4. 从规范化候选集中排除 6 个 `.DS_Store` 和 1 个 Office 临时文件。
5. 在版权和 Git 体积策略决定前，不把全量二进制原件重复提交到新目录。

**Gate 1**：manifest 覆盖率 219/219；哈希可复算；每份资产都有处置状态。

### Phase 2：需求、Gold 和模块契约裁决（3-5 个工程日 + 产品/法律复核）

**权威顺序**

1. `config/module_registry.json` 决定当前软件稳定身份；
2. PRD 和功能路径规格决定候选产品要求；
3. Gold 正文决定候选 Rubric，不直接改写 API；
4. 种子案例和分数汇总是待复核证据，不自动压过前三者。

**产出**

- `module-mapping.v1.json`：外部任务到稳定 `module_id` 的映射；
- `requirement-traceability.v1.csv`：PRD→规格→Schema→代码→测试→Gold 条目；
- `conflict-register.v1.jsonl`：任务分类冲突登记；
- `release-scope.v1.md`：明确 v1.0 交付与非目标；
- 产品、法律、工程三方审批记录。

**Gate 2**：冲突已裁决或明确从 v1.0 Gold 中排除；未裁决项不得进入后续自动评分。

### Phase 3：Gold 规范化与可信评测（1-2 周 + 专家标注）

**实施原则**

- 原始 DOCX/XLSX 作为只读证据，规范化案例进入现有 `benchmarks/datasets/`；
- 复用 `backend/tests/harness/runner.py` 和 `validators.py`，不创建第二套 runner；
- 评测集不进入生产 RAG，防止答案泄漏。

**案例状态**

```text
raw → extracted → mapped → dual_reviewed → adjudicated → published
                   └→ quarantined / rejected
```

**三层评分**

| 层 | 内容 | CI 地位 |
|---|---|---|
| 确定性契约 | Schema、枚举、必填字段、路径/风险级别 | 硬门禁，100% 通过 |
| 专家 Rubric | D1-D6、关键否决项、事实完整性 | 关键否决项为硬门禁 |
| LLM-as-Judge | 规模化辅助评分 | 校准前仅 advisory |

**Gate 3**：所有发布案例可追溯至原始资产、复核人和法律来源；评测不读取生产答案索引；确定性硬门禁全通过。

### Phase 4：知识管道收敛与影子索引（1-2 周）

**先收敛而非先扩展**

1. 使 `config/module_registry.json` 成为模块身份主表；
2. 为 `sources.csv` 补充单向生成命令；
3. 把法域差异实现为窄接口策略；
4. 保持现有消费端接口，用等价性测试逐步替换内部硬编码。

**新加坡影子试点**

- 仅使用获得授权、官方来源和法律复核的文件；
- 先做英文原文结构化；
- 构建版本化 `legal` 影子索引；
- 使用专门的检索评测集测量 Recall@k、引用定位正确率；
- 完成别名切换和回滚演练后才能申请生产晋级。

**Gate 4**：旧 CN/EU/US 索引等价性验证通过；模块目录漂移为 0；新加坡影子索引可重建、可评测、可回滚。

### Phase 5：以 Gold 失败驱动产品修复（2-4 周）

将已发布 Gold 子集逐个跑过当前服务，失败必须归类为：

| 类别 | 示例 | 处理 |
|---|---|---|
| 契约缺口 | Schema/枚举不兼容 | 修 Builder、Schema |
| 规则缺口 | 路径、阈值错误 | 法律复核后修规则 |
| 知识缺口 | 应命中条款未召回 | 修来源/分块/检索策略 |
| 生成缺口 | 结构、引用错误 | 修渲染链 |
| Gold 缺陷 | 期望互相矛盾 | 退回裁决 |

**Gate 5**：确定性 Gold 全通过；关键否决项无失败；分数不低于锁定基线。

### Phase 6：真实 Provider 与输出验收（3-5 个工程日）

在隔离的验收环境中使用受控密钥和费用上限，记录：

- LLM Provider/模型、Token 用量；
- 总耗时与阶段耗时；
- RAG 候选、重排结果、报告引用对应关系；
- 外部 API 调用条件、fallback；
- Markdown、DOCX/PDF 导出一致性。

**Gate 6**：每次运行的 input/output/trace/manifest 齐全；Token 守恒；引用可跳转；不泄露密钥。

### Phase 7：发布、封存与回滚演练（2-3 个工程日）

- 生成 release manifest、迁移说明、已知限制；
- 从干净环境重放安装、索引构建和验收命令；
- 演练软件回滚、数据库迁移回滚、索引别名回切；
- 仅在所有强制门禁绿色后更新软件版本和发布标签。

**Gate 7**：干净环境可复现；回滚演练通过；发布签字完整。

## 五、门禁矩阵

| Gate | 强制证据 | 责任人 | 失败时处理 |
|---|---|---|---|
| G0 基线 | 提交/依赖/索引快照 | Release Owner | 停止迁移 |
| G1 资料 | 219/219 manifest、哈希 | Data Steward | 资产保持隔离 |
| G2 映射 | 任务/身份交叉表、冲突裁决 | Product + Legal | 冲突案例不发布 |
| G3 Gold | 来源、双人复核、确定性断言 | Benchmark Owner + Legal | 退回标注 |
| G4 知识 | 来源注册、影子索引评测 | Knowledge Owner + Legal | 候选索引不晋级 |
| G5 产品 | Schema/HTTP/CLI/E2E + Gold 棘轮 | Backend/Frontend | 修根因并增回归 |
| G6 真实链路 | LLM/RAG/Token/引用证据包 | QA + Provider Owner | 禁止发布或显式降级 |
| G7 发布 | 干净重放、签字、版本 | Release Owner | 不打标签、不切生产 |

## 六、风险清单

| 编号 | 风险 | 等级 | 控制 |
|---|---|:---:|---|
| R1 | 资料中法律名称、日期、效力未独立核验 | 高 | 全部初始为 `pending_legal_review` |
| R2 | Gold 正文与种子案例任务冲突 | 高 | 冲突登记 + 三方裁决 + 隔离 |
| R3 | 评测答案进入 RAG 造成泄漏 | 高 | Gold 与生产知识物理/逻辑分离 |
| R4 | 未授权标准、论文进入 Git/报告 | 高 | 版权/用途审批 |
| R5 | 文件含恶意内容、密钥、PII | 高 | 隔离扫描、脱敏 |
| R6 | 原文、译文和研究摘要混用 | 高 | 语言/翻译来源元数据 |
| R7 | 两条入库管道继续漂移 | 高 | 单向生成 + `--check` 门禁 |
| R8 | OCR/多语言分块静默丢条款 | 高 | 条款数/页码覆盖、人工样本复核 |
| R9 | 候选索引覆盖活动索引无法回滚 | 高 | 不可变构建 + 原子别名切换 |
| R10 | LLM Judge 自由评分造成不稳定阻断 | 中 | 校准前 advisory |
| R11 | 只跑离线模式却宣称 LLM/RAG/Token 可用 | 高 | 独立受控真实链路门禁 |

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

### 7.2 条件化估算

| 范围 | 前提 | 参考时间 |
|---|---|---:|
| v1.0 工程基础 + 现有 10 任务 Gold 基线 | 2 名工程师 + 复核人按时可用 | 6-10 周 |
| 新加坡影子试点 | 来源/版权/法律复核已通过 | 额外 2-4 周 |
| 其余 7 个新法域 | 每法域单独评估 | 不纳入 v1.0 统一承诺 |

关键路径：`任务冲突裁决 → Gold 复核 → 产品基线 → 修复 → 真实 Provider 验收`。

## 八、Git 与文件规范

1. 每个 Phase 在动工前记录基线提交，通过门禁后再做原子提交。
2. `git add` 使用显式文件路径，不使用 `git add .`。
3. 原始大文件、生成索引、截图按仓库规范或对象存储管理。
4. 证据文档记录命令、退出码、时间、提交和产物哈希。
5. `status/todo/` 保留尚未全部实施的方案；阶段完成后在 `status/check/` 生成独立验收报告。

## 九、完成定义

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

如果未裁决案例、未核验法律资料或新法域仍处于影子阶段，应当在发布说明中明确列出，不影响已限定范围的 v1.0 发布，也不得被包装为"全法域已完成"。
