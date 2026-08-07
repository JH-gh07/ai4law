"""Schema-first adapter for the legacy security-assessment chapter output."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from backend.common.citation.registry import CitationRegistry as LegacyCitationRegistry
from backend.common.llm.postprocess import strip_markdown_inline
from backend.common.reporting import (
    ClaimBlock,
    DocumentIR,
    ParagraphBlock,
    SectionIR,
    legacy_registry_to_reporting,
)
from backend.common.reporting.schema import Provenance, ReportMetadata
from backend.common.reporting.schema.citations import CitationRegistry
from backend.domains.cn.security_assessment.schema import ChapterContent

_CITATION_MARKER_RE = re.compile(r"\{\{(CIT-[^{}\s]+)\}\}")
_HEADING_PREFIX_RE = re.compile(r"(?m)^\s*#{1,6}\s+")
_SPACE_BEFORE_PUNCTUATION_RE = re.compile(r"\s+([，。；：！？])")


def _semantic_text(paragraph: str) -> str:
    without_markers = _CITATION_MARKER_RE.sub("", paragraph)
    without_headings = _HEADING_PREFIX_RE.sub("", without_markers)
    normalized = strip_markdown_inline(without_headings).strip()
    return _SPACE_BEFORE_PUNCTUATION_RE.sub(r"\1", normalized)


def build_assessment_document_ir(
    *,
    task_id: str,
    company_name: str,
    chapters: list[ChapterContent],
    citation_registry: LegacyCitationRegistry,
    model: str,
    generated_at: datetime | None = None,
) -> tuple[DocumentIR, CitationRegistry]:
    """Translate current assessment chapters into typed DocumentIR.

    This adapter does not render or repair content. Unknown marker identities
    remain as citation refs so CitationValidationPass can fail closed.
    """
    reporting_registry = legacy_registry_to_reporting(citation_registry)
    sections: list[SectionIR] = []
    for chapter in chapters:
        blocks = []
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", chapter.content) if part.strip()]
        for index, paragraph in enumerate(paragraphs, start=1):
            citation_refs = list(dict.fromkeys(_CITATION_MARKER_RE.findall(paragraph)))
            text = _semantic_text(paragraph)
            if not text:
                continue
            block_id = f"assessment.chapter.{chapter.chapter_no}.block.{index}"
            if citation_refs:
                registered = all(reporting_registry.resolve(ref) is not None for ref in citation_refs)
                blocks.append(ClaimBlock(
                    block_id=block_id,
                    text=text,
                    citation_refs=citation_refs,
                    verification="verified" if registered else "missing_evidence",
                    verification_reason=(
                        "由 legacy citation marker 迁移"
                        if registered
                        else "存在未注册的 legacy citation marker"
                    ),
                ))
            else:
                blocks.append(ParagraphBlock(block_id=block_id, text=text))
        sections.append(SectionIR(
            section_id=f"assessment.chapter.{chapter.chapter_no}",
            title=chapter.title,
            level=2,
            ordinal=str(chapter.chapter_no),
            blocks=blocks,
        ))

    timestamp = generated_at or datetime.now(timezone.utc)
    document = DocumentIR(
        compiler_version="0.1.0",
        prompt_version="legacy-assessment-adapter-v1",
        template_version="assessment-v0",
        model=model,
        document_id=f"assessment:{task_id}",
        report_type="assessment",
        metadata=ReportMetadata(
            title=f"{company_name}数据出境风险自评估报告",
            company_name=company_name,
            report_date=timestamp.date().isoformat(),
            report_id=task_id,
        ),
        sections=sections,
        provenance=Provenance(generated_at=timestamp),
    )
    return document, reporting_registry
