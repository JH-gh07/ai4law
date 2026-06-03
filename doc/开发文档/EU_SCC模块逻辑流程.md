# EU SCC 合规模块 — 全部代码逻辑流程文档

> 模块路径: `backend/modules/eu_scc/`
> 法律框架: GDPR Article 44–49 / EU 2021/914 / EDPB Recommendations 01/2020 / Schrems II C-311/18
> 创建时间: 2026-06-03
> 测试状态: 11 passed

---

## 一、总体架构概览

### 1.1 两层引擎架构

```
POST /eu_scc/generate
        │
        ▼
  EU_SCCService.generate_report(payload)
        │
        ├─[第0层] 确定性规则引擎 (scc_parser.py + scc_rule_engine.py)
        │   ├─ parse_scc_document()     → SCC 文档结构化解析
        │   ├─ _build_transfer_chain()  → 数据传输链建模
        │   └─ run_eu_scc_rule_engine() → 5 大审查器并行执行
        │       输出: SCCRuleEngineResult (含所有 findings + 总体评级)
        │
        └─[第1层] WorkflowPipeline 14 步流水线
            ├─ extract_profile       → 原样传递 payload
            ├─ evaluate_diagnosis    → rule_result (跳过内部诊断)
            ├─ build_facts           → 从 request + rule result 提取事实
            ├─ retrieve_regulations  → RAG 检索 GDPR/EU SCC 法规
            ├─ build_attachment_notes→ 解析上传文件
            ├─ build_issues          → 基于 findings 生成 IssueItem
            ├─ build_evidence        → 构建 issue→fact→regulation 证据链
            ├─ build_context_pack    → 组装生成上下文包
            ├─ generate_chapters     → LLM 生成 4 章报告
            ├─ check_consistency     → 结构性检查
            ├─ render_artifacts      → MD + 批注版 DOCX + JSON
            └─ → SCCReviewResult
```

### 1.2 与中国 SCC 模块的关系

本模块是 **独立新建** 的 EU SCC 合规审查模块，与中国 SCC 模块 (`backend/modules/scc/`) 完全分离、互不影响：

| 维度 | 中国 SCC | EU SCC（本模块）|
|------|---------|-----------------|
| API 端点 | `/scc/generate` | `/eu_scc/generate` |
| 法律框架 | 中国 PIPL / 标准合同办法 | GDPR / EU 2021/914 / Schrems II |
| 法规检索管辖域 | `jurisdiction="cn"` | `jurisdiction="eu"` |
| 风险评级基础 | PII/SPI 数量阈值 | 模块正确性 + 条款完整性 + TIA + 补充措施 |
| 架构 | 直接串联调用 | 规则引擎 + WorkflowPipeline |

---

## 二、逐模块详细逻辑流程

---

### 2.1 `schema.py` — 数据模型层

**文件**: `backend/modules/eu_scc/schema.py`
**行数**: ~180 行
**模型总数**: 18 个 Pydantic BaseModel

#### 2.1.1 SCC 文档结构模型（解析产物）

```
SCCParty
├── name: str              ← 主体名称
├── address: str           ← 地址
├── contact: str           ← 联系方式
├── role: str              ← controller / processor
├── signature: str         ← 签名信息
└── is_incomplete: bool    ← 是否为 "See MSA" 等占位引用

SCCAnnexIA                  ← Annex I.A — 主体清单
└── parties: list[SCCParty]

SCCAnnexIB                  ← Annex I.B — 传输描述
├── data_subjects: str
├── data_categories: str
├── special_category_data: list[str]  ← GDPR Article 9 特殊类别
├── processing_purpose: str
├── processing_nature: str
├── transfer_frequency: str
└── retention_period: str

SCCAnnexII                  ← Annex II — 技术组织措施
├── tom_items: list[str]              ← 基础安全措施
└── supplementary_measures: list[str] ← Schrems II 补充措施

SCCAnnexIII                 ← Annex III — 子处理者名单
└── sub_processors: list[dict]  ← [{name, location}]

SCCClause                   ← 单个条款
├── clause_no: int          ← 1–18
├── title: str
├── content: str
├── has_deviation: bool
├── deviation_type: str     ← deletion | weakening | restriction_added | none
└── deviation_description: str

SCCDocument                 ← 解析后的完整 SCC 文档
├── module_type: str        ← Module One / Two / Three / Four
├── clauses: list[SCCClause]
├── annex_i_a: SCCAnnexIA
├── annex_i_b: SCCAnnexIB
├── annex_ii: SCCAnnexII
├── annex_iii: SCCAnnexIII
└── raw_text: str
```

#### 2.1.2 传输链模型

```
SCCTransferChain
├── exporter_name: str
├── exporter_role: str       ← controller / processor
├── importer_name: str
├── importer_role: str       ← controller / processor
├── sub_processors: list[str]
├── onward_transfer_locations: list[str]
├── storage_locations: list[str]
└── access_locations: list[str]
```

#### 2.1.3 审查发现与结果模型

```
SCCFinding                  ← 单条合规发现
├── finding_id: str
├── location: str           ← "Clause 15(a)" / "Annex I.B" / "Annex II"
├── clause_ref: str         ← "15(a)"
├── original_text: str
├── issue_type: str         ← module_mismatch | clause_weakened | clause_deleted
│                             | annex_incomplete | annex_vague
│                             | special_category_misclassified | tia_missing
│                             | supplementary_measures_insufficient
│                             | sub_processor_chain_incomplete | ...
├── severity: str           ← HIGH / MEDIUM / LOW
├── risk_analysis: str      ← 风险分析说明
├── legal_basis: str         ← 法规依据
├── recommendation: str     ← 修改建议
└── suggested_text: str     ← 建议修改后的文本

ModuleValidation            ← 模块校验结果
├── expected_module: str
├── actual_module: str
├── is_correct: bool
└── mismatch_reason: str

ClauseComparison            ← 条款比对结果
├── clauses_checked: int
├── deviations_found: int
└── findings: list[SCCFinding]

AnnexReview                 ← Annex 审查结果
└── findings: list[SCCFinding]

TIAReview                   ← TIA / 补充措施审查结果
├── has_third_country_transfer: bool
├── third_country_transfers: list[str]
├── tia_present: bool
├── has_supplementary_measures: bool
├── schrems_ii_measures_present: bool
└── findings: list[SCCFinding]

SCCRuleEngineResult         ← 规则引擎总输出
├── document: SCCDocument
├── transfer_chain: SCCTransferChain
├── module_validation: ModuleValidation
├── clause_comparison: ClauseComparison
├── annex_review: AnnexReview
├── tia_review: TIAReview
├── all_findings: list[SCCFinding]
└── overall_rating: str     ← HIGH / MEDIUM / LOW

SCCReviewResult             ← 最终审查结果
├── report_path: str
├── output_files: dict[str, str]
├── findings: list[SCCFinding]
├── module_validation: ModuleValidation
├── chapters: list[SCCChapter]
└── consistency_issues: list[str]
```

---

### 2.2 `scc_parser.py` — SCC 文档解析器

**文件**: `backend/modules/eu_scc/scc_parser.py`
**行数**: ~330 行
**核心函数**: `parse_scc_document(text, declared_module, exporter_role, importer_role) → SCCDocument`

#### 2.2.1 解析流程

```
原始 SCC 文本
    │
    ├─[1] _find_module_type()
    │     正则匹配 "MODULE ONE/TWO/THREE/FOUR" → module_type
    │     支持 Module One/Two/Three/Four 和 MODULE 1/2/3/4 两种写法
    │
    ├─[2] _split_sections()
    │     用 Annex I/II/III 的正则模式定位 annex 边界
    │     将文本分割为:
    │       preamble → 序言
    │       clauses  → Clause 正文区域
    │       annex_ia → Annex I.A 区域
    │       annex_ib → Annex I.B 区域
    │       annex_ii → Annex II 区域
    │       annex_iii→ Annex III 区域
    │
    ├─[3] _extract_clauses()
    │     在内置的 _SCC_CLAUSE_TITLES 字典中查找 Clause 1-18 的标准标题
    │     每个 clause 的标题包括 "Purpose and scope" / "Docking clause" /
    │       "Use of sub-processors" / "Local laws and practices" /
    │       "Obligations in case of access by public authorities" 等
    │     用这些标题在 clauses 区域中定位分割点
    │     对每个 clause 创建 SCCClause(clause_no, title, content)
    │     备选: 如果标准标题匹配失败，用 r"[Cc]lause\s+(\d+)" 模式兜底
    │
    ├─[4] _extract_annex_ia()
    │     在 annex_ia 区域中用正则分割 "Data exporter:" 和 "Data importer:" 块
    │     对每个 party 块提取:
    │       name   ← r"(?:name|名称)[:\s]*(.+)"
    │       address← r"(?:address|地址)[:\s]*(.+)"
    │       is_incomplete ← 检测 "See MSA" / "See Master Service Agreement"
    │     返回 SCCAnnexIA(parties=[...])
    │
    ├─[5] _extract_annex_ib()
    │     用多组正则提取 Annex I.B 各字段:
    │       data_subjects      ← "Data subjects:" / "categories of data subjects:"
    │       data_categories    ← "Data categories:" / "Categories of personal data:"
    │       processing_purpose ← "Purpose:" / "purposes of transfer:"
    │       retention_period   ← "Retention:" / "period:" / "duration:"
    │       transfer_frequency ← "Frequency:" / "transfer frequency:"
    │     特殊类别检测:
    │       扫描 "special categor" / "sensitive data" / "health data" /
    │             "genetic" / "biometric" / "religious" / "political" /
    │             "ethnic" / "trade union" 等关键词
    │       如果命中则加入 special_category_data 列表
    │
    ├─[6] _extract_annex_ii()
    │     提取以 - 或 • 开头的列表项 → tom_items
    │     扫描 "supplement" / "additional" / "further measure" /
    │          "schrems" / "onward transfer restriction" 关键词
    │     → supplementary_measures
    │
    ├─[7] _extract_annex_iii()
    │     提取以 - 或 • 开头的列表项作为子处理者
    │     尝试从每项中提取 location 字段
    │
    └─[8] _build_transfer_chain()
          从 Annex I.A 中提取 exporter/importer 名称和角色
          从 Annex III 中提取子处理者名称和位置
          扫描全文中的国家名称 → 填充 storage_locations / access_locations
```

#### 2.2.2 关键数据结构

**内置条款标题字典** `_SCC_CLAUSE_TITLES`:
```
1  → "Purpose and scope" / "Clause 1"
2  → "Effect and invariability" / "Clause 2"
3  → "Third-party beneficiaries" / "Clause 3"
7  → "Docking Clause" / "docking" / "Clause 7"
9  → "Use of sub-processors" / "sub processors" / "Clause 9"
14 → "Local laws and practices" / "local laws" / "Clause 14"
15 → "Access by public authorities" / "public authorities" /
      "government access" / "Clause 15"
17 → "Governing law" / "governing" / "Clause 17"
18 → "Choice of forum and jurisdiction" / "jurisdiction" / "Clause 18"
```

**Annex 边界定位模式** `_ANNEX_PATTERNS`:
```
annex_ia  → "ANNEX I" / "Annex I.A" / "LIST OF PARTIES"
annex_ib  → "Annex I.B" / "DESCRIPTION OF TRANSFER"
annex_ii  → "ANNEX II" / "TECHNICAL AND ORGANISATIONAL MEASURES"
annex_iii → "ANNEX III" / "LIST OF SUB-PROCESSORS"
```

---

### 2.3 `scc_rule_engine.py` — 五大审查器

**文件**: `backend/modules/eu_scc/scc_rule_engine.py`
**行数**: ~420 行
**入口**: `run_eu_scc_rule_engine(doc, chain, declared_module, has_tia, has_supplementary) → SCCRuleEngineResult`

#### 2.3.1 内置标准条款文本 (`_STANDARD_CLAUSE_KEY_PROVISIONS`)

引擎内置了 EU 2021/914 关键条款的标准措辞作为比对基准：

```
Clause 7:
  "Additional parties may accede to these Clauses throughout
   the life-cycle of the contract."
  "Changes to the agreed-upon list of additional parties may only
   be made with the prior consent of the data exporter."

Clause 9:
  "The data importer shall not sub-contract any of its processing
   activities without the data exporter's prior specific written
   authorization."
  "The data importer shall maintain an up-to-date list of sub-processors
   and make it available to the data exporter."

Clause 14:
  "The Parties warrant that they have no reason to believe that the
   laws and practices in the third country of destination prevent the
   data importer from fulfilling its obligations under these Clauses."
  "The data importer shall document the specific circumstances of the
   transfer and the assessment carried out."

Clause 15:
  "The data importer shall promptly notify the data exporter if it
   receives a legally binding request from a public authority."
  "The data importer shall review the legality of the request and
   challenge it if it reasonably considers that there are grounds to do so."
  "The data importer shall provide the data exporter with as much
   relevant information as possible."
  "The data importer shall document its assessment and make it available
   to the competent supervisory authority on request."

Clause 16:
  "Following termination, the data importer shall delete all personal
   data or return them to the data exporter."

Clause 17:
  "Each Party shall be liable to the other Party for any damages it
   causes the other Party by any breach of these Clauses."

Clause 18:
  "These Clauses shall be governed by the law of one of the EU Member
   States."
  "Any dispute shall be resolved by the courts of an EU Member State."
```

#### 2.3.2 削弱信号检测 (`_WEAKENING_SIGNALS`)

引擎内置了针对关键条款的削弱信号模式表，覆盖 Clause 9/14/15：

| 条款 | 检测模式 | 描述 |
|------|---------|------|
| Clause 15(a) | `as soon as legally permissible` | "promptly"→"法律许可时" |
| Clause 15(a) | `without undue delay to the extent legally permissible` | 增加法律许可限定条件 |
| Clause 15(a) | `subject to applicable local law` | 受限于当地法律 |
| Clause 15(b) | `at its sole discretion` | 审查义务→酌情处理 |
| Clause 15(b) | `if it considers appropriate` | 降低审查标准 |
| Clause 15(b) | `reserves the right` | 保留选择权 |
| Clause 15(c) | `at the data importer's discretion` | 信息提供→酌情处理 |
| Clause 15(c) | `to the extent reasonably practicable` | 增加合理可行限定 |
| Clause 14 | `to the best of its knowledge` | 评估义务→"据其所知" |
| Clause 14 | `no independent assessment` | 否认独立评估义务 |
| Clause 9 | `general written authorization` | 具体授权→一般授权 |
| Clause 9 | `objection within N business days` | objection 窗口过短 |

#### 2.3.3 审查器一：`validate_module_selection(chain, declared_module) → ModuleValidation`

**逻辑**:

```
exporter_role × importer_role → expected_module:

  controller × controller → Module One    (C2C)
  controller × processor  → Module Two    (C2P)
  processor  × processor  → Module Three  (P2P)
  processor  × controller  → Module Four  (P2C)
  无法确定                  → "" (空字符串，标记为无法判断)

compare expected_module vs declared_module:
  match → is_correct = True
  mismatch → is_correct = False + mismatch_reason
```

#### 2.3.4 审查器二：`compare_standard_clauses(doc) → ClauseComparison`

**逻辑**:

```
对每个 clause:
  1. 归一化 clause.content
  2. 遍历 _WEAKENING_SIGNALS 中的 (label, signals) 对
  3. 对每个 (pattern, risk_desc, suggestion):
     如果在 clause.content 中匹配 pattern:
       → 创建 SCCFinding:
           finding_id = "EU-SCC-CLAUSE-{clause_no}-DEVIATION"
           location = label
           clause_ref = "15(a)" / "14" / "9" 等（从 label 中提取）
           issue_type = "clause_weakened"
           severity = "HIGH"
           legal_basis = "EU 2021/914, Recital 3 (invariability);
                          GDPR Article 46"
           recommendation = suggestion
       → 标记 clause.has_deviation = True
       → 标记 clause.deviation_type = "weakening"
  4. 返回 ClauseComparison(clauses_checked, deviations_found, findings)
```

**关键设计**: 只在文本级别做正则匹配，不依赖 LLM。

#### 2.3.5 审查器三：`review_annexes(doc, declared_module) → AnnexReview`

**Annex I.A 审查**:

```
对每个 party:
  1. 如果 is_incomplete (例如 "See MSA"):
     → MEDIUM: "主体信息引用外部文档，未在SCC中直接填写"
  2. 如果 name 或 role 为空:
     → MEDIUM: "主体名称或角色缺失"
  3. 如果总 party 数 < 2 (且应为 Module One/Two):
     → HIGH (Docking Clause 多方场景): "主体数量不足2个，
        加入方信息可能缺失"
```

**Annex I.B 审查**:

```
1. 如果 data_categories 过于模糊
   (例如 "order history data" / "customer data"):
   → LOW: "数据类别描述过于模糊，不满足EU 2021/914的明确性要求"

2. 扫描内容中是否包含健康/医疗/基因/生物识别术语:
   "health", "medical", "patient", "diagnosis", "clinical",
   "treatment", "disease", "prescription", "genetic", "biometric"
   如果有这些术语但 special_category_data 列表为空:
   → HIGH: "传输描述中包含健康/医疗数据术语，但特殊类别数据
           未声明。依据GDPR Article 9，健康数据需要明确同意或其他
           豁免条件，仅SCC可能不足。"
```

**Annex II 审查**:

```
如果 tom_items 为空:
  → HIGH: "Annex II 技术组织措施为空，不满足GDPR Articles 32/46要求"
```

**Annex III 审查**:

```
允许为空（无子处理者是合法的）。
```

#### 2.3.6 审查器四：`review_tia_and_measures(chain, doc, has_tia, has_supplementary) → TIAReview`

这是最复杂的审查器，负责 Schrems II 完整性评估。

**第三国识别**:

```
从 chain 的 storage_locations + access_locations + onward_transfer_locations 提取位置
对每个位置:
  归一化后匹配 _THIRD_COUNTRY_ADEQUACY 字典:
    有充分性认定: UK, Japan, South Korea, Switzerland,
                  Canada, Argentina, Israel, New Zealand, Uruguay...
    无充分性认定: United States, India, Serbia, China,
                  Russia, Brazil, Singapore, Australia...
```

**Schrems II 补充措施检测**:

扫描 Annex II 文本和全文，匹配三类措施：

```
技术措施 _SCHREMS_II_TECHNICAL_MEASURES:
  "end-to-end encryption", "e2e encryption", "端到端加密"
  "hold your own key", "customer-managed keys", "BYOK"
  "eu-held encryption keys", "欧盟持钥"
  "zero-access encryption", "zero knowledge encryption"

合同措施 _SCHREMS_II_CONTRACTUAL_MEASURES:
  "government access notification", "政府访问通知"
  "challenge unlawful requests", "挑战非法请求"
  "transparency report", "透明度报告"
  "warrant canary"

组织措施 _SCHREMS_II_ORGANIZATIONAL_MEASURES:
  "data minimization and retention limits"
  "independent annual audit", "独立年度审计"
  "privacy impact assessment for government access"
  "separation of duties for key management"
```

**TIA 缺失发现**:

```
如果 has_third_country AND NOT has_tia:
  → HIGH: "识别到向 {countries} 的第三国传输，但未提供TIA。
          根据GDPR和Schrems II (C-311/18)，向无充分性认定第三国
          传输前必须完成书面的Transfer Impact Assessment。"

如果 has_third_country AND clause_14_weakened:
  → HIGH: "Clause 14被削弱且存在第三国传输，
          叠加TIA缺失形成不可接受的合规风险。"
```

**补充措施不足发现**:

```
如果 has_third_country AND NOT has_tia:
  → HIGH: 列出技术/合同/组织三类措施的检测结果
          (found/not found)。

如果存在 US 基础设施 (AWS/GCP/Azure):
  → HIGH: "数据流向美国基础设施。美国法律(CLOUD Act,
          FISA 702)允许政府访问。缺少针对美国监控风险的
          补充措施。"
  建议:
    1. 端到端加密 + EU 持钥
    2. 输入方不可访问明文数据
    3. 合同承诺挑战 FISA 702 请求
    4. 透明度报告

如果子处理者在非充分性第三国:
  → MEDIUM: 逐项检查 Clause 9 授权、SCC 覆盖、TIA 覆盖
```

#### 2.3.7 审查器五：`score_scc_risk(all_findings) → str`

```
纯规则逻辑:
  遍历所有 findings 的 severity:
    存在 HIGH → 返回 "HIGH"
    存在 MEDIUM → 返回 "MEDIUM"
    否则 → 返回 "LOW"

注意: 不使用 PII/SPI 数量阈值。
风险评分基础是 SCC 文档本身的合规缺陷，不是数据量。
```

#### 2.3.8 主入口 `run_eu_scc_rule_engine()`

```
1. validate_module_selection(chain, declared_module)
   → ModuleValidation
2. compare_standard_clauses(doc)
   → ClauseComparison
3. review_annexes(doc, declared_module)
   → AnnexReview
4. review_tia_and_measures(chain, doc, has_tia, has_supplementary)
   → TIAReview
5. 汇总所有 findings:
   - 如果 ModuleValidation.is_correct=False → 追加 module_mismatch finding
   - 追加 ClauseComparison.findings
   - 追加 AnnexReview.findings
   - 追加 TIAReview.findings
6. score_scc_risk(all_findings) → overall_rating
7. 返回 SCCRuleEngineResult
```

---

### 2.4 `fact_builder.py` — 事实提取器

**文件**: `backend/modules/eu_scc/fact_builder.py`
**行数**: ~65 行
**核心函数**: `build_eu_scc_facts(request, rule_result) → list[FactItem]`

#### 2.4.1 提取三层事实

```
第一层: 请求事实 (source_type="schema", confidence=1.0)
  request.project_name
  request.declared_module_type
  request.exporter_role / importer_role
  request.has_tia / has_supplementary_measures

第二层: 文档事实 (source_type="schema")
  doc.module_type
  doc.clause_count
  doc.annex_ia.party_count
  doc.annex_ii.tom_count
  doc.annex_iii.sub_processor_count
  chain.exporter_role / chain.importer_role
  chain.sub_processor_count

第三层: 规则引擎推导 (source_type="derived", source_ref="RuleEngine")
  review.module_is_correct
  review.expected_module
  review.clauses_checked / deviations_found
  review.has_third_country_transfer / tia_present / schrems_ii_measures
  review.overall_rating / finding_count
```

#### 2.4.2 FactItem 格式

```
FactItem(
  fact_id = "EU-SCC-FACT-{sanitized_field_path}"
  source_type = "schema" | "derived"
  source_ref = "SCCReviewRequest" | "RuleEngine"
  field_path = 例如 "request.project_name"
  value = 原始值
  normalized_value = 原始值
  confidence = 1.0 (schema) | varies (derived)
  evidence_status = "user_claim_only"
)
```

---

### 2.5 `issue_builder.py` — 合规问题识别器

**文件**: `backend/modules/eu_scc/issue_builder.py`
**行数**: ~100 行
**核心函数**: `build_eu_scc_issues(facts, rule_result, regulations) → list[IssueItem]`

#### 2.5.1 4 章映射

```
EU_SCC_CHAPTER_KEYS = {
    "文件概要"             → "document_overview"
    "总体合规评级"          → "overall_rating"
    "条款级审查发现"        → "clause_findings"
    "法规依据与修改建议"    → "legal_basis_and_recommendations"
}
```

#### 2.5.2 6 种合规问题

| Issue ID | 触发条件 | 严重度 | affects_outputs |
|----------|---------|--------|-----------------|
| EU-SCC-ISSUE-MODULE-MISMATCH | `module_validation.is_correct=False` | HIGH | overall_rating, clause_findings |
| EU-SCC-ISSUE-CLAUSE-DEVIATIONS | `clause_comparison.deviations_found > 0` | HIGH | clause_findings, legal_basis |
| EU-SCC-ISSUE-THIRD-COUNTRY | `tia_review.has_third_country_transfer` | HIGH | overall_rating, clause_findings, legal_basis |
| EU-SCC-FINDING-{id} | 每个 severity=HIGH 的 finding | HIGH | clause_findings, legal_basis |
| EU-SCC-ISSUE-NO-ISSUES | 无严重问题 | LOW | overall_rating |

**法规引用备选**: 如果 RAG 未返回结果，使用默认引用:
```
["EU 2021/914", "GDPR Article 46", "Schrems II C-311/18", "EDPB 01/2020"]
```

---

### 2.6 `evidence_builder.py` — 证据链构建器

**文件**: `backend/modules/eu_scc/evidence_builder.py`
**行数**: ~35 行
**核心函数**: `build_eu_scc_evidence(facts, issues, regulations) → (list[IssueItem], list[EvidenceItem])`

#### 2.6.1 证据链逻辑

```
对每个 issue:
  1. 过滤有效的 fact_refs (只保留 fact_ids 中存在的引用)
     备选: 如果没有有效引用，取第一个 fact
  2. 生成 evidence_id = "EU-SCC-EVIDENCE-{issue_id_sanitized}"
  3. 确定置信度:
     BLOCKER → 0.95
     HIGH    → 0.90
     MEDIUM  → 0.75
     LOW     → 0.60
  4. 创建 EvidenceItem:
     claim       = issue.title
     fact_refs   = 过滤后的有效引用
     rule_refs   = issue.rule_refs 或 default_rule_refs
     conclusion  = issue.recommended_action
     confidence  = 按严重度计算的置信度
     used_by     = [issue_id, *affects_outputs]
  5. 更新 issue.evidence_refs = [evidence_id]
返回 (updated_issues, evidence_chain)
```

---

### 2.7 `service.py` — 核心编排服务

**文件**: `backend/modules/eu_scc/service.py`
**行数**: ~280 行
**核心类**: `EU_SCCService`

#### 2.7.1 构造函数

```python
def __init__(self, llm_client=None):
    self.llm_client = llm_client or LLMClient(get_settings())
    self.parser = FileParser()                    # 附件解析器
    self.tasks = InMemoryTaskManager("eu_scc")    # 异步任务管理器
```

#### 2.7.2 主方法 `generate_report(payload) → SCCReviewResult`

```
1. 创建唯一 task_id + trace 目录
2. 规则引擎阶段:
   a. parse_scc_document(payload.scc_text, ...)
      → SCCDocument (Clause 1-18, Annexes)
   b. _build_transfer_chain(exporter_role, importer_role, doc, "")
      → SCCTransferChain (exporter, importer, sub_processors, locations)
   c. run_eu_scc_rule_engine(doc, chain, declared_module, has_tia, has_supplementary)
      → SCCRuleEngineResult (module_validation + clause_comparison +
                              annex_review + tia_review + all_findings +
                              overall_rating)
   d. Trace 记录 rule_engine_result

3. WorkflowPipeline 阶段:
   a. extract_profile        → 原样 payload
   b. evaluate_diagnosis     → rule_result
   c. build_facts            → build_eu_scc_facts(payload, rule_result)
   d. retrieve_regulations   → 检索 EU GDPR/SCC 法规
   e. build_attachment_notes → 解析上传文件
   f. build_issues           → build_eu_scc_issues(facts, rule_result, regs)
   g. build_evidence         → build_eu_scc_evidence(facts, issues, regs)
   h. build_context_pack     → 组装 GenerationContextPack
   i. generate_chapters      → LLM 生成 4 章 (或占位内容)
   j. check_consistency      → 结构性检查
   k. render_artifacts       → MD + 批注版 DOCX + JSON

4. 返回 SCCReviewResult
```

#### 2.7.3 法规检索 `_retrieve_regulations`

```python
query = (
    "GDPR Article 46 standard contractual clauses EU 2021/914 "
    "EDPB recommendations Schrems II transfer impact assessment "
    "{declared_module_type} {exporter_role} {importer_role}"
)
retrieve_regulations(query, top_k=5, jurisdiction="eu", path="scc")
```

检索路由: `jurisdiction="eu"` + `path="scc"` → `_retrieve_eu()` → `eu_scc` 模块的 EU 索引。

#### 2.7.4 章节生成 `_generate_chapters`

4 章标题:
```
1. 文件概要 (document_overview)
2. 总体合规评级 (overall_rating)
3. 条款级审查发现 (clause_findings)
4. 法规依据与修改建议 (legal_basis_and_recommendations)
```

**LLM 启用时**: 调用 `generate_chapter(llm, "eu_scc", title, context_block, citations)`
Context block 包含:
```
- 模块校验结果
- 条款偏离数
- 第三国传输清单
- TIA 是否存在
- Schrems II 措施是否存在
- 总体评级
- Findings 列表 (最多10条)
- Issues 列表
- 法规检索结果 (最多5条)
```

**LLM 禁用时**: 调用 `_render_placeholder(title, chapter_id, rule_result)` 生成结构化占位内容。

#### 2.7.5 产物渲染 `_render_outputs`

输出目录: `outputs/eu_scc/{task_id}/outputs/`

```
1. {公司名}_EU_SCC审查报告_{日期}.md        ← self-rendered MD
2. {公司名}_EU_SCC审查报告_{日期}.docx      ← placeholder (template not yet available)
3. {公司名}_EU_SCC批注修订版_{日期}.docx    ← 如果有源 DOCX:
     每个 finding → DocxComment(label, location, quote, risk_level, basis, risk_analysis, suggestion)
     render_commented_docx(source, output, comments)
     在原合同条款上嵌入审查批注
4. findings.json                              ← 所有 SCCFinding 序列化
5. rule_engine_result.json                    ← 完整规则引擎输出
6. issues.json                                ← IssueItem 列表
7. evidence.json                              ← EvidenceItem 列表
```

#### 2.7.6 模板映射 `_build_template_mapping`

构建 10 个模板变量:
```
company_name, review_date, module_type, overall_rating,
finding_count, clause_deviations, third_country, tia_present,
executive_summary (第2章摘要 + 法规引用),
findings_table (Markdown 7列表格),
revision_recommendations (第4章摘要 + 法规引用)
```

#### 2.7.7 异步 API

```
submit_async     → InMemoryTaskManager.submit(generate_report)
get_async_status → InMemoryTaskManager.get_or_raise(task_id)
retry_async      → InMemoryTaskManager.retry(task_id)
cancel_async     → InMemoryTaskManager.cancel(task_id)
```

---

### 2.8 `router.py` — API 端点

**文件**: `backend/modules/eu_scc/router.py`
**行数**: ~60 行

```
router = APIRouter(tags=["eu_scc"])
service = EU_SCCService()         # 模块级单例
TASK_OWNERS: dict[str, str] = {}  # 内存任务归属表

端点:
  POST   /eu_scc/generate              → 同步生成 + 注册制品
  POST   /eu_scc/generate_async        → 异步提交 + 记录属主
  GET    /eu_scc/tasks/{task_id}       → 轮询状态 + 完成后注册制品
  POST   /eu_scc/tasks/{task_id}/retry → 重试失败任务
```

属主校验: `_assert_owner(task_id, user_id)` — 校验失败返回 404。

---

## 三、端到端完整数据流（以案例一 C2C + US AWS 为例）

```
[用户提交]
POST /eu_scc/generate
body: {
  project_name: "EU SCC Test",
  scc_text: <SCC 全文>,
  declared_module_type: "Module One",
  exporter_role: "controller",
  importer_role: "controller",
  has_tia: false,
  has_supplementary_measures: false
}

        ↓

[EU_SCCService.generate_report()]

        ↓
[1] parse_scc_document(scc_text)
    提取:
      module_type = "Module One"
      clauses = [Clause 1, 2, 7, 9, 14, 15, 16, 17, 18]
      annex_i_a.parties = [
        {name: "French Retail Group SA", role: "controller"},
        {name: "UK Store Ltd", role: "controller"}
      ]
      annex_i_b.data_categories = "order history data, contact details"
      annex_ii.tom_items = ["TLS encryption", "AES-256", "RBAC"]
      annex_iii.sub_processors = [
        {name: "Amazon Web Services (AWS)", location: "United States"}
      ]

        ↓
[2] _build_transfer_chain()
    exporter_name = "French Retail Group SA"
    exporter_role = "controller"
    importer_name = "UK Store Ltd"
    importer_role = "controller"
    sub_processors = ["Amazon Web Services (AWS)"]
    storage_locations = ["United States"]
    onward_transfer_locations = ["United States"]

        ↓
[3] run_eu_scc_rule_engine()

    3a. validate_module_selection()
        controller × controller → Module One
        declared = Module One → is_correct = True ✓

    3b. compare_standard_clauses()
        检查 Clause 7, 9, 14, 15, 16, 17, 18
        均为标准文本 → deviations_found = 0

    3c. review_annexes()
        Annex I.A: 2 parties, OK
        Annex I.B: "order history data" → 模糊 → LOW finding
        Annex II: 有 TOMs → OK
        Annex III: AWS in US → flagged

    3d. review_tia_and_measures()
        third_country = ["United States"]  ← 无充分性认定
        has_tia = False → TIA_MISSING finding (HIGH)
        schrems_tech = False (只有 TLS/AES，无E2EE/持钥)
        schrems_contractual = False
        schrems_org = False
        → SUPP_MEASURES_INSUFFICIENT finding (HIGH)
        US detected → US_CLOUD_ACT_RISK finding (HIGH)
        AWS sub-processor → SUBPROC_THIRD finding (MEDIUM)

    3e. score_scc_risk()
        findings 中有 HIGH → overall_rating = "HIGH"

        ↓
    输出 SCCRuleEngineResult:
      all_findings = [
        {annex_vague: "order history data" (LOW)},
        {tia_missing: US third country no TIA (HIGH)},
        {supplementary_measures_insufficient: Schrems II missing (HIGH)},
        {supplementary_measures_insufficient: US CLOUD Act risk (HIGH)},
        {sub_processor_chain_incomplete: AWS in US (MEDIUM)}
      ]
      overall_rating = "HIGH"

        ↓
[4] WorkflowPipeline.run()
    → facts (21 项)
    → regulations (5 条 EU 法规)
    → issues (MODULE-MISMATCH? 否, THIRD-COUNTRY? 是 → HIGH,
               CLAUSE-DEVIATIONS? 否, per-finding for each HIGH finding)
    → evidence (5 条证据链)
    → 上下文包
    → chapters (4 章，LLM 或占位)
    → render: MD + 批注版 DOCX + JSON

        ↓
[返回]
SCCReviewResult {
  overall_rating: "HIGH",
  findings: [5 条],
  module_validation: {is_correct: true, expected: "Module One"},
  chapters: [4 章],
  output_files: {markdown, docx, annotated_docx, findings_json, ...}
}
```

---

## 四、依赖的公共模块

| 模块 | 文件路径 | 作用 |
|------|---------|------|
| 工作流引擎 | `backend/common/workflow/pipeline.py` | `WorkflowPipeline.run()` — 14 步流水线 |
| 工作流模型 | `backend/common/workflow/context_pack.py` | `GenerationContextPack` — 上下文包 |
| 工作流模型 | `backend/common/workflow/issues.py` | `IssueItem` — 合规问题项 |
| 工作流模型 | `backend/common/workflow/facts.py` | `FactItem` — 事实项 |
| 工作流模型 | `backend/common/workflow/evidence.py` | `EvidenceItem` — 证据项 |
| 追踪 | `backend/common/workflow/trace.py` | `dump_model_list()` — 模型序列化 |
| LLM 生成 | `backend/common/llm/module_generator.py` | `generate_chapter()` — 章节生成 + SYSTEM_PROMPTS/CHAPTER_INSTRUCTIONS |
| RAG 检索 | `backend/common/rag/retriever.py` | `retrieve_regulations()` — 法规检索 |
| RAG 编排 | `backend/common/rag/orchestrator.py` | `_retrieve_eu()` — EU 索引路由 |
| 报告渲染 | `backend/common/render/report.py` | `render_markdown_template/render_docx_template/format_date_stamp/safe_filename` |
| 摘要工具 | `backend/common/render/summary.py` | `attach_citations()` / `summarize_for_slot()` |
| DOCX 批注 | `backend/common/render/docx_comments.py` | `DocxComment` + `render_commented_docx()` |
| 附件解析 | `backend/common/storage/file_parser.py` | `FileParser.parse_text()` |
| 任务管理 | `backend/common/tasks/manager.py` | `InMemoryTaskManager` — 异步任务队列 |
| 追踪 | `backend/common/trace/recorder.py` | `TraceRecorder` — 执行记录 |

---

## 五、RAG 与知识库联动

### 5.1 检索链

```
EU_SCCService._retrieve_regulations()
    ↓
retrieve_regulations(query, jurisdiction="eu", path="scc")
    ↓
backend/common/rag/retriever.py
    ↓
RetrievalOrchestrator._retrieve_eu()  ← module="eu_scc"
    ↓
搜索索引:
  workflow_index_eu      ← 过滤 module: "eu_scc"
  legal_index_eu         ← 过滤 module: "eu_scc"
  standard_clause_index_eu ← 过滤 module: "eu_scc" (仅 issue_discovery/clause_compare 阶段)
  template_index_eu      ← 过滤 module: "eu_scc" (仅 report_generation 阶段)
  testcase_index_eu      ← 过滤 module: "eu_scc" (仅 evaluation 阶段)
    ↓
UsagePolicyFilter 过滤 + 去重
    ↓
返回 top_k=5 条法规
```

### 5.2 知识库构建

```
builders_v2.py:
  build_legal_chunks_eu()          → legal_index_eu
  build_workflow_chunks_eu()       → workflow_index_eu (含 WF-EU-SCC-TRANSFER-MAP)
  build_standard_clause_chunks_eu()→ standard_clause_index_eu (含 STD-EU-SCC-ONWARD)
  build_template_chunks_eu()       → template_index_eu
  build_testcase_chunks_eu()       → testcase_index_eu (含 TC-EU-SCC-001)

registry.py:
  eu_scc: production_enabled = True (已启用)
```

### 5.3 LLM 生成配置

`module_generator.py` 中的 `eu_scc`:
- **系统提示**: EU SCC/GDPR 跨境传输审查律师，掌握 GDPR、EU 2021/914、EDPB、Schrems II
- **章节指令**: 4 章，每章有具体的生成要求（文件概要、总体评级、条款发现、法规依据）

---

## 六、质量控制与校验

### 6.1 一致性校验 (`_check_consistency`)

```
1. scc_text 是否过短 (<100 字符) → "SCC document text is too short"
2. issues 中是否有 HIGH/BLOCKER → "recommend legal review before filing"
```

### 6.2 测试覆盖 (11 项全部通过)

| 测试 | 功能 | 预期 |
|------|------|------|
| test_case1_c2c_us_aws_tia_missing | C2C + US AWS + TIA 缺失 | 模块正确, overall=HIGH, 有 TIA/AWS/subproc 发现 |
| test_case2_c2p_india_clause15_weakened | C2P + India + Clause 15 削弱 | 模块正确, overall=HIGH, 有 Clause 15 偏离 + India 第三国发现 |
| test_case3_p2p_wrong_module | P2P + Module Two + See MSA + Serbia | 模块错误 (应为Three), overall=HIGH, 有 module_mismatch + incomplete + subproc 发现 |
| test_parser_extracts_module_type | 解析器模块类型 | Module One |
| test_parser_extracts_clauses | 解析器条款提取 | ≥4 条 clause |
| test_parser_extracts_sub_processors | 解析器子处理者 | AWS 被提取 |
| test_module_validation_controller_controller | C2C 校验 | Module One, is_correct=True |
| test_module_validation_controller_processor | C2P 校验 | Module Two, is_correct=True |
| test_module_validation_mismatch | P2P 错误 Module Two | Module Three, is_correct=False |
| test_clause_comparison_detects_weakening | Clause 15 削弱检测 | deviations_found > 0 |
| test_output_files_generated | 输出文件 | markdown + findings_json |
