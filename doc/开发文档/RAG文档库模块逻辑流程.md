# RAG 文档库模块 — 逻辑流程文档

## 一、模块概述

RAG 文档库是一个**完整的分层知识检索增强生成系统**，核心分布在两个目录：
- `backend/common/knowledge/*` — 知识定义、治理、构建
- `backend/common/rag/*` — 检索、索引、编排、评测

整个系统按照"知识建模 → 分层入库 → 索引生成 → 检索编排 → Usage Policy 过滤 → 业务消费 → 评测回归"七阶段闭环运行。核心理念是**将知识按层级（L1-L4）建模，按用途（usage）做强约束过滤**，避免不同层次的知识在生产环境中混用。

---

## 二、整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│  知识治理层 (knowledge/)                                         │
│                                                                  │
│  source_registry.v1.json  ← 知识源注册表                        │
│  module_catalog.v1.json   ← 模块-索引-阶段映射                   │
│  sources.csv              ← 原始知识源清单                       │
│                                                                  │
│  registry.py: ensure_source_registry() / load_module_catalog()  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Chunk 构建层 (knowledge/builders_v2.py)                         │
│                                                                  │
│  ┌─ build_legal_chunks_cn/eu/us()         → L1 法规条文         │
│  ├─ build_workflow_chunks_cn/eu/us()      → L2 业务规则         │
│  ├─ build_standard_clause_chunks_cn/eu/us() → L1 标准条款       │
│  ├─ build_template_chunks_cn/eu/us()      → L4 模板             │
│  └─ build_testcase_chunks_cn/eu/us()      → L3 评测案例         │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  索引生成层 (rag/ingest.py)                                      │
│                                                                  │
│  build_multi_index_v3() → 15 个独立索引                         │
│  legal_index_{cn,eu,us} / workflow_index_{cn,eu,us}             │
│  standard_clause_index_{cn,eu,us} / template_index_{cn,eu,us}   │
│  testcase_index_{cn,eu,us}                                      │
│                                                                  │
│  输出: storage/rag/v3/{name}.vector.json + {name}.jsonl         │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  检索编排层 (rag/orchestrator.py)                                │
│                                                                  │
│  RetrievalOrchestrator.retrieve(RetrievalRequest)                │
│    ├── module + task_stage 路由                                  │
│    ├── cn_diagnosis → workflow_cn → legal_cn (by reference_ids) │
│    ├── cn_assessment → issue_discovery / report_generation      │
│    ├── cn_review → issue_discovery / clause_compare             │
│    ├── eu_* → workflow_eu + legal_eu + standard_clause_eu       │
│    └── us_* → workflow_us + legal_us + standard_clause_us       │
│                                                                  │
│  检索策略: Vector(BF16 hash) + Lexical(token overlap) RRF 融合  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Usage Policy 过滤器 (knowledge/usage_policy.py)                 │
│                                                                  │
│  UsagePolicyFilter.filter(chunks, usage, environment, jurisdiction)│
│    ├── external_report → 仅 L1 + can_enter_external_report      │
│    ├── legal_grounding → 仅 L1 + can_be_cited                   │
│    ├── internal_review → L1 + L2                                │
│    ├── structure_control → 仅 L4 official_template              │
│    ├── evaluator/few_shot → 仅 L3 (dev/eval 环境)               │
│    ├── production → 封禁 L3_testcase                            │
│    └── jurisdiction hard gate → 跨法域直接 reject               │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  业务消费层                                                      │
│                                                                  │
│  ┌─ AssessmentRetriever (modules/assessment/retriever.py)       │
│  │   → orchestrator + 旧 retrieve_regulations() 兼容合并         │
│  │   → 拆分为 legal_grounding / workflow / template / eval     │
│  ├─ LocalRegulationKnowledgeBase (services/review_service/)     │
│  │   → issue_discovery + clause_compare 双重检索               │
│  │   → 法域+文档类型智能解析 module                             │
│  └─ 兼容检索层 (rag/retriever.py)                               │
│      → retrieve_regulations() 旧入口 (hybrid/vector/lexical)    │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  评测回归层 (rag/eval.py)                                        │
│                                                                  │
│  run_retrieval_eval() → Recall@K / MRR / 禁用层召回率           │
│  run_generation_eval() → Issue recall / 引用正确率 / 泄漏率      │
│  评测数据: doc/knowledge/evaluation/*.jsonl (cn/eu/us × 6)      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、知识分层模型 (v2.py)

### 3.1 四层知识体系

| 层级 | 名称 | 允许的 Usage | 生产环境 | 示例 |
|------|------|-------------|---------|------|
| L1 | regulatory_evidence | legal_grounding, external_report, internal_review, risk_explanation | ✅ | 法规条文、官方指南、标准条款 |
| L2 | business_rule | internal_review, risk_explanation | ✅ | 业务判断规则、工作流规则 |
| L3 | testcase | evaluator, few_shot | ❌ 封禁 | 评测案例、回归测试数据 |
| L4 | template | structure_control, internal_drafting | ✅ | 报告模板（仅 official_template 进结构控制） |

### 3.2 核心数据类型

```
SourceRegistryEntry          # 知识源注册条目
  ├── source_id, title, jurisdiction, modules[]
  ├── layer, source_kind, authority_level, binding_force
  ├── allowed_usage[], can_be_cited, can_enter_external_report
  └── status, review_status

KnowledgeChunkV2             # 知识片段 V2
  ├── chunk_id, source_id, title, content
  ├── layer (L1/L2/L3/L4), source_kind
  ├── module, jurisdiction, doc_type, path
  ├── allowed_usage[], can_be_cited, can_enter_external_report
  ├── reference_ids[], citation_anchor
  ├── article_no, scenario_tags[], keywords[]
  └── structured_payload (自由扩展字段)

RetrievalRequest → RetrievalBundle
  ├── module (10 种模块)
  ├── task_stage (7 种阶段)
  ├── query, jurisdiction, document_type, top_k
  └── → legal_grounding[] / workflow_rules[] / standard_clauses[]
       templates[] / testcases[]

UsageScopedContext           # Usage 过滤后的上下文
  ├── usage, environment
  ├── chunks[] (通过过滤的)
  └── rejected_chunk_ids[] (被拒绝的)
```

### 3.3 10 种 Module 与 7 种 TaskStage

| Module | 法域 | 用途 |
|--------|------|------|
| cn_diagnosis | cn | 合规路径诊断 |
| cn_assessment | cn | 数据出境安全评估 |
| cn_review | cn | 文档合规审查 |
| eu_scc | eu | EU SCC 审查 |
| eu_bcr | eu | EU BCR 审查 |
| eu_dpia | eu | EU DPIA 生成 |
| eu_tia | eu | EU TIA 生成 |
| us_eo14117 | us | US EO14117 审查 |
| us_vendor_review | us | US 供应商审查 |
| us_privacy_review | us | US 隐私政策审查 |

| TaskStage | 说明 |
|-----------|------|
| path_diagnosis | 路径诊断 |
| document_type_detection | 文档类型检测 |
| issue_discovery | 问题发现 |
| legal_grounding | 法规绑定 |
| clause_compare | 条款比对 |
| report_generation | 报告生成 |
| evaluation | 评测 |

---

## 四、知识治理层

### 4.1 Source Registry (registry.py)

**`ensure_source_registry()`** 逻辑：
1. 若 `doc/knowledge/registry/source_registry.v1.json` 存在 → 直接反序列化
2. 否则从 `doc/knowledge/index/sources.csv` 构建：
   - 按法域 (`cn`/`eu`/`us`) 过滤
   - 按 path (`assessment`/`review`/`all`) 分配模块
   - 自动推断 source_kind（`law_article`/`official_guide`/`standard_clause`）
   - 自动推断 binding_force（`mandatory`/`recommended`/`reference`）
3. 生成 `source_registry.v1.json` 持久化

### 4.2 Module Catalog (module_catalog.v1.json)

定义每个模块的可用索引、支持 stage、默认 usage scope、法域：

```json
{
  "cn_assessment": {
    "indexes": ["workflow_index_cn", "legal_index_cn", "template_index_cn", "testcase_index_cn"],
    "stages": ["issue_discovery", "legal_grounding", "report_generation", "evaluation"],
    "default_usage_scopes": ["internal_review", "legal_grounding", "structure_control"],
    "jurisdiction": "cn",
    "production_enabled": true
  }
}
```

`eu_bcr`、`eu_dpia`、`eu_tia`、`us_vendor_review`、`us_privacy_review` 的 `production_enabled` 设为 `false`，表示这些模块当前处于开发/实验阶段。

---

## 五、Chunk 构建层 (builders_v2.py)

### 5.1 构建策略

按知识用途差异化切分，分为 5 类 × 3 法域 = 15 个构建函数：

| 构建函数 | 切分粒度 | 特殊处理 |
|---------|---------|---------|
| build_legal_chunks_*() | 按条切 | EU/US 按 source registry 的 modules 展开；含 article_no、citation_anchor |
| build_workflow_chunks_*() | 按判断步骤切 | 每个步骤一个 chunk；含 reference_ids 回查法源；含 scenario_tags |
| build_standard_clause_chunks_*() | 按标准义务切 | 如 BCR 的 enforceable rights / complaint handling / liability allocation |
| build_template_chunks_*() | 按 section/slot 切 | 区分 official_template / example；仅 official_template 可进 structure_control |
| build_testcase_chunks_*() | 按案例切 | 默认不进生产链路 |

### 5.2 关键构建细节

**法规构建**（以 CN 为例）：
- 从 `sources.csv` + 对应的 JSONL 数据文件加载
- 按法条拆分，每一条为一个 chunk
- 填充 reference_ids、keywords、path、doc_type

**工作流规则构建**（以 EU BCR 为例）：
- `WF-EU-BCR-BINDING`：要求先查 binding effect、enforceable rights、liability、complaint handling
- 每个 workflow chunk 通过 `reference_ids` 指向对应的 legal chunk

**标准条款构建**（以 EU BCR 为例）：
- `STD-EU-BCR-RIGHTS`：enforceable rights / complaint handling / liability allocation 等核心义务
- 用于 `StandardClauseLocator + Differ` 的条款对比

---

## 六、索引生成层 (ingest.py)

### 6.1 build_multi_index_v3()

```
build_chunk_sets() → 15 组 KnowledgeChunkV2[]
    │
    ├── 对每组 chunk:
    │   ├── 构建 search_text (title + content + citation_anchor + keywords + ...)
    │   ├── HashingEmbedder.embed(search_text) → BF16 hash 向量
    │   ├── 写入 {name}.vector.json (VectorIndexEntry[] + metadata)
    │   └── 写入 {name}.jsonl (KnowledgeChunkV2 payload 可读格式)
    │
    └── schema_version 检查: MULTI_INDEX_SCHEMA_VERSION 不匹配 → 重建
```

### 6.2 15 个索引

| 法域 | legal | workflow | standard_clause | template | testcase |
|------|-------|----------|-----------------|----------|----------|
| cn | legal_index_cn | workflow_index_cn | standard_clause_index_cn | template_index_cn | testcase_index_cn |
| eu | legal_index_eu | workflow_index_eu | standard_clause_index_eu | template_index_eu | testcase_index_eu |
| us | legal_index_us | workflow_index_us | standard_clause_index_us | template_index_us | testcase_index_us |

---

## 七、检索编排层 (orchestrator.py)

### 7.1 RetrievalOrchestrator 核心逻辑

**`retrieve(request) → RetrievalBundle`** 路由：

```
request.module == "cn_diagnosis"
  → workflow_index_cn (module=cn_diagnosis)
  → legal_index_cn (by workflow reference_ids)
  → UsagePolicy: workflow→internal_review, legal→legal_grounding

request.module == "cn_assessment"
  task_stage=issue_discovery/legal_grounding:
    → workflow_index_cn + legal_index_cn
  task_stage=report_generation:
    → template_index_cn → usage=structure_control
  task_stage=evaluation:
    → testcase_index_cn → usage=evaluator

request.module == "cn_review"
  task_stage=issue_discovery/legal_grounding:
    → workflow_index_cn + legal_index_cn
    → 支持 document_type 过滤
  task_stage=clause_compare:
    → standard_clause_index_cn → usage=legal_grounding
    → legal by reference_ids

request.module ∈ {eu_scc, eu_bcr, eu_dpia, eu_tia}
  → workflow_index_eu (module=request.module)
  → legal_index_eu (module=request.module)
  → issue_discovery 时额外查 standard_clause_index_eu

request.module ∈ {us_eo14117, us_vendor_review, us_privacy_review}
  → 同 eu 模式，查 us_* 索引
```

### 7.2 检索算法

**_search_index() 混合检索 + RRF 融合**：

1. **向量检索**：HashingEmbedder 做 BF16 哈希向量 → cosine 相似度排序
2. **词汇检索**：token overlap 计分（精确子串 +3.0、token 命中 +0.35/个、scenario_tags 匹配 +0.5）
3. **RRF 融合**：`score = 1.0/(60 + rank_vector) + 1.0/(60 + rank_lexical)`
4. **过滤器**：path/doc_type 匹配

**_legal_by_reference_ids()**：
- 从 workflow/standard_clause chunks 的 `reference_ids` 收集法源 ID
- 在对应法域的 legal_index 中精确匹配 source_id/chunk_id

### 7.3 旧检索兼容层 (retriever.py)

**`retrieve_regulations()`** 保留为兼容入口：
- 支持 `mode="hybrid"` / `mode="vector"` / `mode="lexical"`
- EnhancedHybridRetriever：Vector + FTS5 RRF 融合 + HeuristicReranker
- 法域/path/doc_type 过滤器

**`RegulationRAGService`** 保留旧版 RAG 服务接口（向量 + BM25 + heuristic rerank）

---

## 八、Usage Policy 过滤器 (usage_policy.py)

这是分层 RAG 的**硬闸门**，防止不同层知识越界使用。

### 8.1 核心规则矩阵

| Usage | 允许的 Layer | 额外条件 |
|-------|-------------|---------|
| `external_report` | 仅 L1 | can_enter_external_report=True AND can_be_cited=True |
| `legal_grounding` | 仅 L1 | can_be_cited=True AND source_kind ∈ {law_article, official_guide, regulation, standard_clause} |
| `internal_review` | L1 + L2 | production 环境禁 L3 |
| `structure_control` | 仅 L4 | template_type=official_template |
| `internal_drafting` | 仅 L4 | 不限 template_type |
| `few_shot` | 仅 L3 | 仅 dev/eval 环境 |
| `evaluator` | 仅 L3 | 仅 eval 环境 |
| `risk_explanation` | L1 + L2 | 无额外条件 |

### 8.2 全局硬约束

- **法域门**：`chunk.jurisdiction != jurisdiction` → 直接 reject
- **生产环境保护**：`environment=production AND layer=L3_testcase` → reject
- **未知 usage**：回退到 chunk 自身 `allowed_usage` 白名单

---

## 九、业务消费层

### 9.1 Assessment 消费路径

```
AssessmentRetriever.search()
  → orchestrator.retrieve(cn_assessment, legal_grounding)
  → 兼容合并旧 retrieve_regulations()
  → 返回 RegulationHit[] (保持旧接口签名)

service._build_context_pack()
  → 拆分 RetrievalBundle 为:
    ├── legal_grounding_context (仅 L1, 进 build_legal_grounding())
    ├── workflow_rule_context (L1+L2, 进 build_issues())
    ├── template_context (L4, 进 build_generation_basis_pack())
    └── evaluation_context (L3, 仅 eval 模式)

build_legal_grounding()
  → 只接受 can_be_cited=True 的 L1 chunk
  → binding 不是 L1_regulatory_evidence 或 can_be_cited=false → 直接剔除
```

### 9.2 Review 消费路径

```
LocalRegulationKnowledgeBase.lookup(clause_type, clause_text)
  → 法域解析 (_resolve_jurisdiction):
      gdpr/edpb/bcr/scc → eu
      cpra/ccpa/eo14117 → us
      其他 → cn
  → 模块解析 (_resolve_module):
      cn → cn_review
      eu + bcr → eu_bcr
      eu + 补充措施 → eu_tia
      eu + scc/跨境 → eu_scc
      us + eo14117 → us_eo14117
      us + privacy_policy → us_privacy_review
  → 双重检索:
      orchestrator.retrieve(issue_discovery) → workflow_rules + legal_grounding
      orchestrator.retrieve(clause_compare) → standard_clauses
  → 外部API增强: DeliLegal.search_cases() 补充案例引用
  → 缓存: (jurisdiction:module:clause_type, text[:160], enrich)

ClauseReviewer.review()
  → DSL规则检查 (从 rulebook + config)
  → 标准条款比对 (StandardClauseLocator + Differ)
  → 专项审查器 (按文档类型)
  → LLM审查 / 规则兜底
```

---

## 十、评测回归层 (eval.py)

### 10.1 检索评测 (run_retrieval_eval)

**指标**：
| 指标 | 说明 |
|------|------|
| Recall@K | 预期法源在 top-K 结果中的命中率 |
| MRR | 首个预期法源排名的倒数均值 |
| Forbidden-layer retrieval rate | 不该召回的层被召回的比例 |
| Forbidden-source-kind retrieval rate | 不该召回的 source_kind 被召回的比例 |
| Cross-jurisdiction contamination rate | 跨法域污染率 |

**评测流程**：
1. 加载 `retrieval_eval_cases_{cn/eu/us}.jsonl`
2. 对每个 case 构造 RetrievalRequest 并调用 orchestrator.retrieve()
3. 比较 retrieved source_ids vs must_retrieve_source_ids
4. 检查 must_not_retrieve_layers / must_not_retrieve_source_kinds / must_not_retrieve_jurisdictions

### 10.2 生成评测 (run_generation_eval)

**指标**：
| 指标 | 说明 |
|------|------|
| Issue recall | 预期问题在生成结果中的检出率 |
| Citation correctness | 法规引用正确率 |
| Forbidden-source leakage rate | 禁用知识源泄漏率 |
| Unsupported-claim rate | 无依据声明率 |

**评测流程**（分模块）：
- `cn_assessment`：完整运行 AssessmentService.generate_report()，验证 issue 检出和引用绑定
- `cn_review` / `eu_scc` / `eu_bcr` / `us_eo14117` / `us_privacy_review`：构造 ClassifiedClause → 运行 ClauseReviewer.review()，验证 issue 检出和标准条款引用

评测数据按法域拆为 6 个 JSONL 文件：`retrieval_eval_cases_{cn,eu,us}.jsonl` + `generation_eval_cases_{cn,eu,us}.jsonl`

---

## 十一、模块文件结构一览

```
backend/common/
├── knowledge/                         # 知识定义与治理
│   ├── v2.py                          # 核心类型: SourceRegistryEntry, KnowledgeChunkV2,
│   │                                  #   RetrievalRequest, RetrievalBundle, UsageScopedContext
│   ├── registry.py                    # 知识源注册 + 模块目录加载
│   ├── builders_v2.py                 # 15个构建函数 (5类×3法域)
│   ├── usage_policy.py                # UsagePolicyFilter 硬闸门
│   ├── models.py                      # ORM 模型 (KnowledgeDocument, KnowledgeChunk, IngestedFile)
│   ├── chunker.py                     # 通用文档切分器
│   ├── document_parser.py             # 文档解析器
│   ├── ingestion_pipeline.py          # 入库流水线
│   ├── storage_manager.py             # 存储管理
│   ├── chinese_legal_patterns.py      # 中文法规模式
│   └── tests/                         # 测试
├── rag/                               # 检索、索引、编排、评测
│   ├── orchestrator.py                # RetrievalOrchestrator 全模块路由调度
│   ├── ingest.py                      # build_regulation_index() + build_multi_index_v3()
│   ├── retriever.py                   # 旧兼容检索层 + retrieve_regulations()
│   ├── hybrid_retriever.py            # Vector + FTS5 RRF 混合检索
│   ├── reranker.py                    # HeuristicReranker
│   ├── embedding.py                   # HashingEmbedder (BF16 hash)
│   ├── vector_store.py                # LocalVectorStore
│   ├── pgvector_store.py              # PGVector 存储
│   ├── fulltext_index.py              # FTS5 全文索引
│   ├── eval.py                        # 双评测 (retrieval + generation)
│   ├── run_eval.py                    # CLI 入口
│   ├── constants.py                   # MULTI_INDEX_SCHEMA_VERSION
│   └── tests/                         # 测试
├── doc/knowledge/
│   ├── registry/
│   │   ├── source_registry.v1.json    # 知识源注册表
│   │   └── module_catalog.v1.json     # 模块-索引-阶段映射
│   ├── evaluation/
│   │   ├── retrieval_eval_cases_{cn,eu,us}.jsonl   # 检索评测数据
│   │   └── generation_eval_cases_{cn,eu,us}.jsonl  # 生成评测数据
│   └── index/
│       └── sources.csv                # 原始知识源清单
└── storage/rag/v3/
    ├── legal_index_{cn,eu,us}.vector.json + .jsonl
    ├── workflow_index_{cn,eu,us}.vector.json + .jsonl
    ├── standard_clause_index_{cn,eu,us}.vector.json + .jsonl
    ├── template_index_{cn,eu,us}.vector.json + .jsonl
    └── testcase_index_{cn,eu,us}.vector.json + .jsonl
```

---

## 十二、关键设计决策

1. **分层而非分库**：不是简单把 RAG 拆成几个索引名，而是 L1-L4 的分层建模，每个 chunk 天生带 layer + allowed_usage + can_be_cited，后续所有链路都按这些字段做约束

2. **Usage Policy 硬闸门**：不是靠 prompt 约定"不要把测试数据当法条用"，而是代码级过滤——production 下 L3 直接封禁，external_report 只能吃 L1

3. **Stage-based 路由**：不同 task_stage 查不同索引组合。`issue_discovery` 查 workflow + legal，`clause_compare` 查 standard_clause，`report_generation` 查 template

4. **Workflow → Legal 回查**：workflow 规则不直接当法规引用，而是通过 `reference_ids` 回查对应的 legal chunk，确保正式引用始终来自 L1

5. **兼容层设计**：新主路径由 orchestrator 接管，但旧 `retrieve_regulations()` 接口保留，assessment 模块先在 orchestrator 检索后再兼容合并旧结果

6. **双评测闭环**：不仅评测"能不能检到"（retrieval eval），还评测"生成结果有没有乱用知识"（generation eval：禁止源泄漏率、无依据声明率、跨法域污染率）
