"""Citation compiler — transforms rendered markdown + CitationRegistry into verified footnote maps.

Responsible for:
1. Extracting only {{CIT-xxx}} markers actually present in the rendered text
2. Producing footnote_map (with stable numbering) strictly from markers-in-text
3. Validating that every binding is semantically relevant to its claim (not just "retrieved")
4. Detecting orphan citations (registered but never used in text) and missing markers

This replaces the legacy pattern of ``CitationRegistry.get_footnote_map()``
which blindly returns all registered items regardless of usage.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from backend.common.citation.markers import CIT_MARKER_RE
from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry


# ── Core compilation ────────────────────────────────────────────────────────


@dataclass
class CompiledFootnotes:
    """Result of compiling a rendered text against a CitationRegistry.

    Only citations whose {{CIT-xxx}} markers actually appear in the text
    are included.  Orphans (registered but unused) and ghosts (markers
    without registry entries) are tracked separately.
    """

    footnote_map: dict[int, CitationItem]
    """Canonical {footnote_number: CitationItem} — only markers present in text."""

    orphans: list[str]
    """Citation IDs that were registered but never appeared in the text."""

    ghosts: list[str]
    """Markers found in text but missing from the registry."""

    marker_positions: dict[str, list[int]]
    """{citation_id: [byte offsets]} for every marker in the text."""


def compile_footnote_map(
    rendered_text: str,
    registry: CitationRegistry,
) -> CompiledFootnotes:
    """Build a footnote map from only the markers that actually appear in the text.

    Algorithm:
    1. Scan the text for all ``{{CIT-xxx}}`` markers.
    2. Look up each marker in the registry.
    3. Assign footnote numbers in first-appearance order.
    4. Report orphans (registered but unused) and ghosts (markers without
       registry entry).
    """
    markers: list[str] = []
    positions: dict[str, list[int]] = {}

    for match in CIT_MARKER_RE.finditer(rendered_text):
        cid = match.group(1)
        positions.setdefault(cid, []).append(match.start())
        markers.append(cid)

    # Deduplicate while preserving first-appearance order
    seen: set[str] = set()
    ordered: list[str] = []
    for cid in markers:
        if cid not in seen:
            seen.add(cid)
            ordered.append(cid)

    # Build footnote map
    footnote_map: dict[int, CitationItem] = {}
    ghosts: list[str] = []
    next_num = 1

    for cid in ordered:
        item = registry.get(cid)
        if item is None:
            ghosts.append(cid)
            continue
        footnote_map[next_num] = item
        next_num += 1

    # Detect orphans — registered entries whose markers never appear
    all_registered = {item.citation_id for item in registry}
    used = set(ordered)
    orphans = sorted(all_registered - used)

    return CompiledFootnotes(
        footnote_map=footnote_map,
        orphans=orphans,
        ghosts=ghosts,
        marker_positions=positions,
    )


# ── Marker extraction utilities ─────────────────────────────────────────────


def extract_citation_markers(text: str) -> list[str]:
    """Return all unique {{CIT-xxx}} markers found in text, in first-appearance order."""
    seen: set[str] = set()
    result: list[str] = []
    for match in CIT_MARKER_RE.finditer(text):
        cid = match.group(1)
        if cid not in seen:
            seen.add(cid)
            result.append(cid)
    return result


def extract_citation_marker_count(text: str) -> int:
    """Count total {{CIT-xxx}} marker occurrences (with duplicates)."""
    return len(CIT_MARKER_RE.findall(text))


# ── Citation marker validation ──────────────────────────────────────────────


def validate_citation_marker(
    citation_id: str,
    registry: CitationRegistry,
) -> str | None:
    """Validate a single citation marker against the registry.

    Returns None if valid, or an error message string if invalid.
    """
    if not citation_id:
        return "Empty citation marker"

    item = registry.get(citation_id)
    if item is None:
        return f"Citation marker {citation_id!r} not found in registry"

    if not item.title.strip():
        return f"Citation {citation_id!r} has empty title"

    if not item.source_id.strip():
        return f"Citation {citation_id!r} has empty source_id"

    return None


def validate_all_markers(
    rendered_text: str,
    registry: CitationRegistry,
) -> list[str]:
    """Validate all citation markers in rendered text against registry.

    Returns list of error messages (empty list = no errors).
    """
    errors: list[str] = []
    for match in CIT_MARKER_RE.finditer(rendered_text):
        cid = match.group(1)
        err = validate_citation_marker(cid, registry)
        if err:
            errors.append(err)
    return errors


# ── Claim-binding validation ────────────────────────────────────────────────


@dataclass
class ClaimBindingReport:
    """Validation report for claim-citation binding consistency."""

    claim_count: int
    """Total claims validated."""

    bound_count: int
    """Claims with at least one verified legal_basis."""

    unbound_claim_ids: list[str]
    """Claim IDs without any legal_basis."""

    unsupported_binding_count: int
    """Citations whose support_level is 'irrelevant' but still appear in legal_basis."""

    errors: list[str]
    """Detailed error messages."""


def validate_claim_bindings(
    evidence_items: list[dict[str, Any]],
) -> ClaimBindingReport:
    """Validate that every claim's legal_basis is meaningful and properly bound.

    Checks:
    1. Every claim has at least one legal_basis entry.
    2. No 'irrelevant' support_level appears in legal_basis (should be in
       discarded_basis).
    3. Each binding has a non-empty source_title.
    """
    claim_count = len(evidence_items)
    bound_count = 0
    unbound: list[str] = []
    unsupported = 0
    errors: list[str] = []

    for item in evidence_items:
        eid = item.get("evidence_id", "?")
        claim = item.get("claim", "?")
        legal_basis = item.get("legal_basis", []) or []

        if not legal_basis:
            unbound.append(eid)
            errors.append(f"Claim {eid!r} ({claim[:60]}…) has no legal_basis")
            continue

        bound_count += 1

        for binding in legal_basis:
            if isinstance(binding, dict):
                support = binding.get("support_level", "")
                source_title = binding.get("source_title", "")
            else:
                support = getattr(binding, "support_level", "")
                source_title = getattr(binding, "source_title", "")

            if support == "irrelevant":
                unsupported += 1
                errors.append(
                    f"Claim {eid!r}: binding source_title={source_title!r} has "
                    f"support_level='irrelevant' in legal_basis (should be discarded)"
                )

            if not source_title or not str(source_title).strip():
                errors.append(f"Claim {eid!r}: binding has empty source_title")

    return ClaimBindingReport(
        claim_count=claim_count,
        bound_count=bound_count,
        unbound_claim_ids=unbound,
        unsupported_binding_count=unsupported,
        errors=errors,
    )


# ── Markdown marker verification ────────────────────────────────────────────


def markers_in_text_equal_footnote_map(
    rendered_text: str,
    footnote_map: dict[int, CitationItem],
) -> tuple[bool, str]:
    """Verify that the set of markers in rendered text exactly matches the footnote_map.

    Returns (True, "") on success, (False, reason) on failure.
    """
    text_markers = set(extract_citation_markers(rendered_text))
    map_markers = {item.citation_id for item in footnote_map.values()}

    missing_from_map = text_markers - map_markers
    extra_in_map = map_markers - text_markers

    issues: list[str] = []
    if missing_from_map:
        issues.append(f"Markers in text but missing from footnote_map: {sorted(missing_from_map)}")
    if extra_in_map:
        issues.append(f"Citations in footnote_map but missing from text: {sorted(extra_in_map)}")

    if issues:
        return False, "; ".join(issues)

    return True, ""


# ── Negative test utilities ─────────────────────────────────────────────────


def simulate_marker_removal(
    rendered_text: str,
    registry: CitationRegistry,
    citation_id: str,
) -> CompiledFootnotes:
    """Compile footnote map after removing one marker — for negative testing.

    Removes all occurrences of {{citation_id}} from the text, then re-compiles.
    """
    marker_pattern = re.compile(r"\{\{" + re.escape(citation_id) + r"\}\}")
    cleaned = marker_pattern.sub("", rendered_text)
    return compile_footnote_map(cleaned, registry)


def simulate_marker_addition(
    rendered_text: str,
    registry: CitationRegistry,
    citation_id: str,
    insertion_point: str | None = None,
) -> CompiledFootnotes:
    """Compile footnote map after adding a marker — for negative testing.

    If insertion_point is provided, inserts after the first occurrence of that
    substring; otherwise appends to end.
    """
    marker = f"{{{{{citation_id}}}}}"
    if insertion_point and insertion_point in rendered_text:
        idx = rendered_text.find(insertion_point)
        new_text = rendered_text[:idx + len(insertion_point)] + marker + rendered_text[idx + len(insertion_point):]
    else:
        new_text = rendered_text + "\n" + marker
    return compile_footnote_map(new_text, registry)
