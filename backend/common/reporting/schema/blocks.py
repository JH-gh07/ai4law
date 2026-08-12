"""Typed semantic blocks emitted by the structured report protocol (v4).

The v3 slice had five generic text blocks. v4 adds the finding / clause /
citation / key-value / page-break blocks required by the BCR layout contract
while keeping ``extra="forbid"`` on every model and ``type`` as the single
discriminator. Renderers must handle the whole union exhaustively.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.common.reporting.schema.findings import ClauseNode

_FORBIDDEN_MARKDOWN = re.compile(r"(?:^|\s)(?:#{1,6}\s|\*\*|__|`|\[\d+\])")
_CITATION_MARKER = re.compile(r"\{\{CIT-[^}]+\}\}")


class _BlockModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")

    @field_validator("block_id")
    @classmethod
    def block_id_must_not_be_whitespace(cls, value: str) -> str:
        return value.strip()


def _validate_semantic_text(value: str) -> str:
    if _FORBIDDEN_MARKDOWN.search(value) or _CITATION_MARKER.search(value):
        raise ValueError("semantic block text must not contain Markdown or citation markers")
    return value


# ── v3 blocks (preserved, unchanged semantics) ─────────────────────────────


class ParagraphBlock(_BlockModel):
    type: Literal["paragraph"] = "paragraph"
    text: str = Field(min_length=1)
    fact_refs: list[str] = Field(default_factory=list)
    issue_refs: list[str] = Field(default_factory=list)

    _text_is_semantic = field_validator("text")(_validate_semantic_text)


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    PENDING_REVIEW = "pending_review"
    MISSING_EVIDENCE = "missing_evidence"
    CONFLICTING_EVIDENCE = "conflicting"
    NOT_APPLICABLE = "not_applicable"


class ClaimBlock(_BlockModel):
    type: Literal["claim"] = "claim"
    text: str = Field(min_length=1)
    citation_refs: list[str] = Field(default_factory=list)
    fact_refs: list[str] = Field(default_factory=list)
    issue_refs: list[str] = Field(default_factory=list)
    finding_ref: str | None = None
    verification: Literal[
        "verified",
        "partially_verified",
        "pending_review",
        "missing_evidence",
        "conflicting",
        "not_applicable",
    ] = "pending_review"
    verification_reason: str = ""

    _text_is_semantic = field_validator("text")(_validate_semantic_text)


class TableBlock(_BlockModel):
    type: Literal["table"] = "table"
    headers: list[str] = Field(min_length=1)
    rows: list[list[str]] = Field(default_factory=list)

    @field_validator("headers", "rows")
    @classmethod
    def table_cells_are_semantic(cls, value):
        cells = value if isinstance(value, list) else []
        flattened = [cell for row in cells for cell in row] if cells and isinstance(cells[0], list) else cells
        for cell in flattened:
            _validate_semantic_text(cell)
        return value


class WarningBlock(_BlockModel):
    type: Literal["warning"] = "warning"
    text: str = Field(min_length=1)
    severity: Literal["info", "warning", "error", "fatal"] = "warning"

    _text_is_semantic = field_validator("text")(_validate_semantic_text)


# ── v4 blocks (BCR layout contract) ───────────────────────────────────────


class ListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    children: list["ListItem"] = Field(default_factory=list)

    _text_is_semantic = field_validator("text")(_validate_semantic_text)


class ListBlock(_BlockModel):
    type: Literal["list"] = "list"
    ordered: bool = False
    items: list[ListItem] = Field(default_factory=list, min_length=1)


class KeyValueItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1)
    value: str = Field(min_length=1)

    _label_is_semantic = field_validator("label")(_validate_semantic_text)
    _value_is_semantic = field_validator("value")(_validate_semantic_text)


class KeyValueBlock(_BlockModel):
    type: Literal["key_value"] = "key_value"
    items: list[KeyValueItem] = Field(min_length=1)
    columns: int = Field(default=2, ge=1, le=4)


class FindingSummaryBlock(_BlockModel):
    type: Literal["finding_summary"] = "finding_summary"
    finding_refs: list[str] = Field(min_length=1)
    columns: list[str] = Field(default_factory=lambda: ["finding_id", "risk_level", "title", "status"])


class FindingDetailBlock(_BlockModel):
    type: Literal["finding_detail"] = "finding_detail"
    finding_ref: str = Field(min_length=1)
    field_order: list[str] = Field(
        default_factory=lambda: ["statement", "legal_basis", "recommendation", "suggested_revision"]
    )


class FindingReferenceBlock(_BlockModel):
    type: Literal["finding_reference"] = "finding_reference"
    finding_ref: str = Field(min_length=1)
    note: str = ""

    _note_is_semantic = field_validator("note")(_validate_semantic_text)


class ClauseGroupBlock(_BlockModel):
    type: Literal["clause_group"] = "clause_group"
    title: str = Field(min_length=1)
    clauses: list[ClauseNode] = Field(min_length=1)

    _title_is_semantic = field_validator("title")(_validate_semantic_text)


class PageBreakBlock(_BlockModel):
    type: Literal["page_break"] = "page_break"
    reason: str = Field(min_length=1)

    _reason_is_semantic = field_validator("reason")(_validate_semantic_text)


class CitationNoteBlock(_BlockModel):
    type: Literal["citation_note"] = "citation_note"
    citation_refs: list[str] = Field(min_length=1)


Block = Annotated[
    Union[
        ParagraphBlock,
        ClaimBlock,
        ListBlock,
        TableBlock,
        WarningBlock,
        KeyValueBlock,
        FindingSummaryBlock,
        FindingDetailBlock,
        FindingReferenceBlock,
        ClauseGroupBlock,
        PageBreakBlock,
        CitationNoteBlock,
    ],
    Field(discriminator="type"),
]

ListItem.model_rebuild()
