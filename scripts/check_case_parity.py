"""Verify the committed case inventory against both test suites.

Two independent suites exercise the eleven registered modules:

* the CLI harness cases under ``backend/tests/<module>/cases/*.json``, which run
  the services in-process and assert their results;
* the developer cases in ``frontend/src/lib/dev-test-cases.ts``, which are
  submitted over real HTTP by the Developer Case Contract workflow.

Neither suite can execute the other language safely. ``config/case_inventory.json``
is the committed contract naming what each side must carry. This script verifies
the CLI side against that contract; the frontend side is verified natively by
``frontend/tests/contract/case-inventory.test.ts`` reading the same file. A drift
on either side fails its own gate without parsing source code as text.

Beyond counting, this script enforces the properties that keep assertions
meaningful:

* every ``expected`` operator is one the validator implements, so a mistyped key
  cannot masquerade as a passing assertion;
* every case declares at least ``assertion_floor`` leaf checks, so a case cannot
  decay back to a bare ``result_not_empty``;
* every ``known_defects`` entry states the field it suppresses and why.

Usage:
    uv run python scripts/check_case_parity.py
    uv run python scripts/check_case_parity.py --write   # refresh the inventory
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.tests.harness.validators import ASSERTION_OPERATORS  # noqa: E402

INVENTORY_PATH = ROOT / "config" / "case_inventory.json"
MODULE_REGISTRY_PATH = ROOT / "config" / "module_registry.json"
TESTS_DIR = ROOT / "backend" / "tests"

SCHEMA_VERSION = "1.0"

# A case carrying fewer leaf checks than this is not asserting its module's
# behaviour in any meaningful way. The floor is the weakest case currently in
# the tree, so it ratchets: it may be raised, never silently lowered.
ASSERTION_FLOOR = 8

_COUNTED_AS_LENGTH = {
    "fields_equal",
    "fields_present",
    "min_counts",
    "max_counts",
    "output_formats",
    "output_roles_contains",
    "profile_contains",
    "legal_basis_contains",
}


def count_leaf_checks(expected: dict[str, Any]) -> int:
    """Count the checks ``expected`` will produce at run time.

    Must stay in step with ``validators._apply``; ``test_case_parity`` asserts
    this by comparing against a real validator run.
    """
    total = 0
    for operator, payload in expected.items():
        if operator == "result_not_empty":
            total += 1
        elif operator == "list_contains":
            if isinstance(payload, dict):
                total += sum(
                    len(needles) for needles in payload.values() if isinstance(needles, list)
                )
        elif operator in _COUNTED_AS_LENGTH:
            if isinstance(payload, (dict, list)):
                total += len(payload)
    return total


def _registry_modules() -> dict[str, str]:
    records = json.loads(MODULE_REGISTRY_PATH.read_text(encoding="utf-8"))
    return {record["frontend_key"]: record["module_id"] for record in records}


def _case_files(module: str) -> list[Path]:
    return sorted((TESTS_DIR / module / "cases").glob("*.json"))


def case_violations(module: str, path: Path) -> list[str]:
    """Return every structural problem in one case file."""
    violations: list[str] = []
    try:
        case = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return [f"{module}/{path.name}: unparseable JSON — {exc}"]
    if not isinstance(case, dict):
        return [f"{module}/{path.name}: top level must be an object"]

    label = f"{module}/{path.stem}"
    if case.get("case_id") != path.stem:
        violations.append(
            f"{label}: case_id {case.get('case_id')!r} must match the file name"
        )
    if not case.get("description"):
        violations.append(f"{label}: description is required")
    if not isinstance(case.get("input"), dict) or not case["input"]:
        violations.append(f"{label}: input must be a non-empty object")

    expected = case.get("expected")
    if not isinstance(expected, dict) or not expected:
        violations.append(f"{label}: expected must be a non-empty object")
        expected = {}

    llm_only = case.get("expected_llm_only") or {}
    if not isinstance(llm_only, dict):
        violations.append(f"{label}: expected_llm_only must be an object")
        llm_only = {}

    for block_name, block in (("expected", expected), ("expected_llm_only", llm_only)):
        for operator in sorted(set(block) - set(ASSERTION_OPERATORS)):
            violations.append(
                f"{label}: {block_name} uses unknown operator {operator!r} "
                f"(known: {sorted(ASSERTION_OPERATORS)})"
            )

    checks = count_leaf_checks(expected)
    if checks < ASSERTION_FLOOR:
        violations.append(
            f"{label}: declares {checks} leaf checks, below the floor of {ASSERTION_FLOOR}"
        )

    for index, defect in enumerate(case.get("known_defects") or []):
        if not isinstance(defect, dict):
            violations.append(f"{label}: known_defects[{index}] must be an object")
            continue
        for key in ("field", "observed", "reason"):
            if not str(defect.get(key, "")).strip():
                violations.append(f"{label}: known_defects[{index}] is missing {key!r}")
    return violations


def observed_inventory() -> dict[str, Any]:
    """Build the inventory from what the CLI suite actually carries."""
    registry = _registry_modules()
    frontend = _frontend_case_counts()
    modules: dict[str, Any] = {}
    for module in sorted(registry):
        cases = []
        for path in _case_files(module):
            try:
                case = json.loads(path.read_text(encoding="utf-8"))
            except ValueError:
                continue
            cases.append(
                {
                    "case_id": path.stem,
                    "assertions": count_leaf_checks(case.get("expected") or {}),
                }
            )
        modules[module] = {
            "module_id": registry[module],
            "cli_cases": cases,
            "frontend_cases": frontend.get(module, 0),
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "assertion_floor": ASSERTION_FLOOR,
        "modules": modules,
    }


def _frontend_case_counts() -> dict[str, int]:
    """Read frontend declarations from the shared structured contract.

    The frontend Vitest gate imports ``DEV_TEST_CASES`` as TypeScript and checks
    these declarations against reality. Python intentionally does not guess the
    structure of a TypeScript object literal.
    """
    if not INVENTORY_PATH.exists():
        return {}
    try:
        inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    modules = inventory.get("modules")
    if not isinstance(modules, dict):
        return {}
    return {
        str(module): int(entry["frontend_cases"])
        for module, entry in modules.items()
        if isinstance(entry, dict)
        and isinstance(entry.get("frontend_cases"), int)
    }


def coverage_violations(inventory: dict[str, Any]) -> list[str]:
    """Verify both suites cover every registered module."""
    violations: list[str] = []
    registry = _registry_modules()
    frontend = _frontend_case_counts()
    if not frontend:
        violations.append(
            "frontend: case counts are absent from config/case_inventory.json"
        )

    inventoried = set(inventory.get("modules", {}))
    if inventoried != set(registry):
        missing = sorted(set(registry) - inventoried)
        extra = sorted(inventoried - set(registry))
        if missing:
            violations.append(f"inventory is missing registered modules: {missing}")
        if extra:
            violations.append(f"inventory names unregistered modules: {extra}")

    for module in sorted(registry):
        entry = inventory.get("modules", {}).get(module, {})
        if entry.get("module_id") != registry[module]:
            violations.append(
                f"{module}: inventory module_id {entry.get('module_id')!r} "
                f"drifts from the registry ({registry[module]!r})"
            )
        if not entry.get("cli_cases"):
            violations.append(f"{module}: no CLI harness case is inventoried")
        if frontend and not frontend.get(module):
            violations.append(f"{module}: no developer case in DEV_TEST_CASES")
    return violations


def inventory_violations(committed: dict[str, Any], observed: dict[str, Any]) -> list[str]:
    """Compare the committed inventory against observed reality."""
    violations: list[str] = []
    if committed.get("schema_version") != SCHEMA_VERSION:
        violations.append(
            f"inventory schema_version must be {SCHEMA_VERSION!r}, "
            f"got {committed.get('schema_version')!r}"
        )
    committed_floor = committed.get("assertion_floor")
    if committed_floor != ASSERTION_FLOOR:
        violations.append(
            f"inventory assertion_floor {committed_floor!r} drifts from "
            f"{ASSERTION_FLOOR} in check_case_parity.py"
        )

    for module, observed_entry in observed["modules"].items():
        committed_entry = committed.get("modules", {}).get(module)
        if committed_entry is None:
            violations.append(f"{module}: absent from the committed inventory")
            continue
        observed_cases = {case["case_id"]: case["assertions"] for case in observed_entry["cli_cases"]}
        committed_cases = {
            case.get("case_id"): case.get("assertions")
            for case in committed_entry.get("cli_cases", [])
        }
        for case_id in sorted(set(observed_cases) - set(committed_cases)):
            violations.append(f"{module}/{case_id}: present on disk, absent from the inventory")
        for case_id in sorted(set(committed_cases) - set(observed_cases)):
            violations.append(f"{module}/{case_id}: inventoried but absent from disk")
        for case_id in sorted(set(observed_cases) & set(committed_cases)):
            if observed_cases[case_id] != committed_cases[case_id]:
                violations.append(
                    f"{module}/{case_id}: {observed_cases[case_id]} leaf checks on disk, "
                    f"inventory records {committed_cases[case_id]} — assertions changed"
                )

        observed_frontend = observed_entry.get("frontend_cases")
        committed_frontend = committed_entry.get("frontend_cases")
        if observed_frontend != committed_frontend:
            violations.append(
                f"{module}: frontend_cases is {observed_frontend!r} in "
                f"the structured contract, inventory records {committed_frontend!r}"
            )
    return violations


def collect_violations() -> list[str]:
    violations: list[str] = []
    registry = _registry_modules()
    for module in sorted(registry):
        for path in _case_files(module):
            violations.extend(case_violations(module, path))

    observed = observed_inventory()
    violations.extend(coverage_violations(observed))
    if not INVENTORY_PATH.exists():
        violations.append(
            f"{INVENTORY_PATH.relative_to(ROOT)} is absent; "
            "run scripts/check_case_parity.py --write"
        )
        return violations
    try:
        committed = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    except ValueError as exc:
        violations.append(f"{INVENTORY_PATH.relative_to(ROOT)}: unparseable JSON — {exc}")
        return violations
    violations.extend(inventory_violations(committed, observed))
    return violations


def write_inventory() -> Path:
    inventory = observed_inventory()
    INVENTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    INVENTORY_PATH.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return INVENTORY_PATH


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="regenerate config/case_inventory.json from the cases on disk",
    )
    args = parser.parse_args()

    if args.write:
        path = write_inventory()
        print(f"Wrote {path.relative_to(ROOT)}")
        return 0

    violations = collect_violations()
    if violations:
        print("Case parity check failed:")
        for violation in violations:
            print(f"- {violation}")
        return 1

    observed = observed_inventory()
    case_count = sum(len(entry["cli_cases"]) for entry in observed["modules"].values())
    assertions = sum(
        case["assertions"]
        for entry in observed["modules"].values()
        for case in entry["cli_cases"]
    )
    frontend_total = sum(_frontend_case_counts().values())
    print(
        f"Case parity check passed ({len(observed['modules'])} modules, "
        f"{case_count} CLI cases carrying {assertions} leaf checks, "
        f"{frontend_total} developer cases)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
