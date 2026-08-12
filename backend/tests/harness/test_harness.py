from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.common.trace.events import RunEvent
from backend.common.trace.recorder import TraceRecorder
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
    }

    assert set(runner.MODULE_ADAPTERS) == set(expected)
    for alias, adapter in runner.MODULE_ADAPTERS.items():
        assert adapter.module_id == expected[alias]["module_id"]
        assert adapter.implementation_package == expected[alias]["implementation_package"]


def test_runner_does_not_restore_legacy_module_imports() -> None:
    source = Path(runner.__file__).read_text(encoding="utf-8")
    assert "backend.modules" not in source


def test_shared_scenario_replaces_inline_case_input(tmp_path: Path, monkeypatch) -> None:
    scenario = tmp_path / "benchmarks" / "cases" / "us_14117" / "red" / "scenario.json"
    scenario.parent.mkdir(parents=True)
    scenario.write_text(
        json.dumps({"request": {"company_name": "GeneGuard生物科技公司"}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)

    resolved = runner._resolve_case_input(
        {"scenario_path": "benchmarks/cases/us_14117/red/scenario.json"}
    )

    assert resolved == {"company_name": "GeneGuard生物科技公司"}


def test_shared_scenario_rejects_a_second_inline_fact_source(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)

    with pytest.raises(ValueError, match="must not define both"):
        runner._resolve_case_input({"scenario_path": "scenario.json", "input": {"value": 1}})


def test_shared_expected_reads_harness_assertions(tmp_path: Path, monkeypatch) -> None:
    expected = tmp_path / "benchmarks" / "cases" / "demo" / "expected.json"
    expected.parent.mkdir(parents=True)
    expected.write_text(json.dumps({"harness": {"result_not_empty": True}}), encoding="utf-8")
    monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)

    assert runner._resolve_case_expected(
        {"expected_path": "benchmarks/cases/demo/expected.json"}
    ) == {"result_not_empty": True}


def test_execute_failure_writes_error_json_and_failed_manifest(
    tmp_path: Path, monkeypatch
) -> None:
    tests_dir = tmp_path / "tests"
    case_dir = tests_dir / "failure" / "cases"
    case_dir.mkdir(parents=True)
    (case_dir / "01_crash.json").write_text(
        json.dumps({"input": {"value": 1}, "expected": {}}), encoding="utf-8"
    )

    def fail(_case, _no_llm, _trace_dir, _trace_subscriber):
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
    assert manifest["schema_version"] == "1.0"
    assert manifest["status"] == "FAIL"
    assert manifest["provider_snapshot"]["mode"] == "no_llm"
    assert manifest["input"]["fields"] == ["value"]
    assert manifest["output"]["artifacts"] == []
    assert manifest["observability"]["tokens"]["total_tokens"] == 0


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


def test_execute_all_modules_runs_every_registered_case(tmp_path, monkeypatch) -> None:
    calls: list[tuple[str, str, bool, bool, bool]] = []
    adapters = {
        "alpha": object(),
        "beta": object(),
    }
    for module, cases in {"alpha": ["01_a", "02_b"], "beta": ["01_c"]}.items():
        case_dir = tmp_path / module / "cases"
        case_dir.mkdir(parents=True)
        for case_id in cases:
            (case_dir / f"{case_id}.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(runner, "TESTS_DIR", tmp_path)
    monkeypatch.setattr(runner, "MODULE_ADAPTERS", adapters)
    monkeypatch.setattr(
        runner,
        "execute",
        lambda module, case_id, *, no_llm, quiet, verbose_trace: (
            calls.append((module, case_id, no_llm, quiet, verbose_trace))
            or {"status": "PASS", "run_id": f"{module}-{case_id}"}
        ),
    )

    outcomes = runner.execute_all_modules(
        no_llm=True,
        quiet=True,
        verbose_trace=False,
    )

    assert len(outcomes) == 3
    assert calls == [
        ("alpha", "01_a", True, True, False),
        ("alpha", "02_b", True, True, False),
        ("beta", "01_c", True, True, False),
    ]


def test_terminal_trace_subscriber_prints_safe_event_summary(capsys) -> None:
    subscriber = runner.TerminalTraceSubscriber()
    subscriber(
        RunEvent(
            task_id="task-1",
            seq=4,
            event_type="tool_result",
            timestamp="2026-08-11T11:21:05+00:00",
            summary="LLM 调用完成",
            detail={
                "tool": "llm_chat",
                "duration_ms": 5800,
                "usage": {
                    "prompt_tokens": 1000,
                    "completion_tokens": 240,
                    "total_tokens": 1240,
                },
                "authorization": "Bearer secret-token",
                "prompt": "private contract text",
            },
        )
    )

    output = capsys.readouterr().err
    assert "#004" in output
    assert "tool_result" in output
    assert "llm_chat done" in output
    assert "1240 tokens" in output
    assert "secret-token" not in output
    assert "private contract text" not in output


def test_verbose_trace_subscriber_observes_same_order_as_persisted_trace(
    tmp_path: Path,
    capsys,
) -> None:
    recorder = TraceRecorder(tmp_path / "trace", task_id="task-1")
    recorder.subscribe(runner.TerminalTraceSubscriber())

    recorder.record("status", {"summary": "开始"})
    recorder.record("warning", {"summary": "需要复核"})
    recorder.record("final", {"summary": "完成"})
    recorder.write_manifest()

    output = capsys.readouterr().err
    assert output.index("#001") < output.index("#002") < output.index("#003")
    manifest = json.loads(
        (tmp_path / "trace" / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["event_count"] == 3
    trace_lines = [line for line in output.splitlines() if line.strip()]
    assert len(trace_lines) == manifest["event_count"]


def test_execute_rejects_quiet_and_verbose_trace_together() -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        runner.execute(
            "diagnosis",
            "01_scc_path",
            no_llm=True,
            quiet=True,
            verbose_trace=True,
        )


def test_review_no_llm_settings_override_environment_keys(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AI4LAW_LLM_PROVIDER", "siliconflow")
    monkeypatch.setenv("AI4LAW_SILICONFLOW_API_KEY", "must-not-be-used")

    settings = runner._review_harness_settings(tmp_path, no_llm=True)

    assert settings.resolved_llm_provider == "none"
    assert settings.resolved_llm_api_key is None
