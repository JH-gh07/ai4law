"""Read and compare persisted white-box harness runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = REPO_ROOT / "runs"


def _find_run(run_id: str) -> Path | None:
    if not RUNS_DIR.exists():
        return None
    for module_dir in RUNS_DIR.iterdir():
        candidate = module_dir / run_id
        if candidate.is_dir() and (candidate / "run_manifest.json").is_file():
            return candidate
    return None


def _read_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_run(run_id: str) -> dict[str, Any] | None:
    run_dir = _find_run(run_id)
    if run_dir is None:
        return None
    return {
        "path": run_dir,
        "manifest": _read_optional_json(run_dir / "run_manifest.json"),
        "result": _read_optional_json(run_dir / "output" / "result.json"),
        "error": _read_optional_json(run_dir / "output" / "error.json"),
        "events": _load_trace_events(run_dir),
    }


def _load_trace_events(run_dir: Path) -> list[dict[str, Any]]:
    trace_manifest = _read_optional_json(run_dir / "trace" / "manifest.json") or {}
    events: list[dict[str, Any]] = []
    for reference in trace_manifest.get("events", []):
        raw_path = Path(str(reference.get("path") or ""))
        candidates = [raw_path]
        if not raw_path.is_absolute():
            candidates.extend(
                [REPO_ROOT / raw_path, run_dir / "trace" / raw_path.name]
            )
        event_path = next((path for path in candidates if path.is_file()), None)
        if event_path is None:
            continue
        event = _read_optional_json(event_path)
        if event:
            events.append(event)
    return events


def diff_runs(left: dict[str, Any], right: dict[str, Any]) -> dict[str, tuple[Any, Any]]:
    left_manifest = left["manifest"] or {}
    right_manifest = right["manifest"] or {}
    left_result = left["result"] or {}
    right_result = right["result"] or {}
    fields = {
        "status": (left_manifest.get("status"), right_manifest.get("status")),
        "module": (left_manifest.get("module"), right_manifest.get("module")),
        "risk_level": (left_result.get("risk_level"), right_result.get("risk_level")),
        "recommended_path": (
            left_result.get("recommended_path"),
            right_result.get("recommended_path"),
        ),
    }
    return fields


def list_runs(module: str | None = None) -> list[dict[str, Any]]:
    if not RUNS_DIR.exists():
        return []
    module_dirs = [RUNS_DIR / module] if module else list(RUNS_DIR.iterdir())
    manifests: list[dict[str, Any]] = []
    for module_dir in module_dirs:
        if not module_dir.is_dir():
            continue
        for run_dir in module_dir.iterdir():
            manifest = _read_optional_json(run_dir / "run_manifest.json")
            if manifest:
                manifests.append(manifest)
    return sorted(manifests, key=lambda item: item.get("run_id", ""), reverse=True)


def _print_run(data: dict[str, Any], *, show_events: bool = False) -> None:
    manifest = data["manifest"] or {}
    result = data["result"] or {}
    error = data["error"] or {}
    print(f"run: {manifest.get('run_id', '?')}")
    print(f"module: {manifest.get('module', '?')}")
    print(f"status: {manifest.get('status', '?')}")
    print(f"duration_ms: {manifest.get('duration_ms', 0):.0f}")
    provider = manifest.get("provider_snapshot") or {}
    observability = manifest.get("observability") or {}
    tokens = observability.get("tokens") or {}
    print(
        f"provider: {provider.get('provider_id', '?')} / "
        f"{provider.get('model', '') or '(no model)'}"
    )
    print(
        f"events: {observability.get('event_count', 0)}, "
        f"llm_calls: {observability.get('llm_calls', 0)}, "
        f"tokens: {tokens.get('total_tokens', 0)}, "
        f"fallbacks: {observability.get('fallback_count', 0)}"
    )
    for artifact in (manifest.get("input") or {}).get("artifacts", []):
        print(
            f"input: {artifact.get('file_name', '')} "
            f"{artifact.get('storage_uri', '')}".rstrip()
        )
    for artifact in (manifest.get("output") or {}).get("artifacts", []):
        print(f"output[{artifact.get('role', '?')}]: {artifact.get('path', '')}")
    if result:
        print(f"risk_level: {result.get('risk_level', '')}")
        print(f"report_path: {result.get('report_path', '')}")
    if error:
        print(f"error: {error.get('type', '?')}: {error.get('message', '')}")
    if show_events:
        for event in data.get("events", []):
            payload = event.get("payload") or {}
            print(
                f"[{int(event.get('seq', 0)):03d}] "
                f"{event.get('name', '?')}: {payload.get('summary', '')}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="AI4Law harness run viewer")
    parser.add_argument("run_id", nargs="?")
    parser.add_argument("--diff")
    parser.add_argument("--list", "-l", nargs="?", const="__all__")
    parser.add_argument("--events", action="store_true", help="print persisted events")
    args = parser.parse_args()
    if args.list is not None:
        module = None if args.list == "__all__" else args.list
        for manifest in list_runs(module):
            print(
                f"{manifest.get('run_id', '?')} "
                f"{manifest.get('module', '?')} {manifest.get('status', '?')}"
            )
        return 0
    if not args.run_id:
        parser.print_help()
        return 1
    current = load_run(args.run_id)
    if current is None:
        print(f"Run not found: {args.run_id}")
        return 1
    if args.diff:
        other = load_run(args.diff)
        if other is None:
            print(f"Run not found: {args.diff}")
            return 1
        for field, values in diff_runs(current, other).items():
            print(f"{field}: {values[0]!r} -> {values[1]!r}")
        return 0
    _print_run(current, show_events=args.events)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
