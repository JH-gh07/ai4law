"""task082 canonical 回退与结果冻结。

- :func:`fallback_title_plan` / :func:`build_canonical_plan`：三类回退的
  整体/节点 canonical tree 生成。
- :func:`freeze_title_plan`：正文生成前唯一允许消费的冻结入口，做 hash/版本
  绑定与计划级审计。
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.common.title_plan.canonical import stable_hash
from backend.common.title_plan.errors import ErrorCode, TitlePlanError
from backend.common.title_plan.models import (
    FallbackReason,
    FallbackScope,
    FrozenTitlePlan,
    NodeValidation,
    NodeValidationStatus,
    PlanAudit,
    PlanValidationStatus,
    TemplateSnapshot,
    TitleNode,
    TitlePlan,
    TitleSource,
    ValidationOutcome,
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_canonical_plan(
    template: TemplateSnapshot,
    *,
    title_plan_version: str | None = None,
    validator_version: str | None = None,
    input_hash: str | None = None,
    reason: FallbackReason | None = None,
    scope: FallbackScope = FallbackScope.PLAN,
) -> TitlePlan:
    """生成完整 canonical tree（所有节点 display=canonical，title_source=canonical）。"""
    nodes: list[TitleNode] = []
    for spec in template.template.sections:
        nodes.append(
            TitleNode(
                section_id=spec.section_id,
                display_title=spec.canonical_title,
                canonical_title=spec.canonical_title,
                title_source=TitleSource.CANONICAL,
                purpose_code=spec.purpose_code,
                validation=NodeValidation(
                    section_id=spec.section_id,
                    canonical_title=spec.canonical_title,
                    display_title=spec.canonical_title,
                    title_source=TitleSource.CANONICAL,
                    purpose_code=spec.purpose_code,
                    status=NodeValidationStatus.PASS,
                    fallback=reason is not None,
                    fallback_reason=reason,
                ),
            )
        )
    return TitlePlan(
        module_key=template.template.module_key,
        artifact_role=template.template.artifact_role,
        template_version=template.template.template_version,
        template_hash=template.template_hash,
        title_plan_version=title_plan_version,
        validator_version=validator_version,
        input_hash=input_hash,
        sections=tuple(nodes),
        additional_sections=(),
        plan_validation_status=(
            PlanValidationStatus.FALLBACK if reason is not None else PlanValidationStatus.PASS
        ),
        fallback=reason is not None,
        fallback_scope=scope,
        fallback_reason=reason,
    )


def fallback_title_plan(
    *,
    template: TemplateSnapshot,
    reason: FallbackReason,
    scope: FallbackScope = FallbackScope.PLAN,
) -> TitlePlan:
    """公开回退入口：生成整体 canonical tree。"""
    return build_canonical_plan(template, reason=reason, scope=scope)


def _plan_hash_payload(plan: TitlePlan) -> str:
    # 排除运行时 audit（含 created_at）以保证幂等
    return stable_hash(
        plan.model_dump(mode="json", exclude={"audit"}), prefix="frozen_plan:"
    )


def _verify_outcome_plan_consistency(outcome: ValidationOutcome) -> None:
    plan = outcome.plan
    if outcome.status != plan.plan_validation_status:
        raise TitlePlanError(
            ErrorCode.POST_VALIDATION_MUTATION,
            f"outcome.status {outcome.status.value} != plan.plan_validation_status "
            f"{plan.plan_validation_status.value}",
        )
    if outcome.fallback_scope != plan.fallback_scope:
        raise TitlePlanError(
            ErrorCode.POST_VALIDATION_MUTATION,
            f"outcome.fallback_scope {outcome.fallback_scope.value} != "
            f"plan.fallback_scope {plan.fallback_scope.value}",
        )
    if outcome.fallback_reason != plan.fallback_reason:
        raise TitlePlanError(
            ErrorCode.POST_VALIDATION_MUTATION,
            f"outcome.fallback_reason {outcome.fallback_reason} != "
            f"plan.fallback_reason {plan.fallback_reason}",
        )


def _verify_template_binding(plan: TitlePlan, template: TemplateSnapshot) -> None:
    spec = template.template
    if plan.module_key != spec.module_key or plan.artifact_role != spec.artifact_role:
        raise TitlePlanError(
            ErrorCode.TEMPLATE_VERSION_MISMATCH,
            f"计划模板身份 {plan.module_key!r}/{plan.artifact_role.value} != "
            f"当前模板 {spec.module_key!r}/{spec.artifact_role.value}",
        )
    if plan.template_version != spec.template_version:
        raise TitlePlanError(
            ErrorCode.TEMPLATE_VERSION_MISMATCH,
            f"plan.template_version {plan.template_version!r} != 当前模板 {spec.template_version!r}",
        )
    if plan.template_hash != template.template_hash:
        raise TitlePlanError(
            ErrorCode.TEMPLATE_HASH_MISMATCH,
            f"plan.template_hash {plan.template_hash!r} != 当前模板 {template.template_hash!r}",
        )

    # 结构仍与模板 canonical order 一致，且 canonical_title 未被篡改
    expected_ids = list(template.canonical_order_ids())
    actual_ids = [n.section_id for n in plan.sections]
    if actual_ids != expected_ids:
        raise TitlePlanError(
            ErrorCode.POST_VALIDATION_MUTATION,
            f"计划节点结构偏离模板 canonical order: {actual_ids} != {expected_ids}",
        )
    section_map = template.section_map()
    for node in plan.sections:
        spec_node = section_map.get(node.section_id)
        if spec_node is None or node.canonical_title != spec_node.canonical_title:
            raise TitlePlanError(
                ErrorCode.POST_VALIDATION_MUTATION,
                f"节点 {node.section_id!r} canonical_title 与模板不一致",
            )


def freeze_title_plan(
    outcome: ValidationOutcome,
    *,
    input_hash: str,
    validator_version: str,
    template: TemplateSnapshot,
    frozen_at: str | None = None,
) -> FrozenTitlePlan:
    """冻结校验结果，返回正文生成唯一允许消费的对象。

    约束（§7.4 / §11.7）：重新核对版本/hash/模板结构、校验 outcome↔plan 一致性、
    计算 frozen_plan_hash、生成计划级审计。
    """
    plan = outcome.plan
    if plan.plan_validation_status not in (PlanValidationStatus.PASS, PlanValidationStatus.FALLBACK):
        raise TitlePlanError(
            ErrorCode.POST_VALIDATION_MUTATION,
            f"只有 pass/fallback 计划可冻结，当前 {plan.plan_validation_status.value}",
        )

    # 冻结前复核：outcome 与 plan 状态一致，plan 与当前模板版本/hash/结构一致
    _verify_outcome_plan_consistency(outcome)
    _verify_template_binding(plan, template)

    frozen_plan_hash = _plan_hash_payload(plan)
    now = frozen_at or _iso_now()

    audit = PlanAudit(
        template_version=plan.template_version,
        template_hash=plan.template_hash,
        title_plan_version=plan.title_plan_version,
        validator_version=validator_version,
        input_hash=input_hash,
        raw_plan_hash=outcome.raw_plan_hash,
        frozen_plan_hash=frozen_plan_hash,
        validation_status=plan.plan_validation_status,
        fallback=plan.fallback,
        fallback_scope=plan.fallback_scope,
        fallback_reason=plan.fallback_reason,
        fallback_node_ids=list(plan.fallback_node_ids),
        created_at=now,
    )

    # 用含 audit 的完整 plan 做最终冻结（audit 不影响 frozen hash，因为 hash 排除 audit）
    frozen_plan = plan.model_copy(update={"audit": audit, "input_hash": input_hash,
                                          "validator_version": validator_version})
    return FrozenTitlePlan(
        plan=frozen_plan,
        frozen_plan_hash=frozen_plan_hash,
        input_hash=input_hash,
        validator_version=validator_version,
        frozen_at=now,
    )


__all__ = [
    "build_canonical_plan",
    "fallback_title_plan",
    "freeze_title_plan",
]
