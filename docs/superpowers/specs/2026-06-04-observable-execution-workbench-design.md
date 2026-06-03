# 可观测执行工作台 — 架构设计文档

> 日期: 2026-06-04  
> 状态: 待审阅  
> 样板模块: CPRA  
> Phase 1 范围: 全栈打通（内部视图）, SSE 实时推送, 前端四段式工作台

---

## 一、目标

把前端 `Copilot/工作区` 从"只能看最终结果和静态中间产物"升级成"运行中可实时观察、运行后可直接汇报"的可观测执行工作台。

### 1.1 Phase 1 具体目标

1. 运行中实时看到系统在执行什么（当前步骤、工具调用、中间结果、成功/失败/阻塞）
2. 运行中看收敛后的"思路摘要"（不暴露 raw CoT）
3. 运行结束后自动给出内部执行简报
4. 前端扩为四段式：对话 + 执行流 + 中间结果 + 结果简报

### 1.2 Phase 1 明确不做

- 客户视图（Phase 2）
- WebSocket 实时推送（Phase 2）
- CPRA 以外的模块接入（Phase 2+）
- 人工标注 thought 摘要（Phase 1 用自动摘要）

---

## 二、架构总览

```
┌─────────────────────────────────────────────────────────┐
│                      前端（四段式）                       │
│  ┌──────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ 对话  │ │  执行流   │ │ 中间结果  │ │ 结果简报  │      │
│  │(现有) │ │ (新增)    │ │(通用化)   │ │ (新增)    │      │
│  └──────┘ └──────────┘ └──────────┘ └──────────┘      │
│       ▲         ▲ SSE          ▲            ▲           │
│       │         │ (主通道)       │            │           │
│       │         │ GET /task/{id}/stream                │
│       │         │ fallback: GET /task/{id}/events       │
├───────┼─────────┼──────────────┼────────────┼──────────┤
│       │         │     后端事件基础设施                    │
│  ┌────┴─────────┴──────────────┴────────────┴──────┐   │
│  │              TraceRecorder（扩展）                  │   │
│  │  record() → 写 JSON 文件 + push 到订阅者队列       │   │
│  └──────────────────────┬───────────────────────────┘   │
│                         │                               │
│  ┌──────────────────────┴───────────────────────────┐   │
│  │              SSEManager                           │   │
│  │  管理 SSE 连接，消费事件推前端                        │   │
│  └──────────────────────┬───────────────────────────┘   │
│                         │                               │
│  ┌──────────────────────┴───────────────────────────┐   │
│  │          CPRAService.generate_report()            │   │
│  │  关键节点调用 stream.record()                        │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 2.1 三层结构

| 层 | 职责 | 改什么 |
|----|------|--------|
| ① 运行时事件层 | 统一事件模型、流式发布、SSE 推送、TraceRecorder 扩展 | 扩 `backend/common/trace/`, 新增 SSE endpoint |
| ② 结构化中间结果层 | 各模块继续输出 facts/issues/gap_items/evidence_chain 等 | CPRA schema 补中间结果字段 |
| ③ 最终摘要层 | 基于事件 + 中间结果生成 internal_summary | 扩 `TraceManifest.audit_summary()` |

---

## 三、事件模型 — RunEvent

### 3.1 事件类型

```python
EventType = Literal[
    "status",          # 任务状态变化
    "thought",         # 思路摘要（收敛后）
    "tool_start",      # 开始工具/Agent/检索/规则引擎
    "tool_result",     # 工具返回结果
    "intermediate",    # 中间结构化结果
    "warning",         # 警告/阻塞/需补充材料
    "final",           # 最终结果
    "final_brief",     # 摘要（Phase 1: internal_summary）
]
```

### 3.2 事件结构

```python
class RunEvent(BaseModel):
    event_id: str              # uuid
    task_id: str               # 所属任务
    seq: int                   # 自增序号（前端判重排序）
    event_type: EventType
    timestamp: str             # ISO 8601
    
    # 一行中文摘要（必填，前端 timeline 主文本）
    summary: str               # 如 "开始法规检索：CPRA §1798.100"
    
    # 可选结构化详情
    detail: dict | None        # 按 event_type 约束
    
    # 双层
    level: Literal["audit", "debug"]  # audit 前端展示，debug 仅 trace 文件
```

### 3.3 detail 按类型约束

| event_type | detail 内容 |
|------------|------------|
| status | `{"from": "RUNNING", "to": "COMPLETED"}` |
| thought | `{"reasoning": "...", "model": "claude-opus-4-8"}` |
| tool_start | `{"tool": "CPRAAttachmentExtractor", "input_summary": "..."}`  |
| tool_result | `{"tool": "...", "duration_ms": 1200, "output_summary": "..."}`  |
| intermediate | `{"category": "facts", "count": 12, "data": [...]}` |
| warning | `{"severity": "block", "message": "缺少隐私政策附件"}` |
| final | `{"output_files": [...], "total_duration_ms": 45000}` |
| final_brief | `{"conclusion": "...", "files": [...], "risks": [...], "next_steps": [...]}` |

### 3.4 与现有 TraceEvent 的关系

扩展现有 `backend/common/workflow/trace.py:TraceEvent`：
- 新增 `RunEvent` 作为前端消费的事件模型（在 `backend/common/trace/events.py`）
- `TraceRecorder.record()` 扩展为同时写文件 AND 发布 `RunEvent` 给订阅者
- `TraceEvent` 保留不变，继续用于事后审计文件的写入

---

## 四、TraceRecorder 扩展

### 4.1 改动点

文件: `backend/common/trace/recorder.py`

```python
class TraceRecorder:
    def __init__(self, trace_dir: Path) -> None:
        self.trace_dir = trace_dir
        self._seq = 0
        self._events: list[TraceEvent] = []
        self._subscribers: list[Callable[[RunEvent], None]] = []  # 新增

    def record(self, name: str, payload: dict[str, Any]) -> Path:
        # 1. 原有文件写入逻辑（不变）
        self._seq += 1
        filename = f"{self._seq:03d}_{safe_name}.json"
        path = self.trace_dir / filename
        path.write_text(json.dumps({...}, ...))
        self._events.append(TraceEvent(...))
        
        # 2. 新增：发布 RunEvent 给订阅者
        run_event = RunEvent(
            event_id=str(uuid4()),
            seq=self._seq,
            event_type=self._infer_event_type(name),
            timestamp=_utc_now_iso(),
            summary=payload.get("summary", name),
            detail=payload.get("detail"),
            level=payload.get("level", "audit"),
        )
        for sub in self._subscribers:
            try:
                sub(run_event)
            except Exception:
                pass  # 订阅者异常不影响主流程
        
        return path

    def subscribe(self, callback: Callable[[RunEvent], None]) -> None:
        self._subscribers.append(callback)
```

### 4.2 name → event_type 映射表

```python
# recorder.py 内部映射
_EVENT_TYPE_MAP: dict[str, EventType] = {
    "status": "status",
    "thought": "thought",
    "tool_start": "tool_start",
    "tool_result": "tool_result",
    "intermediate": "intermediate",
    "warning": "warning",
    "final": "final",
    "final_brief": "final_brief",
    # 向后兼容现存调用点
    "assessment_request": "status",
    "profile_extracted": "intermediate",
    "diagnosis": "thought",
    "path_validation": "warning",
    "fact_extraction": "tool_start",
    "fact_built": "intermediate",
    "regulation_retrieval": "tool_start",
    "rag_hit": "tool_result",
    "issue_built": "intermediate",
    "evidence_built": "intermediate",
    "writing_plan": "thought",
    "report_generation": "tool_result",
    "qa_check": "tool_result",
    "consistency_check": "tool_result",
    "repair": "warning",
    "render": "tool_result",
}
```

### 4.3 design principles

- **文件写入必须成功**（审计需要），SSE 推送 best-effort（订阅者异常不影响主流程）
- 所有现存 `trace.record("xxx", ...)` 调用无需修改，`_infer_event_type()` 通过上表映射
- `task_id` 在 `submit()` 时由 `InMemoryTaskManager` 注入 `TraceRecorder`。

### 4.4 task_id 传递链路

```
前端 POST /api/cpra/run → 后端创建 task
  └── InMemoryTaskManager.submit(runner, task_id)
        ├── 创建 TraceRecorder(trace_dir, task_id=task_id)
        ├── TraceRecorder._task_id = task_id           ← RunEvent.task_id 来源
        ├── contextvar current_trace → 指向此 TraceRecorder
        ├── CPRAService.generate_report() 内 trace = current_trace.get()
        │     └── trace.record("tool_start", ...) → RunEvent.task_id 自动填入
        └── SSEManager 按 task_id 路由事件到对应 SSE 队列
```

---

## 五、SSE 传输

### 5.1 SSE Endpoint

新增文件: `backend/api/events.py`

```python
@router.get("/task/{task_id}/stream")
async def task_event_stream(task_id: str, request: Request):
    """SSE 实时推送"""
    async def event_generator():
        queue: asyncio.Queue[RunEvent] = asyncio.Queue()
        ssemanager.subscribe(task_id, queue)
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {event.model_dump_json()}\n\n"
                except asyncio.TimeoutError:
                    yield f": heartbeat\n\n"
        finally:
            ssemanager.unsubscribe(task_id, queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

### 5.2 轮询 Fallback

```python
@router.get("/task/{task_id}/events")
async def task_events_since(task_id: str, since: int = 0):
    """轮询：拉取 seq > since 的事件"""
    events = ssemanager.get_events_since(task_id, since)
    return {"events": events, "latest_seq": events[-1].seq if events else since}
```

### 5.3 SSEManager

新增文件: `backend/common/events/manager.py`

```python
class SSEManager:
    """管理 SSE 订阅和事件分发。内存队列，task 完成后 30min 自动清理。"""
    
    def __init__(self):
        self._task_events: dict[str, list[RunEvent]] = {}       # task_id → 完整事件列表
        self._task_queues: dict[str, list[asyncio.Queue]] = {}  # task_id → 活跃 SSE 队列
        self._completed_at: dict[str, float] = {}                # task_id → 完成时间戳
    
    def subscribe(self, task_id: str, queue: asyncio.Queue):
        if task_id not in self._task_queues:
            self._task_queues[task_id] = []
        self._task_queues[task_id].append(queue)
        # 回放已有事件
        for event in self._task_events.get(task_id, []):
            queue.put_nowait(event)
    
    def unsubscribe(self, task_id: str, queue: asyncio.Queue):
        if task_id in self._task_queues:
            self._task_queues[task_id].remove(queue)
    
    def publish(self, task_id: str, event: RunEvent):
        if task_id not in self._task_events:
            self._task_events[task_id] = []
        self._task_events[task_id].append(event)
        # 完成事件到达时记录时间戳
        if event.event_type == "final_brief":
            self._completed_at[task_id] = time.time()
        for queue in self._task_queues.get(task_id, []):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass
    
    def get_events_since(self, task_id: str, since: int) -> list[RunEvent]:
        return [e for e in self._task_events.get(task_id, []) if e.seq > since]
    
    def cleanup_expired(self, ttl_seconds: int = 1800):
        """清理已完成超过 ttl 的 task 事件（后台定时调用）"""
        now = time.time()
        expired = [tid for tid, ts in self._completed_at.items() if now - ts > ttl_seconds]
        for tid in expired:
            self._task_events.pop(tid, None)
            self._task_queues.pop(tid, None)
            self._completed_at.pop(tid, None)
```

### 5.4 InMemoryTaskManager 集成

在 `backend/common/tasks/manager.py` 中：
- `submit()` → 创建 `TraceRecorder`，将 `SSEManager` 实例注册为订阅者
- `TraceRecorder` 通过 `ContextVar` 传递给 runner 中的 service 代码
- `TaskSnapshot` 新增 `has_stream: bool` 字段
- `_execute()` 完成/失败后通知 SSEManager（publish status 事件）

---

## 六、CPRA Service 接入

### 6.1 现有链路

```
generate_report(payload)
  ├── attachment extraction → fact_packs
  ├── fact_extraction agent ───→ merged_facts
  ├── legal_retriever.search() → regulation_hits
  ├── gap_rules.run_all_rules() → gap_items
  ├── consistency_review agent → consistency_issues
  ├── spi_sharing_risk agent → spi_risks
  ├── vendor_contract agent → vendor_issues
  ├── chapter generation (6 chapters)
  └── render → docx/pdf/xlsx
```

### 6.2 补事件的关键节点

```python
def generate_report(self, payload: CPRARequest) -> CPRAResult:
    trace = current_trace.get()  # contextvar
    
    trace.record("status", {
        "summary": "开始 CPRA 合规诊断",
        "detail": {"module": "cpra", "company": payload.company_name},
    })
    
    trace.record("thought", {
        "summary": "路径判断：基于企业规模和数据处理范围确定 CPRA 适用条款",
        "detail": {"reasoning": self._summarize_reasoning(diagnosis_reasoning)},
    })
    
    # 附件提取
    trace.record("tool_start", {"summary": "附件事实提取器", "detail": {"tool": "CPRAAttachmentExtractor"}})
    for att in payload.attachments:
        raw_facts = self.extractor.extract(att)
    trace.record("tool_result", {
        "summary": f"提取到 {len(raw_facts)} 条原始事实",
        "detail": {"count": len(raw_facts)},
    })
    
    # 事实构建
    trace.record("tool_start", {"summary": "事实提取 Agent", "detail": {"agent": "fact_extraction"}})
    fact_packs = [...]
    trace.record("intermediate", {
        "summary": f"结构化事实：{len(fact_packs)} 条",
        "detail": {"category": "facts", "data": [f.model_dump() for f in fact_packs]},
    })
    
    # 法规检索
    trace.record("tool_start", {"summary": "CPRA 法规检索"})
    reg_hits = self.legal_retriever.search(...)
    trace.record("tool_result", {
        "summary": f"命中 {len(reg_hits)} 条法规",
        "detail": {"hit_count": len(reg_hits)} if reg_hits else {},
    })
    
    # 差距分析
    trace.record("tool_start", {"summary": "差距分析规则引擎", "detail": {"tool": "CPRA Gap Rules"}})
    gap_items = run_all_rules(...)
    trace.record("intermediate", {
        "summary": f"差距项：{len(gap_items)} 个",
        "detail": {"category": "gap_items", "data": [g.model_dump() for g in gap_items]},
    })
    
    # 一致性审查
    trace.record("tool_start", {"summary": "一致性审查 Agent", "detail": {"agent": "consistency_review"}})
    consistency = self.agents["consistency_review"].run(...)
    trace.record("tool_result", {
        "summary": f"发现 {len(consistency.issues)} 个一致性问题",
        "detail": {"issues": consistency.issues},
    })
    
    # SPI 风险
    trace.record("tool_start", {"summary": "敏感信息共享风险评估", "detail": {"agent": "spi_sharing_risk"}})
    # ...
    
    # 供应商合规
    trace.record("tool_start", {"summary": "供应商合同合规", "detail": {"agent": "vendor_contract"}})
    # ...
    
    # 最终结果
    trace.record("final", {
        "summary": f"CPRA 合规诊断完成",
        "detail": {
            "output_files": result.output_files,
            "total_duration_ms": total_ms,
            "risk_distribution": {"high": 4, "medium": 7, "low": 3},
        },
    })
    
    # 摘要
    trace.record("final_brief", {
        "summary": _generate_internal_summary(result, timings),
    })
    
    return result
```

### 6.3 自动摘要

thought 事件的 summary 生成逻辑：

```python
def _summarize_agent_reasoning(self, raw_output: str, agent_name: str) -> str:
    """用轻量 prompt 把 Agent raw reasoning 收敛为一句话"""
    prompt = f"""将以下 {agent_name} 的推理过程总结为一句中文（不超过40字），只描述做了什么判断，不暴露内部思考细节：

{raw_output[:2000]}

一句话总结："""
    summary = self.llm_client.complete(prompt, max_tokens=60)
    return summary.strip()
```

### 6.4 内部摘要生成

```python
def _generate_internal_summary(result: CPRAResult, timings: list, events: list) -> dict:
    return {
        "conclusion": f"CPRA 合规诊断完成，识别 {result.high_risk_count} 项高风险、{result.medium_risk_count} 项中风险",
        "files": result.output_files,
        "risks": [
            {"severity": "high", "count": result.high_risk_count, "top_items": [...]},
            {"severity": "medium", "count": result.medium_risk_count, "top_items": [...]},
        ],
        "next_steps": [
            "优先处理高风险差距项",
            "补充缺失的隐私政策附件",
            "核验一致性审查中发现的问题",
        ],
        "stats": {
            "total_duration_ms": sum(t[1] for t in timings),
            "llm_calls": count_agent_calls(events),
            "output_files_count": len(result.output_files),
        },
    }
```

---

## 七、前端改造

### 7.1 组件结构

```
WorkspaceShell (改造)
├── TabBar: [💬 对话 | 📋 执行流 | 📊 中间结果 | 📝 结果简报]
├── AssistantPanel (现有, tab="chat" 时渲染)
├── ExecutionTimeline (新增, tab="timeline")
├── IntermediatesPanel (通用化现有 AssessmentIntermediatesPanel)
└── RunBrief (新增, tab="brief")
```

### 7.2 ExecutionTimeline（核心新组件）

文件: `frontend/src/components/workspace/ExecutionTimeline.tsx`

```tsx
interface ExecutionTimelineProps {
  taskId: string;
}

function ExecutionTimeline({ taskId }: ExecutionTimelineProps) {
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const es = new EventSource(`/api/task/${taskId}/stream`);

    es.onopen = () => setConnected(true);

    es.onmessage = (e) => {
      if (e.data.startsWith(":")) return; // heartbeat
      const event = JSON.parse(e.data) as RunEvent;
      setEvents(prev => [...prev, event]);
    };

    es.onerror = () => {
      setConnected(false);
      es.close();
      startPolling(taskId, events.length, setEvents, setConnected);
    };

    return () => es.close();
  }, [taskId]);

  return (
    <div className="execution-timeline">
      <div className="timeline-header">
        <StatusDot connected={connected} />
        {connected ? "实时连接" : "轮询中"}
      </div>
      <div className="timeline-body">
        {events.map(e => (
          <TimelineRow key={e.seq} event={e} />
        ))}
      </div>
    </div>
  );
}
```

### 7.3 TimelineRow 渲染策略

```tsx
function TimelineRow({ event }: { event: RunEvent }) {
  const icon = ICON_MAP[event.event_type]; // 💭🔧✅📊⚠️🏁📝
  const color = COLOR_MAP[event.event_type];

  return (
    <div className={`timeline-row ${color}`}>
      <div className="timeline-icon">{icon}</div>
      <div className="timeline-content">
        <div className="timeline-summary">{event.summary}</div>
        <div className="timeline-time">{formatTime(event.timestamp)}</div>
        {event.detail && (
          <details>
            <summary>详情</summary>
            <pre>{JSON.stringify(event.detail, null, 2)}</pre>
          </details>
        )}
      </div>
    </div>
  );
}
```

### 7.4 IntermediatesPanel（通用化）

扩展现有 `AssessmentIntermediatesPanel.tsx`：

```tsx
function IntermediatesPanel({ taskId }: { taskId: string }) {
  const [intermediates, setIntermediates] = useState<IntermediateSnapshot[]>([]);

  // 同样消费 SSE，筛选 event_type="intermediate"
  useEffect(() => {
    const es = new EventSource(`/api/task/${taskId}/stream`);
    es.onmessage = (e) => {
      const event = JSON.parse(e.data) as RunEvent;
      if (event.event_type === "intermediate") {
        setIntermediates(prev => [...prev, event.detail as IntermediateSnapshot]);
      }
    };
    return () => es.close();
  }, [taskId]);

  return (
    <div className="intermediates-panel">
      {intermediates.map((item, i) => (
        <IntermediateSection key={i} category={item.category} data={item.data} />
      ))}
    </div>
  );
}
```

### 7.5 RunBrief（新增）

```tsx
function RunBrief({ taskId }: { taskId: string }) {
  const [brief, setBrief] = useState<InternalBrief | null>(null);

  useEffect(() => {
    const es = new EventSource(`/api/task/${taskId}/stream`);
    es.onmessage = (e) => {
      const event = JSON.parse(e.data) as RunEvent;
      if (event.event_type === "final_brief") {
        setBrief(event.detail as InternalBrief);
      }
    };
    return () => es.close();
  }, [taskId]);

  if (!brief) return <div className="brief-loading">等待执行完成...</div>;

  return (
    <div className="run-brief">
      <section className="brief-conclusion">
        <h3>执行结论</h3>
        <p>{brief.conclusion}</p>
      </section>
      <section className="brief-files">
        <h3>生成文件</h3>
        <ul>{brief.files.map(f => <li key={f}>{f}</li>)}</ul>
      </section>
      <section className="brief-risks">
        <h3>风险提示</h3>
        {brief.risks.map(r => (
          <div className={`risk-badge risk-${r.severity}`}>
            {r.severity}: {r.count} 项
          </div>
        ))}
      </section>
      <section className="brief-next">
        <h3>建议下一步</h3>
        <ol>{brief.next_steps.map(s => <li key={s}>{s}</li>)}</ol>
      </section>
    </div>
  );
}
```

### 7.6 SSE → 轮询降级逻辑（共享连接）

为避免四个面板各自开 SSE 连接，前端用一个共享 hook：

```tsx
// frontend/src/lib/useTaskEvents.ts — 全局共享 SSE hook
function useTaskEvents(taskId: string): RunEvent[] {
  // 单例：同一 taskId 全局共享一个 EventSource
  const [events, setEvents] = useState<RunEvent[]>([]);
  // ... SSE 连接逻辑同上
  return events;
}

// ExecutionTimeline 消费全量事件
// IntermediatesPanel 过滤 event_type="intermediate"
// RunBrief 过滤 event_type="final_brief"
// 三个组件调用同一个 useTaskEvents(taskId)，底层共享 EventSource
```

降级轮询实现：

```tsx
function startPolling(
  taskId: string,
  currentSeq: number,
  setEvents: Dispatch<SetStateAction<RunEvent[]>>,
  setConnected: Dispatch<SetStateAction<boolean>>,
) {
  const interval = setInterval(async () => {
    try {
      const res = await fetch(`/api/task/${taskId}/events?since=${currentSeq}`);
      const data = await res.json();
      if (data.events.length > 0) {
        setEvents(prev => [...prev, ...data.events]);
        currentSeq = data.latest_seq;
      }
      setConnected(true);
    } catch {
      setConnected(false);
    }
  }, 1500);

  // 30s 后尝试恢复 SSE
  setTimeout(() => {
    clearInterval(interval);
    // 重新走 SSE 连接
  }, 30000);

  return () => clearInterval(interval);
}
```

---

## 八、文件清单

### 8.1 新增文件

| 文件 | 职责 |
|------|------|
| `backend/common/trace/events.py` | RunEvent 模型定义 |
| `backend/common/events/__init__.py` | events 包 |
| `backend/common/events/manager.py` | SSEManager |
| `backend/api/events.py` | SSE endpoint + 轮询 endpoint |
| `frontend/src/components/workspace/ExecutionTimeline.tsx` | 执行流组件 |
| `frontend/src/components/workspace/RunBrief.tsx` | 结果简报组件 |

### 8.2 修改文件

| 文件 | 改动 |
|------|------|
| `backend/common/trace/recorder.py` | 扩展 record() 支持事件发布 |
| `backend/common/trace/context.py` | 新增 SSEManager contextvar |
| `backend/common/tasks/manager.py` | 集成 SSEManager |
| `backend/modules/cpra/service.py` | 关键节点补 stream.record() |
| `backend/modules/cpra/schema.py` | 补中间结果字段（如需要） |
| `frontend/src/components/workspace/WorkspaceShell.tsx` | 加 TabBar + 四个面板切换 |
| `frontend/src/components/workspace/AssessmentIntermediatesPanel.tsx` | 通用化为 IntermediatesPanel |
| `backend/api/router.py` | 注册 events router |

---

## 九、实施顺序

```
Step 1: 后端事件基础设施
  ├── RunEvent 模型 (events.py)
  ├── TraceRecorder 扩展 (recorder.py)
  ├── SSEManager (manager.py)
  ├── SSE endpoint (api/events.py)
  └── 单元测试

Step 2: CPRA service 接入
  ├── 关键节点补 stream.record()
  ├── 自动摘要 prompt
  ├── internal_summary 生成
  └── 集成测试

Step 3: 前端四段改造
  ├── ExecutionTimeline（SSE 消费 + 轮询降级）
  ├── IntermediatesPanel 通用化
  ├── RunBrief
  ├── WorkspaceShell TabBar
  └── 端到端测试
```

---

## 十、验证标准

### Step 1 验证
- [ ] `RunEvent` 模型可序列化/反序列化
- [ ] `TraceRecorder.record()` 同时写文件和推送事件
- [ ] `GET /task/{id}/stream` 返回正确的 SSE 格式
- [ ] `GET /task/{id}/events?since=X` 返回增量事件
- [ ] 订阅者异常不影响主流程

### Step 2 验证
- [ ] CPRA 运行产生完整事件流（至少 8 种事件类型各一条）
- [ ] thought 事件不包含原始 prompt 内容
- [ ] intermediate 事件 detail 包含结构化 CPRAFact 数据
- [ ] final_brief 包含 conclusion/files/risks/next_steps 四项
- [ ] 现有 CPRA 测试全部通过

### Step 3 验证
- [ ] 前端四段式 tab 可切换
- [ ] ExecutionTimeline 实时显示新事件
- [ ] SSE 断开时自动降级到轮询
- [ ] IntermediatesPanel 展示 CPRA facts/gap_items
- [ ] RunBrief 在 final_brief 事件到达后自动渲染
- [ ] 页面刷新后可通过轮询恢复事件列表
