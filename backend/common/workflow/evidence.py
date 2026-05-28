from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    evidence_id: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    fact_refs: list[str] = Field(min_length=1)
    rule_refs: list[str] = Field(default_factory=list)
    conclusion: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    used_by: list[str] = Field(default_factory=list)
