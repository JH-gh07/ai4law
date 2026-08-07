#!/usr/bin/env python3
"""CLI wrapper: run the advisory Markdown quality gate on a delivered report.

Usage
-----
    uv run python scripts/check_report_lint.py <report.md> [--profile external|internal]

Exit codes
----------
0   Always — the linter is advisory by design. BLOCK findings are printed but
    never cause a non-zero exit. Callers decide whether to stop a pipeline.

Integrates ``backend/common/quality/markdown_lint.lint_markdown`` into the
per-module verification checklist described in the migration plan
(status/todo/DataComplyFlow_架构统一迁移与可核验实施方案_20260808.md §16.2).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure repo root is importable when run with `uv run python scripts/…`
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.common.quality.markdown_lint import LintContext, lint_markdown


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Advisory Markdown quality gate for compliance reports"
    )
    p.add_argument("file", help="Path to the Markdown report to lint")
    p.add_argument(
        "--profile",
        choices=["external", "internal"],
        default="external",
        help="Lint profile (default: external)",
    )
    p.add_argument(
        "--expected-risk-level",
        default="",
        metavar="LEVEL",
        help="Expected risk level from the rule engine (enables L5 cross-check)",
    )
    p.add_argument(
        "--citation-map-count",
        type=int,
        default=0,
        metavar="N",
        help="Number of entries in citation_map.json (enables L6 cross-check)",
    )
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    report_path = Path(args.file)

    if not report_path.exists():
        print(f"ERROR: file not found: {report_path}", file=sys.stderr)
        sys.exit(1)

    text = report_path.read_text(encoding="utf-8")

    ctx = LintContext(
        expected_risk_level=args.expected_risk_level,
        citation_map_count=args.citation_map_count,
    )

    findings = lint_markdown(text, profile=args.profile, context=ctx)  # type: ignore[call-arg]

    if not findings:
        print(f"✓ {report_path.name}: no findings ({args.profile} profile)")
        return

    blocks = [f for f in findings if f.severity == "BLOCK"]
    warns = [f for f in findings if f.severity == "WARN"]

    print(f"\n{'─'*70}")
    print(f"  {report_path.name}  [{args.profile} profile]")
    print(f"{'─'*70}")
    for finding in findings:
        icon = "✗" if finding.severity == "BLOCK" else "△"
        print(f"  {icon} {finding}")
        if finding.snippet:
            print(f"      snippet: {finding.snippet!r}")
    print(f"{'─'*70}")
    print(
        f"  {len(findings)} finding(s): "
        f"{len(blocks)} BLOCK  {len(warns)} WARN  — advisory only"
    )
    print()


if __name__ == "__main__":
    main()
