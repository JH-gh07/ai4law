"""L4 幂等、并发与属性测试。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from backend.common.title_plan import (
    freeze_title_plan,
    stable_hash,
    validate_title_plan,
)


def _validate(make_snapshot, tmp_path, fixed_sections, ctx):
    snap = make_snapshot(tmp_path, fixed_sections)
    nodes = [{"section_id": s.section_id, "display_title": s.canonical_title}
             for s in snap.template.sections]
    raw = {"schema_version": "1.0", "template_version": "test-v0", "module_key": "test",
           "artifact_role": "schema_first_markdown", "sections": nodes,
           "additional_sections": [], "fallback": False}
    out = validate_title_plan(raw, template=snap, context=ctx)
    return freeze_title_plan(out, input_hash="ih", validator_version="v", template=snap)


def test_100_runs_same_hash(make_snapshot, tmp_path, fixed_sections, ctx):
    hashes = {_validate(make_snapshot, tmp_path, fixed_sections, ctx).frozen_plan_hash
              for _ in range(100)}
    assert len(hashes) == 1


def test_concurrent_same_result(make_snapshot, tmp_path, fixed_sections, ctx):
    def run(i):
        # 每个线程使用独立目录，避免并发写同一模板文件产生竞态
        thread_dir = tmp_path / f"t{i}"
        thread_dir.mkdir()
        return _validate(make_snapshot, thread_dir, fixed_sections, ctx).frozen_plan_hash
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(run, range(32)))
    assert len(set(results)) == 1


def test_key_order_does_not_change_hash():
    a = {"b": 2, "a": 1, "nested": {"z": 9, "y": 8}}
    b = {"a": 1, "nested": {"y": 8, "z": 9}, "b": 2}
    assert stable_hash(a) == stable_hash(b)


def test_retry_same_scope_and_reason(make_snapshot, tmp_path, fixed_sections, ctx):
    snap = make_snapshot(tmp_path, fixed_sections)
    bad = "not-json{{"
    out1 = validate_title_plan(bad, template=snap, context=ctx)
    out2 = validate_title_plan(bad, template=snap, context=ctx)
    assert out1.fallback_scope == out2.fallback_scope
    assert out1.fallback_reason == out2.fallback_reason


def test_unknown_field_rejected_not_swallowed(make_snapshot, tmp_path, fixed_sections, ctx):
    snap = make_snapshot(tmp_path, fixed_sections)
    nodes = [{"section_id": s.section_id, "display_title": s.canonical_title}
             for s in snap.template.sections]
    raw = {"schema_version": "1.0", "template_version": "test-v0", "module_key": "test",
           "artifact_role": "schema_first_markdown", "sections": nodes,
           "additional_sections": [], "fallback": False, "sneaky": True}
    out = validate_title_plan(raw, template=snap, context=ctx)
    # extra=forbid 使阶段一失败 → 整体回退，未知字段未被当作合法内容吞掉
    assert out.fallback_scope.value == "plan"
