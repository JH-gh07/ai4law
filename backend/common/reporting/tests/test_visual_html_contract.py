"""Task067 T10 — visual-acceptance HTML renderer contract.

The browser half of T10 renders a standalone report body that mirrors the React
``ReportDocumentView`` block DOM 1:1 (same CSS classes, same clause numbering).
These tests lock the *block → HTML* mapping so a silent drop of a block type or
a numbering reset is caught before it reaches the headless-browser screenshots.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
_SCRIPT = ROOT / "scripts" / "run_bcr_visual_acceptance.py"

_spec = importlib.util.spec_from_file_location("run_bcr_visual_acceptance", _SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _mod
_spec.loader.exec_module(_mod)


def _render_case(case: dict) -> str:
    document = _mod._document(
        case["doc_id"], case["company"], case["title"], case["report_id"],
        case["findings"], case["citations"],
        with_clause=case.get("with_clause", False),
        with_long_regulation=case.get("with_long_regulation", False),
    )
    css = (ROOT / "frontend" / "src" / "styles" / "app" / "report.css").read_text(encoding="utf-8")
    return _mod._render_html(document, css)


def test_number_token_mirrors_react_clause_numbering() -> None:
    assert _mod._number_token("decimal", 1) == "1."
    assert _mod._number_token("lower_alpha", 1) == "(a)"
    assert _mod._number_token("lower_alpha", 2) == "(b)"
    assert _mod._number_token("lower_roman", 1) == "i."
    assert _mod._number_token("lower_roman", 2) == "ii."
    assert _mod._number_token("none", 1) == ""


def test_deep_clause_numbering_has_no_reset() -> None:
    block = _mod._deep_clause_group()
    html = _mod._clause_tree_html(block.clauses)
    # decimal → lower_alpha → lower_roman, in order, no reset.
    for heading in ("1. 第一条", "(a) 第一项", "(b) 第二项", "i. 第 1 目", "ii. 第 2 目", "2. 第二条"):
        assert heading in html
    # 6 clause nodes total, nesting preserved (children inside their parent <li>).
    assert html.count('class="clause-node"') == 6


def _body_text(html: str) -> str:
    return html.split("<body>", 1)[1].split("</body>", 1)[0]


def test_all_three_cases_render_every_block_type_without_unknown_block() -> None:
    for case in _mod._build_cases():
        html = _render_case(case)
        # no block type is silently dropped to the recovery note
        assert 'class="ir-unknown-block"' not in html
        # finding summary + one detail card per finding
        assert 'class="ir-table ir-summary-table"' in html
        assert html.count('class="finding-card') == len(case["findings"])
        # no markdown/template residue leaks into the web layer
        assert "| --- |" not in html
        assert "**" not in html and "{{" not in html
        # the metadata title renders exactly once in the body (no duplicate body)
        assert _body_text(html).count(case["title"]) == 1


def test_stress_case_exercises_long_regulation_and_mobile_safe_wrap() -> None:
    case = next(c for c in _mod._build_cases() if c["case_id"] == "issue067_18_finding_stress")
    html = _render_case(case)
    # 18 findings all reach the summary + detail layers
    assert html.count('class="finding-card') == 18
    assert html.count("<tr>") >= 18
    # the long English regulation survives intact (not split per character)
    assert _mod.LONG_REGULATION in html
    # the CSS that prevents page-level horizontal scroll is inlined
    assert "overflow-wrap: anywhere" in html
    assert "@media (max-width: 720px)" in html


def test_finding_card_uses_text_badges_not_color_alone() -> None:
    case = next(c for c in _mod._build_cases() if c["case_id"] == "bcr_controller_basic")
    html = _render_case(case)
    # risk conveyed by text + badge class (accessibility, not color-only)
    assert "finding-risk-badge-high" in html
    assert "高风险" in html
    assert "finding-risk-badge-medium" in html
    assert "中风险" in html
