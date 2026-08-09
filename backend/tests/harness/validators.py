"""Declarative strong assertions for harness case files.

The assertion vocabulary is defined here and nowhere else. A case file may only
use the operators registered in ``ASSERTION_OPERATORS``; an unknown operator is
a hard failure rather than a silently ignored key, because a silently ignored
key is indistinguishable from a passing assertion.

Operators address result fields by path so that one small vocabulary covers
every module instead of a per-module key list:

    ``risk_level``                  scalar at the top level
    ``need_assessment.dpia_required``   nested scalar
    ``chapters[].title``            project ``title`` over every chapter

A path that does not resolve is a failure, not a skip: it means the case
references a field the module no longer produces, which is exactly the drift
this module exists to catch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any, Callable

_MISSING = object()


@dataclass
class AssertionResult:
    """Outcome of validating one case."""

    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failed


def resolve_path(data: Any, path: str) -> Any:
    """Return the value at ``path`` inside ``data``, or ``_MISSING``.

    ``key[]`` projects the remainder of the path over every list element.
    Elements for which the remainder does not resolve are dropped, so a
    projection over a partially shaped list yields the values that do exist.
    """
    if not path:
        return data
    part, _, rest = path.partition(".")
    if part.endswith("[]"):
        key = part[:-2]
        if key:
            if not isinstance(data, dict) or key not in data:
                return _MISSING
            data = data[key]
        if not isinstance(data, list):
            return _MISSING
        projected = [resolve_path(item, rest) for item in data]
        return [value for value in projected if value is not _MISSING]
    if not isinstance(data, dict) or part not in data:
        return _MISSING
    return resolve_path(data[part], rest)


def _describe(value: Any, limit: int = 60) -> str:
    if isinstance(value, str) and len(value) > limit:
        return f"{value[:limit]}..."
    if isinstance(value, list) and len(value) > 3:
        return f"[{len(value)} items]"
    return repr(value)


def _countable(value: Any) -> int | None:
    """Interpret a resolved value as a count.

    Strings are deliberately NOT countable: `min_counts` on a string would
    measure its characters, which is never the assertion a case author means.
    Use `fields_equal` or `list_contains` for string fields instead.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, (list, dict)):
        return len(value)
    return None


def _require_mapping(operator: str, payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError(f"{operator} expects an object of path -> expectation")
    return payload


def _op_result_not_empty(actual: dict[str, Any], payload: Any) -> list[tuple[bool, str]]:
    """Floor check: the module returned at least one populated field.

    Deliberately not defined in terms of ``report_path``/``output_files``:
    ``diagnosis`` returns a decision object with neither, so keying the floor
    on report artefacts would make it unusable for a whole module.
    """
    if payload is not True:
        raise TypeError("result_not_empty only accepts true")
    populated = sorted(
        key
        for key, value in actual.items()
        if value not in (None, "", [], {}, 0, False)
    )
    return [
        (bool(populated), f"result_not_empty: {len(populated)} populated field(s)")
    ]


def _op_fields_equal(actual: dict[str, Any], payload: Any) -> list[tuple[bool, str]]:
    checks: list[tuple[bool, str]] = []
    for path, expected in _require_mapping("fields_equal", payload).items():
        value = resolve_path(actual, path)
        if value is _MISSING:
            checks.append((False, f"fields_equal[{path}]: path absent from result"))
            continue
        checks.append(
            (
                value == expected,
                f"fields_equal[{path}]: expected {_describe(expected)}, got {_describe(value)}",
            )
        )
    return checks


def _op_min_counts(actual: dict[str, Any], payload: Any) -> list[tuple[bool, str]]:
    checks: list[tuple[bool, str]] = []
    for path, minimum in _require_mapping("min_counts", payload).items():
        value = resolve_path(actual, path)
        if value is _MISSING:
            checks.append((False, f"min_counts[{path}]: path absent from result"))
            continue
        count = _countable(value)
        if count is None:
            checks.append(
                (False, f"min_counts[{path}]: {_describe(value)} is not countable")
            )
            continue
        checks.append(
            (count >= minimum, f"min_counts[{path}]: expected >= {minimum}, got {count}")
        )
    return checks


def _op_max_counts(actual: dict[str, Any], payload: Any) -> list[tuple[bool, str]]:
    checks: list[tuple[bool, str]] = []
    for path, maximum in _require_mapping("max_counts", payload).items():
        value = resolve_path(actual, path)
        if value is _MISSING:
            checks.append((False, f"max_counts[{path}]: path absent from result"))
            continue
        count = _countable(value)
        if count is None:
            checks.append(
                (False, f"max_counts[{path}]: {_describe(value)} is not countable")
            )
            continue
        checks.append(
            (count <= maximum, f"max_counts[{path}]: expected <= {maximum}, got {count}")
        )
    return checks


def _op_list_contains(actual: dict[str, Any], payload: Any) -> list[tuple[bool, str]]:
    checks: list[tuple[bool, str]] = []
    for path, needles in _require_mapping("list_contains", payload).items():
        if not isinstance(needles, list):
            raise TypeError(f"list_contains[{path}] expects a list of substrings")
        value = resolve_path(actual, path)
        if value is _MISSING:
            checks.append((False, f"list_contains[{path}]: path absent from result"))
            continue
        if not isinstance(value, list):
            checks.append(
                (False, f"list_contains[{path}]: {_describe(value)} is not a list")
            )
            continue
        haystack = [item for item in value if isinstance(item, str)]
        for needle in needles:
            found = any(needle in item for item in haystack)
            checks.append(
                (
                    found,
                    f"list_contains[{path}]: {needle!r} in {len(haystack)} entries={found}",
                )
            )
    return checks


def _op_list_excludes(actual: dict[str, Any], payload: Any) -> list[tuple[bool, str]]:
    checks: list[tuple[bool, str]] = []
    for path, needles in _require_mapping("list_excludes", payload).items():
        if not isinstance(needles, list):
            raise TypeError(f"list_excludes[{path}] expects a list of substrings")
        value = resolve_path(actual, path)
        if value is _MISSING:
            checks.append((False, f"list_excludes[{path}]: path absent from result"))
            continue
        if not isinstance(value, list):
            checks.append((False, f"list_excludes[{path}]: {_describe(value)} is not a list"))
            continue
        haystack = [item for item in value if isinstance(item, str)]
        for needle in needles:
            found = any(needle in item for item in haystack)
            checks.append(
                (
                    not found,
                    f"list_excludes[{path}]: {needle!r} absent from {len(haystack)} entries={not found}",
                )
            )
    return checks


def _op_output_formats(actual: dict[str, Any], payload: Any) -> list[tuple[bool, str]]:
    if not isinstance(payload, list):
        raise TypeError("output_formats expects a list of extensions")
    output_files = actual.get("output_files")
    if not isinstance(output_files, dict):
        return [(False, "output_formats: result carries no output_files mapping")]
    suffixes = {
        PurePosixPath(str(path)).suffix.lstrip(".").lower()
        for path in output_files.values()
        if isinstance(path, str)
    }
    return [
        (
            extension.lower() in suffixes,
            f"output_formats[{extension}]: present in {sorted(suffixes)}",
        )
        for extension in payload
    ]


def _op_output_roles(actual: dict[str, Any], payload: Any) -> list[tuple[bool, str]]:
    if not isinstance(payload, list):
        raise TypeError("output_roles_contains expects a list of role names")
    output_files = actual.get("output_files")
    if not isinstance(output_files, dict):
        return [(False, "output_roles_contains: result carries no output_files mapping")]
    roles = set(output_files)
    return [
        (role in roles, f"output_roles_contains[{role}]: present in {sorted(roles)}")
        for role in payload
    ]


def _op_profile_contains(actual: dict[str, Any], payload: Any) -> list[tuple[bool, str]]:
    """Readable sugar for ``fields_equal`` scoped to the extracted profile."""
    scoped = {
        f"profile.{key}": value
        for key, value in _require_mapping("profile_contains", payload).items()
    }
    return _op_fields_equal(actual, scoped)


def _op_legal_basis_contains(
    actual: dict[str, Any], payload: Any
) -> list[tuple[bool, str]]:
    """Readable sugar for ``list_contains`` scoped to ``legal_basis``."""
    return _op_list_contains(actual, {"legal_basis": payload})


def _op_fields_present(actual: dict[str, Any], payload: Any) -> list[tuple[bool, str]]:
    """Assert every listed key exists at the top level of the result dict."""
    if not isinstance(payload, list):
        raise TypeError("fields_present expects a list of field names")
    return [
        (key in actual, f"fields_present[{key}]: {'present' if key in actual else 'absent'}")
        for key in payload
    ]


Operator = Callable[[dict[str, Any], Any], list[tuple[bool, str]]]

ASSERTION_OPERATORS: dict[str, Operator] = {
    "result_not_empty": _op_result_not_empty,
    "fields_equal": _op_fields_equal,
    "fields_present": _op_fields_present,
    "min_counts": _op_min_counts,
    "max_counts": _op_max_counts,
    "list_contains": _op_list_contains,
    "list_excludes": _op_list_excludes,
    "output_formats": _op_output_formats,
    "output_roles_contains": _op_output_roles,
    "profile_contains": _op_profile_contains,
    "legal_basis_contains": _op_legal_basis_contains,
}


def unknown_operators(expected: dict[str, Any]) -> list[str]:
    """Return the operator names in ``expected`` that this module cannot honour."""
    return sorted(set(expected) - set(ASSERTION_OPERATORS))


def _apply(
    actual: dict[str, Any], expected: dict[str, Any], outcome: AssertionResult
) -> None:
    for operator, payload in expected.items():
        handler = ASSERTION_OPERATORS.get(operator)
        if handler is None:
            outcome.failed.append(
                f"{operator}: unknown assertion operator "
                f"(known: {sorted(ASSERTION_OPERATORS)})"
            )
            continue
        try:
            checks = handler(actual, payload)
        except TypeError as exc:
            outcome.failed.append(f"{operator}: malformed expectation — {exc}")
            continue
        for ok, message in checks:
            (outcome.passed if ok else outcome.failed).append(message)


def validate_expected(
    actual: dict[str, Any],
    expected: dict[str, Any],
    *,
    no_llm: bool,
    expected_llm_only: dict[str, Any] | None = None,
) -> AssertionResult:
    """Assert ``expected`` against ``actual``.

    ``expected`` is asserted unconditionally, including rule-derived fields such
    as a diagnosis ``risk_level``, which are deterministic without a model.
    ``expected_llm_only`` holds assertions that genuinely depend on generated
    prose and is recorded as skipped when ``no_llm`` is set.
    """
    outcome = AssertionResult()
    _apply(actual, expected, outcome)

    llm_only = expected_llm_only or {}
    if no_llm:
        outcome.skipped.extend(
            f"{operator}: skipped (no_llm mode)" for operator in sorted(llm_only)
        )
    else:
        _apply(actual, llm_only, outcome)
    return outcome
