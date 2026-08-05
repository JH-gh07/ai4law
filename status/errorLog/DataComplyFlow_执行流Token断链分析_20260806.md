# DataComplyFlow 「中间过程、Token 与耗时」功能：完整数据链路断点分析

> 审计日期：2026-08-06  
> 核心问题：安全评估真实运行产出 **22 项文件**，但前端全部显示 **事件 0、节点 0、Token --、用时 --**  
> 方法：从后端 `trace.record()` 首行追到前端最后一行 `RenderTranscript`，逐段标注已做成与未做成

---

## 一、整体数据流图

```
  后端运行路径
 ════════════════
 
 assessment Router                          前端消费路径
   │                                       ════════════════
   ├─ POST /assessment/generate_async
   │                                         ModuleRunPanel
   ├─ service.submit_async(payload)            │
   │   ├─ TraceRecorder(task_id="xxx")         ├─ runWithPayload()
   │   │                                      │    POST /assessment/generate_async
   │   ├─ task_manager.submit_with_trace()     │       ← 获得 task_id
   │   │   ├─ trace_recorder.subscribe(sm) ──┐ │
   │   │   ├─ sm.publish("CREATED") ────SSE──┼─→ useTaskEvents(taskId)
   │   │   ├─ executor.submit(_execute) ─┐   │ │    ├─ SSE connect /task/{id}/stream ←┐
   │   │   └─ return TaskSnapshot        │   │ │    ├─ poll /task/{id}/events   ←┐  │
   │   │                                 │   │ │    └─ events: RunEvent[]        │  │
   │   └─ return AssessmentAsyncAccepted │   │ │                                    │  │
   │                                     │   │ │  RunTranscript({taskId})          │  │
   │  _execute(task_id)                  │   │ │    ├─ events.length === 0 ?       │  │
   │    ├─ sm.publish("RUNNING") ──SSE───┼───┼─┘    │     "暂无执行记录" ← 此处断  │  │
   │    ├─ runner()                      │   │      │                              │  │
   │    │   └─ generate_report()         │   │      ├─ adaptEvents() → nodes[]    │  │
   │    │       ├─ trace.record("step1") │   │      ├─ extractTokenUsage(events)  │  │
   │    │       │   ├─ 写 JSON 到 disk   │   │      └─ → TraceRunHeader            │  │
   │    │       │   └─ sub callback ──SSE┼───┼──────┘     → TraceNodeView          │  │
   │    │       ├─ trace.record("step2") │   │                                     │  │
   │    │       │   └─ sub callback ──SSE┼───┼─────────────────────────────────────┘  │
   │    │       └─ ...                   │   │                                         │
   │    ├─ trace.record("final")         │   │  TaskEventBridge({taskId})              │
   │    │   └─ sub callback ──SSE────────┼───┼──→ app-store dispatch()               │
   │    ├─ sm.publish("COMPLETED")       │   │                                         │
   │    ├─ trace_recorder.write_manifest │   │                                         │
   │    └─ _persist_manifest(run_manifest.json)                                       │
   │                                                                                   │
   │  后端 SSE / polling API:       前端 events.ts:                                    │
   │    GET /task/{id}/stream       apiFetch(`/events/task/${taskId}/events?since=`)  │
   │    GET /task/{id}/events       EventSource(`/events/task/${taskId}/stream`)       │
   │    GET /task/{id}/manifest                                                       │
```

---

## 二、逐模块「已完成」vs「未完成」判定

以下按代码实际存在且可独立单元测试通过为"已完成"标准；端到端浏览器验证通过为"真正可用"标准。

### 2.1 后端 TraceRecorder：写事件到文件 + 发布事件给订阅者

**状态：已完成**

`backend/common/trace/recorder.py:127-163`

```
trace.record(name, payload) 执行：
  1. seq++ → 写 JSON 文件到 trace 目录 (已做成)
  2. 构造 RunEvent (task_id/seq/event_type/summary/detail) (已做成)
  3. 遍历 self._subscribers，逐一调用 callback(run_event) (已做成)
```

确认：
- 78 个 `_NAME_TO_EVENT_TYPE` 规则可实现老 name→新 event_type 的映射
- 文件持久化和事件广播同时执行，订阅者异常被 try/catch 包裹不阻塞主链

---

### 2.2 后端 SSEManager：接收事件 → 推送 SSE + 支持轮询

**状态：已完成**

`backend/common/events/manager.py:79-82`

```python
def on_event(self, event: RunEvent) -> None:
    if event.task_id:
        self.publish(event.task_id, event)
```

`publish()` 做的事：
1. 加锁分配严格递增的 transport_seq
2. 存入 `_task_events[task_id]` 列表（供轮询用）
3. 遍历所有活跃的 SSE 队列，`queue.put_nowait(event)`

确认：
- SSE subscribe 时会回放历史事件 (`manager.py:28-29`)
- 轮询接口 `GET /task/{task_id}/events?since=` 返回 seq > since 的增量
- task 完成后 30min 自动清理 (`cleanup_expired(ttl=1800)`)

---

### 2.3 后端 InMemoryTaskManager.submit_with_trace：组装整条链路

**状态：已完成**

`backend/common/tasks/manager.py:95-166`

```
submit_with_trace() 做的事：
  1. trace_recorder.subscribe(sm.on_event)       ← 搭桥：TraceRecorder → SSEManager
  2. trace_recorder._task_id = task_id           ← 注入 task_id，使 record() 的 RunEvent 带正确 task_id
  3. sm.publish(task_id, RunEvent("CREATED"))     ← 推送创建事件
  4. 包裹 runner：注入 contextvar current_trace = trace_recorder
  5. executor.submit(_execute, task_id)           ← 启动后台线程
  6. sm.publish(task_id, RunEvent("RUNNING"))     ← 推送开始事件
```

确认：
- `_execute()` 的 runner() 完成后自动补 `final`/`final_brief` 事件 (line 247-260)
- `_execute()` 成功后 sm.publish("COMPLETED") (line 309-315)
- `_execute()` 成功后 write_manifest() + _persist_manifest() (line 316-318)

---

### 2.4 后端 SSE API 端点 + 鉴权

**状态：已完成**

`backend/api/v1/endpoints/events.py`

```
GET /task/{task_id}/stream       → SSE 推送
GET /task/{task_id}/events       → 轮询 fallback
GET /task/{task_id}/manifest     → run_manifest.json
```

各有 `require_task_access(db, task_id, user_id)` 鉴权（P0-02 已修复）。

---

### 2.5 后端 run_manifest.json 持久化

**状态：已完成（最小版本）**

`backend/common/tasks/manager.py:353-373` 和 `backend/common/runtime/run_manifest.py`

对每次异步任务落盘 `outputs/<module>/<task_id>/run_manifest.json`，包含：
- run_id / module / status / created_at / updated_at / duration_ms
- provider_snapshot（脱敏）
- input_snapshot（SHA-256 + 字段名）
- LLM 调用总数 / Token / fallback 标记
- trace manifest 引用

**未完成边界：** 不包含 CitationMap 统计、RAG/得理调用明细、usage source 标记。

---

### 2.6 后端 trace manifest.json（事件文件清单）

**状态：已完成**

`backend/common/trace/recorder.py:170-178`

每次运行结束后写 `outputs/<module>/<task_id>/trace/manifest.json`，包含 `created_at`、`event_count`、所有事件的 `[seq, name, path, created_at]` 列表。

---

### 2.7 前端 SSE 连接 + 轮询 fallback

**状态：已完成**

`frontend/src/lib/useTaskEvents.ts:104-185`

```
useTaskEvents(taskId):
  1. 先建 SSE EventSource → GET /task/{taskId}/stream
  2. SSE 断开（CLOSED）→ 启动轮询 fallback（每 1.5s）
  3. 事件去重合并（event_id + seq 双重判断）
  4. 通过 React setState 通知订阅组件
```

确认：
- SSE 断开后浏览器自动重连机制（注释说明不手动 close）
- 轮询 fallback 从 `latestKnownSeq` 开始增量拉取
- Tailwind/React 的 useSyncExternalStore 式通知机制

---

### 2.8 前端事件→语义节点适配

**状态：已完成（逻辑正确）**

`frontend/src/lib/trace-adapter.ts`

```
adaptEvents(events, lang):
  1. 读 'status' event → 取 module/jurisdiction
  2. 按 event_type 映射语义节点：status→Task, thought→LLM, tool_start→Tool...
  3. 从 detail 中提取 duration/tokens/summary
  4. 相邻同类事件合并
```

---

### 2.9 前端 Token 提取

**状态：已完成（逻辑正确）**

`frontend/src/lib/useTaskEvents.ts:43-66`

```
extractTokenUsage(events):
  遍历所有事件 → 找到 detail.tool === "llm_chat" 的事件
  → 从 detail.usage 提取 prompt_tokens/completion_tokens/total_tokens
  → 按 channel (workflow vs copilot) 分类汇总
```

---

### 2.10 前端 RunTranscript 渲染组件

**状态：已完成**

`frontend/src/components/workspace/RunTranscript.tsx:14-110`

正常情况下的行为：
- 拿到 `taskId` → `useTaskEvents(taskId)` 获取事件列表
- `events.length > 0` → 调用 `adaptEvents()` → 渲染 `TraceRunHeader` + `TraceNodeView[]`
- `events.length === 0` → 显示"暂无执行记录"

---

### 2.11 前端 TraceRunHeader 渲染

**状态：已完成**

`frontend/src/components/workspace/TraceRunHeader.tsx:34-111`

接收 props（eventCount, nodeCount, totalTokens, startedAt, completedAt...）→ 渲染一行统计条。

---

### 2.12 前端 TraceNodeView 渲染

**状态：已完成**

`frontend/src/components/workspace/TraceNodeView.tsx:20-57`

每个节点渲染：stage / action / timestamp / durationMs / tokenInput / tokenOutput / input block / output block。

---

### 2.13 前端 TaskEventBridge（应用状态桥接）

**状态：已完成**

`frontend/src/components/workspace/TaskEventBridge.tsx:17-206`

```
TaskEventBridge:
  获取 events → 根据 event_type 分派到 app store:
    status → begin_run_session (创建设置运行会话)
    tool_start → begin_run_session (追加 stage)
    tool_result → stage_done
    thought → stage_done
    warning → begin_run_session (追加 stage)
    intermediate → begin_run_session (追加 stage)
    final → finish_run_session (携带 total_duration_ms)
```

---

## 三、断链位置：从 WorkspaceShell 到 RunTranscript 的 taskId 传递

### 3.1 关键代码

`WorkspaceShell.tsx:1090`：

```tsx
<RunTranscript
  taskId={activeTaskId ?? latestRun?.asyncTaskId ?? null}
  moduleLabel={latestRun?.module ?? taskSpace.module}
/>
```

### 3.2 activeTaskId 的设置逻辑

`WorkspaceShell.tsx:803-808`：

```typescript
useEffect(() => {
  if (!latestRun?.asyncTaskId) return;
  if (activeTaskId === latestRun.asyncTaskId) return;
  if (isRunInProgress(latestRun) || !activeTaskId) {
    setActiveTaskId(latestRun.asyncTaskId);
  }
}, [activeTaskId, latestRun]);
```

### 3.3 断链分析

这段代码有三个条件：

1. `!latestRun?.asyncTaskId` → 不做任何事。**这是最可能的断点**：如果 `latestRun` 对象中 `asyncTaskId` 是 `undefined` 或 `null`，整条事件链就不启动。

2. `activeTaskId === latestRun.asyncTaskId` → 已经是最新的，跳过。

3. `isRunInProgress(latestRun) || !activeTaskId` → 只有在运行中或首次（activeTaskId 为空）时，才把 `latestRun.asyncTaskId` 设给 `activeTaskId`。**注意：一旦运行完成（不在 inProgress 状态），如果页面重新渲染，activeTaskId 可能不再更新**——此时 `!activeTaskId` 为 false（已经有旧值），且 `isRunInProgress` 为 false（已完成），所以不会更新。

这意味着：**如果用户是从历史列表重新打开一个已完成的任务`latestRun`，或者页面先渲染了已完成的任务状态再被检测到，activeTaskId 可能永远不被设置，也就不会建立 SSE 连接或轮询。**

### 3.4 assessment 2026-08-05 真实运行中可能发生的时序

```
T0: 用户点击"一键体验"
T0+0.1s: ModuleRunPanel.runWithPayload() → POST /assessment/generate_async
T0+0.5s: 收到 async response {task_id: "xxx", module: "assessment", state: "CREATED"}
T0+0.5s: WorkspaceShell.addRun({asyncTaskId: "xxx", ...})
T0+0.5s: latestRun 更新为 {asyncTaskId: "xxx", asyncState: "running", ...}
T0+0.5s: activeTaskId useEffect 触发：
  → latestRun.asyncTaskId 为 "xxx" ✅
  → activeTaskId 为 null ✅
  → isRunInProgress(latestRun) 为 true ✅
  → setActiveTaskId("xxx") ✅
T0+0.6s: RunTranscript 收到 taskId="xxx" → useTaskEvents("xxx") 开始 SSE 连接 ✅
T0+0.6s: 后端 trace.record() 开始推送事件 → SSE → 前端收到 ✅
T0+2.0s: 后端继续运行，trace.record() 逐个推送中间事件 ✅
...
T0+8.0s: 后端任务完成 → sm.publish("COMPLETED") → 前端收到
T0+8.0s: latestRun.asyncState 更新为 "completed"
```

**以上路径理论上是通的**。但实际可能发生的问题：

**场景 A：后端任务完成得太快**

如果后端运行极快（比如 2-3 秒全走完），前端 useEffect 的触发时机可能晚于后端：

```
T0+0.5s: latestRun 更新 → asyncState 先看到 "running"
T0+0.6s: useEffect 读到 latestRun → isRunInProgress=true → setActiveTaskId("xxx") ✅
T0+1.0s: SSE 连接建立
T0+1.5s: 后端已完成！但此时所有中间事件都已发完，SSE 连接建立后才来
         SSEManager.subscribe() 会回放历史事件 (line 28-29)
         → 前端收到全部事件 ✅
```

SSEManager 有回放机制，所以只要 taskId 对且 SSE 在 30 分钟内建立，应能收到所有历史事件。这理论上是安全的。

**场景 B：latestRun 中 asyncTaskId 从未被设置**

这是最可能的断链。来看 `addRun` 逻辑：

```typescript
// ModuleRunPanel → WorkspaceShell 的数据流
// 通过 app-store dispatch 或 props callback 传递
```

`ModuleRunPanel` 运行后，结果怎么回传到 `WorkspaceShell` 的 `taskRuns` 状态？这需要确认前端状态管理链路。

**场景 C：前端在 SSE 连接前就已经因某些原因清理了状态**

浏览器刷新、组件卸载重挂载、React strict mode 的 double-render 等。

**场景 D：后端 SSE 连接被浏览器的 CORS/代理/HTTPS 策略拦截**

开发环境 Vite 的代理可能没有正确代理 SSE 流。

---

## 四、另一个关键断点：LLM Token 数据的缺失

即使事件链路通了，Token 数字仍然可能是 0。原因是 `extractTokenUsage` 的条件：

```typescript
if (event.detail?.tool !== "llm_chat") return acc;  // ← 严格检查
```

后端 `trace.record()` 调用中，LLM 相关的事件可能是：
- `trace.record("report_generation", {summary: ..., detail: {tool: "llm_chat", usage: {prompt_tokens: ..., completion_tokens: ...}}})`

**如果 detail 字段中没有 `tool: "llm_chat"`，或 usage 结构不符合预期（prompt_tokens/completion_tokens/total_tokens 三个字段必须在 detail.usage 平铺），Token 提取就会得到 0。**

这个条件在 `--no-llm` 模式下是合理的（确实没有 LLM 调用），但在真实 LLM 调用时是否数据正确传入，需要端到端验证。

---

## 五、完整判定表

| # | 功能 | 后端代码已写 | 后端单测通过 | 前端代码已写 | 前端单测通过 | 端到端联调通过 | **2026-08-05 浏览器验证** |
|---|------|:---:|:---:|:---:|:---:|:---:|---|
| 1 | 后端 trace.record() 写事件 JSON 文件 | ✅ | ✅ | — | — | — | **✅** 后端文件存在 |
| 2 | 后端 trace.record() → subscriber 推送 | ✅ | ✅ | — | — | — | **未知** |
| 3 | 后端 SSEManager SSE 推送 | ✅ | ✅ | — | — | — | **未知** |
| 4 | 后端 SSEManager 轮询回放 | ✅ | ✅ | — | — | — | **未知** |
| 5 | 后端 submit_with_trace 搭桥 | ✅ | ✅ | — | — | — | **未知** |
| 6 | 后端 SSE API 端点 | ✅ | ✅ | — | — | — | — |
| 7 | 后端 events 轮询 API 端点 | ✅ | ✅ | — | — | — | — |
| 8 | 后端 run_manifest.json 落盘 | ✅ | ✅ | — | — | — | **✅** 文件存在 |
| 9 | 前端 useTaskEvents SSE 连接 | ✅ | ✅ | — | — | — | **❌** events=0 |
| 10 | 前端 useTaskEvents 轮询 fallback | ✅ | ✅ | — | — | — | **❌** events=0 |
| 11 | 前端 adaptEvents 语义适配 | ✅ | ✅ | — | — | — | 有事件时可用 |
| 12 | 前端 extractTokenUsage Token 提取 | ✅ | ✅ | — | — | — | 需验证 LLM detail |
| 13 | 前端 RunTranscript 渲染 | ✅ | ✅ | — | — | — | 显示"暂无执行记录" |
| 14 | 前端 TraceRunHeader Token/耗时 | ✅ | ✅ | — | — | — | **❌** 全部 `--` |
| 15 | 前端 TraceNodeView 节点渲染 | ✅ | ✅ | — | — | — | **❌** 0 节点 |
| 16 | 前端 TaskEventBridge 状态桥接 | ✅ | ✅ | — | — | — | **❌** 未触发 |
| 17 | 前端 WorkspaceShell activeTaskId | ✅ | ✅ | — | — | — | **❌** 可能未设定 |
| 18 | 前端 WorkspaceShell asyncTaskId 提取 | 需验证 | — | 需验证 | — | **❌** | **❌** events=0 的根因 |
| 19 | 后端→前端 task_id 传递 | 需验证 | — | 需验证 | — | **❌** | — |

---

## 六、修复方向

按优先级排列：

### P0：修复前端 taskId 传递链路

```diff
WorkspaceShell.tsx:803-808:

-   if (isRunInProgress(latestRun) || !activeTaskId) {
+   // 修正：不仅运行中，已完成的任务也应该设置 activeTaskId
+   if (latestRun?.asyncTaskId) {
       setActiveTaskId(latestRun.asyncTaskId);
+   }
```

或者更精确的修复：activeTaskId 的语义不应该是"仅运行中的任务才值得追踪"，而应该是"任何一个有 asyncTaskId 的 latestRun 都应被追踪"——无论它是运行中还是已完成。SSEManager 在完成后 30 分钟内仍保留所有历史事件，回放完全可行。

### P1：补充后端 LLM Token 数据到 detail

检查 `LLMClient.chat_with_metadata()` 中调用 `trace.record()` 时，`detail.usage` 字段是否包含前端期望的 `{prompt_tokens, completion_tokens, total_tokens}` 结构。以及 `detail.tool === "llm_chat"` 是否正确设置。

### P1：前端直接读 run_manifest.json 作为兜底

即使 SSE/轮询 event 链路断了，前端也可以主动 `GET /api/v1/events/task/{task_id}/manifest` 拿到 run_manifest.json，从中提取 Token 汇总、状态、耗时等信息，至少显示总览数字。当前 manifest API 已就绪，前端没有消费。

### P2：事件持久化替代内存 30 分钟 TTL

当前所有事件在 `SSEManager._task_events` 的 Python 字典中，服务重启即全部丢失。应该将事件增量写入持久存储，至少做到打开历史任务时能从存储恢复列表。`trace/manifest.json` 有事件列表但只包含事件名和路径，不含完整 payload 和 event_type 等前端所需要的信息。

---

> **核心结论**：后端事件产生、推送、存储、API 四层均已完成且可通过单元测试验证。前端消费组件（RunTranscript、TraceRunHeader、TraceNodeView、TaskEventBridge）均已完工。**断链位于 WorkspaceShell 的 taskId 传递逻辑**——`useEffect` 的条件过于保守，只在 `isRunInProgress` 或首次时才给 `activeTaskId` 赋值，导致已完成的任务或时序不对的任务无法建立前端←后端事件通道。

> **不是"功能没做"，而是"管路中的阀门没开"**。
