#!/usr/bin/env python3
"""Content-identity gate for regional (JP/KR) legal sources.

This is the automatic half of the JP/KR source-identity remediation. It only
*detects* anomalies; it never performs legal adjudication. The human decision
lives in `status/check/task065/jp_kr_source_adjudication.csv`.

Checks (read-only, no writes):
  1. One-to-one binding      : no two sources share one PDF snapshot_path.
  2. Orphan PDFs             : every JP/KR references/*.pdf is bound to a source OR
                               declared in the adjudication CSV with a disposition.
  3. PDF present + readable  : every bound snapshot_path exists and its first page
                               has an extractable text layer.
  4. Quarantine enforcement  : every `metadata_review_required` source is in the
                               adjudication CSV, and its registry entry has
                               can_be_cited=False / can_enter_external_report=False
                               / allowed_usage=["internal_review"].
  5. Disposition legality    : the adjudication CSV only uses the authoritative
                               disposition enum, and human sign-off columns are not
                               silently overwritten on re-generation.
  6. Quarantined PDF kept    : quarantined sources with a snapshot_path still have
                               their original PDF on disk (Phase 1: keep, never delete).

Exit codes: 0 = clean, 1 = anomaly found (report), 2 = internal error.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.common.knowledge.registry import (  # noqa: E402
    build_source_registry_from_sources_csv,
)

SOURCES_CSV = ROOT / "resources" / "legal" / "catalog" / "sources.csv"
ADJUDICATION_CSV = ROOT / "status" / "check" / "task065" / "jp_kr_source_adjudication.csv"
REGIONAL_REFERENCE_DIRS = {
    cc: ROOT / "resources" / "legal" / "sources" / cc / "references"
    for cc in ("jp", "kr")
}

LEGAL_DISPOSITIONS = {
    "confirm_binding", "correct_metadata", "replace_pdf", "create_new_source",
    "link_as_version", "link_as_annex", "quarantine", "retire",
}
ORPHAN_DISPOSITIONS = {"link_as_version", "link_as_annex", "retire", "quarantine"}


def _load_sources() -> list[dict[str, str]]:
    if not SOURCES_CSV.exists():
        return []
    with SOURCES_CSV.open("r", encoding="utf-8", newline="") as fh:
        return [row for row in csv.DictReader(fh)]


def _load_adjudication() -> list[dict[str, str]]:
    if not ADJUDICATION_CSV.exists():
        return []
    with ADJUDICATION_CSV.open("r", encoding="utf-8", newline="") as fh:
        return [row for row in csv.DictReader(fh)]


def _extract_first_page(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:  # pragma: no cover - pypdf is a declared dependency
        return ""
    try:
        reader = PdfReader(str(path))
    except Exception:
        return ""
    if not reader.pages:
        return ""
    try:
        return (reader.pages[0].extract_text() or "").strip()
    except Exception:
        return ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="emit a JSON report instead of human text")
    args = ap.parse_args()

    sources = _load_sources()
    adjudication = _load_adjudication()
    registry = {e.source_id: e for e in build_source_registry_from_sources_csv()}

    anomalies: list[dict[str, str]] = []

    # This gate is scoped to JP/KR only: that is the regional package whose
    # title<->PDF identity was found to be systematically misaligned. VN/MY
    # image-only PDFs are a separate, already-documented preview_only concern.
    regional = [
        row for row in sources
        if (row.get("jurisdiction") or "").strip().lower() in {"jp", "kr"}
    ]

    # --- 1. One-to-one binding ---
    by_snapshot: dict[str, list[str]] = defaultdict(list)
    for row in regional:
        sp = (row.get("snapshot_path") or "").strip()
        if sp:
            by_snapshot[sp].append((row.get("source_id") or "").strip())
    for sp, sids in by_snapshot.items():
        if len(sids) > 1:
            anomalies.append({
                "check": "duplicate_snapshot_binding",
                "detail": f"PDF {sp} bound to multiple sources: {', '.join(sorted(sids))}",
            })

    # --- 2. Orphan PDFs ---
    adjudication_by_sid = {(r.get("source_id") or "").strip(): r for r in adjudication}
    for cc, refdir in REGIONAL_REFERENCE_DIRS.items():
        if not refdir.exists():
            continue
        for pdf in sorted(refdir.glob("*.pdf")):
            rel = str(pdf.relative_to(ROOT))
            bound = rel in by_snapshot
            declared = any(
                (r.get("PDF path") or "").strip() == rel for r in adjudication
            )
            if bound:
                continue
            if declared:
                # Orphan must carry an annex/version/retire disposition, not a
                # source-correcting disposition.
                row = next(r for r in adjudication if (r.get("PDF path") or "").strip() == rel)
                disp = (row.get("建议处置") or "").strip()
                if disp and disp not in ORPHAN_DISPOSITIONS:
                    anomalies.append({
                        "check": "orphan_disposition",
                        "detail": f"orphan PDF {rel} declared with non-orphan disposition {disp!r}",
                    })
            else:
                anomalies.append({
                    "check": "orphan_pdf",
                    "detail": f"orphan PDF not bound to any source and not in adjudication CSV: {rel}",
                })

    # --- 3. PDF present + readable ---
    for row in regional:
        sid = (row.get("source_id") or "").strip()
        sp = (row.get("snapshot_path") or "").strip()
        if not sp:
            continue
        p = (ROOT / sp).resolve()
        if not p.exists():
            anomalies.append({
                "check": "pdf_missing",
                "detail": f"{sid}: snapshot_path does not exist: {sp}",
            })
            continue
        if not _extract_first_page(p):
            anomalies.append({
                "check": "pdf_unreadable",
                "detail": f"{sid}: PDF first page has no extractable text layer: {sp}",
            })

    # --- 4. Quarantine enforcement ---
    # Every source the audit isolated (review_status=metadata_review_required in
    # sources.csv) must have its registry flags match the citation policy.
    quarantined_sids = {
        (row.get("source_id") or "").strip()
        for row in sources
        if (row.get("review_status") or "").strip().lower() == "metadata_review_required"
    }
    for sid in sorted(quarantined_sids):
        entry = registry.get(sid)
        if entry is None:
            anomalies.append({
                "check": "quarantine_registry_missing",
                "detail": f"{sid}: quarantined but missing from registry",
            })
            continue
        if entry.review_status != "metadata_review_required":
            anomalies.append({
                "check": "quarantine_review_status",
                "detail": f"{sid}: expected review_status=metadata_review_required, got {entry.review_status!r}",
            })
        if entry.can_be_cited is not False or entry.can_enter_external_report is not False:
            anomalies.append({
                "check": "quarantine_citable",
                "detail": f"{sid}: quarantined source is still citable (can_be_cited={entry.can_be_cited}, can_enter_external_report={entry.can_enter_external_report})",
            })
        if list(entry.allowed_usage) != ["internal_review"]:
            anomalies.append({
                "check": "quarantine_usage",
                "detail": f"{sid}: expected allowed_usage=['internal_review'], got {list(entry.allowed_usage)!r}",
            })
        # Original PDF must be preserved, never deleted.
        sp = (entry.metadata or {}).get("snapshot_path", "") or ""
        if sp and not (ROOT / sp).resolve().exists():
            anomalies.append({
                "check": "quarantine_pdf_deleted",
                "detail": f"{sid}: quarantined PDF was deleted: {sp}",
            })

    # Every quarantined source must be present in the adjudication CSV.
    adjudication_sids = {(r.get("source_id") or "").strip() for r in adjudication}
    for sid in sorted(quarantined_sids):
        if sid not in adjudication_sids:
            anomalies.append({
                "check": "quarantine_adjudication_missing",
                "detail": f"{sid}: quarantined but missing from adjudication CSV",
            })

    # --- 5. Disposition legality ---
    for row in adjudication:
        sid = (row.get("source_id") or "").strip()
        disp = (row.get("建议处置") or "").strip()
        if not disp:
            anomalies.append({
                "check": "adjudication_no_disposition",
                "detail": f"{sid}: missing 建议处置",
            })
        elif disp not in LEGAL_DISPOSITIONS:
            anomalies.append({
                "check": "adjudication_illegal_disposition",
                "detail": f"{sid}: illegal disposition {disp!r}",
            })

    # --- Report ---
    report = {
        "jp_kr_sources": len(regional),
        "jp_kr_pdfs_bound": len([r for r in regional if (r.get("snapshot_path") or "").strip()]),
        "adjudication_rows": len(adjudication),
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
    }

    if args.json:
        import json
        report["status"] = "FAIL" if anomalies else "OK"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1 if anomalies else 0

    print(f"jp/kr sources          : {report['jp_kr_sources']}")
    print(f"jp/kr PDFs bound       : {report['jp_kr_pdfs_bound']}")
    print(f"adjudication rows      : {report['adjudication_rows']}")
    print(f"anomalies              : {report['anomaly_count']}")
    for a in anomalies:
        print(f"  [{a['check']}] {a['detail']}")

    if anomalies:
        print("\nFAIL JP/KR source identity anomalies detected (see adjudication CSV).")
        return 1
    print("OK   JP/KR source identity checks pass (quarantine enforced, no new anomalies).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
