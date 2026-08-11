# DataComplyFlow 前端与 CLI 案例统一第二阶段本地验收

> 日期：2026-08-11
> 对应方案：`status/todo/DataComplyFlow_前端与CLI案例统一及Trace可视化改造方案_20260811.md`
> 范围：前端正式案例事实更正与 cn_flow 兼容逻辑；仅本地，未连接远程，未部署

## 本阶段完成内容

1. SCC 案例一恢复为法国电商控制者向英国关联公司控制者传输，并明确美国 AWS 下游处理风险。
2. SCC 案例二恢复为德国 Gesundheitsforschung GmbH 向印度 Data Insights Solutions 传输患者健康数据，保留 Clause 9、14、15 修改风险。
3. TIA 两例恢复为正式案例一“德国到美国 SaaS”和案例三“荷兰到印度临床试验”。
4. PIPIA 两例恢复为“海淘优选 50 万高价值会员标准合同路径”和“智付通向德国 EuroCert 提交约 5 万商户资料认证路径”。
5. EO 14117 两例恢复为 GeneGuard 的正式红灯和黄灯案例。
6. cn_flow 前端兼容案例复用同一组 EO 14117 红灯、黄灯核心事实，不再保留电商订单和半导体独立业务场景。
7. 正式资料未提供的统一社会信用代码、股权、控制人、留存期限和组织信息改为“待补充”或“资料未提供”，不再用虚构值填充。
8. `config/dev_case_catalog.json` 同步更新来源、案例号、分类、已覆盖事实和未覆盖事实。

## 修复的兼容逻辑错误

旧 `cn_flow` 适配器曾使用以下逻辑：

```python
onward_transfer = bool(payload.transfer_chain.strip())
```

`transfer_chain` 是必填主传输链路，因此任何旧请求都会被错误标记为“存在再传输”。修复后：

- 主传输链保留在统一请求的 `transaction_description`；
- 不再从主传输链推断再传输，`onward_transfer=False`；
- `lossy_fields` 明确加入 `onward_transfer`，提示旧结构无法确认该事实。

该修复由失败测试先复现，再修改实现。cn_flow 相关后端测试结果为 `7 passed`。

## 来源覆盖情况

| 模块 | 本阶段覆盖 | 仍未覆盖 |
|---|---|---|
| `eu_scc` | 正式案例一、二 | 无本阶段新增缺口 |
| `tia` | 正式案例一、三 | 正式案例二“法国到英国充分性认定”未进入前端开发案例 |
| `pipia` | 正式案例一、三 | 正式案例二“跨境人力资源管理豁免”未进入前端开发案例 |
| `us_14117` | 正式红灯、黄灯 | 正式绿灯“向英国公司提供设备遥测数据”未进入前端开发案例 |
| `cn_flow` | 复用红灯、黄灯可表达事实 | 旧结构不能表达股权、访问人员和措施明细 |

## 本地验证

```text
前端全量测试：27 files passed，147 tests passed，2 skipped
前端构建：通过
相关后端测试：52 passed
cn_flow 定向测试：7 passed
case parity：11 modules，20 CLI cases，424 leaf checks，26 developer cases
CLI 无模型全量：20 PASS / 0 FAIL，11 modules
CLI 模型调用：全部 llm_calls=0，tokens=0
```

CLI 全量命令：

```bash
uv run python -m backend.tests.harness.runner all --no-llm
```

## 提交记录

```text
d58b548 fix(cases): restore first official SCC scenario
e5647c0 fix(cases): restore second official SCC scenario
b1188c2 fix(cases): restore official TIA scenarios
00e535e fix(cases): restore official PIPIA scenarios
a08e403 fix(cases): restore official EO 14117 scenarios
a6fef18 fix(cases): reuse EO facts in cn flow compatibility
9cdc9ad fix(cn-flow): stop treating primary chain as onward transfer
```

## 尚未完成

- 前端与 CLI 尚未读取同一个 `benchmarks/cases/<module>/<case_id>/scenario.json`，所以目前只能证明前端事实已纠正，不能宣称案例已经同源。
- CLI 的 SCC、TIA、PIPIA 和 EO 14117 输入仍需按统一 scenario 重建并增加正式预期强断言。
- `cn_flow` 需要基于同一 EO scenario 做直接请求与兼容请求的语义等价验收。
- 正式 TIA 案例二、PIPIA 案例二、EO 14117 绿灯案例需要明确补入或登记不进入开发案例的原因。
- Review 第二例仍是产品扩展案例，缺少正式来源定位。
- 本地 HTTP、认证、上传、异步状态、SSE、浏览器执行流、报告和引用跳转验收尚未执行。
- 远程部署未执行，必须等待用户明确同意。

## 结论

本阶段完成的是“前端案例事实纠正”和“cn_flow 兼容误判修复”。测试全绿不等于前端与 CLI 已统一；主方案继续保留在 `status/todo/`，下一阶段必须建立共享 scenario 和双适配门禁。
