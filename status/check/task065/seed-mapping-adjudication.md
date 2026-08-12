# task065 T03 — Seed Level B 模块身份裁决

> 日期：2026-08-13
> 范围：50 个 seed 案例的模块身份裁决；未支持案例登记 gap
> 性质：技术裁决（产品能力对照）；法律内容签署（Q2）仍待法域专家

## 1. 裁决总表

| task_no | declared_task_name | jurisdiction | module_id | mapping_status | decision_reason |
|---|---|---|---|---|---|
| 1 | 合规路径诊断 | cn | `cn.transfer_diagnosis` | partial | 诊断模块主路径 |
| 2 | 安全评估路径 | cn | `cn.security_assessment` | partial | 安全评估模块 |
| 3 | 标准合同路径 | cn | `cn.pipia` | partial | 标准合同（PIPIA）模块 |
| 4 | 豁免情形诊断 | cn | `cn.transfer_diagnosis` | partial | 豁免是诊断模块的法定情形之一（见 `03_exemption` CLI case） |
| 5 | SCC 审查 | eu | `eu.scc_review` | partial | SCC 审查模块 |
| 6 | TIA 审查 | eu | `eu.tia` | partial | TIA 六项表单直接对应 `eu.tia` structured input |
| 7 | GDPR 合规诊断 | eu | — | gap | 无 GDPR 合规诊断模块；七项表单 ≠ DPIA/BCR/SCC/TIA |
| 8 | BD ROD 判断 | eu | — | gap | 无 GDPR 适用性/元数据/控制者-处理者判断模块 |
| 9 | 14117 行政令合规 | us | `us.eo_14117` | partial | EO 14117 模块 |
| 10 | CPRA 合规 | us | `us.cpra` | partial | CPRA 模块 |

## 2. 逐项裁决理由

### 2.1 Task 4「豁免情形诊断」→ `cn.transfer_diagnosis`（partial）

**输入证据**：Q&A 形式与 Task 1 相同，问题域为「是否属于法定豁免情形」「合同履行必需」等。

**裁决依据**：`cn.transfer_diagnosis` 的 CLI case `03_exemption` 即为豁免路径，模块本身覆盖「安全评估 / 标准合同 / 豁免」三条路径判定。豁免不是独立产品，而是诊断模块的一个判定分支。

**结论**：映射到 `cn.transfer_diagnosis`，`mapping_status=partial`（declared 名称「豁免情形诊断」是诊断模块的子场景）。

### 2.2 Task 6「TIA 审查」→ `eu.tia`（partial）

**输入证据**：表单标题「TIA审查表单（六项信息）」，六项为「了解传输 / 识别传输工具 / 评估目的地法律与实践 / 识别补充措施 / 实施步骤 / 定期复审」。

**裁决依据**：`eu.tia` 的 `TIAStructuredInput` 字段（exporter/importer/destination country、transfer_purpose、data_categories、supplementary measures 等）与该六项表单一一对应。TIA 模块是产品已支持的 EU 模块之一。

**结论**：映射到 `eu.tia`，`mapping_status=partial`。

### 2.3 Task 7「GDPR 合规诊断」→ gap

**输入证据**：表单标题「GDPR合规诊断表单（七项信息）」，七项为「识别需求 / 描述处理活动 / 咨询过程 / 必要性与相称性 / 识别与评估风险 / 降低风险的措施 / 签署与记录」。

**裁决依据**：当前 10 个业务模块中无「GDPR 合规诊断」能力。七项表单虽与 DPIA（Art.35）结构相似，但主体是 GDPR 合规诊断，且含「识别需求」「咨询过程」「签署与记录」等 DPIA 之外的诊断步骤。强行映射到 `eu.dpia` 会改变业务事实，违反「不得硬塞到相近模块」原则。

**结论**：`mapping_status=gap`。缺失能力：GDPR 合规诊断产品能力。

### 2.4 Task 8「BD ROD 判断」→ gap

**输入证据**：表单标题「数据处理项目描述 / 各方关系陈述」，内容涉及通信元数据是否属于个人数据、匿名化效力、控制者-处理者责任是否可通过合同转移。

**裁决依据**：当前模块无「GDPR 适用性 / 元数据定性 / 控制者-处理者责任判断」能力。这不属于 SCC 审查、TIA、DPIA、BCR 任一模块。强行映射会改变业务事实。

**结论**：`mapping_status=gap`。缺失能力：GDPR 适用性与数据处理角色判断产品能力。

## 3. Gap Ledger

见 `status/check/task065/seed-gap-ledger.json`。

| task_no | case_ids | source | 缺失能力 | 影响 | 后续任务 |
|---|---|---|---|---|---|
| 7 | task07_case1..5 | 7 项 GDPR 合规诊断表单 | GDPR 合规诊断产品能力 | 无法进入默认 runner | 待产品定义 GDPR 诊断需求后再评估 |
| 8 | task08_case1..5 | 数据处理项目描述 / 各方关系陈述 | GDPR 适用性与角色判断产品能力 | 无法进入默认 runner | 待产品定义后再评估 |

## 4. 结论

- 50 个 seed case 中：30 个已支持（task 1/2/3/5/9/10），10 个经裁决已支持（task 4/6），10 个 gap（task 7/8）。
- `mapping_status` 词汇：`partial`（已支持但 declared 名称是子场景）、`gap`（无产品能力）。
- 已支持案例的 Level B request adapter 将抽取字段映射到正式请求 Schema；适配器必须拒绝关键事实缺失。
- 本裁决为技术裁决，法律内容签署（Q2）另行处理，不因本裁决改变任何法律结论。

## 5. reviewer 记录

| task_no | reviewer | review_note |
|---|---|---|
| 4 | technical-adjudication (2026-08-13) | 豁免 = 诊断子路径；待法域专家确认 |
| 6 | technical-adjudication (2026-08-13) | 六项表单与 TIAStructuredInput 对应；待法域专家确认 |
| 7 | technical-adjudication (2026-08-13) | 无产品能力，登记 gap |
| 8 | technical-adjudication (2026-08-13) | 无产品能力，登记 gap |
