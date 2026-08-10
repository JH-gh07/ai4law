from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

LayerType = Literal[
    "L1_regulatory_evidence",
    "L2_business_rule",
    "L3_testcase",
    "L4_template",
]

TemplateType = Literal["official_template", "example", "none"]

SourceKind = Literal[
    "law_article",
    "official_guide",
    "workflow_rule",
    "testcase",
    "standard_clause",
    "template_slot",
    "regulation",
    "case_reference",
]

UsageScope = Literal[
    "legal_grounding",
    "external_report",
    "internal_review",
    "evaluator",
    "few_shot",
    "structure_control",
    "internal_drafting",
    "risk_explanation",
]

EnvironmentType = Literal["production", "dev", "eval"]

ModuleKey = Literal[
    "cn_diagnosis",
    "cn_assessment",
    "cn_review",
    "eu_scc",
    "eu_bcr",
    "eu_dpia",
    "eu_tia",
    "us_14117",
    "us_vendor_review",
    "us_cpra",
]

# ---------------------------------------------------------------------------
# Legacy module aliases — map deprecated names to the canonical ModuleKey.
# Only this single map should translate legacy keys; no other code path may
# silently accept a non-canonical module name.
# ---------------------------------------------------------------------------
LEGACY_MODULE_ALIASES: dict[str, str] = {
    "us_eo14117": "us_14117",
}


def normalize_module_key(raw: str) -> str:
    """Return the canonical ModuleKey for *raw*, applying legacy aliases.

    This is the **only** boundary where a deprecated module name is accepted.
    All downstream code (builders, orchestrator, domain services, tests) MUST
    use the canonical key returned here.
    """
    return LEGACY_MODULE_ALIASES.get(raw, raw)

TaskStage = Literal[
    "path_diagnosis",
    "issue_discovery",
    "legal_grounding",
    "report_generation",
    "clause_compare",
    "evaluation",
    "document_type_detection",
]


class SourceRegistryEntry(BaseModel):
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    jurisdiction: str = "cn"
    modules: list[str] = Field(default_factory=list)
    layer: LayerType
    source_kind: SourceKind | str
    authority_level: str = "medium"
    binding_force: str = "recommended"
    status: str = "effective"
    is_current_version: bool = True
    supersedes: list[str] = Field(default_factory=list)
    superseded_by: list[str] = Field(default_factory=list)
    review_status: str = "published"
    allowed_usage: list[UsageScope | str] = Field(default_factory=list)
    can_be_cited: bool = True
    can_enter_external_report: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeChunkV2(BaseModel):
    chunk_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    title: str = ""
    content: str = ""
    layer: LayerType
    template_type: TemplateType = "none"
    source_kind: SourceKind | str
    module: str = ""
    jurisdiction: str = "cn"
    doc_type: str = ""
    authority_level: str = "medium"
    binding_force: str = "recommended"
    allowed_usage: list[UsageScope | str] = Field(default_factory=list)
    can_be_cited: bool = True
    can_enter_external_report: bool = True
    reference_ids: list[str] = Field(default_factory=list)
    citation_anchor: str = ""
    scenario_tags: list[str] = Field(default_factory=list)
    chunk_strategy: str = ""
    article_no: str = ""
    path: str = "all"
    source_url: str = ""
    snapshot_path: str = ""
    keywords: list[str] = Field(default_factory=list)
    structured_payload: dict[str, Any] = Field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return self.model_dump()


class RetrievalRequest(BaseModel):
    module: ModuleKey
    task_stage: TaskStage
    query: str = ""
    facts: dict[str, Any] = Field(default_factory=dict)
    document_type: str = "other"
    environment: EnvironmentType = "production"
    top_k: int = 8
    jurisdiction: str = "cn"
    path: str = "all"


class RetrievalBundle(BaseModel):
    legal_grounding: list[KnowledgeChunkV2] = Field(default_factory=list)
    workflow_rules: list[KnowledgeChunkV2] = Field(default_factory=list)
    standard_clauses: list[KnowledgeChunkV2] = Field(default_factory=list)
    templates: list[KnowledgeChunkV2] = Field(default_factory=list)
    testcases: list[KnowledgeChunkV2] = Field(default_factory=list)
    debug: dict[str, Any] = Field(default_factory=dict)


class UsageScopedContext(BaseModel):
    usage: UsageScope | str
    environment: EnvironmentType = "production"
    chunks: list[KnowledgeChunkV2] = Field(default_factory=list)
    rejected_chunk_ids: list[str] = Field(default_factory=list)
    debug: dict[str, Any] = Field(default_factory=dict)
