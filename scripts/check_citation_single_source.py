"""Static guard for the report citation single-source pipeline.

Production code must resolve citation syntax through ``apply_citation_pipeline``
with a per-report registry. The old helpers remain importable only for explicit
compatibility tests and cannot be called by a module implementation.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FORBIDDEN_CALLS = {"ensure_paragraph_citations", "convert_citation_markers"}


def _has_keyword(call: ast.Call, name: str) -> bool:
    return any(keyword.arg == name for keyword in call.keywords)


def check() -> list[str]:
    violations: list[str] = []
    for path in sorted(BACKEND.rglob("*.py")):
        if "/tests/" in path.as_posix():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            violations.append(f"{path}:{exc.lineno}: syntax error: {exc.msg}")
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            callee = node.func
            name = callee.id if isinstance(callee, ast.Name) else (
                callee.attr if isinstance(callee, ast.Attribute) else ""
            )
            if name in FORBIDDEN_CALLS:
                violations.append(
                    f"{path.relative_to(ROOT)}:{node.lineno}: forbidden production call {name}()"
                )
            if name == "attach_citations" and not _has_keyword(node, "registry"):
                violations.append(
                    f"{path.relative_to(ROOT)}:{node.lineno}: attach_citations() requires registry="
                )
            if name == "generate_chapter" and not _has_keyword(node, "citation_registry"):
                violations.append(
                    f"{path.relative_to(ROOT)}:{node.lineno}: generate_chapter() requires citation_registry="
                )
            if name == "apply_citation_pipeline" and not _has_keyword(node, "registry"):
                violations.append(
                    f"{path.relative_to(ROOT)}:{node.lineno}: apply_citation_pipeline() requires registry="
                )
    return violations


def main() -> int:
    violations = check()
    if violations:
        print("Citation single-source guard failed:")
        print("\n".join(f"- {item}" for item in violations))
        return 1
    print("Citation single-source guard passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
