下面直接给你一个**可落地的 Agent 接入方案**。核心判断是：**CPRA 当前已经有 10 条规则引擎，不应该用 Agent 替代规则；Agent 应该放在“事实抽取、复杂推理、证据匹配、冲突复核、报告增强”这些规则难以稳定覆盖的位置。**

当前模块已经从旧版 4 条规则升级到“附件解析 + 10 条规则 + 域级 RAG + LLM 生成 6 章报告”的结构，`service.py` 主流程是先解析附件，再跑 `gap_rules.run_all_rules()`，再按 gap 域做法规检索，最后生成报告。 
所以 Agent 的最佳接入点不是再加一个“万能判断器”，而是加在规则引擎前后，增强事实质量和结论可信度。

---

# 一、总架构：Agent 应该放在规则前、规则中、规则后

建议形成这个流程：

```text
用户输入 / 附件 / URL / UI信息
        ↓
[Agent 1] 事实抽取 Agent
        ↓
结构化事实包 FactPack
        ↓
[Agent 2] 角色与适用性 Agent
        ↓
增强 applicability / business_role
        ↓
[确定性规则引擎] gap_rules.run_all_rules()
        ↓
初步 gap_items
        ↓
[Agent 3] 复杂场景复核 Agent
        ↓
补充/修正 gap_items
        ↓
[Agent 4] 法规证据匹配 Agent
        ↓
gap_items + 精准法规依据 + snippet
        ↓
[Agent 5] 整改方案 Agent
        ↓
整改任务、优先级、责任模块、完成路径
        ↓
LLM 生成 6 章报告
        ↓
[Agent 6] 一致性审校 Agent
        ↓
最终报告
```

一句话：**规则负责稳定判断，Agent 负责把非结构化材料变成规则可用事实，并处理跨模块、跨材料、跨法律依据的复杂推理。**

---

# 二、最应该加的 Agent 1：附件事实抽取 Agent

## 1. 当前问题

当前 `CPRAAttachmentExtractor` 已经可以按 5 种附件角色提取信息，包括隐私政策、消费者权利 SOP、数据地图、供应商名单和其他文件。隐私政策会检测类别披露、目的披露、保留期披露、SPI 声明、Opt-out 链接、限制 SPI 链接、DSR 说明和免费电话等标志；供应商名单会提取 vendor_names、vendor_count、mentions_dpa、mentions_service_provider、mentions_contractor 等字段。 

这比旧版“只取前 160 字展示”已经好很多，但本质仍是**正则和关键词提取**。它适合发现显性关键词，不适合处理复杂法律文本。

比如隐私政策中可能写：

```text
We may disclose identifiers and internet activity information to advertising partners for analytics and personalized content.
```

它未必直接出现 “sell” 或 “share”，但在 CPRA 下可能仍涉及共享或跨情境行为广告。

再比如合同里可能有 DPA，但 DPA 条款没有：

```text
禁止出售/共享
协助 DSR
删除或返还
审计权
处理目的限制
尊重 opt-out/GPC
```

正则检测到 “DPA” 后，可能误以为合同风险较低。

---

## 2. Agent 目标

这个 Agent 的目标不是写报告，而是把附件解析成**可被规则引擎消费的结构化事实**。

建议命名：

```text
CPRAFactExtractionAgent
```

---

## 3. 输入

```python
{
  "attachment": CPRAAttachment,
  "parsed_text": "...全文...",
  "file_role": "privacy_policy | rights_sop | data_map | vendor_list | other",
  "company_context": {
    "business_model": "...",
    "data_lifecycle": "..."
  }
}
```

---

## 4. 处理逻辑

### 4.1 隐私政策抽取

Agent 读取全文后，抽取：

```python
{
  "notice": {
    "has_notice_at_collection": true,
    "personal_info_categories_disclosed": true,
    "specific_categories": ["identifiers", "commercial information", "internet activity"],
    "purposes_disclosed": true,
    "specific_purposes": ["order fulfillment", "personalization", "advertising"],
    "retention_disclosed": true,
    "retention_rules": [
      {"data": "transaction records", "period": "7 years", "basis": "tax/accounting"},
      {"data": "browsing logs", "period": "13 months", "basis": "analytics"}
    ],
    "spi_disclosed": true,
    "spi_categories": ["precise geolocation", "health data"],
    "do_not_sell_share_link": {
      "exists": true,
      "text": "Privacy Choices",
      "is_standard_text": false,
      "has_required_icon": false
    },
    "limit_spi_link": {
      "exists": false
    },
    "gpc_supported": false
  }
}
```

### 4.2 DSR SOP 抽取

```python
{
  "dsr": {
    "channels": ["web_form", "email"],
    "has_toll_free_phone": false,
    "response_days": 45,
    "extension_allowed": true,
    "verification_method": "account login + email verification",
    "supports_access": true,
    "supports_delete": true,
    "supports_correct": true,
    "supports_opt_out": true,
    "supports_limit_spi": false,
    "is_easy_to_find": true
  }
}
```

### 4.3 数据地图抽取

```python
{
  "data_items": [
    {
      "category": "precise geolocation",
      "is_sensitive": true,
      "spi_type": "precise_geolocation",
      "source": "mobile app",
      "purpose": "nearby store feature",
      "recipient_type": "internal",
      "retention": "30 days",
      "sale_or_share": false,
      "cross_context_advertising": false
    },
    {
      "category": "browsing behavior",
      "is_sensitive": false,
      "purpose": "targeted advertising",
      "recipient_type": "ad_network",
      "sale_or_share": true,
      "cross_context_advertising": true
    }
  ]
}
```

### 4.4 供应商清单 / 合同抽取

```python
{
  "vendors": [
    {
      "name": "AdNetwork Alpha",
      "vendor_type": "ad_network",
      "receives_pi": true,
      "receives_spi": false,
      "sale_or_share": true,
      "has_dpa": true,
      "prohibits_sale_share": false,
      "includes_audit_right": false,
      "requires_deletion": true,
      "specifies_purpose": true,
      "honors_opt_out_or_gpc": false
    }
  ]
}
```

---

## 5. 输出

```python
CPRAFactPack(
    extracted_applicability=None,
    extracted_data_items=[...],
    extracted_dsr_mechanism=...,
    extracted_vendors=[...],
    extracted_consent_ui=None,
    evidence_spans=[
        {
          "fact_id": "vendor.AdNetworkAlpha.honors_opt_out_or_gpc",
          "source_file": "vendor_list.docx",
          "quote": "Advertising partners may use data for personalized advertising...",
          "confidence": 0.82
        }
    ],
    extraction_warnings=[
        "Opt-out link exists but standard wording could not be confirmed.",
        "DPA mentioned, but audit right not found."
    ]
)
```

---

## 6. 接入位置

放在当前 `generate_report()` 的第一步之后、规则引擎之前：

```python
attachment_facts = []
for att in payload.attachments:
    raw_facts = self.extractor.extract(att)
    agent_facts = self.fact_agent.extract(att, raw_facts, payload)
    attachment_facts.append(merge(raw_facts, agent_facts))

enhanced_payload = self.fact_merger.merge(payload, attachment_facts)

gap_items = run_all_rules(
    enhanced_payload.applicability,
    enhanced_payload.business_model,
    enhanced_payload.notice_and_consent,
    enhanced_payload.dsr_mechanism,
    enhanced_payload.consumer_rights_process,
    enhanced_payload.opt_out_and_sale_sharing,
    enhanced_payload.data_items,
    enhanced_payload.vendors,
    enhanced_payload.consent_ui,
)
```

---

## 7. 增益

这个 Agent 的收益最大。因为 CPRA 预期功能要求系统评估适用性、数据映射、DSR、SPI、出售/共享、暗模式、第三方合同等内容；功能说明也明确要求系统基于数据流图谱、数据类别清单、DSR 渠道、身份验证、SLA、SPI 使用清单、出售/共享情况和 UI 截图做判断。

**增益：**

```text
把“用户是否填对结构化字段”变成“系统从材料中主动提取结构化事实”；
把“关键词命中”升级为“条款语义理解”；
让 gap_rules 的输入质量明显提高；
减少漏判和误判。
```

---

# 三、最应该加的 Agent 2：角色与适用性推理 Agent

## 1. 当前问题

当前已经有 `CPRAApplicabilityInfo`，包含年收入、加州消费者数量、出售/分享收入占比、是否在加州运营、可能豁免等字段；规则里也会检查收入超过 2500 万美元、加州消费者数超过 10 万、出售/分享收入占比超过 50% 等阈值。

但 CPRA 的难点不只是阈值，而是：

```text
企业到底是 business？
service provider？
contractor？
third party？
SaaS 平台是否只是服务提供商？
是否也因为处理规模被直接管辖？
HIPAA / GLBA / COPPA 豁免是否只是数据级豁免，而不是企业整体豁免？
```

测试案例 DataFlow 就是典型场景：企业年收入未达标，但可能因为处理超过 10 万消费者个人信息而适用；同时它又是服务提供商，不一定直接面向消费者建立 DSR，但必须协助客户履行 DSR，并更新客户合同。

---

## 2. Agent 目标

建议命名：

```text
CPRABusinessRoleAgent
```

目标：**判断企业身份、适用性状态和义务边界**。

---

## 3. 输入

```python
{
  "business_model": payload.business_model,
  "data_lifecycle": payload.data_lifecycle,
  "applicability": payload.applicability,
  "vendors": payload.vendors,
  "data_items": payload.data_items,
  "attachment_facts": attachment_facts
}
```

---

## 4. 处理逻辑

### 4.1 判断适用性

```text
读取 annual_revenue_usd
读取 ca_consumer_count
读取 sell_share_revenue_ratio
读取 operates_in_california
从业务描述/附件中补充推断处理规模
判断是否满足 CPRA business 门槛
```

### 4.2 判断角色

```text
如果企业直接面向加州消费者提供服务：
    倾向 business

如果企业为客户处理客户上传数据，且不独立决定处理目的：
    倾向 service_provider

如果企业同时进行自有分析、产品改进、广告、模型训练：
    可能同时具有 business 义务

如果向广告网络、数据经纪商、保险推荐方披露数据：
    接收方可能是 third party 或 ad_network，不应简单视为 service provider
```

### 4.3 判断豁免

```text
如果 health_data + HIPAA：
    判断是否为 HIPAA covered entity / business associate 处理的 PHI
    否则不能直接整体豁免

如果 financial_account + GLBA：
    判断是否为金融机构非公开个人信息
    否则不能直接整体豁免

如果 children data + COPPA：
    标记未成年人 opt-in / parental consent 风险
```

预期依据中已经明确 HIPAA、GLBA、COPPA 会影响 CPRA 适用性和数据处理判断。 

---

## 5. 输出

```python
{
  "applicability_decision": {
    "status": "applicable | not_applicable | pending",
    "reasons": [
      "ca_consumer_count >= 100000",
      "operates in California",
      "service provider role does not eliminate contract obligations"
    ],
    "confidence": 0.78
  },
  "business_roles": [
    {
      "role": "service_provider",
      "scope": "customer-uploaded business data analytics",
      "obligations": ["DPA", "DSR assistance", "audit support", "deletion instruction"]
    },
    {
      "role": "business_possible",
      "scope": "own analytics / product improvement",
      "obligations": ["security safeguards", "notice", "data minimization"]
    }
  ],
  "gap_candidates": [
    {
      "domain": "business_role",
      "risk_level": "MEDIUM",
      "gap": "企业将自身简单定位为服务提供商，但未区分客户委托处理与自身独立处理场景。",
      "legal_basis": "CPRA §1798.140",
      "recommendation": "按处理目的拆分角色，并在客户DPA中明确服务提供商义务。"
    }
  ]
}
```

---

## 6. 接入位置

放在 `run_all_rules()` 前，增强 `payload.applicability` 和 `payload.vendors`：

```python
role_analysis = self.role_agent.analyze(enhanced_payload)
enhanced_payload = apply_role_analysis(enhanced_payload, role_analysis)
```

同时也可以在规则引擎后追加 `gap_candidates`。

---

## 7. 增益

这个 Agent 主要解决 **DataFlow Analytics 类 SaaS 角色混淆问题**。规则可以判断阈值，但服务提供商的义务边界、客户合同义务、直接义务与协助义务之间的差异，更适合 Agent 做语义推理。

---

# 四、最应该加的 Agent 3：SPI 与出售/共享复核 Agent

## 1. 当前问题

当前 `gap_rules.py` 已经定义了高风险目的集合，包括 advertising、marketing、insurance_recommendation、targeted_advertising、cross_context_advertising、third_party_sale、automated_decision_making、profiling；同时定义了 14 种 CPRA 敏感个人信息类别。规则会把 “SPI + 高风险目的” 判为 HIGH。

这很好，但仍有一个问题：**SPI、目的、接收方、出售/共享，很多时候不是用户结构化填出来的，而是散落在隐私政策、SDK列表、广告合作说明、数据地图、业务描述中。**

FitLife AI 的预期就是：健康数据用于个性化健身可能合理，但用于第三方营销、保健品推荐、保险推荐就明显超范围；同时健康衍生数据共享构成极高风险，还缺少选择退出和限制 SPI 使用入口。

---

## 2. Agent 目标

建议命名：

```text
CPRASPISharingRiskAgent
```

目标：**识别“敏感信息 + 高风险目的 + 第三方共享 + opt-out/limit-SPI缺失”的组合风险。**

---

## 3. 输入

```python
{
  "data_items": enhanced_payload.data_items,
  "vendors": enhanced_payload.vendors,
  "dsr_mechanism": enhanced_payload.dsr_mechanism,
  "consent_ui": enhanced_payload.consent_ui,
  "notice_facts": attachment_facts.privacy_policy,
  "data_map_facts": attachment_facts.data_map,
  "vendor_facts": attachment_facts.vendor_list
}
```

---

## 4. 处理逻辑

### 4.1 识别敏感信息

```text
遍历 data_items
识别 health_data / biometric_data / precise_geolocation / financial_account / account_credentials 等 SPI
如果附件中出现 health / medical / GPS / biometric 等事实，但 data_items 未填，补充 data_items_candidate
```

### 4.2 识别高风险目的

```text
判断 purpose 是否属于：
advertising
marketing
insurance_recommendation
health product recommendation
targeted advertising
cross-context behavioral advertising
profiling
automated decision making
```

### 4.3 识别第三方共享

```text
如果 recipient_type 是 ad_network / data_broker / insurance / marketing_partner：
    sale_or_share = true 或 sale_or_share_possible = true

如果隐私政策写 “personalized advertising / advertising partners / analytics partners”：
    标记 cross_context_advertising_possible
```

### 4.4 识别权利入口缺失

```text
如果存在 sale_or_share 但 dsr.opt_out = false：
    生成 HIGH gap

如果存在 SPI 且 dsr.limit_spi = false：
    生成 HIGH gap

如果 SPI + high_risk_purpose + consent_ui 有暗模式：
    生成 HIGH / CRITICAL gap
```

---

## 5. 输出

```python
{
  "risk_chains": [
    {
      "chain_id": "spi_health_insurance_share_001",
      "facts": [
        "health_data collected",
        "purpose = insurance_recommendation",
        "recipient = QuickInsure",
        "sale_or_share = true",
        "limit_spi = false",
        "opt_out = false"
      ],
      "risk_level": "HIGH",
      "gap": "健康数据被用于保险推荐并向第三方共享，超出提供健身服务的合理必要范围，且缺少限制敏感信息使用和选择退出入口。",
      "recommendation": "停止该共享路径，补充 Limit Use of Sensitive Personal Information 与 Do Not Sell or Share 入口，重构同意流程。"
    }
  ],
  "data_item_patches": [...],
  "vendor_patches": [...]
}
```

---

## 6. 接入位置

建议放在规则引擎之后：

```python
gap_items = run_all_rules(...)

spi_review = self.spi_sharing_agent.review(enhanced_payload, gap_items)
gap_items = merge_gap_items(gap_items, spi_review.gap_candidates)
enhanced_payload = apply_patches(enhanced_payload, spi_review.data_item_patches)
```

也可以二次跑规则：

```python
if spi_review.has_payload_patches:
    gap_items = run_all_rules(enhanced_payload...)
```

---

## 7. 增益

这个 Agent 解决最关键的高风险组合：

```text
SPI + 高风险用途
SPI + 第三方共享
SPI + 暗模式同意
SPI + 缺少限制使用入口
健康/保险/广告组合风险
```

这是规则可以做一部分，但 Agent 能更好处理跨材料推断。

---

# 五、最应该加的 Agent 4：暗模式 UI 审查 Agent

## 1. 当前问题

当前 `CPRAConsentUI` 已经有字段：

```text
has_cookie_banner
accept_prominent
reject_equally_prominent
preselected_consent
bundled_consent
refusal_more_steps
confusing_language
```

规则也能基于这些结构化字段判断暗模式。

但现实问题是：这些字段通常不是用户天然会准确填写的。用户可能只上传截图，或者只说“有 Cookie 弹窗”。系统如果依赖人工填字段，暗模式判断就会不稳定。

测试案例 TrendyGoods 要判断 Cookie 横幅没有同等突出的“拒绝所有”按钮、页脚 opt-out 链接不符合法规格式；FitLife AI 要判断注册界面通过暗模式胁迫用户同意。 

---

## 2. Agent 目标

建议命名：

```text
CPRADarkPatternAgent
```

目标：**从 UI 截图、HTML、用户描述中判断 consent_ui 字段。**

---

## 3. 输入

```python
{
  "ui_screenshots": [attachments with role="other" or "ui_screenshot"],
  "html_text": "...",
  "notice_and_consent": payload.notice_and_consent,
  "opt_out_text": payload.opt_out_and_sale_sharing,
  "data_items": payload.data_items
}
```

---

## 4. 处理逻辑

### 4.1 Cookie 横幅检查

```text
是否存在 Accept All
是否存在 Reject All
Reject All 是否和 Accept All 同屏
按钮颜色/大小/位置是否明显不对等
是否需要进入二级设置才能拒绝
是否默认打开广告 Cookie
是否使用 “继续即同意”
```

### 4.2 注册同意检查

```text
是否预选同意
是否把服务必要数据和营销/广告/第三方共享捆绑
是否不允许单独拒绝第三方共享
是否用“不接受则无法使用核心服务”胁迫非必要处理
是否对 SPI 处理单独明确说明
```

### 4.3 Opt-out 链接检查

```text
是否存在 Do Not Sell or Share My Personal Information
是否只是写成 Privacy Choices
是否位置显著
是否在页脚/隐私政策/App 设置可访问
是否支持 GPC
是否存在 Limit the Use of My Sensitive Personal Information
```

---

## 5. 输出

```python
{
  "consent_ui_patch": {
    "has_cookie_banner": true,
    "accept_prominent": true,
    "reject_equally_prominent": false,
    "preselected_consent": true,
    "bundled_consent": true,
    "refusal_more_steps": true,
    "confusing_language": false
  },
  "ui_findings": [
    {
      "risk_level": "HIGH",
      "finding": "注册页将健康数据处理、广告推荐和第三方共享捆绑为单一同意。",
      "evidence": "截图中仅有一个总开关：I agree to personalized health recommendations and partner offers."
    },
    {
      "risk_level": "MEDIUM",
      "finding": "Cookie 横幅中接受按钮高亮，拒绝入口位于二级设置页。",
      "evidence": "首页弹窗仅显示 Accept All 和 Manage Settings。"
    }
  ]
}
```

---

## 6. 接入位置

放在 `run_all_rules()` 前：

```python
ui_result = self.dark_pattern_agent.analyze(payload.attachments, payload.notice_and_consent)
enhanced_payload.consent_ui = merge_consent_ui(payload.consent_ui, ui_result.consent_ui_patch)
```

然后让现有 `check_dark_patterns()` 和 `check_spi()` 使用增强后的 `consent_ui`。

---

## 7. 增益

这个 Agent 的价值很明确：**把“用户主观描述 UI”变成“系统主动分析 UI”。**

它不替代规则，而是给规则提供输入。

---

# 六、最应该加的 Agent 5：供应商合同审查 Agent

## 1. 当前问题

当前 `CPRAVendorInfo` 已经支持 vendor_type、receives_pi、receives_spi、sale_or_share、has_dpa、prohibits_sale_share、includes_audit_right、requires_deletion、specifies_purpose 等字段。

但这些字段从哪里来？如果用户上传的是合同、DPA 或供应商清单，正则只能识别“是否提到 DPA”，不能判断条款是否实质满足 CPRA 要求。

测试案例 TrendyGoods 要求修订广告合同，加入必须遵守消费者选择退出指令的条款；DataFlow 要求客户合同纳入完整 CPRA 服务提供商条款。 

---

## 2. Agent 目标

建议命名：

```text
CPRAVendorContractAgent
```

目标：**把供应商合同从“有没有 DPA”升级为“DPA 条款是否完整”。**

---

## 3. 输入

```python
{
  "vendor_list_facts": attachment_facts.vendor_list,
  "contract_texts": [...],
  "vendors": payload.vendors,
  "data_items": payload.data_items,
  "opt_out_context": payload.opt_out_and_sale_sharing
}
```

---

## 4. 处理逻辑

对每个 vendor 建立条款矩阵：

```text
是否明确 vendor 类型：
    service_provider / contractor / third_party / ad_network / data_broker

是否明确处理目的：
    specifies_purpose

是否禁止出售/共享：
    prohibits_sale_share

是否禁止再披露：
    prohibits_further_disclosure

是否协助 DSR：
    assists_dsr

是否尊重 opt-out / GPC：
    honors_opt_out_or_gpc

是否有审计权：
    includes_audit_right

是否终止后删除/返还：
    requires_deletion_or_return

是否有安全义务：
    security_safeguards

是否接收 SPI：
    receives_spi

SPI 是否有额外限制：
    spi_specific_restrictions
```

---

## 5. 输出

```python
{
  "vendor_patches": [
    {
      "name": "AdNetwork Alpha",
      "vendor_type": "ad_network",
      "receives_pi": true,
      "receives_spi": false,
      "sale_or_share": true,
      "has_dpa": true,
      "prohibits_sale_share": false,
      "includes_audit_right": false,
      "requires_deletion": true,
      "specifies_purpose": true,
      "honors_opt_out_or_gpc": false
    }
  ],
  "contract_gaps": [
    {
      "domain": "vendor",
      "risk_level": "HIGH",
      "gap": "广告合作伙伴合同未要求其尊重消费者 Do Not Sell or Share / GPC 选择退出信号。",
      "recommendation": "修订广告合作协议，加入选择退出信号承接、用途限制、禁止再披露和审计条款。",
      "evidence_source": "AdNetworkAlpha_DPA.pdf"
    }
  ]
}
```

---

## 6. 接入位置

规则前后都要接。

规则前：补全 vendors 字段。

```python
vendor_review = self.vendor_contract_agent.extract(payload.attachments, payload.vendors)
enhanced_payload.vendors = merge_vendors(payload.vendors, vendor_review.vendor_patches)
```

规则后：补充规则没有覆盖的合同缺口。

```python
gap_items = merge_gap_items(gap_items, vendor_review.contract_gaps)
```

---

## 7. 增益

这个 Agent 的收益是把合同审查从：

```text
有没有 DPA
```

升级成：

```text
DPA 是否满足 CPRA 服务提供商/承包商/第三方合同要求
```

这对 SaaS、广告网络、数据经纪商、健康/保险合作方非常关键。

---

# 七、最应该加的 Agent 6：法规证据匹配 Agent

## 1. 当前问题

当前 `CPRALegalRetriever` 已经做了域级 RAG，域到 query 的映射包括 applicability、dsr、opt_out、spi、vendor、dark_patterns、exemptions、notice、data_mapping、business_role。每个域检索 3 条法规依据，最多 2 条附加到对应 `CPRAGapItem`。

这个比固定 query 好很多，但仍是**域级检索**，不是**问题级检索**。

例如 gap 是：

```text
健康数据用于保险推荐并共享给 QuickInsure，缺少 Limit SPI 入口。
```

域级 query 可能只检索：

```text
CPRA sensitive personal information limit use Section 1798.121
```

但更好的 query 应该是：

```text
CPRA sensitive personal information health data insurance recommendation limit use disclosure third party
```

---

## 2. Agent 目标

建议命名：

```text
CPRALegalEvidenceAgent
```

目标：**给每条 gap_item 匹配最精准的法规依据和解释。**

---

## 3. 输入

```python
{
  "gap_item": CPRAGapItem,
  "facts": related_facts,
  "domain_citations": current_domain_citations,
  "reference_library": "us"
}
```

---

## 4. 处理逻辑

```text
读取 gap_item.domain
读取 gap_item.gap
读取 evidence_source
生成更具体的 query
调用 retrieve_regulations()
筛选法规片段
判断片段是否真正支持 gap
输出 legal_basis、citation、snippet、rationale
```

---

## 5. 输出

```python
{
  "gap_id": "...",
  "legal_basis": "CPRA §1798.121; CPPA Regulations §7004",
  "citations": [
    "《CPRA》§1798.121",
    "《CPPA Regulations》§7004"
  ],
  "legal_rationale": "该缺口同时涉及敏感个人信息限制使用权和通过暗模式取得同意的有效性问题。",
  "confidence": 0.86
}
```

---

## 6. 接入位置

放在规则引擎和报告生成之间：

```python
for gap in gap_items:
    evidence = self.legal_evidence_agent.match(gap, enhanced_payload, attachment_facts)
    gap.legal_basis = evidence.legal_basis
    gap.citations = evidence.citations
    gap.legal_rationale = evidence.legal_rationale
```

---

## 7. 增益

这个 Agent 主要提升**报告可信度**。
预期功能中明确把 CPRA、CPPA Regulations、CPPA FAQ、执法案例、HIPAA、GLBA、COPPA 等作为输出依据，不同模块需要不同依据。
法规证据匹配 Agent 可以避免报告里出现“泛泛引用 CPRA”，而是让每个 gap 都有更准确的依据链。

---

# 八、最应该加的 Agent 7：一致性审校 Agent

## 1. 当前问题

当前 `_check_consistency()` 主要检查：

```text
是否缺少隐私政策附件；
是否存在 HIGH 风险。
```

旧版文档中也是类似逻辑，只有隐私政策附件缺失和 HIGH 风险提示。

这不足以发现跨模块矛盾。

例如：

```text
隐私政策说没有出售/共享；
数据地图显示 ad_network + cross_context_advertising；
供应商合同显示广告伙伴可个性化广告；
报告却写 opt-out 基本合规。
```

这就是典型的跨材料矛盾。

---

## 2. Agent 目标

建议命名：

```text
CPRAConsistencyReviewAgent
```

目标：**检查输入事实、规则结论、法规依据、报告章节之间是否自洽。**

---

## 3. 输入

```python
{
  "payload": enhanced_payload,
  "attachment_facts": attachment_facts,
  "gap_items": gap_items,
  "chapters": chapters
}
```

---

## 4. 处理逻辑

### 4.1 事实一致性检查

```text
隐私政策是否说没有出售/共享？
数据地图是否显示 ad_network / cross_context_advertising？
供应商合同是否显示广告伙伴？
三者是否冲突？
```

### 4.2 权利入口一致性检查

```text
是否存在 SPI？
是否存在 limit_spi 入口？
报告是否提到限制敏感信息使用权？
gap_items 是否有 spi gap？
如果没有，提示漏判。
```

### 4.3 角色一致性检查

```text
企业是否自称 service provider？
是否又独立进行广告、营销、产品画像？
如果是，提示角色混合。
```

### 4.4 报告一致性检查

```text
gap_items 是 HIGH，但执行摘要写“基本合规” → 冲突
行动清单没有覆盖 HIGH gap → 冲突
章节引用与 gap domain 不匹配 → 冲突
```

---

## 5. 输出

```python
{
  "consistency_issues": [
    {
      "severity": "HIGH",
      "issue": "隐私政策声称不出售/共享，但数据地图显示广告网络接收行为数据用于跨情境广告。",
      "affected_domains": ["opt_out", "vendor", "data_mapping"],
      "recommendation": "将该路径标记为 sale/share_possible，并重新触发 opt-out 与 vendor 规则。"
    }
  ],
  "gap_suggestions": [
    {
      "domain": "opt_out",
      "risk_level": "HIGH",
      "gap": "存在广告共享路径但隐私政策未披露对应选择退出机制。"
    }
  ],
  "chapter_revision_notes": [
    "执行摘要需要反映 opt-out 高风险，而不是写成部分合规。"
  ]
}
```

---

## 6. 接入位置

放在报告生成后：

```python
chapters = self._generate_chapters_from_context(...)
review = self.consistency_agent.review(enhanced_payload, attachment_facts, gap_items, chapters)

gap_items = merge_gap_items(gap_items, review.gap_suggestions)
chapters = revise_chapters(chapters, review.chapter_revision_notes)
issues.extend(review.consistency_issues)
```

---

## 7. 增益

这个 Agent 是质量兜底。它不会承担初判，而是检查：

```text
事实是否冲突；
gap 是否漏判；
报告是否和 gap_items 一致；
高风险项是否进入行动清单。
```

这对答辩、演示和真实交付都很重要。

---

# 九、可选 Agent 8：整改任务拆解 Agent

这个不是合规判断核心，但对产品体验有价值。

## 1. 当前问题

当前报告有行动清单与优先级，LLM 章节指令也要求按 HIGH/MEDIUM/LOW 列整改事项，每项包含问题描述、法律依据、整改方案、完成时间。

但如果要真正做成产品，用户需要的不只是“建议整改”，还需要：

```text
谁负责；
改哪个系统；
改哪个文档；
改哪个合同；
优先级；
完成时间；
验收标准；
需要补充哪些材料。
```

---

## 2. Agent 目标

建议命名：

```text
CPRARemediationPlanningAgent
```

---

## 3. 输入

```python
{
  "gap_items": gap_items,
  "company_context": payload.business_model,
  "risk_level": risk_level
}
```

---

## 4. 输出

```python
{
  "tasks": [
    {
      "priority": "urgent",
      "owner_role": "Legal + Product + Engineering",
      "task": "上线 Do Not Sell or Share My Personal Information 链接",
      "system_affected": ["website footer", "app privacy settings", "privacy policy"],
      "acceptance_criteria": [
        "链接文字使用标准表达",
        "入口位于页脚和隐私政策显著位置",
        "选择退出状态可记录并同步至广告合作伙伴"
      ],
      "estimated_phase": "short_term"
    }
  ]
}
```

---

## 5. 接入位置

放在 gap_items 生成后、报告生成前：

```python
remediation_plan = self.remediation_agent.plan(gap_items, enhanced_payload)
context_block += format_remediation_plan(remediation_plan)
```

---

# 十、最终推荐：不要一次加 8 个 Agent，按优先级加 4 个

你现在最适合的迭代顺序如下。

## 第一优先级：事实抽取 Agent

```text
CPRAFactExtractionAgent
```

原因：当前最大问题是输入事实质量。没有高质量事实，后面的规则、RAG、报告都会不稳定。

它解决：

```text
附件只靠正则；
结构化字段依赖用户填写；
隐私政策、SOP、数据地图、供应商合同不能深度利用。
```

---

## 第二优先级：SPI / 出售共享复核 Agent

```text
CPRASPISharingRiskAgent
```

原因：这是 CPRA 高风险场景的核心，尤其是 FitLife AI 这类健康、位置、生物特征、第三方营销、保险推荐场景。测试案例中 FitLife 的预期输出明确要求识别健康数据营销超范围、健康衍生数据出售/共享、缺少 opt-out 和 limit-SPI 入口、暗模式同意等问题。

---

## 第三优先级：供应商合同审查 Agent

```text
CPRAVendorContractAgent
```

原因：电商广告合作、SaaS 客户 DPA、健康/保险第三方合作，都离不开合同判断。TrendyGoods 和 DataFlow 两个案例都要求合同整改。 

---

## 第四优先级：一致性审校 Agent

```text
CPRAConsistencyReviewAgent
```

原因：当前模块已经有规则和 LLM 报告生成，最容易出现的问题是：

```text
规则判断是 HIGH；
报告写得太温和；
附件事实和结构化输入冲突；
高风险 gap 没进入行动清单。
```

这个 Agent 可以作为最后质量闸门。

---

# 十一、建议的实际代码结构

可以新增目录：

```text
backend/modules/cpra/agents/
├── __init__.py
├── fact_extraction_agent.py
├── business_role_agent.py
├── spi_sharing_risk_agent.py
├── vendor_contract_agent.py
├── dark_pattern_agent.py
├── legal_evidence_agent.py
├── consistency_review_agent.py
└── remediation_planning_agent.py
```

再新增统一数据结构：

```text
backend/modules/cpra/agent_schema.py
```

核心模型：

```python
class CPRAFactPack(BaseModel):
    applicability_patch: CPRAApplicabilityInfo | None = None
    data_item_patches: list[CPRADataItem] = []
    dsr_patch: CPRADSRMechanism | None = None
    vendor_patches: list[CPRAVendorInfo] = []
    consent_ui_patch: CPRAConsentUI | None = None
    evidence_spans: list[EvidenceSpan] = []
    warnings: list[str] = []

class AgentGapCandidate(BaseModel):
    domain: str
    risk_level: Literal["HIGH", "MEDIUM", "LOW"]
    gap: str
    legal_basis: str | None = None
    recommendation: str
    phase: Literal["short_term", "mid_term", "long_term"]
    evidence_source: str | None = None
    confidence: float
```

`service.py` 中可以改成：

```python
def generate_report(self, payload: CPRARequest) -> CPRAResult:
    # 1. 基础附件解析
    attachment_facts = [self.extractor.extract(att) for att in payload.attachments]

    # 2. Agent 事实增强
    fact_pack = self.fact_agent.extract(payload, attachment_facts)
    enhanced_payload = self.fact_merger.merge(payload, fact_pack)

    # 3. 角色判断
    role_pack = self.role_agent.analyze(enhanced_payload)
    enhanced_payload = self.fact_merger.merge(enhanced_payload, role_pack)

    # 4. 确定性规则
    gap_items = run_all_rules(...enhanced_payload...)

    # 5. 高风险组合复核
    spi_review = self.spi_sharing_agent.review(enhanced_payload, gap_items)
    gap_items = merge_gap_items(gap_items, spi_review.gap_candidates)

    # 6. 合同审查
    vendor_review = self.vendor_contract_agent.review(enhanced_payload, attachment_facts)
    gap_items = merge_gap_items(gap_items, vendor_review.gap_candidates)

    # 7. 法规证据匹配
    gap_items = self.legal_evidence_agent.attach_evidence(gap_items, enhanced_payload)

    # 8. 风险评级
    risk_level = self._resolve_overall_level(gap_items)

    # 9. 整改计划
    remediation_plan = self.remediation_agent.plan(gap_items, enhanced_payload)

    # 10. 章节生成
    context_block = self._build_enhanced_context(
        enhanced_payload,
        gap_items,
        risk_level,
        remediation_plan
    )
    chapters = self._generate_chapters_from_context(...)

    # 11. 一致性审校
    review = self.consistency_agent.review(enhanced_payload, gap_items, chapters)
    issues = self._check_consistency(...) + review.issues

    # 12. 渲染
    outputs = self._render(...)
    return CPRAResult(...)
```

---

# 十二、哪些地方不建议加 Agent

这点也要明确。不是所有地方都该 Agent 化。

## 1. 风险等级汇总不需要 Agent

当前逻辑：

```text
存在 HIGH → HIGH
存在 MEDIUM → MEDIUM
否则 LOW
```

这类确定性规则应该保留，不需要 Agent。

---

## 2. 路由、异步任务、文件渲染不需要 Agent

这些是工程流程：

```text
router.py
InMemoryTaskManager
_render()
DOCX/PDF/XLSX/ZIP 输出
```

Agent 加进去没有价值，反而会增加不可控性。

---

## 3. 基础阈值判断不需要 Agent

例如：

```text
年收入 > 2500万美元
消费者数量 >= 10万
出售/分享收入占比 >= 50%
```

这些应由规则直接判断。Agent 只负责从文本里抽取或推断这些字段，不负责最终阈值判断。

---

# 十三、最终落地结论

CPRA 模块最适合采用 **“规则引擎为主，Agent 增强事实和复核”** 的混合架构。

最推荐的处理逻辑是：

```text
附件/文本/UI/合同
    ↓
事实抽取 Agent：把材料转成结构化事实
    ↓
角色适用性 Agent：处理 SaaS、服务提供商、豁免等边界
    ↓
确定性规则引擎：稳定产出 gap_items
    ↓
SPI/出售共享 Agent：复核高风险组合
    ↓
供应商合同 Agent：审查 DPA 和第三方义务
    ↓
法规证据 Agent：给每个 gap 匹配准确依据
    ↓
整改任务 Agent：生成可执行路线图
    ↓
一致性审校 Agent：防止报告与事实/规则冲突
```

真正必要的 Agent 是这四个：

```text
1. CPRAFactExtractionAgent
2. CPRASPISharingRiskAgent
3. CPRAVendorContractAgent
4. CPRAConsistencyReviewAgent
```

它们分别解决：

```text
事实从哪里来；
高风险组合怎么识别；
合同义务怎么判断；
最终报告是否自洽。
```

这样加 Agent 后，CPRA 模块会从现在的：

```text
结构化字段 + 正则规则 + LLM报告生成
```

升级为：

```text
材料理解 + 结构化事实抽取 + 规则判断 + 复杂场景复核 + 法规证据链 + 可执行整改报告
```

这才是和预期功能最匹配的 Agent 化方向。

---

# 十四、严格落实计划

下面这一部分不是“方向建议”，而是 **从当前代码出发的正式执行方案**。后续实现必须严格按这里的顺序、边界、验收标准推进，避免再次回到“先堆功能、后补结构”的状态。

## 14.1 落实目标

本次落实目标不是一次性把所有 Agent 全部做完，而是把 CPRA 模块从当前的：

```text
附件正则提取
+ 10 条规则
+ 域级 RAG
+ 6 章报告生成
```

严格升级为：

```text
结构化事实增强
→ 规则前 Agent 输入增强
→ 规则后高风险复核
→ gap 级法规证据匹配
→ 整改路线图增强
→ 报告一致性审校
```

并且要求：

```text
规则仍然是主判断来源；
Agent 只做事实增强、复杂推理、证据匹配和一致性复核；
任何 Agent 失败都必须静默降级，不能阻塞主流程；
每一阶段都必须有测试、验收标准和回退路径。
```

---

## 14.2 严格范围

### 本次必须落地

```text
1. CPRAFactExtractionAgent
2. CPRASPISharingRiskAgent
3. CPRAVendorContractAgent
4. CPRAConsistencyReviewAgent
5. service.py 主流程重构
6. schema.py 的中间产物结构扩展
7. tests/ 下新增针对 Agent 接入后的单测与服务测试
```

### 本次明确不做

```text
1. 不改 router.py 的 API 形态
2. 不改异步任务管理模型
3. 不把风险汇总改成 Agent 决策
4. 不把 DOCX/PDF/XLSX/ZIP 渲染逻辑 Agent 化
5. 不引入通用 Agent Runtime，仍采用模块内受限 agent 结构
```

---

## 14.3 代码落点

本次落实必须严格落在以下位置：

```text
backend/modules/cpra/
├── service.py
├── schema.py
├── attachment_extractor.py
├── gap_rules.py
├── legal_retriever.py
├── agents/
│   ├── __init__.py
│   ├── fact_extraction_agent.py
│   ├── spi_sharing_risk_agent.py
│   ├── vendor_contract_agent.py
│   └── consistency_review_agent.py
├── fact_merger.py                  ← 新增，负责把附件事实并回 payload
├── gap_merger.py                   ← 新增，负责 gap 去重/排序/合并
└── tests/
    ├── test_service.py
    ├── test_gap_rules.py
    ├── test_fact_merger.py         ← 新增
    ├── test_agents_fact.py         ← 新增
    ├── test_agents_spi.py          ← 新增
    ├── test_agents_vendor.py       ← 新增
    └── test_agents_consistency.py  ← 新增
```

要求：

```text
Agent 逻辑必须放在 agents/ 下；
payload 合并逻辑不能散落在 service.py 中，必须抽到 fact_merger.py / gap_merger.py；
service.py 只保留编排，不继续膨胀成大杂烩。
```

---

## 14.4 分阶段执行顺序

## 第一阶段：先把 Agent 基础骨架搭起来

目标：

```text
先把 CPRA agent 层建好，并和现有 service.py 接通，但不追求第一版就覆盖全部复杂语义。
```

必须完成：

```text
1. 新建 backend/modules/cpra/agents/__init__.py
2. 定义 CPRAAgentBase
3. 统一 system prompt、JSON 输出、失败降级逻辑
4. 提供 create_cpra_agents(llm_client)
5. 在 service.py 初始化 self.agents
```

验收标准：

```text
service.py 能成功初始化 agents；
LLM 未配置时所有 agent 返回 fallback 结构；
现有 CPRA 流程不报错、不降功能。
```

---

## 第二阶段：先落 FactExtractionAgent，不允许跳过

这一阶段优先级最高，必须先做，因为后续 SPI、Vendor、Consistency 都依赖增强后的事实。

必须完成：

```text
1. 实现 CPRAFactExtractionAgent
2. 为 privacy_policy / rights_sop / data_map / vendor_list 四类附件输出结构化增强事实
3. 新增 evidence_spans / extraction_warnings 结构
4. 新增 fact_merger.py，把 agent 事实并回 payload
5. service.py 在 run_all_rules() 前执行 fact merge
```

严格要求：

```text
原 attachment_extractor.py 不删除，保留为规则前基础提取器；
Agent 输出是增强层，不直接替代底层 extractor；
任何合并都必须遵守“显式用户输入优先，Agent 推断次之，正则兜底再次之”。
```

验收标准：

```text
当 payload.data_items 为空但 data_map 附件可解析时，规则引擎能获得补全后的 data_items；
当 payload.dsr_mechanism 为空但 rights_sop 附件可解析时，规则引擎能获得补全后的 dsr；
当 vendor_list 中识别出 DPA / opt-out / audit 等条款时，vendors 字段能被增强；
服务测试中 gap_items 数量和内容相较现状有可解释增强，而不是随机波动。
```

---

## 第三阶段：落 SPISharingRiskAgent

这一阶段负责把规则后复核真正做起来。

必须完成：

```text
1. 实现 CPRASPISharingRiskAgent
2. 输入使用增强后的 data_items / vendors / dsr / consent_ui / attachment facts
3. 输出 risk_chains、gap_candidates、data_item_patches、vendor_patches
4. 新增 gap_merger.py，统一合并规则产物和 agent gap
5. service.py 在 run_all_rules() 后接入该 agent
```

严格要求：

```text
Agent 只能补充 gap 或补丁，不能删除规则已命中的 HIGH gap；
若 Agent 产生 payload patch，必须明确是否二次跑规则；
涉及 SPI + 广告 + 第三方共享 + 缺失 opt-out / limit SPI 的组合，必须可稳定命中。
```

验收标准：

```text
健康数据 + 广告/保险推荐 + 第三方共享能生成 HIGH gap；
存在 SPI 但缺少 limit SPI 入口能生成 HIGH gap；
cross-context advertising 但缺少 Do Not Sell or Share 入口能生成 HIGH gap；
相关用例在测试中稳定复现，不依赖随机模型措辞。
```

---

## 第四阶段：落 VendorContractAgent

这一阶段负责把“有没有 DPA”升级成“DPA 是否满足 CPRA 义务”。

必须完成：

```text
1. 实现 CPRAVendorContractAgent
2. 对每个 vendor 输出 vendor_patches
3. 对合同缺口输出 contract_gaps
4. service.py 在规则前合并 vendor patch，在规则后合并 contract gaps
```

严格要求：

```text
vendor_type、receives_spi、sale_or_share、dpa_honors_opt_out、dpa_requires_audit、dpa_requires_dsr_assist 这些字段必须进入 patch 逻辑；
广告网络、数据经纪商、保险合作方不能简单一律视为 service_provider；
合同缺口必须带 evidence_source。
```

验收标准：

```text
“提到 DPA 但没有 opt-out / audit / deletion / purpose limitation”时，能被识别为不完整；
广告合作合同缺少承接消费者 opt-out / GPC 义务时，能生成 HIGH gap；
service provider 场景下能区分“角色成立”和“合同义务仍缺失”。
```

---

## 第五阶段：落 ConsistencyReviewAgent

这一阶段最后接，因为它依赖前面所有中间产物稳定下来。

必须完成：

```text
1. 实现 CPRAConsistencyReviewAgent
2. 检查 payload、attachment facts、gap_items、chapters 之间是否冲突
3. 输出 issues / warnings / suggested_fixes
4. 在章节生成后接入 consistency review
```

严格要求：

```text
该 Agent 只做复核，不改规则结论；
若发现章节弱化 HIGH 风险、遗漏关键义务、引用和事实冲突，必须产出 issues；
如需修改章节，只能通过追加 warning 或触发 repair 逻辑，不允许 silently rewrite 核心结论。
```

验收标准：

```text
规则已判 HIGH，但章节写成“总体风险可控”时能报错；
gap 提到 SPI 风险，但报告未提 limit SPI 时能报错；
vendor contract gap 存在，但行动清单漏写合同时能报错。
```

---

## 14.5 service.py 必须重构成固定编排顺序

最终 `generate_report()` 必须严格收敛成下面这个顺序：

```text
1. 基础附件提取
2. FactExtractionAgent
3. fact merge，生成 enhanced_payload
4. run_all_rules()
5. SPISharingRiskAgent
6. VendorContractAgent
7. gap merge / 去重 / 排序
8. 法规检索与证据绑定
9. 生成上下文
10. 生成 6 章报告
11. ConsistencyReviewAgent
12. 最终 consistency issues 合并
13. render 输出
```

不允许出现的情况：

```text
Agent 调用顺序来回穿插；
规则前后混在一起；
gap 合并逻辑写成多个 if scattered 在 service.py；
章节生成后再反向修改事实。
```

---

## 14.6 schema.py 必须补的结构

为了让这套逻辑可持续，schema 不能只保留现有 request/result。

本次必须补充中间结构，至少包括：

```text
CPRAFactPack
CPRAEvidenceSpan
CPRAAgentWarning
CPRARiskChain
CPRAVendorPatch
CPRADataItemPatch
CPRAConsistencyIssue
```

严格要求：

```text
这些结构先服务模块内部也可以，但必须定义为 schema/model，而不是临时 dict 拼装；
如果第一版不想暴露到 API 返回体，也至少要在模块内有稳定类型；
禁止继续扩大“dict[str, Any] 到处流动”的实现方式。
```

---

## 14.7 测试要求

本次落实必须同步补测试，不能先上逻辑、后补测试。

最少要覆盖：

```text
1. Agent 关闭 / LLM 不可用时的 fallback
2. 附件事实增强后规则输入是否变化
3. SPI + 高风险用途 + 第三方共享组合
4. vendor 合同缺口识别
5. 报告一致性问题检测
6. 老输入结构的 backward compatibility
```

至少补以下测试场景：

```text
TrendyGoods：广告 Cookie / opt-out / 广告合作方合同缺口
FitLife AI：健康数据 / SPI / 第三方推荐 / dark pattern
DataFlow Analytics：SaaS / service provider / 客户合同义务
```

严格要求：

```text
每个 Agent 至少有 1 个单测；
service.py 至少有 2 个集成测试；
原 test_gap_rules.py 不得因重构失效；
新增逻辑若改变 gap 输出，必须同步更新断言，不允许放宽成“只要不报错”。
```

---

## 14.8 验收标准

这一轮不是“代码能跑”就算完成，必须同时满足：

```text
1. CPRA agent 层存在且接入主流程
2. service.py 主流程顺序清晰
3. 结构化事实能被材料主动增强
4. 高风险组合能被稳定识别
5. 供应商合同义务缺口能被识别
6. 报告与事实/规则冲突能被识别
7. 全部新增测试通过
8. 原有 API 和输出产物不破坏
```

如果上述 8 条有任意一条不满足，就不能视为“CPRA 方案已落实”。

---

## 14.9 实施纪律

后续实现必须遵守下面这些纪律：

```text
1. 先搭骨架，再逐个 Agent 接入，不准同时并行乱改
2. 先补 schema 和 merger，再写 service 编排
3. 先写 fallback，再写 LLM 分支
4. 先有测试，再扩大规则和 Agent 语义
5. 不允许把业务判断重新塞回自由文本 prompt
6. 不允许让 Agent 直接改最终风险等级
7. 不允许删除已有规则兜底
```

---

## 14.10 具体执行顺序

严格执行顺序如下：

```text
第 1 步：新增 agents/__init__.py + CPRAAgentBase
第 2 步：补 schema 中间结构
第 3 步：新增 fact_merger.py / gap_merger.py
第 4 步：接入 CPRAFactExtractionAgent
第 5 步：改造 service.py 使用 enhanced_payload
第 6 步：接入 CPRASPISharingRiskAgent
第 7 步：接入 CPRAVendorContractAgent
第 8 步：补法规证据绑定到 gap 级
第 9 步：接入 CPRAConsistencyReviewAgent
第 10 步：补全单测和集成测试
第 11 步：回归现有输出产物
```

这 11 步必须按顺序执行，不建议跳步，不建议先做报告层再补事实层。

---

## 14.11 当前开始执行的第一落点

从当前仓库状态出发，第一批实际改造就应该是：

```text
1. 新建 backend/modules/cpra/agents/__init__.py
2. 新建 backend/modules/cpra/agents/fact_extraction_agent.py
3. 新建 backend/modules/cpra/fact_merger.py
4. 扩展 backend/modules/cpra/schema.py
5. 改 backend/modules/cpra/service.py，把 FactExtractionAgent 接到 run_all_rules() 前
6. 新增对应测试
```

原因只有一个：

```text
没有 enhanced facts，后面的 SPI / Vendor / Consistency 都只能继续在弱输入上做补丁，收益会被严重削弱。
```
