#!/usr/bin/env python3
"""One-way generation gate: resources/legal/catalog/sources.csv -> source_registry.v1.json

WHY THIS EXISTS
---------------
`backend/common/knowledge/registry.py::ensure_source_registry()` returns the cached
JSON when the file exists, without consulting sources.csv. So a CSV edit has no
effect until someone manually deletes the JSON. That is a silent-staleness shape:
no error, no warning, stale metadata served to every chunk builder downstream.

This script makes the relationship explicit and checkable:
  --write   rebuild the JSON cache from the CSV (CSV is the only source of truth)
  --check   rebuild in memory, compare against the cache, exit non-zero on drift
  --diff    report drift without failing

COMPARISON SEMANTICS (important)
--------------------------------
The cache is not a byte-identical dump of the CSV-built entries. Two legitimate
representation differences exist at cache-write time and are NOT drift:

  * metadata key alias : CSV-built emits `external_url`; the cache stores the
                         same value under `source_url`.
  * cache-derived key  : the cache adds `knowledge_url` (a route path derived
                         from source_id), absent from CSV-built entries.

A naive nested-dict diff flags all 69 entries on a clean repository and would
red-line CI permanently for a non-issue. So this gate:
  - compares top-level fields directly (these carry the legal semantics:
    authority_level, binding_force, allowed_usage, can_be_cited,
    can_enter_external_report, layer, source_kind, jurisdiction, modules, ...)
  - normalizes the metadata alias and drops cache-derived keys before comparing
  - reports added/removed source_ids as hard drift

Verified on 2026-08-07 against the repository state: 69 CSV rows, 69 registry
entries built, 69 cached, fan-out 1.0, and ZERO mismatches on every
legally-meaningful top-level field. The only raw differences were the two
representation artifacts named above.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.common.knowledge.paths import source_registry_path, sources_csv_path  # noqa: E402
from backend.common.knowledge.registry import (  # noqa: E402
    build_source_registry_from_sources_csv,
)

# metadata keys the cache derives at write time; not present in CSV-built entries
CACHE_DERIVED_METADATA_KEYS = frozenset({"knowledge_url"})

# metadata key aliases: canonical name -> set of accepted variants
METADATA_KEY_ALIASES = {"external_url": frozenset({"external_url", "source_url"})}


def _canonicalize_metadata(meta: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize a metadata dict so CSV-built and cached forms are comparable."""
    if not meta:
        return {}
    alias_to_canonical = {
        variant: canonical
        for canonical, variants in METADATA_KEY_ALIASES.items()
        for variant in variants
    }
    out: dict[str, Any] = {}
    for key, value in meta.items():
        if key in CACHE_DERIVED_METADATA_KEYS:
            continue
        out[alias_to_canonical.get(key, key)] = value
    return out


def _normalize(entry: dict[str, Any]) -> dict[str, Any]:
    """Normalize one entry for semantic comparison (order-insensitive lists)."""
    out: dict[str, Any] = {}
    for key, value in entry.items():
        if key == "metadata":
            out[key] = _canonicalize_metadata(value)
        elif isinstance(value, list):
            out[key] = sorted(map(str, value))
        else:
            out[key] = value
    return out


def _build_from_csv() -> dict[str, dict[str, Any]]:
    return {
        e.source_id: _normalize(e.model_dump())
        for e in build_source_registry_from_sources_csv()
    }


def _load_cache(path: Path) -> dict[str, dict[str, Any]] | None:
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    entries = raw.get("entries", raw) if isinstance(raw, dict) else raw
    if not isinstance(entries, list):
        return None
    return {e["source_id"]: _normalize(e) for e in entries if isinstance(e, dict) and e.get("source_id")}


def _diff(
    built: dict[str, dict[str, Any]], cached: dict[str, dict[str, Any]]
) -> tuple[list[str], list[str], list[tuple[str, str, Any, Any]]]:
    added = sorted(set(cached) - set(built))
    removed = sorted(set(built) - set(cached))
    field_deltas: list[tuple[str, str, Any, Any]] = []
    for sid in sorted(set(built) & set(cached)):
        b, c = built[sid], cached[sid]
        for field in sorted(set(b) | set(c)):
            bv, cv = b.get(field), c.get(field)
            if bv != cv:
                field_deltas.append((sid, field, bv, cv))
    return added, removed, field_deltas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="rebuild the JSON cache from sources.csv")
    mode.add_argument("--check", action="store_true", help="fail (exit 2) if the cache diverges from sources.csv")
    mode.add_argument("--diff", action="store_true", help="report divergence without failing")
    args = ap.parse_args()

    csv_path, json_path = sources_csv_path(), source_registry_path()
    if not csv_path.exists():
        print(f"FAIL sources.csv not found: {csv_path}")
        return 2

    built = _build_from_csv()
    print(f"sources.csv        : {csv_path.relative_to(ROOT)}  ({len(built)} entries)")
    print(f"source_registry    : {json_path.relative_to(ROOT)}")

    if args.write:
        payload = {
            "schema_version": "v1",
            "entries": [e.model_dump() for e in build_source_registry_from_sources_csv()],
        }
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"OK   wrote {len(built)} entries")
        return 0

    cached = _load_cache(json_path)
    if cached is None:
        print("FAIL cache missing or unreadable; run --write")
        return 0 if args.diff else 2

    added, removed, field_deltas = _diff(built, cached)
    print(f"cached entries     : {len(cached)}")
    print(f"only in cache      : {len(added)}")
    print(f"only in sources.csv: {len(removed)}")
    print(f"field deltas       : {len(field_deltas)}")

    for sid in added:
        print(f"  ONLY-IN-CACHE   {sid}")
    for sid in removed:
        print(f"  ONLY-IN-CSV     {sid}")
    for sid, field, bv, cv in field_deltas[:40]:
        print(f"  DELTA {sid} :: {field}\n        csv  = {bv!r}\n        cache= {cv!r}")
    if len(field_deltas) > 40:
        print(f"  ... and {len(field_deltas) - 40} more")

    if not (added or removed or field_deltas):
        print("OK   cache is in sync with sources.csv")
        return 0

    if args.diff:
        return 0
    print("\nFAIL cache diverges from sources.csv (sources.csv is the source of truth).")
    print("     Run: uv run --frozen python scripts/build_source_registry.py --write")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
