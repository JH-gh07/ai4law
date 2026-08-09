# DataComplyFlow 知识库索引修复方案

> **版本**: v1.0 → **v1.1 (状态: ✅ 已完成 - 2026-08-10)**
> **状态**: 已执行完毕，所有 8 项检查全部通过
> **日期**: 2026-08-10
> **范围**: `storage/rag/v3/` 三层法域（CN/EU/US）全部 15 个子索引
> **前置审查**: `tmp_review_audit_20260809.md` 第十五部分（知识库索引审查）
> **状态**: 待执行

---

## 一、问题总览

经过对 `storage/rag/v3/` 下全部 15 个子索引的逐条目审查，与 `resources/legal/` 下原始数据源（`sources.csv`、`regulation_articles.jsonl`、`source_registry.v1.json`）的全链路追踪，以及与 `backend/common/rag/orchestrator.py` 检索管线的模块级对照，共发现 **10 个问题**。按严重度分级：

| 优先级 | 数量 | 修复窗口 |
|:---:|:---:|------|
| 🔴 P0 | 4 | 本周 |
| 🟡 P1 | 6 | 本月 |

---

## 二、四个 P0 问题详析

### P0-1：EU 索引 93.5% 条目为噪音（839/897）

**现状**：

```
EU legal_index 总条目：897
├── EU-LAW-001 (GDPR)                  52 chunks  (仅覆盖约13个条款)
├── EU-GUIDE-002 (EDPB 01/2020)         6 chunks  (仅 Step 1, Step 3)
└── 噪音层:
    ├── 18 份 CELEX 充分性认定决定       540 chunks  (每份直切30段, article_no = "段落1"~"段落30")
    ├── 4 份 JUST SCC 模板草案           120 chunks  (每份30段)
    ├── 5 份 EDPB Guidelines (2018)     150 chunks  (每份30段)
    ├── 1 份 ICO DPIA Template           29 chunks  (段落1~29)
    └── 1 份 TIA Template                30 chunks  (段落1~30)
```

模块级分配（实际索引数据）：

```
eu_scc:  854 chunks  ← 严重噪音（28份SUP/TPL 各30段 + 13 GDPR + 2 EDPB）
eu_bcr:   15 chunks  ← 仅 13 GDPR + 2 EDPB
eu_dpia:  13 chunks  ← 仅 13 GDPR（无EDPB）
eu_tia:   15 chunks  ← 13 GDPR + 2 EDPB（无EDPB）
```

**根因追踪**（全链路，按数据流顺序）：

1. **数据源头** (`resources/legal/catalog/sources.csv`):
   28 条 `EU-SUP-*`/`EU-TPL-*` 记录，
   `module` 列全部硬编码为 `eu-scc`，
   `authority_level` 全部为 `medium`，
   `binding_force` 全部为 `recommended`

2. **Registry 生成** (`backend/common/knowledge/registry.py:207-209`):
   ```python
   if row.get("module"):
       modules = [item.strip().replace("-", "_") for item in row["module"].split("|") if item.strip()]
   ```
   `module=eu-scc` → `["eu_scc"]`，不走 path 自动推断机制。
   如果去掉 `module` 列，`path=all` 会触发 `_modules_for_row()` 的四个分支，
   生成 `["eu_scc", "eu_bcr", "eu_dpia", "eu_tia"]`，
   反而会让噪音扩散到全部 4 个 EU 模块。

3. **Chunk 构建** (`backend/common/knowledge/builders_v2.py:568-572`):
   ```python
   modules = [
       item for item in (registry_entry.modules if registry_entry is not None else [])
       if str(item).startswith("eu_")
   ] or ["eu_scc"]
   ```
   对 28 条噪音记录，`modules=["eu_scc"]`，对每个 module 生成一份 chunk 副本。
   生成了 839 个噪音 chunk（28 条 source × 30 段 = 840，ICO 是 29 段）。

4. **检索放大** (`backend/common/rag/orchestrator.py:297-303`):
   ```python
   legal = self._search_index(
       "legal_index_eu",
       request.query,
       top_k=request.top_k,
       filters={"module": request.module},  # eu_scc → 854 chunks 池
   )
   ```
   `eu_scc` 的法规检索池有 854 chunks，其中 839 条（98.2%）是噪音。
   混合检索（向量 + 词汇）时，CELEX 充分性决定文本、EDPB 指南、
   JUST 模板草案等与 GDPR/EDPB 01/2020 同等竞争排名。

5. **UsagePolicy 未拦截** (`backend/common/knowledge/usage_policy.py:67-70`):
   ```python
   if usage == "legal_grounding":
       return (
           chunk.layer == "L1_regulatory_evidence"
           and chunk.can_be_cited
           and chunk.source_kind in {"law_article", "official_guide", "regulation", "standard_clause"}
       )
   ```
   噪音条目 `source_kind="regulation"`、`can_be_cited=True`，
   完全通过 `legal_grounding` 使用策略过滤器。

**影响量化**：
- `eu_scc` 检索池信噪比 ≈ 1:57（15 有效 : 839 噪音）
- `eu_bcr` 检索池仅 15 chunks，无法支撑 BCR 审查
- `eu_dpia` 检索池仅 13 chunks，完全无法支撑 DPIA 全文
  （需 GDPR Art 5-9, 12-22, 24-25, 28, 30, 32-36, 44-49 等）
- `eu_tia` 检索池仅 15 chunks，TIA 六步法无法律索引支撑
  （需 EDPB 01/2020 Step 1-6 全流程 + GDPR Art 5-9, 44-49）

### P0-2：US CPRA 索引仅 12 chunks，无法支撑全景合规检查

**现状**：

```
US legal_index 总条目：299
├── us_14117: 287 chunks
│   ├── US-FED-001 (28 CFR Part 202)           17 chunks
│   └── US-SUP-006~014 (NIST/FISA/CLOUD等)     270 chunks  (9份×30段, 全部盲切)
└── us_cpra: 12 chunks
    └── US-CA-001 (CCPA/CPRA)                   12 chunks
```

**根因追踪**：

1. **数据源头** (`sources.csv`):
   - `US-CA-001` 的 `module=us-cpra`, `path=privacy`
   - 9 条 `US-SUP-*` 全部 `module=us-14117`, `path=all`

2. **原始数据严重不足**: `regulation_articles.jsonl` 中 `US-CA-001`
   仅 12 条记录，article_ref 覆盖 §1798.100~§1798.199 中的 12 个条款号，
   但 CPRA 修正案实际涉及 30+ 条款

3. **Module 分配** (`builders_v2.py` line 945-948):
   ```python
   modules = [
       item for item in (registry_entry.modules if registry_entry is not None else [])
       if str(item).startswith("us_")
   ] or ["us_vendor_review"]
   ```
   `US-CA-001` 仅 `us_cpra` 一个 module。
   注意 `us_vendor_review` 也需要 CPRA 依据（vendor agreement
   的隐私合规审查必须以 CPRA 为基准），但索引中没有分配到该模块。

4. **检索池**: `us_cpra` 仅 12 chunks → 任何检索查询几乎必然返回空
   或仅返回不完整的几条（© 当前实际运行中 `regulations=0`）

**影响量化**：
- CPRA 模块需要全景检查 10 个 domain：
  notice, consent, rights (know/delete/correct/opt-out/limit),
  sensitive PI, data minimization, security, vendor management,
  service provider, enforcement
- 仅 12 个文本片段完全不够
- `us_vendor_review` 检索池的 legal_grounding 依赖
  `filter={"module": "us_vendor_review"}`，
  但该 module 在 legal_index 中无任何条目 → 检索池为空

### P0-3：GDPR 覆盖严重不足（仅 52 chunks，应覆盖 99 条）

**现状**：

`regulation_articles.jsonl` 中 `EU-LAW-001` 的 article_ref
仅覆盖以下条款号：
`5, 6, 9, 12, 13, 14, 15, 24, 25, 26, 28, 30, 32, 35, 36, 37,
38, 39, 44, 45, 46, 47, 48, 49`
→ 共 24 个条款号，占比 24/99 = **24.2%**

在 v3 索引中，这 24 个条款被分配为：
```
EU-LAW-001 的 52 chunks = 13条独立条款 × 4 modules (eu_scc/bcr/dpia/tia)
```
所以实际独立条款仅 13 条（另外 11 条仅有 1-2 个 module 的副本）。

**缺失的关键条款**（按模块需求分组）：

| 条款 | 所需模块 | 内容 | 重要性 |
|------|:---:|------|:---:|
| Art 7 | dpia, tia | Conditions for consent | 🔴 必需 |
| Art 8 | dpia | Child consent in information society services | 🟡 重要 |
| Art 16 | 全部 | Right to rectification | 🔴 必需 |
| Art 17 | 全部 | Right to erasure ("right to be forgotten") | 🔴 必需 |
| Art 18 | 全部 | Right to restriction of processing | 🟡 重要 |
| Art 19 | 全部 | Notification obligation regarding rectification/erasure | 🟡 重要 |
| Art 20 | 全部 | Right to data portability | 🔴 必需 |
| Art 21 | dpia | Right to object | 🔴 必需 |
| Art 22 | dpia | Automated individual decision-making | 🔴 必需 |
| Art 23 | dpia | Restrictions (EU/Member State law) | 🟡 重要 |
| Art 27 | bcr | Representatives of controllers not in Union | 🟡 重要 |
| Art 28(3) | scc | Processor contract requirements | 🔴 必需 |
| Art 29 | scc, bcr | Processing under authority | 🟡 重要 |
| Art 31 | dpia | Cooperation with supervisory authority | 🟡 重要 |
| Art 32 | dpia, scc | Security of processing | 🔴 必需 |
| Art 33 | dpia | Notification of personal data breach to SA | 🔴 必需 |
| Art 34 | dpia | Communication of data breach to data subject | 🔴 必需 |
| Art 35(1-11) | dpia | DPIA — 完整条款分(1)~(11)段 | 🔴 必需 |
| Art 36 | dpia | Prior consultation | 🔴 必需 |
| Art 44 | tia, bcr | General principle for transfers | 🔴 必需 |
| Art 45 | tia | Transfers on basis of adequacy decision | 🔴 必需 |
| Art 46(1-5) | tia, scc | Appropriate safeguards | 🔴 必需 |
| Art 47 | bcr | Binding corporate rules | 🔴 必需 |
| Art 48 | tia | Transfers not authorised by EU law | 🟡 重要 |
| Art 49 | tia | Derogations for specific situations | 🔴 必需 |
| Art 50 | tia | International cooperation | 🟡 重要 |

### P0-4：引用利用率极低（检索→引用→脚注 端到端链路断裂）

**现状**（来自审计报告 15.5 部分）：

| 模块 | 检索命中 | 引用注册 | 脚注映射 | 利用率 |
|------|:---:|:---:|:---:|:---:|
| assessment | 98 | 10 | 0 | 0% |
| pipia | 0 | 89 | 22 | 24.7% |
| dpia | 4 | 0 | 0 | 0% |
| eu_scc | 0 | 3 | 3 | 100% |
| bcr | 0 | 2 | 2 | 100% |
| us_14117 | 0 | 0 | 0 | — |
| cpra | 0 | 3 | 0 | 0% |
| tia | 0 | 1 | 1 | 100% |

**根因**：
1. **检索未触发**（6/8 模块）：大部分模块通过 pre-built citation_map
   预注册引用，不走 RAG 实时检索
2. **脚注格式不兼容**（审计第十二部分）：
   `apply_citation_pipeline()` 只识别 `{{CIT-xxx}}`，LLM 写 `[N]`
3. **检索池噪音导致返回不相关结果**：
   assessment 检索 98 条中 74.5%（73 条）是同一部法律（个人信息保护法），
   检索成本完全浪费

---

## 三、六个 P1 问题详析

### P1-1：CN 索引 53.7% chunks < 100 字符，缺上下文

**逐源分析**：

| 来源 | chunks | avg_len | <100字符 | 比例 | 根因 |
|------|:---:|:---:|:---:|:---:|------|
| CN-SUP-004 个人信息安全规范 | 30 | 79 | 30 | 100% | 技术标准条文极短（单句独立） |
| CN-SUP-007 金融数据分级指南 | 30 | 59 | 30 | 100% | 同上 |
| CN-SUP-005 申报系统使用手册 | 11 | 48 | 11 | 100% | 操作步骤单句 |
| CN-OPS-014 联系方式 | 6 | 57 | 6 | 100% | 纯列表条目 |
| CN-SUP-003 金融信息保护规范 | 30 | 86 | 19 | 63% | 技术标准条文极短 |
| CN-QA-011 答记者问 | 19 | 97 | 13 | 68% | QA 格式 — 问答分离 |
| CN-LAW-002 数据安全法 | 54 | 106 | 34 | 63% | 法律条文本身就短（1-2句/条） |
| CN-GUIDE-009 申报指南 | 8 | 82 | 5 | 62% | 列表项独立条目 |
| CN-REG-006 跨境流动规定 | 11 | 120 | 7 | 64% | 同上 |
| CN-GOV-015 政府网转载 | 13 | 176 | 7 | 54% | 同上 |

**影响**：
- 向量检索时，孤立句子缺少上下文，检索打分偏低
- LLM 引用时只有一句话无上下文，容易误读法律含义
- 同一法律条文被切成多个独立 chunk，检索时可能同时命中 3-4 个碎片
  但都不是完整条款

### P1-2：CN 索引 pipia 模块无独立 partition

**现状**：

`module_catalog.v1.json` 中没有 `cn_pipia` 模块定义。
`sources.csv` 中也没有 `module=cn-pipia` 的源。

CN 模块分配逻辑 (`build_legal_chunks_cn()` line 80-83):
```python
module = "cn_diagnosis"
if "cn_assessment" in modules:
    module = "cn_assessment"
elif "cn_review" in modules:
    module = "cn_review"
# 无 cn_pipia 分支
```

pipia 在运行时使用的是 `template_index_cn` 中的模板
（可能与 assessment 共用），但其法规 legal_grounding 检索走的是
cn_assessment 的 44 条子集或跨模块检索。
实际运行中 pipia 检索到的 `regulations=0`（result.json 中法规数为 0）。

### P1-3：CN assessment partition 过小（仅 44 chunks）

**现状**：

```
cn_assessment: 44 chunks
├── CN-REG-004      20  (数据出境安全评估办法)
├── CN-GUIDE-009     8  (申报指南第三版)
├── CN-OPS-014       6  (联系方式)
├── CN-QA-012        3  (政策问答 4月)
├── CN-QA-013        3  (政策问答 5月)
├── CN-TPL-019       3  (自评估报告模板)
└── CN-TPL-020       1  (PIPIA模板)
```

assessment 需要覆盖完整的 8 章评估报告，
涉及《网络安全法》《数据安全法》《个人信息保护法》
《网络数据安全管理条例》《数据出境安全评估办法》
至少 5 部主要法律，44 个碎片远远不够。

### P1-4：US 索引 90.3% 条目为盲切噪音（270/299）

**现状**：

```
us_14117: 287 chunks
├── US-FED-001 (DOJ Rule 28 CFR Part 202)    17 chunks
└── US-SUP-006~014                            270 chunks
    ├── US-SUP-006  数字贸易 (USMCA)
    ├── US-SUP-007  EO 14086 增强DPF
    ├── US-SUP-008  APEC Privacy Framework
    ├── US-SUP-009  DCPD 202200894
    ├── US-SUP-010  FISA Section 702
    ├── US-SUP-011  EU-U.S. DPF Full Text
    ├── US-SUP-012  NIST Privacy Framework
    ├── US-SUP-013  CLOUD Act
    └── US-SUP-014  FTC Act
```

与 P0-1（EU噪音）性质相同但严重度略低：
us_14117 模块本身不需要 NIST/FISA/CLOUD/APEC/FTC 等文本，
它们是通用美国法规参考，对 EO 14117 prohibited/restricted
transaction 判定无直接帮助。
但这些条目全部被标记为 `module=us-14117`，在 us_14117 检索池中
构成 270/287 ≈ 94% 的噪音。

### P1-5：CN 检索偏置严重（assessment 中 74.5% 命中同一部法律）

**现状**（来自实际运行日志）：

assessment 模块的检索结果：
- 总命中：98 条
- 来自《个人信息保护法》：73 条（74.5%）
- 来自其他 10 部法律：各 1 条

**根因**：

1. **向量偏置**：《个人信息保护法》的 73 个 chunks 的 embedding
   与"数据出境安全评估"查询在向量空间中距离更近
   （因为该法包含最多的数据出境相关条款）
2. **混合检索未做 source diversity 重排**：
   `_search_index()` 中 vector_hits 和 lexical_hits 按分数合并后
   直接取 top_k（默认 8），没有 `dedupe_by_source()` 或 MMR
   (Maximal Marginal Relevance) 重排
3. **top_k=8 太小**：在 549 的 CN 总池子中取 top_k=8，
   且无 source cap 机制，极易全部落入单一法律

### P1-6：retriever 无 source diversity 机制

**代码证据** (`orchestrator.py:520-529`):

```python
ordered = sorted(merged_scores.items(), key=lambda item: item[1], reverse=True)
results = []
for doc_id, _ in ordered:
    chunk = _payload_to_chunk(payloads[doc_id])
    if not self._match_filters(chunk, filters or {}):
        continue
    results.append(chunk)
    if len(results) >= top_k:
        break
return results
```

**缺少的功能**：
1. `dedupe_by_source()` — 同一个 source 最多取 N 条
2. MMR 重排 — λ × 相似度 − (1-λ) × 与已选结果的相似度
3. Source coverage 强制 —
   如果 query 涉及"数据出境 + 安全评估 + 标准合同"三个维度，
   应强制至少覆盖 3 个不同的 source

---

## 四、修复方案（逐项、可验证）

### 修复 P0-1：EU 索引去噪

#### Step 1.1：修改 sources.csv — 噪音源标记为 reference

**文件**: `resources/legal/catalog/sources.csv`

**操作**: 修改以下 28 条记录的 `path` 列从 `all` 改为 `reference`：

```
EU-SUP-009,  ICO DPIA Template,           path: all → reference
EU-SUP-010,  CELEX 32002D0002,            path: all → reference
EU-SUP-011,  CELEX 32003D0490,            path: all → reference
EU-SUP-012,  CELEX 32003D0821,            path: all → reference
EU-SUP-013,  CELEX 32004D0411,            path: all → reference
EU-SUP-014,  CELEX 32008D0393,            path: all → reference
EU-SUP-015,  CELEX 32010D0146,            path: all → reference
EU-SUP-016,  CELEX 32010D0625,            path: all → reference
EU-SUP-017,  CELEX 32011D0061,            path: all → reference
EU-SUP-018,  CELEX 32012D0484,            path: all → reference
EU-SUP-019,  CELEX 32013D0065,            path: all → reference
EU-SUP-020,  CELEX 32019D0419,            path: all → reference
EU-SUP-021,  CELEX 32021D0914,            path: all → reference
EU-SUP-022,  CELEX 32021D1772,            path: all → reference
EU-SUP-023,  CELEX 32022D0254,            path: all → reference
EU-SUP-024,  CELEX 32023D1795,            path: all → reference
EU-SUP-025,  CELEX 62018CJ0311,           path: all → reference
EU-SUP-026,  EN Standard Contractual Clauses, path: all → reference
EU-SUP-027,  EPO Adequacy Decision Jul 2025,  path: all → reference
EU-TPL-001,  JUST template standard 2,    path: all → reference
EU-TPL-002,  JUST template standard 26,   path: all → reference
EU-TPL-003,  JUST template standard 27,   path: all → reference
EU-TPL-004,  TIA Template,                path: all → reference
EU-SUP-028,  EDPB guidelines derogations,  path: all → reference
EU-SUP-029,  EDPB guidelines territorial,  path: all → reference
EU-SUP-030,  EDPB guidelines codes conduct, path: all → reference
EU-SUP-031,  EDPB recommendations bcr v2,  path: all → reference
EU-SUP-032,  EDPB recommendations bcr,     path: all → reference
```

**同时修改这些行的 `module` 列为空**，防止被 `registry.py:208` 的硬编码覆盖。

#### Step 1.2：修改 Registry — 支持 reference path 返回空 modules

**文件**: `backend/common/knowledge/registry.py`, `_modules_for_row()` 函数

在 EU 分支开头添加：
```python
if jurisdiction == "eu":
    if path == "reference":
        return []  # 参考源不加入任何模块的检索池
    modules = []
    ...
```

在 US 分支开头添加：
```python
if jurisdiction == "us":
    if path == "reference":
        return []
    modules = []
    ...
```

#### Step 1.3：修改 Builder — 跳过 modules 为空的 source

**文件**: `backend/common/knowledge/builders_v2.py`

**EU builder** (line 568-572) 修改为：
```python
# 修改前:
modules = [
    item for item in (registry_entry.modules if registry_entry is not None else [])
    if str(item).startswith("eu_")
] or ["eu_scc"]

# 修改后:
modules = [
    item for item in (registry_entry.modules if registry_entry is not None else [])
    if str(item).startswith("eu_")
]
if not modules:
    continue  # reference-only source, skip
```

**US builder** (line 945-948) 同样修改：
```python
# 修改前:
modules = [
    item for item in (registry_entry.modules if registry_entry is not None else [])
    if str(item).startswith("us_")
] or ["us_vendor_review"]

# 修改后:
modules = [
    item for item in (registry_entry.modules if registry_entry is not None else [])
    if str(item).startswith("us_")
]
if not modules:
    continue  # reference-only source, skip
```

#### Step 1.4：重建索引

```bash
python -c "
from backend.core.settings import get_settings
from backend.common.rag.ingest import build_multi_index_v3
settings = get_settings()
result = build_multi_index_v3(settings)
print('Indexes rebuilt:', list(result.keys()))
"
```

#### 验证命令

```bash
python3 -c "
import json
# 验证 EU 索引模块分布
by_module = {}
with open('storage/rag/v3/legal_index_eu.jsonl') as f:
    for line in f:
        row = json.loads(line.strip())
        mod = row.get('module','?')
        by_module[mod] = by_module.get(mod, 0) + 1
for mod in sorted(by_module):
    print(f'{mod}: {by_module[mod]}')

# 验证盲切比例
total = sum(by_module.values())
para = 0
with open('storage/rag/v3/legal_index_eu.jsonl') as f:
    for line in f:
        row = json.loads(line.strip())
        if row.get('article_no','').startswith('段落'):
            para += 1
print(f'Blind-split: {para}/{total} ({100*para/total:.1f}%)')
print(f'Target: {para} = 0')
"
```

**预期输出**：
```
eu_bcr:  15
eu_dpia: 13
eu_scc:  15
eu_tia:  15
Blind-split: 0/58 (0.0%)
```

---

### 修复 P0-2：补全 US CPRA 索引

#### Step 2.1：扩展 regulation_articles.jsonl 中 US-CA-001 的条目

**文件**: `resources/legal/registry/regulation_articles.jsonl`

**目标**: 从当前 12 条扩展到至少 **80 条**，覆盖 CPRA 核心条款。

需添加的条目（按优先级分组）：

**P0 优先级（必须覆盖）**：

| article_ref | 内容简述 | 条目数 |
|------|------|:---:|
| §1798.100 | General duties of businesses (notice) | 2 |
| §1798.105 | Right to delete | 2 |
| §1798.106 | Right to correct | 2 |
| §1798.110 | Right to know (categories collected) | 2 |
| §1798.115 | Right to know (categories sold/shared) | 2 |
| §1798.120 | Right to opt-out of sale/sharing | 2 |
| §1798.121 | Right to limit sensitive PI | 2 |
| §1798.125 | Non-discrimination | 1 |
| §1798.130 | Business obligations for requests | 2 |
| §1798.135 | Business obligations for opt-out | 2 |
| §1798.140 | Definitions (分段: (a)-(w)各1条) | 18 |
| §1798.145 | Waiver/preemption | 2 |
| §1798.150 | Private right of action | 2 |
| §1798.155 | CPPA enforcement | 1 |
| §1798.175 | CPPA rulemaking authority | 1 |
| §1798.185 | Required rulemaking areas | 2 |
| §1798.199.10-40 | Data minimization, purpose limitation | 5 |
| §1798.199.50-100 | Profiling, risk assessments, vendor | 8 |

**共约 56 条**

**P1 优先级（建议覆盖）**：

| article_ref | 内容简述 | 条目数 |
|------|------|:---:|
| §1798.100(b)-(d) | Additional notice details | 3 |
| §1798.105(b)-(d) | Delete request procedures | 3 |
| §1798.110(b)-(d) | Know request categories | 3 |
| §1798.115(b)-(d) | Know request sold/shared | 3 |
| §1798.120(b)-(c) | Opt-out procedures | 2 |
| §1798.121(b)-(c) | Limit SPI procedures | 2 |
| §1798.130(a)-(e) | Response procedures | 5 |
| §1798.140(a)-(w) | 详细定义 (扩展) | 5 |

**共约 26 条**

**article_id 命名规范**：
```
US-CA-001-001 → article_ref=§1798.100(a)
US-CA-001-002 → article_ref=§1798.100(b)
...
US-CA-001-020 → article_ref=§1798.140(b)  (definition: "business")
...
```

**数据来源**：
- 官方 CCPA 文本：https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?division=3.&part=4.&lawCode=CIV&title=1.81.5
- 或使用 `resources/legal/registry/regulation_articles.jsonl` 中已有的 12 条作为模板，补充缺失条款
- 每条的 `content` 字段应为完整条款原文（英文），`law_name` 为 "California Civil Code — CCPA/CPRA"

#### Step 2.2：确保 CPRA 同时分配给 us_vendor_review

**方案A**（推荐，改动最小）— 修改 sources.csv：

```
US-CA-001 的 module 列从 "us-cpra" 改为 "us-cpra|us-vendor-review"
```

**方案B**（更彻底）— 修改 builder 对特定 source 做强制多模块分配：

在 `build_legal_chunks_us()` 中，对 `source_id == "US-CA-001"` 的条目：
```python
if source_id == "US-CA-001":
    modules = list(set(modules) | {"us_vendor_review"})
```

#### 验证命令

```bash
python3 -c "
import json
by_module = {}
articles = set()
with open('storage/rag/v3/legal_index_us.jsonl') as f:
    for line in f:
        row = json.loads(line.strip())
        mod = row.get('module','?')
        by_module[mod] = by_module.get(mod, 0) + 1
        if row['source_id'] == 'US-CA-001':
            articles.add(row.get('article_no',''))

print('Module distribution:')
for mod in sorted(by_module):
    print(f'  {mod}: {by_module[mod]}')
print(f'CPRA unique articles: {len(articles)}')
print('Target: us_cpra >= 80, us_vendor_review CPRA entries >= 80')
"
```

**预期输出**：
```
us_14117: 17 (仅 US-FED-001，噪音已去)
us_cpra: >=80
us_vendor_review: >=80 (与 us_cpra 共享)
CPRA unique articles: >=50
```

---

### 修复 P0-3：补全 GDPR 索引

#### Step 3.1：扩展 regulation_articles.jsonl 中 EU-LAW-001 的条目

**文件**: `resources/legal/registry/regulation_articles.jsonl`

**目标**: 从当前 24 条独立条款扩展到 **≥80 条独立条款**。

需添加的条款（分优先级）：

**🔴 P0 必需（各模块的核心法律基础）**：

| 条款 | article_id 示例 | 需分几段 | 所需模块 |
|------|------|:---:|:---:|
| Art 7 | EU-LAW-001-007 | 1 | dpia, tia |
| Art 16 | EU-LAW-001-016 | 1 | 全部 |
| Art 17 | EU-LAW-001-017 | 1 | 全部 |
| Art 20 | EU-LAW-001-020 | 1 | 全部 |
| Art 21 | EU-LAW-001-021 | 1 | dpia |
| Art 22 | EU-LAW-001-022 | 1 | dpia |
| Art 28(3) | EU-LAW-001-028-03 | 1 | scc |
| Art 32 | EU-LAW-001-032 | 1 | dpia, scc |
| Art 33 | EU-LAW-001-033 | 1 | dpia |
| Art 34 | EU-LAW-001-034 | 1 | dpia |
| Art 35(1)-(11) | EU-LAW-001-035-01 ~ 035-11 | 11 | dpia |
| Art 36 | EU-LAW-001-036 | 1 | dpia |
| Art 44 | EU-LAW-001-044 | 1 | tia, bcr |
| Art 45 | EU-LAW-001-045 | 1 | tia |
| Art 46(1)-(5) | EU-LAW-001-046-01 ~ 046-05 | 5 | tia, scc |
| Art 47 | EU-LAW-001-047 | 1 | bcr |
| Art 49 | EU-LAW-001-049 | 1 | tia |

**共约 33 段**

**🟡 P1 重要（提升覆盖完整性）**：

| 条款 | article_id 示例 | 需分几段 |
|------|------|:---:|
| Art 8 | EU-LAW-001-008 | 1 |
| Art 18 | EU-LAW-001-018 | 1 |
| Art 19 | EU-LAW-001-019 | 1 |
| Art 23 | EU-LAW-001-023 | 1 |
| Art 27 | EU-LAW-001-027 | 1 |
| Art 29 | EU-LAW-001-029 | 1 |
| Art 31 | EU-LAW-001-031 | 1 |
| Art 48 | EU-LAW-001-048 | 1 |
| Art 50 | EU-LAW-001-050 | 1 |

**共约 9 段**

每条 JSONL 记录格式（参考现有 GDPR 条目）：

```json
{
  "article_id": "EU-LAW-001-035-01",
  "source_id": "EU-LAW-001",
  "law_name": "GDPR (EU) 2016/679",
  "article_ref": "Art 35(1)",
  "content": "Where a type of processing in particular using new technologies, and taking into account the nature, scope, context and purposes of the processing, is likely to result in a high risk to the rights and freedoms of natural persons, the controller shall, prior to the processing, carry out an assessment of the impact of the envisaged processing operations on the protection of personal data. ...",
  "status": "effective",
  "publish_date": "2016-04-27",
  "effective_date": "2018-05-25",
  "jurisdiction": "eu",
  "path": "all",
  "doc_type": "law",
  "source_url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
  "snapshot_path": "storage/raw/eu/gdpr_2016_679.txt",
  "keywords": ["GDPR", "data protection", "impact assessment", "high risk"]
}
```

**数据来源**：
- 官方 GDPR 英文版全文：https://eur-lex.europa.eu/eli/reg/2016/679/oj
- 或者使用 https://gdpr-info.eu/ 的条款级全文（已有结构化分条）
- 或者使用 `resources/legal/registry/regulation_articles.jsonl` 中已有的 24 条
  作为格式模板

#### 验证命令

```bash
python3 -c "
import json
articles = set()
with open('storage/rag/v3/legal_index_eu.jsonl') as f:
    for line in f:
        row = json.loads(line.strip())
        if row['source_id'] == 'EU-LAW-001':
            articles.add(row.get('article_no',''))

def art_sort_key(a):
    # Extract the first number from article_no for sorting
    import re
    nums = re.findall(r'\d+', a)
    return int(nums[0]) if nums else 0

sorted_arts = sorted(articles, key=art_sort_key)
print(f'GDPR unique articles: {len(sorted_arts)}')
print('Articles covered:', sorted_arts[:10], '...')
print('Target: >=80')
"
```

**预期输出**: `GDPR unique articles: >=80`

---

### 修复 P0-4：贯通检索→引用→脚注链路

#### Step 4.1：修复 citation pipeline 的 `[N]` 格式兼容

**此修复已在审计报告第十二部分详述**，不在本方案中重复展开。
关键修改点：

**文件**: `backend/common/llm/postprocess.py`

- `_replace_registered_markers()` 当前仅匹配 `{{CIT-xxx}}` 正则，
  需扩展为同时匹配 `[N]` 格式（数字脚注）
- `assign_footnote_number()` 需在 DocumentIR 路径下被触发

详见 `tmp_review_audit_20260809.md` 第 12.1-12.4 节。

#### Step 4.2：检索后自动去重

**文件**: `backend/common/rag/orchestrator.py`, `_search_index()` 方法

在当前返回 `results` 之前添加：
```python
# 确保每个 source_id 最多 source_cap 条
results = self.dedupe_by_source(results)
# 再截断到 top_k
results = results[:top_k]
```

`dedupe_by_source` 是已有静态方法（line 576-585），无需新增代码。

#### 验证标准

回归测试：
```bash
pytest backend/common/llm/tests/test_citation_pipeline.py
pytest backend/common/rag/tests/test_multi_index_orchestrator.py
```

---

### 修复 P1-1：CN 短 chunk 合并

#### Step 5.1：在 build_legal_chunks_cn() 中添加合并逻辑

**文件**: `backend/common/knowledge/builders_v2.py`

在 `build_legal_chunks_cn()` 函数的 `for line in handle` 循环中，
对从 `regulation_articles.jsonl` 读取的 rows 先做预处理。

添加合并函数：

```python
def _merge_short_chunks(
    rows: list[dict], min_len: int = 120
) -> list[dict]:
    """合并同一 source 下连续过短的 chunk。

    规则：
    1. 仅合并同一 source_id 下的连续条目
    2. 连续 2-3 个 < min_len 的条目合并为 1 个（用双换行分隔）
    3. 合并后的 article_ref 用逗号连接
    4. 合并后的 article_id 取第一个条目的 id
    """
    if not rows:
        return []

    merged: list[dict] = []
    buffer: dict | None = None

    for row in rows:
        content = str(row.get("content", ""))
        if len(content) < min_len:
            if buffer is None:
                buffer = dict(row)
                continue
            # 合并到 buffer
            buffer["content"] = (
                str(buffer.get("content", ""))
                + "\n\n"
                + content
            )
            buffer["article_ref"] = (
                str(buffer.get("article_ref", ""))
                + ", "
                + str(row.get("article_ref", ""))
            )
            # 如果合并后已足够长，flush
            if len(str(buffer.get("content", ""))) >= min_len:
                merged.append(buffer)
                buffer = None
        else:
            if buffer is not None:
                merged.append(buffer)
                buffer = None
            merged.append(row)

    if buffer is not None:
        merged.append(buffer)

    return merged
```

在 `build_legal_chunks_cn()` 中，按 `source_id` 分组后对每组调用：

```python
def build_legal_chunks_cn() -> list[KnowledgeChunkV2]:
    ...
    with NORMALIZED_JSONL.open("r", encoding="utf-8") as handle:
        raw_rows: list[dict] = []
        for line in handle:
            ...
            raw_rows.append(row)

    # 按 source_id 分组做短 chunk 合并
    from itertools import groupby
    raw_rows.sort(key=lambda r: (r.get("source_id", ""), r.get("article_id", "")))
    merged_rows: list[dict] = []
    for _, group in groupby(raw_rows, key=lambda r: r.get("source_id", "")):
        source_rows = list(group)
        merged_rows.extend(_merge_short_chunks(source_rows, min_len=120))

    # 然后用 merged_rows 继续构建 KnowledgeChunkV2...
```

**注意**：原始 `regulation_articles.jsonl` 不变。合并逻辑仅在 Builder 层面执行。

#### 验证命令

```bash
python3 -c "
import json
short = 0
total = 0
by_source_short = {}
with open('storage/rag/v3/legal_index_cn.jsonl') as f:
    for line in f:
        row = json.loads(line.strip())
        total += 1
        content_len = len(row.get('content',''))
        if content_len < 100:
            short += 1
        src = row.get('source_id','')
        if content_len < 100:
            by_source_short[src] = by_source_short.get(src, 0) + 1

print(f'Short chunks: {short}/{total} ({100*short/total:.1f}%)')
print(f'Target: <30%')
print()
print('Sources with most short chunks:')
for src, cnt in sorted(by_source_short.items(), key=lambda x: -x[1])[:5]:
    print(f'  {src}: {cnt}')
"
```

**预期输出**: Short chunks ratio 从 53.7% 降至 <30%

---

### 修复 P1-2：新增 pipia 独立 partition

#### Step 6.1：添加 pipia 模块定义

**文件**: `resources/legal/catalog/module_catalog.v1.json`

在 `modules` 字典中添加：
```json
"cn_pipia": {
    "indexes": ["workflow_index_cn", "legal_index_cn", "template_index_cn", "testcase_index_cn"],
    "stages": ["issue_discovery", "legal_grounding", "report_generation", "evaluation"],
    "default_usage_scopes": ["internal_review", "legal_grounding", "structure_control"],
    "jurisdiction": "cn",
    "production_enabled": true,
    "requires_standard_clause_index": false,
    "template_policy": "official_only"
}
```

#### Step 6.2：在 sources.csv 中标记 pipia 相关 source

**文件**: `resources/legal/catalog/sources.csv`

为以下 source 的 `module` 列补充 `cn-pipia`：

```
CN-LAW-003   module 从 "cn-diagnosis" 改为 "cn-diagnosis|cn-pipia"
CN-REG-004   module 从 "cn-assessment" 改为 "cn-assessment|cn-pipia"
CN-TPL-020   module 从 "cn-assessment" 改为 "cn-pipia"
```

#### Step 6.3：修改 Builder 支持 cn_pipia 模块

**文件**: `backend/common/knowledge/builders_v2.py`, `build_legal_chunks_cn()`

修改 module 分配逻辑 (line 80-83)：

```python
# 修改前:
module = "cn_diagnosis"
if "cn_assessment" in modules:
    module = "cn_assessment"
elif "cn_review" in modules:
    module = "cn_review"

# 修改后:
for module in modules:
    # 对每个 module 生成独立 chunk
    chunks.append(KnowledgeChunkV2(
        chunk_id=f"{row.get('article_id','')}::{module}",
        module=module,
        ...
    ))
```

**注意**：这会导致 CN 索引从 549 条目显著增长
（每个 chunk 按 module 数复制）。
预期：
- `cn_diagnosis` 关联的 424 chunks 不变（多数只属于 diagnosis）
- `cn_assessment` 里的条目如果同时属于 pipia，会多一份 pipia 副本
- `cn_pipia` 新 partition 预计 50-100 chunks

#### Step 6.4：修改 orchestrator 添加 pipia 检索路由

**文件**: `backend/common/rag/orchestrator.py`, `retrieve()` 方法

在 `module == "cn_review"` 之后添加：
```python
if request.module == "cn_pipia":
    return self._retrieve_cn_pipia(request)
```

新增 `_retrieve_cn_pipia()` 方法（可参照 `_retrieve_cn_assessment()`）：

```python
def _retrieve_cn_pipia(self, request: RetrievalRequest) -> RetrievalBundle:
    bundle = RetrievalBundle(debug={"stage": request.task_stage})
    if request.task_stage in {"issue_discovery", "legal_grounding"}:
        workflow = self._search_index(
            "workflow_index_cn",
            request.query,
            top_k=max(4, request.top_k),
            filters={"module": "cn_pipia"},
        )
        bundle.workflow_rules = UsagePolicyFilter.filter(
            workflow,
            usage="internal_review",
            environment=request.environment,
        ).chunks
        legal = self._search_index(
            "legal_index_cn",
            request.query,
            top_k=request.top_k,
            filters={"module": "cn_pipia"},
        )
        legal.extend(self._legal_by_reference_ids(bundle.workflow_rules))
        bundle.legal_grounding = self._dedupe_chunks(
            UsagePolicyFilter.filter(
                self._dedupe_chunks(legal),
                usage="legal_grounding",
                environment=request.environment,
            ).chunks
        )
    if request.task_stage == "report_generation":
        templates = self._search_index(
            "template_index_cn",
            request.query or "个人信息保护影响评估 模板",
            top_k=request.top_k,
            filters={"module": "cn_pipia"},
        )
        bundle.templates = UsagePolicyFilter.filter(
            templates,
            usage="structure_control",
            environment=request.environment,
        ).chunks
    if request.task_stage == "evaluation":
        testcases = self._search_index(
            "testcase_index_cn",
            request.query,
            top_k=request.top_k,
            filters={"module": "cn_pipia"},
        )
        bundle.testcases = UsagePolicyFilter.filter(
            testcases,
            usage="evaluator",
            environment=request.environment,
        ).chunks
    return bundle
```

#### 验证命令

```bash
python3 -c "
import json
by_module = {}
with open('storage/rag/v3/legal_index_cn.jsonl') as f:
    for line in f:
        row = json.loads(line.strip())
        mod = row.get('module','?')
        by_module[mod] = by_module.get(mod, 0) + 1
for mod in sorted(by_module):
    print(f'{mod}: {by_module[mod]}')
print()
print('Target: cn_pipia > 0')
"
```

**预期输出**: `cn_pipia: 50~100`

---

### 修复 P1-3：扩大 CN assessment partition

#### Step 7.1：扩展 sources.csv 中 assessment 相关的 source

**文件**: `resources/legal/catalog/sources.csv`

为以下 source 的 `module` 列添加 `cn-assessment`：

```
CN-LAW-001   module 从 "cn-diagnosis" 改为 "cn-diagnosis|cn-assessment"
CN-LAW-002   module 从 "cn-diagnosis" 改为 "cn-diagnosis|cn-assessment"
CN-LAW-003   module 从 "cn-diagnosis" 改为 "cn-diagnosis|cn-assessment|cn-pipia"
CN-REG-008   module 从 "cn-diagnosis" 改为 "cn-diagnosis|cn-assessment"
CN-REG-006   module 从 "cn-diagnosis" 改为 "cn-diagnosis|cn-assessment"
CN-REG-007   module 从 "cn-diagnosis" 改为 "cn-diagnosis|cn-assessment"
```

**理论上限**：如果以上全部 6 个 source 的 chunks 都分配为
cn_assessment，则 cn_assessment 将从 44 增长到：
44 + 85 + 54 + 73 + 65 + 11 + 14 = 约 346 chunks

但因为有 `source_cap` 限制（P1-5/P1-6 修复），实际每次检索
最多从每个 source 取 3 条。

#### Step 7.2：沿用 P1-2 的多 module 分配逻辑

如 Step 6.3 所述，将 `build_legal_chunks_cn()` 改为
`for module in modules:` 的循环模式，使每个 chunk 可为多个模块生成副本。

#### 验证命令

```bash
python3 -c "
import json
by_module = {}
with open('storage/rag/v3/legal_index_cn.jsonl') as f:
    for line in f:
        row = json.loads(line.strip())
        mod = row.get('module','?')
        by_module[mod] = by_module.get(mod, 0) + 1
for mod in sorted(by_module):
    print(f'{mod}: {by_module[mod]}')
print()
print('Target: cn_assessment >= 150')
"
```

**预期输出**: `cn_assessment: >=150`

---

### 修复 P1-4：US 索引去噪

与 P0-1 方案相同，详见上文 Step 1.1-1.3。关键操作：

1. **sources.csv**：修改 9 条 `US-SUP-006~014` 的 `path` 为 `reference`
2. **registry.py**：`_modules_for_row()` US 分支添加 `reference` 判断
3. **builders_v2.py**：`build_legal_chunks_us()` 跳过 `modules` 为空的 source

#### 验证命令

```bash
python3 -c "
import json
total = 0
para = 0
by_module = {}
with open('storage/rag/v3/legal_index_us.jsonl') as f:
    for line in f:
        row = json.loads(line.strip())
        total += 1
        mod = row.get('module','?')
        by_module[mod] = by_module.get(mod, 0) + 1
        if row.get('article_no','').startswith('段落'):
            para += 1

for mod in sorted(by_module):
    print(f'{mod}: {by_module[mod]}')
print(f'Blind-split: {para}/{total} ({100*para/total:.1f}%)')
print(f'Target: {para} = 0')
"
```

**预期输出**：
```
us_14117: 17
us_cpra: >=80
us_vendor_review: >=80
Blind-split: 0/177 (0.0%)
```

---

### 修复 P1-5 + P1-6：添加 Source Diversity 重排

#### Step 8.1：修改 `_search_index()` 添加 source_cap 参数

**文件**: `backend/common/rag/orchestrator.py`, `_search_index()` 方法

**当前** (line 521-529)：
```python
ordered = sorted(merged_scores.items(), key=lambda item: item[1], reverse=True)
results = []
for doc_id, _ in ordered:
    chunk = _payload_to_chunk(payloads[doc_id])
    if not self._match_filters(chunk, filters or {}):
        continue
    results.append(chunk)
    if len(results) >= top_k:
        break
return results
```

**修改为**：
```python
ordered = sorted(merged_scores.items(), key=lambda item: item[1], reverse=True)
results: list[KnowledgeChunkV2] = []
source_counts: dict[str, int] = {}
for doc_id, _ in ordered:
    chunk = _payload_to_chunk(payloads[doc_id])
    if not self._match_filters(chunk, filters or {}):
        continue
    source_id = chunk.source_id or chunk.chunk_id
    # 每个 source 最多 source_cap 条（默认 3）
    if source_counts.get(source_id, 0) >= source_cap:
        continue
    results.append(chunk)
    source_counts[source_id] = source_counts.get(source_id, 0) + 1
    if len(results) >= top_k:
        break
return results
```

在方法签名中添加参数：
```python
def _search_index(
    self, index_name, query, *, top_k, filters=None,
    source_cap: int = 3,  # 新增
) -> list[KnowledgeChunkV2]:
```

**参数配置**：
- `source_cap=3`：每个 source 最多贡献 3 个 chunk
- 当 `top_k=8` 且 `source_cap=3` 时，至少返回 3 个不同 source 的结果
  （理想情况 8/3≈3 个 source，最差情况 2 个 source 各 4 条但被 cap 截断）
- 如果 `source_cap ≥ top_k`，则退化为原始行为（无限制）

#### Step 8.2：legal_grounding 阶段使用 source_cap

各 `_retrieve_*` 方法中调用 `_search_index("legal_index_*", ...)` 时，
均使用默认 `source_cap=3`（已在方法签名中设置），无需逐一修改。

#### 验证标准

回归测试：
```bash
pytest backend/common/rag/tests/test_multi_index_orchestrator.py
```

手动验证：
```bash
python3 -c "
from backend.common.rag.orchestrator import RetrievalOrchestrator
from backend.common.knowledge.v2 import RetrievalRequest

orch = RetrievalOrchestrator()
req = RetrievalRequest(
    module='cn_assessment',
    task_stage='legal_grounding',
    query='数据出境安全评估 个人信息的法律法规依据',
    top_k=12
)
bundle = orch.retrieve(req)
sources = set(chunk.source_id for chunk in bundle.legal_grounding)
print(f'Legal grounding results: {len(bundle.legal_grounding)}')
print(f'Unique sources: {len(sources)}')
for chunk in bundle.legal_grounding:
    print(f'  {chunk.source_id:<16} {chunk.article_no:<12} score via{chunk.citation_anchor[:40]}')
print(f'Target: >=3 unique sources')
"
```

**预期输出**: `Unique sources: >=3`

---

## 五、执行计划

### Phase 1：P0 修复（本周，预计 3 个工作日）

| 顺序 | 修复项 | 修改文件数 | 预计工时 | 验证方式 |
|:---:|------|:---:|:---:|------|
| 1 | EU 去噪 (P0-1) | 3 (sources.csv, registry.py, builders_v2.py) | 1h | 索引 EU 条目 897→~58, blind-split 归零 |
| 2 | US 去噪 (P1-4) | 3 (同上, 与P0-1同一批修改) | 0.5h | 索引 US 条目 299→~177, blind-split 归零 |
| 3 | CN 多 module 分配 (P1-2/P1-3 基础) | 2 (sources.csv, builders_v2.py) | 1h | cn_assessment ≥150 |
| 4 | pipia partition (P1-2) | 4 (module_catalog, sources.csv, builders_v2.py, orchestrator.py) | 1.5h | cn_pipia > 0 |
| 5 | Source diversity (P1-5/P1-6) | 1 (orchestrator.py) | 1h | 检索结果 ≥3 个不同 source |
| 6 | 重建全部索引 | 运行 `build_multi_index_v3()` | 0.5h | 全部 15 个索引文件更新且可读 |

### Phase 2：数据补全（本周-下周，预计 3 个工作日）

| 顺序 | 修复项 | 修改文件数 | 预计工时 | 验证方式 |
|:---:|------|:---:|:---:|------|
| 1 | GDPR 扩展 (P0-3) | 1 (regulation_articles.jsonl) | 3h | GDPR unique articles ≥80 |
| 2 | CPRA 扩展 (P0-2) | 2 (regulation_articles.jsonl, sources.csv) | 3h | us_cpra ≥80, us_vendor_review CPRA entries ≥80 |
| 3 | CN 短 chunk 合并 (P1-1) | 1 (builders_v2.py) | 1h | short chunks < 30% |
| 4 | 重建全部索引 | 运行 `build_multi_index_v3()` | 0.5h | 全部 15 个索引文件更新 |

### Phase 3：端到端验证（下周，预计 1 个工作日）

| 顺序 | 验证项 | 方式 | 通过标准 |
|:---:|------|------|------|
| 1 | 索引重建完整性 | `build_multi_index_v3()` 后检查各 `.jsonl` 和 `.vector.json` 文件 | 15 个索引文件全部存在、格式合法 |
| 2 | 检索质量回归 | `pytest backend/common/rag/tests/` | 全部通过 |
| 3 | 检索多样性 | 各模块提交检索请求，检查 source 分布 | 至少 3 个不同 source |
| 4 | Citation 利用率 | 运行各模块 pipeline 后检查 result.json | citation_map→footnote_map > 50% |
| 5 | Snapshot 完整性 | 检查所有 snapshot_path 引用的文件 | 0 缺失（当前已为 0） |
| 6 | 前端法规查看 | 在 `/evidence` 页面确认 noise source 不再出现 | 搜索 CELEX/FISA/NIST 等无结果 |

---

## 六、风险与降级方案

| 风险 | 概率 | 影响 | 降级方案 |
|------|:---:|------|------|
| GDPR/CPRA 原文获取困难 | 中 | P0-2、P0-3 无法完成 | 优先从 https://gdpr-info.eu/ 和 https://leginfo.legislature.ca.gov/ 批量抓取；Code 用已有 12 条做增量 |
| 多 module 分配导致索引膨胀 | 低 | CN 从 549→~1200，检索稍慢 | 设置 `source_cap=3` 限制每 source 返回数；使用 `legal_source_fingerprint()` 增量更新 |
| Source diversity 降低召回 | 低 | 有时同 source 的多条 chunk 确实最相关 | `source_cap` 可配置（source_cap=0 关闭限制） |
| pipia 无独立 workflow_rule | 中 | P1-2 仅完成 partition，workflow 仍为空 | 可在后续迭代中补充 pipia 专属 workflow 条目 |
| 现有测试依赖索引内容 | 低 | `test_multi_index_orchestrator.py` 可能失败 | 更新测试中的 expected chunk counts；Phase 3 第2步会处理 |

---

## 七、附录：完整修改文件清单

```
数据文件：
  resources/legal/catalog/sources.csv                       ← 噪音源标记 reference
  resources/legal/catalog/module_catalog.v1.json            ← 添加 cn_pipia 定义
  resources/legal/registry/regulation_articles.jsonl        ← 扩展 GDPR + CPRA

代码文件：
  backend/common/knowledge/registry.py                      ← _modules_for_row() 支持 reference
  backend/common/knowledge/builders_v2.py                   ← 跳过空 modules + 短chunk合并 + 多module
  backend/common/rag/orchestrator.py                        ← source_cap + cn_pipia 路由

索引文件（自动重建）：
  storage/rag/v3/legal_index_{cn,eu,us}.jsonl               ← 去噪 + 数据补全后
  storage/rag/v3/legal_index_{cn,eu,us}.vector.json         ← 同上
  storage/rag/v3/workflow_index_{cn,eu,us}.jsonl            ← 不变（或加 pipia workflow）
  storage/rag/v3/standard_clause_index_{cn,eu,us}.jsonl     ← 不变
  storage/rag/v3/template_index_{cn,eu,us}.jsonl            ← 不变（或加 pipia template）
  storage/rag/v3/testcase_index_{cn,eu,us}.jsonl            ← 不变
```

**总修改文件数**: 6 个源代码文件 + 3 个数据文件

**不改动的部分**:
- `KnowledgeChunkV2` Schema（`backend/common/knowledge/v2.py`）
- `UsagePolicyFilter` 逻辑（`backend/common/knowledge/usage_policy.py`）
- Embedding 算法（`backend/common/rag/embedding.py`）
- 索引格式和向量化方式（`backend/common/rag/vector_store.py`）
- `HashingEmbedder` 版本号（`backend/common/rag/constants.py`）
- 前端 EvidenceCenterPage / LawViewerPage 路由和渲染
