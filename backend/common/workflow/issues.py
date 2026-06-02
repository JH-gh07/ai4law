from typing import Literal

from pydantic import BaseModel, Field


IssueCategory = Literal[
    # ── CN assessment ──
    "path",
    "data_scope",
    "data_classification",
    "necessity",
    "consent",
    "recipient",
    "contract",
    "legal_document",
    "onward_transfer",
    "security_measure",
    "documentation",
    "anonymization",
    "link_complexity",
    "internal_approval",
    "remediation",
    "expression",
    # ── EU DPIA ──
    "dpia_trigger",
    "automated_decision",
    "profiling",
    "special_category",
    "large_scale",
    "systematic_monitoring",
    "data_matching",
    "new_technology",
    "vulnerable_subjects",
    "necessity_proportionality",
    "lawful_basis",
    "transparency",
    "discrimination",
    "function_creep",
    "cross_border",
    "mitigation_gap",
    "prior_consultation",
    # ── fallback ──
    "other",
]
IssueSeverity = Literal["LOW", "MEDIUM", "HIGH", "BLOCKER"]


class IssueItem(BaseModel):
    issue_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    category: IssueCategory
    severity: IssueSeverity
    fact_refs: list[str] = Field(default_factory=list)
    rule_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    recommended_action: str = Field(min_length=1)
    affects_outputs: list[str] = Field(default_factory=list)
    missing_materials: list[str] = Field(default_factory=list)
    internal_review_required: bool = Field(default=True)
    external_report_strategy_required: bool = Field(default=True)
