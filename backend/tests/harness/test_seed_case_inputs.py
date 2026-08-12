"""Tests for the manifest-driven seed case input builder.

The builder's unique input list is benchmarks/datasets/seed-cases-v1/manifest.json.
These tests verify: (1) the manifest is the single source of truth and produces
exactly 50 entries; (2) disk parity is satisfied for the current corpus; (3)
canonical name parsing is correct; (4) the gate fails on missing files, extra
files, renames, hash drift and size drift (mutation tests); and (5) missing
markers produce explicit quality flags instead of silent backfill.
"""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = ROOT / "scripts" / "build_seed_case_inputs.py"


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_seed_case_inputs", _SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = _load_builder()


def _fake_tree(entries: list[dict], tmp_root: Path) -> Path:
    """Copy all manifest-declared files into tmp_root at repo-relative paths."""
    src_dir = tmp_root / "benchmarks/datasets/seed-cases-v1/_source"
    for e in entries:
        rel = e["file"].split("_source/", 1)[1]
        dest = src_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / e["file"]).read_bytes())
    return src_dir


def _patch_to_tree(monkeypatch: pytest.MonkeyPatch, tmp_root: Path) -> Path:
    """Point the builder at tmp_root and return the fake _source dir."""
    monkeypatch.setattr(builder, "ROOT", tmp_root)
    src_dir = tmp_root / "benchmarks/datasets/seed-cases-v1/_source"
    monkeypatch.setattr(builder, "SRC_DIR", src_dir)
    monkeypatch.setattr(builder, "load_gold_standard_source", lambda: None)
    return src_dir


def test_manifest_has_exactly_50_entries() -> None:
    entries = builder.load_manifest_entries()
    assert len(entries) == 50
    ids = {e["file"] for e in entries}
    assert len(ids) == 50


def test_canonical_name_parsing() -> None:
    assert builder.parse_canonical_name("task01_case1.docx") == (1, 1)
    assert builder.parse_canonical_name("task10_case5.docx") == (10, 5)
    with pytest.raises(ValueError):
        builder.parse_canonical_name("任务1_案例1_测试结果.docx")


def test_disk_parity_passes_for_current_corpus() -> None:
    entries = builder.load_manifest_entries()
    # Should not raise SystemExit for the frozen corpus.
    builder.verify_disk_vs_manifest(entries)


def test_missing_file_fails() -> None:
    entries = builder.load_manifest_entries()
    bad = [dict(e) for e in entries]
    bad[0]["file"] = "benchmarks/datasets/seed-cases-v1/_source/task01/does_not_exist.docx"
    with pytest.raises(SystemExit) as exc:
        builder.verify_disk_vs_manifest(bad)
    assert exc.value.code == 2


def test_extra_file_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """A DOCX on disk that is not declared in the manifest must fail."""
    entries = builder.load_manifest_entries()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        src_dir = _patch_to_tree(monkeypatch, tmp_root)
        _fake_tree(entries, tmp_root)
        # Add a phantom extra DOCX under _source not in the manifest.
        (src_dir / "phantom_extra.docx").write_text("x", encoding="utf-8")

        with pytest.raises(SystemExit) as exc:
            builder.verify_disk_vs_manifest(entries)
        assert exc.value.code == 2


def test_rename_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """A file renamed off the canonical taskNN_caseM pattern must fail."""
    entries = builder.load_manifest_entries()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        src_dir = _patch_to_tree(monkeypatch, tmp_root)
        _fake_tree(entries, tmp_root)
        # Rename one canonical file to a non-canonical (old-Chinese) name.
        original = src_dir / "task01" / "task01_case1.docx"
        renamed = src_dir / "task01" / "任务1_案例1_测试结果.docx"
        original.rename(renamed)

        with pytest.raises(SystemExit) as exc:
            builder.verify_disk_vs_manifest(entries)
        assert exc.value.code == 2


def test_hash_drift_fails() -> None:
    entries = builder.load_manifest_entries()
    bad = [dict(e) for e in entries]
    bad[0]["hash"] = "0" * 64
    with pytest.raises(SystemExit) as exc:
        builder.verify_disk_vs_manifest(bad)
    assert exc.value.code == 2


def test_size_drift_fails() -> None:
    entries = builder.load_manifest_entries()
    bad = [dict(e) for e in entries]
    bad[0]["size_bytes"] = 1
    with pytest.raises(SystemExit) as exc:
        builder.verify_disk_vs_manifest(bad)
    assert exc.value.code == 2


def test_task_key_mismatch_fails() -> None:
    entries = builder.load_manifest_entries()
    bad = [dict(e) for e in entries]
    # Keep the same file but lie about its manifest task bucket.
    bad[0]["task_key"] = "task99"
    with pytest.raises(SystemExit) as exc:
        builder.verify_disk_vs_manifest(bad)
    assert exc.value.code == 2


def test_build_record_preserves_source_hash_and_quality_flags() -> None:
    entries = builder.load_manifest_entries()
    first = entries[0]
    path = ROOT / first["file"]
    record = builder.build_record(path, first)
    assert record["source_sha256"] == first["hash"]
    assert record["source_size_bytes"] == first["size_bytes"]
    assert record["source_docx"] == first["file"]
    assert record["expected_status"] == "pending_authoring"
    assert isinstance(record["data_quality_flags"], list)
    assert "input" in record
    assert "paragraphs" in record["input"]


def test_missing_marker_produces_flag_not_silent_backfill() -> None:
    """A missing section marker yields an explicit quality flag."""
    paras = ["标题", "这是正文但没有标准小节标记。", "继续正文"]
    sec = builder.slice_sections(paras)
    assert sec["_found"] == {"input": False, "output": False, "remark": False}
    assert sec["input"] == []
    assert sec["output"] == []
    assert sec["remark"] == []


def test_slice_sections_extracts_only_declared_spans() -> None:
    paras = [
        "任务1 案例1：标题",
        builder.MARK_INPUT,
        "问题1：是否包含重要数据？",
        "不知道。",
        builder.MARK_OUTPUT,
        "核心结论",
        "本场景适用安全评估路径。",
        builder.MARK_REMARK,
        "备注：需人工复核。",
    ]
    sec = builder.slice_sections(paras)
    assert sec["_found"] == {"input": True, "output": True, "remark": True}
    assert sec["input"] == ["问题1：是否包含重要数据？", "不知道。"]
    assert sec["output"] == ["核心结论", "本场景适用安全评估路径。"]
    assert sec["remark"] == ["备注：需人工复核。"]


def test_gold_standard_source_is_exempt_from_case_parity() -> None:
    gold = builder.load_gold_standard_source()
    assert gold is not None
    assert gold == "benchmarks/datasets/seed-cases-v1/_source/数规通黄金标准_v1.0.docx"
    entries = builder.load_manifest_entries()
    assert gold not in {e["file"] for e in entries}
