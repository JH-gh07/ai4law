"""Schema-first adapter for the DPIA chapter output.

Translates DPIAChapterContent list → DocumentIR, following the same
convention as the security-assessment adapter (schema_first.py).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from backend.common.citation.registry import CitationRegistry as LegacyCitationRegistry
from backend.common.llm.postprocess import strip_markdown_inline
from backend.common.reporting import (
    CitationNoteBlock,
    ClaimBlock,
    DocumentIR,
    KeyValueBlock,
    KeyValueItem,
    ParagraphBlock,
    SectionIR,
    extract_citation_refs,
    legacy_registry_to_reporting,
)
from backend.common.reporting.schema import Provenance, ReportMetadata
from backend.common.reporting.schema.citations import CitationRegistry
from backend.domains.eu.dpia.schema import DPIAChapterContent

# Marker parsing lives in backend/common/citation/markers.py (single source of
# truth); this module must not redefine a citation-marker regex.
_HEADING_PREFIX_RE = re.compile(r"(?m)^\s*#{1,6}\s+")
_SPACE_BEFORE_PUNCTUATION_RE = re.compile(r"\s+([，。；：！？])")
_FOOTNOTE_RESIDUE_RE = re.compile(r"\[\d+\]")


def _semantic_text(paragraph: str) -> str:
    """Normalize already citation-free text into semantic block text.

    Citation tokens are removed upstream by ``extract_citation_refs``; this
    only strips heading syntax and inline Markdown.
    """
    without_headings = _HEADING_PREFIX_RE.sub("", paragraph)
    normalized = strip_markdown_inline(without_headings).strip()
    return _SPACE_BEFORE_PUNCTUATION_RE.sub(r"\1", normalized)


def build_dpia_document_ir(
    *,
    task_id: str,
    project_name: str,
    chapters: list[DPIAChapterContent],
    citation_registry: LegacyCitationRegistry,
    model: str,
    generated_at: datetime | None = None,
    input_appendix: list[tuple[str, str]] | None = None,
) -> tuple[DocumentIR, CitationRegistry]:
    """Translate DPIA chapter output into typed DocumentIR.

    Does not render or repair content.  Unknown marker identities survive
    so that CitationValidationPass can fail closed.  The adapter appends a
    citations appendix and an input appendix so the full layout is stable
    (task068 T09).  ``input_appendix`` must be sanitized by the caller —
    profile fields / risk matrix / mitigation plan / attachments are surfaced
    as key-value entries, never nested JSON.
    """
    reporting_registry = legacy_registry_to_reporting(citation_registry)
    sections: list[SectionIR] = []

    for chapter in chapters:
        blocks = []
        paragraphs = [
            part.strip()
            for part in re.split(r"\n\s*\n", chapter.content)
            if part.strip()
        ]
        for index, paragraph in enumerate(paragraphs, start=1):
            # Accepts both citation shapes: raw {{CIT-*}} markers (pre-generator)
            # and [N] footnotes (post-generator, the production shape).
            citation_free, citation_refs = extract_citation_refs(paragraph, citation_registry)
            # Surface any [N] residue the registry could not resolve (see
            # assessment/schema_first.py for rationale — prevents ParagraphBlock
            # validation from eating CITATION_NOT_REGISTERED before the compiler).
            residue = _FOOTNOTE_RESIDUE_RE.findall(citation_free)
            if residue:
                citation_refs = list(dict.fromkeys(citation_refs + residue))
                citation_free = _FOOTNOTE_RESIDUE_RE.sub("", citation_free)
            text = _semantic_text(citation_free)
            if not text:
                continue
            block_id = f"dpia.chapter.{chapter.chapter_no}.block.{index}"
            if citation_refs:
                registered = all(
                    reporting_registry.resolve(ref) is not None
                    for ref in citation_refs
                )
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
            section_id=f"dpia.chapter.{chapter.chapter_no}",
            title=chapter.title,
            level=2,
            ordinal=str(chapter.chapter_no),
            blocks=blocks,
        ))

    # Fixed tail: 引用 → 输入附录 (numbering continues after the chapters).
    appendix_no = len(chapters) + 1
    ordered_cids = sorted(
        reporting_registry.footnote_map().keys(),
        key=lambda cid: reporting_registry.footnote_map()[cid],
    )
    if ordered_cids:
        sections.append(SectionIR(
            section_id="dpia.appendix.citations",
            title="引用法规与条文",
            level=2,
            ordinal=str(appendix_no),
            blocks=[
                CitationNoteBlock(
                    block_id="dpia.appendix.citations.block",
                    citation_refs=ordered_cids,
                )
            ],
        ))
        appendix_no += 1

    if input_appendix:
        items = [
            KeyValueItem(label=label, value=value)
            for label, value in input_appendix
            if str(value).strip()
        ]
        if items:
            sections.append(SectionIR(
                section_id="dpia.appendix.inputs",
                title="输入附录",
                level=2,
                ordinal=str(appendix_no),
                blocks=[
                    KeyValueBlock(
                        block_id="dpia.appendix.inputs.block",
                        items=items,
                    )
                ],
            ))

    timestamp = generated_at or datetime.now(timezone.utc)
    document = DocumentIR(
        compiler_version="0.1.0",
        prompt_version="legacy-dpia-adapter-v1",
        template_version="dpia-v0",
        model=model,
        document_id=f"dpia:{task_id}",
        report_type="dpia",
        metadata=ReportMetadata(
            title=f"{project_name} — DPIA 草案",
            company_name=project_name,
            report_date=timestamp.date().isoformat(),
            report_id=task_id,
        ),
        sections=sections,
        provenance=Provenance(generated_at=timestamp),
    )
    return document, reporting_registry
