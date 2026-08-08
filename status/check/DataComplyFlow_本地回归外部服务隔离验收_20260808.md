# DataComplyFlow 本地回归外部服务隔离验收

> 日期：2026-08-08
>
> 范围：本地后端普通回归中的 TIA、CPRA 模型调用隔离
>
> 未执行：远端部署、远端配置修改、生产数据修改
>
> 判定：**隔离修复通过；TIA 真实 provider 完整首跑仍未完成**

## 1. 问题和原因

普通 `pytest` 会读取仓库 `.env`。TIA 测试直接创建 `TIAService()`，服务因此启用真实 SiliconFlow provider，并按 6 个章节顺序发起模型请求。多个 60 秒请求叠加后，全量测试会在 TIA 位置等待十分钟以上。

普通回归只应验证代码、Schema、编排和产物结构。真实 provider 的内容质量、token 和耗时应由单独的 live 首跑验证，两类测试不能混在一起。

## 2. 现场证据

第一次全量运行在 608 项通过后停在：

```text
backend/domains/eu/tia/tests/test_service.py::test_tia_generate_report
  -> TIAService.generate_report()
  -> generate_chapter()
  -> LLMClient.chat()
  -> OpenAI chat.completions.create()
```

人工停止时已经运行 788.89 秒。排除异步测试后仍停在同一个 service 测试，证明异步 API 和 service 测试都需要隔离真实模型。

## 3. 修复范围

| 文件 | 修复内容 | 原因 |
|---|---|---|
| `backend/domains/eu/tia/tests/test_async_api.py` | 向 router 注入 `TIAService(llm_client=_DisabledLLM())` | 异步契约只验证提交、轮询和结果结构 |
| `backend/domains/us/cpra/tests/test_async_api.py` | 向 router 注入 `CPRAService(llm_client=_DisabledLLM())` | 与 DPIA、PIPIA、BCR 的测试隔离方式一致 |
| `backend/domains/eu/tia/tests/test_service.py` | `test_tia_generate_report` 明确使用 `_DisabledLLM` | service 契约测试不负责验证 provider 内容质量 |

真实 provider 没有被删除。TIA live 首跑仍要单独记录 token、耗时、trace、fallback、完整章节和最终产物。

## 4. 复验结果

| 范围 | 结果 |
|---|---:|
| TIA、CPRA、DPIA、PIPIA、BCR 异步契约 | 5 passed，6.51 秒 |
| TIA、CPRA service 测试 | 10 passed，16.02 秒 |
| TIA/CPRA 隔离和 RAG 共享目录复验 | 8 passed，98.09 秒 |
| 后端全量回归（修复后） | 823 passed，0 failed，0 flaky，7m01s |
| 案例契约门禁 | 11 modules、20 CLI cases、397 leaf checks、28 developer cases，PASS |

RAG 隔离测试曾在另一个 `pytest` 进程同时写入 `storage/traces` 时失败；并行进程结束后相同测试通过。该测试要求运行期间没有其他任务写共享运行目录，不是 RAG 召回或报告逻辑失败。

## 5. 当前边界

| 结论 | 是否成立 |
|---|---:|
| 普通 TIA/CPRA 契约测试不再调用真实模型 | 是 |
| 后端确定性回归全部通过 | 是 |
| TIA 真实 provider 已完整生成 6 章和最终产物 | 否 |
| TIA 本地浏览器引用跳转已验收 | 否 |
| 可以开始远端部署 | 否 |

下一步继续在本地完成 TIA 真实 provider 的有界首跑和浏览器闭环，再处理 CPRA、14117/`cn_flow`、文档专项审查等未完整验收功能。
