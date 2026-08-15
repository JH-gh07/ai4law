#!/usr/bin/env python3
"""Extract seed-case INPUT spans from the 50 source DOCX files.

The unique input list is `benchmarks/datasets/seed-cases-v1/manifest.json`
(tasks -> files). File discovery by glob is FORBIDDEN here: the manifest is the
authoritative collection, and every file must match its recorded path, size and
SHA-256 exactly. Any missing/extra/renamed/rehashed file fails with a non-zero
exit code.

INPUT SPAN RULE: input = first input marker (or document start) -> first output
marker (or end of document). Output markers are used ONLY to bound the input
span; output text is never extracted or emitted.

    v1.0 legacy markers:
        一、用户输入               -> input start
        二、标准答案（即系统输出） -> input end (output NOT extracted)
    v2.0 corrected case1/2 markers:
        用户输入 / 待审查的BCR条款原文 -> input start
        标准答案（DPIA草案）/ 标准答案（TIA草案）/
        标准答案（错误与缺失清单）     -> input end (output NOT extracted)
    task04 (document review): no input marker -> document body from the title
        to 标准答案（错误与缺失清单） is the input.

This script writes the INPUT side ONLY. It produces `input.paragraphs` and never
extracts or emits output text. No expected.json is produced and no answer is
asserted to be gold.
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

# 输入段标记候选：输入段起点 = 命中后下一段；无命中则回退到文档开头。
# "一、用户输入" 是 v1.0 legacy；"用户输入"/"待审查的BCR条款原文" 是 v2.0 校正文件。
INPUT_MARKERS = ("一、用户输入", "用户输入", "待审查的BCR条款原文")

# 输出标记只用于给输入段定终点，不抽取、不写盘任何输出内容。
# "二、标准答案（即系统输出）" 是 v1.0 legacy；其余是 v2.0 校正文件。
OUTPUT_MARKERS = (
    "二、标准答案（即系统输出）",
    "标准答案（DPIA草案）",
    "标准答案（TIA草案）",
    "标准答案（错误与缺失清单）",
)

# task_no -> (declared folder name, module_id, jurisdiction, mapping_status)
# mapping_status vocabulary (adjudicated 2026-08-13, see
# status/check/task065/seed-mapping-adjudication.md):
#   partial — supported module; the declared task name is a sub-scenario of it
#   gap     — no product capability exists; must NOT enter the default runner
TASKS: dict[int, tuple[str, str, str, str]] = {
    1: ("合规路径诊断", "cn.transfer_diagnosis", "cn", "partial"),
    2: ("安全评估路径", "cn.security_assessment", "cn", "partial"),
    3: ("标准合同路径", "cn.pipia", "cn", "partial"),
    4: ("文档审查", "cn.document_review", "cn", "partial"),
    5: ("SCC 审查", "eu.scc_review", "eu", "partial"),
    6: ("BCR 审查", "eu.bcr_review", "eu", "partial"),
    7: ("DPIA 草案生成", "eu.dpia", "eu", "partial"),
    8: ("TIA 草案生成", "eu.tia", "eu", "partial"),
    9: ("14117 行政令合规", "us.eo_14117", "us", "partial"),
    10: ("CPRA 合规", "us.cpra", "us", "partial"),
}

# v2.0 中标记为【需修正/待修正】的 12 个案例：正文仍是 v1.0 旧内容（如「豁免情形诊断
# / BD ROD 判断」），尚未按 v2.0 改写为对应新任务（文档审查 / BCR / DPIA / TIA）。
# 这些案例在 Level B 转换前必须隔离，不得当作新模块的有效种子案例。
PENDING_CORRECTION_CASES: frozenset[str] = frozenset(
    f"task{tn:02d}_case{c}"
    for tn, cs in ((4, (3, 4, 5)), (6, (3, 4, 5)), (7, (3, 4, 5)), (8, (3, 4, 5)))
    for c in cs
)

_CANONICAL_RE = re.compile(r"^(task\d{2})_(case\d+)$")


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def paragraphs_of(path: Path) -> list[str]:
    doc = Document(str(path))
    return [p.text.strip() for p in doc.paragraphs]


def index_of_any_marker(paras: list[str], markers: tuple[str, ...]) -> int:
    """Return the first paragraph index starting with any marker, else -1."""
    for i, text in enumerate(paras):
        if any(text.startswith(m) for m in markers):
            return i
    return -1


def slice_input(paras: list[str]) -> dict:
    """Split off the INPUT span only; output markers only bound its end."""
    i_in = index_of_any_marker(paras, INPUT_MARKERS)
    i_out = index_of_any_marker(paras, OUTPUT_MARKERS)

    start = i_in + 1 if i_in >= 0 else 0
    stop = i_out if i_out > start else len(paras)

    return {
        "input": [t for t in paras[start:stop] if t],
        "_has_input_marker": i_in >= 0,
        "_has_output_marker": i_out >= 0,
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
    sec = slice_input(paras)

    flags: list[str] = []
    # 既无输入标记也无输出标记时，输入段无法可靠定界（task04 有输出标记兜底，不算）。
    if not sec["_has_input_marker"] and not sec["_has_output_marker"]:
        flags.append("marker_missing_input")
    if re.search(r"[Ѐ-ӿ]", "\n".join(paras)):
        flags.append("cyrillic_contamination")
    if f"task{task_no:02d}_case{case_no}" in PENDING_CORRECTION_CASES:
        flags.append("pending_correction:v2.0_需修正/待修正_内容未改回")

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
    empty_input = 0
    for r in records:
        mapping[r["mapping_status"]] = mapping.get(r["mapping_status"], 0) + 1
        if not r["input"]["paragraphs"]:
            empty_input += 1
        for f in r["data_quality_flags"]:
            key = f.split(":")[0]
            flag_tally[key] = flag_tally.get(key, 0) + 1

    print(f"  mapping_status      : {mapping}")
    print(f"  input present       : {len(records) - empty_input}/{len(records)}")
    print(f"  quality flags       : {flag_tally}")

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
        "input_markers": list(INPUT_MARKERS),
        "output_markers_note": (
            "Output markers are used only to bound the input span; output text "
            "is never extracted or emitted."
        ),
        "scope_note": (
            "INPUT side only. Only input.paragraphs is produced. No output, no "
            "expected.json, no gold assertion. Not wired into any test runner; "
            "config/case_inventory.json is unchanged."
        ),
        "summary": {
            "mapping_status": mapping,
            "input_present": len(records) - empty_input,
            "empty_input": empty_input,
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
                "input_paragraphs": len(r["input"]["paragraphs"]),
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
