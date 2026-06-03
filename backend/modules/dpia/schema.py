"""DPIA (Data Protection Impact Assessment) schemas under GDPR Article 35.

Input model ── 7-group DPIA template fields.
Output model ── full draft generation result with risk matrix and mitigation plan.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Input sub-models
# ---------------------------------------------------------------------------


class RiskInput(BaseModel):
    """A single risk identified before DPIA drafting."""

    risk_id: str = Field(min_length=1)
    risk_description: str = Field(min_length=2)
    likelihood: Literal["low", "medium", "high"] = "medium"
    impact: Literal["low", "medium", "high"] = "medium"
    affected_data_subjects: str = ""
    risk_source: Literal[
        "processing_activity", "data_type", "technology",
        "third_party", "organizational", "other",
    ] = "other"


class MitigationInput(BaseModel):
    """A single mitigation measure proposed before DPIA drafting."""

    mitigation_id: str = Field(min_length=1)
    description: str = Field(min_length=2)
    target_risk_ids: list[str] = Field(default_factory=list)
    status: Literal["planned", "in_progress", "implemented", "verified"] = "planned"
    responsible_party: str = ""


# ---------------------------------------------------------------------------
# DPIARequest — 7-group input aligned with ICO DPIA template
# ---------------------------------------------------------------------------


class DPIARequest(BaseModel):
    # ── 1. Identify need ──
    project_name: str = Field(min_length=2)
    project_goal: str = Field(min_length=2)
    dpia_trigger_reasons: list[str] = Field(default_factory=list)

    # ── 2. Describe processing ──
    processing_flow_description: str = Field(min_length=2)
    data_categories: list[str] = Field(default_factory=list)
    special_category_data: bool = False
    special_category_types: list[str] = Field(default_factory=list)
    data_subject_categories: list[str] = Field(default_factory=list)
    data_subject_count: str = ""
    retention_period: str = ""
    cross_border_transfer: bool = False
    transfer_destination: str = ""
    automated_decision_making: bool = False
    systematic_monitoring: bool = False
    large_scale_processing: bool = False
    data_matching: bool = False
    new_technology: bool = False
    vulnerable_data_subjects: bool = False

    # ── 3. Consultation ──
    consulted_internal_departments: list[str] = Field(default_factory=list)
    external_experts: list[str] = Field(default_factory=list)
    data_subject_consultation_plan: str = ""

    # ── 4. Necessity & proportionality ──
    lawful_basis: list[str] = Field(default_factory=list)
    necessity_statement: str = ""
    proportionality_statement: str = ""
    transparency_information: str = ""

    # ── 5. Risk assessment ──
    identified_risks: list[RiskInput] = Field(default_factory=list)

    # ── 6. Mitigation ──
    mitigation_measures: list[MitigationInput] = Field(default_factory=list)

    # ── 7. Sign-off & record ──
    dpia_owner: str = ""
    dpo_name: str = ""
    dpo_opinion: str = ""
    review_date: str = ""

    # Attachments
    uploaded_files: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Output sub-models
# ---------------------------------------------------------------------------


class DPIAProjectProfile(BaseModel):
    """Processing-activity profile (not company profile)."""

    project_name: str
    project_goal: str
    processing_flow_description: str
    data_categories: list[str]
    special_category_data: bool
    special_category_types: list[str] = Field(default_factory=list)
    data_subject_categories: list[str] = Field(default_factory=list)
    data_subject_count: str = ""
    retention_period: str = ""
    cross_border_transfer: bool = False
    transfer_destination: str = ""
    automated_decision_making: bool = False
    systematic_monitoring: bool = False
    large_scale_processing: bool = False
    data_matching: bool = False
    new_technology: bool = False
    vulnerable_data_subjects: bool = False
    lawful_basis: list[str] = Field(default_factory=list)
    dpia_trigger_reasons: list[str] = Field(default_factory=list)
    dpo_name: str = ""
    dpo_opinion: str = ""
    extracted_notes: list[str] = Field(default_factory=list)
    attachment_metadata: list[dict] = Field(default_factory=list)


class DPIANeedAssessment(BaseModel):
    """Whether a DPIA is required and why."""

    dpia_required: bool
    trigger_reasons: list[str] = Field(default_factory=list)
    legal_basis: list[str] = Field(default_factory=list)
    prior_consultation_possible: bool = False
    reasoning: str = ""


class DPIARiskMatrixItem(BaseModel):
    risk_id: str
    risk_description: str
    likelihood: str  # low / medium / high
    impact: str      # low / medium / high
    risk_level: str   # low / medium / high (likelihood × impact)
    affected_data_subjects: str = ""
    risk_source: str = ""


class DPIAMitigationItem(BaseModel):
    mitigation_id: str
    description: str
    target_risk_ids: list[str] = Field(default_factory=list)
    status: str = "planned"
    responsible_party: str = ""
    residual_risk_level: str = ""


class RegulationHit(BaseModel):
    """Lightweight regulation hit (compatible with assessment's RegulationHit)."""

    source_id: str
    title: str
    article: str = ""
    snippet: str = ""


class DPIAChapterContent(BaseModel):
    chapter_no: int
    title: str
    content: str
    citations: list[str] = Field(default_factory=list)
    risk_level: str = "medium"
    footnote_map: dict | None = None


class DPIAResult(BaseModel):
    task_id: str
    state: str
    report_path: str
    output_files: dict[str, str] = Field(default_factory=dict)
    profile: DPIAProjectProfile
    regulations: list[RegulationHit] = Field(default_factory=list)
    chapters: list[DPIAChapterContent] = Field(default_factory=list)
    consistency_issues: list[str] = Field(default_factory=list)
    need_assessment: DPIANeedAssessment | None = None
    risk_matrix: list[DPIARiskMatrixItem] = Field(default_factory=list)
    mitigation_plan: list[DPIAMitigationItem] = Field(default_factory=list)

    # ── Agent enrichment fields ──
    processing_activity_pack: dict | None = None
    necessity_findings: dict | None = None
    dpo_decision_pack: dict | None = None
    internal_ai_review: dict | None = None
    consistency_report: dict | None = None
    generation_basis_snapshot: dict | None = None
    trace_manifest_path: str = ""


# ── Agent-specific I/O models (per doc/tmp/dpia) ──


class DPIANeedAgentInput(BaseModel):
    """Input for DPIA Need Agent (Section 2)."""
    project_profile: dict = Field(default_factory=dict)
    rule_signals: dict = Field(default_factory=dict)
    legal_candidates: list[str] = Field(default_factory=list)


class DPIANeedAgentOutput(BaseModel):
    """Output from DPIA Need Agent."""
    agent_name: str = "DPIANeedAgent"
    dpia_required: bool = False
    trigger_reasons: list[dict] = Field(default_factory=list)
    draft_text: str = ""
    legal_basis_refs: list[str] = Field(default_factory=list)
    confidence: str = "MEDIUM"


class ProcessingActivityPack(BaseModel):
    """Processing activity description pack (Section 3)."""
    processing_steps: list[dict] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)
    data_categories: list[str] = Field(default_factory=list)
    data_subjects: list[str] = Field(default_factory=list)
    recipients: list[str] = Field(default_factory=list)
    retention_periods: list[str] = Field(default_factory=list)
    cross_border_transfer: dict = Field(default_factory=dict)
    ambiguities: list[str] = Field(default_factory=list)
    draft_text: str = ""


class NecessityFinding(BaseModel):
    """Necessity & Proportionality finding (Section 4)."""
    processing: str = ""
    reason: str = ""


class NecessityFindings(BaseModel):
    """Necessity & Proportionality analysis output."""
    agent_name: str = "NecessityProportionalityAgent"
    necessary_processing: list[NecessityFinding] = Field(default_factory=list)
    questionable_processing: list[NecessityFinding] = Field(default_factory=list)
    excessive_data_items: list[str] = Field(default_factory=list)
    less_intrusive_alternatives: list[str] = Field(default_factory=list)
    data_minimisation_recommendations: list[str] = Field(default_factory=list)
    draft_text: str = ""


class RiskMatrixEntry(BaseModel):
    """Single risk in risk matrix (Section 5)."""
    risk_id: str = ""
    risk_name: str = ""
    description: str = ""
    affected_rights: list[str] = Field(default_factory=list)
    likelihood: str = "MEDIUM"
    impact: str = "MEDIUM"
    overall_level: str = "MEDIUM"
    related_processing_steps: list[str] = Field(default_factory=list)
    related_facts: list[str] = Field(default_factory=list)
    related_legal_basis: list[str] = Field(default_factory=list)
    reasoning: str = ""


class RiskMatrix(BaseModel):
    """Full risk assessment output."""
    agent_name: str = "RiskAssessmentAgent"
    risk_matrix: list[RiskMatrixEntry] = Field(default_factory=list)
    draft_text: str = ""


class MitigationMeasure(BaseModel):
    """Single mitigation measure (Section 6)."""
    measure: str = ""
    status: Literal["planned", "implemented", "missing"] = "planned"
    effect: str = ""
    verification: str = ""


class MitigationPlanEntry(BaseModel):
    """Risk → measures mapping."""
    risk_id: str = ""
    measures: list[MitigationMeasure] = Field(default_factory=list)
    residual_risk: str = "MEDIUM"
    additional_actions_required: list[str] = Field(default_factory=list)


class MitigationPlan(BaseModel):
    """Full mitigation plan output."""
    agent_name: str = "MitigationMappingAgent"
    mitigation_plan: list[MitigationPlanEntry] = Field(default_factory=list)
    draft_text: str = ""


class DPODecisionPack(BaseModel):
    """DPO / Prior Consultation decision (Section 7)."""
    agent_name: str = "DPOPriorConsultationAgent"
    dpo_position: Literal["approval", "conditional_approval", "objection"] = "conditional_approval"
    conditions: list[str] = Field(default_factory=list)
    prior_consultation_recommended: bool = False
    reason: str = ""
    draft_text: str = ""


class InternalReviewOutput(BaseModel):
    """Internal AI review output (Section 9)."""
    agent_name: str = "InternalReviewAgent"
    overall_risk_judgment: str = ""
    high_risk_issues: list[str] = Field(default_factory=list)
    insufficient_evidence_items: list[str] = Field(default_factory=list)
    planned_vs_implemented_gaps: list[str] = Field(default_factory=list)
    dpo_preconditions: list[str] = Field(default_factory=list)
    recommend_delay_launch: bool = False
    material_supplement_priority: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    draft_text: str = ""


class ConsistencyReport(BaseModel):
    """Consistency / Repair check output (Section 10)."""
    agent_name: str = "ConsistencyRepairAgent"
    checks_passed: int = 0
    checks_total: int = 10
    blocking_issues: list[dict] = Field(default_factory=list)
    repairs_applied: list[dict] = Field(default_factory=list)
    needs_manual_review: bool = False
    final_status: Literal["ready", "needs_repair", "blocked"] = "needs_repair"
    draft_text: str = ""


class DPIAAsyncAccepted(BaseModel):
    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int


class DPIAAsyncStatus(BaseModel):
    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int
    created_at: str
    updated_at: str
    error: str | None = None
    result: DPIAResult | None = None
