from backend.common.citation.models import CitationItem


def test_citation_item_defaults() -> None:
    item = CitationItem(citation_id="CIT-CN-PIPL-ART39-P01", source_id="CN-LAW-001-001")
    assert item.citation_id == "CIT-CN-PIPL-ART39-P01"
    assert item.source_id == "CN-LAW-001-001"
    assert item.citation_type == "law_article"
    assert item.authority_level == "medium"
    assert item.binding_force == "recommended"
    assert item.related_issue_ids == []
    assert item.related_fact_ids == []
    assert item.related_evidence_ids == []
    assert item.confidence_score == 0.0


def test_citation_item_full_fields() -> None:
    item = CitationItem(
        citation_id="CIT-CN-PIPL-ART39-P01",
        source_id="CN-LAW-001-001",
        chunk_id="CN-LAW-001/CH5/AR39",
        citation_type="law_article",
        title="个人信息保护法",
        article_no="39",
        quote_text="个人信息处理者向境外提供个人信息的...",
        source_file_id="",
        page_no=0,
        related_issue_ids=["ISSUE-consent-evidence-missing"],
        related_fact_ids=["FACT-request-pii_count"],
        related_evidence_ids=["EVID-001"],
        confidence_score=0.85,
        authority_level="high",
        binding_force="mandatory",
    )
    assert item.title == "个人信息保护法"
    assert item.confidence_score == 0.85


def test_citation_item_to_dict() -> None:
    item = CitationItem(
        citation_id="CIT-CN-PIPL-ART39-P01",
        source_id="CN-LAW-001-001",
        title="个人信息保护法",
        article_no="39",
        related_issue_ids=["ISSUE-1"],
        confidence_score=0.85,
    )
    d = item.to_dict()
    assert d["citation_id"] == "CIT-CN-PIPL-ART39-P01"
    assert d["title"] == "个人信息保护法"
    assert d["related_issue_ids"] == ["ISSUE-1"]
    assert d["confidence_score"] == 0.85
