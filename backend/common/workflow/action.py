"""L1 Platform base model — Remediation Action layer.

Actions translate compliance issues into concrete, executable next steps:
specific clause replacements, material checklists, and staged implementation
roadmaps.  Every action must declare what issue(s) it addresses and what
evidence supports the required change.
"""

from typing import Literal

from pydantic import BaseModel, Field


# ── Enumerations ──────────────────────────────────────────────────────────

ActionPriority = Literal["P0", "P1", "P2"]


# ── Core models ───────────────────────────────────────────────────────────

class RemediationAction(BaseModel):
    """A single executable remediation step.

    Unlike an IssueItem (which describes *what is wrong*), a RemediationAction
    describes *what to do about it* — with suggested replacement text, owner
    hints, and verifiable acceptance criteria.
    """

    action_id: str = Field(min_length=1, description="Unique action identifier")
    priority: ActionPriority = Field(
        description="P0 = blocking, must fix before filing; P1 = fix before filing; P2 = optimisation"
    )

    # ── What to fix ──
    target: str = Field(
        min_length=1,
        description="What needs to change: clause reference, system name, process step",
    )
    action: str = Field(
        min_length=1,
        description="Human-readable description of the required action",
    )
    issue_refs: list[str] = Field(
        default_factory=list,
        description="IssueItem.issue_id values this action addresses",
    )

    # ── How to fix ──
    suggested_text: str | None = Field(
        default=None,
        description="Replaceable clause text or configuration change description",
    )
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="EvidenceItem.evidence_id values backing this recommendation",
    )
    legal_basis: list[str] = Field(
        default_factory=list,
        description="Citation IDs (CitationItem.citation_id) that mandate this action",
    )

    # ── Who and when ──
    owner_hint: str = Field(
        default="",
        description="Suggested responsible role: Legal / DPO / Engineering / Product",
    )
    estimated_phase: Literal["short_term", "mid_term", "long_term"] = "short_term"

    # ── Verification ──
    acceptance_criteria: list[str] = Field(
        default_factory=list,
        description="Verifiable conditions that must be met for this action to be considered complete",
    )


class MaterialItem(BaseModel):
    """A single missing material that the user should provide."""

    material_name: str = Field(min_length=1)
    why_needed: str = Field(
        min_length=1,
        description="Why this material is required (link to regulation or template requirement)",
    )
    affected_chapters: list[str] = Field(
        default_factory=list,
        description="Report chapters whose content depends on this material",
    )
    affected_issues: list[str] = Field(
        default_factory=list,
        description="IssueItem.issue_id values that could be resolved with this material",
    )
    priority: ActionPriority = "P1"
    suggested_file_format: str = Field(
        default="",
        description="e.g. 'PDF scan of signed agreement', 'XLSX data inventory'",
    )


class StagePlan(BaseModel):
    """A phased implementation roadmap grouping actions by urgency."""

    phase: Literal["short_term", "mid_term", "long_term"] = Field(
        description="short_term = before filing, mid_term = within quarter, long_term = ongoing"
    )
    label: str = Field(
        default="",
        description="Human-readable phase label (e.g. '备案前必须完成')",
    )
    actions: list[RemediationAction] = Field(default_factory=list)
    estimated_timeline: str = Field(
        default="",
        description="e.g. '4-6 weeks', '3 months'",
    )


# ── Aggregation ───────────────────────────────────────────────────────────

class ActionPlan(BaseModel):
    """Complete remediation plan for a module run."""

    module: str = Field(min_length=1)
    actions: list[RemediationAction] = Field(default_factory=list)
    materials: list[MaterialItem] = Field(default_factory=list)
    roadmap: list[StagePlan] = Field(default_factory=list)

    # ── Counters ──
    p0_count: int = 0
    p1_count: int = 0
    p2_count: int = 0
