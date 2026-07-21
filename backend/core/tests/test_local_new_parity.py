from scripts.check_local_new_parity import (
    scoped_delta,
    validate_manifest,
    validate_module_ids,
)


def test_scoped_delta_excludes_runtime_outputs_but_keeps_source_changes() -> None:
    entries = [
        ("M", ".gitignore"),
        ("D", ".streamlit/config.toml"),
        ("A", "backend/common/render/pdf_renderer.py"),
        ("A", "storage/traces/run-1/manifest.json"),
        ("A", "runs/result.json"),
        ("M", "doc/.DS_Store"),
        ("A", "frontend/tmp.zip"),
    ]

    assert scoped_delta(entries) == [
        ("M", ".gitignore"),
        ("D", ".streamlit/config.toml"),
        ("A", "backend/common/render/pdf_renderer.py"),
    ]


def test_validate_manifest_rejects_compromised_rebase_snapshot() -> None:
    manifest = {
        "source_ref": "archive/local-full",
        "source_delta_summary": {"added": 0, "modified": 0, "deleted": 0, "total": 0},
        "items": [],
    }

    errors = validate_manifest(manifest, [])

    assert "source_ref must be archive/local-original" in errors


def test_validate_manifest_detects_missing_extra_and_wrong_change_type() -> None:
    manifest = {
        "source_ref": "archive/local-original",
        "source_delta_summary": {"added": 1, "modified": 1, "deleted": 0, "total": 2},
        "items": [
            {"source_path": "added.py", "source_change": "A", "disposition": "pending"},
            {"source_path": "changed.py", "source_change": "M", "disposition": "pending"},
        ],
    }

    errors = validate_manifest(
        manifest,
        [("M", "added.py"), ("M", "extra.py")],
    )

    assert "change type mismatch: added.py (manifest A, git M)" in errors
    assert "missing from git delta: changed.py" in errors
    assert "missing from manifest: extra.py" in errors


def test_validate_manifest_accepts_exact_delta_and_summary() -> None:
    manifest = {
        "source_ref": "archive/local-original",
        "source_delta_summary": {"added": 1, "modified": 1, "deleted": 1, "total": 3},
        "items": [
            {"source_path": "added.py", "source_change": "A", "disposition": "pending"},
            {"source_path": "changed.py", "source_change": "M", "disposition": "pending"},
            {"source_path": "removed.py", "source_change": "D", "disposition": "pending"},
        ],
    }

    assert validate_manifest(
        manifest,
        [("A", "added.py"), ("M", "changed.py"), ("D", "removed.py")],
    ) == []


def test_validate_module_ids_requires_exact_registry_coverage() -> None:
    manifest = {"module_ids": ["cn.transfer_diagnosis", "eu.dpia"]}

    assert validate_module_ids(
        manifest,
        ["cn.transfer_diagnosis", "us.cpra"],
    ) == [
        "module missing from parity manifest: us.cpra",
        "unknown module in parity manifest: eu.dpia",
    ]
