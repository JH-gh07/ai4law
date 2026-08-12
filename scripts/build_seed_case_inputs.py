#!/usr/bin/env python3
"""Extract seed-case fixtures from the 50 source DOCX files.

MARKERS (verified 2026-08-07 by dumping every heading-like paragraph in all 50
files; see the marker diagnostic in the session record):

    一、用户输入                 -> input section     (present in 50/50)
    二、标准答案（即系统输出）   -> output section    (present in 50/50)
    三、备注                     -> remark section    (present in 50/50)

An earlier version of this script searched for `二、输出信息` / `一、诊断结论`.
Those strings do not occur in any of the 50 files, so the output span was never
located and the script reported a bogus `no_output_marker_found: 45`.

PLACEHOLDER DETECTION: only multi-character tokens are matched, and only inside
the output span. The bare character `待` occurs 204 times across the corpus in
ordinary legal prose (`未主张`, `期待`) and inside the legitimate section
heading `（四）已知合规差距与待定项`; matching it produced a false
"all 50 are stubs" reading. Verified ground truth: `待补充` in 10 files
(task02 + task03), `待定` in the same 10, `待专家复核` in 0.

This script writes the INPUT side only. It does not write expected.json and it
does not assert any answer is gold. Promotion of the authored output spans to
evaluation expectations requires per-jurisdiction Legal sign-off (Q2).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "benchmarks/datasets/seed-cases-v1/_source"
OUT_DIR = ROOT / "benchmarks/datasets/seed-cases-v1"

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


def build_record(path: Path) -> dict:
    m = re.search(r"任务(\d+)_案例(\d+)", path.name)
    if not m:
        raise ValueError(f"cannot parse task/case from {path.name}")
    task_no, case_no = int(m.group(1)), int(m.group(2))
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
        "source_sha256": sha256_of(path),
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

    files = sorted(SRC_DIR.rglob("任务*_案例*_测试结果.docx"))
    print(f"source DOCX found: {len(files)}")
    if len(files) != 50:
        print("ERROR expected 50 source files")
        return 2

    records = [build_record(p) for p in files]
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
    exp_dir = OUT_DIR / "expected"
    in_dir.mkdir(parents=True, exist_ok=True)
    exp_dir.mkdir(parents=True, exist_ok=True)
    (exp_dir / ".gitkeep").write_text("", encoding="utf-8")

    for r in records:
        (in_dir / f"{r['case_id']}.input.json").write_text(
            json.dumps(r, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    manifest = {
        "dataset": "seed-cases-v1",
        "generated_by": "scripts/build_seed_case_inputs.py",
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
