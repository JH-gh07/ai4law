"""CPRA module schemas — structured input models for compliance diagnosis."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ── Attachment ──────────────────────────────────────────────────────────

class CPRAAttachment(BaseModel):
    file_role: Literal["privacy_policy", "rights_sop", "data_map", "vendor_list", "other"]
    file_name: str = Field(min_length=1)
    file_format: Literal["docx", "pdf", "url", "xlsx", "csv"]
    storage_uri: str = Field(min_length=1)
    size_bytes: int | None = Field(default=None, ge=1)
    checksum_sha256: str | None = None


# ── Structured input models (NEW) ──────────────────────────────────────

class CPRAApplicabilityInfo(BaseModel):
    annual_revenue_usd: float | None = None
    ca_consumer_count: int | None = None
    sell_share_revenue_ratio: float | None = None
    operates_in_california: bool = True
    possible_exemptions: list[str] = Field(default_factory=list)  # HIPAA / GLBA / COPPA / None


class CPRADataItem(BaseModel):
    category: str
    is_sensitive: bool = False
    spi_type: str | None = None
    source: str = ""
    purpose: str = ""
    recipient_type: str = ""  # advertising_network / service_provider / third_party / internal
    retention: str = ""
    sale_or_share: bool = False
    cross_context_advertising: bool = False


class CPRADSRMechanism(BaseModel):
    has_web_form: bool = False
    has_email: bool = False
    has_toll_free_phone: bool = False
    supports_access: bool = False
    supports_delete: bool = False
    supports_correct: bool = False
    supports_opt_out: bool = False
    supports_limit_spi: bool = False
    response_days: int | None = None
    is_easy_to_find: bool = False


class CPRAVendorInfo(BaseModel):
    name: str
    vendor_type: str = "service_provider"  # service_provider / contractor / third_party / ad_partner / data_broker
    receives_pi: bool = True
    receives_spi: bool = False
    sale_or_share: bool = False
    has_dpa: bool = False
    dpa_prohibits_sale_share: bool = False
    dpa_requires_dsr_assist: bool = False
    dpa_requires_audit: bool = False
    dpa_honors_opt_out: bool = False


class CPRAConsentUI(BaseModel):
    has_cookie_banner: bool = False
    accept_prominent: bool = False
    reject_equally_prominent: bool = False
    preselected_consent: bool = False
    bundled_consent: bool = False
    refusal_more_steps: bool = False
    confusing_language: bool = False


class CPRAEvidenceSpan(BaseModel):
    fact_id: str
    source_file: str
    quote: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class CPRAAgentWarning(BaseModel):
    message: str
    severity: Literal["info", "warning", "error"] = "warning"


class CPRACitationRef(BaseModel):
    citation_id: str
    source_id: str
    source_title: str
    article_no: str = ""
    display_label: str = ""
    snippet: str = ""
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    authority_level: Literal["high", "medium", "low"] = "medium"
    binding_force: Literal["mandatory", "recommended", "reference"] = "recommended"
    citation_type: Literal[
        "law_article",
        "official_guide",
        "template_requirement",
        "standard_clause",
        "case_reference",
        "user_material",
    ] = "law_article"
    source_kind: str = "law_article"
    jurisdiction: str = "US"
    knowledge_url: str = ""


class CPRAFactPack(BaseModel):
    source_file: CPRAAttachment
    extracted_applicability: CPRAApplicabilityInfo | None = None
    extracted_data_items: list[CPRADataItem] = Field(default_factory=list)
    extracted_dsr_mechanism: CPRADSRMechanism | None = None
    extracted_vendors: list[CPRAVendorInfo] = Field(default_factory=list)
    extracted_consent_ui: CPRAConsentUI | None = None
    evidence_spans: list[CPRAEvidenceSpan] = Field(default_factory=list)
    extraction_warnings: list[str] = Field(default_factory=list)


class CPRARiskChain(BaseModel):
    chain_id: str
    facts: list[str] = Field(default_factory=list)
    risk_level: Literal["HIGH", "MEDIUM", "LOW"]
    gap: str
    recommendation: str


class CPRAVendorPatch(BaseModel):
    vendor: CPRAVendorInfo
    evidence_source: str = "attachment_extracted"


class CPRADataItemPatch(BaseModel):
    data_item: CPRADataItem
    evidence_source: str = "attachment_extracted"


class CPRAConsistencyIssue(BaseModel):
    issue: str
    severity: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    suggested_fix: str = ""


# ── Request ─────────────────────────────────────────────────────────────

class CPRARequest(BaseModel):
    # Original text fields (backward compat)
    business_model: str = Field(min_length=2)
    data_lifecycle: str = Field(min_length=2)
    notice_and_consent: str = Field(min_length=2)
    consumer_rights_process: str = Field(min_length=2)
    opt_out_and_sale_sharing: str = Field(min_length=2)
    vendor_management: str = Field(default="")
    attachments: list[CPRAAttachment] = Field(min_length=1)
    company_name: str = Field(default="示例企业")
    # NEW structured fields (all Optional for backward compat)
    applicability: CPRAApplicabilityInfo | None = None
    data_items: list[CPRADataItem] = Field(default_factory=list)
    dsr_mechanism: CPRADSRMechanism | None = None
    vendors: list[CPRAVendorInfo] = Field(default_factory=list)
    consent_ui: CPRAConsentUI | None = None


# ── Output ──────────────────────────────────────────────────────────────

class CPRAGapItem(BaseModel):
    domain: str
    risk_level: Literal["HIGH", "MEDIUM", "LOW"]
    gap: str
    legal_basis: str
    recommendation: str
    phase: Literal["short_term", "mid_term", "long_term"]
    evidence_source: str = "user_input"  # user_input / attachment_extracted / rule_inferred
    citations: list[str] = Field(default_factory=list)
    citation_refs: list[CPRACitationRef] = Field(default_factory=list)


class CPRAChapter(BaseModel):
    chapter_no: int
    title: str
    content: str
    citations: list[str] = Field(default_factory=list)
    citation_refs: list[CPRACitationRef] = Field(default_factory=list)
    risk_level: str


class CPRAResult(BaseModel):
    report_path: str
    output_files: dict[str, str] = Field(default_factory=dict)
    company_name: str
    risk_level: Literal["HIGH", "MEDIUM", "LOW"]
    gap_items: list[CPRAGapItem] = Field(default_factory=list)
    chapters: list[CPRAChapter] = Field(default_factory=list)
    consistency_issues: list[str] = Field(default_factory=list)
    attachment_notes: list[str] = Field(default_factory=list)


class CPRAAsyncAccepted(BaseModel):
    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int


class CPRAAsyncStatus(BaseModel):
    task_id: str
    module: str
    state: str
    attempts: int
    max_attempts: int
    created_at: str
    updated_at: str
    error: str | None = None
    result: CPRAResult | None = None
