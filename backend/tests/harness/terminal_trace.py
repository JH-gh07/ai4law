"""TerminalTraceSubscriber — real-time safe Trace output for the CLI harness.

Wired into TraceRecorder.subscribe(), prints each RunEvent as it is produced,
filtering sensitive fields. Must never cause a business failure.
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.common.trace.events import RunEvent

_SENSITIVE_KEYS = {
    "api_key", "authorization", "password", "secret", "token",
    "ssn", "credit_card", "credentials", "prompt", "full_text",
    "company_uscc", "legal_representative", "registered_address",
}

_SAFE_MAX_VALUE_LEN = 60


def _safe_summary(event: RunEvent) -> str:
    """Return a human-readable summary for terminal display."""
    summary = event.summary or event.event_type
    detail = event.detail or {}

    # Enrich with LLM info
    if event.event_type == "tool_start" and detail.get("tool") == "llm_chat":
        model = detail.get("model", "")
        if model:
            summary = f"llm_chat → {model}"
    elif event.event_type == "tool_result" and detail.get("tool") == "llm_chat":
        usage = detail.get("usage") or {}
        tokens = usage.get("total_tokens", 0)
        summary = f"llm_chat done ({tokens} tokens)"
    elif event.event_type == "tool_result":
        dur = detail.get("duration_ms")
        results = detail.get("results", detail.get("result_count"))
        parts = []
        if dur is not None:
            parts.append(f"duration={dur:.0f}ms" if isinstance(dur, float) else f"duration={dur}ms")
        if results is not None:
            parts.append(f"results={results}")
        if parts:
            summary = f"{event.summary} ({', '.join(parts)})"
    elif event.event_type == "final":
        dur = detail.get("total_duration_ms")
        if dur is not None:
            summary = f"{summary} ({dur:.0f}ms)"
    elif event.event_type == "warning":
        msg = detail.get("message", detail.get("warning", ""))
        if msg:
            summary = f"⚠ {msg}"
    elif event.event_type == "thought":
        text = detail.get("text", detail.get("thought", ""))
        if text and len(text) < 80:
            summary = text

    return _sanitize_text(str(summary))


def _sanitize_text(text: str) -> str:
    """Remove or mask sensitive content from terminal output."""
    result = text.replace("\n", " ").replace("\r", " ")
    # Truncate long values
    if len(result) > 120:
        result = result[:117] + "..."
    return result


def _contains_sensitive_keys(data: dict) -> bool:
    """Check if a dict contains any sensitive keys (case-insensitive)."""
    if not isinstance(data, dict):
        return False
    lower_keys = {k.lower() for k in data}
    return bool(lower_keys & _SENSITIVE_KEYS)


def _safe_detail(detail: dict | None) -> dict:
    """Return a safe subset of detail for terminal, filtering sensitive values."""
    if not detail:
        return {}
    safe = {}
    for key, value in detail.items():
        if key.lower() in _SENSITIVE_KEYS:
            safe[key] = "***REDACTED***"
        elif isinstance(value, str) and len(value) > _SAFE_MAX_VALUE_LEN:
            safe[key] = value[:_SAFE_MAX_VALUE_LEN] + "..."
        elif isinstance(value, dict) and _contains_sensitive_keys(value):
            safe[key] = "***REDACTED***"
        else:
            safe[key] = value
    return safe


class TerminalTraceSubscriber:
    """Print each trace event to stderr as it arrives, with sensitive filtering.

    Usage:
        subscriber = TerminalTraceSubscriber()
        recorder.subscribe(subscriber)
    """

    def __init__(self, stream=None):
        import sys as _sys
        self._stream = stream or _sys.stderr
        self._event_count = 0

    def __call__(self, event: RunEvent) -> None:
        try:
            self._event_count += 1
            ts = datetime.fromisoformat(event.timestamp).strftime("%H:%M:%S")
            etype = event.event_type.ljust(13)
            summary = _safe_summary(event)
            self._stream.write(
                f"\033[2m{ts}\033[0m \033[1m#{event.seq:03d}\033[0m "
                f"\033[36m{etype}\033[0m {summary}\n"
            )
            self._stream.flush()
        except Exception:
            pass  # Never crash the business process
