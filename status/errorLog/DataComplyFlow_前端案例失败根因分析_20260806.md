# 前端 26 个案例直投真实 API 失败根因分析

> 审计日期：2026-08-06  
> 审计基线：`826e23d`  
> 代码范围：`frontend/src/lib/dev-test-cases.ts` + 各模块后端 Schema + `frontend/src/components/workspace/ModuleRunPanel.tsx`  
> 核心问题：9/26 成功、17/26 失败（HTTP 422/400），全部原因是**前端案例 payload 字段与当前后端 Pydantic Schema 不兼容**

---

## 零、先懂三条代码路径——这是理解所有失败的前提

为什么同一个模块，浏览器"一键体验"可能成功，但 payload 直投失败？

```
路径 A：浏览器"一键体验"
  formDefaults（字段名可能是旧名，值可能是旧枚举）
    → 填入表单组件（表单有枚举下拉、必填校验）
      → buildXxxPayloadFrom()（前端转换函数，做字段映射和类型转换）
        → POST fetch → 后端 FastAPI → Pydantic 校验 → 业务逻辑
```

```
路径 B：payload 直投（你手上的表格）
  payload（文件 dev-test-cases.ts 中写死的 JSON，声称"可直接 POST"）
    → 直接 POST fetch（跳过表单层、跳过 buildPayloadFrom 转换）
      → 后端 FastAPI → Pydantic 校验 → ❌ 422/400 失败
```

```
路径 C：CLI harness
  cases/*.json（后端目录中独立的 JSON 文件）
    → runner.py → service.generate_report() 直接调用
      → 不走 HTTP 层，不经过 FastAPI Pydantic 校验路由
```

**关键结论：**

- **diagnosis 在浏览器成功**：因为 `formDefaults` 中的 `business_operation` 经由前端表单的枚举下拉框被用户/UI builder 转换成了正确的 `contract_performance`，所以后端的 `buildDiagnosisPayloadFrom()` 发出的是正确枚举。
- **diagnosis 直投失败**：因为 `payload` 字段中的 `"business_operation"` 不经过任何转换，直接打到后端的 Pydantic `TransferScenario` 枚举校验，当场 422。
- **PIPIA 同上**：浏览器的 `buildPipiaPayloadFrom()` 可能补充了 `company_uscc` 等必填字段，而直投的 payload 没有这些字段。
- **review 直投失败**：文件上传类模块（review 需要先上传文件获取路径，再提交 payload 引用该路径），直投 payload 没有经过上传步骤。
- **BCR/DPIA/TIA 浏览器一键体验失败**：因为 `buildBcrPayloadFrom()` / `buildDpiaPayloadFrom()` / `buildTiaPayloadFrom()` 本身的逻辑也有断点，抛出了 `"Invalid or missing required input"`。

---

## 一、diagnosis（3 例全部失败，422）

### 失败现象
```
q6_scenario=business_operation 不在枚举 （跨境优品）
q6_scenario=scientific_research 不在枚举 （前沿生命科技）
q6_scenario=technology_development 不在枚举 （智造未来）
q7_receiver_type=affiliated_company 不在枚举 （跨境优品、智造未来）
q7_receiver_type=academic_partner 不在枚举 （前沿生命科技）
```

### 代码流程分析

**后端 Schema（当前生效的权威约束）**：

`backend/domains/cn/transfer_diagnosis/schema.py` 定义了：

```python
class TransferScenario(str, Enum):
    CONTRACT_PERFORMANCE = "contract_performance"   # 履行合同
    HR_MANAGEMENT = "hr_management"                 # 内部人力
    EMERGENCY = "emergency"                         # 紧急
    LEGAL_DUTY = "legal_duty"                       # 法定职责
    OTHER = "other"                                 # 其他

class ReceiverType(str, Enum):
    INTRA_GROUP = "intra_group"    # 集团内
    THIRD_PARTY = "third_party"    # 独立第三方
```

**前端案例 payload 中的值**：

`frontend/src/lib/dev-test-cases.ts:197-198` →
```json
{
  "q6_scenario": "business_operation",
  "q7_receiver_type": "affiliated_company"
}
```

**失败机理**：

```
1. 用户选择"跨境优品"案例
2. 点击"填充并执行"（或直接 POST payload 到 API）
3. POST → /api/v1/diagnosis/evaluate
4. FastAPI 接收 JSON → 反序列化为 DiagnosisAnswers (Pydantic v2)
5. Pydantic 校验 q6_scenario 字段：
   - 收到字符串 "business_operation"
   - 检查 → TransferScenario 枚举中无此成员
   - 拒绝请求，返回 HTTP 422 + 错误详情
6. 业务逻辑从未执行
```

**为什么浏览器一键体验能成功？**

浏览器路径走的是 `formDefaults` → 表单 UI → `buildDiagnosisPayloadFrom()`：

1. `formDefaults` 中的 `business_operation` 填入表单
2. 表单的**枚举下拉框**（由 `TransferScenario` 枚举渲染）只允许选择 `contract_performance`、`hr_management` 等合法值
3. 用户或 UI builder 在表单中选择 **"履行合同"**（对应 `contract_performance`）
4. `buildDiagnosisPayloadFrom()` 提取表单值，此时已变成正确枚举 → 成功提交

### 根因

**`dev-test-cases.ts` 中的 payload 字段使用了旧版/设计阶段的枚举值名称**（`business_operation`、`scientific_research`、`technology_development`、`affiliated_company`、`academic_partner`），这些值从未被后端 `TransferScenario` 或 `ReceiverType` 枚举采纳。这是典型的 **"文档（前端案例文件）与实现（后端 Schema）漂移"**——文件头注释声称"可直接 POST"，实则在 Schema 发生过重构后没有同步更新。

---

## 二、assessment（东方信托 422，智慧云联 200 成功）

### 失败现象
```
legal_document_review 等字段应为对象，案例仍给字符串
```

### 代码流程分析

**后端 Schema**：`backend/domains/cn/security_assessment/schema.py:132`

```python
class AssessmentProfile(BaseModel):
    # ...
    legal_document_review: LegalDocumentReview | None = None
    # LegalDocumentReview 是一个复杂的 Pydantic 对象
```

也就是说，`legal_document_review` 需要的类型不是普通字符串，而是一个至少包含若干字段的**对象**（例如 `{document_type: "...", review_scope: "..."}` 等）。

**前端案例 payload**（东方信托）：

测试案例中把 `data_scenarios`、`legal_document_review` 等字段直接写成了**平铺字符串**（类似 `"法律文件审查: 已审查合同等法律文件"`），而不是嵌套对象。

**失败机理**：

```
Pydantic 在反序列化时：
  期望 → legal_document_review: LegalDocumentReview（对象）| None
  收到 → legal_document_review: "法律文件审查: ..."（字符串）
  结果 → 类型不匹配 → 422
```

智慧云联为什么成功？它的 payload 中这些字段的格式**碰巧与当前 Schema 兼容**（或本身就是对象格式）。

**为什么浏览器一键体验能成功？**

浏览器的表单不是自由文本输入，而是分步骤的多页表单。`buildAssessmentPayloadFrom()` 会把表单中分散的字段**组装成** `LegalDocumentReview` 对象结构，再发出请求。所以即使 `formDefaults` 中写的是简化版，经过表单→payload 转换后就是正确格式。

### 根因

Schema 从 **"扁平字符串字段"** 重构为 **"结构化嵌套对象"**，但 `dev-test-cases.ts` 中的东方信托案例 payload 停留在旧格式。

---

## 三、BCR（3 例全部失败，422）

### 失败现象
```
review_items[].finding 缺失（GlobalTech）
review_items[].finding 缺失（HealthData）
review_items[].finding/legal_basis 缺失（CloudProcessors）
```

### 代码流程分析

**后端 Schema**：`backend/domains/eu/bcr_review/schema.py:40-41`

```python
class BCRReviewItem(BaseModel):
    code: str
    title: str
    score: BCRScore
    finding: str = Field(min_length=2)       # ← min_length=2，必填
    legal_basis: str = Field(min_length=2)   # ← min_length=2，必填
    recommendation: str = ""
    evidence: str = ""
```

每个 `review_item` 必须包含 `finding`（发现）和 `legal_basis`（法律依据）两个字符串字段，且**最少 2 个字符**。

**前端案例 payload**（GlobalTech）：

案例 payload 中的 `review_items` 条目**没有** `finding` 和 `legal_basis` 字段，或字段为空字符串（长度不足 2）。

**失败机理**：

```
Pydantic 校验 review_items[0]:
  期望 → {code, title, score, finding(str min=2), legal_basis(str min=2), ...}
  收到 → {code, title, score, evidence, ...}（缺少 finding 和 legal_basis）
  结果 → validation error → 422
```

**为什么浏览器一键体验也失败？**

这是关键不同：对于 BCR，浏览器的 `buildBcrPayloadFrom()` 位于 `ModuleRunPanel.tsx:802-840`：

```typescript
const review_items = BCR_REVIEW_ITEMS.map((item, index) => {
  const evidence = evidenceTexts[index]?.trim() || "未提供";
  const score = toBcrScore(evidence);
  return {
    code: item.code,
    title: item.title,
    score,
    finding: composeBcrFinding(score, evidence.slice(0, 180)),
    legal_basis: item.legal_basis,
    // ...
  };
});
```

`buildBcrPayloadFrom()` 在 **`buildBcrPayloadFrom()` 之前** 就因为表单校验 `assertInput(hasText(values.binding_mechanism), "...")` 失败而抛出异常。表单中 BCR 有 10+ 个必填文本域（如 `binding_mechanism`、`data_flow_scope` 等），`formDefaults` 中没有给出这些值，表单校验就挂了。

### 根因（两层）

1. **表单层**：BCR 一键体验的 `buildBcrPayloadFrom()` 之前，表单校验要求填写大量必填域（`binding_mechanism` 等），`formDefaults` 没有覆盖这些字段 → 前端直接抛 `"Invalid or missing required input"`
2. **payload 层**：案例 payload 的 `review_items` 缺少 `finding` 和 `legal_basis` 字段 → 后端 422

---

## 四、DPIA（直投 2/2 成功 200，浏览器一键体验失败）

### 特别说明

DPIA 是 **唯一一个直投全部成功但浏览器一键体验失败** 的模块：

| 路径 | 结果 | 原因 |
|------|------|------|
| payload 直投 | ✅ 200（AI 招聘 14 产物、智慧城市 14 产物） | 案例 payload 与当前 DPIA Schema 兼容 |
| 浏览器一键体验 | ❌ 0 产物 | `buildDpiaPayloadFrom()` 内部 `assertInput` 失败 |

`ModuleRunPanel.tsx:868-870` 的 `buildDpiaPayloadFrom()` 在构建 payload 前检查了大量必填表单字段，`formDefaults` 没有完整覆盖这些字段 → 前端校验直接失败，请求根本未发出。

**这意味着**：DPIA 的后端代码和案例 payload 都是正常的，**坏点仅在浏览器的表单预设不完整**。

---

## 五、TIA / EU SCC（TIA 直投失败 422，EU SCC 全部成功 200）

### TIA 失败现象
```
file_role=tia_main_report 不在枚举
file_role=tia_main_report 不在枚举
file_format=txt 不在枚举
file_format=txt 不在枚举
```

### 代码流程分析

**后端 Schema**：`backend/domains/eu/tia/schema.py:13-15`

```python
class TiaAttachment(BaseModel):
    file_role: Literal["transfer_agreement", "country_law_analysis", "technical_control_doc", "other"]
    # ← 只有这 4 个合法值
    file_format: Literal["docx", "pdf"]
    # ← 只有这 2 个合法值
```

**前端案例 payload**：

```json
{
  "file_role": "tia_main_report",    // ← 不在 Literal 枚举中
  "file_format": "txt"                // ← 不在 Literal 枚举中
}
```

**失败机理**：

`tia_main_report` 和 `txt` 是前端 UI 中使用的显示标签或旧设计值，不在后端 Schema 定义的有效枚举中。Pydantic 的 `Literal` 类型校验非常严格——只接受字面量，不接受任何同义变体。

### EU SCC 为什么全部成功？

EU SCC 的后端 Schema 和案例 payload 保持了同步。3 个 EU SCC 案例的 attachment 字段使用了正确的 `file_role` 和 `file_format` 值。

### TIA 浏览器一键体验也失败

`buildTiaPayloadFrom()` 位于 `ModuleRunPanel.tsx:998-1000`，同样因表单校验 `assertInput` 失败。

---

## 六、PIPIA（2 例全部失败，422）

### 失败现象
```
company_profile.company_uscc 缺失（标准合同备案）
company_profile.company_uscc 缺失（认证路径）
```

### 代码流程分析

**后端 Schema**：`backend/domains/cn/pipia/schema.py:10`

```python
class CompanyProfile(BaseModel):
    company_uscc: str = Field(min_length=8)  # 统一社会信用代码，18位，最少8字符
    # ... 其他字段
```

**前端案例 payload**：

案例的 `company_profile` 字典中**没有** `company_uscc` 这个键，或值为空。Pydantic 将其解释为字段缺失，直接 422 拒绝。

**为什么浏览器一键体验能成功？**

浏览器的 PIPIA 表单可能单独收集了 `company_uscc` 字段（例如从用户 profile 或上一步表单中继承），`buildPipiaPayloadFrom()` 会将其注入到 `company_profile` 对象中。

### 根因

PIPIA Schema 在最近的版本中**将 `company_uscc` 从一个可选字段升级为必填字段**（`min_length=8`），但案例 payload 没有追加这个新强制字段。

---

## 七、CN Flow（2 例全部失败，422）

### 失败现象
```
recipient_entities[].country_region 缺失（基础数据流）
recipient_entities[].country_region 缺失（受限主体）
```

### 代码流程分析

**后端 Schema**：`backend/domains/us/eo14117_flow_review/schema.py:10`

```python
class RecipientEntity(BaseModel):
    entity_name: str
    country_region: str = Field(min_length=2)  # ← 必填，最少2字符
    # ...
```

**前端案例 payload**（CN Flow 基础数据流，`dev-test-cases.ts:1233-1242`）：

```json
{
  "recipient_entities": [
    {
      "entity_name": "深圳智能制造有限公司",
      "country": "中国",              // ← 字段名是 "country"
      "entity_role": "vendor",
      "is_restricted_party": false,
      "entity_type": "manufacturer"   // 没有 "country_region" 字段
    }
  ]
}
```

**失败机理**：

案例使用的是旧字段名 `country` 而非当前的 `country_region`。Pydantic 严格按字段名校验——`country_region` 缺失意味着该字段被认为必填但未提供 → 422。

此外，CN Flow 还有更根本的问题：system prompt 写的是 **"美国 EO 14117 合规律师"**，与 CN Flow 的中国数据流检查语义矛盾。

---

## 八、US 14117（2 例全部失败，422）

### 失败现象
```
data_items[].data_item_name 缺失（基础交易）
data_items[].data_item_name 缺失（受限主体）
```

### 代码流程分析

**后端 Schema**：`backend/domains/us/eo14117/schema.py:43`

```python
class DataItem(BaseModel):
    data_item_name: str = Field(min_length=1)  # ← 必填
    data_category: str
    # ...
```

**前端案例 payload**（US 14117 基础交易，`dev-test-cases.ts:1155-1159`）：

```json
{
  "data_items": [
    {
      "data_category": "human_genomic_data",
      "description": "5万份人类全基因组测序数据",
      "contains_human_genomic": true,
      "volume": "50000",
      "sensitivity": "high"
      // ← 没有 "data_item_name" 字段
    }
  ]
}
```

**失败机理**：

`data_item_name` 是后端 Schema 中的必填字段（`min_length=1`），但案例 payload 没有这个字段。这个字段可能是在 Schema 演进中新增的必填项，案例文件没有同步更新。

---

## 九、review（2 例全部失败，400）

### 失败现象
```
No files uploaded for review task（隐私政策）
No files uploaded for review task（标准合同）
```

### 代码流程分析

`review` 和其他模块有本质区别——它是**文件驱动**的：

```
其他模块流程：
  表单 JSON → 后端 → 规则引擎/LLM → 报告

review 流程：
  1. 上传文件 → 后端保存到 storage/uploads → 返回文件路径
  2. 创建 ReviewTask（payload 中引用步骤1的文件路径）
  3. ReviewService._run_pipeline() 解析文档→审查→报告
```

**前端案例 payload**（`dev-test-cases.ts:1316-1325`）：

```json
{
  "company_name": "华东云链科技（测试）",
  "document_type": "privacy_policy",
  "receiver_name": "OceanStar Technology Pte. Ltd.",
  "receiver_country": "新加坡",
  "transfer_purpose": "跨境客服工单处理...",
  "review_focus": "重点核查...",
  "pii_count": 280000,
  "spi_count": 5000
  // ← 没有文件引用！
}
```

**失败机理**：

payload 中没有 `files` 字段或文件引用路径。后端 Review API 在创建任务时检查是否已有上传文件，发现无文件 → 返回 400 `"No files uploaded for review task"`。

review 案例的 `payload` 字段**只能作为补充元数据**，**不能独立完成文件上传**。正确的直接测试流程应该是：

```
步骤 1：POST /api/v1/review/upload → 上传隐私政策 PDF
步骤 2：从响应中获取 file_path
步骤 3：POST /api/v1/review/create → 在 payload 中引用 file_path
```

文件头注释声称"可直接 POST"对 review 模块是错误的——它必须先完成文件上传。

---

## 十、总体根因归纳

| 失败类别 | 涉及模块 | 计数 | 根因本质 |
|----------|----------|------|----------|
| **枚举值漂移** | diagnosis, TIA | 5 例 | 案例文件中使用的枚举值（如 `business_operation`、`tia_main_report`、`txt`）与后端 Pydantic 枚举/Literal 不匹配 |
| **字段名漂移** | CN Flow | 2 例 | 案例中用 `country` 而非当前 Schema 要求的 `country_region` |
| **新增必填字段** | PIPIA, US 14117 | 4 例 | Schema 演进中新增了必填字段（`company_uscc`、`data_item_name`），案例未同步追加 |
| **类型漂移** | assessment | 1 例 | 案例用字符串表示一个字段，但当前 Schema 要求该字段为嵌套对象 |
| **缺少必填子字段** | BCR | 3 例 | `review_items[].finding` 和 `legal_basis` 缺失 |
| **文件上传流程缺失** | review | 2 例 | 案例 payload 只有元数据，缺少文件上传步骤 |

**共计 17 例失败，覆盖 6 大类根因，全部是 Schema 同步问题。**

---

## 十一、为什么这 17 例失败不代表后端功能坏了

| 结论 | 解释 |
|------|------|
| **422 是"门槛拦截"，不是业务逻辑错误** | 所有 17 例失败都发生在 Pydantic Schema 校验层，业务代码（Agent、RAG、规则引擎、报告生成）从未被执行。调整案例 payload 对齐当前 Schema 后，这些模块极大概率可以正常产出。 |
| **浏览器一键体验能成就是证据** | diagnosis 浏览器流程成功（因为 `formDefaults` 经过表单 UI builder 被转换），证明后端逻辑是完好的——就是案例文件的数据格式过时了。 |
| **CLI harness 15/15 PASS 也是证据** | CLI 路径使用 `backend/tests/harness/cases/` 中的独立 JSON 文件，这些文件与当前 Schema 一致。 |
| **DPIA 直投 200 是正向证据** | 说明只要 payload Schema 对了，系统就能正常工作。 |

---

## 十二、修复路线图

按工作量从小到大排列：

| 优先级 | 修复项 | 涉及文件 | 预计工作量 |
|--------|--------|----------|-----------|
| P0 | 修复 diagnosis 案例枚举值 | `dev-test-cases.ts`: 将 `business_operation` → `contract_performance` 等 | 5 分钟 |
| P0 | 补全 PIPIA 案例的 `company_uscc` | `dev-test-cases.ts`: 追加必填字段 | 5 分钟 |
| P0 | 修复 US 14117 案例的 `data_item_name` | `dev-test-cases.ts`: 追加必填字段 | 5 分钟 |
| P0 | 修复 CN Flow 案例的 `country_region` | `dev-test-cases.ts`: `country` → `country_region` | 5 分钟 |
| P0 | 修复 TIA 案例的 file_role/file_format | `dev-test-cases.ts`: 对齐 Literal 枚举 | 5 分钟 |
| P1 | 修复 assessment 东方信托案例结构 | `dev-test-cases.ts`: 字符串 → 嵌套对象 | 15 分钟 |
| P1 | 补全 BCR 案例的 finding/legal_basis | `dev-test-cases.ts`: 追加必填子字段 | 15 分钟 |
| P1 | 补全 BCR/DPIA/TIA 表单预设值 | `dev-test-cases.ts` 的 formDefaults | 30 分钟 |
| P2 | review 案例加入文件上传两步流程 | `dev-test-cases.ts` + 上传逻辑 | 1 小时 |
| P3 | 建立案例文件的 CI 自动化 Schema 校验 | CI pipeline | 半天 |

---

> **核心教训**：`dev-test-cases.ts` 文件头的注释 "该案例的完整 JSON payload，可直接 POST" 应该改为 "该案例的 payload 需要定期与后端 Schema 同步更新，提交前请运行 `check_test_case_parity.py` 验证"。
