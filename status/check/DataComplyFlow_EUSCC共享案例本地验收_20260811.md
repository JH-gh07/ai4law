# DataComplyFlow EU SCC 共享案例本地验收

> 日期：2026-08-11
> 对应方案：`status/todo/DataComplyFlow_前端与CLI案例统一及Trace可视化改造方案_20260811.md`
> 范围：EU SCC 三条正式案例的共享事实、CLI 强断言、前端请求等价和规则缺口；仅本地，未连接远程，未部署

## 已完成内容

EU SCC 三条正式案例已建立统一 `scenario.json` 和 `expected.json`：

1. 法国电商 C2C 到英国关联公司，存在美国 AWS 下游处理和存储；
2. 德国健康研究公司 C2P 到印度处理者，Clause 15 被削弱、健康数据被错误分类；
3. 荷兰处理者 P2P 到塞尔维亚子处理者，但文档错误声明 Module Two，上游控制者信息不完整。

CLI 外壳只引用共享文件，不再复制输入和预期。第二例继续使用正式抽取的上传 DOCX，并保留：

- 上传 DOCX 解析；
- `attachment_notes`；
- `annotated_docx` 输出断言。

前端从同一共享请求生成表单默认值，再调用真实 `buildEuSccPayload()`。测试对三条前端 payload 与共享 request 做深度相等比较。

## 修复的逻辑问题

### 1. TIA 和补充措施事实反转

旧逻辑根据两段审查说明是否有文字推断 `has_tia` 和 `has_supplementary_measures`。用户写“缺少 TIA”时，反而可能被转换为“已有 TIA”。

现改为两个独立复选字段，builder 原样传递布尔事实；说明文字不再改变事实。

### 2. 实际角色和声明模块无法分离

旧表单用同一个角色选项同时决定实际角色和文档模块，无法表达正式第三例。

现改为：

```text
transfer_role            → 实际出口方/进口方角色
declared_module_type     → 被审查文档声明的模块
```

第三例因此可真实传入：实际 `processor → processor`，声明 `Module Two`，后端正确得到 `expected Module Three / actual Module Two`。

### 3. Annex I.B 未披露美国最终位置

正式第一例要求指出 Annex I.B 没有写明美国最终处理或存储位置。旧实现只发现美国需要 TIA 和补充措施，没有对 Annex I.B 单独出具 finding。

现由解析器保存 Annex I.B 原始片段，规则引擎比较完整传输链和 Annex I.B 已披露位置；缺失时产生 `annex_incomplete`，并由 CLI 强断言验证 `Annex I.B` 和 `United States`。

## 本地验证

```text
EU SCC CLI：3 PASS / 0 FAIL
案例一：27 passed
案例二：28 passed
案例三：23 passed

前端全量：151 passed，2 skipped
前端 SCC/builder 定向：57 passed
前端生产构建：通过

case parity：11 modules
CLI cases：23
leaf checks：501
developer cases：27
```

最近一次 CLI 运行目录：

```text
runs/eu_scc/20260811_212203_228650_01_minimal
runs/eu_scc/20260811_212206_487738_02_india_health_uploaded
runs/eu_scc/20260811_212207_255349_03_module_mismatch
```

SCC 领域测试结果为 `25 passed / 1 failed`。失败项是既有的 `citation_map.display_label` 未出现 `2021/914`，对应项目此前记录的单项 SCC 标签失败；本阶段没有修改用户正在处理的 `issue_builder.py`，不能把该失败写成通过。

## 提交记录

```text
b68377a feat(cases): share official SCC scenarios
baec1f7 feat(cases): unify official SCC scenarios
```

## 尚未完成

- TIA、PIPIA 等其他模块尚未全部迁移为共享案例；
- EU SCC 三条案例尚未完成真实本地 HTTP 和浏览器一键运行截图；
- 上传、异步状态、SSE 执行流、报告展示和引用跳转仍需浏览器分别验收；
- SCC `citation_map.display_label` 既有失败仍待独立修复；
- 远程部署未执行，必须等待用户明确同意。

## 结论

EU SCC 三条正式案例已完成“正式资料 → 共享事实 → CLI → 前端 builder”的本地统一，且保留了上传 DOCX 和批注产物覆盖。该结论不包含浏览器链路，也不代表总体方案已经完成。
