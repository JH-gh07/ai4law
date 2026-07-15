# 可观测执行工作台 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将前端 Copilot/工作区从"只能看最终结果"升级为"运行中实时可观察 + 运行后可直接汇报"的可观测执行工作台，CPRA 样板全栈打通过。

**Architecture:** 后端扩展 TraceRecorder 使其 record() 同时写文件和推 SSE 事件；新增 SSEManager 管理事件分发和 SSE 连接；前端新增 ExecutionTimeline/RunBrief 组件 + 通用化 IntermediatesPanel，在 WorkspaceShell 中做四段 tab 切换。

**Tech Stack:** Python 3.11+ / FastAPI / Pydantic v2 / asyncio / React 18+ / TypeScript / EventSource (SSE)

---

## 文件映射

### 新增
| 文件 | 职责 |
|------|------|
| `backend/common/trace/events.py` | RunEvent 模型 |
| `backend/common/events/__init__.py` | events 包初始化 |
| `backend/common/events/manager.py` | SSEManager 事件分发 |
| `backend/api/events.py` | SSE + 轮询 endpoint |
| `frontend/src/lib/useTaskEvents.ts` | 共享 SSE hook |
| `frontend/src/components/workspace/ExecutionTimeline.tsx` | 执行流组件 |
| `frontend/src/components/workspace/RunBrief.tsx` | 结果简报组件 |

### 修改
| 文件 | 改动 |
|------|------|
| `backend/common/trace/recorder.py` | 扩展 record() 支持订阅者推送 |
| `backend/common/trace/context.py` | 新增 ssemanager contextvar |
| `backend/common/tasks/manager.py` | 集成 SSEManager |
| `backend/api/router.py` | 注册 events router |
| `backend/modules/cpra/service.py` | 关键节点补 trace.record() |
| `frontend/src/components/workspace/WorkspaceShell.tsx` | 四段 tab 切换 |
| `frontend/src/components/workspace/AssessmentIntermediatesPanel.tsx` | 通用化为 IntermediatesPanel |

---

### Task 1: RunEvent 模型定义

**Files:**
- Create: `backend/common/trace/events.py`
- Create: `backend/common/trace/tests/test_events.py`

- [ ] **Step 1: 编写 RunEvent 模型**

```python
# backend/common/trace/events.py
"""RunEvent — 前端消费的运行时事件模型，与 TraceEvent（审计文件）并行。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

EventType = Literal[
    "status",
    "thought",
    "tool_start",
    "tool_result",
    "intermediate",
    "warning",
    "final",
    "final_brief",
]

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class RunEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str = ""
    seq: int = 0
    event_type: EventType
    timestamp: str = Field(default_factory=_utc_now_iso)
    summary: str = ""
    detail: dict[str, Any] | None = None
    level: Literal["audit", "debug"] = "audit"
```

- [ ] **Step 2: 编写测试验证序列化/反序列化**

```python
# backend/common/trace/tests/test_events.py
import json
from backend.common.trace.events import RunEvent

def test_run_event_serialize():
    event = RunEvent(
        task_id="test-task-1",
        seq=1,
        event_type="tool_start",
        summary="开始法规检索",
        detail={"tool": "CPRALegalRetriever", "query": "CPRA §1798.100"},
    )
    data = event.model_dump()
    assert data["event_type"] == "tool_start"
    assert data["summary"] == "开始法规检索"
    assert data["detail"]["tool"] == "CPRALegalRetriever"

def test_run_event_deserialize():
    raw = '{"event_type":"thought","summary":"路径判断完成","task_id":"t1","seq":5}'
    event = RunEvent.model_validate_json(raw)
    assert event.event_type == "thought"
    assert event.summary == "路径判断完成"

def test_run_event_json_serializable():
    event = RunEvent(task_id="t2", seq=1, event_type="status", summary="开始执行")
    text = event.model_dump_json()
    parsed = json.loads(text)
    assert parsed["event_type"] == "status"

def test_all_event_types():
    valid_types = {"status","thought","tool_start","tool_result","intermediate","warning","final","final_brief"}
    for et in valid_types:
        event = RunEvent(task_id="t", seq=0, event_type=et, summary=et)
        assert event.event_type == et
```

- [ ] **Step 3: Run tests**

```bash
cd /Users/oujiazhan/Desktop/实验室/社团/代码/ai4law && python -m pytest backend/common/trace/tests/test_events.py -v
```

- [ ] **Step 4: Commit**

```bash
git add backend/common/trace/events.py backend/common/trace/tests/test_events.py
git commit -m "feat(events): add RunEvent model for frontend-consumable event stream

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: name → event_type 映射表

**Files:**
- Modify: `backend/common/trace/recorder.py`

- [ ] **Step 1: 添加映射表到 recorder.py**

在 [recorder.py](backend/common/trace/recorder.py) 文件顶部添加：

```python
# 在现有 import 之后，TraceEvent dataclass 之前添加

# ── name → event_type 映射 ──────────────────────────────────────────────
_NAME_TO_EVENT_TYPE: dict[str, str] = {
    # 新事件类型（直接映射）
    "status": "status",
    "thought": "thought",
    "tool_start": "tool_start",
    "tool_result": "tool_result",
    "intermediate": "intermediate",
    "warning": "warning",
    "final": "final",
    "final_brief": "final_brief",
    # 向后兼容 — 现有 trace.record() 调用点
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
    # CPRA 特有
    "attachment_extraction_and_fact_agents": "tool_result",
    "fact_merge": "tool_result",
    "rule_engine": "tool_result",
    "legacy_fallback": "warning",
    "spi_review": "tool_result",
    "vendor_review": "tool_result",
    "attach_gap_citations": "tool_result",
    "resolve_rating": "tool_result",
    "attachment_notes": "tool_result",
    "build_context": "tool_result",
    "generate_chapters": "tool_result",
    "consistency_review": "tool_result",
}
```

- [ ] **Step 2: Commit**

```bash
git add backend/common/trace/recorder.py
git commit -m "feat(trace): add name-to-event-type mapping table for backward compat

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: TraceRecorder 扩展 — 订阅者机制

**Files:**
- Modify: `backend/common/trace/recorder.py`

- [ ] **Step 1: 扩展 TraceRecorder，增加订阅者支持和 RunEvent 发布**

编辑 [recorder.py](backend/common/trace/recorder.py)，修改 `TraceRecorder` 类：

```python
# 在现有 import 中添加
from typing import Callable

# 将 TraceRecorder.__init__ 改为：
def __init__(self, trace_dir: Path, task_id: str = "") -> None:
    self.trace_dir = trace_dir
    self.trace_dir.mkdir(parents=True, exist_ok=True)
    self._seq = 0
    self._events: list[TraceEvent] = []
    self._subscribers: list[Callable] = []  # Callable[[RunEvent], None]
    self._task_id = task_id

# 在 record() 方法中，return path 之前插入 RunEvent 发布逻辑：
def record(self, name: str, payload: dict[str, Any]) -> Path:
    self._seq += 1
    safe_name = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in (name or "event")).strip("_")
    filename = f"{self._seq:03d}_{safe_name}.json"
    path = self.trace_dir / filename
    to_write = {"name": name, "seq": self._seq, "created_at": _utc_now_iso(), "payload": payload}
    path.write_text(json.dumps(to_write, ensure_ascii=False, indent=2), encoding="utf-8")
    self._events.append(TraceEvent(seq=self._seq, name=name, path=str(path), created_at=to_write["created_at"]))

    # ── 新增：发布 RunEvent 给订阅者 ──
    if self._subscribers:
        from backend.common.trace.events import RunEvent
        event_type = _NAME_TO_EVENT_TYPE.get(name, "status")
        run_event = RunEvent(
            task_id=self._task_id,
            seq=self._seq,
            event_type=event_type,
            timestamp=to_write["created_at"],
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

# 新增方法：
def subscribe(self, callback: Callable) -> None:
    """注册事件订阅者。callback 接收 RunEvent 实例。"""
    self._subscribers.append(callback)
```

- [ ] **Step 2: 编写测试验证双写行为**

```python
# backend/common/trace/tests/test_recorder_stream.py
import tempfile
from pathlib import Path
from backend.common.trace.recorder import TraceRecorder

def test_recorder_writes_file_and_pushes_event():
    received: list = []
    with tempfile.TemporaryDirectory() as tmpdir:
        recorder = TraceRecorder(trace_dir=Path(tmpdir), task_id="test-task")
        recorder.subscribe(lambda e: received.append(e))
        recorder.record("tool_start", {"summary": "测试工具", "detail": {"key": "val"}})
        recorder.record("tool_result", {"summary": "测试结果"})

    assert len(received) == 2
    assert received[0].event_type == "tool_start"
    assert received[0].task_id == "test-task"
    assert received[0].summary == "测试工具"
    assert received[0].detail == {"key": "val"}
    assert received[1].event_type == "tool_result"
    assert received[1].seq == 2

    # 验证文件也已写入
    trace_files = list(Path(tmpdir).glob("*.json"))
    assert len(trace_files) >= 2

def test_subscriber_exception_does_not_block_writing():
    received: list = []
    def bad_subscriber(event):
        if event.event_type == "tool_result":
            raise RuntimeError("boom")
        received.append(event)

    with tempfile.TemporaryDirectory() as tmpdir:
        recorder = TraceRecorder(trace_dir=Path(tmpdir), task_id="t")
        recorder.subscribe(bad_subscriber)
        recorder.record("tool_start", {"summary": "s1"})
        recorder.record("tool_result", {"summary": "s2"})
        recorder.record("tool_start", {"summary": "s3"})

    # bad_subscriber 在 tool_result 时抛异常，但后续事件仍正常
    assert len(received) == 2
    assert received[0].event_type == "tool_start"
    assert received[1].event_type == "tool_start"

def test_legacy_name_mapping():
    received: list = []
    with tempfile.TemporaryDirectory() as tmpdir:
        recorder = TraceRecorder(trace_dir=Path(tmpdir), task_id="t")
        recorder.subscribe(lambda e: received.append(e))
        recorder.record("diagnosis", {"summary": "路径判断"})
        recorder.record("profile_extracted", {"summary": "提取完成"})
        recorder.record("path_validation", {"summary": "路径警告"})

    assert received[0].event_type == "thought"
    assert received[1].event_type == "intermediate"
    assert received[2].event_type == "warning"
```

- [ ] **Step 3: Run tests**

```bash
cd /Users/oujiazhan/Desktop/实验室/社团/代码/ai4law && python -m pytest backend/common/trace/tests/test_recorder_stream.py -v
```

- [ ] **Step 4: Commit**

```bash
git add backend/common/trace/recorder.py backend/common/trace/tests/test_recorder_stream.py
git commit -m "feat(trace): extend TraceRecorder with subscriber mechanism for RunEvent push

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: SSEManager

**Files:**
- Create: `backend/common/events/__init__.py`
- Create: `backend/common/events/manager.py`

- [ ] **Step 1: 创建 events 包初始化文件**

```python
# backend/common/events/__init__.py
"""Runtime event stream infrastructure — SSEManager and related utilities."""
```

- [ ] **Step 2: 实现 SSEManager**

```python
# backend/common/events/manager.py
"""SSEManager — 管理 SSE 订阅连接和事件分发。"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from backend.common.trace.events import RunEvent


class SSEManager:
    """内存事件队列管理器。task 完成后 30min 自动清理。"""

    def __init__(self) -> None:
        self._task_events: dict[str, list[RunEvent]] = {}
        self._task_queues: dict[str, list[asyncio.Queue[RunEvent]]] = {}
        self._completed_at: dict[str, float] = {}

    def subscribe(self, task_id: str, queue: asyncio.Queue[RunEvent]) -> None:
        """注册 SSE 连接并回放历史事件。"""
        if task_id not in self._task_queues:
            self._task_queues[task_id] = []
        self._task_queues[task_id].append(queue)
        for event in self._task_events.get(task_id, []):
            queue.put_nowait(event)

    def unsubscribe(self, task_id: str, queue: asyncio.Queue[RunEvent]) -> None:
        if task_id in self._task_queues:
            try:
                self._task_queues[task_id].remove(queue)
            except ValueError:
                pass

    def publish(self, task_id: str, event: RunEvent) -> None:
        """推送事件到所有对应 task 的活跃 SSE 连接。"""
        if task_id not in self._task_events:
            self._task_events[task_id] = []
        self._task_events[task_id].append(event)
        if event.event_type in ("final", "final_brief"):
            self._completed_at[task_id] = time.time()
        for queue in self._task_queues.get(task_id, []):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def get_events_since(self, task_id: str, since: int) -> list[RunEvent]:
        """轮询用：返回 seq > since 的事件。"""
        return [e for e in self._task_events.get(task_id, []) if e.seq > since]

    def cleanup_expired(self, ttl_seconds: int = 1800) -> int:
        """清理已完成超过 ttl 的 task 事件数据。返回清理数量。"""
        now = time.time()
        expired = [tid for tid, ts in self._completed_at.items() if now - ts > ttl_seconds]
        for tid in expired:
            self._task_events.pop(tid, None)
            self._task_queues.pop(tid, None)
            self._completed_at.pop(tid, None)
        return len(expired)

    def on_event(self, event: RunEvent) -> None:
        """作为 TraceRecorder 订阅者的回调入口。"""
        if event.task_id:
            self.publish(event.task_id, event)


# 全局单例
_ssemanager: SSEManager | None = None


def get_ssemanager() -> SSEManager:
    global _ssemanager
    if _ssemanager is None:
        _ssemanager = SSEManager()
    return _ssemanager
```

- [ ] **Step 3: Commit**

```bash
git add backend/common/events/__init__.py backend/common/events/manager.py
git commit -m "feat(events): add SSEManager for SSE subscription and event distribution

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: context.py 扩展 — SSEManager contextvar

**Files:**
- Modify: `backend/common/trace/context.py`

- [ ] **Step 1: 添加 SSEManager contextvar**

编辑 [context.py](backend/common/trace/context.py)：

```python
from __future__ import annotations

from contextvars import ContextVar

from backend.common.trace.recorder import TraceRecorder

# 新增 import
from backend.common.events.manager import SSEManager


current_trace: ContextVar[TraceRecorder | None] = ContextVar("current_trace", default=None)

# 新增
current_ssemanager: ContextVar[SSEManager | None] = ContextVar("current_ssemanager", default=None)
```

- [ ] **Step 2: Commit**

```bash
git add backend/common/trace/context.py
git commit -m "feat(trace): add SSEManager contextvar for per-request event streaming

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: InMemoryTaskManager 集成 SSEManager

**Files:**
- Modify: `backend/common/tasks/manager.py`

- [ ] **Step 1: 在 submit() 中桥接 TraceRecorder → SSEManager**

编辑 [manager.py](backend/common/tasks/manager.py)，在 `submit()` 方法中：

```python
# 在 submit() 方法内，创建 TraceRecorder 后添加：
def submit(self, runner: Callable[[], Any], max_attempts: int = 2) -> TaskSnapshot:
    # ... 现有代码 ...
    self._executor.submit(self._execute, task_id)
    return self.get_or_raise(task_id)

# 新增带 trace 的 submit 方法：
def submit_with_trace(
    self,
    runner: Callable[[], Any],
    trace_recorder: Any,  # TraceRecorder
    max_attempts: int = 2,
) -> TaskSnapshot:
    """提交任务并绑定 TraceRecorder 用于事件推送。"""
    now = _utc_now_iso()
    task_id = str(uuid.uuid4())

    # 将 SSEManager 注册为 TraceRecorder 订阅者
    from backend.common.events.manager import get_ssemanager
    sm = get_ssemanager()
    trace_recorder.subscribe(sm.on_event)

    record = _TaskRecord(
        task_id=task_id,
        module=self.module,
        state="CREATED",
        attempts=0,
        max_attempts=max(1, max_attempts),
        created_at=now,
        updated_at=now,
        error=None,
        result=None,
        runner=runner,
    )
    # 包裹 runner：注入 TraceRecorder 到 contextvar
    def wrapped_runner():
        from backend.common.trace.context import current_trace
        token = current_trace.set(trace_recorder)
        try:
            return runner()
        finally:
            current_trace.reset(token)

    record = _TaskRecord(
        task_id=task_id,
        module=self.module,
        state="CREATED",
        attempts=0,
        max_attempts=max(1, max_attempts),
        created_at=now,
        updated_at=now,
        error=None,
        result=None,
        runner=wrapped_runner,
    )
    with self._lock:
        self._tasks[task_id] = record
    self._executor.submit(self._execute, task_id)

    # 发布 status 事件
    from backend.common.trace.events import RunEvent
    sm.publish(task_id, RunEvent(
        task_id=task_id,
        seq=0,
        event_type="status",
        summary=f"任务已创建 ({self.module})",
        detail={"module": self.module, "state": "CREATED"},
    ))

    return self.get_or_raise(task_id)
```

- [ ] **Step 2: _execute 中发布状态事件**

在 `_execute` 方法中补充：

```python
def _execute(self, task_id: str) -> None:
    # ... 现有 RUNNING 状态设置代码 ...
    
    # 新增：发布 RUNNING 状态事件
    from backend.common.events.manager import get_ssemanager
    from backend.common.trace.events import RunEvent
    sm = get_ssemanager()
    sm.publish(task_id, RunEvent(
        task_id=task_id,
        seq=-1,  # 状态事件不计入主序列
        event_type="status",
        summary=f"任务开始执行 ({self.module})",
        detail={"module": self.module, "state": "RUNNING"},
    ))

    try:
        result = record.runner()
        # ... 现有 COMPLETED 逻辑 ...
        # 新增：发布 COMPLETED 状态
        sm.publish(task_id, RunEvent(
            task_id=task_id,
            seq=-1,
            event_type="status",
            summary=f"任务执行完成 ({self.module})",
            detail={"module": self.module, "state": "COMPLETED"},
        ))
    except Exception as exc:
        # ... 现有 FAILED 逻辑 ...
        # 新增：发布 FAILED 状态
        sm.publish(task_id, RunEvent(
            task_id=task_id,
            seq=-1,
            event_type="status",
            summary=f"任务执行失败: {exc}",
            detail={"module": self.module, "state": "FAILED", "error": str(exc)},
        ))
```

- [ ] **Step 3: 更新 _snapshot_to_accepted 以包含 has_stream 信息**

CPRA service 的 `_snapshot_to_accepted` 需要知道此 task 是否有流。由于 CPRA schema 的 `CPRAAsyncAccepted` 需要检查，先不改 schema，在 SSE endpoint 里做判断即可。

- [ ] **Step 4: Commit**

```bash
git add backend/common/tasks/manager.py
git commit -m "feat(tasks): integrate SSEManager into InMemoryTaskManager for event publishing

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: SSE + 轮询 Endpoint

**Files:**
- Create: `backend/api/events.py`
- Modify: `backend/api/router.py`

- [ ] **Step 1: 实现 SSE 和轮询 endpoint**

```python
# backend/api/events.py
"""SSE 实时事件推送 + 轮询 fallback endpoint。"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from backend.common.events.manager import get_ssemanager
from backend.common.trace.events import RunEvent

logger = logging.getLogger(__name__)
router = APIRouter(tags=["events"])


@router.get("/task/{task_id}/stream")
async def task_event_stream(task_id: str, request: Request):
    """SSE 实时推送任务执行事件。"""

    async def event_generator():
        queue: asyncio.Queue[RunEvent] = asyncio.Queue(maxsize=256)
        sm = get_ssemanager()
        sm.subscribe(task_id, queue)
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {event.model_dump_json()}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            sm.unsubscribe(task_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/task/{task_id}/events")
async def task_events_since(task_id: str, since: int = Query(0, ge=0)):
    """轮询 fallback：拉取 seq > since 的增量事件。"""
    sm = get_ssemanager()
    events = sm.get_events_since(task_id, since)
    latest_seq = events[-1].seq if events else since
    return {
        "events": [e.model_dump() for e in events],
        "latest_seq": latest_seq,
    }
```

- [ ] **Step 2: 注册路由**

编辑 [router.py](backend/api/router.py)：

```python
from backend.api import events  # 新增

# 在 api_router 定义中新增一行：
api_router.include_router(events.router, prefix="/events", tags=["events"])
```

- [ ] **Step 3: Commit**

```bash
git add backend/api/events.py backend/api/router.py
git commit -m "feat(api): add SSE stream and polling endpoints for task events

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: 后端事件基础设施集成测试

**Files:**
- Create: `backend/api/tests/test_events_api.py`

- [ ] **Step 1: 编写集成测试**

```python
# backend/api/tests/test_events_api.py
import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from backend.common.events.manager import get_ssemanager
from backend.common.trace.events import RunEvent
from backend.main import app


@pytest.fixture(autouse=True)
def reset_ssemanager():
    """每个测试前重置全局 SSEManager。"""
    from backend.common.events.manager import _ssemanager as sm_ref
    import backend.common.events.manager as mod
    mod._ssemanager = None


def test_polling_returns_events_since():
    client = TestClient(app)
    sm = get_ssemanager()

    sm.publish("task-1", RunEvent(task_id="task-1", seq=1, event_type="status", summary="开始"))
    sm.publish("task-1", RunEvent(task_id="task-1", seq=2, event_type="thought", summary="路径判断"))

    resp = client.get("/api/v1/events/task/task-1/events?since=0")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["events"]) == 2
    assert data["events"][0]["event_type"] == "status"
    assert data["latest_seq"] == 2

    resp2 = client.get("/api/v1/events/task/task-1/events?since=1")
    data2 = resp2.json()
    assert len(data2["events"]) == 1
    assert data2["events"][0]["seq"] == 2


def test_polling_empty_when_no_events():
    client = TestClient(app)
    resp = client.get("/api/v1/events/task/nonexistent/events?since=0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["events"] == []
    assert data["latest_seq"] == 0
```

- [ ] **Step 2: Run tests**

```bash
cd /Users/oujiazhan/Desktop/实验室/社团/代码/ai4law && python -m pytest backend/api/tests/test_events_api.py -v
```

- [ ] **Step 3: Commit**

```bash
git add backend/api/tests/test_events_api.py
git commit -m "test(api): add integration tests for SSE polling endpoint

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: CPRA Service 接入 — 关键节点补 event

**Files:**
- Modify: `backend/modules/cpra/service.py`

- [ ] **Step 1: 在 generate_report() 的每个 mark() 前后补 trace.record()**

编辑 [service.py](backend/modules/cpra/service.py)，在现有 `generate_report` 方法中插入事件调用。关键改点：

```python
def generate_report(self, payload: CPRARequest) -> CPRAResult:
    timings: list[tuple[str, float]] = []
    t0 = time.perf_counter()

    def mark(stage: str) -> None:
        nonlocal t0
        now = time.perf_counter()
        timings.append((stage, now - t0))
        t0 = now

    # 从 contextvar 获取 trace
    from backend.common.trace.context import current_trace
    trace = current_trace.get()

    # ── 开始 ──
    trace.record("status", {"summary": "开始 CPRA 合规诊断", "detail": {"module": "cpra", "company": payload.company_name}})
    trace.record("thought", {"summary": "路径判断：基于企业规模和数据处理范围确定 CPRA 适用条款范围"})

    # ── Attachment extraction ──
    trace.record("tool_start", {"summary": "附件事实提取器", "detail": {"tool": "CPRAAttachmentExtractor"}})
    attachment_facts: list[dict] = []
    fact_packs = []
    for att in payload.attachments:
        raw_facts = self.extractor.extract(att)
        attachment_facts.append(raw_facts)
        fact_packs.append(
            self.agents["fact_extraction"].run(
                attachment=att,
                raw_facts=raw_facts,
                business_model=payload.business_model,
                data_lifecycle=payload.data_lifecycle,
            )
        )
    mark("attachment_extraction_and_fact_agents")
    trace.record("tool_result", {
        "summary": f"附件提取完成：{len(attachment_facts)} 个附件，{len(fact_packs)} 个事实包",
        "detail": {"attachment_count": len(attachment_facts), "fact_pack_count": len(fact_packs)},
    })

    # ── Fact merge ──
    trace.record("tool_start", {"summary": "事实合并器", "detail": {"tool": "CPRAFactMerger"}})
    enhanced_payload = self.fact_merger.merge(payload, fact_packs)
    mark("fact_merge")
    trace.record("intermediate", {
        "summary": f"事实合并完成",
        "detail": {"category": "facts", "data_item_count": len(enhanced_payload.data_items), "vendor_count": len(enhanced_payload.vendors)},
    })

    # ── Rule engine ──
    trace.record("tool_start", {"summary": "差距分析规则引擎", "detail": {"tool": "CPRA Gap Rules"}})
    gap_items = run_all_rules(...)
    mark("rule_engine")
    trace.record("intermediate", {
        "summary": f"差距分析完成：{len(gap_items)} 项差距",
        "detail": {
            "category": "gap_items",
            "data": [{"domain": g.domain, "risk_level": g.risk_level, "gap": g.gap} for g in gap_items],
        },
    })

    # ── Legacy fallback ──
    if not gap_items and enhanced_payload.applicability is None and not enhanced_payload.data_items:
        trace.record("warning", {"summary": "结构化输入缺失，启用回退规则"})
        gap_items = self._build_legacy_gap_items(enhanced_payload)
    mark("legacy_fallback")

    # ── SPI ──
    trace.record("tool_start", {"summary": "敏感信息共享风险评估", "detail": {"agent": "spi_sharing_risk"}})
    spi_review = self.agents["spi_sharing_risk"].run(...)
    gap_items = self.gap_merger.merge(gap_items, spi_review.gap_candidates)
    mark("spi_review")
    trace.record("tool_result", {
        "summary": f"SPI 风险评估完成：{len(spi_review.gap_candidates)} 个候选差距",
        "detail": {"spi_gap_count": len(spi_review.gap_candidates)},
    })

    # ── Vendor ──
    trace.record("tool_start", {"summary": "供应商合同合规审查", "detail": {"agent": "vendor_contract"}})
    vendor_review = self.agents["vendor_contract"].run(...)
    gap_items = self.gap_merger.merge(gap_items, vendor_review.contract_gaps)
    mark("vendor_review")
    trace.record("tool_result", {
        "summary": f"供应商审查完成：{len(vendor_review.contract_gaps)} 个合同差距",
        "detail": {"vendor_gap_count": len(vendor_review.contract_gaps)},
    })

    # ── RAG citations ──
    trace.record("tool_start", {"summary": "法规检索与引用匹配", "detail": {"tool": "CPRALegalRetriever"}})
    self._attach_gap_citations(gap_items)
    mark("attach_gap_citations")
    cited = sum(1 for g in gap_items if g.citations)
    trace.record("tool_result", {"summary": f"法规引用匹配完成：{cited} 项差距有法规引用"})

    # ── Rating ──
    risk_level = self._resolve_overall_level(gap_items)
    mark("resolve_rating")
    trace.record("intermediate", {
        "summary": f"综合风险评级：{risk_level}",
        "detail": {"category": "risk_level", "value": risk_level},
    })

    # ── Chapters ──
    trace.record("tool_start", {"summary": "报告章节生成", "detail": {"agent": "chapter_generation"}})
    # ... existing chapter generation code ...
    mark("generate_chapters")

    # ── Consistency ──
    trace.record("tool_start", {"summary": "一致性审查", "detail": {"agent": "consistency_review"}})
    # ... existing consistency code ...
    mark("consistency_review")
    trace.record("tool_result", {
        "summary": f"一致性审查完成：{len(consistency_review.issues)} 个问题",
        "detail": {"issues": [i.issue for i in consistency_review.issues]} if consistency_review.issues else {},
    })

    # ── Render ──
    trace.record("tool_start", {"summary": "报告渲染输出"})
    outputs = self._render(enhanced_payload, chapters, gap_items, attachment_notes)
    mark("render")

    # ── Final ──
    high_count = sum(1 for g in gap_items if g.risk_level == "HIGH")
    medium_count = sum(1 for g in gap_items if g.risk_level == "MEDIUM")
    low_count = sum(1 for g in gap_items if g.risk_level == "LOW")

    trace.record("final", {
        "summary": f"CPRA 合规诊断完成：{high_count} 项高风险，{medium_count} 项中风险，{low_count} 项低风险",
        "detail": {
            "output_files": outputs,
            "risk_distribution": {"HIGH": high_count, "MEDIUM": medium_count, "LOW": low_count},
            "total_duration_ms": int(sum(d for _, d in timings) * 1000),
        },
    })

    trace.record("final_brief", {
        "summary": f"CPRA 合规诊断完成",
        "detail": {
            "conclusion": f"完成 CPRA 合规全景诊断，识别 {high_count} 项高风险、{medium_count} 项中风险差距",
            "files": list(outputs.values()),
            "risks": [
                {"severity": "HIGH", "count": high_count},
                {"severity": "MEDIUM", "count": medium_count},
                {"severity": "LOW", "count": low_count},
            ],
            "next_steps": [
                "优先处理所有 HIGH 风险差距项，制定短期整改计划",
                "核查一致性审查中发现的问题",
                "补充缺失的隐私政策附件和数据处理协议",
                "建议每半年复审一次 CPRA 合规状态",
            ],
            "stats": {
                "total_duration_seconds": round(sum(d for _, d in timings), 1),
                "gap_count": len(gap_items),
                "output_files_count": len(outputs),
            },
        },
    })

    return CPRAResult(...)
```

- [ ] **Step 2: 确保现有 CPRA 测试仍通过**

```bash
cd /Users/oujiazhan/Desktop/实验室/社团/代码/ai4law && python -m pytest backend/modules/cpra/tests/ -v
```

- [ ] **Step 3: Commit**

```bash
git add backend/modules/cpra/service.py
git commit -m "feat(cpra): instrument generate_report with stream events at all key stages

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: CPRA submit_async 接入 TraceRecorder

**Files:**
- Modify: `backend/modules/cpra/service.py`

- [ ] **Step 1: 修改 submit_async 使用 submit_with_trace**

```python
def submit_async(self, payload: CPRARequest) -> CPRAAsyncAccepted:
    from pathlib import Path
    from backend.common.trace.recorder import TraceRecorder
    
    trace_dir = Path(f"storage/traces/cpra_{format_date_stamp()}")
    trace_recorder = TraceRecorder(trace_dir=trace_dir)
    
    snapshot = self.tasks.submit_with_trace(
        runner=lambda: self.generate_report(payload),
        trace_recorder=trace_recorder,
    )
    return self._snapshot_to_accepted(snapshot)
```

- [ ] **Step 2: 验证 CPRA async 流程**

```bash
cd /Users/oujiazhan/Desktop/实验室/社团/代码/ai4law && python -m pytest backend/modules/cpra/tests/ -v
```

- [ ] **Step 3: Commit**

```bash
git add backend/modules/cpra/service.py
git commit -m "feat(cpra): wire TraceRecorder via submit_with_trace in async submit path

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: 前端共享 SSE hook

**Files:**
- Create: `frontend/src/lib/useTaskEvents.ts`

- [ ] **Step 1: 实现 useTaskEvents hook**

```typescript
// frontend/src/lib/useTaskEvents.ts
import { useEffect, useRef, useState, useCallback } from "react";

export type RunEvent = {
  event_id: string;
  task_id: string;
  seq: number;
  event_type:
    | "status"
    | "thought"
    | "tool_start"
    | "tool_result"
    | "intermediate"
    | "warning"
    | "final"
    | "final_brief";
  timestamp: string;
  summary: string;
  detail?: Record<string, unknown> | null;
  level: "audit" | "debug";
};

// 全局单例：同一 taskId 共享一个 EventSource
const eventSources = new Map<string, EventSource>();
const listeners = new Map<string, Set<(events: RunEvent[]) => void>>();
const eventBuffers = new Map<string, RunEvent[]>();

function connectSSE(taskId: string): EventSource {
  const es = new EventSource(`/api/v1/events/task/${taskId}/stream`);

  es.onmessage = (e) => {
    if (!e.data || e.data.startsWith(":")) return;
    try {
      const event: RunEvent = JSON.parse(e.data);
      const buffer = eventBuffers.get(taskId) ?? [];
      buffer.push(event);
      eventBuffers.set(taskId, buffer);
      const subs = listeners.get(taskId);
      if (subs) {
        for (const cb of subs) cb([...buffer]);
      }
    } catch {
      // ignore parse errors
    }
  };

  es.onerror = () => {
    es.close();
    eventSources.delete(taskId);
  };

  return es;
}

function startPolling(taskId: string, since: number): () => void {
  let active = true;
  const poll = async () => {
    while (active) {
      try {
        const res = await fetch(`/api/v1/events/task/${taskId}/events?since=${since}`);
        const data = await res.json();
        if (data.events.length > 0) {
          const buffer = eventBuffers.get(taskId) ?? [];
          for (const e of data.events) {
            const exists = buffer.some((b) => b.seq === e.seq);
            if (!exists) buffer.push(e);
          }
          eventBuffers.set(taskId, buffer);
          since = data.latest_seq;
          const subs = listeners.get(taskId);
          if (subs) {
            for (const cb of subs) cb([...buffer]);
          }
        }
      } catch {
        // retry on next interval
      }
      await new Promise((r) => setTimeout(r, 1500));
    }
  };
  poll();
  return () => {
    active = false;
  };
}

export function useTaskEvents(taskId: string | null): RunEvent[] {
  const [events, setEvents] = useState<RunEvent[]>([]);
  const pollingCleanup = useRef<(() => void) | null>(null);

  const setEventsAndNotify = useCallback((newEvents: RunEvent[]) => {
    setEvents(newEvents);
  }, []);

  useEffect(() => {
    if (!taskId) return;

    // 注册监听器
    if (!listeners.has(taskId)) {
      listeners.set(taskId, new Set());
    }
    listeners.get(taskId)!.add(setEventsAndNotify);

    // 已有数据回放
    const existing = eventBuffers.get(taskId);
    if (existing && existing.length > 0) {
      setEvents([...existing]);
    }

    // 连 SSE
    if (!eventSources.has(taskId)) {
      const es = connectSSE(taskId);
      eventSources.set(taskId, es);
    }

    // 如果 3 秒内没收到事件，回退到轮询
    const fallbackTimer = setTimeout(() => {
      const buffer = eventBuffers.get(taskId);
      if (!buffer || buffer.length === 0) {
        pollingCleanup.current = startPolling(taskId, 0);
      }
    }, 3000);

    return () => {
      clearTimeout(fallbackTimer);
      listeners.get(taskId)?.delete(setEventsAndNotify);
      if (pollingCleanup.current) {
        pollingCleanup.current();
        pollingCleanup.current = null;
      }
    };
  }, [taskId, setEventsAndNotify]);

  return events;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/useTaskEvents.ts
git commit -m "feat(frontend): add shared useTaskEvents SSE hook with polling fallback

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 12: ExecutionTimeline 组件

**Files:**
- Create: `frontend/src/components/workspace/ExecutionTimeline.tsx`

- [ ] **Step 1: 实现 ExecutionTimeline**

```tsx
// frontend/src/components/workspace/ExecutionTimeline.tsx
import { useMemo } from "react";
import { useLang } from "../../lib/language";
import type { RunEvent } from "../../lib/useTaskEvents";
import { useTaskEvents } from "../../lib/useTaskEvents";

type Props = {
  taskId: string | null;
};

const ICON_MAP: Record<RunEvent["event_type"], string> = {
  status: "●",
  thought: "💭",
  tool_start: "🔧",
  tool_result: "✅",
  intermediate: "📊",
  warning: "⚠️",
  final: "🏁",
  final_brief: "📝",
};

const COLOR_MAP: Record<RunEvent["event_type"], string> = {
  status: "#6b7280",
  thought: "#7c3aed",
  tool_start: "#2563eb",
  tool_result: "#059669",
  intermediate: "#ea580c",
  warning: "#dc2626",
  final: "#9333ea",
  final_brief: "#d946ef",
};

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function TimelineRow({ event }: { event: RunEvent }) {
  const icon = ICON_MAP[event.event_type] ?? "●";
  const color = COLOR_MAP[event.event_type] ?? "#6b7280";

  return (
    <div className="timeline-row" style={{ borderLeftColor: color }}>
      <div className="timeline-icon" style={{ color }}>
        {icon}
      </div>
      <div className="timeline-content">
        <div className="timeline-summary">{event.summary}</div>
        <div className="timeline-time">{formatTime(event.timestamp)}</div>
        {event.detail && Object.keys(event.detail).length > 0 && (
          <details className="timeline-detail">
            <summary>详情</summary>
            <pre>{JSON.stringify(event.detail, null, 2)}</pre>
          </details>
        )}
      </div>
    </div>
  );
}

export function ExecutionTimeline({ taskId }: Props) {
  const { lang } = useLang();
  const events = useTaskEvents(taskId);

  const isConnected = events.length > 0;

  return (
    <section className="execution-timeline">
      <header className="workspace-tab-head">
        <h3>{lang === "zh" ? "执行流" : "Execution Timeline"}</h3>
        <p>
          <span className={`timeline-status-dot ${isConnected ? "connected" : "waiting"}`} />
          {isConnected
            ? lang === "zh"
              ? `实时连接 · ${events.length} 个事件`
              : `Connected · ${events.length} events`
            : lang === "zh"
              ? "等待事件..."
              : "Waiting for events..."}
        </p>
      </header>
      <div className="timeline-body">
        {events.length === 0 ? (
          <p className="resource-empty">
            {lang === "zh" ? "尚未收到执行事件。启动模块运行后将在此展示实时执行流。" : "No execution events yet. Start a module run to see the live timeline."}
          </p>
        ) : (
          events.map((e) => <TimelineRow key={e.seq ? `${e.task_id}-${e.seq}` : e.event_id} event={e} />)
        )}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/workspace/ExecutionTimeline.tsx
git commit -m "feat(frontend): add ExecutionTimeline component with real-time SSE consumption

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 13: RunBrief 组件

**Files:**
- Create: `frontend/src/components/workspace/RunBrief.tsx`

- [ ] **Step 1: 实现 RunBrief**

```tsx
// frontend/src/components/workspace/RunBrief.tsx
import { useMemo } from "react";
import { useLang } from "../../lib/language";
import { useTaskEvents } from "../../lib/useTaskEvents";
import type { RunEvent } from "../../lib/useTaskEvents";

type Props = {
  taskId: string | null;
};

type BriefDetail = {
  conclusion?: string;
  files?: string[];
  risks?: Array<{ severity: string; count: number }>;
  next_steps?: string[];
  stats?: Record<string, unknown>;
};

export function RunBrief({ taskId }: Props) {
  const { lang } = useLang();
  const events = useTaskEvents(taskId);

  const briefEvent = useMemo(() => {
    return events.find((e) => e.event_type === "final_brief") ?? null;
  }, [events]);

  const finalEvent = useMemo(() => {
    return events.find((e) => e.event_type === "final") ?? null;
  }, [events]);

  const brief: BriefDetail | null = (briefEvent?.detail as BriefDetail) ?? null;
  const isComplete = finalEvent !== null;

  if (!isComplete) {
    return (
      <section className="run-brief">
        <header className="workspace-tab-head">
          <h3>{lang === "zh" ? "结果简报" : "Run Brief"}</h3>
          <p>{lang === "zh" ? "等待执行完成..." : "Waiting for execution to complete..."}</p>
        </header>
      </section>
    );
  }

  return (
    <section className="run-brief">
      <header className="workspace-tab-head">
        <h3>{lang === "zh" ? "结果简报" : "Run Brief"}</h3>
        <p>{lang === "zh" ? "执行完成，以下是本次运行摘要。" : "Run complete. Summary below."}</p>
      </header>

      <div className="brief-sections">
        {/* 结论 */}
        <article className="brief-section brief-conclusion">
          <h4>{lang === "zh" ? "📋 执行结论" : "📋 Conclusion"}</h4>
          <p>{brief?.conclusion ?? finalEvent?.summary ?? "-"}</p>
        </article>

        {/* 文件列表 */}
        {brief?.files && brief.files.length > 0 && (
          <article className="brief-section brief-files">
            <h4>{lang === "zh" ? "📁 生成文件" : "📁 Generated Files"}</h4>
            <ul>
              {brief.files.map((f) => (
                <li key={f}>
                  <code>{f}</code>
                </li>
              ))}
            </ul>
          </article>
        )}

        {/* 风险分布 */}
        {brief?.risks && brief.risks.length > 0 && (
          <article className="brief-section brief-risks">
            <h4>{lang === "zh" ? "⚠️ 风险提示" : "⚠️ Risk Summary"}</h4>
            <div className="brief-risk-badges">
              {brief.risks.map((r) => (
                <span key={r.severity} className={`risk-badge risk-${r.severity.toLowerCase()}`}>
                  {r.severity}: {r.count}
                </span>
              ))}
            </div>
          </article>
        )}

        {/* 下一步 */}
        {brief?.next_steps && brief.next_steps.length > 0 && (
          <article className="brief-section brief-next">
            <h4>{lang === "zh" ? "👉 建议下一步" : "👉 Recommended Next Steps"}</h4>
            <ol>
              {brief.next_steps.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ol>
          </article>
        )}

        {/* 统计 */}
        {brief?.stats && (
          <article className="brief-section brief-stats">
            <h4>{lang === "zh" ? "📊 执行统计" : "📊 Execution Stats"}</h4>
            <div className="brief-stats-grid">
              {Object.entries(brief.stats).map(([key, value]) => (
                <div key={key} className="brief-stat-item">
                  <span className="brief-stat-label">{key}</span>
                  <strong>{String(value)}</strong>
                </div>
              ))}
            </div>
          </article>
        )}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/workspace/RunBrief.tsx
git commit -m "feat(frontend): add RunBrief component showing execution summary

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 14: IntermediatesPanel 通用化

**Files:**
- Modify: `frontend/src/components/workspace/AssessmentIntermediatesPanel.tsx`

- [ ] **Step 1: 扩展 SUB_TABS 以支持 CPRA**

在 SUB_TABS 数组中新增 CPRA 特有的中间产物标签：

```tsx
const SUB_TABS: SubTabDef[] = [
  { id: "facts", labelZh: "事实识别", labelEn: "Facts", fileKey: "facts_json" },
  { id: "path_judgment", labelZh: "路径判断", labelEn: "Path Judgment", fileKey: "path_judgment_json" },
  { id: "issues", labelZh: "问题清单", labelEn: "Issue List", fileKey: "issue_list_json" },
  { id: "gaps", labelZh: "差距项", labelEn: "Gap Items", fileKey: "gap_items_json" },       // 新增 CPRA
  { id: "evidence", labelZh: "证据链", labelEn: "Evidence Chain", fileKey: "evidence_chain_json" },
  { id: "spi", labelZh: "敏感信息风险", labelEn: "SPI Risks", fileKey: "spi_risks_json" },  // 新增 CPRA
  { id: "vendor", labelZh: "供应商问题", labelEn: "Vendor Issues", fileKey: "vendor_issues_json" }, // 新增 CPRA
  { id: "materials", labelZh: "材料清单", labelEn: "Material Checklist", fileKey: "material_checklist_json" },
  { id: "report", labelZh: "报告输出", labelEn: "Report Output", fileKey: "markdown" },
];

// 扩展 COLUMNS 增加 gaps 表格列定义
// 在 COLUMNS 对象中添加：
gaps: [
  { key: "domain", labelZh: "领域", labelEn: "Domain" },
  { key: "risk_level", labelZh: "风险等级", labelEn: "Risk", render: (v) => severityBadge(String(v)) },
  { key: "gap", labelZh: "差距描述", labelEn: "Gap" },
  { key: "legal_basis", labelZh: "法律依据", labelEn: "Legal Basis" },
  { key: "recommendation", labelZh: "建议", labelEn: "Recommendation" },
  { key: "phase", labelZh: "阶段", labelEn: "Phase" },
],
spi: [
  { key: "category", labelZh: "类别", labelEn: "Category" },
  { key: "is_sensitive", labelZh: "是否敏感", labelEn: "Sensitive" },
  { key: "risk", labelZh: "风险", labelEn: "Risk" },
],
vendor: [
  { key: "name", labelZh: "供应商名", labelEn: "Vendor" },
  { key: "vendor_type", labelZh: "类型", labelEn: "Type" },
  { key: "receives_spi", labelZh: "接收 SPI", labelEn: "Receives SPI" },
],
```

- [ ] **Step 2: 导出时支持 consumption from SSE events**

组件当前从 `outputFiles` 读文件路径。不改这个接口，但 WorkspaceShell 也传 SSE 消费得到的中间数据：

```tsx
// Props 接口扩展
interface Props {
  outputFiles: Record<string, string>;
  lang: "zh" | "en";
  sseIntermediates?: Array<{ category: string; data: unknown }>; // 新增：来自 SSE 的实时中间数据
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/workspace/AssessmentIntermediatesPanel.tsx
git commit -m "feat(frontend): generalize IntermediatesPanel with CPRA gap/spi/vendor tabs

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 15: WorkspaceShell 四段式 TabBar

**Files:**
- Modify: `frontend/src/components/workspace/WorkspaceShell.tsx`

- [ ] **Step 1: 扩展 WorkspaceTopTabId 类型，新增 timeline 和 brief tab**

```tsx
// 修改 WorkspaceTopTabId 类型定义
type WorkspaceTopTabId = "details" | "canvas" | "docs" | "terminal" | "report" | "timeline" | "brief";
type WorkspaceTopTab = {
  id: WorkspaceTopTabId;
  key: "workspaceTabDetails" | "workspaceTabCanvas" | "workspaceTabDocs" | "workspaceTabTerminal" | "workspaceTabReport" | "workspaceTabTimeline" | "workspaceTabBrief";
  closable: boolean;
};

// 在 WORKSPACE_TABS 数组中新增：
{ id: "timeline", key: "workspaceTabTimeline", closable: true },
{ id: "brief", key: "workspaceTabBrief", closable: true },
```

- [ ] **Step 2: 在 renderTabSurface() 中新增 timeline 和 brief 渲染分支**

在 switch/if 逻辑中扩展：

```tsx
// 在 renderTabSurface() 函数内，在 "report" 分支之前添加：

if (activeTab === "timeline") {
  return <ExecutionTimeline taskId={latestRun?.asyncTaskId ?? null} />;
}

if (activeTab === "brief") {
  return <RunBrief taskId={latestRun?.asyncTaskId ?? null} />;
}
```

- [ ] **Step 3: import 新组件**

在文件顶部添加：

```tsx
import { ExecutionTimeline } from "./ExecutionTimeline";
import { RunBrief } from "./RunBrief";
```

- [ ] **Step 4: 运行完成后自动打开 timeline**

在 `onRunDone` 回调中：

```tsx
const onRunDone = (output: RunOutput) => {
  // ... 现有代码 ...
  if (output.response && output.asyncTaskId) {
    setOpenTabs((prev) => (prev.includes("timeline") ? prev : [...prev, "timeline"]));
    setActiveTab("timeline");  // 改为自动切到执行流
  }
};
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/workspace/WorkspaceShell.tsx
git commit -m "feat(frontend): add timeline and brief tabs to WorkspaceShell four-panel layout

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 16: 端到端验证

**Files:**
- No new files — manual verification

- [ ] **Step 1: 启动后端**

```bash
cd /Users/oujiazhan/Desktop/实验室/社团/代码/ai4law && uvicorn backend.main:app --reload --port 8000
```

- [ ] **Step 2: 通过 API 触发 CPRA 异步运行**

```bash
curl -X POST http://localhost:8000/api/v1/cpra/run \
  -H "Content-Type: application/json" \
  -d '{"company_name":"TestCorp","business_model":"电商零售","data_lifecycle":"收集用户信息用于订单处理"}' | jq .
```

- [ ] **Step 3: 立即连接 SSE 验证事件流**

```bash
curl -N http://localhost:8000/api/v1/events/task/<task_id>/stream
```

预期输出：SSE 格式的 `data:` 行，包含 status → thought → tool_start → tool_result → intermediate → final → final_brief 事件流。

- [ ] **Step 4: 验证轮询 endpoint**

```bash
curl http://localhost:8000/api/v1/events/task/<task_id>/events?since=0 | jq .
```

- [ ] **Step 5: 启动前端验证**

```bash
cd /Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/frontend && npm run dev
```

在浏览器中：
1. 创建 CPRA 任务空间
2. 运行模块
3. 确认自动切换到 "执行流" tab，看到实时事件
4. 切换 "中间结果" tab，确认 CPRA facts/gap_items 展示
5. 切换 "结果简报" tab，确认 conclusion/files/risks/next_steps
6. "对话" tab 保持 AssistantPanel 功能不变

- [ ] **Step 6: 运行全部测试确认无回归**

```bash
cd /Users/oujiazhan/Desktop/实验室/社团/代码/ai4law && python -m pytest backend/ -v --tb=short
```

- [ ] **Step 7: Commit final**

```bash
git add -A
git commit -m "chore: final verification — all tests pass, CPRA E2E observable execution verified

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 验证检查清单

### Step 1 验证
- [ ] `RunEvent` 模型可序列化/反序列化
- [ ] `TraceRecorder.record()` 同时写文件和推送事件
- [ ] `GET /task/{id}/stream` 返回 SSE 格式
- [ ] `GET /task/{id}/events?since=X` 返回增量事件
- [ ] 订阅者异常不影响主流程

### Step 2 验证
- [ ] CPRA 运行产生完整事件流（8 种事件类型至少各一条）
- [ ] intermediate 事件 detail 包含结构化 CPRA 数据
- [ ] final_brief 包含 conclusion/files/risks/next_steps 四项
- [ ] 现有 CPRA 测试全部通过

### Step 3 验证
- [ ] 前端四段 tab 可切换
- [ ] ExecutionTimeline 实时显示新事件
- [ ] SSE 断开时自动降级到轮询
- [ ] IntermediatesPanel 展示 CPRA facts/gap_items/spi/vendor
- [ ] RunBrief 在 final_brief 事件到达后自动渲染
- [ ] 页面刷新后可通过轮询恢复事件列表
