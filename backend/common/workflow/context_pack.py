from typing import Any

from pydantic import BaseModel, Field

from backend.common.workflow.evidence import EvidenceItem
from backend.common.workflow.facts import FactItem
from backend.common.workflow.issues import IssueItem


class GenerationContextPack(BaseModel):
    module_key: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    facts: list[FactItem]
    diagnosis_result: dict | None = None
    regulations: list[dict]
    issues: list[IssueItem]
    evidence_chain: list[EvidenceItem] = Field(default_factory=list)
    path_warning: str | None = None
    risk_summary: dict | None = None
    attachment_notes: list[dict] = Field(default_factory=list)
    output_requirements: dict = Field(default_factory=dict)
    legal_grounding: dict[str, Any] | None = None
    case_grounding: dict[str, Any] | None = None
    writing_strategy: dict[str, Any] | None = None
    generation_basis_pack: dict[str, Any] | None = None
    citation_registry: Any = None
    legal_grounding_context: list[dict[str, Any]] = Field(default_factory=list)
    workflow_rule_context: list[dict[str, Any]] = Field(default_factory=list)
    template_context: list[dict[str, Any]] = Field(default_factory=list)
    evaluation_context: list[dict[str, Any]] = Field(default_factory=list)
    compliance_reasoning: list[dict[str, Any]] = Field(default_factory=list)
    # ── Legal Agent Control Plane（task073，additive，opt-in） ──
    # 跨 pipeline 阶段累积的 Gate 结果，最终由 AssessmentService 合并为
    # LegalControlDecision；未启用控制时保持空列表。
    control_gate_results: list[Any] = Field(default_factory=list)
