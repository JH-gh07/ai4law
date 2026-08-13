import importlib.util
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
