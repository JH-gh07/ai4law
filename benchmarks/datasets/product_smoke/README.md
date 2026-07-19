# Product Smoke 数据集

本目录保存可执行的小规模产品回归 Case。`retrieval_eval_cases_{cn,eu,us}.jsonl` 共 17 例，`generation_eval_cases_{cn,eu,us}.jsonl` 共 14 例。

Generation Case 的 `input` 是自包含执行输入；`must_*` 字段是当前待确认评测标注。EU、US 的部分 Issue Gold 标识尚未与运行时 Issue Schema 对齐，真实评测会报告未命中，不得通过宽松匹配伪造通过。