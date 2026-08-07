"""Pydantic models for the reporting intermediate representation."""

from backend.common.reporting.schema.blocks import (
    Block,
    ClaimBlock,
    ListBlock,
    ParagraphBlock,
    TableBlock,
    VerificationStatus,
    WarningBlock,
)
from backend.common.reporting.schema.citations import CitationRecord, CitationRegistry
from backend.common.reporting.schema.document import (
    DocumentIR,
    Provenance,
    ReportMetadata,
    SectionIR,
)

__all__ = [
    "Block",
    "ClaimBlock",
    "CitationRecord",
    "CitationRegistry",
    "DocumentIR",
    "ListBlock",
    "ParagraphBlock",
    "Provenance",
    "ReportMetadata",
    "SectionIR",
    "TableBlock",
    "VerificationStatus",
    "WarningBlock",
]
