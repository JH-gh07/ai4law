# DataComplyFlow 执行流「实时事件不显示」— 根因确认

> 审计日期：2026-08-06  
> 问题：运行中及运行后始终"事件 0、节点 0、Token --、用时 --"  
> 结论：**Bearer Token 没有进入事件通道，所有 SSE/轮询请求都被 401 拦截**

---

## 确认的根因（不是"功能没做"）

后端 100% 到位、前端 UI 100% 到位，**断点在事件通道的鉴权层**。

### 证据链

**第一环**：后端 SSE/轮询端点要求登录态

`backend/api/v1/endpoints/events.py:27-33`：
```python
@router.get("/task/{task_id}/stream")
async def task_event_stream(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),  # ← 需要 Bearer token
):
    require_task_access(db, task_id=task_id, user_id=current_user.id)
```

**第二环**：前端认证机制是 Bearer token（`localStorage`/`sessionStorage`）

`frontend/src/api/auth.ts:37-40`：
```typescript
export function getAuthHeaders(): Record<string, string> {
  const token = getToken();  // ← 从 localStorage/sessionStorage 读 token
  return token ? { Authorization: `Bearer ${token}` } : {};
}
```

**第三环**：`fetchTaskEvents` 没有传 token

`frontend/src/api/events.ts:12-20`：
```typescript
export async function fetchTaskEvents<TEvent>(
  taskId: string,
  since: number,
): Promise<TaskEventsResponse<TEvent>> {
  const response = await apiFetch(
    `/api/v1/events/task/${encodeURIComponent(taskId)}/events?since=${since}`,
    // ← 没有 headers！没有 Authorization！
  );
  return (await response.json()) as TaskEventsResponse<TEvent>;
}
```

**第四环**：SSE `EventSource` 无法传自定义 header

`frontend/src/lib/useTaskEvents.ts:110`：
```typescript
const es = new EventSource(getTaskEventStreamUrl(taskId));
// EventSource API 不支持自定义 headers
// → Authorization: Bearer xxx 无法传入
```

---

## 完整断链流程（以 assessment 一键体验为例）

```
T0    浏览器点击"一键体验"
T0    runModule() → POST /assessment/generate_async  （带 Authorization: Bearer xxx ✅）
T0    后端收到请求，鉴权通过 → submit_with_trace → 后台线程开始执行
T0    后端 trace.record() 逐个推送 RunEvent → SSEManager.publish → 事件写入内存队列
T0    后端 SSE endpoint 等待 EventSource 连接...

T0    前端收到 task_id → handleTaskCreated → setActiveTaskId("xxx") → setActiveTab("timeline")
T0    React 渲染 RunTranscript({taskId: "xxx"})
T0    useTaskEvents("xxx") 启动：

      ┌─────────────────────────────────────────────────┐
      │  SSE 通道：                                      │
      │  new EventSource("/api/v1/events/task/xxx/stream")│
      │  → 浏览器发出 GET 请求                            │
      │  → 请求头：无 Authorization                      │  ← 断点！
      │  → 后端 require_task_access() → Bearer token 为空  │
      │  → get_current_user() → 401 UNAUTHORIZED        │
      │  → EventSource.onerror → EventSource.CLOSED     │
      │  → 3 秒后触发 polling fallback                  │
      └─────────────────────────────────────────────────┘

      ┌─────────────────────────────────────────────────┐
      │  Polling 通道（3 秒后）：                         │
      │  fetchTaskEvents("xxx", since=-1)                │
      │  → fetch("/api/v1/events/task/xxx/events?since=-1")│
      │  → 请求头：无 Authorization                      │  ← 再次断点！
      │  → 后端 → 401 UNAUTHORIZED                      │
      │  → 每隔 1.5 秒重试，永远 401                    │
      └─────────────────────────────────────────────────┘

T0-30s 后端任务执行完成 → 22 项产物生成 ✅
       后端 sm.publish("COMPLETED") → 事件在内存中等待推送
       但没有任何客户端订阅了它的 SSE 队列
       因为前端两次尝试连接都被 401 拦截

T30    30 分钟后 SSEManager.cleanup_expired() 清空内存事件

最终    浏览器页面：
        ✅ 左侧资源面板：22 项产物
        ❌ 执行时间线：事件 0、节点 0
        ❌ 模块 Token：--
        ❌ 总 Token：--
        ❌ 用时：--
        ❌ "暂无执行记录"
```

对比：`POST /assessment/generate_async` 为什么能通过？

```
POST /assessment/generate_async
  → headers: { "Content-Type": "application/json", "Authorization": "Bearer xxx" } ✅
  → 鉴权通过 → 业务逻辑执行 → 22 项产物正常生成

GET /events/task/xxx/stream
  → headers: { } ❌ ← 没有 Authorization
  → 鉴权失败 → 401 → 事件永远传不到前端
```

---

## 为什么历史 trace 文件存在但不能回放？

后端确实把每个事件写了 JSON 文件：
```
outputs/assessment/<task_id>/trace/
  001_assessment_request.json
  002_profile_extracted.json
  003_diagnosis.json
  ...
  manifest.json
```

但 `RunTranscript` 不会读这些文件。它只走两个通道：
- SSE → 被 401 挡住
- polling API → 被 401 挡住

历史 trace 文件是**后端审计用的**，没有被设计成前端可读取的 API。前端有 `GET /task/{task_id}/manifest` 端点可以拿到 `run_manifest.json`，但那份 JSON 只有汇总数字（event_count），不包含每条 event 的 detail。

---

## 三个修复方向

### 方案 A（最小改动）：polling 加 token

```diff
// frontend/src/api/events.ts
+ import { getAuthHeaders } from "./auth";

  export async function fetchTaskEvents<TEvent>(
    taskId: string,
    since: number,
  ): Promise<TaskEventsResponse<TEvent>> {
    const response = await apiFetch(
      `/api/v1/events/task/${encodeURIComponent(taskId)}/events?since=${since}`,
+     { headers: getAuthHeaders() }
    );
    return (await response.json()) as TaskEventsResponse<TEvent>;
  }
```

**效果**：polling 可以工作。SSE 仍然不行（EventSource 不支持自定义 header），但 polling 每 1.5s 拉一次，实时性差但至少能看到事件。

### 方案 B：SSE 替换为 fetch + ReadableStream

```typescript
// 用 fetch() 替代 EventSource，手动解析 SSE 流，同时传 Auth header
async function* sseStream(url: string, token: string): AsyncGenerator<string> {
  const response = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const reader = response.body!.getReader();
  // 逐块解析 SSE data: ...\n\n 格式
  // ...
}
```

**效果**：真正的实时推送，与当前行为一致。

### 方案 C（最彻底）：SSE URL 带 token 参数

```python
# 后端：增加 query param 鉴权 fallback
@router.get("/task/{task_id}/stream")
async def task_event_stream(token: str = Query(...), ...):
    user = await verify_token(token)
    require_task_access(db, task_id, user.id)
```

```typescript
// 前端：token 拼进 URL
const url = `${getTaskEventStreamUrl(taskId)}?token=${encodeURIComponent(token)}`;
const es = new EventSource(url);
```

**风险**：token 暴露在 URL 中（浏览记录、服务器日志），不适合生产环境。

### 推荐组合

- **短期（立即修复）**：方案 A — `fetchTaskEvents` 加 `getAuthHeaders()`，至少 polling 通
- **中期**：方案 B — fetch-based SSE，真正的实时推送 + auth
- **如果已经有计划换 cookie-based auth**：那方案 C 可快速过度

---

## 不是 bug 的部分（确认功能代码正确）

| 组件 | 状态 | 验证 |
|------|------|------|
| 后端 `TraceRecorder.record()` → `subscriber` 推送 | ✅ 完成 | 单元测试覆盖 |
| 后端 `SSEManager.publish()` → 队列分发 | ✅ 完成 | 单元测试覆盖 |
| 后端 `InMemoryTaskManager.submit_with_trace()` → `trace_recorder.subscribe(sm)` | ✅ 完成 | 单元测试覆盖 |
| 后端 SSE endpoint generator → `await queue.get()` → `yield` | ✅ 完成 | 代码逻辑正确 |
| 后端 polling endpoint `get_events_since` | ✅ 完成 | 代码逻辑正确 |
| 前端 `useTaskEvents` SSE + polling fallback + merge | ✅ 完成 | 单元测试覆盖 |
| 前端 `extractTokenUsage` | ✅ 完成 | 单元测试覆盖 |
| 前端 `adaptEvents` | ✅ 完成 | 单元测试覆盖 |
| 前端 `RunTranscript` / `TraceRunHeader` / `TraceNodeView` | ✅ 完成 | 有 events 时能正确渲染 |
| 前端 `TaskEventBridge` → app store dispatch | ✅ 完成 | 代码逻辑正确 |
| 前端 `WorkspaceShell.handleTaskCreated` → `setActiveTaskId` | ✅ 完成 | 代码逻辑正确 |

**唯一的断点**：Bearer token 过不了事件通道的鉴权层。这是一个发现级问题——所有代码逻辑都是对的，但 auth 机制的设计隐含了"需要 auth 的端点不能被 EventSource 消费"的冲突。
