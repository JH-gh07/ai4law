"""Tests for backend.common.citation.markers — single source of truth for regex."""
from __future__ import annotations

import re

import pytest

from backend.common.citation.markers import (
    CITATION_ID_RE,
    CIT_MARKER_RE,
    is_valid_citation_id,
)


# ---------------------------------------------------------------------------
# CITATION_ID_RE — format validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cid", [
    "CIT-CN-PIPL-ART39-P01",
    "CIT-CN-DSL-ART21-P12",
    "CIT-CN-CSL-GEN-P01",
    "CIT-CN-EXPORT_ASSESSMENT-ART5-P01",   # new format (sanitized abbr)
    "CIT-CN-DATA_CLASSIFICATION-ART3-P02",
    "CIT-EU-GDPR-ART17-P01",
    "CIT-US-CCPA-GEN-P99",
])
def test_citation_id_re_valid(cid: str) -> None:
    assert CITATION_ID_RE.fullmatch(cid), f"Expected {cid!r} to match CITATION_ID_RE"


@pytest.mark.parametrize("bad_cid, reason", [
    ("CIT-CN-PIPL-39-P01",          "missing ART prefix"),
    ("CIT-C-PIPL-ART39-P01",        "jurisdiction too short"),
    ("cit-CN-PIPL-ART39-P01",       "lowercase prefix"),
    ("CIT-CN-PIPL-ART39",           "missing P segment"),
    ("CIT-CN-PIPL-GEN-P1X",         "non-digit in P segment"),
    ("CITCNPIPL-ART39-P01",         "missing dashes"),
    ("{{CIT-CN-PIPL-ART39-P01}}",   "with braces"),
])
def test_citation_id_re_invalid(bad_cid: str, reason: str) -> None:
    assert not CITATION_ID_RE.fullmatch(bad_cid), f"{reason}: {bad_cid!r} should not match"


# ---------------------------------------------------------------------------
# is_valid_citation_id — convenience wrapper
# ---------------------------------------------------------------------------

def test_is_valid_returns_true_for_valid_id() -> None:
    assert is_valid_citation_id("CIT-CN-PIPL-ART39-P01")


def test_is_valid_returns_true_for_sanitized_abbr() -> None:
    # New-format ID with underscore in abbr (post-fix generation)
    assert is_valid_citation_id("CIT-CN-EXPORT_ASSESSMENT-ART5-P01")


def test_is_valid_returns_true_for_legacy_hyphen_abbr() -> None:
    # Old-format IDs with hyphen in abbr must still be recognised (backward compat)
    assert is_valid_citation_id("CIT-CN-EXPORT-ASSESSMENT-ART5-P01")


def test_is_valid_returns_false_for_garbage() -> None:
    assert not is_valid_citation_id("NOT-A-CITATION-ID")
    assert not is_valid_citation_id("")
    assert not is_valid_citation_id("{{CIT-CN-PIPL-ART39-P01}}")


# ---------------------------------------------------------------------------
# CIT_MARKER_RE — marker extraction from text
# ---------------------------------------------------------------------------

def test_cit_marker_re_finds_marker_in_text() -> None:
    text = "根据{{CIT-CN-PIPL-ART39-P01}}的规定，数据处理者应当……"
    matches = CIT_MARKER_RE.findall(text)
    assert matches == ["CIT-CN-PIPL-ART39-P01"]


def test_cit_marker_re_finds_multiple_markers() -> None:
    text = "{{CIT-CN-PIPL-ART39-P01}}和{{CIT-CN-DSL-ART21-P01}}均适用。"
    matches = CIT_MARKER_RE.findall(text)
    assert matches == ["CIT-CN-PIPL-ART39-P01", "CIT-CN-DSL-ART21-P01"]


def test_cit_marker_re_captures_sanitized_abbr() -> None:
    text = "参见{{CIT-CN-EXPORT_ASSESSMENT-ART5-P01}}。"
    matches = CIT_MARKER_RE.findall(text)
    assert matches == ["CIT-CN-EXPORT_ASSESSMENT-ART5-P01"]


def test_cit_marker_re_ignores_plain_text() -> None:
    assert CIT_MARKER_RE.findall("没有引用标记的普通文本") == []


def test_cit_marker_re_ignores_malformed_marker() -> None:
    # Missing ART prefix — should not be captured
    assert CIT_MARKER_RE.findall("{{CIT-CN-PIPL-39-P01}}") == []
