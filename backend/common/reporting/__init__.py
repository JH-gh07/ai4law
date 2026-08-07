"""Schema-first reporting primitives.

The package is additive during the migration. Existing Markdown renderers keep
their current behavior until a compiler feature flag is explicitly enabled.
"""

from backend.common.reporting.compiler import DocumentCompiler
from backend.common.reporting.schema import (
    Block,
    ClaimBlock,
    CitationRecord,
    CitationRegistry,
    DocumentIR,
    ListBlock,
    ParagraphBlock,
    SectionIR,
    TableBlock,
    WarningBlock,
)

__all__ = [
    "Block",
    "ClaimBlock",
    "CitationRecord",
    "CitationRegistry",
    "DocumentCompiler",
    "DocumentIR",
    "ListBlock",
    "ParagraphBlock",
    "SectionIR",
    "TableBlock",
    "WarningBlock",
]
