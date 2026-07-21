"""Verify the frozen local-new migration ledger against Git history."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "config/local_new_parity_manifest.json"
EXPECTED_SOURCE_REF = "archive/local-original"
ALLOWED_DISPOSITIONS = {
    "pending",
    "migrate",
    "rewrite",
    "archive",
    "keep-target",
    "reject-with-evidence",
}


def scoped_delta(entries: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Remove runtime and archive outputs from a Git name-status delta."""
    return [
        (change, path)
        for change, path in entries
        if not path.startswith(("storage/", "runs/"))
        and Path(path).name != ".DS_Store"
        and path != "frontend/tmp.zip"
    ]


def _summary(entries: list[tuple[str, str]]) -> dict[str, int]:
    counts = Counter(change for change, _ in entries)
    return {
        "added": counts["A"],
        "modified": counts["M"],
        "deleted": counts["D"],
        "total": len(entries),
    }


def validate_manifest(
    manifest: dict[str, Any], actual_entries: list[tuple[str, str]]
) -> list[str]:
    errors: list[str] = []
    if manifest.get("source_ref") != EXPECTED_SOURCE_REF:
        errors.append(f"source_ref must be {EXPECTED_SOURCE_REF}")

    items = manifest.get("items", [])
    paths = [item.get("source_path") for item in items]
    duplicates = sorted(path for path, count in Counter(paths).items() if count > 1)
    errors.extend(f"duplicate manifest path: {path}" for path in duplicates)

    manifest_delta = {
        item.get("source_path"): item.get("source_change") for item in items
    }
    actual_delta = {path: change for change, path in actual_entries}
    for path in sorted(manifest_delta.keys() - actual_delta.keys()):
        errors.append(f"missing from git delta: {path}")
    for path in sorted(actual_delta.keys() - manifest_delta.keys()):
        errors.append(f"missing from manifest: {path}")
    for path in sorted(manifest_delta.keys() & actual_delta.keys()):
        if manifest_delta[path] != actual_delta[path]:
            errors.append(
                f"change type mismatch: {path} "
                f"(manifest {manifest_delta[path]}, git {actual_delta[path]})"
            )

    for item in items:
        if item.get("disposition") not in ALLOWED_DISPOSITIONS:
            errors.append(f"invalid disposition: {item.get('source_path')}")

    if manifest.get("source_delta_summary") != _summary(actual_entries):
        errors.append("source_delta_summary does not match git delta")
    return errors


def validate_module_ids(
    manifest: dict[str, Any], registry_ids: list[str]
) -> list[str]:
    manifest_ids = manifest.get("module_ids", [])
    errors: list[str] = []
    errors.extend(
        f"module missing from parity manifest: {module_id}"
        for module_id in sorted(set(registry_ids) - set(manifest_ids))
    )
    errors.extend(
        f"unknown module in parity manifest: {module_id}"
        for module_id in sorted(set(manifest_ids) - set(registry_ids))
    )
    duplicates = sorted(
        module_id for module_id, count in Counter(manifest_ids).items() if count > 1
    )
    errors.extend(f"duplicate module in parity manifest: {item}" for item in duplicates)
    return errors


def validate_completion(manifest: dict[str, Any], *, root: Path = ROOT) -> list[str]:
    """Require every source candidate to have evidence and a real target when applicable."""
    errors: list[str] = []
    materialized_dispositions = {"archive", "migrate", "rewrite"}
    for item in manifest.get("items", []):
        source_path = str(item.get("source_path", ""))
        disposition = item.get("disposition")
        target_path = str(item.get("target_path", ""))
        if disposition == "pending":
            errors.append(f"manifest item is still pending: {source_path}")
            continue
        if disposition in materialized_dispositions and not (root / target_path).is_file():
            errors.append(f"materialized target missing: {source_path} -> {target_path}")
        if not str(item.get("evidence", "")).strip():
            errors.append(f"completion evidence missing: {source_path}")
    return errors


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _git_delta(common_ancestor: str, source_ref: str) -> list[tuple[str, str]]:
    output = subprocess.run(
        ["git", "diff", "--name-status", "-z", f"{common_ancestor}..{source_ref}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout.decode("utf-8")
    tokens = output.rstrip("\0").split("\0") if output else []
    entries: list[tuple[str, str]] = []
    index = 0
    while index < len(tokens):
        change = tokens[index][0]
        path = tokens[index + 1]
        index += 2
        if change in {"R", "C"}:
            path = tokens[index]
            index += 1
        entries.append((change, path))
    return scoped_delta(entries)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))

    errors: list[str] = []
    source_ref = manifest["source_ref"]
    source_sha = _git("rev-parse", f"{source_ref}^{{commit}}")
    target_sha = _git("rev-parse", f"{manifest['target_ref']}^{{commit}}")
    common_ancestor = _git("merge-base", source_ref, manifest["target_ref"])
    expected_refs = {
        "source_sha": source_sha,
        "target_sha": target_sha,
        "common_ancestor_sha": common_ancestor,
    }
    for field, actual in expected_refs.items():
        if manifest.get(field) != actual:
            errors.append(f"{field} mismatch: manifest {manifest.get(field)}, git {actual}")

    actual_entries = _git_delta(common_ancestor, source_ref)
    errors.extend(validate_manifest(manifest, actual_entries))
    registry = json.loads((ROOT / "config/module_registry.json").read_text(encoding="utf-8"))
    errors.extend(validate_module_ids(manifest, [item["module_id"] for item in registry]))
    if args.require_complete:
        errors.extend(validate_completion(manifest))

    if errors:
        print("Local-new parity check failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Local-new parity check passed ({len(actual_entries)} source candidates).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
