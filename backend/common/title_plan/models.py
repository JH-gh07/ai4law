"""task082 公共模型与闭集枚举。

所有枚举值均为闭集；新增 role/reason/policy/purpose 必须同步更新：
- 本文件枚举；
- task080 模板 registry 与 schema；
- 测试 fixture；
- 版本变更记录。
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────────────
# 闭集枚举
# ─────────────────────────────────────────────────────────────────────────────

class ArtifactRole(str, Enum):
    """最终产物角色（闭集）。禁止自由字符串。"""

    OFFICIAL_MARKDOWN = "official_markdown"
    INTERNAL_MARKDOWN = "internal_markdown"
    SCHEMA_FIRST_MARKDOWN = "schema_first_markdown"
    LEGACY_MARKDOWN = "legacy_markdown"
    WEB = "web"
    DOCX = "docx"
    PDF = "pdf"
    DOCUMENT_IR = "document_ir"


class TitlePolicy(str, Enum):
    """标题策略（闭集）。"""

    FIXED = "fixed"
    DISPLAY_ALIAS_ONLY = "display_alias_only"
    CONTROLLED_REWRITE = "controlled_rewrite"
    CANDIDATE_SELECT = "candidate_select"
    MODEL_GENERATED = "model_generated"
    ADDITIONAL_SECTION = "additional_section"


class FallbackReason(str, Enum):
    """回退原因（闭集）。hash_mismatch / policy_violation 为 task082 补充项。"""

    PARSE_ERROR = "parse_error"
    SCHEMA_ERROR = "schema_error"
    SEMANTIC_ERROR = "semantic_error"
    TIMEOUT = "timeout"
    PROVIDER_ERROR = "provider_error"
    TEMPLATE_MISMATCH = "template_mismatch"
    POST_VALIDATION_MUTATION = "post_validation_mutation"
    HASH_MISMATCH = "hash_mismatch"
    POLICY_VIOLATION = "policy_violation"


class FallbackScope(str, Enum):
    """回退范围（闭集）。"""

    NONE = "none"
    NODE = "node"
    DYNAMIC_NODE = "dynamic_node"
    PLAN = "plan"


class PlanValidationStatus(str, Enum):
    PASS = "pass"
    FALLBACK = "fallback"
    REJECT = "reject"


class NodeValidationStatus(str, Enum):
    PENDING = "pending"
    PASS = "pass"
    FALLBACK = "fallback"
    REJECT = "reject"


class TitleSource(str, Enum):
    CANONICAL = "canonical"
    MODEL = "model"
    FALLBACK = "fallback"


class RunStatus(str, Enum):
    """task082 §2.3 运行事实报告闭集状态。"""

    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    IMPLEMENTED_NOT_VERIFIED = "IMPLEMENTED_NOT_VERIFIED"
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    NOT_EXECUTED = "NOT_EXECUTED"
    FALLBACK = "FALLBACK"
    DEGRADED = "DEGRADED"


class PurposeCode(str, Enum):
    """语义职责代码（闭集）。语义校验优先匹配职责代码，不依赖模型自由解释。"""

    DOCUMENT_TITLE = "document_title"
    EXECUTIVE_SUMMARY = "executive_summary"
    OVERVIEW = "overview"
    SCOPE = "scope"
    BASIC_INFO = "basic_info"
    DATA_SCOPE = "data_scope"
    PROCESSING_DESCRIPTION = "processing_description"
    TRANSFER_ACTIVITY = "transfer_activity"
    LEGAL_BASIS = "legal_basis"
    CONSULTATION = "consultation"
    NECESSITY_PROPORTIONALITY = "necessity_proportionality"
    RECIPIENT = "recipient"
    RIGHTS_IMPACT = "rights_impact"
    SECURITY_MEASURES = "security_measures"
    RISK_ASSESSMENT = "risk_assessment"
    RISK_DETAILS = "risk_details"
    RISK_REMEDIATION = "risk_remediation"
    MITIGATION = "mitigation"
    FINDINGS = "findings"
    CONCLUSION = "conclusion"
    COMPLIANCE_ACTIONS = "compliance_actions"
    ACTIONS = "actions"
    RECOMMENDATIONS = "recommendations"
    CITATIONS = "citations"
    BOUNDARY = "boundary"
    GAP = "gap"
    PATH = "path"
    MONITORING = "monitoring"
    SIGNOFF = "signoff"
    APPENDIX = "appendix"


# ─────────────────────────────────────────────────────────────────────────────
# 模板模型（TemplateSpec / SectionSpec / TemplateSnapshot）
# ─────────────────────────────────────────────────────────────────────────────

class SectionSpec(BaseModel):
    """模板节点规范。加载时由 content lint 补齐 purpose_code 等 task082 字段。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    section_id: str = Field(min_length=1)
    parent_id: str | None = None
    level: int = Field(ge=1, le=6)
    order: int = Field(ge=0)
    canonical_title: str = Field(min_length=1)
    semantic_purpose: str = Field(min_length=1)
    purpose_code: PurposeCode
    required: bool = True
    conditional_rule: str = "always"
    title_policy: TitlePolicy = TitlePolicy.FIXED
    allowed_aliases: tuple[str, ...] = ()
    allowed_candidates: tuple[str, ...] = ()
    max_length: int = Field(default=64, ge=1)
    dynamic_child_limit: int = Field(default=0, ge=0)
    allowed_child_purpose_codes: tuple[PurposeCode, ...] = ()


class TemplateSpec(BaseModel):
    """模板骨架。sections 使用 tuple，配合 frozen=True 实现不可变。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    title_spec_version: str = "1.0"
    template_version: str = Field(min_length=1)
    module_key: str = Field(min_length=1)
    artifact_role: ArtifactRole
    sections: tuple[SectionSpec, ...]


class TemplateSnapshot(BaseModel):
    """不可变模板快照 + hash 绑定。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    template: TemplateSpec
    template_hash: str = Field(min_length=1)
    loaded_version: str = Field(min_length=1)

    def section_map(self) -> dict[str, SectionSpec]:
        return {s.section_id: s for s in self.template.sections}

    def required_ids(self) -> tuple[str, ...]:
        return tuple(s.section_id for s in self.template.sections if s.required)

    def canonical_order_ids(self) -> tuple[str, ...]:
        return tuple(s.section_id for s in self.template.sections)


# ─────────────────────────────────────────────────────────────────────────────
# 输入草稿模型（阶段一：Schema/解析校验）
# ─────────────────────────────────────────────────────────────────────────────

class PlanSectionDraft(BaseModel):
    """节点草稿（模型输出/输入），extra=forbid。

    ``parent_id``/``level``/``order`` 为可选的防御性声明：模型本不该输出结构，
    但若输出则必须与模板一致，否则触发 S5/S6 违规。
    """

    model_config = ConfigDict(extra="forbid")

    section_id: str = Field(min_length=1)
    display_title: str = Field(min_length=1)
    canonical_title: str | None = None
    title_source: TitleSource | None = None
    selected_candidate_id: str | None = None
    purpose_code: PurposeCode | None = None
    parent_id: str | None = None
    level: int | None = Field(default=None, ge=1, le=6)
    order: int | None = Field(default=None, ge=0)
    validation: dict[str, Any] | None = None
    fallback: bool = False
    fallback_reason: FallbackReason | None = None


class TitlePlanDraft(BaseModel):
    """标题计划草稿（阶段一入口）。"""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    template_version: str = Field(min_length=1)
    module_key: str = Field(min_length=1)
    artifact_role: ArtifactRole
    title_plan_version: str | None = None
    sections: list[PlanSectionDraft]
    additional_sections: list[PlanSectionDraft] = Field(default_factory=list)
    fallback: bool = False
    fallback_reason: FallbackReason | None = None
    audit: dict[str, Any] | None = None


# ─────────────────────────────────────────────────────────────────────────────
# 输出模型（校验结果 / 最终计划 / 审计 / 冻结）
# ─────────────────────────────────────────────────────────────────────────────

class NodeValidation(BaseModel):
    """节点级校验结果（§8.1）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    section_id: str = Field(min_length=1)
    canonical_title: str = Field(min_length=1)
    display_title: str = Field(min_length=1)
    title_source: TitleSource
    selected_candidate_id: str | None = None
    purpose_code: PurposeCode | None = None
    status: NodeValidationStatus
    rule_ids: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    fallback: bool = False
    fallback_reason: FallbackReason | None = None


class TitleNode(BaseModel):
    """最终计划节点（§4.6），内嵌 validation。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    section_id: str = Field(min_length=1)
    display_title: str = Field(min_length=1)
    canonical_title: str = Field(min_length=1)
    title_source: TitleSource
    selected_candidate_id: str | None = None
    purpose_code: PurposeCode | None = None
    validation: NodeValidation


class PlanAudit(BaseModel):
    """计划级审计（§8.1），与节点级 NodeValidation 分离。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    audit_version: str = "1.0"
    template_version: str = Field(min_length=1)
    template_hash: str = Field(min_length=1)
    title_plan_version: str | None = None
    validator_version: str | None = None
    input_hash: str | None = None
    raw_plan_hash: str | None = None
    frozen_plan_hash: str | None = None
    validation_status: PlanValidationStatus
    fallback: bool
    fallback_scope: FallbackScope
    fallback_reason: FallbackReason | None = None
    fallback_node_ids: list[str] = Field(default_factory=list)
    model: str | None = None
    provider: str | None = None
    created_at: str = Field(min_length=1)
    redaction_version: str = "1.0"


class TitlePlan(BaseModel):
    """最终标题计划（校验后的产物，正文生成只消费冻结后的它）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    module_key: str = Field(min_length=1)
    artifact_role: ArtifactRole
    template_version: str = Field(min_length=1)
    template_hash: str = Field(min_length=1)
    title_plan_version: str | None = None
    validator_version: str | None = None
    input_hash: str | None = None
    sections: tuple[TitleNode, ...]
    additional_sections: tuple[TitleNode, ...] = ()
    plan_validation_status: PlanValidationStatus
    fallback: bool
    fallback_scope: FallbackScope
    fallback_reason: FallbackReason | None = None
    fallback_node_ids: tuple[str, ...] = ()
    rejected_dynamic_ids: tuple[str, ...] = ()
    audit: PlanAudit | None = None


class ValidationContext(BaseModel):
    """校验上下文。不执行 I/O，不调用 LLM。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    input_hash: str | None = None
    validator_version: str | None = None
    model: str | None = None
    provider: str | None = None
    locale: str = "zh-CN"
    created_at: str | None = None


class ValidationOutcome(BaseModel):
    """校验结果。领域代码只能通过 freeze 后消费其中 plan。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: PlanValidationStatus
    plan: TitlePlan
    fallback_scope: FallbackScope
    fallback_reason: FallbackReason | None = None
    fallback_node_ids: tuple[str, ...] = ()
    rejected_dynamic_ids: tuple[str, ...] = ()
    violations: tuple = ()
    raw_plan_hash: str | None = None


class FrozenTitlePlan(BaseModel):
    """冻结后的标题计划。正文生成唯一允许消费的对象。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    plan: TitlePlan
    frozen_plan_hash: str = Field(min_length=1)
    input_hash: str = Field(min_length=1)
    validator_version: str = Field(min_length=1)
    frozen_at: str = Field(min_length=1)


__all__ = [
    "ArtifactRole",
    "FallbackReason",
    "FallbackScope",
    "FrozenTitlePlan",
    "NodeValidation",
    "NodeValidationStatus",
    "PlanAudit",
    "PlanSectionDraft",
    "PlanValidationStatus",
    "PurposeCode",
    "RunStatus",
    "SectionSpec",
    "TemplateSnapshot",
    "TemplateSpec",
    "TitleNode",
    "TitlePlan",
    "TitlePlanDraft",
    "TitlePolicy",
    "TitleSource",
    "ValidationContext",
    "ValidationOutcome",
]
