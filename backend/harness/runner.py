"""Deterministic white-box runner for the registered report modules."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import shutil
import sys
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.common.trace.recorder import TraceRecorder
from backend.common.trace.events import RunEvent
from backend.common.runtime.run_manifest import (
    summarize_input,
    summarize_output,
    summarize_trace,
)
from backend.tests.harness.validators import validate_expected


RUNS_DIR = REPO_ROOT / "runs"
TESTS_DIR = REPO_ROOT / "backend" / "tests"


def _resolve_case_input(case: dict[str, Any]) -> dict[str, Any]:
    scenario_path = case.get("scenario_path")
    if not scenario_path:
        value = case.get("input", {})
        return value if isinstance(value, dict) else {}
    if "input" in case:
        raise ValueError("case must not define both scenario_path and input")
    path = (REPO_ROOT / str(scenario_path)).resolve()
    if not path.is_relative_to(REPO_ROOT.resolve()):
        raise ValueError("scenario_path must stay inside the repository")
    scenario = json.loads(path.read_text(encoding="utf-8"))
    request = scenario.get("request") if isinstance(scenario, dict) else None
    if not isinstance(request, dict):
        raise ValueError(f"shared scenario must contain an object request: {path}")
    return request


def _resolve_case_expected(case: dict[str, Any]) -> dict[str, Any]:
    expected_path = case.get("expected_path")
    if not expected_path:
        return case.get("expected", {})
    if "expected" in case:
        raise ValueError("case must not define both expected_path and expected")
    path = (REPO_ROOT / str(expected_path)).resolve()
    if not path.is_relative_to(REPO_ROOT.resolve()):
        raise ValueError("expected_path must stay inside the repository")
    document = json.loads(path.read_text(encoding="utf-8"))
    expected = document.get("harness") if isinstance(document, dict) else None
    if not isinstance(expected, dict) or not expected:
        raise ValueError(f"shared expected must contain a non-empty harness object: {path}")
    return expected


class _DisabledLLM:
    enabled = False
    _enabled = False


class _DisabledLegalService:
    enabled = False


TraceSubscriber = Callable[[RunEvent], None]
Invoke = Callable[
    [dict[str, Any], bool, Path, TraceSubscriber | None],
    dict[str, Any],
]


from backend.tests.harness.terminal_trace import TerminalTraceSubscriber  # noqa: E402, F811


@dataclass(frozen=True)
class ModuleAdapter:
    alias: str
    module_id: str
    implementation_package: str
    invoke: Invoke


_ADAPTER_DEFINITIONS = {
    "diagnosis": (
        "cn.transfer_diagnosis",
        "backend.domains.cn.transfer_diagnosis",
        "DiagnosisAnswers",
        "DiagnosisService",
    ),
    "assessment": (
        "cn.security_assessment",
        "backend.domains.cn.security_assessment",
        "AssessmentRequest",
        "AssessmentService",
    ),
    "pipia": (
        "cn.pipia",
        "backend.domains.cn.pipia",
        "PIPIARequest",
        "PIPIAService",
    ),
    "cn_flow": (
        "us.eo_14117_flow_review",
        "backend.domains.us.eo14117_flow_review",
        "CNFlowRequest",
        "CNFlowService",
    ),
    "eu_scc": (
        "eu.scc_review",
        "backend.domains.eu.scc_review",
        "SCCReviewRequest",
        "EU_SCCService",
    ),
    "bcr": (
        "eu.bcr_review",
        "backend.domains.eu.bcr_review",
        "BCRRequest",
        "BCRService",
    ),
    "dpia": (
        "eu.dpia",
        "backend.domains.eu.dpia",
        "DPIARequest",
        "DPIAService",
    ),
    "tia": (
        "eu.tia",
        "backend.domains.eu.tia",
        "TIARequest",
        "TIAService",
    ),
    "us_14117": (
        "us.eo_14117",
        "backend.domains.us.eo14117",
        "US14117Request",
        "US14117Service",
    ),
    "cpra": (
        "us.cpra",
        "backend.domains.us.cpra",
        "CPRARequest",
        "CPRAService",
    ),
}


def _product_registry() -> dict[str, dict[str, Any]]:
    records = json.loads(
        (REPO_ROOT / "config" / "module_registry.json").read_text(encoding="utf-8")
    )
    return {record["frontend_key"]: record for record in records}


def _make_service(alias: str, service_class, no_llm: bool):
    if not no_llm:
        return service_class()
    if alias == "assessment":
        service = service_class(
            llm_client=_DisabledLLM(), legal_api_service=_DisabledLegalService()
        )
        diagnosis_class = getattr(
            importlib.import_module("backend.domains.cn.transfer_diagnosis.service"),
            "DiagnosisService",
        )
        service.diagnosis_service = diagnosis_class(llm_client=_DisabledLLM())
        return service
    if alias in {"pipia", "dpia"}:
        return service_class(llm_client=None)
    service = service_class(llm_client=_DisabledLLM())
    if alias == "cpra":
        service.schema_first_enabled = True
    return service


def _serialize_result(result: Any) -> dict[str, Any]:
    if hasattr(result, "model_dump"):
        data = result.model_dump(mode="json")
    elif isinstance(result, dict):
        data = dict(result)
    else:
        raise TypeError(f"Unsupported harness result: {type(result).__name__}")
    for field in ("chapters", "regulations", "risk_matrix", "mitigation_plan"):
        value = data.get(field)
        if isinstance(value, list):
            data[f"{field}_count"] = len(value)
    return data


def _generic_invoke(
    alias: str, package: str, request_name: str, service_name: str
) -> Invoke:
    def invoke(
        case: dict[str, Any],
        no_llm: bool,
        trace_dir: Path,
        trace_subscriber: TraceSubscriber | None,
    ) -> dict[str, Any]:
        schema_module = importlib.import_module(f"{package}.schema")
        service_module = importlib.import_module(f"{package}.service")
        request_class = getattr(schema_module, request_name)
        service_class = getattr(service_module, service_name)
        payload = request_class.model_validate(case["input"])
        service = _make_service(alias, service_class, no_llm)
        recorder = TraceRecorder(trace_dir, task_id=f"harness-{alias}")
        if trace_subscriber is not None:
            recorder.subscribe(trace_subscriber)
        result = service.generate_report(payload, trace=recorder)
        recorder.write_manifest()
        return _serialize_result(result)

    return invoke


def _diagnosis_invoke(
    case: dict[str, Any],
    no_llm: bool,
    trace_dir: Path,
    trace_subscriber: TraceSubscriber | None,
) -> dict[str, Any]:
    package = "backend.domains.cn.transfer_diagnosis"
    answers_class = getattr(importlib.import_module(f"{package}.schema"), "DiagnosisAnswers")
    service_class = getattr(importlib.import_module(f"{package}.service"), "DiagnosisService")
    answers = answers_class.model_validate(case["input"]["answers"])
    service = service_class(llm_client=_DisabledLLM()) if no_llm else service_class()
    recorder = TraceRecorder(trace_dir, task_id="harness-diagnosis")
    if trace_subscriber is not None:
        recorder.subscribe(trace_subscriber)
    result = service.evaluate(answers, trace=recorder)
    recorder.write_manifest()
    return _serialize_result(result)


def _review_harness_settings(run_dir: Path, no_llm: bool):
    from backend.core.settings import Settings

    settings_kwargs: dict[str, Any] = {
        "database_url": f"sqlite:///{run_dir / 'review.db'}",
        "storage_dir": run_dir / "storage",
        "task_mode": "inline",
    }
    if no_llm:
        settings_kwargs.update(
            {
                "llm_provider": "none",
                "llm_api_key": None,
                "siliconflow_api_key": None,
                "tencent_api_key": None,
            }
        )
    return Settings(**settings_kwargs, _env_file=None)


def _review_invoke(
    case: dict[str, Any],
    no_llm: bool,
    trace_dir: Path,
    trace_subscriber: TraceSubscriber | None,
) -> dict[str, Any]:
    from backend.common.trace.context import current_trace
    from backend.core.container import AppContainer
    from backend.core.db import init_db
    from backend.schemas.review import ReviewGenerateRequest

    run_dir = trace_dir.parent
    settings = _review_harness_settings(run_dir, no_llm)
    container = AppContainer(settings)
    init_db(container.engine)

    copied_files: list[str] = []
    destination_dir = settings.upload_dir / "harness-input"
    destination_dir.mkdir(parents=True, exist_ok=True)
    for raw_path in case["input"].get("uploaded_files", []):
        source = Path(raw_path)
        if not source.is_absolute():
            source = REPO_ROOT / source
        source = source.resolve()
        if not source.exists() or not source.is_file():
            raise FileNotFoundError(f"Review fixture not found: {source}")
        destination = destination_dir / source.name
        shutil.copy2(source, destination)
        copied_files.append(str(destination))

    request_data = dict(case["input"])
    request_data["uploaded_files"] = copied_files
    payload = ReviewGenerateRequest.model_validate(request_data)
    recorder = TraceRecorder(trace_dir, task_id="harness-review")
    if trace_subscriber is not None:
        recorder.subscribe(trace_subscriber)
    recorder.record(
        "status",
        {
            "summary": "开始文档审查 CLI 案例",
            "detail": {"file_count": len(copied_files)},
        },
    )
    db = container.session_factory()
    token = current_trace.set(recorder)
    try:
        result = container.review_service.generate_from_request(
            db,
            "harness-review-user",
            payload,
        )
        recorder.record(
            "final",
            {
                "summary": "文档审查 CLI 案例完成",
                "detail": {"status": "COMPLETED"},
            },
        )
        return _serialize_result(result)
    finally:
        current_trace.reset(token)
        recorder.write_manifest()
        db.close()
        container.engine.dispose()


def _build_adapters() -> dict[str, ModuleAdapter]:
    product_registry = _product_registry()
    adapters: dict[str, ModuleAdapter] = {}
    for alias, definition in _ADAPTER_DEFINITIONS.items():
        module_id, package, request_name, service_name = definition
        registered = product_registry.get(alias)
        if not registered:
            raise RuntimeError(f"Harness module is absent from module_registry.json: {alias}")
        if registered["module_id"] != module_id:
            raise RuntimeError(f"Harness module_id drift for {alias}")
        if registered["implementation_package"] != package:
            raise RuntimeError(f"Harness package drift for {alias}")
        invoke = (
            _diagnosis_invoke
            if alias == "diagnosis"
            else _generic_invoke(alias, package, request_name, service_name)
        )
        adapters[alias] = ModuleAdapter(alias, module_id, package, invoke)
    review = product_registry.get("review")
    if not review:
        raise RuntimeError("Harness review module is absent from module_registry.json")
    adapters["review"] = ModuleAdapter(
        alias="review",
        module_id=review["module_id"],
        implementation_package=review["implementation_package"],
        invoke=_review_invoke,
    )
    expected = set(product_registry)
    if set(adapters) != expected:
        raise RuntimeError(
            f"Harness coverage drift: expected {sorted(expected)}, got {sorted(adapters)}"
        )
    return adapters


MODULE_ADAPTERS = _build_adapters()
_DATABASE_READY = False


def _ensure_database_schema() -> None:
    global _DATABASE_READY
    if _DATABASE_READY:
        return
    from backend.core.db import build_engine, init_db
    from backend.core.settings import get_settings

    engine = build_engine(get_settings().database_url)
    try:
        init_db(engine)
    finally:
        engine.dispose()
    _DATABASE_READY = True


def _hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )


def _trace_reference(trace_dir: Path) -> SimpleNamespace:
    events = [
        SimpleNamespace(path=str(path))
        for path in sorted(trace_dir.glob("[0-9][0-9][0-9]_*.json"))
    ]
    return SimpleNamespace(trace_dir=trace_dir, _events=events)


def _harness_provider_snapshot(no_llm: bool) -> dict[str, Any]:
    if no_llm:
        return {
            "mode": "no_llm",
            "provider_id": "disabled",
            "model": "",
            "api_key_configured": False,
        }
    from backend.common.llm.client import LLMClient
    from backend.core.settings import get_settings

    snapshot = LLMClient(get_settings()).provider_snapshot().sanitized()
    return {"mode": "live", **snapshot}


def _check(case: dict[str, Any], actual: dict[str, Any], no_llm: bool):
    """Assert a case's declared expectations through the shared validator."""
    return validate_expected(
        actual,
        case.get("expected", {}),
        no_llm=no_llm,
        expected_llm_only=case.get("expected_llm_only", {}),
    )


def execute(
    module: str,
    case_id: str,
    *,
    no_llm: bool = False,
    quiet: bool = False,
    verbose_trace: bool = False,
) -> dict[str, str]:
    if quiet and verbose_trace:
        raise ValueError("--quiet and --verbose-trace are mutually exclusive")
    adapter = MODULE_ADAPTERS.get(module)
    if adapter is None:
        raise SystemExit(f"Unknown module {module!r}: {sorted(MODULE_ADAPTERS)}")
    case_file = TESTS_DIR / module / "cases" / f"{case_id}.json"
    if not case_file.exists():
        raise SystemExit(f"Case not found: {case_file}")
    case = json.loads(case_file.read_text(encoding="utf-8"))
    payload = _resolve_case_input(case)
    case["input"] = payload
    case["expected"] = _resolve_case_expected(case)
    _ensure_database_schema()
    run_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{case_id}"
    run_dir = RUNS_DIR / module / run_name
    _write_json(run_dir / "input" / "request.json", payload)
    (run_dir / "input" / "hash.txt").write_text(_hash(payload) + "\n", encoding="utf-8")

    started = time.monotonic()
    result: dict[str, Any] | None = None
    error: dict[str, str] | None = None
    try:
        trace_subscriber = TerminalTraceSubscriber() if verbose_trace else None
        result = adapter.invoke(case, no_llm, run_dir / "trace", trace_subscriber)
    except Exception as exc:  # the harness must persist every production failure
        error = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    duration_ms = (time.monotonic() - started) * 1000
    if result is not None:
        _write_json(run_dir / "output" / "result.json", result)
    if error is not None:
        _write_json(run_dir / "output" / "error.json", error)

    assertions = _check(case, result or {}, no_llm)
    passed, failed, skipped = assertions.passed, assertions.failed, assertions.skipped
    status = "FAIL" if error or failed else "PASS"
    manifest = {
        "schema_version": "1.0",
        "run_id": run_name,
        "module": module,
        "module_id": adapter.module_id,
        "case_id": case_id,
        "status": status,
        "duration_ms": duration_ms,
        "attempts": 1,
        "max_attempts": 1,
        "input_hash": _hash(payload),
        "provider_snapshot": _harness_provider_snapshot(no_llm),
        "input": summarize_input(payload),
        "output": summarize_output(result),
        "observability": {
            **summarize_trace(_trace_reference(run_dir / "trace")),
            "error_count": 1 if error else 0,
        },
        "checks_passed": len(passed),
        "checks_failed": len(failed),
        "checks_skipped": len(skipped),
        "recommended_path": (result or {}).get("recommended_path", ""),
        "risk_level": (result or {}).get("risk_level", ""),
        "error": error,
    }
    _write_json(run_dir / "run_manifest.json", manifest)
    if not quiet:
        observability = manifest["observability"]
        tokens = observability["tokens"]
        print(
            f"{module}/{case_id}: {status} "
            f"({duration_ms:.0f} ms, {len(passed)} passed, {len(failed)} failed, "
            f"{len(skipped)} skipped)"
        )
        print(
            f"events={observability['event_count']} "
            f"llm_calls={observability['llm_calls']} "
            f"tokens={tokens['total_tokens']} "
            f"fallbacks={observability['fallback_count']}"
        )
        print(run_dir)
        for message in failed:
            print(f"  - {message}")
    return {"status": status, "run_id": run_name}


def execute_all_modules(
    *,
    no_llm: bool = False,
    quiet: bool = False,
    verbose_trace: bool = False,
) -> list[dict[str, str]]:
    outcomes: list[dict[str, str]] = []
    for module in sorted(MODULE_ADAPTERS):
        case_dir = TESTS_DIR / module / "cases"
        case_ids = sorted(path.stem for path in case_dir.glob("*.json"))
        if not case_ids:
            outcomes.append(
                {
                    "status": "FAIL",
                    "run_id": "",
                    "module": module,
                    "error": f"No cases found in {case_dir}",
                }
            )
            continue
        for case_id in case_ids:
            outcome = execute(
                module,
                case_id,
                no_llm=no_llm,
                quiet=quiet,
                verbose_trace=verbose_trace,
            )
            outcomes.append({**outcome, "module": module, "case_id": case_id})
    return outcomes


def main() -> int:
    parser = argparse.ArgumentParser(description="AI4Law white-box test runner")
    parser.add_argument("module", choices=["all", *sorted(MODULE_ADAPTERS)])
    parser.add_argument(
        "case",
        nargs="?",
        default="all",
        help="case name without .json, or 'all' (default: all)",
    )
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--quiet", "-q", action="store_true")
    parser.add_argument(
        "--verbose-trace",
        action="store_true",
        help="print each safe Trace event summary as it is recorded",
    )
    args = parser.parse_args()
    if args.quiet and args.verbose_trace:
        parser.error("--quiet and --verbose-trace are mutually exclusive")

    if args.module == "all":
        outcomes = execute_all_modules(
            no_llm=args.no_llm,
            quiet=args.quiet,
            verbose_trace=args.verbose_trace,
        )
        failed = sum(outcome["status"] != "PASS" for outcome in outcomes)
        print(
            f"all modules: {len(outcomes) - failed} PASS, {failed} FAIL "
            f"across {len(MODULE_ADAPTERS)} modules"
        )
        for outcome in outcomes:
            if outcome["status"] != "PASS":
                print(
                    f"  - {outcome.get('module', '?')}/"
                    f"{outcome.get('case_id', '?')}: {outcome.get('error', 'FAIL')}"
                )
        return 1 if failed else 0

    if args.case == "all":
        case_dir = TESTS_DIR / args.module / "cases"
        case_ids = sorted(path.stem for path in case_dir.glob("*.json"))
        if not case_ids:
            print(f"No cases found in {case_dir}", file=sys.stderr)
            return 1
    else:
        case_ids = [args.case]
    outcomes = [
        execute(
            args.module,
            case_id,
            no_llm=args.no_llm,
            quiet=args.quiet,
            verbose_trace=args.verbose_trace,
        )
        for case_id in case_ids
    ]
    failed = sum(outcome["status"] != "PASS" for outcome in outcomes)
    print(f"{args.module}: {len(outcomes) - failed} PASS, {failed} FAIL")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
