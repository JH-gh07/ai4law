"""Compatibility adapters for the legacy and schema-first citation registries."""

from __future__ import annotations

from collections.abc import Iterable

from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry as LegacyCitationRegistry
from backend.common.reporting.schema.citations import (
    CitationLocator,
    CitationRecord,
    CitationRegistry,
)

_SOURCE_TYPE_MAP = {
    "law_article": "regulation",
    "standard_clause": "standard",
    "official_guide": "guide",
    "template_requirement": "policy_qa",
    "case_reference": "case",
    "user_material": "user_material",
}


def legacy_item_to_record(item: CitationItem) -> CitationRecord:
    """Convert one legacy item without changing its citation identity."""
    article = item.article_no or None
    locator = CitationLocator(article=article) if article else None
    return CitationRecord(
        citation_id=item.citation_id,
        source_id=item.source_id,
        source_type=_SOURCE_TYPE_MAP.get(item.citation_type, "user_material"),
        title=item.title or item.display_label or item.source_id,
        locator=locator,
        knowledge_id=item.chunk_id or None,
        evidence_unit_id=(item.related_evidence_ids[0] if item.related_evidence_ids else None),
        authority_level=item.authority_level,
        binding_force=item.binding_force,
        can_enter_external_report=item.can_enter_external_report and item.external_report_allowed,
    )


def legacy_registry_to_reporting(
    legacy: LegacyCitationRegistry | Iterable[CitationItem],
) -> CitationRegistry:
    """Convert a legacy registry while preserving already assigned footnotes.

    The adapter is intentionally one-way and loss-aware: fields with no
    DocumentIR equivalent are omitted, while identity and numbering are kept.
    """
    records = list(legacy) if not isinstance(legacy, LegacyCitationRegistry) else list(legacy)
    reporting = CitationRegistry(legacy_item_to_record(item) for item in records)
    legacy_numbers = legacy.get_footnote_map() if isinstance(legacy, LegacyCitationRegistry) else {}
    for number in sorted(legacy_numbers):
        item = legacy_numbers[number]
        if reporting.resolve(item.citation_id) is not None:
            assigned = reporting.assign_footnote_number(item.citation_id)
            if assigned != number:
                raise ValueError(
                    f"legacy footnote numbering cannot be preserved for {item.citation_id}: "
                    f"expected {number}, got {assigned}"
                )
    return reporting
