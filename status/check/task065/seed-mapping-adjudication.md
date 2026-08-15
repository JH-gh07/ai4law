# task065 T03 — Seed Level B 模块身份裁决（v2.0 校正后）

> 日期：2026-08-15（v2.0 校正；替代 2026-08-13 旧裁决）
> 范围：50 个 seed 案例的模块身份裁决；gap 归零
> 性质：技术裁决（产品能力对照）；法律内容签署仍待法域专家

## 1. 裁决总表

| task_no | declared_task_name | jurisdiction | module_id | mapping_status | decision_reason |
|---|---|---|---|---|---|
| 1 | 合规路径诊断 | cn | `cn.transfer_diagnosis` | partial | 诊断模块主路径 |
| 2 | 安全评估路径 | cn | `cn.security_assessment` | partial | 安全评估模块 |
| 3 | 标准合同路径 | cn | `cn.pipia` | partial | 标准合同（PIPIA）模块 |
| 4 | 文档审查 | cn | `cn.document_review` | partial | 文档审查模块（v2.0 已改对，替代旧名「豁免情形诊断」） |
| 5 | SCC 审查 | eu | `eu.scc_review` | partial | SCC 审查模块 |
| 6 | BCR 审查 | eu | `eu.bcr_review` | partial | BCR 审查模块（v2.0 已改对，替代旧名「TIA 审查」） |
| 7 | DPIA 草案生成 | eu | `eu.dpia` | partial | DPIA 草案生成模块（v2.0 已改对，替代旧名「GDPR 合规诊断」） |
| 8 | TIA 草案生成 | eu | `eu.tia` | partial | TIA 草案生成模块（v2.0 已改对，替代旧名「BD ROD 判断」） |
| 9 | 14117 行政令合规 | us | `us.eo_14117` | partial | EO 14117 模块 |
| 10 | CPRA 合规 | us | `us.cpra` | partial | CPRA 模块 |

## 2. 逐项裁决理由（v2.0 关键修正）

### 2.1 Task 4「文档审查」→ `cn.document_review`

**v2.0 修正**：旧裁决把 task4 映射到 `cn.transfer_diagnosis`（豁免情形诊断），
依据是 v1.0 正文为「豁免情形诊断」Q&A。v2.0 已确认 task4 的真实任务是**文档审查**，
case1/2 正文为《个人信息出境标准合同》草案 / 《隐私政策》跨境章节节选，是待审查文档，
映射到 `cn.document_review`。

### 2.2 Task 6「BCR 审查」→ `eu.bcr_review`

**v2.0 修正**：旧裁决把 task6 映射到 `eu.tia`（TIA 六项表单）。v2.0 已确认 task6 的真实
任务是**BCR 审查**，case1/2 正文为 AlphaTech / BetaCloud 的 Binding Corporate Rules 全文，
映射到 `eu.bcr_review`。

### 2.3 Task 7「DPIA 草案生成」→ `eu.dpia`

**v2.0 修正**：旧裁决把 task7 判为 gap（GDPR 合规诊断七项表单）。v2.0 已确认 task7 的
真实任务是 **DPIA 草案生成**，case1/2 正文为「识别需求 / 描述处理活动 / 咨询过程 / 必要性
与相称性 / 识别风险 / 降低风险 / 签署记录」七组信息，与 `DPIARequest` 的 7 组输入字段对应。

### 2.4 Task 8「TIA 草案生成」→ `eu.tia`

**v2.0 修正**：旧裁决把 task8 判为 gap（BD ROD 判断）。v2.0 已确认 task8 的真实任务是
**TIA 草案生成**，case1/2 正文为「传输方 / 接收方 / 传输数据 / 目的 / 法律基础 / 第三国法律
环境 / 安全措施」等结构化事实，映射到 `eu.tia` 的 `TIAStructuredInput`。

## 3. Gap Ledger

v2.0 校正后 gap 归零，见 `status/check/task065/seed-gap-ledger.json`（`gaps: []`）。

## 4. 结论

- 50 个 seed case 全部有对应产品模块，**gap 归零**。
- `mapping_status` 词汇：`partial`（已支持但 declared 名称是子场景或曾用旧名）。
- 12 个 `pending_correction`（task4/6/7/8 case3/4/5）仍为 v1.0 旧内容，Level B 前隔离。
- 已支持案例的 Level B request adapter 抽取字段映射到正式请求 Schema；适配器必须拒绝关键事实缺失（task065 §T03 禁止伪造）。
- 本裁决为技术裁决，法律内容签署另行处理，不因本裁决改变任何法律结论。

## 5. reviewer 记录

| task_no | reviewer | review_note |
|---|---|---|
| 4 | technical-adjudication (2026-08-15) | v2.0：文档审查 → cn.document_review |
| 6 | technical-adjudication (2026-08-15) | v2.0：BCR 审查 → eu.bcr_review |
| 7 | technical-adjudication (2026-08-15) | v2.0：DPIA 草案生成 → eu.dpia |
| 8 | technical-adjudication (2026-08-15) | v2.0：TIA 草案生成 → eu.tia |
