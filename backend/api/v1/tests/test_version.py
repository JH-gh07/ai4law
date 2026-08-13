import json

from backend.core.release_info import load_public_release_info


def test_release_info_fails_closed_when_manifest_is_missing(tmp_path) -> None:
    assert load_public_release_info(tmp_path / "missing.json") == {
        "verified": False,
        "git_commit": "unknown",
    }


def test_release_info_exposes_only_public_manifest_fields(tmp_path) -> None:
    path = tmp_path / "release-manifest.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "git_commit": "a" * 40,
                "git_tree": "b" * 40,
                "built_at": "2026-08-14T00:00:00+00:00",
                "builder": "production-release",
                "frontend_bundle_sha256": "c" * 64,
                "backend_source_sha256": "d" * 64,
                "dependency_lock_sha256": "e" * 64,
                "developer_mode": True,
                "api_key": "must-not-leak",
                "working_directory": "/private/release/path",
            }
        ),
        encoding="utf-8",
    )

    result = load_public_release_info(path)

    assert result["verified"] is True
    assert result["git_commit"] == "a" * 40
    assert result["developer_mode"] is True
    assert "api_key" not in result
    assert "working_directory" not in result


def test_public_version_endpoint_reports_unverified_without_manifest(
    authenticated_client,
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("AI4LAW_RELEASE_MANIFEST", str(tmp_path / "missing.json"))

    response = authenticated_client.get("/api/v1/version")

    assert response.status_code == 200
    assert response.json() == {"verified": False, "git_commit": "unknown"}
