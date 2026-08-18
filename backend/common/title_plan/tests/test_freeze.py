"""L3 冻结测试。"""

from __future__ import annotations

import pytest

from backend.common.title_plan import (
    ErrorCode,
    FallbackReason,
    TitlePlanError,
    fallback_title_plan,
    freeze_title_plan,
    validate_title_plan,
)


def _valid_outcome(make_snapshot, tmp_path, fixed_sections, ctx):
    snap = make_snapshot(tmp_path, fixed_sections)
    nodes = [{"section_id": s.section_id, "display_title": s.canonical_title}
             for s in snap.template.sections]
    out = validate_title_plan(
        {"schema_version": "1.0", "template_version": "test-v0", "module_key": "test",
         "artifact_role": "schema_first_markdown", "sections": nodes,
         "additional_sections": [], "fallback": False},
        template=snap, context=ctx,
    )
    return out, snap


def test_freeze_binds_hash_and_versions(make_snapshot, tmp_path, fixed_sections, ctx):
    out, snap = _valid_outcome(make_snapshot, tmp_path, fixed_sections, ctx)
    frozen = freeze_title_plan(out, input_hash="ih-1", validator_version="v-1", template=snap)
    assert frozen.frozen_plan_hash
    assert frozen.input_hash == "ih-1"
    assert frozen.validator_version == "v-1"
    assert frozen.plan.audit is not None
    assert frozen.plan.audit.frozen_plan_hash == frozen.frozen_plan_hash


def test_freeze_mutating_source_does_not_change_hash(make_snapshot, tmp_path, fixed_sections, ctx):
    out, snap = _valid_outcome(make_snapshot, tmp_path, fixed_sections, ctx)
    frozen1 = freeze_title_plan(out, input_hash="ih", validator_version="v", template=snap)
    # 尝试修改 outcome 里的 plan（frozen 应阻止）
    with pytest.raises(Exception):
        out.plan.sections[0].canonical_title = "changed"
    frozen2 = freeze_title_plan(out, input_hash="ih", validator_version="v", template=snap)
    assert frozen1.frozen_plan_hash == frozen2.frozen_plan_hash


def test_freeze_rejects_reject_status(make_snapshot, tmp_path, fixed_sections, ctx):
    snap = make_snapshot(tmp_path, fixed_sections)
    plan = fallback_title_plan(template=snap, reason=FallbackReason.SCHEMA_ERROR)
    # 构造一个 reject 状态的 outcome 不可冻结
    from backend.common.title_plan import PlanValidationStatus, ValidationOutcome
    reject_plan = plan.model_copy(update={"plan_validation_status": PlanValidationStatus.REJECT})
    outcome = ValidationOutcome(
        status=PlanValidationStatus.REJECT, plan=reject_plan,
        fallback_scope=plan.fallback_scope, fallback_reason=plan.fallback_reason,
    )
    with pytest.raises(TitlePlanError) as ei:
        freeze_title_plan(outcome, input_hash="ih", validator_version="v", template=snap)
    assert ei.value.code == ErrorCode.POST_VALIDATION_MUTATION


def test_freeze_hash_excludes_created_at(make_snapshot, tmp_path, fixed_sections, ctx):
    out, snap = _valid_outcome(make_snapshot, tmp_path, fixed_sections, ctx)
    frozen1 = freeze_title_plan(out, input_hash="ih", validator_version="v", template=snap,
                                frozen_at="2026-01-01T00:00:00+00:00")
    frozen2 = freeze_title_plan(out, input_hash="ih", validator_version="v", template=snap,
                                frozen_at="2026-12-31T23:59:59+00:00")
    assert frozen1.frozen_plan_hash == frozen2.frozen_plan_hash


# ── 冻结前模板/hash/版本/结构复核（§11.7 负向覆盖）─────────────────────

def test_freeze_rejects_template_version_mismatch(make_snapshot, tmp_path, fixed_sections, ctx):
    out, snap = _valid_outcome(make_snapshot, tmp_path, fixed_sections, ctx)
    tampered = out.plan.model_copy(update={"template_version": "other-v9"})
    tampered_outcome = out.model_copy(update={"plan": tampered})
    with pytest.raises(TitlePlanError) as ei:
        freeze_title_plan(tampered_outcome, input_hash="ih", validator_version="v", template=snap)
    assert ei.value.code == ErrorCode.TEMPLATE_VERSION_MISMATCH


def test_freeze_rejects_template_hash_mismatch(make_snapshot, tmp_path, fixed_sections, ctx):
    out, snap = _valid_outcome(make_snapshot, tmp_path, fixed_sections, ctx)
    tampered = out.plan.model_copy(update={"template_hash": "sha256:forged"})
    tampered_outcome = out.model_copy(update={"plan": tampered})
    with pytest.raises(TitlePlanError) as ei:
        freeze_title_plan(tampered_outcome, input_hash="ih", validator_version="v", template=snap)
    assert ei.value.code == ErrorCode.TEMPLATE_HASH_MISMATCH


def test_freeze_rejects_structure_mismatch(make_snapshot, tmp_path, fixed_sections, ctx):
    out, snap = _valid_outcome(make_snapshot, tmp_path, fixed_sections, ctx)
    reordered = out.plan.sections[::-1]
    tampered = out.plan.model_copy(update={"sections": tuple(reordered)})
    tampered_outcome = out.model_copy(update={"plan": tampered})
    with pytest.raises(TitlePlanError) as ei:
        freeze_title_plan(tampered_outcome, input_hash="ih", validator_version="v", template=snap)
    assert ei.value.code == ErrorCode.POST_VALIDATION_MUTATION


def test_freeze_rejects_outcome_status_mismatch(make_snapshot, tmp_path, fixed_sections, ctx):
    out, snap = _valid_outcome(make_snapshot, tmp_path, fixed_sections, ctx)
    from backend.common.title_plan import PlanValidationStatus
    tampered = out.plan.model_copy(update={"plan_validation_status": PlanValidationStatus.FALLBACK})
    tampered_outcome = out.model_copy(update={"plan": tampered})
    with pytest.raises(TitlePlanError) as ei:
        freeze_title_plan(tampered_outcome, input_hash="ih", validator_version="v", template=snap)
    assert ei.value.code == ErrorCode.POST_VALIDATION_MUTATION
