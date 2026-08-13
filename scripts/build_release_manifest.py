#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _git_or_env(env_name: str, *args: str) -> str:
    configured = os.getenv(env_name, "").strip()
    if configured:
        return configured
    try:
        return _git(*args)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(
            f"{env_name} is required when release source has no Git metadata"
        ) from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_digest() -> str:
    digest = hashlib.sha256()
    try:
        files = _git("ls-files", "backend", "frontend/src", "scripts").splitlines()
    except (OSError, subprocess.CalledProcessError):
        files = [
            path.relative_to(ROOT).as_posix()
            for base in (ROOT / "backend", ROOT / "frontend" / "src", ROOT / "scripts")
            for path in base.rglob("*")
            if path.is_file()
        ]
    for relative in sorted(files):
        path = ROOT / relative
        if not path.is_file():
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def build_manifest(*, developer_mode: bool) -> dict[str, object]:
    frontend_assets = sorted((ROOT / "frontend" / "dist" / "assets").glob("*"))
    bundle_hash = ""
    if frontend_assets:
        digest = hashlib.sha256()
        for path in frontend_assets:
            if path.is_file():
                digest.update(path.name.encode("utf-8"))
                digest.update(path.read_bytes())
        bundle_hash = digest.hexdigest()
    lock_path = ROOT / "uv.lock"
    return {
        "schema_version": 1,
        "git_commit": _git_or_env("AI4LAW_RELEASE_COMMIT", "rev-parse", "HEAD"),
        "git_tree": _git_or_env("AI4LAW_RELEASE_TREE", "rev-parse", "HEAD^{tree}"),
        "built_at": os.getenv("AI4LAW_RELEASE_BUILT_AT", "").strip()
        or _git_or_env("AI4LAW_RELEASE_BUILT_AT", "show", "-s", "--format=%cI", "HEAD"),
        "builder": "task070-release",
        "frontend_bundle_sha256": bundle_hash,
        "backend_source_sha256": _source_digest(),
        "dependency_lock_sha256": _sha256(lock_path) if lock_path.is_file() else "",
        "developer_mode": developer_mode,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "release-manifest.json")
    parser.add_argument("--developer-mode", action="store_true")
    args = parser.parse_args()
    payload = build_manifest(developer_mode=args.developer_mode)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
