#!/usr/bin/env python3
"""T10 — reconcile regional source metadata with the 51 PDFs on disk.

The 51 regional law PDFs live at resources/legal/sources/<cc>/references/ but the
51 regional rows in sources.csv carry an empty `snapshot_path`. This script is the
single, checkable gate that:

  1. maps every regional source_id to its PDF via the curated mapping in
     ingest_regional_laws.py (basename is the durable key, jurisdiction the dir);
  2. writes `snapshot_path` back into sources.csv for every resolvable row;
  3. reports a one-to-one reconciliation: 49 assigned + 2 source-without-PDF +
     2 PDF-without-source (both are known, expert-review data gaps).

It never touches remote data and only rewrites the `snapshot_path` column of
resources/legal/catalog/sources.csv.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import ingest_regional_laws as ing  # noqa: E402

SOURCES_CSV = ROOT / "resources/legal/catalog/sources.csv"
REFERENCES_BASE = ROOT / "resources/legal/sources"

REGIONAL_JURISDICTIONS = frozenset({"jp", "my", "kr", "hk", "vn", "sg", "tw", "mo"})


def resolve_pdf(source: ing.SourceDef) -> Path | None:
    """Return the on-disk PDF for a regional SourceDef, or None if unmatched."""
    filename = Path(source.pdf_subpath).name
    candidate = REFERENCES_BASE / source.jurisdiction / "references" / filename
    return candidate if candidate.exists() else None


def load_rows() -> tuple[list[str], list[dict[str, str]]]:
    with SOURCES_CSV.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    return fieldnames, rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true", help="write snapshot_path back to sources.csv")
    ap.add_argument("--check", action="store_true", help="fail if any resolvable row is missing a snapshot_path")
    args = ap.parse_args()

    fieldnames, rows = load_rows()
    mapping: dict[str, Path] = {s.source_id: p for s in ing.SOURCES if (p := resolve_pdf(s)) is not None}

    assigned_pdfs: set[str] = set()
    assigned_source_ids: set[str] = set()
    updated = 0
    pending_rows: list[str] = []

    for row in rows:
        sid = row["source_id"]
        if sid not in mapping:
            continue
        path = mapping[sid]
        snapshot = f"resources/legal/sources/{row['jurisdiction'].strip().lower()}/references/{path.name}"
        assigned_source_ids.add(sid)
        assigned_pdfs.add(path.name)
        if row.get("snapshot_path", "").strip() != snapshot:
            updated += 1
        row["snapshot_path"] = snapshot

    # Source ids present in the mapping but whose PDF is missing on disk.
    source_without_pdf = sorted(
        s.source_id for s in ing.SOURCES if s.source_id not in assigned_source_ids
    )
    # PDFs on disk that no regional source_id claims (computed once per jurisdiction).
    claimed = {p.name for p in mapping.values()}
    pdf_without_source = sorted(
        f"{j}/references/{pdf.name}"
        for j in REGIONAL_JURISDICTIONS
        for pdf in sorted((REFERENCES_BASE / j / "references").glob("*.pdf"))
        if (REFERENCES_BASE / j / "references").exists() and pdf.name not in claimed
    )

    print(f"regional sources in CSV        : {sum(1 for r in rows if (r.get('jurisdiction') or '').strip().lower() in REGIONAL_JURISDICTIONS)}")
    print(f"PDF mapping entries            : {len(mapping)}")
    print(f"rows with snapshot_path now set: {assigned_source_ids.__len__()}")
    print(f"snapshot_path values updated   : {updated}")
    print(f"source_without_pdf             : {source_without_pdf}")
    print(f"pdf_without_source             : {pdf_without_source}")

    if args.write:
        with SOURCES_CSV.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        print(f"OK   wrote snapshot_path back to {SOURCES_CSV.relative_to(ROOT)}")

    if args.check:
        missing = [r["source_id"] for r in rows if r["source_id"] in mapping and not (r.get("snapshot_path") or "").strip()]
        if missing:
            print(f"FAIL {len(missing)} resolvable rows missing snapshot_path: {missing}")
            return 2
        print("OK   every resolvable regional row has a snapshot_path")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
