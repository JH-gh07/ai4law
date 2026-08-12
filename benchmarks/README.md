# DataComplyFlow Benchmarks

本目录是仓库内评测数据与执行实现的权威入口。评测用于发现系统差异，不以“满分”为目标；法律 Gold 尚未经过专家确认的字段不得解释为最终法律结论。

---

## 目录总览

```
benchmarks/
├── cases/                        共享 Scenario 案例（11 模块 × 22 场景，前端与 CLI 共用）
├── datasets/
│   ├── product_smoke/            小规模产品回归（检索 + 生成，cn/eu/us）
│   ├── rag_retrieval/            合成 RAG 检索数据集（正例 / 负例 / 困难负例）
│   ├── retrieval_gates/          逐模块检索门禁 fixture（must-include / must-exclude）
│   └── seed-cases-v1/            Gold 种子案例 v1（10 任务 × 5 案例 + 输入抽取）
├── source-materials/             历史 DOCX 来源材料（非 Gold，待结构化）
├── sample-inputs/                已废弃占位（fixture 迁移至 backend/tests/fixtures/）
├── tests/                        评测实现测试（Schema / 指标语义 / 运行隔离）
├── schema.py                     Product Smoke Case 的唯一 Schema
├── smoke_eval.py                 Product Smoke 执行与确定性指标
├── rag_retrieval_eval.py         规模化 RAG Retrieval 执行与报告生成
└── README.md                     本文件
```

---

## 子目录详解

### 1. `cases/` — 共享 Scenario 案例

22 个共享 benchmark scenario，覆盖 11 个模块，每个场景含 `scenario.json`（request + display）与 `expected.json`（harness 断言）。前端案例与 CLI 案例通过 `scenario_path` / `expected_path` 引用同一份场景，保证事实与断言对齐。

| 模块 | 场景数 | 场景目录 |
|------|:---:|------|
| `us_14117` | 3 | geneguard_genomic_red / geneguard_geolocation_yellow / geneguard_telemetry_green |
| `eu_scc` | 3 | france_c2c_uk_aws / germany_c2p_india_health / netherlands_p2p_serbia_module_error |
| `pipia` | 3 | haitao_marketing_singapore / weilan_hr_exemption_us / zhifutong_eurocert_de |
| `diagnosis` | 3 | kuajing_youpin_ecommerce_sg / qianyan_medical_research_eu / zhijia_weilai_anonymized_de |
| `assessment` | 2 | dongfang_capital_trust_hk / youxuan_shopping_data_export |
| `bcr` | 2 | bcr_controller_basic / bcr_high_risk_health |
| `dpia` | 2 | ai_recruitment_screening / smart_city_surveillance |
| `tia` | 2 | innovate_crm_us_saas / leiden_clinical_india |
| `cpra` | 1 | trendy_goods_ecommerce |
| `review` | 1 | data_security_agreement |

> 案例一致性由 `scripts/check_case_parity.py` 门禁校验（26 CLI 案例、603 叶断言、28 开发者案例）。

### 2. `datasets/product_smoke/` — Product Smoke 小规模回归

可执行的小规模产品回归 Case，按 `cn / eu / us` 三法域分文件。

| 文件 | 案例数 |
|------|:---:|
| `retrieval_eval_cases_{cn,eu,us}.jsonl` | 17（cn 10 / eu 4 / us 3） |
| `generation_eval_cases_{cn,eu,us}.jsonl` | 14（cn 10 / eu 2 / us 2） |

Generation Case 的 `input` 是自包含执行输入；`must_*` 字段是当前待确认评测标注。EU、US 的部分 Issue Gold 标识尚未与运行时 Issue Schema 对齐，真实评测会报告未命中，不得通过宽松匹配伪造通过。

### 3. `datasets/rag_retrieval/` — 合成 RAG 检索数据集

| 文件 | 行数 | 内容 |
|------|:---:|------|
| `queries.csv` | 300 | 主数据集（240 正例 + 60 负例） |
| `hard_negatives.csv` | 80 | 扩展困难负例 |

数据由 `scripts/build_rag_retrieval_dataset.py` 与 `scripts/build_rag_hard_negatives.py` 生成，属合成评测数据，不是法律案例 Gold。

### 4. `datasets/retrieval_gates/` — 逐模块检索门禁 fixture

`module_retrieval_benchmark.json`：逐模块检索基准 fixture，每个条目定义固定 query、预期 must-include 的 source_id / locator、以及必须排除的噪音 source_id。覆盖 11 个模块（cn_diagnosis / cn_assessment / cn_pipia / cn_review / eu_scc / eu_bcr / eu_dpia / eu_tia / us_cpra / us_vendor_review / us_14117）。

> 由 `backend/common/rag/tests/test_module_retrieval_benchmark.py` 参数化消费；快照归档脚本为 `scripts/snapshot_rag_retrieval_benchmark.py`。

### 5. `datasets/seed-cases-v1/` — Gold 种子案例 v1

来自历史产品资料的种子案例，含原始 DOCX、抽取输入与状态台账。

| 子目录 / 文件 | 说明 |
|------|------|
| `_source/task01/` ~ `task10/` | 10 个任务 × 5 案例 = 50 个原始 DOCX |
| `_source/数规通黄金标准_v1.0.docx` | Gold 标准总表（状态 `PENDING`，待 rubric 抽取） |
| `_source/测试案例及测试分数汇总表.xlsx` | 案例分数汇总表 |
| `inputs/task*_case*.input.json` | 50 个抽取后的输入侧 JSON（无 expected.json） |
| `manifest.json` | 源文件清单（SHA-256 + 大小） |
| `manifest.v1.json` | 输入抽取结果清单（50 案例，0 published / 50 pending_authoring） |
| `levelb-disposition.v1.json` | Level B 归置记录（40 rejected / 10 gap） |

> 当前状态：仅产出 **INPUT 侧**，无 expected.json，未接入任何测试 runner，不改变 `config/case_inventory.json`。缺口台账见 `status/check/task065/seed-gap-ledger.json`。

### 6. `source-materials/` — 历史来源材料（非 Gold）

从历史产品资料中筛出的测试案例与功能说明原件，按法域分目录保存：

| 目录 | DOCX 数 |
|------|:---:|
| `cn/legacy-docx/` | 12 |
| `eu/legacy-docx/` | 9 |
| `us/legacy-docx/` | 5 |
| `shared/` | 1 |
| `cn/review/fixtures/` | 4（review 模块 fixture：docx / pdf / png） |

这些 DOCX 是 Benchmark 的来源材料，**不是已确认 Gold**，不应直接计入自动指标。使用前必须完成：来源确认、敏感信息检查、结构化 Case Schema 转换、法律专家标注和版本记录。原目录中 65 个法规与模板副本因 SHA-256 已被 `resources/legal/` 或研究资产覆盖而未迁入。运行时法规检索只能读取 `resources/legal/`，不得读取本目录。

### 7. `sample-inputs/` — 已废弃占位

测试输入 fixture 已迁移至 `backend/tests/fixtures/{cn,eu,us}/`。本目录仅保留说明，旧占位文件已删除。

### 8. `tests/` — 评测实现测试

`test_rag_eval.py`：Schema、指标语义、运行隔离与三法域回归测试。

### 9. 顶层执行模块

| 文件 | 行数 | 职责 |
|------|:---:|------|
| `schema.py` | 56 | Product Smoke Case 的唯一 Schema |
| `smoke_eval.py` | 337 | Product Smoke 执行与确定性指标 |
| `rag_retrieval_eval.py` | 454 | 规模化 RAG Retrieval 执行与报告生成 |

---

## 执行入口

```bash
python scripts/run_smoke_benchmark.py --mode all --target cn
python scripts/run_smoke_benchmark.py --mode retrieval --target all
python scripts/run_rag_retrieval_benchmark.py
pytest benchmarks/tests -q
```

运行结果写入被 Git 忽略的 `outputs/benchmarks/`。Product Smoke 的报告、Trace 和引用审计使用隔离临时运行目录，不写入共享 `storage/` 或 `outputs/assessment/`。

RAG Retrieval 回归快照可用 `python scripts/snapshot_rag_retrieval_benchmark.py` 归档到 `outputs/benchmarks/regression/`。

---

## 指标边界

- Recall、MRR、Schema 通过率和污染率是确定性计算。
- `Issue recall` 只按 Gold 标识或标题的精确命中计算；产生“任意 Issue”不算命中。
- Forbidden rate 是出现至少一次违规的案例占比，取值范围为 `[0, 1]`。
- 当前 Unsupported Claim 仅检查 Case 明确列出的禁止性文本，不等同于完整事实忠实度或法律正确性评测。
- Citation correctness 当前是来源 ID 覆盖率，不等同于引用相关性、蕴含性或法律充分性。

---

## 数据治理

- 更新 JSONL 时必须通过 `benchmarks/schema.py`；更新 CSV 时应通过对应构建脚本并检查 query ID 唯一性。
- 禁止把 `source-materials/`、Gold、负样本或测试答案加入生产法规索引。
- 原顶层 `qa/` 已退出活动路径。其无运行消费者但有审计价值的旧版输入、期望输出和历史 RAG 结果保存在 `docs/archive/evaluation/legacy-qa/`，仅用于历史追溯，不得作为当前数据集、Gold 或默认回归基线。
