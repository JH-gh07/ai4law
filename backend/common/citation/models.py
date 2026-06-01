from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

CitationType = Literal[
    "law_article",
    "official_guide",
    "template_requirement",
    "standard_clause",
    "user_material",
]

AuthorityLevel = Literal["high", "medium", "low"]
BindingForce = Literal["mandatory", "recommended", "reference"]


@dataclass
class CitationItem:
    """A single citable reference — law article, guide clause, standard, or user material.

    Stored in-memory per report via CitationRegistry; not an ORM model.
    """

    citation_id: str
    source_id: str
    chunk_id: str = ""
    citation_type: CitationType = "law_article"
    title: str = ""
    article_no: str = ""
    quote_text: str = ""
    source_file_id: str = ""
    page_no: int = 0
    related_issue_ids: list[str] = field(default_factory=list)
    related_fact_ids: list[str] = field(default_factory=list)
    related_evidence_ids: list[str] = field(default_factory=list)
    confidence_score: float = 0.0
    authority_level: AuthorityLevel = "medium"
    binding_force: BindingForce = "recommended"

    def to_dict(self) -> dict:
        return {
            "citation_id": self.citation_id,
            "source_id": self.source_id,
            "chunk_id": self.chunk_id,
            "citation_type": self.citation_type,
            "title": self.title,
            "article_no": self.article_no,
            "quote_text": self.quote_text,
            "source_file_id": self.source_file_id,
            "page_no": self.page_no,
            "related_issue_ids": self.related_issue_ids,
            "related_fact_ids": self.related_fact_ids,
            "related_evidence_ids": self.related_evidence_ids,
            "confidence_score": self.confidence_score,
            "authority_level": self.authority_level,
            "binding_force": self.binding_force,
        }
