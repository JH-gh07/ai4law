"""run_with_trace — 为同步/异步执行路径注入 TraceRecorder + SSEManager 桥接。"""

from __future__ import annotations

import contextvars
from pathlib import Path
from typing import Any, Callable

from backend.common.trace.context import current_trace
from backend.common.trace.recorder import TraceRecorder


def make_traced_runner(
    runner: Callable[[], Any],
    *,
    trace_dir: Path,
    module: str,
    task_id: str = "",
) -> tuple[Callable[[], Any], TraceRecorder, str]:
    """创建一个带 TraceRecorder 注入的 wrapped runner。

    返回 (wrapped_runner, trace_recorder, task_id)。
    调用方将 wrapped_runner 提交给 InMemoryTaskManager，
    SSEManager 在 submit_with_trace 里自动注册为订阅者。
    """
    trace_recorder = TraceRecorder(trace_dir=trace_dir)
    from uuid import uuid4
    final_task_id = task_id or str(uuid4())
    trace_recorder._task_id = final_task_id

    def wrapped_runner() -> Any:
        token: contextvars.Token | None = None
        try:
            token = current_trace.set(trace_recorder)
            return runner()
        finally:
            if token is not None:
                current_trace.reset(token)

    return wrapped_runner, trace_recorder, final_task_id


def trace_sync(module: str, runner: Callable[[], Any]) -> Any:
    """在上下文管理器内注入 TraceRecorder 并执行 runner。

    用于同步端点（例如 POST /cpra/generate），
    使 generate_report 内部的 trace.record() 调用生效。
    """
    trace_dir = Path(f"storage/traces/{module}_sync")
    recorder = TraceRecorder(trace_dir=trace_dir)
    token = current_trace.set(recorder)
    try:
        return runner()
    finally:
        current_trace.reset(token)
        recorder.write_manifest()
