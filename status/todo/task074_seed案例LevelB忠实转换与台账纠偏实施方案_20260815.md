# task074 — 种子案例 Level B 忠实转换与台账纠偏实施方案

> **日期**：2026-08-15
> **关联**：`task065`（seed 三级管线）、`task071`（前端开发期入口去重）、`task072`（v2.0 校正）、`issue071`
> **目标**：纠正"Level B 代码已全部落实、36 个 rejected 只能人工补"的错误结论；把仍可由代码消除的误判/派生项与真正的人工项精确分开，并给出可执行顺序。
> **性质**：技术纠偏 + 代码实施方案（不含法律结论签署 / 金标签署）。

> ✅ **执行结果（2026-08-15）**：Phase A/B/C/D 已全部落实并提交（`998482c9`）。随后按用户授权，对**占位符主体名**（task02/03 的公司名 / 接收方名，仅替换不影响业务的标识名，业务事实一律不碰）替换为测试名，使 task02_case4 由 rejected 转 converted。最终台账：**converted 9 / rejected 29 / pending_correction 12 / gap 0**。同时补装 item 4（LibreOffice + 可再分发 CJK 字体 `resources/fonts/NotoSansSC-Regular.ttf`），PDF CJK 字体嵌入门已由 blocked 转 pass。item 3（gold 签署）属法域专家验收项，本 task 不做。

> ✅ **授权模拟补充结果（2026-08-16）**：在不覆盖原始 DOCX、Level A 输入、严格请求目录和严格台账的前提下，为 29 个 rejected 建立独立 `synthetic_fixture` overlay。synthetic 口径为 **converted 38 / pending_correction 12 / rejected 0 / gap 0**；严格 source 口径仍保持 **converted 9 / rejected 29 / pending_correction 12 / gap 0**。模拟值不冒充原文事实或 owner-confirmed 数据。

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

---

## 九、2026-08-16 授权模拟补充实施记录

### 9.1 双口径与文件隔离

用户明确授权：业务事实也可基于原文范围和合理业务假设生成模拟值。为避免该授权破坏本 task 原有“忠实转换”语义，实施采用 opt-in 双模式：

| 口径 | 命令 | 请求目录 | 台账 | 结果 |
|---|---|---|---|---|
| 严格 source | `./.venv/bin/python scripts/build_seed_case_requests.py --mode source` | `benchmarks/datasets/seed-cases-v1/requests/` | `levelb-disposition.v1.json` | 9 converted / 29 rejected / 12 pending |
| 授权 synthetic | `./.venv/bin/python scripts/build_seed_case_requests.py --mode synthetic --write` | `benchmarks/datasets/seed-cases-v1/requests-synthetic/` | `levelb-disposition.synthetic.v1.json` | 38 converted / 12 pending |

逐字段机器可读依据：`benchmarks/datasets/seed-cases-v1/synthetic-supplements.v1.json`。每个字段固定记录 `value`、`basis_type`、`source_hint`、`reason`；总 provenance 为 `synthetic_fixture`，`owner_confirmed=false`。

### 9.2 task01 诊断：主体名与敏感个人信息人数

| 案例 | 补充值 | 依据与选择原因 |
|---|---|---|
| case1 | `海岳通信科技股份有限公司`；`q4_spi_count=2,000,000` | 原文为电信运营商并写“≥1万、粗略约200万”；名称按行业模拟，人数采用原文约数中心值且满足下限。 |
| case2 | `澜桥跨境电子商务有限公司`；`q4_spi_count=8,000` | 原文写“<1万、大概8000”；直接采用8000。 |
| case3 | `莱茵智造汽车零部件有限公司`；`q4_spi_count=6,000` | 原文写“<1万、大概6000个员工”；直接采用6000。 |
| case4 | `薪云软件科技有限公司`；`q4_spi_count=200` | 原文明确200名员工，且薪酬/银行账号使适配器进入敏感事实分支；用原文人数，不另造数值。 |
| case5 | `新衡医疗人工智能有限公司` | q4 已由原文“5000人的全基因组数据”解析；只补业务一致的主体名。 |

### 9.3 task02 安全评估：累计出境人数

原文完全未给精确人数，因此均为 `business_simulation`，不是 range/source concretization：

| 案例 | `pii_count` | 选择原因 |
|---|---:|---|
| case1 银行核心系统/AWS灾备 | 1,200,000 | 城商银行持续实时同步客户数据，采用百万级规模以覆盖法定高阈值路径。 |
| case2 新能源汽车/德国研发 | 180,000 | 持续量产车辆实时上传，采用18万活跃车辆/车主的中型车队规模。 |
| case3 社交APP/美国人脸服务 | 350,000 | 长期按需实名认证，采用35万实名用户体现规模化生物识别调用。 |
| case5 互联网医院/日本AI | 80,000 | 采用8万年度活跃患者，符合互联网医院中等规模且不无依据放大到百万级。 |

### 9.4 task03 标准合同/PIPIA：信用代码、国家和附件

| 案例 | 补充值 | 选择原因 |
|---|---|---|
| case1 | `91310115MA1K4A2X7Q` | 18位测试格式信用代码；只验证字段和链路，不声称为真实登记号。 |
| case2 | `91310106MA1FY8C62R` | 同上，保持案例间唯一。 |
| case3 | `91110108MA01X7G84P` | 同上，保持案例间唯一。 |
| case4 | `91110105MA02B6H31N`；接收国 `新加坡` | 原文只称“海外合作教育机构”；新加坡与国际教育合作/区域数据中心场景一致，且不与其他事实冲突。 |
| case5 | `91310000MA1H9R5M2C` | 18位唯一测试格式信用代码。 |

五案附件均引用各自 `_source/task03/task03_caseN.docx`，角色为 `supporting_evidence`。理由：文件真实存在、路径和大小可验核，可用于上传链路测试；但其内容是案例材料，不冒充已签署标准合同。

### 9.5 task05 SCC 审查：项目、Module 与 SCC fixture

| 案例 | 项目/双方 | Module | 原因 |
|---|---|---|---|
| case1 | EU客户数据AWS托管；Northstar Digital Europe GmbH → AWS | Module Two | 客户企业决定处理目的，AWS作为处理服务商，按 controller-to-processor。 |
| case2 | 印度IT外包；EuroRetail Operations S.A. → Bharat IT Services | Module Two | 欧盟甲方控制目的，印度外包商代为处理。 |
| case3 | 荷兰总部至英国子公司共享；Oranje Group N.V. → Oranje Group UK Ltd. | Module One | 测试设定双方共同决定共享用途，按 controller-to-controller。 |
| case4 | 欧盟母公司至中国子公司处理；Alpine Consumer Products AG → 上海子公司 | Module Two | 测试设定中国子公司提供集团处理服务。 |
| case5 | 欧盟患者数据巴西分析；MediNova Europe S.A. → Saude Analytics Brasil | Module Two | 医疗机构决定目的，巴西分析商作为处理者。 |

`scc_text` 由代码按每案实体、Module 和处理目的生成，首行强制为 `[SYNTHETIC TEST FIXTURE - NOT AN EXECUTED AGREEMENT]`，包含 Clause 1-18 及 Annex I-III 的测试结构。理由：满足完整解析/审查链路所需结构，同时明确不是欧委会正式文本、已签署合同或 owner-supplied SCC。

### 9.6 task09 EO 14117：项目、人数与境外接收实体

| 案例 | 人数 | 模拟接收实体 | 依据与原因 |
|---|---:|---|---|
| case1 | 30,000 | 云析科技（深圳）有限公司 / China | 原文“几万人、传至中国关联公司”；取3万作为“几万”代表值。 |
| case2 | 15,000 | Volga Cloud Systems LLC / Russia | 原文“约1.5万、俄罗斯公司控股55%”；人数直接确定化，保留55%控股描述。 |
| case3 | 300 | Tehran Genomics Research Institute / Iran | 原文“约300名、伊朗学术机构”；人数直接采用，名称仅作测试标识。 |
| case4 | 20,000 | Caracas Audience Analytics C.A. / Venezuela | 原文“约2万、委内瑞拉营销公司”；交易类型同步识别为 `data_brokerage`。 |
| case5 | 12,000 | 华算智能科技（上海）有限公司 / China | 原文“约1.2万、中国母公司持股60%”；人数确定化并保留60%关系。 |

生成器同时把人数写入每个 `US14117DataItem.us_person_count`，并按精确位置、生物识别、基因或身份标识映射 DOJ 数据类别，避免仅补实体却继续保留默认人数0。
五案申报主体分别补为 `Atlas Cloud Storage, Inc.`、`Nova Social Media, Inc.`、`Helix Genomics, Inc.`、`Meridian Data Brokerage, Inc.`、`GateVision Workforce, Inc.`，原因是消除 Schema 的 `示例企业` 默认值并保持与各案业务一致。

### 9.7 task10 CPRA：五段业务事实与附件

| 案例 | 模拟业务模型 | 关键补充理由 |
|---|---|---|
| case1 | 电商销售 + 跨情境行为广告 | 原文明示广告网络和“无需退出”的错误认识；补入订单/广告生命周期、45日DSR流程及缺失首页退出链接。 |
| case2 | 员工设备管理和生产率分析SaaS | 原文明示员工追踪且未发通知；补入24个月日志、HR请求渠道和不完整SOP，不虚构已经合规。 |
| case3 | 在线订阅平台 + 公有云托管 | 原文明示只有云厂商通用条款；补入账户/支付/工单生命周期和标准DSR，同时保留服务提供商合同限制未确认。 |
| case4 | 位置推荐APP + 订阅/位置广告 | 原文明示精确位置仅写入隐私政策、无单独弹窗；补入位置保留期、APP权利入口和缺少敏感信息限制链接。 |
| case5 | 数据经纪和数据许可 | 原文明示大量删除、授权代理、未核验和下游买方；补入5年画像生命周期、核验缺口及下游同步不完整。 |

五案的 `business_model/data_lifecycle/notice_and_consent/consumer_rights_process/opt_out_and_sale_sharing` 完整原文及逐字段理由均在 overlay。附件引用各自 `_source/task10/task10_caseN.docx`，按案例分别标记 `other/other/vendor_list/privacy_policy/rights_sop`，均是 synthetic 输入角色，不声称为真实政策或SOP。

### 9.8 代码修改与验证证据

| 文件 | 修改 |
|---|---|
| `scripts/build_seed_case_requests.py` | 新增 overlay 校验、`--mode source|synthetic`、六模块显式 supplement 消费、SCC fixture builder、独立请求/台账输出。 |
| `backend/tests/harness/test_seed_case_requests.py` | 新增 overlay覆盖、双口径、范围值、SCC/EO/CPRA与附件验证。 |
| `synthetic-supplements.v1.json` | 29案逐字段值、依据和原因。 |
| `requests-synthetic/*.request.json` | 38份经真实模块Schema验证的synthetic运行请求。 |
| `levelb-disposition.synthetic.v1.json` | 独立synthetic处置台账。 |

已执行：

```text
./.venv/bin/pytest -q backend/tests/harness/test_seed_case_requests.py
25 passed

./.venv/bin/python scripts/build_seed_case_requests.py --mode source
9 converted / 29 rejected / 12 pending_correction

./.venv/bin/python scripts/build_seed_case_requests.py --mode synthetic --write
38 converted / 12 pending_correction

逐份调用 _schema_for(module_id).model_validate_json(...)
validated_requests=38
```

扩大运行六个相关 domain 测试目录的结果为 `207 passed / 3 failed`。失败为现有 PIPIA finding 标题断言两项和 SCC citation display label 断言一项，均不经过本轮修改的 seed builder/overlay；本轮不改无关业务逻辑，失败详情保留在交付说明中，不能将该宽回归表述为全绿。

### 9.9 仍不改变的边界

1. `inputs/*.input.json` 和 `_source/*.docx` 未因本轮模拟补充被改写。
2. `requests/` 与 `levelb-disposition.v1.json` 继续表达严格 source 口径。
3. synthetic request 不得作为 gold、owner-confirmed 事实、正式合同或正式法律申报材料。
4. 12 个 `pending_correction` 仍被隔离；本轮授权只覆盖当前29个 rejected，不越过正文版本隔离门。
