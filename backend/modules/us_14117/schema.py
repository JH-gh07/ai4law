"""EO 14117 compliance assessment schemas.

Implements the full data model for:
- Data items with DOJ category classification fields
- Entity and access person screening
- Security measure tracking
- Risk matrix and traffic light decisions
- Report generation output
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Input sub-models
# ---------------------------------------------------------------------------

TrafficLight = Literal["RED", "YELLOW", "GREEN"]
DOJDataCategory = Literal[
    "human_genomic_data",
    "biometric_identifiers",
    "precise_geolocation_data",
    "personal_health_data",
    "personal_financial_data",
    "covered_personal_identifiers",
    "government_related_data",
    "not_14117_data",
]
SecurityMeasureCategory = Literal[
    "access_control", "encryption", "data_minimization",
    "audit_logging", "personnel_controls", "contractual_controls",
]
SecurityMeasureStatus = Literal["implemented", "planned", "missing"]


class US14117DataItem(BaseModel):
    """A single data item subject to EO 14117 classification."""

    data_item_name: str = Field(min_length=1)
    data_description: str = ""
    business_context: str = ""
    is_personal_info: bool = False
    is_sensitive_personal_info: bool = False
    us_person_count: int = Field(default=0, ge=0)
    data_subject_type: str = ""  # consumer, employee, patient, etc.
    doj_data_category: DOJDataCategory | str = "not_14117_data"
    precision_level: str = ""  # raw, aggregated, anonymized, pseudonymized
    is_government_related: bool = False
    export_necessity: str = ""


class US14117Entity(BaseModel):
    """An entity receiving or accessing US person data."""

    entity_name: str = Field(min_length=2)
    country_of_registration: str = Field(min_length=2)
    tax_id: str = ""
    ownership_structure: str = ""  # free-text ownership description
    governing_law: str = ""
    government_control: bool = False
    government_investment: str = ""  # description of government investment
    parent_company: str = ""
    entity_role: str = "processor"  # processor, controller, subprocessor, affiliate, vendor
    is_covered_person: bool | None = None  # None = system should infer


class US14117AccessPerson(BaseModel):
    """A person with actual or potential access to the data."""

    person_name: str = Field(min_length=1)
    nationality: str = ""
    country_of_residence: str = ""
    department: str = ""
    position: str = ""
    employer: str = ""  # empty means same as entity
    has_actual_access: bool = True
    access_type: str = ""  # direct, remote, indirect


class US14117SecurityMeasure(BaseModel):
    """A single security measure relevant to EO 14117 restricted transactions."""

    measure_name: str = Field(min_length=1)
    category: SecurityMeasureCategory | str = "access_control"
    status: SecurityMeasureStatus | str = "missing"
    description: str = ""


# ---------------------------------------------------------------------------
# US14117Request
# ---------------------------------------------------------------------------


class US14117Request(BaseModel):
    """EO 14117 compliance assessment request."""

    project_name: str = Field(min_length=2)
    transaction_description: str = Field(min_length=2)
    transaction_type: str = Field(
        default="vendor_agreement",
        description=(
            "vendor_agreement, employment_agreement, investment_agreement, "
            "data_brokerage, cooperative_research, cloud_remote_access, "
            "onward_transfer, or other"
        ),
    )
    data_items: list[US14117DataItem] = Field(min_length=1)
    recipient_entities: list[US14117Entity] = Field(min_length=1)
    access_persons: list[US14117AccessPerson] = Field(default_factory=list)
    security_measures: list[US14117SecurityMeasure] = Field(default_factory=list)
    onward_transfer: bool = False
    onward_transfer_description: str = ""
    attachments: list[str] = Field(default_factory=list)  # uploaded file paths
    company_name: str = "示例企业"
    override_thresholds: dict[str, int] | None = None  # optional rule threshold overrides


# ---------------------------------------------------------------------------
# Rule engine output models
# ---------------------------------------------------------------------------


class US14117RuleHit(BaseModel):
    """A single rule hit from the deterministic engine."""

    rule_id: str
    rule_name: str
    section_ref: str  # EO 14117 section reference
    hit: bool
    reason: str


class US14117RiskMatrixRow(BaseModel):
    """One row of the entity × data × transaction risk matrix."""

    entity_name: str
    covered_person_status: str  # confirmed, inferred, not_covered, uncertain
    covered_person_reason: str
    data_item_name: str
    data_category: str
    us_person_count: int
    threshold: int
    threshold_hit: bool
    transaction_type: str
    access_method: str  # how data reaches the entity/person
    rule_hit_refs: list[str] = Field(default_factory=list)
    traffic_light: TrafficLight | str = "GREEN"
    reason: str
    required_actions: list[str] = Field(default_factory=list)


class US14117TrafficLightResult(BaseModel):
    """EO 14117 traffic light assessment.

    RED    = Prohibited transaction under §100.2
    YELLOW = Restricted transaction under §100.3 — requires security measures
             - yellow_status "blocked": measures missing, must not proceed
             - yellow_status "controlled": measures implemented, may proceed under monitoring
    GREEN  = No EO 14117 trigger detected
    """

    overall_light: TrafficLight | str = "GREEN"
    per_entity_lights: dict[str, str] = Field(default_factory=dict)
    summary: str = ""
    is_prohibited: bool = False
    is_restricted: bool = False
    prohibition_reasons: list[str] = Field(default_factory=list)
    restriction_reasons: list[str] = Field(default_factory=list)
    required_security_measures: list[str] = Field(default_factory=list)
    missing_security_measures: list[str] = Field(default_factory=list)
    # ── Yellow sub-states ──
    yellow_status: str = ""  # "blocked" | "controlled" | "" (empty for RED/GREEN)
    can_proceed_conditionally: bool = False  # True only for YELLOW-controlled
    # ── Due diligence gaps ──
    clarification_questions: list[str] = Field(default_factory=list)


class US14117RuleEngineResult(BaseModel):
    """Complete rule engine output — drives all downstream pipeline stages."""

    # Fields required by WorkflowPipeline.validate_path
    recommended_path: str = "us_14117"
    rationale: str = "EO 14117 deterministic rule engine assessment"

    data_classifications: list[dict] = Field(default_factory=list)
    entity_assessments: list[dict] = Field(default_factory=list)
    transaction_classification: dict = Field(default_factory=dict)
    security_gap_report: dict = Field(default_factory=dict)
    traffic_light: US14117TrafficLightResult = Field(default_factory=US14117TrafficLightResult)
    risk_matrix: list[US14117RiskMatrixRow] = Field(default_factory=list)
    all_rule_hits: list[US14117RuleHit] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Output sub-models
# ---------------------------------------------------------------------------


class US14117Chapter(BaseModel):
    """A single report chapter."""

    chapter_no: int
    title: str
    content: str
    citations: list[str] = Field(default_factory=list)
    risk_level: str = "MEDIUM"


class US14117Result(BaseModel):
    """EO 14117 compliance assessment result."""

    report_path: str
    output_files: dict[str, str] = Field(default_factory=dict)
    company_name: str
    overall_traffic_light: TrafficLight | str = "GREEN"
    traffic_light_result: US14117TrafficLightResult = Field(
        default_factory=US14117TrafficLightResult
    )
    risk_matrix: list[US14117RiskMatrixRow] = Field(default_factory=list)
    rule_hits: list[US14117RuleHit] = Field(default_factory=list)
    chapters: list[US14117Chapter] = Field(default_factory=list)
    consistency_issues: list[str] = Field(default_factory=list)
    attachment_notes: list[str] = Field(default_factory=list)


class US14117AsyncAccepted(BaseModel):
    """Acknowledgment from async task submission."""

    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int


class US14117AsyncStatus(BaseModel):
    """Async task polling result."""

    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int
    created_at: str
    updated_at: str
    error: str | None = None
    result: US14117Result | None = None
