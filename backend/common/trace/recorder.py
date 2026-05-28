from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TraceEvent:
    seq: int
    name: str
    path: str
    created_at: str


class TraceRecorder:
    """Write step-by-step trace payloads as JSON files under a run directory."""

    def __init__(self, trace_dir: Path) -> None:
        self.trace_dir = trace_dir
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self._seq = 0
        self._events: list[TraceEvent] = []

    def record(self, name: str, payload: dict[str, Any]) -> Path:
        self._seq += 1
        safe_name = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in (name or "event")).strip("_")
        filename = f"{self._seq:03d}_{safe_name}.json"
        path = self.trace_dir / filename
        to_write = {"name": name, "seq": self._seq, "created_at": _utc_now_iso(), "payload": payload}
        path.write_text(json.dumps(to_write, ensure_ascii=False, indent=2), encoding="utf-8")
        self._events.append(TraceEvent(seq=self._seq, name=name, path=str(path), created_at=to_write["created_at"]))
        return path

    def write_manifest(self) -> Path:
        path = self.trace_dir / "manifest.json"
        payload = {
            "created_at": _utc_now_iso(),
            "event_count": len(self._events),
            "events": [event.__dict__ for event in self._events],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

