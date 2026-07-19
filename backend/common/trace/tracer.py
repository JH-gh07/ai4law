"""run_with_trace — 为同步/异步执行路径注入 TraceRecorder + SSEManager 桥接。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from backend.common.trace.context import current_trace
from backend.common.trace.recorder import TraceRecorder



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
