"""Schema-first adapter for the document review aggregated output.

Unlike chapter-based adapters, document_review produces an AggregatedReview
(sections built by ReviewReportRenderer.build_sections). Each rendered section
becomes a SectionIR; each paragraph in the section becomes a ParagraphBlock.
The review renderer does NOT emit citation markers in its output, so all blocks
are plain ParagraphBlocks. The reuse_policy is set to "summary" because an
aggregated report legitimately repeats the document title and risk scores across
multiple sections.
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.common.citation.registry import CitationRegistry as LegacyCitationRegistry
from backend.common.reporting import (
    DocumentIR,
    ParagraphBlock,
    SectionIR,
    legacy_registry_to_reporting,
)
from backend.common.reporting.schema import Provenance, ReportMetadata
from backend.common.reporting.schema.citations import CitationRegistry
from backend.schemas.review import AggregatedReview


def build_document_review_ir(
    *,
    task_id: str,
    document_title: str,
    review: AggregatedReview,
    sections: list[tuple[str, list[str]]],
    citation_registry: LegacyCitationRegistry,
    model: str,
    generated_at: datetime | None = None,
) -> tuple[DocumentIR, CitationRegistry]:
    """Translate rendered review sections into typed DocumentIR.

    Parameters
    ----------
    sections:
        Output of ReviewReportRenderer.build_sections(aggregated) —
        list of (section_title, list[paragraph_text]) tuples.
    """
    reporting_registry = legacy_registry_to_reporting(citation_registry)
    ir_sections: list[SectionIR] = []

    for ordinal, (section_title, paragraphs) in enumerate(sections, start=1):
        blocks = []
        for block_idx, paragraph in enumerate(paragraphs, start=1):
            text = paragraph.strip()
            if not text:
                continue
            blocks.append(ParagraphBlock(
                block_id=f"review.section.{ordinal}.block.{block_idx}",
                text=text,
            ))
        ir_sections.append(SectionIR(
            section_id=f"review.section.{ordinal}",
            title=section_title,
            level=2,
            ordinal=str(ordinal),
            blocks=blocks,
            # Aggregated review legitimately repeats summary text across sections.
            reuse_policy="summary",
        ))

    timestamp = generated_at or datetime.now(timezone.utc)
    document = DocumentIR(
        compiler_version="0.1.0",
        prompt_version="legacy-document-review-adapter-v1",
        template_version="document-review-v0",
        model=model,
        document_id=f"review:{task_id}",
        report_type="review",
        metadata=ReportMetadata(
            title=f"{document_title} — 智能审查报告",
            company_name=document_title,
            report_date=timestamp.date().isoformat(),
            report_id=task_id,
        ),
        sections=ir_sections,
        provenance=Provenance(generated_at=timestamp),
    )
    return document, reporting_registry
