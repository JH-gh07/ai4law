"""task082 标题计划公共校验、确定性回退与审计能力。

公共导出入口。领域层应只从这里 import，禁止直接依赖内部文件。
"""

from backend.common.title_plan.audit import (
    DEFAULT,
    RedactionPolicy,
    redact,
    restore_audit,
    serialize_audit,
    serialize_audit_json,
    verify_audit_hash,
)
from backend.common.title_plan.canonical import canonical_json, canonicalize_payload, stable_hash
from backend.common.title_plan.config import (
    DEFAULT_CONFIG,
    FailPolicy,
    TitlePlanConfig,
    TitlePlanMode,
    parse_config,
)
from backend.common.title_plan.errors import ErrorCode, RuleViolation, TitlePlanError
from backend.common.title_plan.fallback import (
    build_canonical_plan,
    fallback_title_plan,
    freeze_title_plan,
)
from backend.common.title_plan.models import (
    ArtifactRole,
    FallbackReason,
    FallbackScope,
    FrozenTitlePlan,
    NodeValidation,
    NodeValidationStatus,
    PlanAudit,
    PlanSectionDraft,
    PlanValidationStatus,
    PurposeCode,
    RunStatus,
    SectionSpec,
    TemplateSnapshot,
    TemplateSpec,
    TitleNode,
    TitlePlan,
    TitlePlanDraft,
    TitlePolicy,
    TitleSource,
    ValidationContext,
    ValidationOutcome,
)
from backend.common.title_plan.template_registry import (
    DEFAULT_TEMPLATE_DIR,
    list_available_templates,
    load_template,
)
from backend.common.title_plan.validator import validate_title_plan

__version__ = "0.1.0"

__all__ = [
    "ArtifactRole",
    "DEFAULT",
    "DEFAULT_CONFIG",
    "DEFAULT_TEMPLATE_DIR",
    "ErrorCode",
    "FailPolicy",
    "FallbackReason",
    "FallbackScope",
    "FrozenTitlePlan",
    "NodeValidation",
    "NodeValidationStatus",
    "PlanAudit",
    "PlanSectionDraft",
    "PlanValidationStatus",
    "PurposeCode",
    "RedactionPolicy",
    "RuleViolation",
    "RunStatus",
    "SectionSpec",
    "TemplateSnapshot",
    "TemplateSpec",
    "TitleNode",
    "TitlePlan",
    "TitlePlanConfig",
    "TitlePlanDraft",
    "TitlePlanError",
    "TitlePlanMode",
    "TitlePolicy",
    "TitleSource",
    "ValidationContext",
    "ValidationOutcome",
    "__version__",
    "build_canonical_plan",
    "canonical_json",
    "canonicalize_payload",
    "fallback_title_plan",
    "freeze_title_plan",
    "list_available_templates",
    "load_template",
    "parse_config",
    "redact",
    "restore_audit",
    "serialize_audit",
    "serialize_audit_json",
    "stable_hash",
    "validate_title_plan",
    "verify_audit_hash",
]
