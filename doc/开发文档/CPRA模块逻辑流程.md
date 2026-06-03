# CPRA 合规模块 — 全部代码逻辑流程文档

> 模块路径: `backend/modules/cpra/`
> 法律框架: California Privacy Rights Act (CPRA) / CCPA / CPPA Regulations
> 首页: `frontend/src/lib/task-templates.ts` → `us_cpra` (workspaceStyle: `us_cpra`)
> 创建时间: 2026-06-03

---

## 一、总体架构概览

### 1.1 模块定位

CPRA 模块是一个**全景合规评估报告生成器**，功能是：用户提交企业隐私合规信息（结构化或自由文本），系统通过 10 条确定性规则引擎发现合规差距，再通过 LLM 生成 6 章全景合规报告。

### 1.2 执行流程

```
前端用户提交 CPRA 合规评估请求
        │
        ▼
POST /cpra/generate                 (同步)
POST /cpra/generate_async            (异步)
        │
        ▼
CPRAService.generate_report(payload)
        │
        ├─[1] CPRAAttachmentExtractor → 5种附件角色解析
        ├─[2] gap_rules.run_all_rules() → 10条规则引擎
        ├─[3] CPRALegalRetriever.retrieve_all() → 域级RAG法规检索
        ├─[4] _resolve_overall_level() → 总体风险等级
        ├─[5] _extract_attachment_notes() → 附件文本摘要
        ├─[6] _build_enhanced_context() → LLM上下文块
        ├─[7] _generate_chapters_from_context() → 6章报告
        ├─[8] _check_consistency() → 一致性警告
        └─[9] _render() → MD + DOCX + PDF + XLSX + ZIP
        │
        ▼
  CPRAResult
```

### 1.3 架构特点

与 us_14117 不同，CPRA 模块**不使用 WorkflowPipeline**。它在 `service.py` 中直接串联调用各组件，是一个更早期、更直接的服务实现模式。它与 diagnosis 模块同为直接串联模式，但 CPRA 使用 `InMemoryTaskManager` 额外支持异步执行。

---

## 二、逐模块详细逻辑流程

---

### 2.1 `schema.py` — 数据模型层

**文件**: `backend/modules/cpra/schema.py`
**模型总数**: 11 个 Pydantic BaseModel

#### 2.1.1 输入模型

**`CPRAAttachment`** — 上传文件/URL:

```
file_role: Literal["privacy_policy", "rights_sop", "data_map",
                    "vendor_list", "other"]
file_format: Literal["docx", "pdf", "xlsx", "csv", "url", "md", "txt"]
storage_uri: str               ← 文件路径或URL
size_bytes: int | None
checksum_sha256: str | None
```

**`CPRAApplicabilityInfo`** — CPRA 适用性判断:

```
annual_revenue_usd: int        ← 年收入（美元），默认 0
ca_consumer_count: int         ← 加州消费者数量
sell_share_revenue_ratio: float ← 出售/分享数据收入占比
operates_in_california: bool   ← 是否在加州运营
possible_exemptions: list[str] ← HIPAA / GLBA / COPPA / None
```

**`CPRADataItem`** — 单个数据项:

```
category: str                  ← 数据类别名称
is_sensitive: bool             ← 是否敏感个人信息
spi_type: str                  ← SPI类型（14种之一）
source: str                    ← 数据来源
purpose: str                   ← 处理目的
recipient_type: str            ← 接收方类型
retention: str                 ← 保留期限
sale_or_share: bool            ← 是否出售/分享
cross_context_advertising: bool ← 是否用于跨情境广告
```

**`CPRADSRMechanism`** — 消费者权利请求机制:

```
has_web_form: bool             ← 是否提供网页表单
has_email: bool                ← 是否提供邮箱
has_toll_free_phone: bool      ← 是否提供免费电话
# 支持的权利:
access: bool                ← 知情权/访问权
delete: bool                ← 删除权
correct: bool               ← 更正权
opt_out: bool               ← 拒绝出售/分享权
limit_spi: bool             ← 限制SPI使用权
response_days: int          ← 响应天数
is_easy_to_find: bool       ← 是否容易找到
```

**`CPRAVendorInfo`** — 第三方信息:

```
name: str
vendor_type: str  ← service_provider | contractor | ad_network |
                    data_broker | analytics | other
receives_pi: bool          ← 接收个人信息
receives_spi: bool         ← 接收敏感个人信息
sale_or_share: bool        ← 是否涉及出售/分享
has_dpa: bool              ← 是否有数据处理协议
# DPA条件:
prohibits_sale_share       ← 是否禁止进一步出售/分享
includes_audit_right       ← 是否包含审计权
requires_deletion          ← 是否要求终止后删除
specifies_purpose          ← 是否明确处理目的
```

**`CPRAConsentUI`** — 同意界面:

```
has_cookie_banner           ← 是否有Cookie横幅
accept_prominent            ← "接受"按钮是否突出
reject_equally_prominent    ← "拒绝"按钮是否同等突出
preselected_consent         ← 是否有预选同意
bundled_consent             ← 是否有捆绑同意
refusal_more_steps          ← 拒绝是否比接受需要更多步骤
confusing_language           ← 是否有混淆性语言
```

**`CPRARequest`** — 主请求（旧版自由文本 + 新版结构化共存）:

```
# 旧版自由文本字段:
business_model: str              ← 商业模式描述
data_lifecycle: str              ← 数据生命周期
notice_and_consent: str          ← 告知与同意实践
consumer_rights_process: str     ← 消费者权利处理流程
opt_out_and_sale_sharing: str    ← Opt-out与出售/分享实践
vendor_management: str           ← 供应商管理
attachments: list[CPRAAttachment] ← 最少1个
company_name: str

# 新版结构化字段（可选）:
applicability: CPRAApplicabilityInfo | None
data_items: list[CPRADataItem]
dsr_mechanism: CPRADSRMechanism | None
vendors: list[CPRAVendorInfo]
consent_ui: CPRAConsentUI | None
```

#### 2.1.2 输出模型

**`CPRAGapItem`** — 单条合规差距:

```
domain: str         ← applicability | notice | data_mapping | dsr |
                      opt_out | spi | vendor | dark_patterns |
                      exemptions | business_role
risk_level: str      ← HIGH | MEDIUM | LOW
gap: str             ← 差距描述
legal_basis: str     ← 法律依据
recommendation: str  ← 整改建议
phase: str           ← short_term | mid_term | long_term
evidence_source: str ← 附件路径或 "structured_input"
citations: list[str] ← RAG 检索到的法规引用
```

**`CPRAChapter`** — 报告章节:

```
chapter_no: int         ← 1–6
title: str
content: str
citations: list[str]
risk_level: str
```

**`CPRAResult`** — 最终结果:

```
report_path: str         ← 主报告路径
output_files: dict[str, str]  ← MD/DOCX/PDF/XLSX/ZIP 路径映射
company_name: str
risk_level: str          ← HIGH / MEDIUM / LOW
gap_items: list[CPRAGapItem]
chapters: list[CPRAChapter]
consistency_issues: list[str]
attachment_notes: list[str]
```

**`CPRAAsyncAccepted`** / **`CPRAAsyncStatus`** — 异步模型（与其他模块模式一致）。

---

### 2.2 `attachment_extractor.py` — 附件解析器

**文件**: `backend/modules/cpra/attachment_extractor.py`
**核心类**: `CPRAAttachmentExtractor`

#### 2.2.1 5 种附件角色解析逻辑

**角色 1: `privacy_policy` — 隐私政策**

使用正则模式提取 8 个二进制标志（同时支持中英文关键词）:

```
检测项              正则/keyword 示例
---------------------------------------------------------
类别披露:           "categories of personal information" |
                    "收集的个人信息类别" | "我们收集"
目的披露:           "business or commercial purpose" |
                    "使用目的" | "我们使用"
保留期披露:         "retention" | "保留" | "保存"
SPI声明:            "sensitive personal information" |
                    "敏感个人信息"
Opt-out链接:        "opt.out" | "do not sell" |
                    "拒绝出售" | "global privacy control"
限制SPI链接:        "limit the use" | "限制使用" |
                    "sensitive personal information link"
DSR说明:            "right to know" | "right to delete" |
                    "访问权" | "删除权"
免费电话:           "toll.free" | "phone" | "电话" |
                    "400." | "800."
```

返回: `{category_disclosed, purpose_disclosed, retention_disclosed, spi_stated, opt_out_link, spi_limit_link, dsr_explained_correctly, has_toll_free_number}`

**角色 2: `rights_sop` — 消费者权利SOP**

```
提取:
  response_days:   r"(\d+)\s*(?:天|days|business days|business days)"
  access:          文本是否提及 "right to know" / "访问权" / "知情权"
  delete:          文本是否提及 "删除"
  correct:         文本是否提及 "更正" / "correct"
  opt_out:         文本是否提及 "opt.out" / "拒绝" / "global privacy control"
  verification:    文本是否提及 "验证" / "verify" / "verification"
  extension:       文本是否提及 "延期" / "extension" / "extend"
```

**角色 3: `data_map` — 数据映射**

用 7 条正则提取数据类别:

```
personal_identifier:     r"(?:name|姓名|email|邮箱|phone|电话|address|地址|SSN|社保|ID)"
health_data:             r"(?:health|健康|medical|医疗|diagnos|诊断|patient|患者)"
biometric_information:   r"(?:biometric|生物|fingerprint|指纹|facial|面部)"
precise_geolocation:     r"(?:geolocation|地理位置|GPS|latitude|经度|longitude|纬度)"
financial_account:       r"(?:financial|金融|bank|银行|credit|信用|account number|账号)"
account_credentials:     r"(?:password|密码|login|登录|credential|凭据)"
racial_or_ethnic_origin: r"(?:race|种族|ethnic|族裔|民族|肤色|color)"
```

同时提取: 用途、接收方、保留期限。统计总数和数量。

**角色 4: `vendor_list` — 供应商名单**

```
提取:
  vendor_names:  逐行解析供应商名称
  vendor_count:  统计
  mentions_dpa:  是否提及 "DPA" / "数据处理协议" / "data processing agreement"
  mentions_service_provider: 是否提及 "service provider"
  mentions_contractor:       是否提及 "contractor"
```

**角色 5: `other` / URL**

```
URL:  → {url_only: true, file_role: "other"}
其他: → FileParser 尝试 parse_text()，失败 → {parse_error: true}
```

#### 2.2.2 公共接口

```python
extractor = CPRAAttachmentExtractor()
result = extractor.extract(attachment)  # CPRAAttachment → dict
```

---

### 2.3 `gap_rules.py` — 10 条合规差距规则引擎

**文件**: `backend/modules/cpra/gap_rules.py`
**核心函数**: `run_all_rules(applicability, business_text, notice_text, dsr, dsr_text, opt_out_text, data_items, vendors, consent_ui) → list[CPRAGapItem]`

#### 2.3.1 全局常量

```
_HIGH_RISK_PURPOSES = {"advertising", "marketing", "insurance_recommendation",
                        "targeted_advertising", "cross_context_advertising",
                        "third_party_sale", "automated_decision_making",
                        "profiling"}
    ↑ 这些目的 + SPI 使用 → HIGH 风险

_SPI_CATEGORIES = {
    "government_id", "financial_account", "precise_geolocation",
    "racial_ethnic_origin", "religious_beliefs", "union_membership",
    "health_data", "sex_life_orientation", "genetic_data",
    "biometric_data", "contents_of_mail", "contents_of_text",
    "unique_biometric_data", "personal_data_of_children"
}
    ↑ 14 种 CPRA 敏感个人信息类别
```

#### 2.3.2 10 条规则详解

**规则 1: `check_applicability(applicability, business_text)`**

```
评估 CPRA 是否适用。

输入: applicability (CPRAApplicabilityInfo | None) + business_text (str)

逻辑:
1. 如果 applicability 为 None 且 business_text 为空 → LOW "无法确定适用性"
2. 检查强制阈值:
   - annual_revenue > 25,000,000 → MEDIUM (高度可能适用)
   - ca_consumer_count >= 100,000 → MEDIUM
   - sell_share_revenue_ratio >= 0.5 → MEDIUM
3. 如果 operates_in_california = True 但没有达到阈值 → LOW
4. 检查豁免:
   - HIPAA 适用 → LOW (部分豁免)
   - GLBA 适用 → LOW (部分豁免)
   - COPPA 适用 → LOW (部分豁免)

输出: CPRAGapItem(domain="applicability", risk_level, gap, legal_basis="CPRA §1798.140", ...)
```

**规则 2: `check_business_role(business_text, vendors)`**

```
判断企业在 CPRA 下的角色（业务方/服务提供商/承包商/第三方）。

输入: business_text (str) + vendors (list[CPRAVendorInfo] | None)

逻辑:
1. 如果有供应商 (vendors) 且它们有CPRA结构:
   - 如果任何 vendor 是 service_provider 但没有 DPA → MEDIUM
   - 如果任何 vendor 是 contractor 且 receives_pi 但没有 specifies_purpose → MEDIUM
   - 如果任何 vendor 是 ad_network + data_broker 但没有 opt-out → HIGH
2. 文本关键词检测:
   - "服务提供商" / "service provider" / "处理者" → LOW (已识别)
   - "独立决定目的" / "determines purposes" → MEDIUM (可能是业务方)
3. 如果没有结构化 vendors 且文本为空 → MEDIUM "无法确定角色"

输出: CPRAGapItem(domain="business_role", ...)
```

**规则 3: `check_notice(notice_text)`**

```
评估 CPRA 告知义务履行情况。

输入: notice_text (str)

逻辑:
1. 通知缺失检测:
   - 关键词 "notice at collection" / "告知" / "privacy notice" 不存在 → HIGH
2. 内容完整性检测 (如通知存在):
   - 缺少 "categories" / "类别" → MEDIUM
   - 缺少 "purpose" / "目的" → MEDIUM
   - 缺少 "retention" / "保留" → MEDIUM
   - 缺少 "sale or share" / "出售或分享" / "opt out" → MEDIUM
3. 如果全部满足 → LOW "告知内容完整"

输出: CPRAGapItem(domain="notice", ...)
    legal_basis = "CPRA §1798.100"
```

**规则 4: `check_data_mapping(data_items)`**

```
评估数据映射的完整性和合规性。

输入: data_items (list[CPRADataItem] | None)

逻辑:
如果 data_items 存在:
  1. SPI + 高风险目的:
     任何 SPI 类别 + 在 _HIGH_RISK_PURPOSES 中的目的 → HIGH
     (e.g. 健康数据用于广告 = HIGH)
  2. SPI + 出售/分享给 "ad_network" / "data_broker" → HIGH
  3. 保留 > 7年 (文本中包含 "7年" / "7 years" / "permanent") → MEDIUM
  4. 数据类别 < 3 且用途模糊 → MEDIUM

如果 data_items 不存在 (旧版自由文本):
  通过数据映射附件中的 extracted Facts 检查

输出: CPRAGapItem(domain="data_mapping", ...)
    legal_basis = "CPRA §1798.100, §1798.106"
```

**规则 5: `check_dsr(dsr, dsr_text, has_spi)`**

```
评估消费者权利请求(DSR)机制。

输入: dsr (CPRADSRMechanism | None) + dsr_text (str) + has_spi (bool)

逻辑:
结构化检查 (如果 dsr 存在):
  1. 渠道数量 < 2 (只有 web_form 或 email 之一) → MEDIUM
  2. 没有免费电话 → MEDIUM (CPRA 要求至少一个免费电话号码)
  3. is_easy_to_find = False → MEDIUM
  4. response_days > 45 → HIGH
  5. 没有 opt_out 支持 → HIGH
  6. has_spi=True 但没有 limit_spi 支持 → HIGH

文本检查 (如果 dsr 不存在):
  1. "right to know" / "right to delete" 缺失 → MEDIUM
  2. "45 days" / "45天" 缺失 → MEDIUM

输出: CPRAGapItem(domain="dsr", ...)
    legal_basis = "CPRA §1798.130, §1798.140"
```

**规则 6: `check_opt_out(opt_out_text, data_items, dsr)`**

```
评估 Opt-Out 机制的合规性。

输入: opt_out_text (str) + data_items (list | None) + dsr (CPRADSRMechanism | None)

逻辑:
1. 有出售/分享但没有 Opt-Out:
   检查是否有 data_items 标记为 sale_or_share=True
   如果没有 opt_out 机制 → HIGH
2. 跨情境广告 + 没有标准DNS:
   任何 cross_context_advertising=True 但没有 opt_out → HIGH
3. Opt-out 链接检查:
   - 包含 "global privacy control" / "GPC" → LOW
   - 包含 "opt out" / "opt-out" → LOW
   - 包含 "do not sell" / "privacy choices" → MEDIUM (非标准化)
4. 文本检查:
   - 没有 "do not sell" / "opt out" / "opt-out" → HIGH

输出: CPRAGapItem(domain="opt_out", ...)
    legal_basis = "CPRA §1798.120, §1798.135"
```

**规则 7: `check_spi(data_items, dsr, consent_ui)`**

```
评估敏感个人信息(SPI)处理合规性。

输入: data_items (list | None) + dsr (CPRADSRMechanism | None) + consent_ui (CPRAConsentUI | None)

逻辑:
1. SPI 收集但未声明:
   检测 data_items 中有 is_sensitive=True → MEDIUM
2. SPI + 高风险目的:
   SPI + _HIGH_RISK_PURPOSES 目的 → HIGH
3. SPI + 营销使用超出原始目的 → HIGH
4. 没有 limit_spi 机制 → HIGH
   (dsr.limit_spi = False 或 dsr = None)
5. 暗模式同意检测 (如果有 consent_ui):
   - preselected_consent = True → HIGH (预选同意)
   - bundled_consent = True → HIGH (捆绑同意)
   - reject_equally_prominent = False → MEDIUM (拒绝不突出)
   - refusal_more_steps = True → MEDIUM (拒绝步骤更多)
   - confusing_language = True → MEDIUM (混淆语言)

输出: CPRAGapItem(domain="spi", ...)
    legal_basis = "CPRA §1798.121, §1798.185"
```

**规则 8: `check_vendor(vendors)`**

```
评估第三方供应商管理合规性。

输入: vendors (list[CPRAVendorInfo] | None)

逻辑 (如果 vendors 存在):
  1. receives_pi=True 但没有 DPA → MEDIUM
  2. receives_spi=True 但没有 DPA → HIGH
     receives_spi + DPA 但没有 audit_right → HIGH
  3. sale_or_share=True + DPA 但没有 prohibit_sale_share → HIGH
  4. ad_network/analytics/data_broker 类型:
     - 没有 prohibits_sale_share → HIGH
     - 没有 requires_deletion → HIGH
     - sale_or_share=True 但没有 opt-out 合同条款 → HIGH

如果 vendors 不存在或为空:
  → MEDIUM "无法评估供应商管理"

输出: CPRAGapItem(domain="vendor", ...)
    legal_basis = "CPRA §1798.140, §1798.145"
```

**规则 9: `check_dark_patterns(consent_ui)`**

```
评估暗模式同意设计。

输入: consent_ui (CPRAConsentUI | None)

如果 consent_ui 存在:
  preselected_consent = True → HIGH "预选同意违反CPPA §7004"
  bundled_consent = True → HIGH "捆绑同意不被允许"
  reject_equally_prominent = False → MEDIUM "拒绝选项与接受不对等"
  refusal_more_steps = True → MEDIUM "拒绝同意比接受需要更多步骤"
  confusing_language = True → MEDIUM "语言表述可能导致混淆"

如果 consent_ui 不存在:
  → LOW "未提供同意界面信息，无法评估暗模式"

输出: CPRAGapItem(domain="dark_patterns", ...)
    legal_basis = "CPPA Regulations §7004"
```

**规则 10: `check_exemptions(applicability, data_items)`**

```
评估潜在的CPRA豁免是否合理。

输入: applicability (CPRAApplicabilityInfo | None) + data_items (list | None)

逻辑:
1. SPI 包含 health_data 但适用性声明 HIPAA 豁免 → 记录为合理豁免 (LOW)
2. SPI 包含 financial_account 但适用性声明 GLBA 豁免 → 记录为合理豁免 (LOW)
3. 声明了豁免但没有对应的SPI类型支持 → MEDIUM (豁免可能不合理)

输出: CPRAGapItem(domain="exemptions", ...)
    legal_basis = "CPRA §1798.145"
```

#### 2.3.3 `run_all_rules()` 聚合器

```python
def run_all_rules(...) -> list[CPRAGapItem]:
    gap_items = []
    gap_items.extend(check_applicability(...) or [])
    gap_items.extend(check_business_role(...) or [])
    gap_items.extend(check_notice(...) or [])
    gap_items.extend(check_data_mapping(...) or [])
    gap_items.extend(check_dsr(...) or [])
    gap_items.extend(check_opt_out(...) or [])
    gap_items.extend(check_spi(...) or [])
    gap_items.extend(check_vendor(...) or [])
    gap_items.extend(check_dark_patterns(...) or [])
    gap_items.extend(check_exemptions(...) or [])
    return gap_items
```

返回: 所有非 None 的差距项列表。

#### 2.3.4 旧版回退规则

当 `run_all_rules()` 未产生任何结果（无结构化输入）时，`service.py` 调用 `_build_legacy_gap_items()`。此函数使用 4 条基于关键词的规则:

```
1. 通知缺失: 文本不含 "privacy notice" / "隐私政策" → HIGH
2. DSR SLA 不明确: 文本不含 "45 days" / "45天" / "response time" → MEDIUM
3. 出售/分享 + 没有 opt-out: 文本含 "sale" / "share" / "出售" / "分享"
   但不含 "opt out" / "opt-out" → HIGH
4. 第三方 + 没有 DPA: 文本含 "vendor" / "third party" / "第三方" / "供应商"
   但不含 "DPA" / "data processing agreement" → MEDIUM

如果以上都不触发:
  返回 [LOW "未发现明显合规缺口，但仍需人工审查"]
```

---

### 2.4 `legal_retriever.py` — 法律检索器

**文件**: `backend/modules/cpra/legal_retriever.py`
**核心类**: `CPRALegalRetriever`

#### 2.4.1 域 → 查询映射

```python
_CPRA_DOMAIN_QUERIES = {
    "applicability": "CPRA business threshold annual revenue 25 million consumers Section 1798.140",
    "dsr": "CPRA consumer rights request methods 45 days toll-free number Section 1798.130",
    "opt_out": "CPRA do not sell or share global privacy control opt-out link Section 1798.120",
    "spi": "CPRA sensitive personal information limit use Section 1798.121",
    "vendor": "CPRA service provider contractor contract requirements DPA audit delete Section 1798.140",
    "dark_patterns": "CPPA dark patterns consent regulations Section 7004",
    "exemptions": "CPRA HIPAA GLBA exemption scope Section 1798.145",
    "notice": "CPRA notice at collection categories purposes retention Section 1798.100",
    "data_mapping": "CPRA data minimization purpose limitation retention Section 1798.100",
    "business_role": "CPRA business service provider contractor third party definitions",
}
```

#### 2.4.2 检索方法

```python
def retrieve(domain: str) -> list[dict]:
    query = _CPRA_DOMAIN_QUERIES.get(domain, f"CPRA {domain}")
    docs = retrieve_regulations(query, top_k=3, jurisdiction="us", path="all")
    return [{"source": f"《{d.title}》{d.article}", "snippet": d.content[:200]}
            for d in docs]

def retrieve_all(domains: list[str]) -> dict[str, list[dict]]:
    return {domain: self.retrieve(domain) for domain in domains}
```

`retrieve_all()` 在 `service.py` 中被调用，每个域检索 3 条法规依据，最多 2 条附加到对应的 `CPRAGapItem` 上。

---

### 2.5 `service.py` — 核心编排服务

**文件**: `backend/modules/cpra/service.py`
**核心类**: `CPRAService`

#### 2.5.1 构造函数

```python
class CPRAService:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client or LLMClient(get_settings())
        self.extractor = CPRAAttachmentExtractor()
        self.legal_retriever = CPRALegalRetriever()
        self.tasks = InMemoryTaskManager(module="cpra")
```

#### 2.5.2 主入口 `generate_report(payload) → CPRAResult`

```
── 步骤 1: 附件解析 ──
attachment_facts = []
for att in payload.attachments:
    attachment_facts.append(self.extractor.extract(att))

── 步骤 2: 规则引擎 ──
gap_items = run_all_rules(
    payload.applicability,
    payload.business_model,         # 旧版自由文本
    payload.notice_and_consent,     # 旧版自由文本
    payload.dsr_mechanism,          # 新版结构化
    payload.consumer_rights_process,# 旧版自由文本
    payload.opt_out_and_sale_sharing,# 旧版自由文本
    payload.data_items,             # 新版结构化
    payload.vendors,                # 新版结构化
    payload.consent_ui,             # 新版结构化
)

# 旧版回退
if not gap_items and payload.applicability is None and not payload.data_items:
    gap_items = self._build_legacy_gap_items(payload)

── 步骤 3: 域级 RAG 检索 ──
# 收集所有 HIGH/MEDIUM 差距的域
domains = list(set(g.domain for g in gap_items if g.risk_level in ("HIGH", "MEDIUM")))
domain_citations = self.legal_retriever.retrieve_all(domains[:5])

# 将引用附加到每个 gap_item
for g in gap_items:
    g.citations = [c["source"] for c in domain_citations.get(g.domain, [])[:2]]

── 步骤 4: 整体评级 ──
risk_level = self._resolve_overall_level(gap_items)
# 存在 HIGH → HIGH
# 存在 MEDIUM → MEDIUM
# 否则 → LOW

── 步骤 5: 附件摘要 ──
attachment_notes = self._extract_attachment_notes(payload)
# 对每个文件调用 FileParser.parse_text()
# 取前 160 字符，失败记录 [parse skipped]

── 步骤 6: 构建 LLM 上下文 ──
context_block = self._build_enhanced_context(payload, gap_items, risk_level)
# 组装包含企业信息、结构化事实、差距摘要、风险等级的文本块

── 步骤 7: LLM 章节生成 ──
# 6 章标题:
#   执行摘要
#   企业适用性与范围
#   数据处理活动合规分析
#   消费者权利保障评估
#   敏感信息与第三方管理
#   行动清单与优先级

all_citations = []
for g in gap_items:
    all_citations.extend(g.citations)

chapters = self._generate_chapters_from_context(context_block, risk_level, all_citations[:6])

── 步骤 8: 一致性检查 ──
issues = self._check_consistency(payload, gap_items, attachment_facts)
# 缺少隐私政策附件 → "隐私政策附件缺失"
# 存在 HIGH 差距 → "存在高风险项，建议立即整改"

── 步骤 9: 渲染 ──
outputs = self._render(payload, chapters, gap_items, attachment_notes)
# 生成 5 个文件:
#   1. {company}_CPRA_合规全景报告_草案_{date}.md    (模板渲染)
#   2. {company}_CPRA_合规全景报告_草案_{date}.docx  (模板渲染)
#   3. {company}_CPRA_合规全景报告_草案_{date}.pdf   (章节渲染)
#   4. {company}_CPRA_合规全景报告_草案_{date}.xlsx  (差距项表格)
#   5. {company}_CPRA_合规全景报告_草案_{date}.zip   (打包以上全部)

return CPRAResult(
    report_path = outputs["docx"],
    output_files = outputs,
    company_name = payload.company_name,
    risk_level = risk_level,
    gap_items = gap_items,
    chapters = chapters,
    consistency_issues = issues,
    attachment_notes = attachment_notes,
)
```

#### 2.5.3 模板映射 `_build_template_mapping()`

构建 DOCX/MD 模板的 `{{key}}` → value 映射:

```
current_state:
  每个差距项的逐条描述 + 域 + 风险等级

cpra_mapping:
  企业信息、适用性结论、数据项列表、DSR渠道列表

gaps_and_risks:
  差距清单表（域、等级、差距描述、法律依据、建议、阶段）

remediation_roadmap:
  按短期/中期/长期分组的整改建议

final_conclusion:
  总体结论文字（高风险→"建议立即启动合规整改"、
                中风险→"建议制定整改路线图"、
                低风险→"当前基本合规"）
```

#### 2.5.4 异步 API

```python
submit_async     → InMemoryTaskManager.submit(generate_report)
get_async_status → InMemoryTaskManager.get_or_raise(task_id)
retry_async      → InMemoryTaskManager.retry(task_id)
cancel_async     → InMemoryTaskManager.cancel(task_id)
```

---

### 2.6 `router.py` — API 端点

**文件**: `backend/modules/cpra/router.py`

4 个端点，标准模块模式:

```
router = APIRouter(tags=["cpra"])
service = CPRAService()
TASK_OWNERS: dict[str, str] = {}  # 内存任务归属表

端点:
  POST   /cpra/generate              → 同步生成 + 注册制品
  POST   /cpra/generate_async        → 异步提交 + 记录属主
  GET    /cpra/tasks/{task_id}       → 轮询状态 + 完成后注册制品
  POST   /cpra/tasks/{task_id}/retry → 重试失败任务
```

**路由注册** (`backend/main.py`):
```python
from backend.modules.cpra.router import router as cpra_router
app.include_router(cpra_router, prefix="/api/v1")
```

---

### 2.7 LLM 集成 (`module_generator.py`)

#### 2.7.1 系统提示 (cpra)

```
你是一名专注于加州隐私合规的资深律师，
深度掌握CPRA/CCPA、CPPA执法实践及加州隐私保护局规章。
请按照CPRA合规审查框架，用专业中文评估企业数据处理活动的合规状态，
识别差距并给出优先级整改建议。
```

#### 2.7.2 6 章指令

| 章节 | 指令 |
|------|------|
| 执行摘要 | CPRA适用性结论、主要合规差距数量和严重程度、3项以内的关键行动 |
| 企业适用性与范围 | CPRA适用性判断依据、涉及的加州居民PI范围、SPI识别和分类 |
| 数据处理活动合规分析 | 数据生命周期合规审查、最小化和目的限制合规情况、保留政策合规性 |
| 消费者权利保障评估 | 知情权（隐私政策合规）、删除权/更正权实现机制、拒绝出售/共享权入口、SPI限制处理权 |
| 敏感信息与第三方管理 | SPI处理合规、第三方服务商合同条款审查、数据经纪商登记要求 |
| 行动清单与优先级 | 按HIGH/MEDIUM/LOW列出整改事项，每项包含问题描述、法律依据、整改方案、完成时间 |

---

## 三、端到端完整数据流

以 **FitLife AI 健康应用** 为例（含结构化输入）:

```
[用户提交]
POST /cpra/generate
{
  "company_name": "FitLife AI",
  "business_model": "健康健身应用，通过AI算法提供个性化健身和营养计划",
  "data_lifecycle": "收集健康数据、生物识别数据、位置数据用于分析...",
  "notice_and_consent": "隐私政策中说明了数据收集，但同意流程为预选+捆绑",
  "consumer_rights_process": "未提供opt-out或SPI限制机制",
  "opt_out_and_sale_sharing": "将健康数据分享给广告平台和保险公司用于推荐",
  "vendor_management": "多个第三方广告和分析供应商，无标准DPA",
  "applicability": {
    "annual_revenue_usd": 15000000,
    "ca_consumer_count": 80000,
    "sell_share_revenue_ratio": 0.3,
    "operates_in_california": true
  },
  "data_items": [
    {"category": "健康数据", "is_sensitive": true, "spi_type": "health_data",
     "purpose": "insurance_recommendation", "sale_or_share": true,
     "recipient_type": "ad_network"},
    {"category": "精确位置", "is_sensitive": true, "spi_type": "precise_geolocation",
     "purpose": "advertising", "sale_or_share": true},
    {"category": "生物识别", "is_sensitive": true, "spi_type": "biometric_data",
     "purpose": "profiling"}
  ],
  "consent_ui": {
    "preselected_consent": true,
    "bundled_consent": true,
    "reject_equally_prominent": false
  },
  "vendors": [
    {"name": "AdNetwork Inc", "vendor_type": "ad_network",
     "receives_spi": true, "sale_or_share": true, "has_dpa": false}
  ],
  "attachments": [...]
}

        ↓

CPRAService.generate_report(payload)

[1] extractor.extract() × N attachments
    → 隐私政策附件: categories=yes, purpose=yes, opt_out=no, spi_stated=yes

[2] run_all_rules():
    check_applicability:
      annual_revenue=1500万<2500万, consumers=8万<10万 → LOW (可能适用)
    check_business_role:
      ad_network + 无DPA → MEDIUM
    check_notice:
      告知存在 → LOW
    check_data_mapping:
      健康数据(spi) + insurance_recommendation(high_risk) → HIGH
      位置数据(spi) + advertising(high_risk) → HIGH
      出售/分享给 ad_network → HIGH
    check_dsr:
      无opt-out支持 → HIGH
      无limit_spi → HIGH
    check_opt_out:
      出售/分享但没有opt-out → HIGH
    check_spi:
      SPI + 高风险目的 → HIGH
      预选+捆绑+拒绝不突出 → HIGH
    check_vendor:
      receives_spi + 无DPA → HIGH
      ad_network + sale_or_share + 无DPA → HIGH
    check_dark_patterns:
      预选→HIGH, 捆绑→HIGH, 拒绝不突出→MEDIUM
    → 返回 10+ 条 gap_items

[3] legal_retriever.retrieve_all(["data_mapping","dsr","opt_out","spi","vendor"])
    → 每个域检索3条CPRA法规

[4] _resolve_overall_level():
    存在HIGH → HIGH

[5] _extract_attachment_notes() → 各附件前160字符

[6] _build_enhanced_context() → LLM上下文块

[7] _generate_chapters_from_context() → 6章LLM报告

[8] _check_consistency() → "存在高风险项，建议立即整改"

[9] _render():
    → .md + .docx + .pdf + .xlsx + .zip

[返回]
CPRAResult {
  risk_level: "HIGH",
  gap_items: [10+条],
  chapters: [6章],
  output_files: {markdown, docx, pdf, xlsx, zip}
}
```

---

## 四、前文提到的三个测试案例

### 案例 1: TrendyGoods.com (电商平台)

```
年收入: 3000万 (触发适用性阈值)
数据项: 客户名称、邮箱、购买历史 (→ ad_network 分享)
同意界面: Cookie横幅 → 接受突出/拒绝不突出
预期: 至少 4/6 模式匹配
  - applicability: MEDIUM (收入超阈值)
  - data_mapping: MEDIUM (分享到ad_network)
  - opt_out: MEDIUM (可能缺少opt-out)
  - dark_patterns: MEDIUM (拒绝不突出)
```

### 案例 2: DataFlow Analytics (SaaS)

```
年收入: 1500万 (未达阈值)
消费者数: 12万 (触发阈值)
角色: 服务提供商（处理客户数据）
预期: 至少 3/4 模式匹配
  - applicability: MEDIUM (消费者数超阈值)
  - business_role: MEDIUM (需验证DPA)
  - notice: MEDIUM (数据处理者通知义务)
```

### 案例 3: FitLife AI (健康应用)

```
年收入: 未提供
SPI: 健康数据、生物识别、精确位置
目的: 保险推荐、广告
同意: 预选+捆绑
供应商: 无DPA
预期: 至少 5/7 模式匹配
  - data_mapping: HIGH (SPI+高风险目的)
  - spi: HIGH (SPI+营销+无限制)
  - vendor: HIGH (SPI+无DPA)
  - dark_patterns: HIGH (预选+捆绑)
  - opt_out: HIGH (出售但无opt-out)
```

---

## 五、依赖的公共模块

| 模块 | 文件路径 | 作用 |
|------|---------|------|
| LLM 客户端 | `backend/common/llm/client.py` | `LLMClient.chat()` — LLM 调用 |
| LLM 生成 | `backend/common/llm/module_generator.py` | `generate_chapter()` — 章节生成 |
| RAG 检索 | `backend/common/rag/retriever.py` | `retrieve_regulations()` — 法规检索 |
| 报告渲染 | `backend/common/render/report.py` | `render_markdown_template/render_docx_template/format_date_stamp/safe_filename` |
| 摘要工具 | `backend/common/render/summary.py` | `attach_citations() / summarize_for_slot()` |
| PDF 渲染 | `backend/common/render/artifacts.py` | `render_pdf_report() / render_simple_xlsx() / bundle_files()` |
| 附件解析 | `backend/common/storage/file_parser.py` | `FileParser.parse_text()` |
| 任务管理 | `backend/common/tasks/manager.py` | `InMemoryTaskManager` — 异步任务队列 |
| 制品注册 | `backend/api/artifact_registry.py` | `register_module_result_artifacts()` |

**CPRA 模块不依赖**:
- `WorkflowPipeline` — 使用直接串联调用
- `GenerationContextPack` / `FactItem` / `IssueItem` / `EvidenceItem` — 不适用
- `TreaceRecorder` — 不使用 trace

---

## 六、前端集成

```
domain.ts:
  ModuleKey: "cpra"
  WorkspaceStyleKey: "us_cpra"

task-templates.ts:
  id: "us_cpra", jurisdiction: "US", module: "cpra",
  title: "CPRA 合规", subtitle: "完成数据映射、告知与合同机制检查"

module-adapter.ts:
  syncEndpoint: "/api/v1/cpra/generate"
  asyncSubmitEndpoint: "/api/v1/cpra/generate_async"
  asyncStatusEndpoint: "/api/v1/cpra/tasks/{taskId}"

demoPayloads.ts:
  business_model: "SaaS 营销自动化平台"
  notice_and_consent: "隐私告知缺失"
  opt_out_and_sale_sharing: "存在共享但无opt-out"
  vendor_management: "供应商管理未体现DPA"
```

---

## 七、测试覆盖

| 测试 | 类型 | 验证点 |
|------|------|--------|
| test_service.py | 集成 | 旧版自由文本→生成docx/xlsx→gap_items非空 |
| test_async_api.py | 集成 | 异步提交→轮询→完成→xlsx存在 |
| test_gap_rules.py 案例1 | 规则 | TrendyGoods (电商) → ≥4个模式匹配 |
| test_gap_rules.py 案例2 | 规则 | DataFlow (SaaS) → ≥3个模式匹配 |
| test_gap_rules.py 案例3 | 规则 | FitLife AI (健康) → ≥5个模式匹配 |

---

## 八、关键设计特征

1. **双模式输入**: 旧版自由文本字段 + 新版结构化字段共存，规则引擎优先使用结构化数据，无结构化时回退到旧版规则
2. **10 条模块化规则**: 每条规则独立运行，按域归类（applicability/notice/data_mapping/dsr/opt_out/spi/vendor/dark_patterns/exemptions/business_role）
3. **域级 RAG**: 对 HIGH/MEDIUM 差距所涉及的域进行精准法规检索，每条差距附带最多 2 条法规引用
4. **直接串联架构**: 不使用 WorkflowPipeline，服务直接串联所有组件
5. **CPPA 暗模式检测**: 通过结构化 `CPRAConsentUI` 字段检测预选同意、捆绑同意、不平衡设计、混淆语言等暗模式
6. **附件结构化提取**: 5 种角色（隐私政策/SOP/数据映射/供应商名单/其他）的正则解析，产出可被规则引擎消费的结构化标志
