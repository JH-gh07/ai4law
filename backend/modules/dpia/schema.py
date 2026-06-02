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
