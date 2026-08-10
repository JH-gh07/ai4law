"""Negative tests for citation compiler — Phase 2 claim-evidence-citation contract validation.

Covers:
- Marker removal → footnote disappears from map
- Wrong locator → detected
- Invalid source → rejected
- Orphan detection
- Ghost detection
- Claim-binding validation
- Empty legal_basis
- Irrelevant support_level in legal_basis
"""

from __future__ import annotations

import pytest

from backend.common.citation.compiler import (
    ClaimBindingReport,
    compile_footnote_map,
    extract_citation_markers,
    markers_in_text_equal_footnote_map,
    simulate_marker_addition,
    simulate_marker_removal,
    validate_all_markers,
    validate_citation_marker,
    validate_claim_bindings,
)
from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry


# ── Fixtures ──────────────────────────────────────────────────────────────

def _make_item(citation_id: str, *, title: str = "测试法规", source_id: str = "TEST-SRC", article_no: str = "1") -> CitationItem:
    return CitationItem(
        citation_id=citation_id,
        source_id=source_id,
        title=title,
        article_no=article_no,
        jurisdiction="CN",
        display_label=f"{title} 第{article_no}条",
        allowed_usage=["external_report", "internal_review"],
    )


def _make_registry(*citation_ids: str) -> CitationRegistry:
    reg = CitationRegistry()
    for cid in citation_ids:
        reg.register(_make_item(cid))
    return reg


@pytest.fixture
def sample_registry() -> CitationRegistry:
    return _make_registry(
        "CIT-CN-TEST-ART1-P1",
        "CIT-CN-TEST-ART2-P1",
        "CIT-CN-TEST-ART3-P1",
    )


@pytest.fixture
def sample_text() -> str:
    return (
        "# 测试报告\n\n"
        "根据{{CIT-CN-TEST-ART1-P1}}的规定，数据处理者应当…\n\n"
        "此外，{{CIT-CN-TEST-ART2-P1}}也要求…\n\n"
        "{{CIT-CN-TEST-ART1-P1}}再次强调…\n"  # duplicate marker
    )


# ── Core compilation tests ────────────────────────────────────────────────

def test_compile_footnote_map_only_includes_markers_in_text(
    sample_registry, sample_text
):
    """Markers present in text → appear in footnote_map. Unused → orphan."""
    compiled = compile_footnote_map(sample_text, sample_registry)

    # Two unique markers in text
    assert len(compiled.footnote_map) == 2
    map_cids = {item.citation_id for item in compiled.footnote_map.values()}
    assert "CIT-CN-TEST-ART1-P1" in map_cids
    assert "CIT-CN-TEST-ART2-P1" in map_cids

    # Third registered item is an orphan
    assert "CIT-CN-TEST-ART3-P1" in compiled.orphans
    assert compiled.ghosts == []


def test_compile_footnote_map_preserves_first_appearance_order(
    sample_registry
):
    """First-appearance order in text determines footnote numbering."""
    text = "先看{{CIT-CN-TEST-ART2-P1}}，再看{{CIT-CN-TEST-ART1-P1}}。"
    compiled = compile_footnote_map(text, sample_registry)

    assert compiled.footnote_map[1].citation_id == "CIT-CN-TEST-ART2-P1"
    assert compiled.footnote_map[2].citation_id == "CIT-CN-TEST-ART1-P1"


def test_compile_no_markers_returns_empty():
    """Text without any markers → empty footnote_map, all registered → orphans."""
    reg = _make_registry("CIT-CN-TEST-ART1-P1", "CIT-CN-TEST-ART2-P1")
    compiled = compile_footnote_map("普通文本，没有引用。", reg)

    assert compiled.footnote_map == {}
    assert len(compiled.orphans) == 2
    assert compiled.ghosts == []


def test_compile_empty_text():
    """Empty text → empty map."""
    reg = _make_registry("CIT-CN-TEST-ART1-P1")
    compiled = compile_footnote_map("", reg)

    assert compiled.footnote_map == {}
    assert compiled.orphans == ["CIT-CN-TEST-ART1-P1"]


# ── Negative: marker removal ──────────────────────────────────────────────

def test_remove_marker_then_footnote_vanishes(sample_registry, sample_text):
    """G7: Delete a marker from text → citation no longer in footnote_map."""
    compiled_before = compile_footnote_map(sample_text, sample_registry)
    assert "CIT-CN-TEST-ART1-P1" in {
        item.citation_id for item in compiled_before.footnote_map.values()
    }

    # Remove all occurrences of ART1
    compiled_after = simulate_marker_removal(
        sample_text, sample_registry, "CIT-CN-TEST-ART1-P1"
    )

    map_cids = {item.citation_id for item in compiled_after.footnote_map.values()}
    assert "CIT-CN-TEST-ART1-P1" not in map_cids, (
        "Deleted marker should not appear in footnote_map"
    )
    assert "CIT-CN-TEST-ART2-P1" in map_cids, (
        "Unrelated marker should still be present"
    )
    assert "CIT-CN-TEST-ART1-P1" in compiled_after.orphans


def test_remove_all_markers_then_map_empty(sample_registry, sample_text):
    """Removing all markers → footnote_map becomes empty."""
    compiled = simulate_marker_removal(sample_text, sample_registry, "CIT-CN-TEST-ART1-P1")
    compiled = simulate_marker_removal(
        "".join(f"{{{{{item.citation_id}}}}}" for item in compiled.footnote_map.values()),
        sample_registry,
        "CIT-CN-TEST-ART2-P1",
    )
    # Actually just remove both from sample_text
    text = sample_text
    text = text.replace("{{CIT-CN-TEST-ART1-P1}}", "")
    text = text.replace("{{CIT-CN-TEST-ART2-P1}}", "")
    compiled = compile_footnote_map(text, sample_registry)
    assert compiled.footnote_map == {}


# ── Negative: marker addition ─────────────────────────────────────────────

def test_add_unregistered_marker_produces_ghost(sample_registry, sample_text):
    """Adding a marker for a non-existent citation → ghost, not in footnote_map."""
    compiled = simulate_marker_addition(
        sample_text, sample_registry, "CIT-CN-FAKE-ART99-P1"
    )
    assert "CIT-CN-FAKE-ART99-P1" in compiled.ghosts
    assert "CIT-CN-FAKE-ART99-P1" not in {
        item.citation_id for item in compiled.footnote_map.values()
    }


def test_add_registered_marker_at_specific_location(sample_registry, sample_text):
    """Adding a registered marker at a specific insertion point works."""
    compiled = simulate_marker_addition(
        sample_text,
        sample_registry,
        "CIT-CN-TEST-ART3-P1",
        insertion_point="也要求",
    )
    assert "CIT-CN-TEST-ART3-P1" in {
        item.citation_id for item in compiled.footnote_map.values()
    }
    assert compiled.ghosts == []
    assert "CIT-CN-TEST-ART3-P1" not in compiled.orphans


# ── Ghost detection ───────────────────────────────────────────────────────

def test_ghost_marker_detected():
    """G8: Markers without registry entry are detected as ghosts."""
    reg = _make_registry("CIT-CN-TEST-ART1-P1")
    text = "引用{{CIT-CN-TEST-ART1-P1}}和{{CIT-CN-FAKE-ART99-P1}}。"
    compiled = compile_footnote_map(text, reg)

    assert compiled.ghosts == ["CIT-CN-FAKE-ART99-P1"]
    assert len(compiled.footnote_map) == 1


# ── Marker validation ─────────────────────────────────────────────────────

def test_validate_valid_marker():
    """Valid marker passes validation."""
    reg = _make_registry("CIT-CN-TEST-ART1-P1")
    assert validate_citation_marker("CIT-CN-TEST-ART1-P1", reg) is None


def test_validate_missing_marker():
    """Marker not in registry → error."""
    reg = _make_registry("CIT-CN-TEST-ART1-P1")
    err = validate_citation_marker("CIT-CN-FAKE-ART99-P1", reg)
    assert err is not None
    assert "not found" in err


def test_validate_empty_marker():
    """Empty marker string → error."""
    reg = _make_registry("CIT-CN-TEST-ART1-P1")
    err = validate_citation_marker("", reg)
    assert err is not None
    assert "Empty" in err


def test_validate_all_markers_in_text(sample_registry, sample_text):
    """All markers in valid text should pass validation."""
    errors = validate_all_markers(sample_text, sample_registry)
    assert errors == []


def test_validate_ghost_marker_in_text():
    """Ghost marker in text → validation error."""
    reg = _make_registry("CIT-CN-TEST-ART1-P1")
    text = "引用{{CIT-CN-FAKE-ART99-P1}}。"
    errors = validate_all_markers(text, reg)
    assert len(errors) == 1
    assert "not found" in errors[0]


# ── Claim-binding validation ──────────────────────────────────────────────

def test_validate_empty_legal_basis():
    """G5: Claim without legal_basis → reported as unbound."""
    evidence = [
        {
            "evidence_id": "E1",
            "claim": "测试断言",
            "legal_basis": [],
        }
    ]
    report = validate_claim_bindings(evidence)
    assert report.claim_count == 1
    assert report.bound_count == 0
    assert "E1" in report.unbound_claim_ids
    assert len(report.errors) == 1


def test_validate_irrelevant_support_in_legal_basis():
    """G8: 'irrelevant' support in legal_basis → error (should be in discarded_basis)."""
    evidence = [
        {
            "evidence_id": "E1",
            "claim": "测试",
            "legal_basis": [
                {"source_title": "测试法", "article": "1", "support_level": "irrelevant"}
            ],
        }
    ]
    report = validate_claim_bindings(evidence)
    assert report.unsupported_binding_count == 1
    assert any("irrelevant" in err for err in report.errors)


def test_validate_valid_binding_passes():
    """Valid binding with exact_support → no errors."""
    evidence = [
        {
            "evidence_id": "E1",
            "claim": "测试",
            "legal_basis": [
                {"source_title": "个人信息保护法", "article": "38", "support_level": "exact_support"}
            ],
        }
    ]
    report = validate_claim_bindings(evidence)
    assert report.bound_count == 1
    assert report.unsupported_binding_count == 0
    assert report.errors == []


def test_validate_empty_source_title():
    """Binding with empty source_title → error."""
    evidence = [
        {
            "evidence_id": "E1",
            "claim": "测试",
            "legal_basis": [
                {"source_title": "", "article": "1", "support_level": "exact_support"}
            ],
        }
    ]
    report = validate_claim_bindings(evidence)
    assert any("empty source_title" in err.lower() for err in report.errors)


def test_validate_multiple_claims_mixed():
    """Mixed valid/invalid claims → accurate reporting."""
    evidence = [
        {
            "evidence_id": "E-VALID",
            "claim": "有效断言",
            "legal_basis": [
                {"source_title": "测试法", "article": "1", "support_level": "exact_support"}
            ],
        },
        {
            "evidence_id": "E-NO-BASIS",
            "claim": "无依据断言",
            "legal_basis": [],
        },
        {
            "evidence_id": "E-IRRELEVANT",
            "claim": "不相关断言",
            "legal_basis": [
                {"source_title": "测试法", "article": "2", "support_level": "irrelevant"}
            ],
        },
    ]
    report = validate_claim_bindings(evidence)
    assert report.claim_count == 3
    assert report.bound_count == 2
    assert "E-NO-BASIS" in report.unbound_claim_ids
    assert report.unsupported_binding_count == 1


# ── footnote_map equality test ────────────────────────────────────────────

def test_markers_equal_footnote_map_pass(sample_registry, sample_text):
    """G7: When markers match exactly, equality check passes."""
    compiled = compile_footnote_map(sample_text, sample_registry)
    ok, msg = markers_in_text_equal_footnote_map(sample_text, compiled.footnote_map)
    assert ok, msg
    assert msg == ""


def test_markers_equal_footnote_map_extra_in_map(sample_registry):
    """G7: Extra citation in footnote_map not in text → failure."""
    text = "引用{{CIT-CN-TEST-ART1-P1}}。"
    fake_map = {
        1: _make_item("CIT-CN-TEST-ART1-P1"),
        2: _make_item("CIT-CN-TEST-ART2-P1"),  # not in text!
    }
    ok, msg = markers_in_text_equal_footnote_map(text, fake_map)
    assert not ok
    assert "CIT-CN-TEST-ART2-P1" in msg


def test_markers_equal_footnote_map_missing_from_map(sample_registry):
    """G7: Marker in text but missing from footnote_map → failure."""
    text = "引用{{CIT-CN-TEST-ART1-P1}}和{{CIT-CN-TEST-ART2-P1}}。"
    fake_map = {
        1: _make_item("CIT-CN-TEST-ART1-P1"),
    }
    ok, msg = markers_in_text_equal_footnote_map(text, fake_map)
    assert not ok
    assert "CIT-CN-TEST-ART2-P1" in msg


# ── Marker extraction ─────────────────────────────────────────────────────

def test_extract_markers_deduplicates():
    """Duplicate markers → unique list in first-appearance order."""
    text = "{{CIT-CN-TEST-ART1-P1}} {{CIT-CN-TEST-ART2-P1}} {{CIT-CN-TEST-ART1-P1}}"
    markers = extract_citation_markers(text)
    assert markers == ["CIT-CN-TEST-ART1-P1", "CIT-CN-TEST-ART2-P1"]


def test_extract_markers_empty():
    """No markers → empty list."""
    assert extract_citation_markers("普通文本") == []


# ── Edge cases ────────────────────────────────────────────────────────────

def test_compile_with_empty_registry():
    """Empty registry → all markers become ghosts."""
    reg = CitationRegistry()
    compiled = compile_footnote_map("{{CIT-CN-TEST-ART1-P1}}", reg)
    assert compiled.footnote_map == {}
    assert compiled.ghosts == ["CIT-CN-TEST-ART1-P1"]


def test_compile_with_invalid_marker_format():
    """Malformed markers are ignored by CIT_MARKER_RE."""
    reg = _make_registry("CIT-CN-TEST-ART1-P1")
    # CIT_MARKER_RE requires CIT-JU-ABBR-ARTn|GEN-Pnn format
    compiled = compile_footnote_map("{{BAD-FORMAT}} 和 {{CIT-CN-TEST-ART1-P1}}", reg)
    assert len(compiled.footnote_map) == 1
    assert compiled.ghosts == []


def test_marker_positions_recorded(sample_registry, sample_text):
    """Marker byte positions are recorded for debugging."""
    compiled = compile_footnote_map(sample_text, sample_registry)
    positions = compiled.marker_positions
    assert "CIT-CN-TEST-ART1-P1" in positions
    assert len(positions["CIT-CN-TEST-ART1-P1"]) == 2  # appears twice
    assert len(positions["CIT-CN-TEST-ART2-P1"]) == 1  # appears once
