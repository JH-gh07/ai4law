# task072 — 种子案例 v2.0 校正后输入段抽取治理实施方案

> **日期**：2026-08-15
> **关联 issue**：`status/issue/issue072_种子案例v2.0校正后正文结构不一致_20260815.md`
> **目标**：让 8 个 v2.0 校正文件（task04/06/07/08 各 case1/2）的**输入段**能被正确抽出并写入 `input.json`；`input.json` 只装输入侧，不装输出/金标。

---

## 一、背景与问题

任务 4/6/7/8 的任务名已按 v2.0 改对（文档审查 / BCR 审查 / DPIA 草案生成 / TIA 草案生成），8 个 case1/2 docx 已用 v2.0 内容覆盖。但重跑 Level A 后，这 8 个文件的 `input.paragraphs` 全是空——因为脚本硬编码的输入标记是 v1.0 的 `一、用户输入`，与 v2.0 的写法对不上。

## 二、范围与非范围

**范围（本 task 只做这一件事）**：改 `scripts/build_seed_case_inputs.py`，把 8 个文件的输入段正确抽出，并落实「input-only」产物契约。

**非范围（明确不做，另行处理）**：
- 金标补齐 / OCR / 法域签署（task4 图片、task6 缺金标 → expected 阶段）。
- Level B adapter / request 生成 / 台账同步（task065、task071 等）。

## 三、改动内容

### 3.1 输入段识别（三种写法 + 兜底）

```python
INPUT_MARKERS  = ("一、用户输入", "用户输入", "待审查的BCR条款原文")
OUTPUT_MARKERS = ("二、标准答案（即系统输出）",
                  "标准答案（DPIA草案）", "标准答案（TIA草案）",
                  "标准答案（错误与缺失清单）")

def slice_input(paras):
    i_in  = 第一个命中 INPUT_MARKERS 的段落下标（无则 -1）
    i_out = 第一个命中 OUTPUT_MARKERS 的段落下标（无则 -1）
    start = i_in + 1 if i_in >= 0 else 0
    stop  = i_out if i_out > start else len(paras)
    return [t for t in paras[start:stop] if t]
```

- `OUTPUT_MARKERS` 只用于给 input 定终点，**不抽取输出内容**。
- task6 无输出标记 → `stop = 文末`，输入 = BCR 条款全文。
- task4 无输入标记 → `start = 0`，输入 = 文档标题到输出标记前的正文。

### 3.2 input-only 产物契约

`input.json` 只保留输入侧 + 身份溯源，**移除所有基于输出文本的字段**：

| 动作 | 字段 |
|---|---|
| 保留 | `case_id` / `task_no` / `declared_task_name` / `jurisdiction` / `module_id` / `mapping_status` / `source_docx` / `source_sha256` / `source_size_bytes` / `input.paragraphs` |
| 移除 | `output_measure`、`expected_status`、`expected_note` |
| flag 保留 | `pending_correction`、`marker_missing_input` |
| flag 移除 | `marker_missing_output`、`marker_missing_remark`、`placeholder_in_output`、`output_under_300_chars` |

> 依据：Level B（`build_seed_case_requests.py`）只消费 `module_id` / `mapping_status` / `input.paragraphs`，不消费 output 相关字段，移除不破坏下游。

## 四、验收标准

- [ ] task07/08 各 case1/2 的 `input.paragraphs` 非空，且与 v2.0 原文「用户输入」之后、输出标记之前的段落一致。
- [ ] task06 各 case1/2 的 `input.paragraphs` 非空（BCR 条款全文，含到文末）。
- [ ] task04 各 case1/2 的 `input.paragraphs` 非空（文档正文，标题起到输出标记前）。
- [ ] 其余 42 个 v1.0 文件的输入抽取结果不变（标记仍为 `一、用户输入`）。
- [ ] 8 个文件不再出现 `marker_missing_input`。
- [ ] `input.json` 中不含 `output_measure` / `expected_status` / `expected_note` 及输出文本。
- [ ] dry-run 与 `--write` 幂等，重复运行结果一致。

## 五、验证命令

```bash
# dry-run 先看统计，不写盘
python3 scripts/build_seed_case_inputs.py

# 校验通过后再写盘
python3 scripts/build_seed_case_inputs.py --write

# 抽查 8 个文件的 input 是否非空、无 output 字段
python3 - <<'PY'
import json, glob
for p in sorted(glob.glob("benchmarks/datasets/seed-cases-v1/inputs/task0*_case[12].input.json")):
    r = json.load(open(p, encoding="utf-8"))
    if r["task_no"] in (4,6,7,8):
        n = len(r["input"]["paragraphs"])
        has_out = any(k in r for k in ("output_measure","expected_status","expected_note"))
        print(r["case_id"], "input_paras=", n, "has_output_field=", has_out)
PY
```

## 六、完成定义

1. 8 个 v2.0 校正文件的输入段全部非空、与原文一致；
2. `input.json` 无任何输出文本或 output 相关字段；
3. 42 个 v1.0 文件的输入抽取无回归；
4. dry-run / `--write` 幂等，全部验收项通过。
