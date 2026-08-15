"""TIA module schemas — structured input models for transfer impact assessment."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from backend.domains.us.cpra.schema import CPRACitationRef


class TIAAttachment(BaseModel):
    file_role: Literal["transfer_agreement", "country_law_analysis", "technical_control_doc", "other"]
    file_name: str = Field(min_length=1)
    file_format: Literal["docx", "pdf"]
    storage_uri: str = Field(min_length=1)
    size_bytes: int | None = Field(default=None, ge=1)
    checksum_sha256: str | None = None


# ── NEW: Structured input models ───────────────────────────────────────

DataCategory = Literal[
    "contact_information", "transaction_records", "crm_data",
    "employee_data", "hr_records", "financial_data",
    "health_data", "genetic_data", "biometric_data",
    "clinical_trial_data", "political_opinion", "religious_belief",
    "children_data", "location_data", "behavioral_data",
    "communication_content", "other",
]

TransferTool = Literal["scc", "bcr", "derogation", "adequacy_decision", "unknown"]
GDPRRole = Literal["controller", "processor", "joint_controller", "subprocessor", "unknown"]


class TIAStructuredInput(BaseModel):
    """Structured transfer facts — enables independent system assessment."""
    exporter_country: str = ""
    importer_country: str = ""
    destination_country: str = ""
    exporter_role: GDPRRole = "unknown"
    importer_role: GDPRRole = "unknown"
    transfer_purpose: str = ""
    data_categories: list[DataCategory] = Field(default_factory=list)
    has_special_category_data: bool = False
    special_category_types: list[str] = Field(default_factory=list)
    data_subjects: list[str] = Field(default_factory=list)
    transfer_frequency: str = ""
    transfer_scale: str = ""
    encryption_before_transfer: bool = False
    key_managed_in_eu: bool = False
    has_end_to_end_encryption: bool = False
    has_secure_enclave: bool = False
    has_key_separation: bool = False


# ── Route decider output ───────────────────────────────────────────────

class TIARouteDecision(BaseModel):
    route: Literal["adequacy_simplified", "full_tia_scc", "full_tia_bcr",
                    "derogation_exception", "missing_or_invalid_tool"] = "full_tia_scc"
    need_full_tia: bool = True
    adequacy_decision_exists: bool = False
    adequacy_country: str = ""
    adequacy_notes: list[str] = Field(default_factory=list)
    reason: str = ""


# ── Country risk assessment ────────────────────────────────────────────

class TIACountryRisk(BaseModel):
    country: str
    has_adequacy: bool = False
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "VERY_HIGH"] = "MEDIUM"
    risk_sources: list[str] = Field(default_factory=list)
    gov_access_risk: bool = False
    effective_remedy: bool = True
    independent_oversight: bool = True
    notes: str = ""


# ── Supplementary measure assessment ───────────────────────────────────

class TIAMeasureAssessment(BaseModel):
    measure_name: str = ""
    measure_type: Literal["contractual", "organizational", "technical_weak",
                           "technical_strong", "technical_extreme"] = "contractual"
    sufficient_for_risk: bool = False
    assessment: str = ""


class TIADecision(BaseModel):
    """Deterministic transfer decision; model reviews cannot override it."""

    transfer_status: Literal["proceed", "proceed_with_conditions", "suspend"]
    inherent_risk: Literal["LOW", "MEDIUM", "HIGH", "VERY_HIGH"]
    residual_risk: Literal["LOW", "MEDIUM", "HIGH", "VERY_HIGH"]
    measure_sufficiency: Literal[
        "sufficient", "conditional", "highly_conditional", "insufficient", "unknown",
    ] = "unknown"
    evidence_status: Literal["verified", "partial", "missing"]
    reasons: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    mandatory_conditions: list[str] = Field(default_factory=list)
    decision_source: Literal["deterministic_rule"] = "deterministic_rule"


# ── Request (backward compat) ──────────────────────────────────────────

class TIARequest(BaseModel):
    # Original form fields（structured_input 存在时可空，见下方 validator）
    transfer_tool: Literal["scc", "bcr", "derogation"]
    data_exporter_profile: str = Field(default="")
    data_importer_profile: str = Field(default="")
    third_country_assessment: str = Field(default="")
    supplementary_measures: str = Field(default="")
    final_conclusion: str = Field(default="")
    attachments: list[TIAAttachment] = Field(default_factory=list)
    # NEW structured fields (all Optional)
    structured_input: TIAStructuredInput | None = None

    @model_validator(mode="after")
    def _legacy_fields_required_without_structured_input(self) -> "TIARequest":
        if self.structured_input is None:
            missing = [
                name
                for name in (
                    "data_exporter_profile",
                    "data_importer_profile",
                    "third_country_assessment",
                    "supplementary_measures",
                    "final_conclusion",
                )
                if not getattr(self, name).strip()
            ]
            if not self.attachments:
                missing.append("attachments")
            if missing:
                raise ValueError(
                    "TIA legacy form fields required when structured_input is absent: "
                    + ", ".join(missing)
                )
        return self


# ── Output ─────────────────────────────────────────────────────────────

class TIAChapter(BaseModel):
    chapter_no: int
    title: str
    content: str
    citations: list[str] = Field(default_factory=list)
    citation_refs: list[CPRACitationRef] = Field(default_factory=list)
    risk_level: str


class TIAResult(BaseModel):
    report_path: str
    output_files: dict[str, str] = Field(default_factory=dict)
    transfer_tool: str
    risk_level: str
    chapters: list[TIAChapter]
    consistency_issues: list[str]
    attachment_notes: list[str] = Field(default_factory=list)
    # NEW
    route_decision: TIARouteDecision | None = None
    country_risk: TIACountryRisk | None = None
    measure_assessments: list[TIAMeasureAssessment] = Field(default_factory=list)
    decision: TIADecision | None = None


class TIAAsyncAccepted(BaseModel):
    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int


class TIAAsyncStatus(BaseModel):
    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int
    created_at: str
    updated_at: str
    error: str | None = None
    result: TIAResult | None = None
