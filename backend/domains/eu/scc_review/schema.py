"""EU SCC compliance review schemas.

Data models for:
- Parsed SCC document structure (Clauses 1-18, Annexes I.A/B, II, III)
- Transfer chain modeling
- Review findings (clause-level, annex-level, TIA-level)
- Review result and report output
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field
from backend.domains.us.cpra.schema import CPRACitationRef

# ═══════════════════════════════════════════════════════════════════════
# SCC Document Structure (parsed from uploaded SCC text)
# ═══════════════════════════════════════════════════════════════════════

SCCModuleType = Literal["Module One", "Module Two", "Module Three", "Module Four"]
PartyRole = Literal["controller", "processor"]


class SCCParty(BaseModel):
    """A party to the SCC (from Annex I.A)."""
    name: str = ""
    address: str = ""
    contact: str = ""
    role: str = ""  # controller / processor
    signature: str = ""
    is_incomplete: bool = False  # "See MSA" or similar placeholder


class SCCAnnexIA(BaseModel):
    """Annex I.A — List of Parties."""
    parties: list[SCCParty] = Field(default_factory=list)
    signing_info: str = ""

class SCCAnnexIB(BaseModel):
    """Annex I.B — Description of Transfer."""
    data_subjects: str = ""
    data_categories: str = ""
    special_category_data: list[str] = Field(default_factory=list)
    processing_purpose: str = ""
    processing_nature: str = ""
    transfer_frequency: str = ""
    retention_period: str = ""

class SCCAnnexII(BaseModel):
    """Annex II — Technical and Organisational Measures."""
    tom_items: list[str] = Field(default_factory=list)
    supplementary_measures: list[str] = Field(default_factory=list)

class SCCAnnexIII(BaseModel):
    """Annex III — List of Sub-Processors."""
    sub_processors: list[dict] = Field(default_factory=list)


class SCCClause(BaseModel):
    """A single clause from the SCC document."""
    clause_no: int
    title: str = ""
    content: str = ""
    has_deviation: bool = False
    deviation_type: str = ""  # deletion | weakening | restriction_added | none
    deviation_description: str = ""


class SCCDocument(BaseModel):
    """The fully parsed SCC document."""
    module_type: SCCModuleType | str = ""
    clauses: list[SCCClause] = Field(default_factory=list)
    annex_i_a: SCCAnnexIA = Field(default_factory=SCCAnnexIA)
    annex_i_b: SCCAnnexIB = Field(default_factory=SCCAnnexIB)
    annex_ii: SCCAnnexII = Field(default_factory=SCCAnnexII)
    annex_iii: SCCAnnexIII = Field(default_factory=SCCAnnexIII)
    raw_text: str = ""


# ═══════════════════════════════════════════════════════════════════════
# Transfer Chain Model
# ═══════════════════════════════════════════════════════════════════════

class SCCTransferChain(BaseModel):
    """Modeled data transfer chain extracted from SCC document context."""
    exporter_name: str = ""
    exporter_role: PartyRole | str = ""
    importer_name: str = ""
    importer_role: PartyRole | str = ""
    sub_processors: list[str] = Field(default_factory=list)
    onward_transfer_locations: list[str] = Field(default_factory=list)
    storage_locations: list[str] = Field(default_factory=list)
    access_locations: list[str] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════
# Review Finding Models
# ═══════════════════════════════════════════════════════════════════════

FindingSeverity = Literal["HIGH", "MEDIUM", "LOW"]
FindingType = Literal[
    "module_mismatch", "clause_weakened", "clause_deleted",
    "annex_incomplete", "annex_vague", "special_category_misclassified",
    "tia_missing", "supplementary_measures_insufficient",
    "sub_processor_chain_incomplete", "party_info_incomplete",
    "governing_law_issue", "other",
]


class SCCFinding(BaseModel):
    """A single compliance finding."""
    finding_id: str
    location: str  # e.g., "Clause 15(a)", "Annex I.B", "Annex II"
    clause_ref: str = ""  # e.g., "15(a)"
    original_text: str = ""
    issue_type: FindingType | str = "other"
    severity: FindingSeverity | str = "MEDIUM"
    risk_analysis: str = ""
    legal_basis: str = ""
    recommendation: str = ""
    suggested_text: str = ""


class ModuleValidation(BaseModel):
    """Module selection validation result."""
    expected_module: str = ""
    actual_module: str = ""
    is_correct: bool = True
    mismatch_reason: str = ""


class ClauseComparison(BaseModel):
    """Standard clause comparison result."""
    clauses_checked: int = 0
    deviations_found: int = 0
    findings: list[SCCFinding] = Field(default_factory=list)


class AnnexReview(BaseModel):
    """Annex review result."""
    findings: list[SCCFinding] = Field(default_factory=list)


class TIAReview(BaseModel):
    """TIA and supplementary measures review result."""
    has_third_country_transfer: bool = False
    third_country_transfers: list[str] = Field(default_factory=list)
    tia_present: bool = False
    has_supplementary_measures: bool = False
    schrems_ii_measures_present: bool = False
    findings: list[SCCFinding] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════
# Request and Result Models
# ═══════════════════════════════════════════════════════════════════════

class SCCReviewRequest(BaseModel):
    """EU SCC compliance review request."""
    project_name: str = Field(min_length=2)
    scc_text: str = Field(min_length=10, description="Full SCC document text")
    declared_module_type: SCCModuleType | Literal[""] = ""
    exporter_role: PartyRole | Literal[""] = ""
    importer_role: PartyRole | Literal[""] = ""
    has_tia: bool = False
    has_supplementary_measures: bool = False
    uploaded_files: list[str] = Field(default_factory=list)
    company_name: str = "示例企业"


class SCCChapter(BaseModel):
    """A single report chapter."""
    chapter_no: int
    title: str
    content: str
    citations: list[str] = Field(default_factory=list)
    citation_refs: list[CPRACitationRef] = Field(default_factory=list)
    risk_level: str = "MEDIUM"


class SCCRuleEngineResult(BaseModel):
    """Complete rule engine output."""
    recommended_path: str = "eu_scc"
    rationale: str = "EU SCC deterministic rule engine review"
    document: SCCDocument = Field(default_factory=SCCDocument)
    transfer_chain: SCCTransferChain = Field(default_factory=SCCTransferChain)
    module_validation: ModuleValidation = Field(default_factory=ModuleValidation)
    clause_comparison: ClauseComparison = Field(default_factory=ClauseComparison)
    annex_review: AnnexReview = Field(default_factory=AnnexReview)
    tia_review: TIAReview = Field(default_factory=TIAReview)
    all_findings: list[SCCFinding] = Field(default_factory=list)
    overall_rating: str = "LOW"


class SCCReviewResult(BaseModel):
    """EU SCC compliance review result."""
    report_path: str
    output_files: dict[str, str] = Field(default_factory=dict)
    company_name: str
    overall_rating: str
    findings: list[SCCFinding] = Field(default_factory=list)
    module_validation: ModuleValidation = Field(default_factory=ModuleValidation)
    chapters: list[SCCChapter] = Field(default_factory=list)
    consistency_issues: list[str] = Field(default_factory=list)
    attachment_notes: list[str] = Field(default_factory=list)


class SCCAsyncAccepted(BaseModel):
    task_id: str; module: str; state: str; attempts: int; max_attempts: int

class SCCAsyncStatus(BaseModel):
    task_id: str; module: str; state: str; attempts: int; max_attempts: int
    created_at: str; updated_at: str
    error: str | None = None
    result: SCCReviewResult | None = None
