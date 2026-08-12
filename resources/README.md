# DataComplyFlow Resources

> **生成时间**: 2026-08-10（由 issue064 深度审计推动的完整文档化）
>
> 本目录保存可复用的仓库资源——法规原文、快照、条文注册表、业务规则、报告模板、研究文献及产品设计输入。
> **不保存**运行生成的索引、Trace、上传件或 Benchmark Gold。

```
resources/
├── README.md                             ← 本文件
├── legal/                                ← 法规知识资源（生产级，运行时读取）
│   ├── README.md
│   ├── catalog/                          ← 来源编目与策略文件
│   ├── registry/                         ← 运行时注册表与条文语料
│   └── sources/                          ← 原始法规原文与采集快照（按法域分）
├── rules/                                ← 确定性业务规则（生产级）
├── templates/                            ← 经审核的报告结构与交付模板（生产级）
├── standards/                            ← 国标/行标参考 PDF
├── manuals/                              ← 实务操作手册
├── research/                             ← 研究材料（不参与生产运行）
│   ├── README.md
│   ├── papers/                           ← 学术论文 PDF
│   ├── product-design-sources/           ← 早期产品设计输入与统筹文档
│   ├── module-specs/                     ← 历史模块功能说明与测试案例
│   └── benchmarks/                       ← 参考 Benchmark 论文
└── new/                                  ← 待迁移/待处理材料（暂不参与生产）
    ├── 知识库补充/                        ← 区域法律原始 PDF（8 法域，约 55 个）
    ├── 数规通功能路径描述…/               ← 需求说明书中的功能路径与测试案例
    ├── 数规通黄金标准与种子案例/           ← 黄金标准（v1.0）与种子案例
    └── *.json / *.jsonl                  ← 阶段分析、决策记录、入库清单
```

---

## I. `legal/` — 法规知识资源（生产级）

> 生产代码通过 `backend/core/resource_paths.py` 和 `backend/common/knowledge/paths.py` 解析路径。
> 法规按法域只保存一份，模块适用关系由 catalog 和 registry 表达，不通过复制文件实现。

### `legal/catalog/` — 来源编目与策略

| 文件 | 描述 | 行/条目 | 生产读取 |
|------|------|---------|---------|
| `sources.csv` | **法规来源元数据索引**。每行一个来源：source_id、法域、doc_type、title、snapshot_path、url、authority_level、binding_force、publish_date、effective_date、status 等 26 列。当前 120 行，覆盖 11 法域 | 120 行 | ✅ |
| `sources.csv.bak` | sources.csv 的历史备份 | — | ❌ |
| `practice_cases.csv` | **实务案例目录**。每行一个案例：case_id、case_title、jurisdiction、expected_module、available_artifacts 等。当前 13 行，仅覆盖 CN/EU/US 的基础案例 | 13 行 | ✅ |
| `module_catalog.v1.json` | **模块-索引-策略映射**。定义 11 个模块的 RAG 索引集合、执行阶段、usage_scope、production_enabled 标志、模板策略 | 11 模块 | ✅ |
| `spec_asset_manifest.csv` | **历史资产迁移及可见性台账**。记录 88 个资产的 source_path、jurisdiction_family、target_module、sync_status（frontend_visible 或 tracked_only） | 88 行 | ✅ |

**sources.csv 字段（完整 26 列）**:
`source_id, layer, jurisdiction, path, doc_type, title, source_org, authority_level, publish_date, effective_date, status, url, snapshot_path, usage_priority, notes, module, category, usage, binding_force, authority, publisher, suitable_for, report_usage, summary, knowledge_url, origin_path`

**法域分布**: CN 28 + EU 30 + US 11 + VN 6 + SG 6 + JP 9 + KR 7 + HK 7 + MO 3 + TW 5 + MY 8 = **120 行**

### `legal/registry/` — 运行时注册表与条文语料

| 文件 | 描述 | 大小 | 生产读取 |
|------|------|------|---------|
| `source_registry.v1.json` | **运行时活动来源注册表**。由 `build_source_registry_from_sources_csv()` 从 CSV 生成（或读取缓存 JSON）。含 102 条 SourceRegistryEntry，按 jurisdiction 排序。**注意：当前仅 CN/EU/US 条目由 CSV 自动生成，其余 33 条非主流法域条目需手动维护** | 102 条 | ✅ |
| `regulation_articles.jsonl` | **逐条结构化条文注册表**。由 `scripts/build_regulation_articles.py`（CN/EU/US 来源）和 `scripts/ingest_regional_laws.py`（区域法律）生成。每行一个 JSON 对象。共 1,968 条。**⚠️ 区域法律条目缺少 `article_id` 字段** | 1,968 条 | ✅ |
| `regulation_article.schema.json` | JSONL 条目的 JSON Schema 定义。定义 8 个必填字段 + 5 个可选字段 | — | ❌（文档用途） |
| `cpra_locator_migration.json` | CPRA 历史定位符迁移表。记录 5 个已删除的 `-NN` 后缀条目与规范定位符的映射关系 | 4 entries | ❌（迁移记录） |

**regulation_articles.jsonl 条目结构**（CN/EU/US 来源，由 `build_regulation_articles.py` 生成）:
```json
{
  "article_id": "CN-LAW-001-001",
  "jurisdiction": "cn",
  "path": "all",
  "law_name": "中华人民共和国网络安全法（2025修正）",
  "article_ref": "第一条",
  "content": "...",
  "keywords": ["...", "..."],
  "source_url": "https://...",
  "snapshot_path": "resources/legal/sources/cn/snapshots/...",
  "publish_date": "2025-12-29",
  "effective_date": "2025-12-29",
  "status": "effective",
  "source_id": "CN-LAW-001",
  "doc_type": "law",
  "usage_priority": "P0",
  "layer": "legal_rules"
}
```

**⚠️ 区域法律条目**（由 `ingest_regional_laws.py` 生成）**仅含 5 个字段**：
```json
{
  "source_id": "MY-LAW-001",
  "article_ref": "1",
  "law_name": "Personal Data Protection Act 2010",
  "content": "...",
  "jurisdiction": "my"
}
```
缺少：`article_id`、`path`、`doc_type`、`source_url`、`keywords`、`publish_date`、`effective_date`、`status`、`snapshot_path`、`layer`、`usage_priority`。

**条文来源覆盖（56 个唯一 source_id）**:

| 法域 | 来源数 | 条文数 | 来源示例 |
|------|--------|--------|---------|
| CN | 19 | 420 | CN-LAW-001 (网络安全法 85条), CN-LAW-002 (数据安全法 54条), CN-REG-004 (安全评估办法 20条) |
| EU | 2 | 101 | EU-LAW-001 (GDPR 99条), EU-GUIDE-002 (SCC指南 2条) |
| US | 2 | 100 | US-CA-001 (CPRA 83条), US-FED-001 (EO14117 17条) |
| JP | 7 | 441 | JP-LAW-001 (个人情報保護法 200条), JP-REG-002 (施行规则 95条) |
| KR | 6 | 267 | KR-LAW-001 (個人情報保護法 76条) |
| HK | 5 | 94 | HK-LAW-006 (CISO条例 71条) |
| TW | 5 | 196 | TW-LAW-001 (个人资料保护法 56条) |
| MY | 6 | 243 | MY-LAW-001 (PDPA 2010 146条), MY-LAW-006 (网络安全法 64条) |
| MO | 2 | 80 | MO-LAW-001 (个人资料保护法 49条) |
| SG | 2 | 26 | SG-LAW-001 (PDPA 2012 7条) |

### `legal/sources/` — 原始法规原文与采集快照

按法域分三个子目录，每个子目录下有 `references/` 和 `snapshots/`：

```
legal/sources/
├── cn/
│   ├── references/        ← 官方 PDF 原件（17 个）
│   └── snapshots/         ← 采集文本快照（26 个：22 .md + 4 .html）
├── eu/
│   ├── references/        ← 官方 PDF 原件（27 个）
│   └── snapshots/         ← 文本快照（28 个 .md）
└── us/
    ├── references/        ← 官方 PDF 原件（11 个）
    └── snapshots/         ← 文本快照（11 个 .md）
```

| 目录 | 用途 | 格式 | 数量 |
|------|------|------|------|
| `references/` | **最 raw 的原始法规文件**——官网 PDF 直接下载或转制，未经过清洗 | `.pdf`（仅有 CN 含 1 个 `.PNG`） | 55 |
| `snapshots/` | **采集清洗后的文本快照**——从官网抓取的 HTML 或手工整理的 Markdown，作为 `build_regulation_articles.py` 的直接输入 | `.md`（61 个）+ `.html`（4 个，仅 CN 网信办公告页） | 65 |

**CN references 示例**: `网络安全法.pdf`、`数据安全法.pdf`、`个人信息保护法.pdf`、`数据出境安全评估办法.pdf`、`个人信息出境标准合同办法.pdf`、`网络数据安全管理条例.pdf`、`促进和规范数据跨境流动规定.pdf`、`个人信息出境认证办法.pdf`、`汽车数据安全管理若干规定.pdf`、`金融数据安全 数据安全分级指南.pdf`、`信息安全技术 个人信息安全规范.pdf`、`个人金融信息保护技术规范.pdf`、`数据出境申报系统使用手册.pdf`、`数据处理协议样例.pdf`、`隐私政策样例.PNG`

**CN snapshots 示例**: `cac_2021_08_20_pipl.html`（个保法网信办公告）、`cac_2022_07_07_security_assessment_measures.html`（安全评估办法）、`cac_2024_09_30_network_data_security_regulation.html`（网络数据安全管理条例）、`cac_2025_12_29_cybersecurity_law.html`（网络安全法 2025 修正）、`cn-tpl-016_个人信息出境标准合同模板.md`、`cn-tpl-019_数据出境风险自评估报告模板.md`、`cn-sup-003_信息安全技术_个人信息安全规范.md`

**EU references 示例**: `CELEX_32016R0679_EN_TXT.pdf`（GDPR）、`edpb_recommendations_202001vo.2.0_supplementarymeasurestransferstools_en.pdf`、各国 adequacy decision PDF（CELEX 编号前缀）

**EU snapshots 示例**: `eurlex_gdpr_2016_679_excerpts.md`（GDPR 摘录）、`eu-sup-002_celex_32002d0002_en_txt.md`、`edpb_recommendations_01_2020_excerpts.md`

**US references 示例**: `The California Privacy Rights Act of 2020.pdf`、`19-Digital-Trade.pdf`、`FISA_Section_702.pdf`、`NIST.CSWP.01162020.pdf`、`cloud_act.pdf`

**US snapshots 示例**: `ca_civil_code_cpra_sections.md`、`fr_2025_01_08_eo14117_excerpts.md`

**⚠️ 重要**: 非 CN/EU/US 法域（8 个）的原始 PDF 不在 `legal/sources/` 下，而在 `resources/new/知识库补充/` 中。它们通过独立的 `scripts/ingest_regional_laws.py` 管线处理（pdftotext → 正则提取条文 → 直接写入 JSONL）。

---

## II. 数据转换全链路

### 路径 A：官网快照 → 条文 JSONL → 前端（CN/EU/US）

```
references/*.pdf（原始 PDF）
  → 人工/半自动采集，转为快照
snapshots/*.{md,html}（文本快照）
  → scripts/build_regulation_articles.py
     ├── _html_to_text(): HTML 标签剥离（如有）
     ├── _extract_article_chunks(): 正则匹配"第X条" / "Article X" / "Step X"
     └── 每条截断 2500 字符，生成 article_id = f"{source_id}-{idx:03d}"
  → regulation_articles.jsonl（条文注册表）
  → 后端两层消费：
     (a) GET /api/v1/knowledge/sources/{id}/articles/{no}
         → get_article_detail() → 查 JSONL + 返回前后相邻条文
         → 前端 KnowledgeContentRenderer → ReactMarkdown 渲染
     (b) builders_v2.py: build_legal_chunks_{cn|eu|us}()
         → KnowledgeChunkV2 → HashingEmbedder → V3 向量索引
         → search_user_articles() → EvidenceCenterPage articles tab
```

### 路径 B：区域法律 PDF → JSONL（非 CN/EU/US，8 法域）

```
resources/new/知识库补充/{日韩,港澳台,新加坡,越南,马来西亚}/*.pdf（原始 PDF，约 55 个）
  → scripts/ingest_regional_laws.py
     ├── extract_pdf_text(): pdftotext -layout
     ├── 法域专用 parser: parse_japanese_articles / parse_chinese_articles /
     │     parse_english_sections / parse_malay_sections
     └── write_articles_jsonl(): 直接追加到 regulation_articles.jsonl
         ⚠️ 每条仅含 5 字段（无 article_id/path/doc_type/source_url/keywords）
  → 同时调用 write_sources_csv(): 追加行到 sources.csv
  → 手动重建 source_registry.v1.json（如已执行）
```

**当前阻塞点**: 即使 JSONL 已写入、注册表已手动包含、V2 向量索引 `regulation_index_v2.json` 有数据：
1. `registry.py:204` 的 `if jurisdiction not in {"cn","eu","us"}: continue` 在 CSV→注册表构建时过滤
2. V3 多索引管线 `build_multi_index_v3()` 不处理非 CN/EU/US 数据
3. `search_user_articles()` 仅查询 `legal_index_{cn|eu|us}.vector.json`

### 路径 C-E：工作流规则 / 标准条款 / 模板分片（硬编码）

这三类数据不依赖文件系统上的 raw 文件，直接通过 `builders_v2.py` 中硬编码的 Python 字典生成 `KnowledgeChunkV2`：

| 路径 | builders_v2.py 函数 | 产出 | 覆盖法域 |
|------|-------------------|------|---------|
| C: 工作流规则 | `build_workflow_chunks_{cn|eu|us}()` | L2_business_rule，共 18 条规则（CN 7 + EU 4 + US 7） | CN/EU/US |
| D: 标准条款 | `build_standard_clause_chunks_{cn|eu|us}()` | L1_regulatory_evidence + source_kind=standard_clause，共 11 条（CN 5 + EU 3 + US 3） | CN/EU/US |
| E: 模板分片 | `build_template_chunks_{cn|eu|us}()` | L4_template，CN 读 `official_template_schema.json`，EU/US 硬编码 | CN/EU/US |

---

## III. `rules/` — 业务规则（生产级）

| 文件 | 描述 | 生产读取 |
|------|------|---------|
| `cn/review_rulebook.json` | **中国文档审查规则手册**。定义 clause_types 及其 citations、protected_obligations、modification_sensitivity。被 `build_standard_clause_chunks_cn()` 引用以生成标准条款的 citation_strings | ✅ |

---

## IV. `templates/` — 报告与交付模板（生产级）

按法域分三个子目录。模板作为 KnowledgeChunkV2（L4_template）进入 RAG 检索池。

| 文件 | 描述 | 用途 |
|------|------|------|
| `cn/official_template_schema.json` | 中国安全评估报告官方模板的结构化 schema（sections + subsections + required_inputs） | `build_template_chunks_cn()` 直接解析 |
| `cn/official_risk_self_assessment_template.md` | 中国安全评估自评估报告示例 Markdown | `build_template_chunks_cn()` 读取前 1200 字符作为 example chunk |
| `cn/2.2_risk_assessment_template_v0.{docx,md}` | 风险评估模板 v0（.docx 原始 + .md 转换） | 报告生成参考 |
| `eu/3.2_bcr_review_template_v0.{docx,md}` | BCR 审查模板 v0 | 报告生成参考 |
| `eu/3.4_tia_template_v0.{docx,md}` | TIA 模板 v0 | 报告生成参考 |
| `us/4.1_cn_flow_compliance_template_v0.{docx,md}` | 中国路径合规模板 v0 | 报告生成参考 |
| `us/4.2_cpra_panorama_template_v0.{docx,md}` | CPRA 全景报告模板 v0 | 报告生成参考 |
| `us/4.2_us_14117_compliance_template_v0.md` | EO14117 合规模板 v0（仅 .md） | 报告生成参考 |

---

## V. `standards/` — 国标/行标参考 PDF

| 文件 | 描述 |
|------|------|
| `数据分级分类指南GBT_43697-2024.pdf` | GB/T 43697-2024 数据安全技术 数据分类分级规则 |
| `数据安全技术敏感个人信息处理安全要求GBT_45574-2025.pdf` | GB/T 45574-2025 数据安全技术 敏感个人信息处理安全要求 |

---

## VI. `manuals/` — 实务操作手册

| 文件 | 描述 |
|------|------|
| `167_数据出境合规实务手册.pdf` | 数据出境合规实务操作手册（含 Checklist 与案例） |

---

## VII. `research/` — 研究材料（不参与生产运行）

> **使用约束**：
> - 生产代码、RAG 不得读取本目录
> - 来源不明的 DOCX/PDF 不能直接认定为产品权威依据
> - 进入法规知识库的材料必须登记到 `resources/legal/catalog/sources.csv`
> - Benchmark Gold 必须进入 `benchmarks/datasets/`

### `research/papers/` — 学术论文（15 个 PDF）

法律 AI / LLM 相关论文，涵盖 LLM 在法律领域的综述、评估方法和多智能体框架：

| 论文 | 年份 |
|------|------|
| `Large_Language_Models_in_Law_A_Survey_2023.pdf` | 2023 |
| `Natural_Language_Processing_for_the_Legal_Domain_2024.pdf` | 2024 |
| `A_Survey_of_Large_Language_Models_2024.pdf` | 2024 |
| `Large_Language_Models_in_Legal_Systems_A_Survey_2025.pdf` | 2025 |
| `A_Survey_of_LLM_Evolution_and_Applications_2025.pdf` | 2025 |
| `LLMs_for_Legal_Reasoning_Unified_Framework_2025.pdf` | 2025 |
| `Large_Language_Models_Meet_Legal_AI_A_Survey_2025.pdf` | 2025 |
| `Evaluation_Techniques_for_LLMs_in_Law_2025.pdf` | 2025 |
| `From_Single_Agent_to_Multi_Agent_A_Review_of_LLM_based_Legal_Agents_2025.pdf` | 2025 |
| `Challenges_for_Generative_AI_in_Legal_Reasoning_2026.pdf` | 2026 |
| `A_Survey_of_Large_Language_Models_for_Legal_Tasks_2026.pdf` | 2026 |
| `Legal Evalutions and Challenges of Large Language Models.pdf` | — |
| `paper.md` / `download_report.md` | 论文清单/下载记录 |

### `research/benchmarks/` — 参考 Benchmark 论文（3 个 PDF + 1 个 DOCX）

LexEval、LegalBench、PLAWBENCH 等法律 LLM 评测基准的原始论文。

### `research/product-design-sources/` — 早期产品设计输入

| 子目录 | 内容 |
|--------|------|
| `00_index/` | 来源目录 `00_source_catalog.md`、命名规则 `01_file_naming_rules.md`、原始统筹开发文档（.docx + .pdf） |
| `01_pathway_layer/` | 中国、美国及待研究欧洲路径层的设计来源 |
| `02_function_layer/` | 合同审查、表单和报告生成模块的设计来源 |

**⚠️**：这些材料仅用于解释产品设计来源，**不是**生产法规、正式模板或当前功能实现的事实依据。

### `research/module-specs/` — 历史模块功能说明与测试案例

按 `法域/模块/` 划分，每个模块含 `spec.md` 和 `test-cases.md`：

| 法域 | 模块 | 文件 |
|------|------|------|
| CN | cn-diagnosis | `spec.md`, `test-cases.md`, `reference-catalog.md` |
| CN | cn-assessment | `spec.md`, `test-cases.md` |
| CN | cn-pipia | `spec.md`, `test-cases.md` |
| CN | cn-review | `spec.md`, `test-cases.md` |
| EU | eu-scc | `spec.md`, `test-cases.md` |
| EU | eu-bcr | `spec.md`, `test-cases.md` |
| EU | eu-dpia | `spec.md`, `test-cases.md` |
| EU | eu-tia | `spec.md`, `test-cases.md` |
| US | us-14117 | `spec.md`, `test-cases.md` |
| US | us-cpra | `spec.md`, `test-cases.md` |

这些 spec 和 test-cases 记录早期功能描述与演示预期，不是当前法规依据、Benchmark Gold 或稳定接口契约。如需将案例转为 Benchmark，必须重新进行来源核验和法律专家标注。

---

## VIII. `new/` — 待迁移/待处理材料（暂不参与生产）

### `new/知识库补充/` — 区域法律原始 PDF（8 法域）

已入库但前端不可见的区域法律原始 PDF，按法域分目录：

| 子目录 | 法域 | PDF 数量 | 说明 |
|--------|------|---------|------|
| `日韩/日本/` | JP | 8 | 个人信息保护法、施行令/规则、指引、网络安全法 |
| `日韩/韩国/` | KR | 6 | 个人信息保护法、施行令、跨境转移规定、安全措施标准 |
| `港澳台/香港/` | HK | 7 | 私隐条例、跨境转移指引、大湾区标准合同、CISO条例 |
| `港澳台/澳门/` | MO | 2 | 个人资料保护法、网络安全法 |
| `港澳台/台湾/` | TW | 5 | 个人资料保护法、施行细则、资通安全管理法 |
| `新加坡/` | SG | 6 | PDPA 2012、条例（跨境/泄露通知/执法）、网络安全法 |
| `越南/` | VN | 6 | 数据保护法、数据法、网络安全法及实施法令 |
| `马来西亚/` | MY | 9 | PDPA 2010、2024 修正法、条例/标准、网络安全法 |

每个子目录同时含 `.html` 和 `.md` 格式的法规目录索引文件。

**处理状态**:
- ✅ PDF→JSONL 已通过 `scripts/ingest_regional_laws.py` 完成
- ✅ `sources.csv` 已追加对应行
- ✅ `source_registry.v1.json` 已手动包含（102 条含 33 条区域法律）
- ✅ V2 向量索引 `regulation_index_v2.json` 有数据（1,347 条区域法律条文）
- ❌ `article_id` 字段缺失（写入时未生成）
- ❌ 元数据残缺（仅 5 字段 vs 标准 15 字段）
- ❌ V3 多索引不覆盖非 CN/EU/US
- ❌ 前端法规列表、条文搜索不可用

### `new/数规通功能路径描述（含reference）、流程描述、测试案例/` — 需求规格

三个法域路径的需求描述、测试案例与预期输出（全部为 `.docx` 格式）：

| 子目录 | 模块/任务 | 文件 |
|--------|----------|------|
| `中国数据出境路径/` | 1. 合规路径诊断 | 路径描述 + 测试案例 + Reference标注版功能说明 |
| | 2. 安全评估路径 | 路径描述 + 测试案例 |
| | 3. 认证标准合同路径 | 路径描述 + 测试案例 |
| | 4. 文档专项智能审查 | 功能说明 |
| | Reference库 | Reference库清单 |
| `欧盟数据出境路径/` | 1. SCC审查 | 路径描述 + 测试案例 |
| | 2. BCR审核 | 路径描述 + 测试案例 |
| | 3. DPIA草案生成 | 路径描述 + 测试案例 |
| | 4. TIA草案生成 | 路径描述 + 测试案例 |
| | Reference库 | Reference库清单 |
| `美国（加州）数据出境路径/` | 1. 14117行政令合规 | 路径描述 + 测试案例 |
| | 2. CPRA合规 | 路径描述 + 测试案例 |
| | Reference库 | Reference库清单 |

### `new/数规通黄金标准与种子案例/`

| 文件 | 描述 |
|------|------|
| `数规通黄金标准（v1.0 正式版）.docx` | 黄金标准定义文件（v1.0） |
| `参考Benchmark/` | 参考 Benchmark 目录 |
| `种子案例及测试结果/` | 种子案例与测试结果 |

### `new/` 根目录下的工作总结文件

| 文件 | 描述 |
|------|------|
| `《数规通（DataComplyFlow）需求说明书》.docx` | 完整需求规格说明书 |
| `"合规路径诊断"功能说明与路径描述（标注Reference）.docx` | 诊断模块的独立功能说明 |
| `analysis.phase1.json` | **第一阶段入库分析结果**。含 `total_files`（文件总数）、`duplicates`（重复文件）、`name_conflicts`（命名冲突）、`mime_mismatches`（MIME 类型不匹配）、`large_files`（大文件） |
| `decisions.v1.jsonl` | **入库决策记录**（17 条）。含 `decision_id`、`type`、`hash`、`action`（kept/removed）、`kept`（保留的文件）、`removed`（移除的文件）、`reason`（原因） |
| `manifest.intake.v1.json` | **入库清单**。记录待入库文件的路径、类型、目标模块、目标层级等元数据 |

---

## IX. 文件数量汇总

| 目录 | 文件数 | 生产读取 | 说明 |
|------|--------|---------|------|
| `legal/catalog/` | 5 | ✅ | 来源 CSV + 案例 CSV + 模块策略 + 资产台账 |
| `legal/registry/` | 4 | ✅ | 注册表 + 条文 JSONL + Schema + 迁移表 |
| `legal/sources/cn/references/` | 17 | ❌（构建时） | 中国法规原始 PDF |
| `legal/sources/cn/snapshots/` | 26 | ✅（构建时） | 中国法规文本快照 |
| `legal/sources/eu/references/` | 27 | ❌（构建时） | 欧盟法规原始 PDF |
| `legal/sources/eu/snapshots/` | 28 | ✅（构建时） | 欧盟法规文本快照 |
| `legal/sources/us/references/` | 11 | ❌（构建时） | 美国法规原始 PDF |
| `legal/sources/us/snapshots/` | 11 | ✅（构建时） | 美国法规文本快照 |
| `rules/` | 1 | ✅ | review_rulebook.json |
| `templates/` | 14 | ✅（构建时） | 报告模板（.json/.md/.docx） |
| `standards/` | 2 | ❌ | 国标参考 PDF |
| `manuals/` | 1 | ❌ | 实务手册 PDF |
| `research/papers/` | 15 | ❌ | 论文 PDF + 清单 |
| `research/benchmarks/` | 4 | ❌ | Benchmark 论文 |
| `research/product-design-sources/` | 9 | ❌ | 设计输入文档 |
| `research/module-specs/` | 21 | ❌ | 历史 spec + test-cases |
| `new/知识库补充/` | 约 55 | ❌ | 区域法律原始 PDF |
| `new/功能路径/` | 约 30 | ❌ | 需求路径与测试案例 |
| `new/黄金标准/` | 2+ | ❌ | 黄金标准 + 种子案例 |
| `new/` 根目录 | 4 | ❌ | 工作总结 JSON/JSONL + 需求说明书 |
| **总计** | **约 290** | | |

---

## X. 已知问题与待处理事项

1. **区域法律元数据残缺**（P0）：`ingest_regional_laws.py` 写入 JSONL 时缺少 `article_id`、`path`、`doc_type` 等 10 个字段 → V2 索引 doc_id 为空 → 前端不可见

2. **V3 多索引不覆盖非 CN/EU/US**（P0）：`builders_v2.py` 的 `build_legal_chunks_*()` 仅处理 CN/EU/US → V3 向量索引无区域法律数据 → `search_user_articles()` 无法检索

3. **注册表白名单过严**（P0）：`registry.py:204` 的 `if jurisdiction not in {"cn","eu","us"}: continue` 阻止 CSV→注册表的自动构建，虽然缓存 JSON 已被手动 patch

4. **条文截断**（P2）：`build_regulation_articles.py:95` 每条强制截断 2500 字符；`ingest_regional_laws.py:1245` 截断 2000 字符。长条文丢失后半部分

5. **构建脚本双轨**（P2）：CN/EU/US 用 `build_regulation_articles.py`（含 15 字段），区域法律用 `ingest_regional_laws.py`（仅 5 字段），两条管线的 schema 不统一

6. **vector index 双轨**（P2）：V2 `regulation_index_v2.json`（3,049 条含区域法律但已弃用）vs V3 多索引（仅 CN/EU/US 但为当前生产使用），两套索引无合并机制
