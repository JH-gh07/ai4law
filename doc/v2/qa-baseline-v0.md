# v0 样例数据与基准输出对比（T-QA-02）

## 1. 样例数据集
- 文件：`qa/baseline/v0_sample_dataset.json`
- 覆盖模块：`2.2/2.3/3.2/3.3/3.4/4.1/4.2`
- 每个 case 包含：
1. `module_code`
2. `input_payload`
3. `required_artifacts`

## 2. 基准对比脚本
- Python脚本：`scripts/qa_v0_baseline.py`
- Shell入口：`scripts/qa_v0_baseline.sh`

执行：
```bash
bash scripts/qa_v0_baseline.sh
```

## 3. 基准生成与更新
首次生成或需要刷新基准时：
```bash
bash scripts/qa_v0_baseline.sh --update-baseline
```

会写入：
- `qa/baseline/v0_expected_outputs.json`（基准）
- `outputs/qa/v0_baseline_run_<timestamp>.json`（当次运行报告）

## 4. 对比规则
1. 每个模块任务必须 `COMPLETED`
2. 产物类型必须覆盖 `required_artifacts`
3. `markdown` 输出 SHA256 必须与基准一致
4. `audit.rule_hits` 必须是结构化对象（`rule_id/hit/evidence`）

## 5. 失败处理
1. 查看 `outputs/qa/v0_baseline_*.log`
2. 查看 `outputs/qa/v0_baseline_run_*.json` 的实际值
3. 确认是否为预期变更；若是预期变更，执行 `--update-baseline`
