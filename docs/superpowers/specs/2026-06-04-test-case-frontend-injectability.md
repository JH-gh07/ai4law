# 测试案例前端可注入性分析

> 2026-06-04 · 判定 docx 测试案例输入能否直接填入前端表单，以及一键注入方案

---

## 一、核心发现：两条数据路径

每个模块从前端到后端有 **两条不同的数据路径**：

```
路径A（正常用户路径）：
  表单字段（10-40个） → buildXxxPayload() 序列化 → API JSON → 后端 Pydantic schema

路径B（后端直连路径）：
  JSON payload 直接 POST /api/v1/{module}/generate → 后端 Pydantic schema
```

路径 A 经过了前端序列化层的"压缩"——例如 CPRA 把 13 个表单字段合并成 6 个 API 字段（用"；"拼接）。路径 B 直接打后端，跳过了前端序列化逻辑。

**结论：开发模式注入应走路径 B，绕过前端表单序列化层。**

---

## 二、逐模块映射分析

### 2.1 CPRA — ✅ 完全可注入，但有 3 级精度差异

**前端表单字段 (16个)**：
```
company_name, dba_name, cpra_applicability_selfcheck, business_model,
data_lifecycle, data_categories, notice_and_consent, privacy_policy_url,
consumer_rights_process, identity_verification_method, rights_sla,
opt_out_and_sale_sharing, spi_usage_summary, vendor_management,
ui_dark_pattern_check, review_focus
+ 5 个附件上传区域
```

**序列化逻辑** (`buildCpraPayload`)：多个表单字段被拼接：
- `business_model` = `cpraValues.business_model + dba_name + cpra_applicability_selfcheck + review_focus` (用"；"连接)
- `data_lifecycle` = `data_lifecycle + data_categories + spi_usage_summary`
- `notice_and_consent` = `notice_and_consent + privacy_policy_url + ui_dark_pattern_check`
- `consumer_rights_process` = `consumer_rights_process + identity_verification_method + rights_sla`

**后端 CPRARequest schema 支持的可选结构化字段**：
```python
applicability: CPRAApplicabilityInfo | None  # 年收入、消费者数等
data_items: list[CPRADataItem]              # 结构化数据项
dsr_mechanism: CPRADSRMechanism | None      # DSR渠道结构化描述
vendors: list[CPRAVendorInfo]               # 供应商列表
consent_ui: ConsentUIInfo | None            # 同意界面描述
```

**与测试案例的对照**：

| 测试案例字段 | 前端表单有对应？ | 注入方式 |
|------------|:---:|------|
| 公司名、DBA | ✅ | 直填 |
| 年收入 $30M | ❌ 无独立字段 | 写入 `cpra_applicability_selfcheck` textarea |
| 消费者数/处理量 | ❌ 无独立字段 | 同上 |
| 业务模型描述 | ✅ business_model | 直填 |
| 数据生命周期 | ✅ data_lifecycle | 直填 |
| 告知同意机制 | ✅ notice_and_consent | 直填 |
| DSR渠道详情 | ✅ consumer_rights_process | 直填 |
| 出售/共享机制 | ✅ opt_out_and_sale_sharing | 直填 |
| 供应商管理 | ✅ vendor_management | 直填 |
| 暗模式检查 | ✅ ui_dark_pattern_check | 直填 |
| SPI使用说明 | ✅ spi_usage_summary | 直填 |
| 附件文件 | ✅ 上传区域 | URL模式可伪传 |

**判定：CPRA 测试案例 ✅ 可完整注入。精度损失：结构化字段被 flatten 成 textarea。**

### 2.2 Diagnosis — ✅ 完美匹配

**前端表单字段 (≈40个，5步向导)**：
```
Step 1: company_name, m1_industry(单选), m1_business_channels(多选), 
        m1_service_targets(单选), m1_company_size(单选)
Step 2: m2_core_needs(多选), m2_had_compliance_issue(单选), m2_deadline(单选)
Step 3: m3_processes_personal_info(单选), m3_personal_info_types(多选),
        m3_processes_important_data(单选), m3_important_data_types(多选),
        m3_data_sources(多选), m3_processing_activities(多选),
        m3_data_volume_range(单选), m3_retention_period(单选) ...
Step 4: m4_share_to_third_party(单选), m4_cross_border_transfer(单选),
        m4_commercialization(单选), m4_entrusted_processing(单选) ...
Step 5: m5_systems(多选), m5_security_measures(多选),
        m5_compliance_docs(多选), m5_penalty_or_complaint(单选) ...
```

**与测试案例的对照**（以案例一"跨境优品"为例）：

| docx 测试步骤 | 表单字段 | 值 |
|------------|---------|----|
| 步骤一：是否涉及重要数据 | `m3_processes_important_data` | `"no"` |
| 步骤二：是否涉及个人信息 | `m3_processes_personal_info` | `"yes"` |
| 步骤四：是否CIIO | 隐式（无专门字段但后端从 other fields infer） | 通过数据规模推断 |
| 步骤五：个人信息类型 | `m3_personal_info_types` | 不含敏感信息 |
| 步骤五子路径：量化规模 | `m3_data_volume_range` | `"10-100万条"` |

**判定：Diagnosis ✅ 完美匹配。docx 的问题流就是表单的问题流。**

### 2.3 Assessment — ⚠️ 有 2 个小缺口

**前端表单字段 (≈20个)**：
```
company_name, company_uscc, legal_representative, registered_address,
company_nature, industry, receiver_country, receiver_name,
assessment_start_date, assessment_end_date, lead_department,
participant_departments, third_party_support, third_party_name,
third_party_scope, scenario_name, transfer_frequency, is_long_term,
transfer_purpose, legal_basis, necessity_basis, is_ciio,
contains_important_data, pii_count, spi_count, data_inventory_summary,
system_chain_summary, security_capability_summary, force_override_path
+ 附件上传
```

**与测试案例的对照**（以案例一"东方信托"为例）：

| docx 测试输入 | 前端表单字段 | 状态 |
|-------------|---------|:---:|
| 数据处理者名称 | company_name | ✅ |
| 股权结构 | ❌ 无专门字段 | ⚠️ 需写入 textarea 兜底 |
| 组织架构（数据安全委员会） | ❌ 无专门字段 | ⚠️ 同上 |
| 起止时间 | assessment_start_date/end_date | ✅ |
| CIIO 身份 | is_ciio (checkbox) | ✅ |
| 重要数据判断 | contains_important_data (checkbox) | ✅ |
| 涉及 SPI 类型 | 隐式（spi_count + text fields） | ✅ |
| 安全保障能力（加密/等保） | security_capability_summary | ✅ |
| 境外接收方安全能力 | ❌ 无专门字段 | ⚠️ |
| 法律文件缺失条款 | 无（属于文档审查而非评估） | ⚠️ 此信息超出 assessment 范围 |
| 历史合规记录 | ❌ 无专门字段 | ⚠️ |
| 个人信息同意记录 | ❌ 无专门字段 | ⚠️ |

**判定：Assessment ⚠️ 大部分可注入。缺失的企业治理细节字段（股权结构、合规历史）需要扩展或合并到现有 textarea。**

### 2.4 PIPIA (认证/标准合同) — ✅ 良好匹配

**前端表单字段 (≈25个)**，测试案例中的字段基本均有对应。

**判定：PIPIA ✅ 可注入。少数字段需要合并。**

### 2.5 Document Review — ⚠️ 核心依赖文件上传

测试案例包含嵌入的 docx/pdf 样本文件（如 `个人信息出境标准合同【模板】.docx`、`数据处理协议样例.pdf`）。前端表单依赖真实文件上传。

**判定：Review ⚠️ 文本字段可注入，但需要同时解决测试附件的路径引用。**

### 2.6 EU SCC — ✅ 文本字段匹配

**判定：SCC ✅。**

### 2.7 BCR — ✅ 文本字段匹配

**判定：BCR ✅。**

### 2.8 DPIA — ✅ 文本字段匹配

**判定：DPIA ✅。**

### 2.9 TIA — ✅ 文本字段匹配

**判定：TIA ✅。**

### 2.10 US 14117 — ✅ 文本字段匹配

**判定：us_14117 ✅。**

---

## 三、汇总表

| 模块 | 可注入度 | 缺口 | 建议 |
|------|:------:|------|------|
| CPRA | 🟢 高 | 结构化子字段无独立表单 | 走路径B直发JSON |
| Diagnosis | 🟢 高 | 无 | 走路径A（表单字段完美匹配） |
| Assessment | 🟡 中 | 治理细节缺字段 | 部分走路径B |
| PIPIA | 🟢 高 | 少量字段需合并 | 走路径A |
| Review | 🟡 中 | 依赖文件上传 | 路径B + mock附件URI |
| SCC | 🟢 高 | 无 | 走路径A |
| BCR | 🟢 高 | 无 | 走路径A |
| DPIA | 🟢 高 | 无 | 走路径A |
| TIA | 🟢 高 | 无 | 走路径A |
| us_14117 | 🟢 高 | 无 | 走路径A |

---

## 四、建议的一键注入方案

### 4.1 新增文件

```
frontend/src/lib/dev-test-cases.ts   ← 所有测试案例的预编译 JSON payload
backend/api/dev_routes.py            ← 开发模式 endpoint（返回案例列表）
```

### 4.2 实现逻辑

```
┌─ 前端 "开发者模式" 面板 ─────────────────────────┐
│                                                    │
│  选择模块: [CPRA ▾]                                │
│  选择案例: [TrendyGoods 电商 ▾]                    │
│                                                    │
│  ┌─ Payload 预览 ─────────────────────────────┐   │
│  │ {                                           │   │
│  │   "company_name": "TrendyGoods Inc.",       │   │
│  │   "business_model": "线上时尚零售商...",      │   │
│  │   ...                                       │   │
│  │ }                                           │   │
│  └────────────────────────────────────────────┘   │
│                                                    │
│  [直接运行（async）]  [填入表单后手动编辑再运行]      │
│                                                    │
└────────────────────────────────────────────────────┘
```

### 4.3 两种注入模式

**模式 1：直发模式（推荐优先实现）**
```typescript
// 跳过表单，直接把预编译 JSON POST 到后端
async function runDevTestCase(module: ModuleKey, caseId: string) {
  const payload = DEV_TEST_CASES[module][caseId];
  const result = await runModule(definition, payload, "async");
  // 自动打开 timeline tab 观察执行流
}
```

**模式 2：表单回填模式**
```typescript
// 把 payload 反填到表单 state，用户可编辑后再运行
function fillFormWithTestCase(module: ModuleKey, caseId: string) {
  const payload = DEV_TEST_CASES[module][caseId];
  setCpraValues(payload); // 或 setDiagnosisValues(payload)
}
```

Phase 1 建议只做模式 1（直发），因为它：
- 不需要逐个理解每个模块的表单序列化逻辑
- 直接对着后端 schema 发 JSON，精度最高
- 和 SSE 事件流配合最好（async 路径生效）

---

## 五、一句话结论

> **10 个模块中 8 个可直接注入。CPRA 和 Assessment 有字段精度损失但核心断言不受影响。建议先建一个 `frontend/src/lib/dev-test-cases.ts` 预编译所有案例的 JSON payload，前端加一个"开发者模式"下拉面板，选中案例即直接 POST 到 async endpoint，配合 SSE 事件流实时观察执行。**
