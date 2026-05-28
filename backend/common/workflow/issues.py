from typing import Literal

from pydantic import BaseModel, Field


IssueCategory = Literal[
    "path",
    "data_scope",
    "consent",
    "recipient",
    "contract",
    "security_measure",
    "documentation",
    "other",
]
IssueSeverity = Literal["LOW", "MEDIUM", "HIGH", "BLOCKER"]


class IssueItem(BaseModel):
    issue_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    category: IssueCategory
    severity: IssueSeverity
    fact_refs: list[str] = Field(min_length=1)
    rule_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    recommended_action: str = Field(min_length=1)
    affects_outputs: list[str] = Field(default_factory=list)
