"""task068 T03 — review run-input manifest builder + integrity verification."""

from __future__ import annotations

from pathlib import Path

from backend.domains.cn.document_review.input_manifest import (
    build_review_input_manifest,
    verify_review_manifest,
)
from backend.models.review import UploadedFileModel


def _file(tmp_path: Path, name: str, content: bytes = b"hello", file_id: str = "f-1") -> UploadedFileModel:
    path = tmp_path / name
    path.write_bytes(content)
    return UploadedFileModel(
        id=file_id,
        user_id="u-1",
        task_id="t-1",
        filename=name,
        content_type="text/plain",
        storage_path=str(path),
        extracted_text=content.decode("utf-8"),
    )


def test_build_manifest_seals_and_records_disk_bytes(tmp_path: Path) -> None:
    f = _file(tmp_path, "a.txt", b"hello world")
    manifest = build_review_input_manifest(task_id="t-1", files=[f])
    assert manifest.integrity.manifest_hash
    entry = manifest.entries[0]
    assert entry.input_id == "f-1"
    assert entry.source_kind == "uploaded"
    assert entry.consumed_by_service is True
    assert entry.parser_status == "parsed"
    assert entry.sha256
    # storage_uri is internal; public locator is the controlled name
    assert entry.storage_uri == str(tmp_path / "a.txt")
    assert entry.public_locator == "a.txt"


def test_verify_review_manifest_passes_clean(tmp_path: Path) -> None:
    manifest = build_review_input_manifest(task_id="t-1", files=[_file(tmp_path, "a.txt")])
    assert verify_review_manifest(manifest) == []


def test_verify_review_manifest_detects_missing_file(tmp_path: Path) -> None:
    f = _file(tmp_path, "a.txt")
    manifest = build_review_input_manifest(task_id="t-1", files=[f])
    (tmp_path / "a.txt").unlink()
    problems = verify_review_manifest(manifest)
    assert {"input_id": "f-1", "kind": "missing"} in problems


def test_verify_review_manifest_detects_hash_changed(tmp_path: Path) -> None:
    f = _file(tmp_path, "a.txt", b"original")
    manifest = build_review_input_manifest(task_id="t-1", files=[f])
    (tmp_path / "a.txt").write_bytes(b"tampered")
    problems = verify_review_manifest(manifest)
    assert {"input_id": "f-1", "kind": "hash_changed"} in problems


def test_missing_file_is_not_consumed_and_pending(tmp_path: Path) -> None:
    missing = UploadedFileModel(
        id="f-missing",
        user_id="u-1",
        task_id="t-1",
        filename="gone.txt",
        content_type="text/plain",
        storage_path=str(tmp_path / "gone.txt"),
        extracted_text="",
    )
    manifest = build_review_input_manifest(task_id="t-1", files=[missing])
    entry = manifest.entries[0]
    assert entry.consumed_by_service is False
    assert entry.parser_status == "pending"
    assert {"input_id": "f-missing", "kind": "missing"} in verify_review_manifest(manifest)


def test_inline_scenario_entry_registered(tmp_path: Path) -> None:
    manifest = build_review_input_manifest(
        task_id="t-1",
        files=[],
        request_context={"scenario_context": {"document_title": "隐私政策", "company_name": "测试公司"}},
    )
    inline = [e for e in manifest.entries if e.source_kind == "inline"]
    assert len(inline) == 1
    assert inline[0].role == "scenario"
    assert inline[0].consumed_by_service is True
    assert verify_review_manifest(manifest) == []


def test_duplicate_file_ids_fail_closed(tmp_path: Path) -> None:
    import pytest
    from pydantic import ValidationError

    f = _file(tmp_path, "a.txt", file_id="dup")
    manifest = build_review_input_manifest(task_id="t-1", files=[f])
    # builder produces unique ids by construction (from file.id), but a manually
    # forged duplicate must still be rejected by the model validator.
    from backend.common.workflow.input_manifest import RunInputManifest

    with pytest.raises(ValidationError, match="input_id"):
        RunInputManifest(
            run_id="t-1",
            module_key="review",
            entries=[manifest.entries[0], manifest.entries[0]],
        )
