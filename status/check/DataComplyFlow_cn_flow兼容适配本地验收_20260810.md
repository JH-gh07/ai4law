# DataComplyFlow `cn_flow` 兼容适配本地验收（2026-08-10）

## 结论

旧 `cn_flow` 入口已完成第一阶段接管：输入先经过兼容适配，再由 `us_14117` 统一执行规则、RAG、报告和产物生成。旧 API 返回结构和 DOCX 主报告路径保持兼容。未进行远程操作。

## 代码改动

| 文件 | 改动 | 目的 |
|---|---|---|
| `backend/domains/us/eo14117_flow_review/compatibility.py` | 新增旧请求到 `US14117Request` 的转换边界 | 统一业务实现，记录信息损失 |
| `backend/domains/us/eo14117_flow_review/schema.py` | 增加 `us_person_count`、`transaction_type`、`doj_data_category_by_item` | 允许旧表单逐步补齐结果关键事实 |
| `backend/domains/us/eo14117_flow_review/service.py` | `generate_report()` 先适配，再委托 `US14117Service` | 消除主入口重复规则执行 |
| `backend/domains/us/eo14117_flow_review/tests/test_compatibility.py` | 新增适配契约测试 | 防止缺失事实被静默补默认值 |
| `backend/domains/us/eo14117_flow_review/tests/test_service.py` | 补充统一路径所需字段 | 验证历史响应兼容 |

旧独立实现已在 parity 测试通过后删除。`cn_flow` 只保留兼容转换、旧 API/任务契约和旧响应包装；规则、RAG、章节与产物全部由 `us_14117` 负责。

## 安全行为

- 缺 `us_person_count`：返回补充问题，不填 `0`。
- 缺 `transaction_type`：返回补充问题，不猜测交易类型。
- 缺 DOJ 数据分类：逐项列出待补字段。
- 附件只传递 `storage_uri`，并在 `lossy_fields` 标记 `attachments.content_unparsed`。
- 兼容结果记录 `canonical_module=us_14117` 和 `compatibility_lossy_field:*`。

## 本地测试证据

```text
uv run pytest backend/domains/us/eo14117_flow_review/tests backend/domains/us/eo14117/tests -q
36 passed, 1 warning
```

已覆盖：同步生成、异步提交与轮询、规则结果、统一产物、历史 `cn_flow_request` 事件、缺失事实拦截、完整请求转换。

补充验核：同一组事实经兼容适配和直接构造 canonical 请求后，红黄绿结论、规则 ID、法规条款和命中状态完全一致；RED 数据经纪场景已加入自动测试。

## 尚未完成

1. 旧输入案例补齐新字段并运行全量 parity，对比旧结果与 canonical 结果。
2. 异步任务中对适配失败状态的前端展示验收。
3. 完成 diagnosis、assessment、14117 浏览器闭环及截图验收。

## 旧实现删除复验

删除文件：

```text
backend/domains/us/eo14117_flow_review/fact_builder.py
backend/domains/us/eo14117_flow_review/issue_builder.py
backend/domains/us/eo14117_flow_review/evidence_builder.py
```

`service.py` 已重写为兼容薄层。删除后的本地回归：

```text
69 passed
ruff: All checks passed
```

## Git

本阶段已提交：

```text
bf9463c feat: add cn flow compatibility boundary
```

服务接入改动待本地全量测试后单独提交。

后续已完成提交：

```text
5749e57 refactor: delegate cn flow reports to EO 14117
c5e4bd7 fix: reject incomplete legacy cn flow requests
ae5f90e fix: align cn flow test inputs with canonical fields
9a2deb8 fix: expose canonical facts in legacy cn flow form
```
