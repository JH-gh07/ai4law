# DataComplyFlow RAG 与知识库系统详解

> 生成日期：2026-08-16 · 基于 `new` 分支当前代码事实：16 索引、schema `v3.2`、`sources.csv` 120 条来源记录、模板引用策略收敛、Legal Control 来源身份门禁。

---

## 〇、概览：RAG 与知识库的关系

本项目的 RAG 系统分为两层：

```
┌──────────────────────────────────────────────────────────────┐
│                   knowledge/ (知识库层)                       │
│  数据模型 · 文档摄入管道 · 分块构建器 · 存储管理 · 使用策略      │
│  关注："知识从哪来、怎么存、怎么组织"                              │
└──────────────────────────┬───────────────────────────────────┘
                           │ 提供 KnowledgeChunkV2 数据
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                     rag/ (检索引擎层)                          │
│  向量化 · 索引构建 · 混合检索 · 重排序 · 多索引编排              │
│  关注："用户提问后怎么找到最相关的知识"                            │
└──────────────────────────────────────────────────────────────┘
```

**简单比喻：** knowledge 层是"图书馆的藏书和编目系统"，rag 层是"图书馆的搜索引擎"。

---

## 一、代码文件全景地图

### 1.1 文件索引表

| 层级 | 文件路径 | 行数 | 核心职责 |
|------|---------|------|---------|
| **检索引擎** | `backend/common/rag/service.py` | 303 | 统一检索门面，三后端路由（multi/single/compat） |
| | `backend/common/rag/orchestrator.py` | 672 | 多索引编排器，16 索引 × 法域 × 按 stage 路由；`INDEX_NAMES` 与 `build_chunk_sets()` 在此定义 |
| | `backend/common/rag/retriever.py` | 543 | 单索引检索器（v1），含 DeliLegal 外部回退 |
| | `backend/common/rag/hybrid_retriever.py` | 168 | 增强混合检索（向量+FTS5+RRF 融合） |
| | `backend/common/rag/vector_store.py` | 104 | 本地 JSON 向量存储，余弦相似度搜索 |
| | `backend/common/rag/embedding.py` | 71 | 确定性哈希嵌入器（SHA-256 → 稀疏向量） |
| | `backend/common/rag/reranker.py` | 67 | 启发式重排序器，短语/关键词/元数据加权 |
| | `backend/common/rag/fulltext_index.py` | 107 | SQLite FTS5 全文索引 |
| | `backend/common/rag/ingest.py` | 148 | 索引构建：单索引 + 多索引 v3 |
| | `backend/common/rag/constants.py` | 2 | 版本常量（`MULTI_INDEX_SCHEMA_VERSION = "v3.2"`） |
| **知识模型** | `backend/common/knowledge/v2.py` | 162 | 核心 Pydantic 模型：KnowledgeChunkV2、SourceRegistryEntry、SourceKind 等 |
| | `backend/common/knowledge/models.py` | 74 | SQLAlchemy ORM：KnowledgeDocument/IngestedFile/KnowledgeChunk |
| **知识构建** | `backend/common/knowledge/builders_v2.py` | 1473 | 16 个 chunk builder 函数（含 `build_legal_chunks_intl()`），全法域 × 全类型 |
| | `backend/common/knowledge/registry.py` | 320 | SourceRegistry + ModuleCatalog 管理，含 `_citation_policy_for_row()` 引用策略 |
| **知识摄入** | `backend/common/knowledge/ingestion_pipeline.py` | 125 | 文档摄入管道：保存→解析→分块→入库 |
| | `backend/common/knowledge/document_parser.py` | 125 | PDF/DOCX 解析器 |
| | `backend/common/knowledge/chunker.py` | 170 | 中国法律结构感知分块器 |
| | `backend/common/knowledge/chinese_legal_patterns.py` | 98 | 法律文书正则模式库 |
| **知识存储** | `backend/common/knowledge/storage_manager.py` | 93 | 文件哈希去重 + 目录组织 |
| | `backend/common/knowledge/paths.py` | 33 | 知识库文件路径解析（`sources_csv_path()` 等） |
| **使用策略** | `backend/common/knowledge/usage_policy.py` | 96 | UsagePolicyFilter：按用途/环境/法域过滤 |
| **API 端点** | `backend/api/v1/endpoints/knowledge.py` | 192 | 知识库 REST API（检索/详情/同步） |
| **测试** | `backend/common/rag/tests/` | 5 文件 | 多索引编排器、服务层、单索引检索器、模块检索基准 |
| | `backend/common/knowledge/tests/` | 7 文件 | chunker、regional knowledge、registry、reingest、usage_policy |

---

## 二、知识库系统（knowledge/）详解

### 2.1 数据模型分层

```
SourceRegistryEntry (Pydantic)         ← 法规来源的元数据登记
    │
    ▼
KnowledgeDocument (SQLAlchemy ORM)    ← 数据库中的"文档"记录
    │
    ▼
KnowledgeChunk (SQLAlchemy ORM)       ← 数据库中的"分块"记录（存 DB）
    │  (ingestion_pipeline 转换)
    ▼
KnowledgeChunkV2 (Pydantic)           ← 运行时检索的"分块"对象（存 JSON 索引）
```

### 2.2 `KnowledgeChunkV2` — 核心运行时数据模型

```python
# /v2.py — 所有检索操作统一使用的分块模型
class KnowledgeChunkV2(BaseModel):
    chunk_id: str          # 唯一标识 "CN-LAW-002/CH5/AR39"
    source_id: str         # 来源 ID "CN-LAW-003"
    title: str             # 法规标题 "中华人民共和国个人信息保护法"
    content: str           # 分块正文（条文原文）
    layer: LayerType       # L1_法规证据 / L2_业务规则 / L3_测试案例 / L4_模板
    source_kind: SourceKind # 8 值 Literal：law_article / official_guide / workflow_rule / testcase / standard_clause / template_slot / regulation / case_reference
    module: str            # 所属模块 "cn_assessment"
    jurisdiction: str      # 法域 "cn" / "eu" / "us" / "intl"
    doc_type: str          # 自由文本来源类型（policy / technical_standard 等，映射到 SourceKind）
    authority_level: str   # 权威等级 high / medium / low
    binding_force: str     # 效力等级 mandatory / recommended / reference
    allowed_usage: list    # 允许的使用场景 [legal_grounding, external_report]
    can_be_cited: bool     # 可被引用
    can_enter_external_report: bool  # 可进入外部报告
    reference_ids: list    # 关联的其他法规 ID
    citation_anchor: str   # 引用定位 "第三十九条"
    article_no: str        # 条号 "39"
    path: str              # 业务路径 "assessment" / "review" / "all"
    keywords: list[str]    # 关键词标签
    structured_payload: dict  # 结构化业务载荷（规则条件、模板映射等）
```

### 2.3 知识的四层架构（Layer）

| Layer | 名称 | source_kind | 作用 | 是否进外部报告 |
|-------|------|-------------|------|:---:|
| **L1** | 法规证据层 | `law_article` / `standard_clause` | 法律条文原文、标准合同条款 | ✅ |
| **L2** | 业务规则层 | `workflow_rule` | 合规工作流判断规则（如"CIIO 触发安全评估"） | ❌ |
| **L3** | 测试案例层 | `testcase` | LLM 评估用的测试用例（Few-shot / Evaluator） | ❌ |
| **L4** | 模板层 | `template_slot` | 官方报告模板的章节结构 | ❌（结构控制用） |

> **说明：** 上表只列出各层最常见的 `source_kind`。实际 `SourceKind` 是一个 8 值 `Literal`：`law_article` / `official_guide` / `workflow_rule` / `testcase` / `standard_clause` / `template_slot` / `regulation` / `case_reference`。其中 `regulation`、`case_reference`、`official_guide` 主要服务于国际法域（`legal_index_intl`）及 JP/KR 等区域来源；`sources.csv` 里的自由文本 `doc_type`（如 `policy`、`technical_standard`）会由 `registry._source_kind_from_row()` 映射到稳定枚举（`policy`→`official_guide`，`technical_standard`→`standard_clause`）。

### 2.4 SourceRegistry — 法规来源登记

**数据来源：** `resources/legal/catalog/sources.csv`（`KNOWLEDGE_ROOT = PROJECT_ROOT / "resources" / "legal"`，见 `backend/core/resource_paths.py`）

CSV 字段（当前为 27 列，121 行）：
```
source_id,layer,jurisdiction,path,doc_type,title,source_org,authority_level,
publish_date,effective_date,status,url,snapshot_path,usage_priority,notes,
module,category,usage,binding_force,authority,publisher,suitable_for,
report_usage,summary,knowledge_url,origin_path,review_status
```

**注册流程：**

```
sources.csv                          ┌─ 首次启动时
    │                                │
    ▼                                │
build_source_registry_from_sources_csv()  ─┤ 解析 CSV → SourceRegistryEntry 列表
    │                                │
    │ (若 JSON 不存在)                 │
    ▼                                │
source_registry.v1.json              ─┘  缓存为 JSON，后续直接读取
    │
    ▼
ensure_source_registry()             ← 所有 Builder 调用入口
    │  优先读 JSON，不存在时从 CSV 生成
    ▼
list[SourceRegistryEntry]            → builders_v2.py 使用
```

**SourceRegistryEntry 核心字段（定义在 `v2.py`）：**
```python
class SourceRegistryEntry(BaseModel):
    source_id: str            # "CN-LAW-003"
    title: str                # "个人信息保护法"
    aliases: list[str]        # 别名
    jurisdiction: str         # "cn" / "eu" / "us" / "intl"
    modules: list[str]        # ["cn_diagnosis", "cn_assessment"]
    layer: LayerType
    source_kind: SourceKind | str   # "law_article" / "official_guide" / ...
    authority_level: str      # 从 CSV authority/authority_level 推断
    binding_force: str        # mandatory / recommended / reference
    status: str               # effective / repealed 等
    is_current_version: bool
    supersedes: list[str]     # 替代的历史 source_id（版本链）
    superseded_by: list[str]
    review_status: str        # "published" / "metadata_review_required"
    allowed_usage: list[str]
    can_be_cited: bool        # 由 _citation_policy_for_row() 计算
    can_enter_external_report: bool
    metadata: dict            # 扩展字段
```

**引用策略（`registry._citation_policy_for_row()`）：** 对 `review_status == "metadata_review_required"` 的来源行，返回 `can_be_cited=False`、`can_enter_external_report=False`、`allowed_usage=["internal_review"]`，即隔离区（quarantine）语义——未通过元数据审核的来源不进外部报告、不进入可引用路径。

**模板来源策略：** `doc_type=template` 的来源统一得到 `can_be_cited=false`、`can_enter_external_report=false`、`allowed_usage=["structure_control", "internal_review"]`。因此 `CN-TPL-019` 这类模板来源能为报告结构提供控制依据，但不能被 Citation Gate 当作实体法条引用；策略实现与回归测试分别在 `registry.py` 与 `backend/common/knowledge/tests/test_registry.py`。

**当前规模与漂移检查：** `sources.csv` 当前为 121 行（含表头，即 120 条数据记录），缓存文件为 `resources/legal/registry/source_registry.v1.json`。生成/漂移检查：

```bash
./.venv/bin/python scripts/build_source_registry.py --check
# sources.csv: 120 entries; cached entries: 120; field deltas: 0
```

**Module Catalog（模块目录）：**

`module_catalog.v1.json` — 记录每个模块的生产启用状态、所需索引、支持的 stage、默认用途范围与模板策略：

```json
{
  "version": "v1",
  "modules": {
    "cn_assessment": {
      "indexes": ["workflow_index_cn", "legal_index_cn", "template_index_cn", "testcase_index_cn"],
      "stages": ["issue_discovery", "legal_grounding", "report_generation", "evaluation"],
      "default_usage_scopes": ["internal_review", "legal_grounding", "structure_control"],
      "jurisdiction": "cn",
      "production_enabled": true,
      "requires_standard_clause_index": false,
      "template_policy": "official_only"
    }
  }
}
```

> 各模块的实际字段包括 `version`、`modules` 包装、`default_usage_scopes`、`jurisdiction`、`requires_standard_clause_index`、`template_policy`。注意：`legal_index_intl` 是纯法规索引，**不**绑定任何生产模块，因此不出现在 `module_catalog.v1.json` 的 `indexes` 里。

### 2.5 Chunk Builders — 知识数据的"生产线"

**总览：** `build_chunk_sets()` 函数定义在 `backend/common/rag/orchestrator.py:654`（**不是** builders_v2.py），返回 16 个索引的全部数据。16 个 `build_*` 函数本体仍在 `builders_v2.py`：

```
build_chunk_sets() → {                                            # orchestrator.py:654
    "legal_index_cn":        build_legal_chunks_cn(),        ← 从 regulation_articles.jsonl 解析
    "workflow_index_cn":     build_workflow_chunks_cn(),     ← 硬编码的业务规则
    "standard_clause_index_cn": build_standard_clause_chunks_cn(), ← 审查规则库
    "template_index_cn":     build_template_chunks_cn(),     ← official_template_schema.json
    "testcase_index_cn":     build_testcase_chunks_cn(),     ← 硬编码的测试案例
    ─── 欧盟 × 5 ───
    "legal_index_eu":        build_legal_chunks_eu(),
    ...
    ─── 美国 × 5 ───
    "legal_index_us":        build_legal_chunks_us(),
    ...
    ─── 国际法域 × 1 ───
    "legal_index_intl":      build_legal_chunks_intl(),      ← JP/KR/MY/HK/VN/SG/TW/MO 区域来源
}
```

> `INDEX_NAMES`（16 项）与 `LEGAL_INDEX_NAMES = frozenset({"legal_index_cn", "legal_index_eu", "legal_index_us", "legal_index_intl"})` 都定义在 `orchestrator.py`。`build_legal_chunks_intl()` 定义在 `builders_v2.py:195`，专门承载国际法域（regional jp/my/kr/hk/vn/sg/tw/mo）法规来源，与 CN/EU/US 三大法域隔离。

**各 Builder 详解：**

#### 2.5.1 `build_legal_chunks_cn()` — 法规条文构建

**数据来源：** `resources/legal/registry/regulation_articles.jsonl`

每条 JSONL 行包含：
```json
{
  "article_id": "CN-LAW-003-ART39",
  "source_id": "CN-LAW-003",
  "law_name": "中华人民共和国个人信息保护法",
  "article_ref": "第三十九条",
  "content": "个人信息处理者向中华人民共和国境外提供个人信息的，应当...",
  "jurisdiction": "cn",
  "path": "assessment",
  "keywords": ["个人信息出境", "单独同意", "告知义务"]
}
```

**构建逻辑：**
1. 读取 `regulation_articles.jsonl`，逐行解析
2. 按 `jurisdiction` 过滤（cn/eu/us 分别构建）
3. 从 `SourceRegistry` 获取对应条目的元数据（authority_level、binding_force）
4. 从 `sources.csv` 获取补充字段（source_url、snapshot_path、status）
5. 按 `path` 推断所属 module（assessment → cn_assessment，review → cn_review）
6. 生成 `KnowledgeChunkV2` 对象，包含完整元数据

#### 2.5.2 `build_workflow_chunks_cn()` — 业务规则构建

**数据来源：** 硬编码在代码中的规则字典列表

**中国诊断规则示例：**
```
WF-CN-DIAG-CIIO:  CIIO 触发安全评估
  condition: is_ciio == true → output_action: security_assessment
  reference_ids: [CN-REG-004, CN-LAW-003]

WF-CN-DIAG-PII-THRESHOLD: 个人信息数量阈值判断
  condition: pii_count >= 1,000,000 → output_action: security_assessment
```

**中国安全评估规则示例：**
```
WF-CN-ASSESS-MATERIALS: 安全评估申报材料清单
  required_materials: [自评估报告, 申报书, 法律文件摘要, 接收方安全能力证明, 必要性说明]

WF-CN-ASSESS-LEGAL-DOC: 法律文件重点核查项
  required_terms: [再转移约束, 保存期限, 违约责任, 争议解决, 个人权利保障]
```

**中国审查规则示例：**
```
WF-CN-REVIEW-PRIVACY: 隐私政策高风险核查框架
  document_type: privacy_policy
  required_topics: [告知同意, 境外接收方信息, 撤回机制, 权利响应期限, 敏感个人信息保护]

WF-CN-REVIEW-DPA: 委托处理协议高风险核查框架
  document_type: dpa
  required_topics: [处理范围, 出境责任分配, 安全措施, 删除返还证明, 标准合同优先级]
```

#### 2.5.3 `build_standard_clause_chunks_cn()` — 标准合同条款构建

**数据来源：** `resources/rules/cn/review_rulebook.json`（经 `resource_paths.rule_resource_path("cn", "review_rulebook.json")` 解析，`RULE_ROOT = PROJECT_ROOT / "resources" / "rules"`）+ 硬编码条款

每个标准条款包含：
- `clause_type`：条款类型（CROSS_BORDER_TRANSFER / RIGHTS_REQUEST / LIABILITY / RETENTION_DELETION 等）
- `protected_obligations`：受保护的核心义务列表
- `modification_sensitivity`：修改敏感度（high / medium / low）

**示例条款：**
```
STD-CN-SCC-PRIORITY: 标准合同优先性保护
  当标准合同正文与其他协议不一致时，不得约定由其他协议优先适用
  protected_obligations: [standard_contract_priority, no_conflicting_master_agreement]

STD-CN-DPA-COMPLIANCE: 出境合规责任不得整体转嫁
  出境合规责任应由个人信息处理者主导，不宜整体约定由受托方单方完成
  protected_obligations: [controller_primary_responsibility, no_full_responsibility_shift]
```

#### 2.5.4 `build_template_chunks_cn()` — 模板结构构建

**数据来源：**
1. `resources/templates/cn/official_template_schema.json` — 官方模板的章节结构定义
2. `resources/templates/cn/official_risk_self_assessment_template.md` — 示例文本（限 1200 字）

每个模板 chunk 携带 `structured_payload`：
```json
{
  "section_id": "basic_info",
  "number": "一",
  "mapped_chapters": ["出境活动概述"],
  "required_inputs": ["company_name", "transfer_purpose", "receiver_country"],
  "required_issues": []
}
```

#### 2.5.5 `build_testcase_chunks_cn()` — 测试案例构建

**数据来源：** 硬编码的评估案例

每个测试案例包含：
```python
{
  "chunk_id": "TC-CN-ASSESS-001",
  "expected_path": "assessment",
  "must_find_issues": ["ISSUE-ciio-security-assessment"],
  "must_cite_source_ids": ["CN-REG-004", "CN-LAW-003"],
  "must_not_claim": ["No issue found"]
}
```

### 2.6 文档摄入管道（IngestionPipeline）

**代码位置：** `backend/common/knowledge/ingestion_pipeline.py`

**完整流程：**

```
用户上传 PDF/DOCX
      │
      ▼
┌──────────────────────────────────────┐
│ Step 1: KnowledgeStorageManager.save()│
│   ├─ SHA-256 哈希去重检查              │
│   ├─ 目录: storage/knowledge/raw/     │
│   │         {jurisdiction}/{doc_type}/ │
│   └─ 文件名: {hash[:8]}_{原名}.pdf     │
├──────────────────────────────────────┤
│ Step 2: DocumentParser.parse_bytes()  │
│   ├─ PDF: pypdf 逐页提取文本           │
│   ├─ DOCX: python-docx 段落解析       │
│   └─ 输出: ParsedDocument             │
│          (.raw_text, .pages, .title)  │
├──────────────────────────────────────┤
│ Step 3: KnowledgeDocument (ORM)      │
│   ├─ 写入 knowledge_documents 表      │
│   └─ review_status = "published"     │
│       或 "review_pending"            │
├──────────────────────────────────────┤
│ Step 4: ChineseLegalChunker.chunk()  │
│   ├─ 按法律结构切分：章→节→条→款→项    │
│   ├─ 每 chunk 含 structural_path     │
│   │   例: "CN-LAW-002/CH5/AR39"      │
│   └─ 写入 knowledge_chunks 表         │
├──────────────────────────────────────┤
│ Step 5: IngestedFile 状态更新         │
│   uploaded → parsed → chunked        │
│   → review_pending / published       │
└──────────────────────────────────────┘
```

**数据库三表关系：**
```
knowledge_documents (1) ──→ (N) knowledge_chunks
         │
ingested_files ──────────→ knowledge_documents (via document_id)
         │
         └── 记录原始文件哈希、路径、状态
```

### 2.7 中国法律结构感知分块器（ChineseLegalChunker）

**代码位置：** `backend/common/knowledge/chunker.py`

**核心算法：**

1. 逐行扫描，用 `chinese_legal_patterns.detect_structure()` 识别结构标记
2. 发现结构边界时，flush 当前 buffer 为新的 chunk
3. 用栈维护层级祖先（章 > 节 > 条 > 款 > 项），出栈/压栈处理层级跳转
4. 构建 `structural_path`：`CN-LAW-002/CH5/AR39`

**支持的结构层级（chinese_legal_patterns.py）：**

| 层级 | 正则 | 示例 | 缩写 |
|------|------|------|------|
| 章 `chapter` | `第[一二三…\d]+章` | 第一章 | CH1 |
| 节 `section` | `第[一二三…\d]+节` | 第一节 | SEC1 |
| 条 `article` | `第[一二三…\d]+条` | 第三十九条 | AR39 |
| 款 `paragraph` | `第[一二三…\d]+款` | 第一款 | PA1 |
| 项 `item` | `（[一二三…\d]）` | （一） | IT1 |

### 2.8 存储管理器（KnowledgeStorageManager）

**代码位置：** `backend/common/knowledge/storage_manager.py`

**核心设计：**

```
storage/knowledge/raw/
├── cn/                    ← 中国法规
│   ├── law/              ← 法律
│   └── regulation/       ← 行政法规/部门规章
├── eu/                    ← 欧盟法规
│   └── law/
├── us/                    ← 美国法规
│   └── law/
└── user/                  ← 用户上传
    └── {user_id}/
```

**哈希去重：**
- 每个文件计算 SHA-256
- 存储时检查是否已存在同哈希文件
- 文件名格式：`{hash[:8]}_{原名}.pdf`
- `save()` 返回 `(hash, path, is_duplicate)` 三元组

### 2.9 使用策略过滤器（UsagePolicyFilter）

**代码位置：** `backend/common/knowledge/usage_policy.py`

**核心机制：** 根据使用目的和环境，决定哪些 chunk 可以进入 LLM 上下文。

| 使用场景 | 允许的 Layer | 额外条件 |
|---------|-------------|---------|
| `legal_grounding` | L1 | can_be_cited=True, source_kind 为法规类 |
| `external_report` | L1 | can_enter_external_report=True, can_be_cited=True |
| `internal_review` | L1 + L2 | 生产环境排除 L3 |
| `structure_control` | L4 | template_type="official_template" |
| `risk_explanation` | L1 + L2 | — |
| `evaluator` | L3 | 仅 eval 环境 |
| `few_shot` | L3 | 仅 dev/eval 环境 |

**典型调用链：**
```python
legal_chunks = orchestrator._search_index("legal_index_cn", query, top_k=8)
filtered = UsagePolicyFilter.filter(
    legal_chunks,
    usage="legal_grounding",
    environment="production"
)
# filtered.chunks  → 进入 LLM prompt
# filtered.rejected_chunk_ids → 记录到 debug 日志
```

---

## 三、检索引擎（rag/）详解

### 3.1 检索架构总览

```
                     LegalRetrievalService (service.py)
                     ┌────────────┼────────────┐
                     │            │            │
              multi_index   single_index  enriched_compat
             (orchestrator) (RegulationRAG) (retrieve_regs)
                     │            │            │
                     ▼            ▼            ▼
            RetrievalOrchestrator  HybridRetriever  DeliLegal API
            ┌──────┼──────┐      ┌────┼────┐
            │      │      │      │    │    │
          Vector Lexical FTS   Vector FTS5 RRF
          ┌──────┴──────┐
          │ LocalVectorStore │
          │ (JSON 文件)      │
          └─────────────────┘
```

### 3.2 三后端路由机制

**代码位置：** `backend/common/rag/service.py` — `LegalRetrievalService`

| 后端 | 适用场景 | 索引数量 | 检索策略 |
|------|---------|---------|---------|
| `multi_index` | **默认首选**，生产环境 | 16 个专用索引 | Vector + Lexical RRF 融合 × module/stage 路由 |
| `single_index` | 降级/兼容 | 1 个合并索引 | Vector + Lexical 加权 7:3 |
| `enriched_compatibility` | 最后回退 | 1 个合并索引 | 同上 + DeliLegal 外部 API 补充 |

**三级回退链（`retrieve_with_fallback`）：**

```
multi_index (首选)
    │
    ├── 命中 → 返回
    │
    └── 未命中 → single_index (一级回退)
                    │
                    ├── 命中 → 返回
                    │
                    └── 未命中 → enriched_compatibility (二级回退)
                                    └── DeliLegal API 在线检索补充
```

### 3.3 RetrievalOrchestrator — 多索引编排器

**代码位置：** `backend/common/rag/orchestrator.py`

**16 个索引矩阵：**

| 索引名 | 内容 | cn | eu | us | intl |
|--------|------|:--:|:--:|:--:|:--:|
| `legal_index_*` | 法律条文原文 | ✅ | ✅ | ✅ | ✅ |
| `workflow_index_*` | 业务规则 | ✅ | ✅ | ✅ | ❌ |
| `standard_clause_index_*` | 标准合同条款 | ✅ | ✅ | ✅ | ❌ |
| `template_index_*` | 报告模板结构 | ✅ | ✅ | ✅ | ❌ |
| `testcase_index_*` | 测试案例 | ✅ | ✅ | ✅ | ❌ |

> 国际法域（`intl`）只有一个 `legal_index_intl`，承载 JP/KR/MY/HK/VN/SG/TW/MO 等区域法规来源，暂不单独拆分 workflow/standard_clause/template/testcase 四类子索引。

**按模块 × 阶段路由：**

```python
def retrieve(self, request: RetrievalRequest) -> RetrievalBundle:
    # 中国诊断
    if request.module == "cn_diagnosis":
        workflow = search("workflow_index_cn")  → 通过 reference_ids 回链法律条文
        legal = search_by_reference_ids(workflow)
    
    # 中国安全评估
    if request.module == "cn_assessment":
        if stage == "issue_discovery" / "legal_grounding":
            workflow = search("workflow_index_cn", filters={"module": "cn_assessment"})
            legal = search("legal_index_cn", filters={"path": "assessment"})
            legal.extend(backlink_from_workflow())
        if stage == "report_generation":
            templates = search("template_index_cn")
        if stage == "evaluation":
            testcases = search("testcase_index_cn")
    
    # 中国文档审查
    if request.module == "cn_review":
        if stage == "clause_compare":
            standard = search("standard_clause_index_cn")
        # ... 类似的分阶段路由
```

**一个检索周期的流程：**

```
request (query="数据出境安全评估触发条件")
    │
    ├─ module 路由: cn_assessment
    ├─ stage 路由: legal_grounding
    │
    ▼
_search_index("workflow_index_cn", query, top_k=8)
    │
    ├─ 1. Vector search (LocalVectorStore.search)
    │       └─ HashingEmbedder.embed(query) → 稀疏向量 → 余弦相似度排序
    │
    ├─ 2. Lexical search (_lexical_score)
    │       └─ 精确匹配 + token 重叠 + 场景标签匹配
    │
    ├─ 3. RRF 融合 (vector rank + lexical rank → 加权求和)
    │       └─ 公式: score = Σ (1 / (60 + rank_i))
    │
    └─ 4. Filters → top_k 结果
    │
    ▼
_search_index("legal_index_cn", query, top_k=8, filters={"path": "assessment"})
    │       (同上流程)
    │
    ├─ 5. _legal_by_reference_ids(workflow_chunks)
    │       └─ workflow 结果中的 reference_ids 回链加载法律原文
    │
    └─ 6. _dedupe_chunks (按 chunk_id 去重)
    │
    ▼
UsagePolicyFilter.filter(chunks, usage="legal_grounding")
    │
    ▼
RetrievalBundle(legal_grounding=[...], workflow_rules=[...])
```

### 3.4 向量化引擎（HashingEmbedder）

**代码位置：** `backend/common/rag/embedding.py`

**为什么不用 OpenAI Embedding？** 本项目采用自研的确定性哈希嵌入器，原因：
1. **零成本**：不需要调用外部 API
2. **确定性**：同一文本始终生成相同向量，便于缓存和离线索引
3. **足够好**：对于法律条文这种高度结构化的中文文本，稀疏 token 向量已经够用

**算法流程：**

```
输入文本 "个人信息处理者向境外提供个人信息"
    │
    ▼
tokenize_text()
    ├─ 提取英文/数字 token: [a-z0-9_+-]+
    ├─ 提取中文字符: 个→人→信→息→处→理→者→向→境→外→提→供→个→人→信→息
    └─ 生成 2-gram + 3-gram:
        个人信息, 信息处理, 处理者向, 者向境外, ...
        个人信息处, 信息处理者, 处理者向境, ...
    │
    ▼
Counter(token) → 词频统计
    │
    ▼
每个 token → SHA-256 → 取前 8 字节 → mod 384 → 向量索引
    │
    ▼
L2 归一化 → {index: normalized_value, ...}
    │
    ▼
稀疏向量（大部分维度为 0）
```

**相似度计算：** 两个稀疏向量的共享非零维度内积 → 余弦相似度等价

```python
similarity(left, right) = Σ (left[i] * right[i]) for i in (left.keys() & right.keys())
```

### 3.5 LocalVectorStore — 本地向量存储

**代码位置：** `backend/common/rag/vector_store.py`

**存储格式：** 单个 JSON 文件

```json
{
  "metadata": {
    "schema_version": "v3.2",
    "embedding_version": "sha256-v1",
    "embedding_dimension": 384,
    "entry_count": 150
  },
  "entries": [
    {
      "doc_id": "CN-LAW-003-ART39",
      "payload": {
        "id": "CN-LAW-003-ART39",
        "title": "中华人民共和国个人信息保护法",
        "article": "第三十九条",
        "content": "个人信息处理者向境外提供个人信息的，应当..."
      },
      "search_text": "个人信息保护法 第三十九条 ...",
      "embedding": { "12": 0.23, "47": 0.15, "89": 0.08, ... }
    }
  ]
}
```

**版本兼容性检查（`has_compatible_embedding`）：**
- 检查 metadata 中的 `embedding_version` 和 `embedding_dimension`
- 不匹配则触发自动重建索引

### 3.6 混合检索融合策略

#### 3.6.1 RRF（Reciprocal Rank Fusion）

**代码位置：** `backend/common/rag/hybrid_retriever.py` — `_rrf_fusion()`

```
RRF 公式: score(doc) = Σ 1/(k + rank_i)

其中 k=60（常数），rank_i 是文档在第 i 个检索器中的排名

示例：
  向量排名 [A:1, B:2, C:3]
  FTS5 排名 [B:1, C:2, D:3]
  
  A: 1/(60+1) = 0.0164
  B: 1/(60+2) + 1/(60+1) = 0.0161 + 0.0164 = 0.0325
  C: 1/(60+3) + 1/(60+2) = 0.0159 + 0.0161 = 0.0320
  D: 1/(60+3) = 0.0159
  
  最终排序: B > C > A > D
```

#### 3.6.2 Orchestrator 的 Vector + Lexical 融合

**代码位置：** `orchestrator.py` — `_search_index()`

不同于 RRF，使用**加权排名倒数融合**：

```python
# 对每个检索通道的命中结果累加加权分
for rank, (score, entry) in enumerate(vector_hits, start=1):
    merged_scores[doc_id] += 1.0 / (60 + rank)

for rank, (score, entry) in enumerate(lexical_hits, start=1):
    if score > 0:  # 仅正分加入
        merged_scores[doc_id] += 1.0 / (60 + rank)
```

#### 3.6.3 RegulationRAGService 的加权融合

**代码位置：** `retriever.py` — `retrieve()`

```python
if mode == "hybrid":
    base_score = vector_score * 0.7 + lexical_score * 0.3  # 7:3 加权
elif mode == "vector":
    base_score = vector_score
elif mode == "lexical":
    base_score = lexical_score
```

**不同模式的最低分阈值（score_floor）：**
- `vector`：0.05
- `hybrid`：0.1
- `lexical`：2.0

### 3.7 词法评分器（_lexical_score）

**代码位置：** `orchestrator.py` + `retriever.py` — 两个独立的实现

**Orchestrator 版本（用于多索引）：**
```
1. query 完全在 body 中或 body 前 80 字在 query 中 → +3.0
2. token 重叠数 × 0.35，上限 4.0
3. 场景标签匹配 → 每个 +0.5
```

**Retriever 版本（用于单索引）：**
```
1. law_hint（提取的法名）匹配 title → +6.0
2. article_hint（提取的条号）匹配 article → +3.0
3. query 在 title 中或反之 → +4.0
4. token 重叠数 × 0.35，上限 6.0
5. 关键词匹配 → 每个 +0.4
```

### 3.8 重排序器（HeuristicReranker）

**代码位置：** `backend/common/rag/reranker.py`

在初次检索后，对候选人做精细化的二次排序：

```python
final_score = base_score
    + phrase_bonus      # title 完全匹配 query → +2.0, article 匹配 → +1.2
    + overlap_bonus     # token 重叠数 × 0.15，上限 2.4
    + keyword_bonus     # 关键词匹配 × 0.3，上限 1.2
    + metadata_bonus    # jurisdiction/path 精确匹配 → 各 +0.4
```

### 3.9 查询改写（Query Rewriting）

**代码位置：** `retriever.py` — `_rewrite_query()`

当查询中缺少法域或路径信号时，自动补充关键词：

```python
# 法域提示词
JURISDICTION_HINTS = {
    "cn": ("数据出境", "个人信息", "重要数据", "网信", "安全评估", "pipl"),
    "eu": ("gdpr", "edpb", "bcr", "dpia", "tia"),
    "us": ("cpra", "ccpa", "california", "eo 14117"),
}

# 路径提示词
PATH_HINTS = {
    "assessment": ("安全评估", "100万", "10万敏感"),
    "scc": ("标准合同", "认证", "备案"),
    "review": ("合同审查", "条款", "协议", "合规审查"),
}

# 改写：
"数据出境需要什么条件" → "数据出境需要什么条件 安全评估 100万 pipl"
```

**越界检测：** 在被改写前先检查：
- `_is_off_topic_query()`：包含 weather/python/steak 等非法律词 → 直接返回空
- `_is_jurisdiction_mismatch()`：cn 关键词但查 eu 索引 → 直接返回空

### 3.10 外部回退（DeliLegal API）

**代码位置：** `retriever.py` — `retrieve_regulations()`

当本地索引结果不足（`len(docs) < min_local`，默认 3）且 DeliLegal API 可用时：

```python
remote_hits = delilegal.search_laws(query, size=top_k - len(docs))
for hit in remote_hits:
    docs.append(RegulationDoc(
        id=f"delilegal-{title[:20]}",
        title=hit["title"],
        content=hit["summary"],
        doc_type="external"   # 标记为外部来源
    ))
```

### 3.11 RAG 命中日志

**代码位置：** `retriever.py` — `_log_rag_hits()`

可选功能，由环境变量控制：

| 环境变量 | 作用 |
|---------|------|
| `AI4LAW_RAG_LOG=1` | 启用日志 |
| `AI4LAW_RAG_LOG_DIR=/path` | 日志输出目录（默认 `outputs/qa/`） |

日志格式：每行一个 JSONL，记录 query、rewritten_query、jurisdiction、path、mode、top_k、hit_count 及每条命中详情。

---

## 四、知识库的数据来源与更新方式

### 4.1 数据源全景

```
┌──────────────────────────────────────────────────────────────┐
│                      数据来源层次                              │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ① regulation_articles.jsonl  ─── 预处理的法规条文（JSONL）     │
│     │  路径: resources/legal/registry/                        │
│     │  更新: 手动维护 / 脚本生成                               │
│     │  内容: 逐条法规原文 + 元数据                              │
│     │                                                        │
│  ② sources.csv  ─── 法规来源目录（CSV）                        │
│     │  路径: resources/legal/catalog/                         │
│     │  更新: 手动编辑 CSV                                      │
│     │  内容: 法规名称/法域/路径/类型/发布日期/URL/review_status 等 │
│     │                                                        │
│  ③ 硬编码业务规则  ─── builders_v2.py 内                      │
│     │  workflow_chunks: 合规判断逻辑规则                        │
│     │  standard_clause_chunks: 合同审查标准条款                  │
│     │  testcase_chunks: 评估/审查测试用例                       │
│     │  更新: 修改代码后重新部署                                 │
│     │                                                        │
│  ④ 官方模板文件  ─── resources/templates/                     │
│     │  official_template_schema.json: 章节结构                 │
│     │  official_risk_self_assessment_template.md: 示例文本      │
│     │  更新: 手动维护                                          │
│     │                                                        │
│  ⑤ 用户上传文档  ─── 通过 API 上传 PDF/DOCX                   │
│     │  存储: storage/knowledge/raw/                           │
│     │  处理: IngestionPipeline → 分块写入 knowledge_chunks 表  │
│     │  更新: 用户随时通过 API 上传                              │
│     │                                                        │
│  ⑥ DeliLegal API  ─── 外部法律数据在线检索                     │
│     │  触发: 本地索引结果不足时自动回退                          │
│     │  更新: 实时（依赖第三方服务）                              │
│     │                                                        │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 索引构建与刷新

#### 4.2.1 单索引（v1 兼容）

**触发方式：** 首次检索时自动检查并构建

```python
# retriever.py
def _ensure_entries(self):
    if not self.vector_store.has_compatible_embedding():
        if self.settings.rag_auto_build_index:
            build_regulation_index(self.settings)  # → ingest.py
    return tuple(self.vector_store.load())
```

**构建流程：**
```
regulation_articles.jsonl
    │
    ▼
ingest.py: load_regulation_rows() → 逐行解析 JSONL
    │
    ▼
ingest.py: build_regulation_index()
    ├─ 每行 → payload {id, title, article, content, jurisdiction, path, ...}
    ├─ build_search_text(row) → 拼接 law_name + article_ref + content + keywords
    ├─ embedder.embed(search_text) → 稀疏向量
    └─ store.save(entries, metadata) → 写入 regulation_index_v2.json
```

**输出：** `storage/rag/regulation_index_v2.json`（单文件，包含所有法域；`settings.rag_index_path`）

#### 4.2.2 多索引 v3（生产默认）

**触发方式：** Orchestrator 首次检索时自动检查 16 个索引文件的版本兼容性

```python
# orchestrator.py
def _ensure_multi_indexes(self):
    for name in INDEX_NAMES:  # 16 个索引
        if not self._is_index_current(name):
            build_multi_index_v3(self.settings)  # → ingest.py
            break
```

**版本检查（_is_index_current）：**
```
1. 索引文件存在？
2. schema_version == "v3.2"？
3. embedding_version == "sha256-v1"？
4. embedding_dimension 匹配（settings.rag_embedding_dimension = 384）？

→ 任一不满足 → 重建全部 16 个索引
```

**构建流程：**
```
build_chunk_sets() → 16 个 chunk 列表     (orchestrator.py:654)
    │
    ▼
ingest.py: build_multi_index_v3()
    ├─ for each index_name in INDEX_NAMES:
    │   ├─ chunks → 每个 chunk 嵌入向量
    │   ├─ store.save(vector_path) → {index_name}.vector.json
    │   └─ jsonl_path → {index_name}.jsonl (备份)
    │
    └─ 输出: storage/rag/v3/*.vector.json + *.jsonl (32 个文件)
```

**输出目录结构：**
```
storage/rag/v3/
├── legal_index_cn.vector.json      # 中国法律（向量）
├── legal_index_cn.jsonl            # 中国法律（原始数据备份）
├── workflow_index_cn.vector.json   # 中国业务规则
├── workflow_index_cn.jsonl
├── standard_clause_index_cn.vector.json
├── ...
├── legal_index_eu.vector.json
├── ...
├── testcase_index_us.vector.json
└── legal_index_intl.vector.json    # 共 32 个文件
```

### 4.3 更新机制的完整矩阵

| 数据层 | 文件位置 | 更新方式 | 生效时机 | 是否需要重建索引 |
|--------|---------|---------|---------|:---:|
| 法规条文 | `regulation_articles.jsonl` | 手动编辑 | 重启服务 / 索引版本不匹配自动重建 | ✅ |
| 来源目录 | `sources.csv` | 手动编辑 CSV | 删除 `source_registry.v1.json` 后重启 | ✅ |
| 业务规则 | `builders_v2.py` | 修改代码 → 部署 | 重启服务 / 索引版本不匹配自动重建 | ✅ |
| 模板结构 | `official_template_schema.json` | 手动编辑 | 重启服务 | ✅ |
| 用户文档 | API 上传 | 实时 API 调用 | 即时（写入 DB） | ❌（不进入主索引） |
| 外部 API | DeliLegal | 无需维护 | 实时 | ❌ |

**为什么用户上传文档不进入向量索引？**
- 用户文档流经 `IngestionPipeline` → 写入 `knowledge_documents` + `knowledge_chunks` 表
- 存储在 SQLite 中，通过 `FulltextIndex(FTS5)` 进行全文检索
- 不走 `build_chunk_sets()` → 多索引 v3 流程，避免混入未审核的用户数据进入 LLM 外部报告生成

### 4.4 索引重建的手动触发

```bash
# 方式 1: 删除索引文件后重启
rm -rf storage/rag/v3/
# 服务启动后首次检索自动重建

# 方式 2: 手动修改 constants.py 的版本号
# MULTI_INDEX_SCHEMA_VERSION = "v3.3"  → 下次检索时检测到不匹配，自动重建

# 方式 3: Python 脚本手动构建
python3 -c "
from backend.common.rag.ingest import build_multi_index_v3
from backend.core.settings import get_settings
build_multi_index_v3(get_settings())
"
```

---

## 五、检索全链路示例（从用户提问到返回结果）

```
用户问题: "数据出境安全评估的触发条件是什么？"
    │
    ▼
┌─ 1. LegalRetrievalService.retrieve()                         ─┐
│    backend: "multi_index"                                     │
│    → RetrievalOrchestrator.retrieve(request)                  │
├─ 2. 模块路由                                                   │
│    module="cn_assessment" → _retrieve_cn_assessment()          │
├─ 3. 阶段路由                                                   │
│    stage="legal_grounding"                                     │
├─ 4. 检索 workflow_index_cn                                     │
│    query → _search_index("workflow_index_cn", query)          │
│    ├─ vector: 384 维稀疏向量 × 80 条规则 → Top-K               │
│    ├─ lexical: 关键词匹配 + token 重叠 → Top-K                 │
│    ├─ RRF 融合排名                                             │
│    └─ filter: module="cn_assessment"                          │
│    → [WF-CN-DIAG-PII-THRESHOLD, WF-CN-DIAG-CIIO, ...]        │
├─ 5. 回链法律原文                                               │
│    reference_ids: [CN-REG-004, CN-LAW-003]                    │
│    → _legal_by_reference_ids()                                │
│    → 从 legal_index_cn 加载对应 chunk                          │
├─ 6. 直接检索 legal_index_cn                                    │
│    query → _search_index("legal_index_cn", query)             │
│    filter: path="assessment"                                  │
│    → [个保法第38条, 安全评估办法第4条, ...]                     │
├─ 7. 去重                                                       │
│    _dedupe_chunks(legal) → 按 chunk_id 去重                   │
├─ 8. 使用策略过滤                                               │
│    UsagePolicyFilter.filter(legal, usage="legal_grounding")   │
│    → 仅保留 L1 + can_be_cited + 法规类型                       │
├─ 9. 组装返回                                                   │
│    RetrievalBundle(                                            │
│      legal_grounding=[KnowledgeChunkV2 × 5],                   │
│      workflow_rules=[KnowledgeChunkV2 × 3],                    │
│      debug={stage, rejected_chunk_ids, ...}                   │
│    )                                                           │
├─ 10. 写入 Manifest                                             │
│    RetrievalManifest(                                          │
│      backend="multi_index",                                    │
│      hit_count=8, duration_ms=45,                              │
│      index_schema_version="v3.2"                              │
│    )                                                           │
└─ 11. 返回 LegalRetrievalResult(bundle, manifest)             ─┘
    │
    ▼
LLM Agent 使用这些 chunk 内容填充 prompt:
  "以下是相关法律条文，请基于这些条文回答用户问题：
   [1] 数据出境安全评估办法 第四条：数据处理者向境外提供数据，有下列情形之一的...
   [2] 中华人民共和国个人信息保护法 第四十条：关键信息基础设施运营者...
   ..."
```

---

## 六、关键设计决策

### 6.1 为什么用哈希嵌入而不用模型嵌入？

| 维度 | HashingEmbedder (当前) | OpenAI Embedding | 本地模型 (bge/m3e) |
|------|----------------------|-------------------|-------------------|
| 成本 | 零 | $0.02/1K tokens | GPU 资源 |
| 确定性 | 完全确定 | 略有波动 | 完全确定 |
| 中文能力 | 稀疏 2-3 gram 够用 | 优秀 | 优秀 |
| 法律文本适应性 | 法律条文短、结构固定，稀疏匹配足够 | 过强 | 过强 |
| 离线可用 | ✅ | ❌ | ✅ |

**结论：** 对于法律条文的条文标题+条号+关键词这种高度结构化内容的检索，哈希嵌入的召回精度足够（法律条文天然具备精确匹配特性），而零成本和无外部依赖的优势很关键。

### 6.2 为什么分 16 个索引而不是 1 个？

1. **法域隔离**：中国、欧盟、美国、国际法域（JP/KR/MY/HK/VN/SG/TW/MO）法规不可能交叉引用，分开避免噪音——尤其 `legal_index_intl` 把区域来源与 CN/EU/US 主法域彻底隔离，避免 JP/KR 来源"整体错位"污染三大法域检索
2. **类型隔离**：法律条文、业务规则、模板的检索语义完全不同
3. **阶段路由**：`issue_discovery` 阶段需要 workflow + legal，`report_generation` 阶段需要 template，按需加载
4. **relevance 提升**：在 50 条规则中搜比在 500 条混合数据中搜更精确

### 6.3 为什么用户文档不进向量索引？

- 用户上传的 PDF/DOCX 走 `IngestionPipeline` → `knowledge_chunks` 表 → FTS5 全文索引
- 不进 `build_chunk_sets()` → 不进 v3 向量索引
- 原因：用户文档未审核，不应直接进入 LLM 外部报告生成的知识库；但可通过 FTS5 全文检索供内部参考

### 6.4 Control Plane 如何收紧 RAG 引用

CN Security Assessment 在 `control=true` 时为 Citation 构建注入 `backend/common/citation/source_identity.py` 的 `SourceIdentityResolver`。Resolver 只负责两件事：通过 exact membership 判断 `source_id` 是否在 SourceRegistry 注册，并读取 Registry 权威字段判断 Eligibility；未注册或不具备引用资格的来源不会被提升为正式 citation。Traceability 不由 Resolver 判断，而由 `backend/domains/cn/security_assessment/citation_validity_gate.py` 的 C3 检查完成：它核对 Citation 的 `related_issue_ids`、`related_fact_ids`、`related_evidence_ids` 是否能回指本次 ContextPack。控制平面目前只贯通 CN Transfer Diagnosis 与 CN Security Assessment，其余 9 个模块仍走原有检索路径——因此 RAG 返回命中不等于法律结论，`allowed_usage`、`can_be_cited` 和模块 stage 仍需由上层 workflow/citation gate 解释。

---

## 七、文件路径速查表

| 代码文件 | 完整路径 |
|---------|---------|
| 检索服务门面 | `backend/common/rag/service.py` |
| 多索引编排器 | `backend/common/rag/orchestrator.py` |
| 单索引检索器 | `backend/common/rag/retriever.py` |
| 增强混合检索器 | `backend/common/rag/hybrid_retriever.py` |
| 向量存储 | `backend/common/rag/vector_store.py` |
| 哈希嵌入器 | `backend/common/rag/embedding.py` |
| 重排序器 | `backend/common/rag/reranker.py` |
| 全文索引 | `backend/common/rag/fulltext_index.py` |
| 索引构建 | `backend/common/rag/ingest.py` |
| 核心数据模型 | `backend/common/knowledge/v2.py` |
| ORM 数据模型 | `backend/common/knowledge/models.py` |
| Chunk Builder | `backend/common/knowledge/builders_v2.py` |
| 来源注册表 | `backend/common/knowledge/registry.py` |
| 摄入管道 | `backend/common/knowledge/ingestion_pipeline.py` |
| 文档解析器 | `backend/common/knowledge/document_parser.py` |
| 法律分块器 | `backend/common/knowledge/chunker.py` |
| 法律正则模式 | `backend/common/knowledge/chinese_legal_patterns.py` |
| 存储管理器 | `backend/common/knowledge/storage_manager.py` |
| 使用策略过滤 | `backend/common/knowledge/usage_policy.py` |
| 知识库 API | `backend/api/v1/endpoints/knowledge.py` |

| 数据文件 | 路径 |
|---------|------|
| 法规条文数据 | `resources/legal/registry/regulation_articles.jsonl` |
| 来源目录 | `resources/legal/catalog/sources.csv` |
| 模块目录 | `resources/legal/catalog/module_catalog.v1.json` |
| 来源注册表缓存 | `resources/legal/registry/source_registry.v1.json` |
| 审查规则库 | `resources/rules/cn/review_rulebook.json` |
| 官方模板结构 | `resources/templates/cn/official_template_schema.json` |
| 向量索引 (v3) | `storage/rag/v3/{index_name}.vector.json` + `.jsonl`（16 索引 × 2 = 32 文件） |
| 向量索引 (v1) | `storage/rag/regulation_index_v2.json` |
| 知识库文件存储 | `storage/knowledge/raw/{jurisdiction}/{doc_type}/` |

> 本文档于 2026-08-16 基于 `new` 分支当前代码事实重新生成，已同步 task065（JP/KR 来源隔离 + `legal_index_intl`）与 task073（Legal Control 来源身份门禁）；来源真相以 `sources.csv`、Registry 和对应 snapshot 为准，改动后须重新生成并执行 `scripts/build_source_registry.py --check`。
