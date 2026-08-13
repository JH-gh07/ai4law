import importlib.util
import hashlib
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "build_release_manifest.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("build_release_manifest", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_release_manifest_is_deterministic_for_same_tree(monkeypatch) -> None:
    module = _load_script()
    monkeypatch.setattr(
        module,
        "_git",
        lambda *args: {
            ("rev-parse", "HEAD"): "a" * 40,
            ("rev-parse", "HEAD^{tree}"): "b" * 40,
            ("show", "-s", "--format=%cI", "HEAD"): "2026-08-13T00:00:00+00:00",
            ("ls-files", "backend", "frontend/src", "scripts"): "",
        }[args],
    )

    first = json.dumps(module.build_manifest(developer_mode=True), sort_keys=True)
    second = json.dumps(module.build_manifest(developer_mode=True), sort_keys=True)

    assert first == second
    assert json.loads(first)["developer_mode"] is True


def test_release_manifest_requires_explicit_commit_without_git_metadata(
    monkeypatch,
) -> None:
    module = _load_script()
    monkeypatch.setattr(module, "_git", lambda *_args: (_ for _ in ()).throw(OSError()))
    monkeypatch.delenv("AI4LAW_RELEASE_COMMIT", raising=False)

    try:
        module.build_manifest(developer_mode=False)
    except SystemExit as exc:
        assert "AI4LAW_RELEASE_COMMIT" in str(exc)
    else:
        raise AssertionError("release without Git metadata must fail closed")


def test_source_digest_falls_back_when_parent_git_metadata_does_not_match_release(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _load_script()
    backend_file = tmp_path / "backend" / "app.py"
    frontend_file = tmp_path / "frontend" / "src" / "main.tsx"
    backend_file.parent.mkdir(parents=True)
    frontend_file.parent.mkdir(parents=True)
    backend_file.write_text("backend-source\n", encoding="utf-8")
    frontend_file.write_text("frontend-source\n", encoding="utf-8")

    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(
        module,
        "_git",
        lambda *args: "backend/file-from-parent-repository.py"
        if args == ("ls-files", "backend", "frontend/src", "scripts")
        else "",
    )

    digest = hashlib.sha256()
    for relative, content in (
        ("backend/app.py", b"backend-source\n"),
        ("frontend/src/main.tsx", b"frontend-source\n"),
    ):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
        digest.update(b"\0")

    assert module._source_digest() == digest.hexdigest()
    assert module._source_digest() != hashlib.sha256().hexdigest()
