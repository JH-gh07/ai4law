#!/usr/bin/env python3
"""Render + gate the BCR report artifacts (task067 T08).

This is the repeatable-failure half of the layout gate: it renders Markdown /
DOCX / PDF (and a canonical IR + citation map) from a ``DocumentIR``, writes a
``render_manifest.json``, then re-runs the layout-contract verifiers and the
manifest hash/equivalence gates. The same checks are exercised by
``backend/common/reporting/tests/test_layout_contract.py``; this script turns
them into an artifact-level gate that produces JSON evidence.

Exit codes:
    0  every gate passed
    1  one or more gates failed
    2  BLOCKED (PDF CJK font gate blocked by the missing redistributable font)

Usage:
    python scripts/check_report_artifacts.py --ir <document_ir.json> \
        [--out <output_dir>] [--write <structural_checks.json>]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.common.reporting import DocumentIR  # noqa: E402
from backend.common.reporting.layout_gate import (  # noqa: E402
    broken_word_fragments,
    markdown_table_residue,
    six_column_table,
)
from backend.common.reporting.render_manifest import (  # noqa: E402
    build_render_manifest,
    verify_render_manifest,
)

STATUS_DIR = ROOT / "status" / "check" / "task067"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _text_from_docx(path: Path) -> str:
    from docx import Document
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    doc = Document(str(path))
    parts: list[str] = []
    for child in doc.element.body.iterchildren():
        if child.tag == qn("w:p"):
            parts.append(Paragraph(child, doc).text)
        elif child.tag == qn("w:tbl"):
            table = Table(child, doc)
            for row in table.rows:
                for cell in row.cells:
                    parts.append(cell.text)
    return "\n".join(parts)


def _text_from_pdf(path: Path) -> str:
    pdftotext = shutil.which("pdftotext")
    if pdftotext:
        result = subprocess.run(
            [pdftotext, "-layout", str(path), "-"], capture_output=True, text=True
        )
        if result.returncode == 0:
            return result.stdout
    from io import BytesIO

    from pypdf import PdfReader

    return "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(path.read_bytes())).pages)


def _gate(name: str, status: str, diagnostics: list[str], metrics: dict | None = None) -> dict:
    return {"name": name, "status": status, "diagnostics": diagnostics, "metrics": metrics or {}}


def _check_text_layers(output_dir: Path) -> list[dict]:
    gates: list[dict] = []
    md = (output_dir / "report.md").read_text(encoding="utf-8")
    docx_text = _text_from_docx(output_dir / "report.docx")
    pdf_text = _text_from_pdf(output_dir / "report.pdf")

    # Six-column degradation is the core issue067 regression; check all three.
    for label, text in (("markdown", md), ("docx", docx_text), ("pdf", pdf_text)):
        gates.append(_gate(
            f"six_column_table/{label}", "fail" if six_column_table(text) else "pass",
            six_column_table(text),
        ))

    # Broken fragments (char-by-char split) surface in the PDF/DOCX text layer.
    for label, text in (("docx", docx_text), ("pdf", pdf_text)):
        gates.append(_gate(
            f"broken_fragments/{label}", "fail" if broken_word_fragments(text) else "pass",
            broken_word_fragments(text),
        ))

    # Markdown pipe residue must never leak into DOCX/PDF.
    for label, text in (("docx", docx_text), ("pdf", pdf_text)):
        gates.append(_gate(
            f"markdown_residue/{label}", "fail" if markdown_table_residue(text) else "pass",
            markdown_table_residue(text),
        ))

    return gates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ir", type=Path, required=True, help="path to document_ir.json")
    parser.add_argument("--out", type=Path, help="output directory for artifacts + manifest")
    parser.add_argument("--write", type=Path, help="evidence JSON path (default: status/check/task067/structural_checks.json)")
    args = parser.parse_args()

    ir_path = args.ir
    output_dir = args.out or (ir_path.parent / "outputs")
    write_path = args.write or (STATUS_DIR / "structural_checks.json")

    data = json.loads(ir_path.read_text(encoding="utf-8"))
    document = DocumentIR.model_validate(data)
    registry = None  # build_render_manifest reconstructs from document.citations

    manifest = build_render_manifest(document, registry, output_dir, module="bcr", task_id=document.document_id)

    text_gates = _check_text_layers(output_dir)
    manifest_gates = [gate.model_dump(mode="json") for gate in manifest.gates]

    # Re-verify hash + equivalence from disk.
    verify_gates = [gate.model_dump(mode="json") for gate in verify_render_manifest(manifest, output_dir)]

    all_gates = manifest_gates + text_gates + verify_gates

    report = {
        "task": "task067",
        "stage": "T08",
        "document_id": document.document_id,
        "report_type": document.report_type,
        "output_dir": str(output_dir),
        "canonical_ir_sha256": manifest.canonical_ir_sha256,
        "manifest_render_status": manifest.render_status,
        "artifacts": [
            {
                "path": artifact.path,
                "size": artifact.size,
                "sha256": artifact.sha256,
                "mime": artifact.mime,
            }
            for artifact in manifest.artifacts
        ],
        "gates": all_gates,
    }

    write_path.parent.mkdir(parents=True, exist_ok=True)
    write_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))

    # Exit code: blocked(2) > fail(1) > pass(0).
    blocked = any(gate["status"] == "blocked" for gate in all_gates)
    failed = any(gate["status"] == "fail" for gate in all_gates)
    if failed:
        print("\n❌ one or more layout gates failed", file=sys.stderr)
        return 1
    if blocked:
        print("\n⚠  BLOCKED_BY_FONT: PDF CJK font gate remains blocked (no redistributable CJK asset).", file=sys.stderr)
        return 2
    print("\n✅ all layout gates passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
