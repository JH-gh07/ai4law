"""task082 两阶段校验算法。

阶段一：Schema/解析校验（TitlePlanDraft + extra=forbid + 闭集枚举）。
阶段二：Template/Policy 运行时校验（按模板 canonical order，不信任模型顺序）。

Validator 是纯函数：不执行 I/O、不调用 LLM、不修改传入对象、不读全局可变状态。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from pydantic import ValidationError

from backend.common.title_plan.canonical import stable_hash
from backend.common.title_plan.errors import RuleViolation
from backend.common.title_plan.fallback import build_canonical_plan
from backend.common.title_plan.models import (
    FallbackReason,
    FallbackScope,
    NodeValidation,
    NodeValidationStatus,
    PlanSectionDraft,
    PlanValidationStatus,
    SectionSpec,
    TemplateSnapshot,
    TitleNode,
    TitlePlan,
    TitlePlanDraft,
    TitlePolicy,
    TitleSource,
    ValidationContext,
    ValidationOutcome,
)
from backend.common.title_plan.policies import (
    CONCLUSION_PATTERNS,
    FACT_ADDITION_PATTERNS,
    M1_SEMANTIC_EQUIVALENCE,
    M2_NO_FACT_ADDITION,
    M3_NO_CONCLUSION,
    M4_NO_STATUS_FLIP,
    M5_NO_DUTY_MERGE,
    ORDINAL_PREFIX_HEAD_RE,
    PURPOSE_LABELS,
    S1_UNKNOWN_SECTION,
    S2_MISSING_REQUIRED,
    S3_DUPLICATE_SECTION,
    S4_REORDER,
    S5_PARENT,
    S6_LEVEL_ORDER,
    S7_FIXED_RENAMED,
    S8_DYNAMIC_PARENT,
    S9_DYNAMIC_LIMIT,
    STATUS_FLIP_PATTERNS,
    T1_NONEMPTY,
    T2_LENGTH,
    T3_NO_MARKDOWN,
    T4_NO_CITATION,
    T5_NO_PROMPT_INSTRUCTION,
    T6_NO_ORDINAL_PREFIX,
    T7_NO_DUPLICATE,
    T8_LOCALE,
    _CITATION_RE,
    _JSON_FRAGMENT_RE,
    _LOCALE_ALLOWED_RE,
    _MARKDOWN_RE,
    _PROMPT_INSTRUCTION_RE,
    matches_any,
    normalize_title,
    strip_placeholders,
    title_hits_purpose,
)


@dataclass
class _NodeResult:
    section_id: str
    display_title: str
    canonical_title: str
    title_source: TitleSource
    selected_candidate_id: str | None
    purpose_code: object
    fallback: bool = False
    fallback_reason: FallbackReason | None = None
    rule_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _plan_fallback(
    template: TemplateSnapshot,
    reason: FallbackReason,
    context: ValidationContext,
    raw_plan_hash: str | None,
) -> ValidationOutcome:
    plan = build_canonical_plan(
        template,
        title_plan_version=None,
        validator_version=context.validator_version,
        input_hash=context.input_hash,
        reason=reason,
        scope=FallbackScope.PLAN,
    )
    return ValidationOutcome(
        status=PlanValidationStatus.FALLBACK,
        plan=plan,
        fallback_scope=FallbackScope.PLAN,
        fallback_reason=reason,
        raw_plan_hash=raw_plan_hash,
    )


def _parse_draft(raw_plan: object) -> tuple[TitlePlanDraft | None, FallbackReason | None]:
    if isinstance(raw_plan, str):
        try:
            raw_plan = json.loads(raw_plan)
        except json.JSONDecodeError:
            return None, FallbackReason.PARSE_ERROR
    if not isinstance(raw_plan, dict):
        return None, FallbackReason.PARSE_ERROR
    try:
        return TitlePlanDraft.model_validate(raw_plan), None
    except ValidationError:
        return None, FallbackReason.SCHEMA_ERROR


def _raw_hash(raw_plan: object) -> str | None:
    if isinstance(raw_plan, dict):
        return stable_hash(raw_plan, prefix="raw_plan:")
    if isinstance(raw_plan, str):
        return stable_hash(raw_plan, prefix="raw_plan:")
    return None


def _hit_other_purpose_codes(display_title: str, own: object) -> set:
    normalized = normalize_title(display_title, strip_ordinal=True)
    hits: set = set()
    for code, labels in PURPOSE_LABELS.items():
        if code == own:
            continue
        if any(label in normalized for label in labels):
            hits.add(code)
    return hits


# 这些规则在回退语义上属于“语义错误”（核心节点也用 SEMANTIC_ERROR 表达）。
_SEMANTIC_FALLBACK_RULE_IDS = frozenset({
    M2_NO_FACT_ADDITION,
    M3_NO_CONCLUSION,
    M4_NO_STATUS_FLIP,
    M5_NO_DUTY_MERGE,
    T4_NO_CITATION,
    T5_NO_PROMPT_INSTRUCTION,
})


def _text_safety_violations(
    display: str,
    *,
    max_length: int,
    title_policy: TitlePolicy,
    purpose_code: object,
    run_semantic: bool,
) -> list[tuple[str, str, FallbackReason]]:
    """T1-T6/T8 与（可选）M2-M5 文本/安全规则，返回 (rule_id, message, reason)。

    核心节点与动态节点共用，避免规则漂移。T7（跨节点重复）不在此处，由调用方聚合。
    """
    out: list[tuple[str, str, FallbackReason]] = []
    if not display or not display.strip():
        out.append((T1_NONEMPTY, "display_title 为空", FallbackReason.SCHEMA_ERROR))
    elif len(display) > max_length:
        out.append((T2_LENGTH, f"display_title 长度 {len(display)} 超过上限 {max_length}",
                    FallbackReason.SCHEMA_ERROR))
    if "\n" in display or _MARKDOWN_RE.search(strip_placeholders(display)):
        out.append((T3_NO_MARKDOWN, "display_title 含换行或 Markdown 标记",
                    FallbackReason.SCHEMA_ERROR))
    if _CITATION_RE.search(display):
        out.append((T4_NO_CITATION, "display_title 含 citation marker",
                    FallbackReason.SEMANTIC_ERROR))
    if _PROMPT_INSTRUCTION_RE.search(display) or _JSON_FRAGMENT_RE.search(display):
        out.append((T5_NO_PROMPT_INSTRUCTION, "display_title 含注入指令或 JSON 片段",
                    FallbackReason.SEMANTIC_ERROR))
    if title_policy != TitlePolicy.FIXED and ORDINAL_PREFIX_HEAD_RE.match(display):
        out.append((T6_NO_ORDINAL_PREFIX, "display_title 含重复编号前缀",
                    FallbackReason.SCHEMA_ERROR))
    if not _LOCALE_ALLOWED_RE.match(strip_placeholders(display)):
        out.append((T8_LOCALE, "display_title 含 locale 非法字符",
                    FallbackReason.SCHEMA_ERROR))
    if run_semantic:
        if matches_any(display, FACT_ADDITION_PATTERNS):
            out.append((M2_NO_FACT_ADDITION, "display 引入未提供的事实",
                        FallbackReason.SEMANTIC_ERROR))
        if matches_any(display, CONCLUSION_PATTERNS):
            out.append((M3_NO_CONCLUSION, "display 含未经证实结论",
                        FallbackReason.SEMANTIC_ERROR))
        if matches_any(display, STATUS_FLIP_PATTERNS):
            out.append((M4_NO_STATUS_FLIP, "display 含状态翻转表述",
                        FallbackReason.SEMANTIC_ERROR))
        if purpose_code is not None and len(_hit_other_purpose_codes(display, purpose_code)) >= 2:
            out.append((M5_NO_DUTY_MERGE, "display 合并多个业务职责",
                        FallbackReason.SEMANTIC_ERROR))
    return out


def _dynamic_fallback_reason(violations: list[RuleViolation]) -> FallbackReason:
    if any(v.rule_id in _SEMANTIC_FALLBACK_RULE_IDS for v in violations):
        return FallbackReason.SEMANTIC_ERROR
    return FallbackReason.SCHEMA_ERROR


def _validate_core_node(
    draft: PlanSectionDraft, spec: SectionSpec
) -> _NodeResult:
    result = _NodeResult(
        section_id=spec.section_id,
        display_title=draft.display_title,
        canonical_title=spec.canonical_title,
        title_source=TitleSource.MODEL,
        selected_candidate_id=draft.selected_candidate_id,
        purpose_code=spec.purpose_code,
    )

    def fail(rule_id: str, reason: FallbackReason, message: str) -> None:
        result.rule_ids.append(rule_id)
        result.errors.append(message)
        result.fallback = True
        result.fallback_reason = reason

    # ── S5/S6 防御性结构声明 ────────────────────────────────────────────
    if draft.parent_id is not None and draft.parent_id != spec.parent_id:
        fail(S5_PARENT, FallbackReason.SCHEMA_ERROR,
             f"parent_id 声明 {draft.parent_id!r} 与模板 {spec.parent_id!r} 不一致")
    if draft.level is not None and draft.level != spec.level:
        fail(S6_LEVEL_ORDER, FallbackReason.SCHEMA_ERROR,
             f"level 声明 {draft.level} 与模板 {spec.level} 不一致")
    if draft.order is not None and draft.order != spec.order:
        fail(S6_LEVEL_ORDER, FallbackReason.SCHEMA_ERROR,
             f"order 声明 {draft.order} 与模板 {spec.order} 不一致")

    # ── 文本与安全规则（T1-T6/T8 + M2-M5，与动态节点共用）─────────────
    display = draft.display_title
    is_rewrite = (
        spec.title_policy in (TitlePolicy.CONTROLLED_REWRITE, TitlePolicy.MODEL_GENERATED)
        and display != spec.canonical_title
    )
    for rule_id, message, reason in _text_safety_violations(
        display,
        max_length=spec.max_length,
        title_policy=spec.title_policy,
        purpose_code=spec.purpose_code,
        run_semantic=is_rewrite,
    ):
        fail(rule_id, reason, message)

    # ── 策略校验 ────────────────────────────────────────────────────────
    if spec.title_policy == TitlePolicy.FIXED:
        result.title_source = TitleSource.CANONICAL
        if display != spec.canonical_title:
            fail(S7_FIXED_RENAMED, FallbackReason.SCHEMA_ERROR,
                 f"fixed 节点 display {display!r} != canonical {spec.canonical_title!r}")
        if draft.title_source == TitleSource.MODEL:
            fail(S7_FIXED_RENAMED, FallbackReason.SCHEMA_ERROR,
                 "fixed 节点 title_source=model 为伪造来源")
    elif spec.title_policy == TitlePolicy.DISPLAY_ALIAS_ONLY:
        allowed = set(spec.allowed_aliases) | {spec.canonical_title}
        if display not in allowed:
            fail(S7_FIXED_RENAMED, FallbackReason.SEMANTIC_ERROR,
                 f"display_alias_only 节点使用未批准的 alias {display!r}")
    elif spec.title_policy == TitlePolicy.CANDIDATE_SELECT:
        allowed = set(spec.allowed_candidates) | {spec.canonical_title}
        if draft.selected_candidate_id is not None and draft.selected_candidate_id not in spec.allowed_candidates:
            fail(S7_FIXED_RENAMED, FallbackReason.SEMANTIC_ERROR,
                 f"selected_candidate_id {draft.selected_candidate_id!r} 未登记")
        if display not in allowed:
            fail(S7_FIXED_RENAMED, FallbackReason.SEMANTIC_ERROR,
                 f"candidate_select 节点使用未批准的候选 {display!r}")
    elif spec.title_policy in (TitlePolicy.CONTROLLED_REWRITE, TitlePolicy.MODEL_GENERATED):
        # M1 语义等价：canonical / alias / candidate / purpose label 命中
        if not is_rewrite:
            result.title_source = TitleSource.CANONICAL
        elif display in spec.allowed_aliases or display in spec.allowed_candidates:
            result.title_source = TitleSource.MODEL
        elif title_hits_purpose(display, spec.purpose_code):
            result.title_source = TitleSource.MODEL
        else:
            fail(M1_SEMANTIC_EQUIVALENCE, FallbackReason.SEMANTIC_ERROR,
                 f"display {display!r} 未命中 canonical/alias/candidate 或 purpose 标签")

    if result.fallback:
        result.display_title = spec.canonical_title
        result.title_source = TitleSource.FALLBACK
    return result


def _to_title_node(res: _NodeResult) -> TitleNode:
    status = NodeValidationStatus.PASS
    if res.fallback:
        status = NodeValidationStatus.FALLBACK
    return TitleNode(
        section_id=res.section_id,
        display_title=res.display_title,
        canonical_title=res.canonical_title,
        title_source=res.title_source,
        selected_candidate_id=res.selected_candidate_id,
        purpose_code=res.purpose_code,
        validation=NodeValidation(
            section_id=res.section_id,
            canonical_title=res.canonical_title,
            display_title=res.display_title,
            title_source=res.title_source,
            selected_candidate_id=res.selected_candidate_id,
            purpose_code=res.purpose_code,
            status=status,
            rule_ids=list(res.rule_ids),
            errors=list(res.errors),
            fallback=res.fallback,
            fallback_reason=res.fallback_reason,
        ),
    )


def _validate_dynamic_node(
    draft: PlanSectionDraft,
    template: TemplateSnapshot,
) -> tuple[TitleNode | None, list[RuleViolation]]:
    violations: list[RuleViolation] = []
    section_map = template.section_map()
    parent_id = draft.parent_id

    # S8 动态 parent 越界
    if parent_id is None or parent_id not in section_map:
        violations.append(RuleViolation(rule_id=S8_DYNAMIC_PARENT, section_id=draft.section_id,
                                        message=f"动态节点 parent {parent_id!r} 不存在或未登记"))
    else:
        parent = section_map[parent_id]
        if parent.dynamic_child_limit <= 0:
            violations.append(RuleViolation(rule_id=S8_DYNAMIC_PARENT, section_id=draft.section_id,
                                            message=f"parent {parent_id!r} 不允许动态子节点"))
        if draft.purpose_code is not None and parent.allowed_child_purpose_codes:
            if draft.purpose_code not in parent.allowed_child_purpose_codes:
                violations.append(RuleViolation(rule_id=S8_DYNAMIC_PARENT, section_id=draft.section_id,
                                                message="动态节点 purpose_code 不在 parent 允许集合"))

    # 动态节点也必须经过完整文本/安全校验（T1-T6/T8 + M2-M5）
    for rule_id, message, _reason in _text_safety_violations(
        draft.display_title,
        max_length=64,
        title_policy=TitlePolicy.ADDITIONAL_SECTION,
        purpose_code=draft.purpose_code,
        run_semantic=True,
    ):
        violations.append(RuleViolation(rule_id=rule_id, section_id=draft.section_id, message=message))

    if violations:
        return None, violations

    node = _to_title_node(
        _NodeResult(
            section_id=draft.section_id,
            display_title=draft.display_title,
            canonical_title=draft.display_title,
            title_source=TitleSource.MODEL,
            selected_candidate_id=draft.selected_candidate_id,
            purpose_code=draft.purpose_code,
        )
    )
    return node, violations


def validate_title_plan(
    raw_plan: object,
    *,
    template: TemplateSnapshot,
    context: ValidationContext,
) -> ValidationOutcome:
    """两阶段校验入口（纯函数）。"""
    raw_plan_hash = _raw_hash(raw_plan)

    # ── 阶段一 ─────────────────────────────────────────────────────────
    draft, parse_reason = _parse_draft(raw_plan)
    if draft is None:
        return _plan_fallback(template, parse_reason or FallbackReason.SCHEMA_ERROR,
                              context, raw_plan_hash)

    # ── 阶段二：身份与核心结构 ─────────────────────────────────────────
    spec = template.template
    if (
        draft.module_key != spec.module_key
        or draft.artifact_role != spec.artifact_role
        or draft.template_version != spec.template_version
    ):
        return _plan_fallback(template, FallbackReason.TEMPLATE_MISMATCH, context, raw_plan_hash)

    section_map = template.section_map()
    required_ids = set(template.required_ids())
    canonical_order = template.canonical_order_ids()
    draft_ids = [n.section_id for n in draft.sections]
    draft_id_set = set(draft_ids)
    core_violations: list[RuleViolation] = []

    if len(draft_ids) != len(draft_id_set):
        dup = sorted({sid for sid in draft_ids if draft_ids.count(sid) > 1})
        core_violations.append(RuleViolation(rule_id=S3_DUPLICATE_SECTION, section_id=dup[0] if dup else None,
                                             message=f"section_id 重复: {dup}"))
    unknown = [sid for sid in draft_id_set if sid not in section_map]
    if unknown:
        core_violations.append(RuleViolation(rule_id=S1_UNKNOWN_SECTION, section_id=unknown[0],
                                             message=f"未知 section_id: {unknown}"))
    missing = [sid for sid in required_ids if sid not in draft_id_set]
    if missing:
        core_violations.append(RuleViolation(rule_id=S2_MISSING_REQUIRED, section_id=missing[0],
                                             message=f"缺失必需节点: {missing}"))
    core_draft_order = [sid for sid in draft_ids if sid in section_map]
    if core_draft_order != list(canonical_order):
        core_violations.append(RuleViolation(rule_id=S4_REORDER,
                                             message="核心节点顺序与模板 canonical order 不一致"))

    if core_violations:
        plan = build_canonical_plan(
            template,
            validator_version=context.validator_version,
            input_hash=context.input_hash,
            reason=FallbackReason.SCHEMA_ERROR,
            scope=FallbackScope.PLAN,
        )
        return ValidationOutcome(
            status=PlanValidationStatus.FALLBACK,
            plan=plan,
            fallback_scope=FallbackScope.PLAN,
            fallback_reason=FallbackReason.SCHEMA_ERROR,
            violations=tuple(core_violations),
            raw_plan_hash=raw_plan_hash,
        )

    # ── 逐节点校验（按模板 canonical order）───────────────────────────
    draft_by_id = {n.section_id: n for n in draft.sections}
    results: list[_NodeResult] = []
    for section_id in canonical_order:
        node_draft = draft_by_id.get(section_id)
        if node_draft is None:
            continue
        spec_node = section_map[section_id]
        results.append(_validate_core_node(node_draft, spec_node))

    # ── 动态节点校验（结构 + 文本/安全）───────────────────────────────
    additional_nodes: list[TitleNode] = []
    dynamic_violations: list[RuleViolation] = []
    rejected_dynamic_ids: list[str] = []
    surviving_dynamic_displays: dict[str, str] = {}

    # S9：统计每个 parent 的动态子节点数量（超限整体拒绝）
    dynamic_count_by_parent: dict[str, int] = {}
    for add in draft.additional_sections:
        if add.parent_id:
            dynamic_count_by_parent[add.parent_id] = dynamic_count_by_parent.get(add.parent_id, 0) + 1

    for add in draft.additional_sections:
        node, violations = _validate_dynamic_node(add, template)
        parent_id = add.parent_id
        if parent_id and parent_id in section_map:
            limit = section_map[parent_id].dynamic_child_limit
            if limit > 0 and dynamic_count_by_parent.get(parent_id, 0) > limit:
                violations.append(RuleViolation(
                    rule_id=S9_DYNAMIC_LIMIT, section_id=add.section_id,
                    message=f"动态节点数量 {dynamic_count_by_parent[parent_id]} 超过 "
                            f"parent {parent_id!r} 上限 {limit}"))
        if violations:
            rejected_dynamic_ids.append(add.section_id)
            dynamic_violations.extend(violations)
        else:
            additional_nodes.append(node)
            surviving_dynamic_displays[add.section_id] = add.display_title

    # T7 重复标题（跨核心 + 存活动态节点，基于模型原始 display，回退前比较）
    title_owners: dict[str, list[tuple[str, str]]] = {}
    for res in results:
        original = draft_by_id[res.section_id].display_title
        key = normalize_title(original, strip_ordinal=True)
        if key:
            title_owners.setdefault(key, []).append(("core", res.section_id))
    for sid, display in surviving_dynamic_displays.items():
        key = normalize_title(display, strip_ordinal=True)
        if key:
            title_owners.setdefault(key, []).append(("dynamic", sid))

    for key, owners in title_owners.items():
        if len(owners) <= 1:
            continue
        for kind, sid in owners:
            if kind == "core":
                res = next(r for r in results if r.section_id == sid)
                res.rule_ids.append(T7_NO_DUPLICATE)
                res.errors.append(f"display_title 重复: {key}")
                if not res.fallback:
                    res.fallback = True
                    res.fallback_reason = FallbackReason.SCHEMA_ERROR
                    res.display_title = res.canonical_title
                    res.title_source = TitleSource.FALLBACK
            else:
                # 动态节点无 canonical 可回退 → 拒绝该动态节点
                rejected_dynamic_ids.append(sid)
                dynamic_violations.append(RuleViolation(
                    rule_id=T7_NO_DUPLICATE, section_id=sid,
                    message=f"display_title 重复: {key}"))
                additional_nodes = [n for n in additional_nodes if n.section_id != sid]

    core_nodes = [_to_title_node(r) for r in results]

    fallback_node_ids = tuple(r.section_id for r in results if r.fallback)
    all_violations = list(core_violations) + [
        RuleViolation(rule_id=rid, section_id=r.section_id, message=msg)
        for r in results
        for rid, msg in zip(r.rule_ids, r.errors)
    ] + dynamic_violations

    # ── 汇总状态与 scope ──────────────────────────────────────────────
    if fallback_node_ids:
        status = PlanValidationStatus.FALLBACK
        scope = FallbackScope.NODE
        fallback_reason = next(
            (r.fallback_reason for r in results if r.fallback and r.fallback_reason), None
        )
    elif rejected_dynamic_ids:
        status = PlanValidationStatus.FALLBACK
        scope = FallbackScope.DYNAMIC_NODE
        fallback_reason = _dynamic_fallback_reason(dynamic_violations)
    else:
        status = PlanValidationStatus.PASS
        scope = FallbackScope.NONE
        fallback_reason = None

    plan = TitlePlan(
        module_key=spec.module_key,
        artifact_role=spec.artifact_role,
        template_version=spec.template_version,
        template_hash=template.template_hash,
        title_plan_version=draft.title_plan_version,
        validator_version=context.validator_version,
        input_hash=context.input_hash,
        sections=tuple(core_nodes),
        additional_sections=tuple(additional_nodes),
        plan_validation_status=status,
        fallback=status == PlanValidationStatus.FALLBACK,
        fallback_scope=scope,
        fallback_reason=fallback_reason,
        fallback_node_ids=fallback_node_ids,
        rejected_dynamic_ids=tuple(rejected_dynamic_ids),
    )
    return ValidationOutcome(
        status=status,
        plan=plan,
        fallback_scope=scope,
        fallback_reason=fallback_reason,
        fallback_node_ids=fallback_node_ids,
        rejected_dynamic_ids=tuple(rejected_dynamic_ids),
        violations=tuple(all_violations),
        raw_plan_hash=raw_plan_hash,
    )


__all__ = ["validate_title_plan"]
