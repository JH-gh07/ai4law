from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit


_SAFE_PATH_PART = re.compile(r"^[A-Za-z0-9_-]+$")


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _safe_reference(value: str) -> str:
    parts = urlsplit(value)
    if parts.scheme:
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    return parts.path


def _input_artifacts(value: Any) -> list[dict[str, str]]:
    artifacts: list[dict[str, str]] = []

    def visit(item: Any, parent_key: str = "") -> None:
        if isinstance(item, dict):
            artifact = {
                key: (
                    _safe_reference(str(item[key]))
                    if key == "storage_uri"
                    else str(item[key])
                )
                for key in ("file_name", "file_role", "storage_uri", "file_format")
                if item.get(key) not in (None, "")
            }
            if artifact and ("file_name" in artifact or "storage_uri" in artifact):
                artifacts.append(artifact)
            for key, child in item.items():
                visit(child, str(key))
        elif isinstance(item, list):
            for child in item:
                visit(child, parent_key)
        elif isinstance(item, str) and parent_key in {
            "uploaded_files",
            "files",
            "attachments",
        }:
            safe_uri = _safe_reference(item)
            file_name = Path(urlsplit(safe_uri).path).name
            if file_name:
                artifacts.append(
                    {"file_name": file_name, "storage_uri": safe_uri}
                )

    visit(value)
    return artifacts


def summarize_input(value: Any) -> dict[str, Any]:
    payload = value if isinstance(value, dict) else {"value": value}
    return {
        "sha256": _canonical_hash(payload),
        "fields": sorted(str(key) for key in payload),
        "artifacts": _input_artifacts(payload),
    }


def summarize_output(value: Any) -> dict[str, Any]:
    payload = value if isinstance(value, dict) else {}
    artifacts: list[dict[str, str]] = []
    seen_paths: set[str] = set()
    output_files = payload.get("output_files")
    if isinstance(output_files, dict):
        for role, path in output_files.items():
            if isinstance(path, str) and path.strip() and path not in seen_paths:
                artifact = {"role": str(role), "path": path}
                artifacts.append(artifact)
                seen_paths.add(path)
    report_path = payload.get("report_path")
    if (
        isinstance(report_path, str)
        and report_path.strip()
        and report_path not in seen_paths
    ):
        artifacts.append({"role": "report", "path": report_path})
    return {
        "fields": sorted(str(key) for key in payload),
        "artifacts": artifacts,
    }


def summarize_trace(trace_recorder: Any) -> dict[str, Any]:
    tokens = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }
    llm_calls = 0
    fallback_count = 0
    events = list(getattr(trace_recorder, "_events", []) or [])
    for event in events:
        try:
            raw = json.loads(Path(event.path).read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            continue
        payload = raw.get("payload") if isinstance(raw, dict) else {}
        detail = payload.get("detail") if isinstance(payload, dict) else {}
        if not isinstance(detail, dict):
            continue
        nested_llm = detail.get("llm")
        if isinstance(nested_llm, dict):
            usage = nested_llm
        elif detail.get("tool") == "llm_chat":
            usage = detail.get("usage")
        else:
            continue
        if raw.get("name") == "tool_result":
            llm_calls += 1
        if (
            isinstance(nested_llm, dict) and nested_llm.get("fallback") is True
        ) or detail.get("fallback") is True:
            fallback_count += 1
        if isinstance(usage, dict):
            for key in tokens:
                value = usage.get(key)
                if isinstance(value, int):
                    tokens[key] += value
    return {
        "event_count": len(events),
        "trace_manifest": str(trace_recorder.trace_dir / "manifest.json"),
        "llm_calls": llm_calls,
        "tokens": tokens,
        "fallback_count": fallback_count,
    }


def write_run_manifest(
    path: Path,
    *,
    run_id: str,
    module: str,
    status: str,
    created_at: str,
    updated_at: str,
    attempts: int,
    max_attempts: int,
    duration_ms: int,
    provider_snapshot: dict[str, Any] | None,
    input_snapshot: Any,
    result: Any,
    error: str | None,
    trace_recorder: Any,
) -> Path:
    payload = {
        "schema_version": "1.0",
        "run_id": run_id,
        "module": module,
        "status": status,
        "created_at": created_at,
        "updated_at": updated_at,
        "duration_ms": max(0, int(duration_ms)),
        "attempts": attempts,
        "max_attempts": max_attempts,
        "provider_snapshot": provider_snapshot,
        "input": summarize_input(input_snapshot),
        "output": summarize_output(result),
        "observability": summarize_trace(trace_recorder),
        "error": error,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    temporary.replace(path)
    return path


def load_run_manifest(
    outputs_dir: Path,
    *,
    module: str,
    run_id: str,
) -> dict[str, Any] | None:
    if not _SAFE_PATH_PART.fullmatch(module) or not _SAFE_PATH_PART.fullmatch(run_id):
        return None
    root = outputs_dir.resolve()
    path = (root / module / run_id / "run_manifest.json").resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("run_id") != run_id or payload.get("module") != module:
        return None
    return payload
