from typing import Any

from pydantic import BaseModel, Field

from backend.common.workflow.evidence import EvidenceItem
from backend.common.workflow.facts import FactItem
from backend.common.workflow.issues import IssueItem


class GenerationContextPack(BaseModel):
    module_key: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    facts: list[FactItem]
    diagnosis_result: dict | None = None
    regulations: list[dict]
    issues: list[IssueItem]
    evidence_chain: list[EvidenceItem] = Field(default_factory=list)
    path_warning: str | None = None
    risk_summary: dict | None = None
    attachment_notes: list[dict] = Field(default_factory=list)
    output_requirements: dict = Field(default_factory=dict)
    legal_grounding: dict[str, Any] | None = None
    writing_strategy: dict[str, Any] | None = None
    generation_basis_pack: dict[str, Any] | None = None
