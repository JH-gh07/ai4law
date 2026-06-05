from __future__ import annotations

from pydantic import BaseModel, Field


class CitationDetailResponse(BaseModel):
    citation_id: str
    module: str = ""
    source_id: str
    jurisdiction: str = ""
    display_label: str = ""
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
    source_kind: str = "law_article"
    allowed_usage: list[str] = Field(default_factory=list)
    can_enter_external_report: bool = True
    external_report_allowed: bool = True
    confidence_threshold: float = 0.20
    knowledge_url: str = ""
    anchor: str = ""
    section_id: str = ""
    clause_id: str = ""
    open_mode: str = "new_tab"
    can_jump: bool = False
    source_url: str = ""


class CitationMapResponse(BaseModel):
    task_id: str
    module: str = ""
    footnote_map: dict[str, CitationDetailResponse]
    citation_count: int
