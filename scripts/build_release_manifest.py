#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True
    ).strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_digest() -> str:
    digest = hashlib.sha256()
    files = _git("ls-files", "backend", "frontend/src", "scripts").splitlines()
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
        "git_commit": _git("rev-parse", "HEAD"),
        "git_tree": _git("rev-parse", "HEAD^{tree}"),
        "built_at": _git("show", "-s", "--format=%cI", "HEAD"),
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
