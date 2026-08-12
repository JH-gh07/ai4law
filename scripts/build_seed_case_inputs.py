#!/usr/bin/env python3
"""Extract seed-case fixtures from the 50 source DOCX files.

The unique input list is `benchmarks/datasets/seed-cases-v1/manifest.json`
(tasks -> files). File discovery by glob is FORBIDDEN here: the manifest is the
authoritative collection, and every file must match its recorded path, size and
SHA-256 exactly. Any missing/extra/renamed/rehashed file fails with a non-zero
exit code.

MARKERS (verified 2026-08-07 by dumping every heading-like paragraph in all 50
files; see the marker diagnostic in the session record):

    一、用户输入                 -> input section     (present in 50/50)
    二、标准答案（即系统输出）   -> output section    (present in 50/50)
    三、备注                     -> remark section    (present in 50/50)

PLACEHOLDER DETECTION: only multi-character tokens are matched, and only inside
the output span. The bare character `待` occurs 204 times across the corpus in
ordinary legal prose; matching it produced a false "all 50 are stubs" reading.

This script writes the INPUT side only (Level A source-fidelity extraction
records). It does not write expected.json and it does not assert any answer is
gold. Promotion of the authored output spans to evaluation expectations
requires per-jurisdiction Legal sign-off (Q2).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "benchmarks/datasets/seed-cases-v1"
SRC_DIR = DATASET_DIR / "_source"
MANIFEST_PATH = DATASET_DIR / "manifest.json"
OUT_DIR = DATASET_DIR

MARK_INPUT = "一、用户输入"
MARK_OUTPUT = "二、标准答案（即系统输出）"
MARK_REMARK = "三、备注"

PLACEHOLDER_TOKENS = ("待补充", "待定", "待专家复核", "待确认", "待填写", "TBD")

# task_no -> (declared folder name, module_id, jurisdiction, mapping_status)
# mapping_status=conflict where the declared task name disagrees with the
# approved functional spec / Gold rubric. Content quality is INDEPENDENT of
# this; conflict cases have full authored output. Adjudication is Q1.
TASKS: dict[int, tuple[str, str, str, str]] = {
    1: ("合规路径诊断", "cn.transfer_diagnosis", "cn", "partial"),
    2: ("安全评估路径", "cn.security_assessment", "cn", "partial"),
    3: ("标准合同路径", "cn.pipia", "cn", "partial"),
    4: ("豁免情形诊断", "", "cn", "conflict"),
    5: ("SCC 审查", "eu.scc_review", "eu", "partial"),
    6: ("TIA 审查", "", "eu", "conflict"),
    7: ("GDPR 合规诊断", "", "eu", "conflict"),
    8: ("BD ROD 判断", "", "eu", "conflict"),
    9: ("14117 行政令合规", "us.eo_14117", "us", "partial"),
    10: ("CPRA 合规", "us.cpra", "us", "partial"),
}

_CANONICAL_RE = re.compile(r"^(task\d{2})_(case\d+)$")


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def paragraphs_of(path: Path) -> list[str]:
    doc = Document(str(path))
    return [p.text.strip() for p in doc.paragraphs]


def index_of_marker(paras: list[str], marker: str) -> int:
    for i, text in enumerate(paras):
        if text.startswith(marker):
            return i
    return -1


def slice_sections(paras: list[str]) -> dict[str, list[str]]:
    i_in = index_of_marker(paras, MARK_INPUT)
    i_out = index_of_marker(paras, MARK_OUTPUT)
    i_rem = index_of_marker(paras, MARK_REMARK)

    def span(start: int, end: int) -> list[str]:
        if start < 0:
            return []
        stop = end if end > start else len(paras)
        return [t for t in paras[start + 1 : stop] if t]

    return {
        "input": span(i_in, i_out),
        "output": span(i_out, i_rem),
        "remark": span(i_rem, -1),
        "_found": {"input": i_in >= 0, "output": i_out >= 0, "remark": i_rem >= 0},
    }


def load_manifest_entries() -> list[dict]:
    """Return the 50 authoritative file entries from manifest.json."""
    if not MANIFEST_PATH.exists():
        print(f"ERROR manifest not found: {MANIFEST_PATH}")
        raise SystemExit(2)

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entries: list[dict] = []
    for task_key in sorted(manifest.get("tasks", {})):
        for f in manifest["tasks"][task_key].get("files", []):
            entries.append(
                {
                    "file": f["file"],
                    "hash": f["hash"],
                    "size_bytes": f["size_bytes"],
                    "task_key": task_key,
                }
            )
    return entries


def parse_canonical_name(filename: str) -> tuple[int, int]:
    """Parse `taskNN_caseM.docx` into (task_no, case_no).

    The canonical name is `task{NN}_case{M}.docx`. This parser is used only to
    CROSS-CHECK the manifest-derived task/case identity; the manifest is the
    authoritative list and the name must agree with it or the build fails.
    """
    stem = filename[:-5] if filename.endswith(".docx") else filename
    m = re.fullmatch(r"task(\d{2})_case(\d+)", stem)
    if not m:
        raise ValueError(f"cannot parse canonical task/case from {filename}")
    return int(m.group(1)), int(m.group(2))


def load_gold_standard_source() -> str | None:
    """Return the gold-standard DOCX path declared in the manifest, if any."""
    if not MANIFEST_PATH.exists():
        return None
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    gs = manifest.get("gold_standard") or {}
    return gs.get("source")


def verify_disk_vs_manifest(entries: list[dict]) -> None:
    """Fail on any manifest/disk divergence.

    Rejects: manifest has file but disk missing; disk has file but manifest
    missing; count != 50; task/case parsed from name disagrees with manifest;
    SHA-256 mismatch; size mismatch. The gold-standard DOCX is a sibling of the
    50 seed files and is excluded from the case-file count check.
    """
    if len(entries) != 50:
        print(f"ERROR expected 50 manifest entries, got {len(entries)}")
        raise SystemExit(2)

    gold_source = load_gold_standard_source()
    disk_docx = {p.relative_to(ROOT).as_posix(): p for p in SRC_DIR.rglob("*.docx")}

    manifest_paths = set()
    for e in entries:
        rel = e["file"]
        manifest_paths.add(rel)
        if rel not in disk_docx:
            print(f"ERROR manifest file missing on disk: {rel}")
            raise SystemExit(2)

        path = disk_docx[rel]
        actual_sha = sha256_of(path)
        if actual_sha != e["hash"]:
            print(f"ERROR hash mismatch: {rel}")
            print(f"  manifest={e['hash']}")
            print(f"  disk    ={actual_sha}")
            raise SystemExit(2)

        actual_size = path.stat().st_size
        if actual_size != e["size_bytes"]:
            print(f"ERROR size mismatch: {rel} manifest={e['size_bytes']} disk={actual_size}")
            raise SystemExit(2)

        # Cross-check task/case identity parsed from the canonical name.
        try:
            task_no, case_no = parse_canonical_name(path.name)
        except ValueError as exc:
            print(f"ERROR non-canonical filename: {rel} ({exc})")
            raise SystemExit(2)

        expected_task_key = f"task{task_no:02d}"
        expected_case_id = f"task{task_no:02d}_case{case_no}"
        if expected_task_key != e["task_key"]:
            print(
                f"ERROR task key mismatch: {rel} parsed={expected_task_key} "
                f"manifest={e['task_key']}"
            )
            raise SystemExit(2)
        if task_no not in TASKS:
            print(f"ERROR unknown task_no {task_no} for {rel}")
            raise SystemExit(2)

    # Reject disk files not declared in the manifest. The gold-standard source
    # is declared separately at manifest.gold_standard.source, not as a case
    # file, so it is exempt from the case-file parity check.
    extra = [p for p in disk_docx if p not in manifest_paths and p != gold_source]
    if extra:
        print("ERROR disk files not declared in manifest:")
        for p in sorted(extra):
            print(f"  {p}")
        raise SystemExit(2)

    # Reject a case-file set size other than 50 (defense in depth). The gold
    # standard DOCX (if present) is not one of the 50 case files.
    case_files = [p for p in disk_docx if p != gold_source]
    if len(case_files) != 50:
        print(f"ERROR expected 50 source case DOCX on disk, got {len(case_files)}")
        raise SystemExit(2)


def build_record(path: Path, entry: dict) -> dict:
    task_no, case_no = parse_canonical_name(path.name)
    declared, module_id, jurisdiction, mapping_status = TASKS[task_no]

    paras = paragraphs_of(path)
    sec = slice_sections(paras)
    out_text = "\n".join(sec["output"])

    flags: list[str] = []
    for key in ("input", "output", "remark"):
        if not sec["_found"][key]:
            flags.append(f"marker_missing_{key}")
    hits = [tok for tok in PLACEHOLDER_TOKENS if tok in out_text]
    if hits:
        flags.append("placeholder_in_output:" + "|".join(hits))
    if out_text and len(out_text) < 300:
        flags.append("output_under_300_chars")
    if re.search(r"[Ѐ-ӿ]", "\n".join(paras)):
        flags.append("cyrillic_contamination")

    return {
        "case_id": f"task{task_no:02d}_case{case_no}",
        "task_no": task_no,
        "declared_task_name": declared,
        "jurisdiction": jurisdiction,
        "module_id": module_id,
        "mapping_status": mapping_status,
        "source_docx": str(path.relative_to(ROOT)),
        "source_sha256": entry["hash"],
        "source_size_bytes": entry["size_bytes"],
        "input": {"paragraphs": sec["input"]},
        "output_measure": {
            "chars": len(out_text),
            "paragraphs": len(sec["output"]),
            "placeholder_tokens": hits,
        },
        "expected_status": "pending_authoring",
        "expected_note": (
            "Output span exists in the source DOCX but is NOT promoted here. "
            "expected.json requires per-jurisdiction Legal sign-off (Q2)."
        ),
        "data_quality_flags": flags,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="write fixtures to disk")
    args = ap.parse_args()

    entries = load_manifest_entries()
    print(f"manifest entries      : {len(entries)}")

    verify_disk_vs_manifest(entries)
    print(f"source DOCX found     : {len(entries)}")
    print("manifest/disk parity  : OK (paths, task/case, size, SHA-256 all match)")

    records: list[dict] = []
    for e in entries:
        path = ROOT / e["file"]
        records.append(build_record(path, e))
    records.sort(key=lambda r: (r["task_no"], r["case_id"]))

    mapping: dict[str, int] = {}
    flag_tally: dict[str, int] = {}
    with_ph = 0
    min_chars = min(r["output_measure"]["chars"] for r in records)
    for r in records:
        mapping[r["mapping_status"]] = mapping.get(r["mapping_status"], 0) + 1
        if r["output_measure"]["placeholder_tokens"]:
            with_ph += 1
        for f in r["data_quality_flags"]:
            key = f.split(":")[0]
            flag_tally[key] = flag_tally.get(key, 0) + 1

    print(f"  mapping_status      : {mapping}")
    print(f"  output present      : {sum(1 for r in records if r['output_measure']['chars'] > 0)}/50")
    print(f"  min output chars    : {min_chars}")
    print(f"  with placeholder    : {with_ph}   clean: {50 - with_ph}")
    print(f"  quality flags       : {flag_tally}")
    print(f"  expected side       : 0 published / {len(records)} pending_authoring")

    if not args.write:
        print("DRY-RUN (pass --write to emit fixtures)")
        return 0

    in_dir = OUT_DIR / "inputs"
    in_dir.mkdir(parents=True, exist_ok=True)

    for r in records:
        (in_dir / f"{r['case_id']}.input.json").write_text(
            json.dumps(r, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    manifest = {
        "dataset": "seed-cases-v1",
        "generated_by": "scripts/build_seed_case_inputs.py",
        "source_manifest": str(MANIFEST_PATH.relative_to(ROOT)),
        "source_dir": str(SRC_DIR.relative_to(ROOT)),
        "case_count": len(records),
        "markers": {"input": MARK_INPUT, "output": MARK_OUTPUT, "remark": MARK_REMARK},
        "placeholder_tokens": list(PLACEHOLDER_TOKENS),
        "expected_status": "0 published / 50 pending_authoring",
        "scope_note": (
            "INPUT side only. No expected.json is produced. No case is asserted "
            "to be gold. Not wired into any test runner; config/case_inventory.json "
            "is unchanged."
        ),
        "summary": {
            "mapping_status": mapping,
            "with_placeholder": with_ph,
            "clean": 50 - with_ph,
            "min_output_chars": min_chars,
            "quality_flags": flag_tally,
        },
        "cases": [
            {
                "case_id": r["case_id"],
                "task_no": r["task_no"],
                "jurisdiction": r["jurisdiction"],
                "module_id": r["module_id"],
                "mapping_status": r["mapping_status"],
                "source_sha256": r["source_sha256"],
                "output_chars": r["output_measure"]["chars"],
                "data_quality_flags": r["data_quality_flags"],
            }
            for r in records
        ],
    }
    (OUT_DIR / "manifest.v1.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"WROTE {len(records)} inputs -> {in_dir.relative_to(ROOT)}")
    print(f"WROTE manifest        -> {(OUT_DIR / 'manifest.v1.json').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
