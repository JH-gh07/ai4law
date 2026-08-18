"""L3 回退测试：node / dynamic_node / plan 三类回退。"""

from __future__ import annotations

from backend.common.title_plan import (
    FallbackReason,
    FallbackScope,
    fallback_title_plan,
    validate_title_plan,
)


def test_plan_fallback_equals_canonical_tree(make_snapshot, tmp_path, fixed_sections, ctx):
    snap = make_snapshot(tmp_path, fixed_sections)
    out = validate_title_plan("bad{{", template=snap, context=ctx)
    assert out.fallback_scope == FallbackScope.PLAN
    # plan fallback 的核心树与模板 canonical 完全一致
    canonical = fallback_title_plan(template=snap, reason=FallbackReason.PARSE_ERROR)
    assert [n.section_id for n in out.plan.sections] == [n.section_id for n in canonical.sections]
    for n in out.plan.sections:
        assert n.display_title == n.canonical_title
        assert n.title_source.value == "canonical"


def test_node_fallback_keeps_other_valid_nodes(make_snapshot, tmp_path, rewrite_sections, ctx):
    snap = make_snapshot(tmp_path, rewrite_sections)
    nodes = [
        {"section_id": s.section_id, "display_title": s.canonical_title}
        for s in snap.template.sections
    ]
    # ch1 语义不匹配，ch2 保持 canonical
    nodes[1]["display_title"] = "无关标题"
    out = validate_title_plan(
        {"schema_version": "1.0", "template_version": "test-v0", "module_key": "test",
         "artifact_role": "schema_first_markdown", "sections": nodes,
         "additional_sections": [], "fallback": False},
        template=snap, context=ctx,
    )
    assert out.fallback_scope == FallbackScope.NODE
    assert out.fallback_node_ids == ("ch1",)
    ch2 = [n for n in out.plan.sections if n.section_id == "ch2"][0]
    assert ch2.display_title == ch2.canonical_title
    assert not ch2.validation.fallback


def test_dynamic_reject_keeps_core_tree(make_snapshot, tmp_path, fixed_sections, ctx):
    snap = make_snapshot(tmp_path, fixed_sections)
    nodes = [
        {"section_id": s.section_id, "display_title": s.canonical_title}
        for s in snap.template.sections
    ]
    out = validate_title_plan(
        {"schema_version": "1.0", "template_version": "test-v0", "module_key": "test",
         "artifact_role": "schema_first_markdown", "sections": nodes,
         "additional_sections": [{"section_id": "extra", "display_title": "X", "parent_id": "ghost"}],
         "fallback": False},
        template=snap, context=ctx,
    )
    assert out.fallback_scope == FallbackScope.DYNAMIC_NODE
    assert "extra" in out.rejected_dynamic_ids
    # 核心树不受影响
    assert [n.section_id for n in out.plan.sections] == [s.section_id for s in snap.template.sections]


def test_fallback_fields_consistent(make_snapshot, tmp_path, rewrite_sections, ctx):
    snap = make_snapshot(tmp_path, rewrite_sections)
    nodes = [
        {"section_id": s.section_id, "display_title": s.canonical_title}
        for s in snap.template.sections
    ]
    nodes[1]["display_title"] = "无关"
    out = validate_title_plan(
        {"schema_version": "1.0", "template_version": "test-v0", "module_key": "test",
         "artifact_role": "schema_first_markdown", "sections": nodes,
         "additional_sections": [], "fallback": False},
        template=snap, context=ctx,
    )
    assert out.plan.fallback is True
    assert out.plan.fallback_scope == FallbackScope.NODE
    assert out.plan.fallback_reason is not None
    assert out.plan.fallback_node_ids == ("ch1",)
