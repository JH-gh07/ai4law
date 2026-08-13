from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


DEFAULT_RELEASE_MANIFEST = Path("release-manifest.json")
PUBLIC_FIELDS = {
    "schema_version",
    "git_commit",
    "git_tree",
    "built_at",
    "builder",
    "frontend_bundle_sha256",
    "backend_source_sha256",
    "dependency_lock_sha256",
    "developer_mode",
}


def release_manifest_path() -> Path:
    configured = os.getenv("AI4LAW_RELEASE_MANIFEST", "").strip()
    return Path(configured) if configured else DEFAULT_RELEASE_MANIFEST


def load_public_release_info(path: Path | None = None) -> dict[str, Any]:
    manifest_path = path or release_manifest_path()
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"verified": False, "git_commit": "unknown"}
    if not isinstance(payload, dict):
        return {"verified": False, "git_commit": "unknown"}
    commit = str(payload.get("git_commit") or "")
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit.lower()):
        return {"verified": False, "git_commit": "unknown"}
    public = {key: payload[key] for key in PUBLIC_FIELDS if key in payload}
    public["verified"] = True
    return public
