"""L1 Platform base model — Issue / Risk layer.

Every compliance gap, risk finding, or material deficiency is represented as an
IssueItem.  Issues form the bridge between raw facts and the final report:
each issue must reference the facts it depends on, the rules that were checked,
and the evidence that supports (or fails to support) the conclusion.

Three-tier certainty classification (NEW) ensures that the report generator
does not treat a suspected issue the same way as a confirmed one.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Enumerations ──────────────────────────────────────────────────────────

IssueCategory = Literal[
    # ── CN path / data ──
    "path",
    "data_scope",
    "data_classification",
    "necessity",
    "consent",
    "rights_protection",
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
    # ── US CPRA ──
    "sale_or_share",
    "opt_out",
    "spi_risk",
    "vendor_contract",
    "dark_pattern",
    # ── Multi-jurisdiction ──
    "cross_jurisdiction_conflict",
    # ── fallback ──
    "other",
]

IssueSeverity = Literal["LOW", "MEDIUM", "HIGH", "BLOCKER"]

IssueCertainty = Literal[
    "confirmed_issue",       # rule hit or clear documentary gap
    "suspected_issue",       # Agent inference, evidence insufficient
    "default_review_item",   # template must-check item, no material to confirm or deny
]


# ── Core model ────────────────────────────────────────────────────────────

class IssueItem(BaseModel):
    """A single compliance issue — the platform's unit of risk communication.

    Every issue MUST link to:
      - fact_refs    → the FactItem(s) that triggered it
      - rule_refs    → the rule(s) that were checked
      - evidence_refs → the EvidenceItem(s) that support or fail to support compliance

    This triangular reference chain is the foundation of the platform's
    auditability guarantee.
    """

    issue_id: str = Field(min_length=1, description="Unique issue identifier")
    title: str = Field(min_length=1, description="Short human-readable title")
    description: str = Field(
        min_length=1, description="Detailed description of the finding"
    )

    # ── Classification ──
    category: IssueCategory = Field(
        description="Which domain this issue belongs to"
    )
    severity: IssueSeverity = Field(
        description="Risk severity of this specific issue"
    )
    issue_certainty: IssueCertainty = Field(
        default="default_review_item",
        description=(
            "How certain the system is that this is a real issue.\n"
            "  confirmed_issue      → use assertive language in external report\n"
            "  suspected_issue      → use hedging language ('尚无法确认', '可能存在')\n"
            "  default_review_item  → use advisory language ('建议核验', '建议补充')\n"
        ),
    )

    # ── Reference chain (the audit backbone) ──
    fact_refs: list[str] = Field(
        default_factory=list,
        description="FactItem.fact_id values this issue is based on",
    )
    rule_refs: list[str] = Field(
        default_factory=list,
        description="RuleHit.rule_id values that triggered this issue",
    )
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="EvidenceItem.evidence_id values supporting or contradicting",
    )

    # ── Action guidance ──
    recommended_action: str = Field(
        min_length=1,
        description="What the user should do about this issue",
    )
    affects_outputs: list[str] = Field(
        default_factory=list,
        description="Which output artefacts this issue should appear in",
    )
    missing_materials: list[str] = Field(
        default_factory=list,
        description="Materials the user should provide to resolve this issue",
    )

    # ── Report strategy ──
    internal_review_required: bool = Field(
        default=True,
        description="Should appear in internal review? (almost always yes)",
    )
    external_report_strategy_required: bool = Field(
        default=True,
        description="Does the writing planner need to decide how to phrase this?",
    )
    can_enter_external_report: bool = Field(
        default=True,
        description=(
            "If False, this issue is for internal review only "
            "(e.g. raw suspicion, uncertain inference)."
        ),
    )

    @field_validator("recommended_action", mode="before")
    @classmethod
    def ensure_recommended_action_nonempty(cls, value: Any) -> str:
        """防穿透：保证 recommended_action 永不为空或全空白。

        使用 mode="before" 在 Pydantic min_length=1 校验之前拦截空串，
        避免 ValidationError。这是一个平台级安全网——无论哪个模块构造
        IssueItem，只要 recommended_action 为空字符串或仅含空白，
        就自动填入通用整改建议。
        """
        if isinstance(value, str) and (not value or not value.strip()):
            return (
                "针对发现的问题进行详细评估，根据适用法规完成合规整改，"
                "并补充相关材料以确保合规。"
            )
        return value
