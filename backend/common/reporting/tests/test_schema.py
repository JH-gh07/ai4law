from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.common.reporting.schema import (
    ClaimBlock,
    CitationRecord,
    CitationRegistry,
    DocumentIR,
    ParagraphBlock,
    Provenance,
    ReportMetadata,
    SectionIR,
)


def _document(*sections: SectionIR) -> DocumentIR:
    return DocumentIR(
        compiler_version="0.1.0",
        prompt_version="test",
        template_version="test",
        model="test-model",
        document_id="doc-1",
        report_type="assessment",
        metadata=ReportMetadata(title="测试报告"),
        sections=list(sections),
        provenance=Provenance(generated_at=datetime.now(timezone.utc)),
    )


def test_semantic_blocks_reject_markdown_syntax() -> None:
    with pytest.raises(ValidationError):
        ParagraphBlock(block_id="s1_b1", text="**不应由 IR 接收 Markdown**")


def test_claim_keeps_citation_identity_separate_from_display_number() -> None:
    block = ClaimBlock(
        block_id="s1_b1",
        text="该主张有明确依据。",
        citation_refs=["cit-law-1"],
    )
    assert block.citation_refs == ["cit-law-1"]
    assert "[1]" not in block.text


def test_registry_assigns_numbers_by_first_reference_and_rejects_conflicting_duplicate() -> None:
    registry = CitationRegistry()
    first = CitationRecord(
        citation_id="cit-law-1",
        source_id="law-1",
        source_type="regulation",
        title="测试法",
    )
    second = CitationRecord(
        citation_id="cit-law-2",
        source_id="law-2",
        source_type="regulation",
        title="另一部法",
    )
    registry.register(first)
    registry.register(second)
    assert registry.assign_footnote_number("cit-law-2") == 1
    assert registry.assign_footnote_number("cit-law-1") == 2
    with pytest.raises(ValueError):
        registry.register(first.model_copy(update={"title": "篡改标题"}))


def test_document_schema_forbids_unknown_fields() -> None:
    payload = _document(SectionIR(section_id="s1", title="第一节", level=2)).model_dump()
    payload["unexpected"] = True
    with pytest.raises(ValidationError):
        DocumentIR.model_validate(payload)
