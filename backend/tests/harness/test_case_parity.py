"""Mutation tests for the case parity gate.

A gate is only worth its runtime if it fails on the drift it claims to catch.
Every test here breaks one property and asserts the gate reports it.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

from backend.tests.harness import runner, validators

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "check_case_parity.py"


def _load_gate():
    spec = importlib.util.spec_from_file_location("check_case_parity", _SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _load_gate()


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _sound_case(case_id: str = "01_demo") -> dict[str, Any]:
    return {
        "case_id": case_id,
        "description": "a case carrying enough checks to clear the floor",
        "input": {"company_name": "示例企业"},
        "expected": {
            "result_not_empty": True,
            "fields_equal": {"risk_level": "LOW", "route_type": "scc_filing"},
            "min_counts": {"chapters": 4, "output_files": 2},
            "output_formats": ["md", "docx"],
            "output_roles_contains": ["markdown", "docx"],
        },
    }


# ── the live tree must satisfy its own gate ─────────────────────────────────


def test_committed_tree_passes_the_gate() -> None:
    assert gate.collect_violations() == []


def test_python_gate_reads_frontend_counts_from_structured_inventory() -> None:
    counts = gate._frontend_case_counts()

    assert sum(counts.values()) == 27
    assert counts["cpra"] == 3
    assert counts["review"] == 2
    assert counts["us_14117"] == 3


def test_case_catalog_has_unique_registered_cases_and_real_sources() -> None:
    assert gate.case_catalog_violations() == []


def test_case_catalog_rejects_unknown_classification(monkeypatch) -> None:
    catalog = json.loads(gate.CASE_CATALOG_PATH.read_text(encoding="utf-8"))
    catalog["cases"][0]["classification"] = "invented"
    monkeypatch.setattr(gate, "_case_catalog", lambda: catalog)

    violations = gate.case_catalog_violations()

    assert any("classification" in item for item in violations)


def test_leaf_check_counter_matches_the_validator() -> None:
    """The inventory's arithmetic must equal what the validator really emits.

    Counting statically and asserting at run time are two implementations of one
    rule; if they diverge, the inventory's numbers stop meaning anything.
    """
    expected = _sound_case()["expected"]
    # A result satisfying every declared path, so no check is dropped.
    actual = {
        "risk_level": "LOW",
        "route_type": "scc_filing",
        "chapters": [1, 2, 3, 4],
        "output_files": {"markdown": "a/b.md", "docx": "a/b.docx"},
        "report_path": "a/b.md",
    }
    outcome = validators.validate_expected(actual, expected, no_llm=True)

    assert gate.count_leaf_checks(expected) == len(outcome.passed) + len(outcome.failed)
    assert outcome.ok


# ── per-case structural properties ─────────────────────────────────────────


def test_unknown_operator_is_reported(tmp_path: Path) -> None:
    case = _sound_case()
    case["expected"]["recomended_path"] = "scc_or_certification"  # typo
    _write(tmp_path / "01_demo.json", case)

    violations = gate.case_violations("demo", tmp_path / "01_demo.json")

    assert any("unknown operator" in item for item in violations)


def test_assertion_floor_is_enforced(tmp_path: Path) -> None:
    case = _sound_case()
    case["expected"] = {"result_not_empty": True}
    _write(tmp_path / "01_demo.json", case)

    violations = gate.case_violations("demo", tmp_path / "01_demo.json")

    assert any("below the floor" in item for item in violations)


def test_case_id_must_match_the_file_name(tmp_path: Path) -> None:
    _write(tmp_path / "01_demo.json", _sound_case(case_id="something_else"))

    violations = gate.case_violations("demo", tmp_path / "01_demo.json")

    assert any("must match the file name" in item for item in violations)


def test_missing_description_and_input_are_reported(tmp_path: Path) -> None:
    case = _sound_case()
    case.pop("description")
    case["input"] = {}
    _write(tmp_path / "01_demo.json", case)

    violations = gate.case_violations("demo", tmp_path / "01_demo.json")

    assert any("description is required" in item for item in violations)
    assert any("input must be a non-empty object" in item for item in violations)


def test_shared_scenario_is_accepted_as_the_only_input_source(tmp_path: Path, monkeypatch) -> None:
    scenario = tmp_path / "benchmarks" / "cases" / "demo" / "scenario.json"
    _write(scenario, {"request": {"company_name": "示例企业"}})
    case = _sound_case()
    case.pop("input")
    case["scenario_path"] = "benchmarks/cases/demo/scenario.json"
    case_path = tmp_path / "01_demo.json"
    _write(case_path, case)
    monkeypatch.setattr(gate, "ROOT", tmp_path)

    assert gate.case_violations("demo", case_path) == []


def test_shared_expected_is_accepted_as_the_only_assertion_source(tmp_path: Path, monkeypatch) -> None:
    expected_path = tmp_path / "benchmarks" / "cases" / "demo" / "expected.json"
    _write(expected_path, {"harness": _sound_case()["expected"]})
    case = _sound_case()
    case.pop("expected")
    case["expected_path"] = "benchmarks/cases/demo/expected.json"
    case_path = tmp_path / "01_demo.json"
    _write(case_path, case)
    monkeypatch.setattr(gate, "ROOT", tmp_path)

    assert gate.case_violations("demo", case_path) == []


def test_unparseable_case_is_reported(tmp_path: Path) -> None:
    (tmp_path / "01_demo.json").write_text("{not json", encoding="utf-8")

    violations = gate.case_violations("demo", tmp_path / "01_demo.json")

    assert any("unparseable JSON" in item for item in violations)


def test_known_defect_must_state_field_observed_and_reason(tmp_path: Path) -> None:
    case = _sound_case()
    case["known_defects"] = [{"field": "module_validation.is_correct"}]
    _write(tmp_path / "01_demo.json", case)

    violations = gate.case_violations("demo", tmp_path / "01_demo.json")

    assert any("missing 'observed'" in item for item in violations)
    assert any("missing 'reason'" in item for item in violations)


def test_sound_case_yields_no_violations(tmp_path: Path) -> None:
    _write(tmp_path / "01_demo.json", _sound_case())

    assert gate.case_violations("demo", tmp_path / "01_demo.json") == []


# ── inventory drift ────────────────────────────────────────────────────────


def test_added_cli_case_without_inventory_refresh_fails(monkeypatch) -> None:
    observed = gate.observed_inventory()
    committed = json.loads(json.dumps(observed))
    observed["modules"]["diagnosis"]["cli_cases"].append(
        {"case_id": "04_new", "assertions": 12}
    )

    violations = gate.inventory_violations(committed, observed)

    assert any("04_new" in item for item in violations)


def test_weakened_assertions_without_inventory_refresh_fails() -> None:
    observed = gate.observed_inventory()
    committed = json.loads(json.dumps(observed))
    observed["modules"]["diagnosis"]["cli_cases"][0]["assertions"] -= 4

    violations = gate.inventory_violations(committed, observed)

    assert any("assertions" in item for item in violations)


def test_frontend_case_count_drift_fails() -> None:
    observed = gate.observed_inventory()
    committed = json.loads(json.dumps(observed))
    committed["modules"]["cpra"]["frontend_cases"] = 99

    violations = gate.inventory_violations(committed, observed)

    assert any("frontend_cases" in item for item in violations)


def test_schema_version_drift_fails() -> None:
    observed = gate.observed_inventory()
    committed = json.loads(json.dumps(observed))
    committed["schema_version"] = "0.9"

    violations = gate.inventory_violations(committed, observed)

    assert any("schema_version" in item for item in violations)


# ── coverage ───────────────────────────────────────────────────────────────


def test_every_registered_module_must_appear(monkeypatch) -> None:
    inventory = gate.observed_inventory()
    inventory["modules"].pop("tia")

    violations = gate.coverage_violations(inventory)

    assert any("tia" in item for item in violations)


def test_module_without_cli_cases_is_reported() -> None:
    inventory = gate.observed_inventory()
    inventory["modules"]["tia"]["cli_cases"] = []

    violations = gate.coverage_violations(inventory)

    assert any("tia" in item for item in violations)


def test_gate_covers_exactly_the_registered_modules() -> None:
    """The gate's module set is the product registry's, not a private list."""
    registry = json.loads(
        (gate.MODULE_REGISTRY_PATH).read_text(encoding="utf-8")
    )
    expected = {record["frontend_key"] for record in registry}

    assert set(gate.observed_inventory()["modules"]) == expected
    assert set(runner.MODULE_ADAPTERS) == expected
