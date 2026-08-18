"""L1 模板 registry 测试。"""

from __future__ import annotations

import json

import pytest

from backend.common.title_plan import (
    ArtifactRole,
    ErrorCode,
    TitlePlanError,
    load_template,
)
from backend.common.title_plan.tests.conftest import section, write_spec


def test_load_valid_template(make_snapshot, tmp_path, fixed_sections):
    snap = make_snapshot(tmp_path, fixed_sections)
    assert snap.loaded_version == "test-v0"
    assert len(snap.template.sections) == 3
    assert snap.template_hash


def test_load_missing_template(tmp_path):
    with pytest.raises(TitlePlanError) as ei:
        load_template(module_key="nope", artifact_role=ArtifactRole.LEGACY_MARKDOWN,
                      template_dir=tmp_path)
    assert ei.value.code == ErrorCode.TEMPLATE_NOT_FOUND


def test_load_ambiguous_template(tmp_path, fixed_sections):
    write_spec(tmp_path, module_key="dup", sections=fixed_sections, filename="dup-a.json")
    write_spec(tmp_path, module_key="dup", sections=fixed_sections, filename="dup-b.json")
    with pytest.raises(TitlePlanError) as ei:
        load_template(module_key="dup", artifact_role=ArtifactRole.SCHEMA_FIRST_MARKDOWN,
                      template_dir=tmp_path)
    assert ei.value.code == ErrorCode.TEMPLATE_AMBIGUOUS


def test_load_invalid_json(tmp_path):
    (tmp_path / "bad-schema_first_markdown.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(TitlePlanError):
        load_template(module_key="bad", artifact_role=ArtifactRole.SCHEMA_FIRST_MARKDOWN,
                      template_dir=tmp_path)


def test_duplicate_section_id(make_snapshot, tmp_path):
    sections = [
        section("s1", "A", order=1),
        section("s1", "B", order=2),
    ]
    write_spec(tmp_path, sections=sections)
    with pytest.raises(TitlePlanError) as ei:
        load_template(module_key="test", artifact_role=ArtifactRole.SCHEMA_FIRST_MARKDOWN,
                      template_dir=tmp_path)
    assert ei.value.code == ErrorCode.TEMPLATE_CONTENT_INVALID


def test_parent_cycle(make_snapshot, tmp_path):
    sections = [
        section("a", "A", parent_id="b", order=1),
        section("b", "B", parent_id="a", order=2),
    ]
    write_spec(tmp_path, sections=sections)
    with pytest.raises(TitlePlanError) as ei:
        load_template(module_key="test", artifact_role=ArtifactRole.SCHEMA_FIRST_MARKDOWN,
                      template_dir=tmp_path)
    assert ei.value.code == ErrorCode.TEMPLATE_CONTENT_INVALID


def test_parent_dangling(make_snapshot, tmp_path):
    sections = [
        section("a", "A", parent_id="ghost", order=1),
    ]
    write_spec(tmp_path, sections=sections)
    with pytest.raises(TitlePlanError) as ei:
        load_template(module_key="test", artifact_role=ArtifactRole.SCHEMA_FIRST_MARKDOWN,
                      template_dir=tmp_path)
    assert ei.value.code == ErrorCode.TEMPLATE_CONTENT_INVALID


def test_order_duplicate(make_snapshot, tmp_path):
    sections = [
        section("a", "A", order=1),
        section("b", "B", order=1),
    ]
    write_spec(tmp_path, sections=sections)
    with pytest.raises(TitlePlanError) as ei:
        load_template(module_key="test", artifact_role=ArtifactRole.SCHEMA_FIRST_MARKDOWN,
                      template_dir=tmp_path)
    assert ei.value.code == ErrorCode.TEMPLATE_CONTENT_INVALID


def test_required_conditional_conflict(make_snapshot, tmp_path):
    sections = [
        section("a", "A", order=1, required=True, conditional_rule="if_x"),
    ]
    write_spec(tmp_path, sections=sections)
    with pytest.raises(TitlePlanError) as ei:
        load_template(module_key="test", artifact_role=ArtifactRole.SCHEMA_FIRST_MARKDOWN,
                      template_dir=tmp_path)
    assert ei.value.code == ErrorCode.TEMPLATE_CONTENT_INVALID


def test_hash_stable_across_loads(tmp_path, fixed_sections):
    write_spec(tmp_path, sections=fixed_sections)
    h1 = load_template(module_key="test", artifact_role=ArtifactRole.SCHEMA_FIRST_MARKDOWN,
                       template_dir=tmp_path).template_hash
    h2 = load_template(module_key="test", artifact_role=ArtifactRole.SCHEMA_FIRST_MARKDOWN,
                       template_dir=tmp_path).template_hash
    assert h1 == h2


def test_version_mismatch(tmp_path, fixed_sections):
    write_spec(tmp_path, sections=fixed_sections, template_version="test-v0")
    with pytest.raises(TitlePlanError) as ei:
        load_template(module_key="test", artifact_role=ArtifactRole.SCHEMA_FIRST_MARKDOWN,
                      template_version="other-v9", template_dir=tmp_path)
    assert ei.value.code == ErrorCode.TEMPLATE_VERSION_MISMATCH


def test_not_ready_template(tmp_path, fixed_sections):
    write_spec(tmp_path, sections=fixed_sections, template_version="N/A")
    with pytest.raises(TitlePlanError) as ei:
        load_template(module_key="test", artifact_role=ArtifactRole.SCHEMA_FIRST_MARKDOWN,
                      template_dir=tmp_path)
    assert ei.value.code == ErrorCode.TEMPLATE_VERSION_MISMATCH


def test_snapshot_immutable(make_snapshot, tmp_path, fixed_sections):
    snap = make_snapshot(tmp_path, fixed_sections)
    with pytest.raises(Exception):
        snap.template.sections = ()  # frozen
    with pytest.raises(Exception):
        snap.template.sections[0].canonical_title = "changed"


def test_mutating_source_file_does_not_change_snapshot(make_snapshot, tmp_path, fixed_sections):
    path = write_spec(tmp_path, sections=fixed_sections)
    snap = load_template(module_key="test", artifact_role=ArtifactRole.SCHEMA_FIRST_MARKDOWN,
                         template_dir=tmp_path)
    original_hash = snap.template_hash
    # 修改磁盘文件
    data = json.loads(path.read_text(encoding="utf-8"))
    data["sections"][0]["canonical_title"] = "改掉"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    # snapshot 已不可变，hash 不变
    assert snap.template_hash == original_hash
    assert snap.template.sections[0].canonical_title != "改掉"
