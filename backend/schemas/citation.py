from __future__ import annotations

from pydantic import BaseModel, Field


class CitationDetailResponse(BaseModel):
    citation_id: str
    source_id: str
    citation_type: str
    title: str
    article_no: str = ""
    quote_text: str = ""
    authority_level: str = "medium"
    binding_force: str = "recommended"
    related_issue_ids: list[str] = Field(default_factory=list)
    related_fact_ids: list[str] = Field(default_factory=list)
    related_evidence_ids: list[str] = Field(default_factory=list)
    confidence_score: float = 0.0
    footnote_number: int | None = None


class CitationMapResponse(BaseModel):
    task_id: str
    footnote_map: dict[str, CitationDetailResponse]
    citation_count: int
