# DataComplyFlow TIA 共享案例本地验收

> 日期：2026-08-11
> 对应方案：`status/todo/DataComplyFlow_前端与CLI案例统一及Trace可视化改造方案_20260811.md`
> 范围：TIA 正式案例一和三；仅本地，未连接远程，未部署

## 已完成

两条前端正式案例和 CLI 已共同读取：

- `benchmarks/cases/tia/innovate_crm_us_saas/`
- `benchmarks/cases/tia/leiden_clinical_india/`

共享请求保存完整叙述和 `structured_input`。前端先拆回表单字段，再通过真实 builder 重建请求；测试要求重建结果与共享 request 深度相等。

通用 `TIA - Template.docx` 只标记为 `other`，不冒充第三国法律分析、签署 SCC 或技术措施实施证据。

## 结论口径

正式资料要求草案记录“补充措施有效时可进行”。系统最终执行决策另设证据门禁：

```text
正式草案结论：有条件可进行 / 高度条件化可进行
当前执行决策：suspend
原因：签署 SCC、第三国法律分析、技术实施证据均未提交
```

两层结论同时保留，不能用自述措施直接授权实际传输。

## 修复问题

1. 前端 TIA 现在透传结构化国家、角色、数据类别和技术控制事实，不再只走关键词兼容路径。
2. `IN` 曾被短字符串模糊匹配成充分性国家，导致印度错误进入 `adequacy_simplified`。
3. 国家别名和安全匹配已下沉为 TIA 域公共能力，由风险评估和路由共同使用。
4. 原 CLI 第二例的三 PDF 解析技术测试已移入服务单元测试 helper，不再反向绑定业务案例目录；真实 PDF 解析和引用同步覆盖仍保留。

## 本地验证

```text
TIA 领域测试：36 passed
TIA CLI：2 PASS / 0 FAIL，每例35个断言
前端全量：151 passed，2 skipped
前端构建：通过
case parity：11 modules，23 CLI cases，521 leaf checks，27 developer cases
```

最近 CLI 运行：

```text
runs/tia/20260811_214237_505224_01_minimal
runs/tia/20260811_214245_972341_02_structured_local_attachment
```

## 提交

```text
b1e20b4 feat(cases): add official TIA scenario facts
83437fd feat(cases): unify official TIA scenarios
```

## 未完成

- 正式案例二“法国到英国充分性决定”尚未进入共享案例；
- 真实 HTTP、浏览器表单、上传、SSE、报告和引用跳转尚未验收；
- 远程部署未执行。

## 结论

当前完成的是两条已有前端 TIA 案例的前端/CLI 同源和确定性证据门禁，不代表 TIA 正式资料三条案例已全部覆盖。
