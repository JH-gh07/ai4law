"""prepare_run / finalize_run — 统一模块执行生命周期的 TraceRecorder 管理。"""

from __future__ import annotations

import contextvars
from pathlib import Path
from typing import Any

from backend.common.trace.context import current_trace
from backend.common.trace.recorder import TraceRecorder


def prepare_run(
    *,
    module: str,
    task_id: str,
    trace: TraceRecorder | None = None,
) -> tuple[TraceRecorder, contextvars.Token[TraceRecorder | None] | None]:
    """准备执行上下文：确保 TraceRecorder 可用并注入 contextvar。

    优先级：显式传入的 trace > contextvar 中已有的 > 默认创建。
    返回 (trace, token)，调用方在 finally 中 finalize_run(token)。
    """
    if trace is None:
        trace = current_trace.get()

    if trace is None:
        trace_dir = Path(f"storage/traces/{module}_{task_id}")
        trace = TraceRecorder(trace_dir=trace_dir, task_id=task_id)

    # 如果 trace 的 task_id 尚未设置，补上
    if not trace._task_id:
        trace._task_id = task_id

    # 将 SSEManager 注册为订阅者（幂等 —— subscribe 追加到列表）
    from backend.common.events.manager import get_ssemanager
    sm = get_ssemanager()
    trace.subscribe(sm.on_event)

    token = current_trace.set(trace)
    return trace, token


def finalize_run(token: contextvars.Token[TraceRecorder | None] | None) -> None:
    """回滚 contextvar 并落盘 trace manifest。"""
    if token is not None:
        current_trace.reset(token)

    # manifest 由 TraceRecorder.write_manifest 负责
    # 这里做一个 best-effort：如果可以从 contextvar 拿到当前 trace，写 manifest
    trace = current_trace.get()
    if trace is not None:
        try:
            trace.write_manifest()
        except Exception:
            pass
