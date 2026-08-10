# DataComplyFlow Review 执行流与终态同步修复验收

> 日期：2026-08-11
> 范围：Review 执行流为空、服务重启后前端状态残留
> 代码状态：本地修复
> 远程部署：未执行

## 一、复现事实

目标任务 `b5c782bb-f60a-4a97-b2f5-7b5906f36fbb` 的后端状态曾为 `REVIEWING / 62%`，但 `run_events` 为 0。后端重新启动后，启动收尾逻辑将其更新为 `FAILED / 62%`。

同一任务在前端工作区同时存在两条记录：一条使用原任务空间 ID，一条错误地使用后端异步任务 ID作为任务空间 ID，导致恢复时出现重复运行记录。

## 二、根因

1. Review 原来只写数据库进度和专用 WebSocket，不写统一 `RunEvent/SSE`，所以执行流无法显示阶段。
2. 前端恢复使用运行记录自身 `id` 去重，没有按 `asyncTaskId` 去重，服务器终态无法稳定覆盖本地 running 记录。
3. Review 执行中存在“结构化响应解析失败但使用确定性结果继续”的中间事件，终态判断必须以明确的 `COMPLETED/FAILED/CANCELED` 状态为准，不能把普通告警当作任务终态。

## 三、修复内容

### 后端

- Review 每次阶段更新写入统一 `status` RunEvent。
- 每条条款审查写入 `tool_start` 和 `tool_result` RunEvent。
- 异常写入明确 `FAILED` 终态事件。
- 保留原专用 WebSocket，兼容已有进度显示。

### 前端

- workspace 恢复时按 `asyncTaskId` 合并同一异步任务。
- 合并时保留原任务空间 ID。
- 有明确终态的服务器记录覆盖本地 `running` 记录。
- 运行中间告警不再改变任务最终状态；最终状态以终态事件为准。

## 四、验证结果

```text
uv run pytest backend/api/v1/tests/test_review_async.py backend/common/events/tests/test_persistent_event_log.py -q
14 passed

npm test -- --run src/lib/app-store.test.ts src/lib/useTaskEvents.test.ts
7 passed

npm run build
通过
```

新增回归验证：

- Review 完成后统一事件接口存在 `status`、`tool_start`、`tool_result` 和 `COMPLETED` 事件。
- 同一个 `asyncTaskId` 的本地 running 与服务器 failed 只保留一条。
- 服务器终态覆盖本地旧状态，并保留原任务空间 ID。

## 五、当前真实状态

```text
b5c782bb-f60a-4a97-b2f5-7b5906f36fbb：FAILED / 62%
```

它已经停止执行，不应继续显示运行中。重新运行时应生成新的异步任务 ID，并在同一个任务空间内更新。

## 六、验收结论

- [x] Review 执行流接入统一 RunEvent/SSE。
- [x] Review 终态可回放。
- [x] 同一异步任务不再产生重复运行记录。
- [x] 服务器终态覆盖本地旧状态。
- [x] 后端专项测试通过。
- [x] 前端专项测试通过。
- [x] 前端构建通过。
- [ ] 登录态浏览器截图验收待执行。
- [ ] 远程部署待用户明确授权。
