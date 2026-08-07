"""Typed semantic blocks emitted by the structured report protocol."""

from __future__ import annotations

import re
from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

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


class ListBlock(_BlockModel):
    type: Literal["list"] = "list"
    ordered: bool = False
    items: list[str] = Field(default_factory=list, min_length=1)

    @field_validator("items")
    @classmethod
    def items_are_semantic(cls, value: list[str]) -> list[str]:
        for item in value:
            _validate_semantic_text(item)
        return value


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


Block = Annotated[
    Union[ParagraphBlock, ClaimBlock, ListBlock, TableBlock, WarningBlock],
    Field(discriminator="type"),
]
