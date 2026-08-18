"""task081 T081-01 — Missing Schema 与验证器测试。

覆盖计划 Section 3 的验收点：正向、反向、重复、dangling reference、
no-llm 不得归因 MODEL_OUTPUT、global/prompt 一致性与唯一性约束。
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.common.workflow import (
    MissingItem,
    MissingManifest,
    validate_missing_item,
    validate_missing_manifest,
    validate_missing_source_paths,
)


def _item(**overrides) -> MissingItem:
    base = {
        "missing_id": "ASSESSMENT-ISSUE-MISSING-ATTACHMENTS",
        "module": "assessment",
        "stage": "issues_built",
        "type": "input",
        "item_key": "ISSUE-missing-attachments",
        "source_paths": ["runs/assessment/x/trace/013_issues_built.json"],
        "present_in_global_context": True,
        "present_in_model_prompt": False,
        "present_in_model_output": False,
        "llm_called": False,
        "root_cause": "INPUT_MISSING",
        "status": "OBSERVED",
    }
    base.update(overrides)
    return MissingItem(**base)


# ── 正向 ──────────────────────────────────────────────────────────────────

def test_valid_item_passes() -> None:
    item = _item()
    assert validate_missing_item(item) == []


def test_manifest_with_unique_items_passes() -> None:
    manifest = MissingManifest(
        module="assessment",
        run_id="run-1",
        items=[
            _item(missing_id="M-1", item_key="ISSUE-a", stage="issues_built"),
            _item(missing_id="M-2", item_key="ISSUE-b", stage="issues_built"),
        ],
    )
    assert validate_missing_manifest(manifest) == []


# ── 反向 ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("field", ["missing_id", "module", "stage", "item_key"])
def test_required_identity_fields_reject_empty(field: str) -> None:
    with pytest.raises(ValidationError):
        _item(**{field: ""})


def test_invalid_type_rejected() -> None:
    with pytest.raises(ValidationError):
        _item(type="not_a_type")


def test_invalid_root_cause_rejected() -> None:
    with pytest.raises(ValidationError):
        _item(root_cause="MODEL_ERROR")


def test_invalid_status_rejected() -> None:
    with pytest.raises(ValidationError):
        _item(status="PENDING")


# ── no-llm 不得归因 MODEL_OUTPUT ──────────────────────────────────────────

def test_no_llm_run_rejects_model_output() -> None:
    item = _item(
        llm_called=False,
        root_cause="MODEL_OUTPUT",
        present_in_model_prompt=True,
    )
    errors = validate_missing_item(item)
    assert any("requires llm_called=True" in e for e in errors)


def test_model_output_requires_prompt_presence() -> None:
    item = _item(
        llm_called=True,
        root_cause="MODEL_OUTPUT",
        present_in_global_context=True,
        present_in_model_prompt=False,
    )
    errors = validate_missing_item(item)
    assert any("requires the fact to have reached the prompt" in e for e in errors)


# ── 存在性单调性 ─────────────────────────────────────────────────────────

def test_output_requires_prompt() -> None:
    item = _item(
        present_in_global_context=True,
        present_in_model_prompt=False,
        present_in_model_output=True,
    )
    assert any("present_in_model_prompt=True" in e for e in validate_missing_item(item))


def test_prompt_requires_global_context() -> None:
    item = _item(present_in_model_prompt=True, present_in_global_context=False)
    assert any("present_in_global_context=True" in e for e in validate_missing_item(item))


# ── global-present / prompt-absent 根因一致性 ──────────────────────────────

def test_global_present_prompt_absent_allows_assembly_and_prompt() -> None:
    # 计划 Section 3 明确要求：global=T / prompt=F 必须允许
    # ASSEMBLY_MISSING / PROMPT_MISSING。
    for cause in ("ASSEMBLY_MISSING", "PROMPT_MISSING", "NOT_VERIFIED"):
        item = _item(
            present_in_global_context=True,
            present_in_model_prompt=False,
            root_cause=cause,
        )
        assert validate_missing_item(item) == [], cause


def test_global_present_prompt_absent_accepts_input_missing() -> None:
    # 计划 Section 3 示例本身即 present_in_global_context=true +
    # root_cause=INPUT_MISSING（"uploaded_files 为空"这一事实存在于全局上下文，
    # 但材料本体缺失）。该组合必须被接受。
    item = _item(
        present_in_global_context=True,
        present_in_model_prompt=False,
        root_cause="INPUT_MISSING",
    )
    assert validate_missing_item(item) == []


# ── 证据路径 ──────────────────────────────────────────────────────────────

def test_observed_requires_source_path() -> None:
    item = _item(source_paths=[], status="OBSERVED")
    assert any("requires at least one source_path" in e for e in validate_missing_item(item))


def test_not_executed_allows_empty_source_paths() -> None:
    item = _item(source_paths=[], status="NOT_EXECUTED", root_cause="NOT_EXECUTED")
    assert validate_missing_item(item) == []


def test_not_verified_allows_empty_source_paths() -> None:
    item = _item(source_paths=[], status="NOT_VERIFIED", root_cause="NOT_VERIFIED")
    assert validate_missing_item(item) == []


def test_empty_source_path_string_rejected() -> None:
    item = _item(source_paths=["   "])
    assert any("must not contain empty strings" in e for e in validate_missing_item(item))


# ── 重复 / dangling reference ─────────────────────────────────────────────

def test_duplicate_missing_id_rejected() -> None:
    manifest = MissingManifest(
        module="assessment",
        run_id="run-1",
        items=[
            _item(missing_id="M-1", item_key="ISSUE-a", stage="s1"),
            _item(missing_id="M-1", item_key="ISSUE-b", stage="s2"),
        ],
    )
    assert any("duplicate missing_id" in e for e in validate_missing_manifest(manifest))


def test_duplicate_item_key_stage_rejected() -> None:
    manifest = MissingManifest(
        module="assessment",
        run_id="run-1",
        items=[
            _item(missing_id="M-1", item_key="ISSUE-a", stage="s1"),
            _item(missing_id="M-2", item_key="ISSUE-a", stage="s1"),
        ],
    )
    assert any("duplicate (item_key, stage)" in e for e in validate_missing_manifest(manifest))


# ── 模块归属一致性（validate_missing_manifest 恒校验） ─────────────────────

def test_manifest_rejects_item_module_mismatch() -> None:
    manifest = MissingManifest(
        module="assessment",
        run_id="run-1",
        items=[_item(missing_id="M-1", module="cpra")],
    )
    errors = validate_missing_manifest(manifest)
    assert any("does not match manifest.module" in e for e in errors)


# ── run-id 一致性（validate_missing_manifest 恒校验，仅 concrete run_id） ────

def test_manifest_rejects_source_path_run_id_mismatch() -> None:
    manifest = MissingManifest(
        module="assessment",
        run_id="20260818_000000_000000_01_minimal",
        items=[
            _item(
                missing_id="M-1",
                source_paths=["runs/assessment/20260818_111111_111111_01_minimal/result.json"],
            )
        ],
    )
    errors = validate_missing_manifest(manifest)
    assert any("embeds run_id" in e for e in errors)


def test_manifest_accepts_matching_source_path_run_id() -> None:
    manifest = MissingManifest(
        module="assessment",
        run_id="20260818_000000_000000_01_minimal",
        items=[
            _item(
                missing_id="M-1",
                source_paths=["runs/assessment/20260818_000000_000000_01_minimal/result.json"],
            )
        ],
    )
    assert validate_missing_manifest(manifest) == []


def test_aggregate_run_id_skips_run_id_consistency_check() -> None:
    # 合成 run_id（如 task081-consolidated）不是具体 run，跳过 run-id 一致性校验。
    manifest = MissingManifest(
        module="assessment",
        run_id="task081-consolidated",
        items=[
            _item(
                missing_id="M-1",
                source_paths=["runs/assessment/20260818_111111_111111_01_minimal/result.json"],
            )
        ],
    )
    assert validate_missing_manifest(manifest) == []


# ── source_paths 存在性（validate_missing_manifest(base_dir=...)） ─────────

def test_source_paths_missing_plain_path_rejected(tmp_path) -> None:
    item = _item(source_paths=[str(tmp_path / "nope" / "trace.json")])
    manifest = MissingManifest(module="assessment", run_id="run-1", items=[item])
    errors = validate_missing_manifest(manifest, base_dir=tmp_path)
    assert any("does not resolve to any file" in e for e in errors)


def test_source_paths_missing_glob_rejected(tmp_path) -> None:
    item = _item(source_paths=["runs/*/trace/013_issues_built.json"])
    manifest = MissingManifest(module="assessment", run_id="run-1", items=[item])
    errors = validate_missing_manifest(manifest, base_dir=tmp_path)
    assert any("does not resolve to any file" in e for e in errors)


def test_source_paths_plain_real_file_accepted(tmp_path) -> None:
    real = tmp_path / "trace" / "013_issues_built.json"
    real.parent.mkdir(parents=True)
    real.write_text("{}", encoding="utf-8")
    item = _item(source_paths=[str(real)])
    manifest = MissingManifest(module="assessment", run_id="run-1", items=[item])
    assert validate_missing_manifest(manifest, base_dir=tmp_path) == []


def test_source_paths_glob_real_match_accepted(tmp_path) -> None:
    real = tmp_path / "runs" / "assessment" / "20260818_000000_000000_01_minimal" / "run_manifest.json"
    real.parent.mkdir(parents=True)
    real.write_text("{}", encoding="utf-8")
    item = _item(source_paths=["runs/assessment/20260818_*_01_minimal/run_manifest.json"])
    manifest = MissingManifest(module="assessment", run_id="run-1", items=[item])
    assert validate_missing_manifest(manifest, base_dir=tmp_path) == []


def test_source_paths_plain_directory_rejected(tmp_path) -> None:
    # 目录路径不得冒充“证据文件”。
    directory = tmp_path / "runs" / "assessment"
    directory.mkdir(parents=True)
    item = _item(source_paths=[str(directory)])
    manifest = MissingManifest(module="assessment", run_id="run-1", items=[item])
    errors = validate_missing_manifest(manifest, base_dir=tmp_path)
    assert any("does not resolve to any file" in e for e in errors)


def test_source_paths_glob_only_directory_rejected(tmp_path) -> None:
    # glob 只命中目录（无文件）时同样拒绝。
    directory = tmp_path / "runs" / "assessment" / "20260818_000000_000000_01_minimal"
    directory.mkdir(parents=True)
    item = _item(source_paths=["runs/assessment/20260818_*_01_minimal"])
    manifest = MissingManifest(module="assessment", run_id="run-1", items=[item])
    errors = validate_missing_manifest(manifest, base_dir=tmp_path)
    assert any("does not resolve to any file" in e for e in errors)


def test_validate_missing_source_paths_standalone(tmp_path) -> None:
    item = _item(source_paths=["missing/evidence.json"])
    errors = validate_missing_source_paths(item, tmp_path)
    assert len(errors) == 1
    assert "missing/evidence.json" in errors[0]
