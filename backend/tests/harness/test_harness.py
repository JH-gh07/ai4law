from __future__ import annotations

import json
from pathlib import Path

from backend.tests.harness import runner, viewer


def test_module_adapters_match_authoritative_registry() -> None:
    registry = json.loads(
        (runner.REPO_ROOT / "config" / "module_registry.json").read_text(
            encoding="utf-8"
        )
    )
    expected = {
        item["frontend_key"]: item
        for item in registry
        if item["frontend_key"] != "review"
    }

    assert set(runner.MODULE_ADAPTERS) == set(expected)
    for alias, adapter in runner.MODULE_ADAPTERS.items():
        assert adapter.module_id == expected[alias]["module_id"]
        assert adapter.implementation_package == expected[alias]["implementation_package"]


def test_runner_does_not_restore_legacy_module_imports() -> None:
    source = Path(runner.__file__).read_text(encoding="utf-8")
    assert "backend.modules" not in source


def test_execute_failure_writes_error_json_and_failed_manifest(
    tmp_path: Path, monkeypatch
) -> None:
    tests_dir = tmp_path / "tests"
    case_dir = tests_dir / "failure" / "cases"
    case_dir.mkdir(parents=True)
    (case_dir / "01_crash.json").write_text(
        json.dumps({"input": {"value": 1}, "expected": {}}), encoding="utf-8"
    )

    def fail(_case, _no_llm, _trace_dir):
        raise RuntimeError("deliberate harness failure")

    monkeypatch.setattr(runner, "TESTS_DIR", tests_dir)
    monkeypatch.setattr(runner, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setitem(
        runner.MODULE_ADAPTERS,
        "failure",
        runner.ModuleAdapter(
            alias="failure",
            module_id="test.failure",
            implementation_package="backend.domains.test.failure",
            invoke=fail,
        ),
    )

    outcome = runner.execute("failure", "01_crash", no_llm=True, quiet=True)

    assert outcome["status"] == "FAIL"
    run_dir = runner.RUNS_DIR / "failure" / outcome["run_id"]
    error = json.loads((run_dir / "output" / "error.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert error["type"] == "RuntimeError"
    assert "deliberate harness failure" in error["message"]
    assert manifest["status"] == "FAIL"


def test_viewer_loads_cross_module_success_and_error_runs(
    tmp_path: Path, monkeypatch
) -> None:
    runs_dir = tmp_path / "runs"
    successful = runs_dir / "assessment" / "run-success"
    failed = runs_dir / "tia" / "run-failed"
    for directory in (successful, failed):
        (directory / "output").mkdir(parents=True)

    (successful / "run_manifest.json").write_text(
        json.dumps({"run_id": "run-success", "module": "assessment", "status": "PASS"}),
        encoding="utf-8",
    )
    (successful / "output" / "result.json").write_text(
        json.dumps({"risk_level": "LOW"}), encoding="utf-8"
    )
    (failed / "run_manifest.json").write_text(
        json.dumps({"run_id": "run-failed", "module": "tia", "status": "FAIL"}),
        encoding="utf-8",
    )
    (failed / "output" / "error.json").write_text(
        json.dumps({"type": "ValueError", "message": "bad input"}), encoding="utf-8"
    )
    monkeypatch.setattr(viewer, "RUNS_DIR", runs_dir)

    success_data = viewer.load_run("run-success")
    failed_data = viewer.load_run("run-failed")

    assert success_data is not None
    assert success_data["result"]["risk_level"] == "LOW"
    assert success_data["error"] is None
    assert failed_data is not None
    assert failed_data["result"] is None
    assert failed_data["error"]["type"] == "ValueError"
    assert viewer.load_run("missing") is None
    assert viewer.diff_runs(success_data, failed_data)["status"] == ("PASS", "FAIL")
