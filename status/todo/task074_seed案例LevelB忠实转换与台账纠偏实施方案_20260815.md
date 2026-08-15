# task074 — 种子案例 Level B 忠实转换与台账纠偏实施方案

> **日期**：2026-08-15
> **关联**：`task065`（seed 三级管线）、`task071`（前端开发期入口去重）、`task072`（v2.0 校正）、`issue071`
> **目标**：纠正"Level B 代码已全部落实、36 个 rejected 只能人工补"的错误结论；把仍可由代码消除的误判/派生项与真正的人工项精确分开，并给出可执行顺序。
> **性质**：技术纠偏 + 代码实施方案（不含法律结论签署 / 金标签署）。

> ✅ **执行结果（2026-08-15）**：Phase A/B/C/D 已全部落实并提交（`998482c9`）。随后按用户授权，对**占位符主体名**（task02/03 的公司名 / 接收方名，仅替换不影响业务的标识名，业务事实一律不碰）替换为测试名，使 task02_case4 由 rejected 转 converted。最终台账：**converted 9 / rejected 29 / pending_correction 12 / gap 0**。同时补装 item 4（LibreOffice + 可再分发 CJK 字体 `resources/fonts/NotoSansSC-Regular.ttf`），PDF CJK 字体嵌入门已由 blocked 转 pass。item 3（gold 签署）属法域专家验收项，本 task 不做。

---

## 一、背景与问题

上一轮汇报曾给出错误结论：**"Level B 代码能做的已全部做完，剩余 36 个 rejected 只能人工补"**。经逐项核验，机械计数属实，但结论不属实：

- 2 个 `converted`（task07_case1/2，DPIA）**只是"schema 能过"，不是"源数据忠实"**，其中 `special_category_data: false`、`cross_border_transfer: false`、`vulnerable_data_subjects: false` 与原文相反，是反向伪造。
- 36 个 `rejected` 里**仍有代码可消除的解析误判和可派生的附件项**，不能一概归为人工补。
- v2.0 的**台账与 provenance 尚未同步**（gap ledger、mapping adjudication、issue071、task071、manifest 五处仍是旧状态）。

## 二、范围与非范围

**范围（本 task）**：

1. 修复两个纯解析 bug（`_parse_count`、`_parse_ynu`）。
2. DPIA adapter 忠实提取（消除反向 `false`）。
3. TIA adapter 改走 `structured_input`，结论由系统产出（不再把结论字段当 input）。
4. task04/06 从源 DOCX 派生 input-only 附件（消除 `uploaded_files` / `uploaded_documents` 误判）。
5. 同步五处台账 + provenance + git 跟踪。
6. 新增 request↔源段落忠实性防回归测试。

**非范围（明确不做，另行处理）**：

- 12 个 `pending_correction`（task4/6/7/8 case3/4/5）的 v1.0→v2.0 正文 authoring（数据 owner）。
- 占位符主体名 / 原文没写结构化字段的 authoring（数据 owner）。
- `expected.json`（gold）签署（法域专家，验收阶段，非 Level B）。
- 任何法律结论的生成。

---

## 三、准确现状（纠偏后）

> Level A / Level B 基础管线、隔离机制和 10 个 adapter 骨架已能运行，机械结果 **2 converted / 36 rejected / 12 pending_correction / 0 gap**。但 converted 是伪完整；rejected 含可代码消除项；台账未同步。

| 声明 | 结论 |
|---|---|
| 2/36/12/0 机械计数 | 属实 |
| 12 个 case3/4/5 隔离 | 属实 |
| 2 个 converted 源数据完整 | **不属实**（schema 能过 ≠ 忠实） |
| 36 个 rejected 全部只能人工补 | **不属实**（含解析 bug + 可派生附件） |
| 台账 / provenance 已同步 | **不属实**（五处仍旧） |

---

## 四、关键问题与根因

### 问题一：DPIA 两个 converted 是"伪完整"

`_adapter_dpia`（`scripts/build_seed_case_requests.py:505`）只提 3 个字段，其余全 schema 默认值：

| 原文（task07_case1）明确写 | request 却写成 | 定性 |
|---|---|---|
| 健康/基因/种族·民族数据 | `data_categories: []` | 漏提 |
| 种族/民族 = 特殊类别 | `special_category_data: false` | 反向 |
| 数据主体含未成年人 | `vulnerable_data_subjects: false` | 反向 |
| 影像保留 10 年等 | `retention_period: ""` | 漏提 |
| 第 6/9/22 条法律基础 | `lawful_basis: []` | 漏提 |
| 模型参数传以色列 + VPN 访问日志 | `cross_border_transfer: false` | 反向 |

三个 `false` 主动声明"无"，违反 task065 §T03 禁止伪造。现有测试 `test_seed_case_requests.py:241` 只验 schema+占位符，**不验 request↔源段落一致性**。

### 问题二：task04/06 有可用 DOCX，却被判"无文件"

- `task04_case1.source_docx`（hash `3bb623…`，90234B）正文即《个人信息出境标准合同》全文；
- `task06_case1.source_docx`（hash `5644cd…`，14225B）正文即 AlphaTech BCR 全文。

`_adapter_document_review` 恒返 `["uploaded_files"]`、`_adapter_bcr_review` 恒返 `["uploaded_documents"]`，是误判。可从源 DOCX 派生 input-only 附件（复制/规范化进 storage），**非伪造**。

### 问题三：解析 bug 仍在

1. `_parse_count`（`:99`）看到 `<`/`>` 就整体拒绝：`task01_case5` 的 `"<1万。5000人的全基因组数据。"` 明确有 `5000人`，却判 `answers.q4_spi_count` 缺失。
2. `_parse_ynu`（`:92`）否定词匹配顺序错误：`不属于CIIO`、`不包含敏感信息`、`不含敏感信息` 都因肯定子串（`不属于`/`包含敏感`/`含敏感`）先命中而返回 `yes`。

### 问题四：TIA 结论字段被错当 input

`TIARequest` 有两条输入路径（`backend/domains/eu/tia/schema.py:110-120`）：

| 路径 | 字段 | 性质 |
|---|---|---|
| 旧表单（backward compat） | `data_exporter_profile`/`data_importer_profile`/`third_country_assessment`/`supplementary_measures`/`final_conclusion`（均 `min_length=2`） | 用户自填文本，后两项是"用户结论" |
| 新结构化（NEW） | `structured_input`（`TIAStructuredInput`） | 事实输入，系统产 `TIADecision` |

`service.py:155-176` 证明：有 `structured_input` 时系统自产结论；仅旧表单才用 `final_conclusion` 推断风险。当前 `_adapter_tia`（`:370-408`）走旧表单，把 `final_conclusion`/`third_country_assessment` 当必填结论 blocking——**这是 adapter 走错路径，不是 seed 缺结论**。

### 问题五：台账 / provenance 五处未同步

| 文件 | 现状 | 应为 |
|---|---|---|
| `status/check/task065/seed-gap-ledger.json` | 仍记 task07/08 gap（旧名） | gap 清空 |
| `status/check/task065/seed-mapping-adjudication.md` | 旧任务名+旧映射 | review/bcr/dpia/tia |
| `status/issue/issue071…md:216` | `requests/ 空`、`40 rejected+10 gap` | 2 request、2/36/12/0 |
| `status/todo/task071…md:254` | "0 个成功" 与 "converted 2" 自相矛盾 | 统一为 2/36/12/0 |
| `manifest.json` | gold_standard 仍指 `_v1.0.docx` | v2.0 进 provenance |
| git | 2 个 request + v2.0 源目录未跟踪 | 纳入跟踪 |

---

## 五、代码可落实项（本 task 执行）

按优先级：

### Phase A — 纯解析 bug（低风险，先做）

| # | 项 | 改动 | 验证 |
|---|---|---|---|
| A1 | `_parse_count` | 先提取明确数字（`(\d+)\s*(万|千)?\s*(人|名|用户)?` 且不紧跟模糊前缀），再判断是否整体含 `<`/`>`/`约`/`几`；支持 `"<1万。5000人"` 取 `5000` | `task01_case5` → `answers.q4_spi_count=5000` |
| A2 | `_parse_ynu` | 先匹配否定词（`不属于/不包含/不含/不涉及/^否`）→ `no`，再匹配肯定词 → `yes` | `不属于CIIO`→no、`不含敏感`→no |

### Phase B — 忠实转换（adapter 重构）

| # | 项 | 改动 | 验证 |
|---|---|---|---|
| B1 | DPIA 忠实提取 | 从原文提取 `data_categories`、`special_category_data/types`、`data_subject_categories`、`vulnerable_data_subjects`（未成年人）、`retention_period`、`lawful_basis`、`cross_border_transfer`+`transfer_destination`；**只有原文确实写"无跨境/无特殊类别"时才填 false**，否则缺省不留反向 false | request 与 task07_case1/2 原文逐项一致 |
| B2 | TIA 走 `structured_input` | 提取 exporter/importer 国家、角色、`transfer_purpose`、`data_categories`、`has_special_category_data`、`transfer_frequency/scale`、加密相关布尔；`final_conclusion`/`third_country_assessment` **不再作为 blocking** | TIA 结论由 `TIADecision` 产出 |
| B3 | task04/06 附件派生 | 从 `source_docx` 复制/规范化出 input-only DOCX 到 storage，填入 `uploaded_files`/`uploaded_documents`（带 provenance：源 hash/路径） | `_adapter_document_review`、`_adapter_bcr_review` 可 converted |

> B2 前置决策：`TIARequest` 5 个旧字段 `min_length=2` 硬必填。建议改 schema 让 5 个旧字段在 `structured_input` 存在时可空（`str = ""` 可选），并对 `backend/domains/eu/tia/tests/` 做回归；否则 `final_conclusion` 无法忠实填值。

### Phase C — 台账 / provenance 同步

| # | 项 |
|---|---|
| C1 | 清空 `seed-gap-ledger.json` 的 gap 项（或标注"v2.0 已全部映射"） |
| C2 | 重写 `seed-mapping-adjudication.md` 为 v2.0（task4=文档审查/`cn.document_review`、task6=BCR/`eu.bcr_review`、task7=DPIA/`eu.dpia`、task8=TIA/`eu.tia`） |
| C3 | 修 `issue071:216`、`task071:254` 为 2/36/12/0 一致口径 |
| C4 | `manifest.json` 补 v2.0 gold 来源 provenance；git 跟踪 2 个 request + v2.0 源目录 |

### Phase D — 忠实性防回归测试

| # | 项 |
|---|---|
| D1 | 新增 test：对每个 converted request，断言其布尔/列表字段与源段落一致（无"原文有、request 却 false/空"的反向声明） |
| D2 | 重跑 `pytest backend/tests/harness/`，保持 `test_seed_case_requests.py` 现状 28 passed + 新增通过 |

---

## 六、真正的人工 / 专家项（纠偏后精确分类）

### 6.1 占位符污染的主体 —— 可替换测试名，非阻塞、非专家 ✅ 已替换

| 功能 | 字段 | 原文 | 已补（测试名，仅标识、不影响业务） |
|---|---|---|---|
| task02 安全评估 | `company_name` | `XX城商银行…` | `临江城商银行股份有限公司` 等 5 个 |
| task03 标准合同 | `company_profile.company_name` | `XX科技…` | `云驰科技有限公司` 等 5 个 |
| task03 标准合同 | `transfer_context.recipient_name` | `XX Tech Inc.` | `Yunchi Tech Inc.` 等 5 个 |

> task07 `dpo_name`（`XX医疗集团`）为可选字段，不阻塞；task04 正文甲乙双方名不进 request。
> 替换原则（task065 §T03「禁止伪造」红线下）：**只替换公司名/接收方名/项目名等标识性占位符，业务事实（`company_uscc`、`pii_count`、`attachments`、`scc_text`、`business_model` 等）一律不碰。**

### 6.2 原文确实没写的结构化字段 —— 数据 owner 补内容

| 功能 | 字段 | 需补 |
|---|---|---|
| task01 诊断 | `company_name` | 公司全称（测试名） |
| task02 安全评估 | `pii_count` | 累计出境人数（精确值） |
| task03 标准合同 | `company_uscc`、`recipient_country_region`（case4）、`attachments` | 信用代码 / 国家地区 / ≥1 附件 |
| task05 SCC | `scc_text`、`declared_module_type`、`project_name` | SCC 全文 / Module 类型 / 项目名 |
| task09 14117 | `recipient_entities`、`project_name` | 外部实体名称+注册国 / 项目名 |
| task10 CPRA | `business_model`、`data_lifecycle`、`notice_and_consent`、`consumer_rights_process`、`opt_out_and_sale_sharing`、`attachments` | 五个结构化文本 + ≥1 附件 |

### 6.3 法律结论 / Gold —— output 侧，法域专家签署，**不属于 Level B**

| 项 | 归属 |
|---|---|
| TIA `final_conclusion` / `third_country_assessment` | **非人工项**：改走 `structured_input` 由系统产结论（见 B2） |
| `expected.json`（gold） | output 侧验收 oracle，法域专家签署；与"能否生成 request"无关 |

> 关键纠偏：**Level B 的 input blocking 里不存在"必须法域专家补的结论字段"**。唯一法域专家项是后置的 gold 签署。

---

## 七、验收标准

- [ ] `python3 scripts/build_seed_case_requests.py` 重跑后：`converted` 的 request 与源段落逐字段一致（无反向 false）。
- [ ] `task01_case5` 的 `answers.q4_spi_count` 可解析为 5000（若 company_name 仍缺则保持 rejected，但缺项清单不再含 `q4_spi_count`）。
- [ ] `_parse_ynu` 对 `不属于CIIO`/`不含敏感` 返回 no。
- [ ] TIA 走 `structured_input` 后，task08_case1/2 不再因 `final_conclusion`/`third_country_assessment` blocking（其余真缺项仍按规则拒绝）。
- [ ] task04/06 附件派生后，`uploaded_files`/`uploaded_documents` 不再是 blocking。
- [x] 五处台账 + manifest + git 与 **9/29/12/0**（修复后新计数，含占位符主体名替换测试名后 task02_case4 转出）一致。
- [ ] `pytest backend/tests/harness/ -q` 全绿，且新增忠实性测试通过。
- [ ] `git diff --check` 干净。

---

## 八、实施顺序

```
Phase A（解析 bug） → Phase B（adapter 忠实化 + 附件派生 + TIA structured_input）
                    → Phase D（忠实性测试）
                    → 重跑 Level B 得到新计数
                    → Phase C（台账/provenance 同步到新计数）
```
