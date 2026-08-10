#!/usr/bin/env python3
"""CI/verification index build with manifest output.

Builds all 15 multi-index-v3 indexes in a **temporary directory** (never
touching the developer's ``storage/rag/v3/``), runs quality gates, and
writes a ``manifest.json`` that can be checked into version control or
compared across builds.

Usage
-----
  uv run python scripts/build_manifest_ci.py
  uv run python scripts/build_manifest_ci.py --output-dir /tmp/ci_build
  uv run python scripts/build_manifest_ci.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Allow running from repo root without install
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
    except Exception:
        return "unknown"


def _git_status_clean() -> bool:
    try:
        out = subprocess.check_output(["git", "status", "--porcelain"], text=True)
        return out.strip() == ""
    except Exception:
        return False


def build_and_manifest(output_dir: Path | None = None) -> dict:
    from backend.common.rag.ingest import build_multi_index_v3
    from backend.common.rag.orchestrator import (
        INDEX_NAMES,
        LEGAL_INDEX_NAMES,
        legal_source_fingerprint,
    )
    from backend.common.rag.constants import MULTI_INDEX_SCHEMA_VERSION
    from backend.core.settings import Settings

    # Use temp dir if none provided
    cleanup: Path | None = None
    if output_dir is None:
        cleanup = Path(tempfile.mkdtemp(prefix="ai4law_ci_index_"))
        output_dir = cleanup

    output_dir.mkdir(parents=True, exist_ok=True)

    # Point settings to temp dir
    settings = Settings()
    original_rag_dir = settings.rag_v3_dir
    settings.rag_v3_dir = output_dir

    try:
        outputs = build_multi_index_v3(settings)
    finally:
        settings.rag_v3_dir = original_rag_dir

    # ── Analyze results ──
    index_stats: dict[str, dict] = {}
    total_paragraph_noise = 0
    total_empty_body = 0
    total_duplicate_chunks = 0
    grand_total = 0

    for name in INDEX_NAMES:
        jsonl_path = output_dir / f"{name}.jsonl"
        if not jsonl_path.exists():
            index_stats[name] = {"rows": 0, "error": "missing"}
            continue

        rows = []
        with jsonl_path.open("r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))

        # Module distribution
        module_counts = Counter(r.get("module", "?") for r in rows)

        # Quality gates
        para_noise = [r for r in rows if "段落" in str(r.get("citation_anchor", ""))]
        empty_body = [r for r in rows if not str(r.get("content", "")).strip()]
        chunk_ids = [r.get("chunk_id", "") for r in rows]
        dup_chunks = len(chunk_ids) - len(set(chunk_ids))

        total_paragraph_noise += len(para_noise)
        total_empty_body += len(empty_body)
        total_duplicate_chunks += dup_chunks
        grand_total += len(rows)

        index_stats[name] = {
            "rows": len(rows),
            "modules": dict(module_counts),
            "paragraph_noise": len(para_noise),
            "empty_body": len(empty_body),
            "duplicate_chunk_id": dup_chunks,
        }

    # ── Build manifest ──
    manifest = {
        "build": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "git_commit": _git_commit(),
            "git_clean": _git_status_clean(),
            "schema_version": MULTI_INDEX_SCHEMA_VERSION,
            "source_fingerprint": legal_source_fingerprint(),
        },
        "summary": {
            "total_indexes": len(INDEX_NAMES),
            "total_rows": grand_total,
            "paragraph_noise_rows": total_paragraph_noise,
            "empty_body_rows": total_empty_body,
            "duplicate_chunk_ids": total_duplicate_chunks,
        },
        "indexes": index_stats,
        "quality_gates": {
            "paragraph_noise_zero": total_paragraph_noise == 0,
            "empty_body_zero": total_empty_body == 0,
            "duplicate_chunk_id_zero": total_duplicate_chunks == 0,
            "all_passed": (
                total_paragraph_noise == 0
                and total_empty_body == 0
                and total_duplicate_chunks == 0
            ),
        },
        "verification": {
            "command": "uv run python scripts/build_manifest_ci.py",
            "integrity_command": "uv run python scripts/check_citation_source_integrity.py --verbose",
            "test_command": "uv run pytest backend -q",
        },
    }

    # Write manifest
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # Cleanup if temp
    if cleanup is not None:
        import shutil
        shutil.rmtree(cleanup, ignore_errors=True)

    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=None,
                        help="Output directory (default: temp dir, cleaned after)")
    parser.add_argument("--json", action="store_true",
                        help="Print manifest as JSON to stdout")
    args = parser.parse_args()

    manifest = build_and_manifest(args.output_dir)

    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        s = manifest["summary"]
        q = manifest["quality_gates"]
        print(f"Indexes built: {s['total_indexes']}")
        print(f"Total rows:    {s['total_rows']}")
        print(f"段落N rows:     {s['paragraph_noise_rows']}")
        print(f"Empty body:    {s['empty_body_rows']}")
        print(f"Dup chunk_ids: {s['duplicate_chunk_ids']}")
        print(f"All gates:     {'PASS' if q['all_passed'] else 'FAIL'}")
        print(f"Manifest at:   {manifest['build']['timestamp']}")

    sys.exit(0 if manifest["quality_gates"]["all_passed"] else 1)


if __name__ == "__main__":
    main()
