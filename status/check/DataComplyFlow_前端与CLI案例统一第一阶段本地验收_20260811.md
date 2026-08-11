# DataComplyFlow 前端与 CLI 案例统一第一阶段本地验收

> 日期：2026-08-11
> 对应方案：`status/todo/DataComplyFlow_前端与CLI案例统一及Trace可视化改造方案_20260811.md`
> 范围：第一阶段，仅本地；未连接远程，未部署

## 已完成

1. CLI 新增 `--verbose-trace`，实时打印安全摘要，同时保留 Trace 落盘。
2. 默认模式保持简洁；`--quiet` 与 `--verbose-trace` 冲突时明确拒绝。
3. 修复 Python 字符串解析 TypeScript 导致前端案例 26 被误报为 28。
4. 新增 `config/dev_case_catalog.json`，登记 26 个前端案例的稳定 ID、来源和分类。
5. 来源门禁检查案例 ID 唯一、模块注册、来源分类和来源文件存在性。
6. 恢复正式 diagnosis 第 3 例“智驾未来完全匿名化车辆传感器数据豁免”。
7. 恢复正式 assessment 第 2 例“优选购物 120 万用户行为数据”。
8. 修复 Review 两个前端案例共用错误协议附件的问题。
9. CLI Review 改用正式数据安全及保密协议 fixture。
10. 修复 Review `--no-llm` 仍读取环境变量并调用真实 DeepSeek 的故障。
11. 修复 PIPIA 生成 `rights_protection` 但公共 IssueCategory 不接受该语义的问题。
12. CPRA harness 显式启用案例所要求的 Schema-first 产物，消除机器配置差异。
13. 修正 cn_flow 非 covered person 场景被错误期待为 HIGH 的断言，并注明它只属于兼容适配测试。

## 关键故障证据

Review 修复前，执行 `--no-llm --verbose-trace` 仍出现：

```text
tool_start 请求模型生成 model=deepseek-ai/DeepSeek-V3.2
tool_result 模型响应返回 tokens=363
```

原因是 `_env_file=None` 只禁用 `.env` 文件，没有覆盖进程环境变量。修复后显式设置 provider 为 `none` 并清空全部 API key。

同一正式 Review fixture 修复后：

```text
耗时：5.75 秒（后续全量回归单例约 3.32 秒）
events：2
llm_calls：0
tokens：0
结果：PASS，9/9 断言
报告：DOCX + PDF
识别问题：39
```

## 最终本地验证

```text
CLI：20 PASS / 0 FAIL
模块：11
CLI leaf checks：424
前端开发案例：26（已修复误报）
前端案例/Builder测试：52 passed
前端 build：通过
case parity：通过
```

CLI 全量命令：

```bash
uv run python -m backend.tests.harness.runner all --no-llm
```

输出：

```text
all modules: 20 PASS, 0 FAIL across 11 modules
```

## 尚未完成

以下事项不能因本阶段测试全绿而宣告完成：

- `eu_scc-01` 表单事实已恢复，但 `scc_text_override` 仍是旧德国 C2P 文本，目录保持 `source_derived`；
- EU SCC 第 2 例、TIA 两例、PIPIA 两例、EO 14117 两例仍需按来源目录逐项恢复或明确保留为派生/产品补充；
- `cn_flow` 两例尚未改为直接复用同一 EO 14117 scenario 文件；
- 前端与 CLI 仍未从同一个 `scenario.json` 生成请求；
- 正式资料中的所有案例尚未全部结构化进入 `benchmarks/cases/`；
- 真实本地 HTTP、认证、上传、异步任务、SSE 和浏览器截图验收尚未执行；
- 远程部署未执行，仍需用户明确同意。

## 当前结论

第一阶段已真实完成基础设施修复、来源登记、三项正式前端案例恢复、Review fixture 修复、CLI Trace 可视化和 20 个 CLI 案例全绿。总体案例统一仍在实施中，下一阶段应继续处理目录中标记为 `source_derived`、`product_extension` 和 `compatibility_adapter` 的案例，不能归档主方案。
