"""Citation identity and deterministic numbering for DocumentIR."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CitationLocator(BaseModel):
    model_config = ConfigDict(extra="forbid")

    article: str | None = None
    paragraph: str | None = None
    item: str | None = None


class CitationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    citation_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_type: Literal["regulation", "standard", "policy_qa", "case", "guide", "user_material"]
    title: str = Field(min_length=1)
    locator: CitationLocator | None = None
    knowledge_id: str | None = None
    evidence_unit_id: str | None = None
    authority_level: Literal["high", "medium", "low"] = "medium"
    binding_force: Literal["mandatory", "recommended", "reference"] = "reference"
    can_enter_external_report: bool = False


class CitationRegistry:
    """Per-document citation registry; IDs are stable, numbers are derived."""

    def __init__(self, records: list[CitationRecord] | None = None) -> None:
        self._records: dict[str, CitationRecord] = {}
        self._numbers: dict[str, int] = {}
        self._next_number = 1
        for record in records or []:
            self.register(record)

    def register(self, record: CitationRecord) -> str:
        existing = self._records.get(record.citation_id)
        if existing is not None and existing != record:
            raise ValueError(f"citation_id already registered with different content: {record.citation_id}")
        self._records[record.citation_id] = record
        return record.citation_id

    def resolve(self, citation_id: str) -> CitationRecord | None:
        return self._records.get(citation_id)

    def assign_footnote_number(self, citation_id: str) -> int | None:
        if citation_id not in self._records:
            return None
        if citation_id not in self._numbers:
            self._numbers[citation_id] = self._next_number
            self._next_number += 1
        return self._numbers[citation_id]

    def footnote_map(self) -> dict[str, int]:
        return dict(self._numbers)

    def records(self) -> dict[str, CitationRecord]:
        return dict(self._records)
