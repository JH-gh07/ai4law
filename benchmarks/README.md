# DataComplyFlow Benchmarks

本目录是仓库内评测数据与执行实现的权威入口。评测用于发现系统差异，不以“满分”为目标；法律 Gold 尚未经过专家确认的字段不得解释为最终法律结论。

## 目录职责

- `datasets/product_smoke/`：17 个检索案例与 14 个生成案例，覆盖 CN、EU、US 的小规模产品调用链回归。
- `datasets/rag_retrieval/`：240 个正例与 140 个负例组成的合成 RAG 检索数据集。
- `source-materials/`：24 份历史 DOCX 来源材料，可能包含修订痕迹或来源信息，不是 Gold。
- `sample-inputs/`：可提交、已脱敏的合成输入样本；运行时副本不得反向成为源码依赖。
- `schema.py`：Product Smoke Case 的唯一 Schema。
- `smoke_eval.py`：Product Smoke 执行与确定性指标。
- `rag_retrieval_eval.py`：规模化 RAG Retrieval 执行与报告生成。
- `tests/`：Schema、指标语义、运行隔离与三法域回归测试。

## 执行入口

```bash
python scripts/run_smoke_benchmark.py --mode all --target cn
python scripts/run_smoke_benchmark.py --mode retrieval --target all
python scripts/run_rag_retrieval_benchmark.py
pytest benchmarks/tests -q
```

运行结果写入被 Git 忽略的 `outputs/benchmarks/`。Product Smoke 的报告、Trace 和引用审计使用隔离临时运行目录，不写入共享 `storage/` 或 `outputs/assessment/`。

## 指标边界

- Recall、MRR、Schema 通过率和污染率是确定性计算。
- `Issue recall` 只按 Gold 标识或标题的精确命中计算；产生“任意 Issue”不算命中。
- Forbidden rate 是出现至少一次违规的案例占比，取值范围为 `[0, 1]`。
- 当前 Unsupported Claim 仅检查 Case 明确列出的禁止性文本，不等同于完整事实忠实度或法律正确性评测。
- Citation correctness 当前是来源 ID 覆盖率，不等同于引用相关性、蕴含性或法律充分性。

## 数据治理

更新 JSONL 时必须通过 `benchmarks/schema.py`；更新 CSV 时应通过对应构建脚本并检查 query ID 唯一性。禁止把 `source-materials/`、Gold、负样本或测试答案加入生产法规索引。

原顶层 `qa/` 已退出活动路径。其无运行消费者但有审计价值的旧版输入、期望输出和历史 RAG 结果保存在 `docs/archive/evaluation/legacy-qa/`，仅用于历史追溯，不得作为当前数据集、Gold 或默认回归基线。
