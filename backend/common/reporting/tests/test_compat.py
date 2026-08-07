from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry as LegacyCitationRegistry
from backend.common.reporting.compat import legacy_item_to_record, legacy_registry_to_reporting


def test_legacy_item_conversion_preserves_identity_and_locator() -> None:
    item = CitationItem(
        citation_id="CIT-CN-EXPORT-ASSESSMENT-ART5-P01",
        source_id="CN-REG-001",
        citation_type="law_article",
        title="数据出境安全评估办法",
        article_no="5",
        chunk_id="chunk-5",
        related_evidence_ids=["evidence-5"],
        external_report_allowed=True,
    )

    record = legacy_item_to_record(item)

    assert record.citation_id == item.citation_id
    assert record.source_type == "regulation"
    assert record.locator is not None and record.locator.article == "5"
    assert record.knowledge_id == "chunk-5"
    assert record.evidence_unit_id == "evidence-5"


def test_legacy_registry_conversion_preserves_assigned_numbers() -> None:
    legacy = LegacyCitationRegistry()
    first = CitationItem(citation_id="CIT-CN-PIPL-ART1-P01", source_id="LAW-1", title="PIPL")
    second = CitationItem(citation_id="CIT-CN-EXPORT-ASSESSMENT-ART5-P01", source_id="REG-1", title="评估办法")
    legacy.register(first)
    legacy.register(second)
    assert legacy.assign_footnote_number(second.citation_id) == 1
    assert legacy.assign_footnote_number(first.citation_id) == 2

    reporting = legacy_registry_to_reporting(legacy)

    assert reporting.footnote_map() == {
        second.citation_id: 1,
        first.citation_id: 2,
    }
