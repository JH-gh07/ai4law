from typing import Any, Literal

from pydantic import BaseModel, Field

EvidenceStatus = Literal[
    "user_claim_only",
    "partial_evidence",
    "documented_evidence",
    "verified_evidence",
]


class FactItem(BaseModel):
    fact_id: str = Field(min_length=1)
    source_type: Literal["schema", "attachment", "user_text", "diagnosis", "derived"]
    source_ref: str | None = None
    field_path: str | None = None
    value: Any
    normalized_value: Any | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    notes: str | None = None
    evidence_status: EvidenceStatus = Field(default="user_claim_only")
    supporting_material_refs: list[str] = Field(default_factory=list)
    can_support_external_positive_claim: bool = Field(default=False)
