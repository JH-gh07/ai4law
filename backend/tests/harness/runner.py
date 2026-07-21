"""Deterministic white-box runner for the registered report modules."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.common.trace.recorder import TraceRecorder


RUNS_DIR = REPO_ROOT / "runs"
TESTS_DIR = REPO_ROOT / "backend" / "tests"


class _DisabledLLM:
    enabled = False
    _enabled = False


class _DisabledLegalService:
    enabled = False


Invoke = Callable[[dict[str, Any], bool, Path], dict[str, Any]]


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
    "scc": (
        "cn.scc_review",
        "backend.domains.cn.scc_review",
        "SCCRequest",
        "SCCService",
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
    if alias in {"scc", "pipia", "dpia"}:
        return service_class(llm_client=None)
    return service_class(llm_client=_DisabledLLM())


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
    def invoke(case: dict[str, Any], no_llm: bool, trace_dir: Path) -> dict[str, Any]:
        schema_module = importlib.import_module(f"{package}.schema")
        service_module = importlib.import_module(f"{package}.service")
        request_class = getattr(schema_module, request_name)
        service_class = getattr(service_module, service_name)
        payload = request_class.model_validate(case["input"])
        service = _make_service(alias, service_class, no_llm)
        recorder = TraceRecorder(trace_dir, task_id=f"harness-{alias}")
        result = service.generate_report(payload, trace=recorder)
        recorder.write_manifest()
        return _serialize_result(result)

    return invoke


def _diagnosis_invoke(
    case: dict[str, Any], no_llm: bool, trace_dir: Path
) -> dict[str, Any]:
    package = "backend.domains.cn.transfer_diagnosis"
    answers_class = getattr(importlib.import_module(f"{package}.schema"), "DiagnosisAnswers")
    service_class = getattr(importlib.import_module(f"{package}.service"), "DiagnosisService")
    answers = answers_class.model_validate(case["input"]["answers"])
    service = service_class(llm_client=_DisabledLLM()) if no_llm else service_class()
    recorder = TraceRecorder(trace_dir, task_id="harness-diagnosis")
    result = service.evaluate(answers, trace=recorder)
    recorder.write_manifest()
    return _serialize_result(result)


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
    expected = set(product_registry) - {"review"}
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


def _check(
    actual: dict[str, Any], expected: dict[str, Any], no_llm: bool
) -> tuple[list[str], list[str]]:
    passed: list[str] = []
    failed: list[str] = []
    for field, expected_value in expected.items():
        if field in {"risk_level", "conclusion_source"} and no_llm:
            continue
        if field == "result_not_empty" and expected_value is True:
            ok = bool(actual.get("report_path") or actual.get("task_id") or actual)
        elif field == "profile_contains" and isinstance(expected_value, dict):
            profile = actual.get("profile") or {}
            for key, value in expected_value.items():
                ok = profile.get(key) == value
                (passed if ok else failed).append(
                    f"profile.{key} expected {value!r}, got {profile.get(key)!r}"
                )
            continue
        elif field == "legal_basis_contains":
            legal_basis = actual.get("legal_basis") or []
            for value in expected_value:
                ok = any(value in item for item in legal_basis)
                (passed if ok else failed).append(f"legal_basis contains {value!r}")
            continue
        else:
            ok = actual.get(field) == expected_value
        message = f"{field} expected {expected_value!r}, got {actual.get(field)!r}"
        (passed if ok else failed).append(message)
    return passed, failed


def execute(
    module: str, case_id: str, *, no_llm: bool = False, quiet: bool = False
) -> dict[str, str]:
    adapter = MODULE_ADAPTERS.get(module)
    if adapter is None:
        raise SystemExit(f"Unknown module {module!r}: {sorted(MODULE_ADAPTERS)}")
    case_file = TESTS_DIR / module / "cases" / f"{case_id}.json"
    if not case_file.exists():
        raise SystemExit(f"Case not found: {case_file}")
    case = json.loads(case_file.read_text(encoding="utf-8"))
    payload = case.get("input", {})
    _ensure_database_schema()
    run_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{case_id}"
    run_dir = RUNS_DIR / module / run_name
    _write_json(run_dir / "input" / "request.json", payload)
    (run_dir / "input" / "hash.txt").write_text(_hash(payload) + "\n", encoding="utf-8")

    started = time.monotonic()
    result: dict[str, Any] | None = None
    error: dict[str, str] | None = None
    try:
        result = adapter.invoke(case, no_llm, run_dir / "trace")
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

    passed, failed = _check(result or {}, case.get("expected", {}), no_llm)
    status = "FAIL" if error or failed else "PASS"
    manifest = {
        "run_id": run_name,
        "module": module,
        "module_id": adapter.module_id,
        "case_id": case_id,
        "status": status,
        "duration_ms": duration_ms,
        "input_hash": _hash(payload),
        "checks_passed": len(passed),
        "checks_failed": len(failed),
        "recommended_path": (result or {}).get("recommended_path", ""),
        "risk_level": (result or {}).get("risk_level", ""),
        "error": error,
    }
    _write_json(run_dir / "run_manifest.json", manifest)
    if not quiet:
        print(
            f"{module}/{case_id}: {status} "
            f"({duration_ms:.0f} ms, {len(passed)} passed, {len(failed)} failed)"
        )
        print(run_dir)
        for message in failed:
            print(f"  - {message}")
    return {"status": status, "run_id": run_name}


def main() -> int:
    parser = argparse.ArgumentParser(description="AI4Law white-box test runner")
    parser.add_argument("module", choices=sorted(MODULE_ADAPTERS))
    parser.add_argument("case", help="case name without .json, or 'all'")
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--quiet", "-q", action="store_true")
    args = parser.parse_args()

    if args.case == "all":
        case_dir = TESTS_DIR / args.module / "cases"
        case_ids = sorted(path.stem for path in case_dir.glob("*.json"))
        if not case_ids:
            print(f"No cases found in {case_dir}", file=sys.stderr)
            return 1
    else:
        case_ids = [args.case]
    outcomes = [
        execute(args.module, case_id, no_llm=args.no_llm, quiet=args.quiet)
        for case_id in case_ids
    ]
    failed = sum(outcome["status"] != "PASS" for outcome in outcomes)
    print(f"{args.module}: {len(outcomes) - failed} PASS, {failed} FAIL")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
