# DataComplyFlow 执行流实时事件系统 — 成熟架构设计

> 文档性质：理想架构方案，不是当前实现描述  
> 目标读者：开发者、架构评审、重构参考  
> 核心原则：**一次写入，多处消费；事件即事实，通道即视图**

---

## 当前落实状态（2026-08-06）

本文件已从纯目标态方案进入实际落地阶段。当前代码已经完成：

1. `run_events` 数据库事件表，按 `(task_id, seq)` 唯一并以 `event_id` 幂等
2. EventLog 先持久化、后推送；服务重启后轮询和 SSE 均可从数据库回放
3. SSE `id: seq`、`Last-Event-ID` / `since` 断点续传，以及跨 worker 数据库追赶
4. 数据库共享、任务绑定、五分钟有效的哈希 stream token
5. 前端 SSE 失败后重新申请 token，并自动启用轮询容灾
6. 历史事件分页、500 条浏览器缓冲上限、终态自动关闭实时连接
7. `correlation_id` 持久化及交错工具调用配对
8. `detail.llm` 规范化 Token 契约，并兼容旧 `detail.tool/detail.usage` 数据
9. `CANCELED` 持久终态事件、任务取消上下文和 LLM 调用边界检查
10. 前端从 `run_manifest` 获取最终 Token、耗时和状态作为权威值

仍未完成：TaskRecord 持久化与运行中任务重启恢复、价格表与精确成本核算、OTel export、事件保留/归档策略，以及底层 SDK 对正在阻塞的同步 HTTP 请求进行强制中断。当前已经保证事件和已完成历史可恢复，但运行中的线程任务不会在服务重启后自动续跑。取消属于协作式取消：状态立即终止，流水线在下一个取消检查边界停止，已发出的同步请求需要等待 SDK 返回。

---

## 零、设计目标

一个成熟的实时执行事件系统，应该满足：

1. **实时可见**：用户提交后立即看到进度条开始走、第一个节点亮起
2. **离线可查**：关了浏览器再打开，历史任务的完整执行轨迹可完整回放
3. **进程重启不丢**：服务挂了重启后，已完成任务的事件不丢失
4. **可核算**：每次运行的 token 总量、LLM 调用次数、花费成本可精确核账
5. **可审计**：每个法律结论反查得到"由哪个 Agent 步骤产生、用了哪些法规条文"
6. **前端三端一致**：浏览器实时视图、历史回放视图、CLI 的 `--events` 输出时间线完全对齐

---

## 一、全局架构总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              前端 (React)                                    │
│                                                                              │
│  ModuleRunPanel                    WorkspaceShell                            │
│  ┌──────────────────────┐         ┌──────────────────────────────────┐      │
│  │ runWithPayload()      │         │ handleTaskCreated(taskId)         │      │
│  │  → POST /gen_async   │────────→│  → addRun({asyncTaskId})         │      │
│  │  ← {task_id, state}   │         │  → setActiveTab("timeline")      │      │
│  └──────────────────────┘         └──────────────────────────────────┘      │
│                                                                              │
│  ┌─────────────────────┐   ┌──────────────────────────────────────────┐     │
│  │ TaskStatusPoller     │   │ RunTranscript({taskId})                  │     │
│  │ 轮询 /tasks/{id}     │   │  ┌──────────────────────────────────┐   │     │
│  │ 获取 state + result  │   │  │ useTaskEvents(taskId)            │   │     │
│  └─────────────────────┘   │  │  ├─ fetchSSEStream(taskId, token)│   │     │
│                             │  │  │  (fetch+ReadableStream 替代   │   │     │
│                             │  │  │   EventSource，可传 Auth hdr) │   │     │
│                             │  │  ├─ fallback: poll /events      │   │     │
│                             │  │  └─ mergeEvents() 去重合并      │   │     │
│                             │  └──────────────────────────────────┘   │     │
│                             │                                          │     │
│                             │  如果实时通道正常:                        │     │
│                             │    events 流 → adaptEvents() → nodes[]   │     │
│                             │    → TraceRunHeader + TraceNodeView[]    │     │
│                             │                                          │     │
│                             │  如果打开历史已完成任务:                  │     │
│                             │    1. GET /events/task/{id}/manifest    │     │
│                             │       → 取汇总(Token,耗时,产物列表)      │     │
│                             │    2. GET /events/task/{id}/events      │     │
│                             │       → 取完整事件列表(从持久存储)       │     │
│                             │    3. adaptEvents() → 渲染时间线         │     │
│                             └──────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
        │                          │                          │
        ▼                          ▼                          ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                          后端 (FastAPI)                                        │
│                                                                                │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐ │
│  │ POST /gen_async       │  │ GET /events/stream    │  │ GET /events/list     │ │
│  │ → 鉴权 (Bearer token) │  │ → 鉴权 (Query token   │  │ → 鉴权 (Bearer)      │ │
│  │ → 创建 task           │  │   或 Bearer via fetch) │  │ → 返回持久事件列表   │ │
│  │ → 返回 task_id        │  │ → SSE 推送实时事件    │  │   (服务重启后仍可用) │ │
│  └──────────────────────┘  └──────────────────────┘  └──────────────────────┘ │
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────┐         │
│  │                     TaskManager (持久化)                          │         │
│  │  ┌────────────┐   ┌────────────┐   ┌────────────────────────┐   │         │
│  │  │ TaskRecord  │   │ RunManifest│   │ EventLog (append-only) │   │         │
│  │  │ (SQLite)    │   │ (JSON文件) │   │ (SQLite / JSONL文件)   │   │         │
│  │  │ task_id     │   │ run_id     │   │ task_id + seq + event  │   │         │
│  │  │ user_id     │   │ status     │   │ 服务重启后不丢失       │   │         │
│  │  │ module      │   │ tokens     │   │ 支持 range query       │   │         │
│  │  │ state       │   │ duration   │   │ 支持全量回放           │   │         │
│  │  │ created_at  │   │ artifacts  │   └────────────────────────┘   │         │
│  │  └────────────┘   └────────────┘                                  │         │
│  └──────────────────────────────────────────────────────────────────┘         │
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────┐         │
│  │                  EventBroker (内存 + 持久双写)                    │         │
│  │                                                                    │         │
│  │  trace.record(name, payload)                                      │         │
│  │    ├─ 1. 写持久 EventLog ────→ DB/JSONL (append-only, 不丢)      │         │
│  │    ├─ 2. 写审计 JSON 文件 ──→ outputs/<module>/<task>/trace/     │         │
│  │    ├─ 3. 通知内存订阅者 ────→ SSEManager.publish() → SSE push    │         │
│  │    └─ 4. (可选) OTel export ────→ 技术监控系统                    │         │
│  └──────────────────────────────────────────────────────────────────┘         │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、分层详解

### 2.1 事件模型设计

成熟的事件模型是分层的不平铺的：

```
┌─────────────────────────────────────────────────────────┐
│                   RunManifest (业务账本)                  │
│  run_id / user_id / module / case_id                     │
│  status / started_at / completed_at / duration_ms        │
│  provider_snapshot (model, URL指纹, 健康检查ID)          │
│  input_summary (SHA-256, 字段名, 文件引用)               │
│  output_artifacts[{role, path, sha256, mime}]            │
│  summary: {llm_calls, tokens, costs, rag_hits, ...}     │
│  citation_summary: {total, exact_article, unresolved}   │
│  trace_ref: "outputs/.../trace/manifest.json"           │
└─────────────────────────────────────────────────────────┘
                           │
                           │ 1:1
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   RunEvent[] (事件流)                     │
│                                                          │
│  每个事件:                                                │
│  {                                                       │
│    event_id: str (uuid)                                  │
│    task_id: str                                          │
│    seq: int        ← 严格递增，供分页/增量拉取            │
│    correlation_id?: str  ← start/result 并发配对           │
│    event_type: "status" | "thought" |                    │
│               "tool_start" | "tool_result" |             │
│               "intermediate" | "warning" |              │
│               "final" | "final_brief"                    │
│    timestamp: ISO8601                                    │
│    stage: "Task" | "LLM" | "RAG" | "Tool" | "Review"   │
│    summary: str (人类可读的一行摘要)                       │
│                                                          │
│    detail?: {                                            │
│      // LLM 事件特有                                      │
│      llm?: {model, provider, prompt_tokens,             │
│              completion_tokens, latency_ms,              │
│              fallback: bool}                             │
│      // RAG 事件特有                                      │
│      rag?: {index, query, hit_count, latency_ms,         │
│              top_source_ids}                             │
│      // 工具事件特有                                      │
│      tool?: str                                          │
│      // 通用                                              │
│      duration_ms?: number                                │
│      error?: string                                      │
│    }                                                     │
│  }                                                       │
└─────────────────────────────────────────────────────────┘
```

关键设计原则：
- **event_type 区分生命周期**：`tool_start` + `tool_result` 通过 `correlation_id` 成对出现
- **detail 字段结构化**：不是 blob JSON，而是按 `tool`/`llm`/`rag` 分组的类型化子对象，前端明确知道取哪个字段
- **seq 严格递增且全局统一**：不依赖 `PYTHONHASHSEED` 或线程序号，由 EventLog 统一分配

### 2.2 持久化策略：双写 + 分层存储

```
事件写入（trace.record 触发）:

  trace.record("rag_retrieval", {
    summary: "检索完成: 8 条命中",
    detail: {
      rag: {index: "legal_index_cn", query: "个人信息保护法第39条",
            hit_count: 8, latency_ms: 361},
      duration_ms: 361
    }
  })

  ┌───────────── 同时写入三个地方 ─────────────┐
  │                                              │
  ▼                                              ▼
┌─────────────────────┐              ┌─────────────────────────┐
│ 持久 EventLog        │              │ 审计 JSON 文件 (完整)   │
│ (SQLite 表)          │              │ outputs/<mod>/<task>/   │
│                      │              │   trace/003_rag_ret... │
│ run_id TEXT          │              │                         │
│ seq INTEGER          │              │ 用途: 开发者 debug,     │
│ event_type TEXT      │              │ 完整 prompt/response    │
│ timestamp TEXT       │              │ 保留, 人类可读          │
│ summary TEXT         │              └─────────────────────────┘
│ detail JSON          │              ┌─────────────────────────┐
│                      │              │ SSEManager 内存队列     │
│ + 索引:              │              │ (asyncio.Queue)         │
│   (run_id, seq)      │              │                         │
│                      │              │ 用途: 实时推送          │
│ 用途: 前端回放,       │              │ TTL: 任务完成后 30min  │
│ API 查询, 服务重启   │              │ 失效后自动清理          │
│ 后仍可用             │              └─────────────────────────┘
└─────────────────────┘
```

为什么需要 EventLog（SQLite 表）而不只依赖文件？

1. **服务重启后可用**：SSEManager 内存队列在重启时清空，EventLog 在 SQLite 中持久存在
2. **范围查询**：`SELECT * FROM events WHERE run_id=? AND seq > ? ORDER BY seq` 天然支持增量拉取
3. **轻量**：每条事件约 500 bytes，一次运行 50 个事件 = 25KB，10万次运行 = 2.5GB，SQLite 完全扛得住
4. **无需维护额外文件**：不像 JSON 文件需要扫描目录、排序、解析，SQLite 自带 B-tree 索引

### 2.3 鉴权策略：一对短期 token，解决 EventSource 的固有问题

问题的根源是浏览器 `EventSource` API 不支持自定义 HTTP header。成熟的解法有三条路：

#### 方案 A：SSE 通道用任务绑定短期 token（当前已实现）

```
流程:
  1. 前端拿到 task_id 后
  2. POST /events/task/{task_id}/token  （带 Bearer token，正常鉴权）
     → 后端验证: 当前用户是 task 的所有者
     → 生成随机 stream_token，数据库只保存 SHA-256 哈希
     → token 5分钟过期，只绑定这个 task_id 和 user_id
     → 返回 {stream_token: "eyJ..."}
  3. new EventSource(`/events/task/{task_id}/stream?token=${stream_token}`)
     → 后端验证 stream_token 的签名、过期时间、task_id 绑定
     → 鉴权通过，开始推送
  4. EventSource 断线时，前端重新申请 token，并携带 since 游标建立 SSE

优点:
  - 不需要改 EventSource，不需要引入 fetch stream
  - token 在 URL 中但有效期极短（5分钟），风险可控
  - 即使 URL 泄露，只能访问这一个 task 的事件

缺点:
  - token 出现在服务器日志/browser history 中
  - 不适合外部高安全场景
```

#### 方案 B：用 fetch + ReadableStream 替代 EventSource（更现代）

```typescript
// 前端
async function* streamEvents(taskId: string, token: string, signal: AbortSignal) {
  const resp = await fetch(`/api/v1/events/task/${taskId}/stream`, {
    headers: { Authorization: `Bearer ${token}` },
    signal,
  });
  const reader = resp.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  
  while (true) {
    const {done, value} = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, {stream: true});
    // 解析 SSE 格式: "data: {...}\n\n"
    const lines = buffer.split("\n\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      const match = line.match(/^data: (.+)$/m);
      if (match) yield JSON.parse(match[1]);
    }
  }
}

// 使用:
const controller = new AbortController();
for await (const event of streamEvents(taskId, token, controller.signal)) {
  // 处理事件
}
// 断开: controller.abort()
```

优点:
- 完整的自定义 header 控制，Bearer token 正常传入
- AbortController 精确控制断开
- 不依赖 EventSource 的自动重连（可以自己实现更智能的重连策略）

缺点:
- 需要自己管理重连逻辑和 buffer 解析
- 比 EventSource 多 ~30 行代码

#### 方案 C：切换到 Cookie-based auth（如果整个系统的 auth 策略允许）

如果全站改用 HttpOnly Cookie 做鉴权（`Set-Cookie: session=xxx; HttpOnly; SameSite=Strict`），则 EventSource 的 `credentials: "include"` 自动携带 Cookie，问题自然消失。但这是**跨模块的大改动**，不只是事件系统的事。

**推荐组合**：
- 第一阶段（立即修复）：**方案 A**，SSE URL token，改动最小
- 第二阶段（中期优化）：**方案 B**，fetch-based stream，更干净
- 如果未来整体切 Cookie auth：自动过渡到方案 C

### 2.4 前端消费的分层设计

前端对事件的消费应该是**三层**，而不是把原始事件直接丢给渲染组件：

```
Layer 1: useTaskEvents(taskId) — 数据获取层
  ├─ 打开 SSE/fetch 流（实时事件）
  ├─ 同时启动轮询 fallback（3秒延迟，仅为容灾）
  ├─ 事件去重（event_id + seq 双重去重）
  ├─ 缓冲区管理（最多保留 500 条，超过丢弃老事件）
  └─ 暴露: events: RunEvent[], isLive: boolean

Layer 2: adaptEvents(events) — 语义聚合层
  ├─ 配对: tool_start + tool_result → 一个 TraceNode (含 duration)
  ├─ detail.tool="llm_chat" 的 tool_start/tool_result → LLM 节点
  ├─ status event → 创建 Task 级节点
  ├─ 计算每个节点的: stage, action, durationMs, tokenInput, tokenOutput
  ├─ 同类连续节点合并（最多连续 3 个同 stage 节点合并为一个组）
  └─ 暴露: nodes: TraceNode[]

Layer 3: extractTokenUsage(events) + computeDuration(events) — 汇总层
  ├─ 按 channel (workflow/copilot) 分类累计 token
  ├─ 记录最早/最晚 timestamp 计算 wall-clock duration
  ├─ 暴露: {total, workflow, copilot}: TokenUsage, durationMs: number
  └─ 与 run_manifest 交叉验证（manifest 是 source of truth）
```

```typescript
// Layer 2: 关键配对逻辑示意
function adaptEvents(events: RunEvent[]): TraceNode[] {
  const nodes: TraceNode[] = [];
  const pendingStarts = new Map<string, RunEvent>(); // correlation_id → start_event

  for (const event of events) {
    switch (event.event_type) {
      case "tool_start":
        pendingStarts.set(event.correlation_id!, event);
        break;
      
      case "tool_result": {
        const startEvent = pendingStarts.get(event.correlation_id ?? "");
        if (startEvent) {
          pendingStarts.delete(event.correlation_id ?? "");
          nodes.push({
            id: `node-${event.seq}`,
            stage: mapStage(event),
            action: event.summary,
            timestamp: startEvent.timestamp,
            durationMs: msBetween(startEvent.timestamp, event.timestamp),
            tokenInput: event.detail?.llm?.prompt_tokens,
            tokenOutput: event.detail?.llm?.completion_tokens,
            status: "done",
          });
        }
        break;
      }
      
      // ... 其他类型
    }
  }
  return nodes;
}
```

### 2.5 历史回放路径

对于已完成的 run（用户从历史列表点开），不走 SSE，走这条路径：

```
前端打开历史任务
  │
  ├─ 1. GET /events/task/{run_id}/manifest
  │     ← run_manifest.json (汇总: 状态, token, 耗时, 产物列表)
  │     → 渲染 TraceRunHeader (显示总 Token、总耗时)
  │     → 渲染产物列表 (ResourcePanel)
  │
  ├─ 2. GET /events/task/{run_id}/events?since=-1&limit=200
  │     ← 从 SQLite EventLog 读取完整事件列表 (按 seq 排序)
  │     → adaptEvents() → nodes[] → 渲染 TraceNodeView
  │     → 补充 extractTokenUsage() → 与 manifest 的 token 交叉验证
  │
  └─ 3. (可选) GET /events/task/{run_id}/trace
         ← 审计级详细 trace 文件列表 (prompt/response 等)
         → 用于开发者 debug 模式
```

关键点：
- **历史回放不需要 SSE**，事件已经在 SQLite EventLog 中持久化
- **manifest 是权威汇总**：即使 EventLog 丢失，至少能看到总的 token 和耗时数字
- **前端代码完全相同**：`useTaskEvents` 检测到 task 已完成 + 无 live 连接 → 自动走 polling 全量拉取 → 同样的事件流、同样的 adaptEvents、同样的渲染

### 2.6 Token 与成本核算

成熟的 Token 核算不是"前端从事件中提取一下再显示"，而是**后端权威记账 + 前端展示**：

```
后端 LLMClient.chat_completion():
  1. 发送请求 → 拿到 response
  2. 从 response.usage 提取 {prompt_tokens, completion_tokens, total_tokens}
  3. trace.record("llm_chat", {
       summary: `LLM 调用完成 (${total_tokens} tokens)`,
       detail: {
         llm: {
           model: "hunyuan-turbo",
           provider: "tencent_hunyuan",
           prompt_tokens: 3421,
           completion_tokens: 782,
           total_tokens: 4203,
           latency_ms: 3249,
           usage_source: "provider_reported",  // ← 区分真实 vs 估算
         }
       }
     })
  4. 事件自动进入 EventLog (持久) + SSEManager (实时) + 审计文件 (debug)

后端 _execute() 完成时:
  1. 汇总所有 llm_chat 事件的 token → run_manifest.tokens
  2. 乘以单价 → run_manifest.estimated_cost (如果配置了价格表)
  3. 写 run_manifest.json

前端:
  1. 实时: extractTokenUsage(events) → TraceRunHeader 显示
  2. 最终: GET /events/task/{id}/manifest → 权威数字，替换实时汇总
     (因为前端可能在中间断连丢了一些事件，manifest 数字更准确)
```

### 2.7 错误处理与取消流程

```
            用户点击"取消"
              │
 前端          ├─ ModuleRunPanel → POST /tasks/{id}/cancel
              │     (带 Auth header)
              │
 后端          ├─ TaskManager.cancel(task_id)
              │   ├─ 1. 设置 TaskRecord.state = "CANCELED" (持久化)
              │   ├─ 2. 设置 threading.Event("cancel") (信号量)
              │   ├─ 3. trace.record("task_canceled", {summary: "用户取消"})
              │   │      → EventLog 持久 → SSE 推送
              │   └─ 4. LLM 调用边界执行取消检查:
              │          → 尚未发出请求时立即停止
              │          → 同步请求阻塞时等待 SDK 返回后停止
              │
 前端          ├─ SSE 收到 status + state="CANCELED" 事件
              │   → RunTranscript 显示 "任务已取消"
              │   → TraceRunHeader 状态: CANCELED
              │   → 显示已生成的部分产物 (如果有)
              │
              └─ 产物: 保留已完成的部分产物
                 (取消不是"全部删除"，而是"停止继续生成")
```

### 2.8 前端状态机

每个 run 在前端至少有五个明确的状态：

```
         CREATED ──→ RUNNING ──→ COMPLETED
            │           │
            │           ├──→ FAILED
            │           │
            └──→ CANCELED (用户在 CREATED 状态就取消)
                         │
                    RUNNING ──→ CANCELED (运行中途取消)
```

`useTaskEvents` 的 `isLive` 标志：

```typescript
const isLive = events.length > 0 && !events.some(e =>
  e.event_type === "status" && ["COMPLETED", "FAILED", "CANCELED"].includes(String(e.detail?.state))
);
```

当 `isLive === false` 时：
- 如果 task 是刚创建的（`Date.now() - task.created_at < 5000` 且 events 为空）→ 显示"正在连接执行引擎..."
- 如果 task 已完成 → 切换到历史回放模式，从 EventLog 拉全量
- 如果 events 为空且 task 已创建超过 timeout → 显示"执行引擎连接超时，任务可能未被正确调度"

---

## 三、数据流完整时序图

一次 assessment 运行的理想完整时序：

```
  T+0ms   前端: 用户点击"开始评估"
  T+10ms  前端: runModule() → POST /assessment/generate_async
                headers: {Authorization: "Bearer xxx"}
                body: {company_name: "...", ...}

  T+50ms  后端: 鉴权通过 → AssessmentService.submit_async()
                → 创建 TaskRecord (SQLite, state=CREATED)
                → 写 EventLog: {event_type:"status", detail:{state:"CREATED"}, seq:0}
                → 返回 {task_id: "abc-123", state: "CREATED"}

  T+100ms 前端: 收到 task_id="abc-123"
                → handleTaskCreated("abc-123")
                → addRun({asyncTaskId:"abc-123", asyncState:"CREATED"})
                → setActiveTaskId("abc-123")
                → setActiveTab("timeline")

  T+120ms 前端: RunTranscript({taskId:"abc-123"}) 挂载
                → useTaskEvents("abc-123")
                → 发起 POST /events/task/abc-123/token (带 Bearer token)
                → 拿到 stream_token

  T+150ms 前端: new EventSource(`/events/task/abc-123/stream?token=xxx`)
                → 同时启动 3 秒 fallback timer

  T+200ms 后端: SSEManager.subscribe("abc-123", queue)
                → 回放已有事件: [{seq:0, event_type:"status", detail:{state:"CREATED"}}]
                → SSE id:0 + data: {...}

  T+250ms 前端: SSE onmessage → 收到 CREATED 状态事件
                → RunTranscript: "任务已创建" 
                → TraceRunHeader: 状态 CREATED

  T+260ms 后端: submit_with_trace → executor.submit(_execute)
                → sm.publish("task_running", seq:2)
                → SSE push → 前端

  T+280ms 前端: SSE → 收到 task_running
                → TraceRunHeader: 状态 RUNNING

  T+300ms 后端: runner() 开始执行 → generate_report()
                → trace.record("profile_extracted", ...)
                  → EventLog insert (seq:3)
                  → 审计 JSON 写入文件
                  → SSEManager.publish → SSE push
                → 前端: stage="Parser", action="提取企业画像", 1s ✅

                → trace.record("rag_retrieval", {detail:{rag:{hit_count:8, latency_ms:361}}})
                  → EventLog (seq:4) → SSE push
                → 前端: stage="RAG", action="法规检索", 8条命中, 361ms ✅

                → trace.record("fact_extraction", ...)
                  → EventLog (seq:5) → SSE push

                → trace.record("fact_built", {detail:{fact_count:6}})
                  → 前端: "已提取 6 项事实"

                → trace.record("issue_built", {detail:{issue_count:4}})
                  → 前端: "已识别 4 个合规问题"

                → trace.record("evidence_built", ...)
                → 前端: "证据链构建完成"

                → trace.record("llm_chat", {
                    detail: {llm: {prompt_tokens: 3421, completion_tokens: 782, latency_ms: 3249}}
                  })
                  → EventLog (seq:9) → SSE push
                → 前端: stage="LLM", 输入3421 tokens, 输出782 tokens, 3.2s ✅
                → extractTokenUsage 实时累加到 TraceRunHeader

                → trace.record("chapters_generated", {detail: {chapter_count: 8}})
                  → 前端: "报告 8 个章节生成完成"

                → trace.record("consistency_check", ...)
                → trace.record("render", {detail: {artifact_count: 22}})

  T+5000ms 后端: runner() 完成
                → sm.publish(status={state:"COMPLETED"}, seq:22)
                  → EventLog insert (seq:22)
                  → 写 run_manifest.json {status: "COMPLETED", tokens: 4203, duration_ms: 4800}
                  → SSE push
                → 前端: TraceRunHeader 状态 COMPLETED ✅
                       总 Token: 4203 ✅
                       耗时: 4.8s ✅
                       22 项产物 ✅

  T+5100ms 前端: TaskEventBridge 收到 final → dispatch("finish_run_session")
                → app-store 更新 run 状态

  T+6000ms 用户关闭浏览器
  T+10000ms 用户重新打开浏览器 → 从历史列表点击这个 run
                → 1. GET /events/task/abc-123/manifest → {status:"COMPLETED", tokens:4203, ...}
                → 2. GET /events/task/abc-123/events?since=-1
                   ← 从 SQLite EventLog 读取全部 22 条事件
                → 3. adaptEvents() → 渲染完整时间线 ✅
                → 4. TraceRunHeader 显示与之前完全一致的数字 ✅
```

---

## 四、与当前实现的差距总结

| 成熟设计的要求 | 当前做到了什么 | 差什么 | 改动量 |
|---|---|---|---|
| 事件持久化 (服务重启不丢) | SQLite EventLog 已落地 | 补保留期与归档策略 | 小 |
| 鉴权友好的 SSE | 数据库共享短期 token 已落地 | 可选升级 Cookie/fetch stream | 可选 |
| 前端历史回放 | EventLog 分页 + manifest 权威汇总已落地 | 增加专门历史模式性能测试 | 小 |
| 结构化 LLM token 传参 | `detail.llm` 已落地并兼容旧格式 | 扩展 RAG/Tool 类型 schema | 小 |
| 任务取消真正停止 | 协作式取消及终态事件已落地 | 底层同步 HTTP 强制 abort | 中 |
| 前端状态机 | CANCELED、终态断连已落地 | 细化连接超时文案 | 小 |
| run_manifest 作为权威汇总 | Token、耗时、状态已接入前端 | 补 CitationMap 汇总与成本 | 小 |
| 价格表 + 成本核算 | 无 | 配置价格表 + 运行完成时自动计算 | 小 |
| 三端一致 (浏览器/CLI/历史) | 三端读不同数据源 | 统一 EventLog → 三端读同一源 | 中 |

---

## 五、核心原则

1. **事件是事实，不是 UI 事件**：`trace.record()` 记录的是"系统做了一件什么事"，前端自己决定怎么展示。不要在后端写"这个事件显示什么颜色"。

2. **持久优先于实时**：先落盘，再推送。EventLog 是源，SSE 是视图。服务重启后从 EventLog 恢复，而不是从 SSE 队列。

3. **run_manifest 是权威账本**：任何汇总数字（token、耗时、产物列表）都以 manifest 为准。前端实时数字是"预览"，最终以 manifest 覆盖。

4. **auth 在入口一次性解决**：不要在每个事件通道都重新发明鉴权机制。短期用 URL token，中期用 fetch stream，长期如果切 cookie auth 则自然解决。

5. **同一套事件、同一个 adaptEvents、同样的渲染**：无论是 live SSE 还是历史查询，事件格式完全一致，前端代码完全复用。
