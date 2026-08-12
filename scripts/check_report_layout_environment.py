#!/usr/bin/env python3
"""Freeze and verify the BCR report-layout environment baseline (task067 T00).

This script is the *automatic* half of the T00 gate. It is deliberately split
into two concerns so the same check can prove both of the following:

1. Environment gate (default): report which PDF/DOCX tools and CJK font assets
   exist, and *refuse* to claim a DOCX visual pass when LibreOffice is absent.
   A missing LibreOffice is reported as ``BLOCKED_BY_TOOLING`` and returns a
   non-zero exit — never a silent skip.

2. Artifact structure gates (``--check-docx/--check-pdf/--check-md``): assert
   the *layout contract* (native Word tables, heading styles, header/footer,
   embedded fonts, no character-by-character break) against a real artifact.
   These gates are expected to fail on the pre-fix baseline and pass only on
   the new IR renderer output.

Exit codes:
    0  environment healthy AND every requested artifact gate passed
    1  artifact gate failure (old/broken artifact)
    2  BLOCKED_BY_TOOLING (LibreOffice missing) or internal error

This script is read-only. It never rewrites business data or user artifacts.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STATUS_DIR = ROOT / "status" / "check" / "task067"

# PDF text-breaking fingerprints observed on the pre-fix baseline.
#
# The old renderer lays the finding detail out as a six-column grid, so a
# short token like "HIGH" is split across three column rows ("HIG" + "H") and
# "MEDIUM" becomes "ME" / "DIU" / "M", while the finding ID "BCR-C-1.1" is
# split into "-C-1" / ".1". ``pdftotext`` (without ``-layout``) emits each
# column cell as its own line, so these fragments surface as *standalone
# lines* — which never occur in a correctly flowing paragraph renderer.
_BROKEN_TOKEN_FRAGMENTS = (
    ("HIG", "risk HIGH broken across columns"),
    ("ME", "risk MEDIUM broken across columns"),
    ("DIU", "risk MEDIUM broken across columns"),
    ("-C-1", "finding ID broken character-by-character"),
    (".1", "finding ID broken character-by-character"),
)

# A six-column finding detail table is the source of both the Markdown pipe
# residue and the PDF char break. The new layout uses a short summary table
# plus longitudinal finding blocks instead.
_FINDING_DETAIL_SIX_COL = (
    re.compile(r"\|\s*检查项\s*\|.*\|\s*法律依据\s*\|"),
    re.compile(r"\|\s*主题\s*\|.*\|\s*现状\s*\|.*\|\s*整改建议\s*\|"),
)


@dataclass
class ToolResult:
    name: str
    path: str | None
    available: bool


@dataclass
class FontAsset:
    path: str
    sha256: str
    license: str | None
    covers_cjk: bool


@dataclass
class GateResult:
    name: str
    status: str  # pass | fail | blocked
    detail: str
    metrics: dict = field(default_factory=dict)


def _which(tool: str) -> str | None:
    return shutil.which(tool)


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60)


def _sha256(path: Path) -> str:
    return subprocess.run(
        ["shasum", "-a", "256", str(path)], capture_output=True, text=True
    ).stdout.split()[0]


def check_tools() -> tuple[list[ToolResult], bool]:
    required = ["uv", "pdftotext", "pdfinfo", "pdffonts", "pdftoppm", "unzip", "zipinfo"]
    visual = ["libreoffice", "soffice"]
    results: list[ToolResult] = []
    for name in required:
        path = _which(name)
        results.append(ToolResult(name, path, path is not None))
    visual_available = False
    for name in visual:
        path = _which(name)
        results.append(ToolResult(name, path, path is not None))
        visual_available = visual_available or (path is not None)
    return results, visual_available


def _scan_fonts() -> list[FontAsset]:
    """Inventory CJK-capable font assets. Latin-only PDF.js fonts are ignored.

    There is no reliable pure-Python way to detect CJK coverage from a TTF
    header alone without a font library, so this scan reports *candidate*
    CJK font assets by filename hint and leaves coverage confirmation to the
    PDF ``pdffonts emb=yes`` gate. The key contract invariant is that the repo
    currently has NO dedicated CJK font asset — which the baseline records.
    """
    cjk_hints = ("noto", "sourcehan", "sourcehans", "pingfang", "microsoftyahei",
                 "simsun", "simhei", "song", "hei", "kai", "cjk", "wqy", "zen",
                 "fang", "ming", "gothic", "han")
    candidates: list[FontAsset] = []
    search_roots = [ROOT / "resources", ROOT / "assets", ROOT / "frontend" / "public"]
    seen: set[str] = set()
    for root in search_roots:
        if not root.exists():
            continue
        for ext in ("*.ttf", "*.otf", "*.ttc", "*.woff", "*.woff2"):
            for p in root.rglob(ext):
                key = str(p)
                if key in seen:
                    continue
                seen.add(key)
                lower = p.name.lower()
                if not any(hint in lower for hint in cjk_hints):
                    continue
                candidates.append(FontAsset(
                    path=str(p.relative_to(ROOT)),
                    sha256=_sha256(p),
                    license=None,
                    covers_cjk=True,
                ))
    return candidates


def _check_docx(path: Path) -> GateResult:
    if not path.exists():
        return GateResult("docx", "fail", f"not found: {path}")
    try:
        with zipfile.ZipFile(path) as z:
            names = set(z.namelist())
            doc = z.read("word/document.xml").decode("utf-8", errors="replace")
            styles = z.read("word/styles.xml").decode("utf-8", errors="replace") if "word/styles.xml" in names else ""
            numbering = z.read("word/numbering.xml").decode("utf-8", errors="replace") if "word/numbering.xml" in names else ""
    except (zipfile.BadZipFile, KeyError) as exc:
        return GateResult("docx", "fail", f"unreadable OOXML: {exc}")

    paragraphs = len(re.findall(r"<w:p[ >]", doc))
    tables = doc.count("<w:tbl>")
    headings = len(re.findall(r'w:val="Heading[123]"', doc))
    has_header = any("header" in n for n in names)
    has_footer = any("footer" in n for n in names)
    numbering_defs = numbering.count("<w:num ")
    pipe_residue = "| --- |" in doc or bool(re.search(r"\|\s*-{2,}\s*\|", doc))

    failures: list[str] = []
    if tables == 0:
        failures.append("Word tables=0 (no native tables; finding detail is a plain paragraph)")
    if headings == 0:
        failures.append("no Heading 1/2/3 styles (flat Normal paragraphs)")
    if not has_header:
        failures.append("no header part (missing page header)")
    if not has_footer:
        failures.append("no footer part (missing page number)")
    if pipe_residue:
        failures.append("Markdown pipe residue embedded in DOCX text")

    metrics = {
        "paragraphs": paragraphs,
        "tables": tables,
        "headings": headings,
        "header": has_header,
        "footer": has_footer,
        "numbering_defs": numbering_defs,
    }
    if failures:
        return GateResult("docx", "fail", "; ".join(failures), metrics)
    return GateResult("docx", "pass", "native structure present", metrics)


def _check_pdf(path: Path) -> GateResult:
    if not path.exists():
        return GateResult("pdf", "fail", f"not found: {path}")
    pdfinfo = _run(["pdfinfo", str(path)])
    pdffonts = _run(["pdffonts", str(path)])
    # Plain (non ``-layout``) extraction preserves linear reading order, which
    # is what surfaces column-split fragments as standalone lines. ``-layout``
    # re-adds column spacing and would hide the exact break.
    pdftotext = _run(["pdftotext", str(path), "-"])

    if pdfinfo.returncode != 0:
        return GateResult("pdf", "fail", f"pdfinfo failed: {pdfinfo.stderr.strip()}")
    text = pdftotext.stdout
    pages_match = re.search(r"Pages:\s+(\d+)", pdfinfo.stdout)
    pages = int(pages_match.group(1)) if pages_match else -1

    failures: list[str] = []
    # Fonts must be embedded. The old baseline uses Helvetica/STSong-Light emb=no.
    embedded = 0
    total = 0
    for line in pdffonts.stdout.splitlines()[2:]:
        cells = line.split()
        if len(cells) < 7 or not cells[0].strip():
            continue
        total += 1
        if cells[5] == "yes":
            embedded += 1
    if total == 0:
        failures.append("no fonts detected")
    elif embedded < total:
        failures.append(f"fonts embedded={embedded}/{total} (require all emb=yes)")

    standalone_lines = {line.strip() for line in text.splitlines()}
    for fragment, label in _BROKEN_TOKEN_FRAGMENTS:
        if fragment in standalone_lines:
            failures.append(label)

    if "| --- |" in text or re.search(r"\|\s*-{2,}\s*\|", text):
        failures.append("Markdown table separator residue in PDF text layer")

    metrics = {
        "pages": pages,
        "fonts_total": total,
        "fonts_embedded": embedded,
        "text_chars": len(text),
    }
    if failures:
        return GateResult("pdf", "fail", "; ".join(failures), metrics)
    return GateResult("pdf", "pass", "embedded fonts + flowing text layer", metrics)


def _check_md(path: Path) -> GateResult:
    if not path.exists():
        return GateResult("markdown", "fail", f"not found: {path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    failures: list[str] = []
    if any(p.search(text) for p in _FINDING_DETAIL_SIX_COL):
        failures.append("six-column finding detail table (pipe residue)")

    metrics = {"pipe_table_rows": len(re.findall(r"^\|", text, re.MULTILINE))}
    if failures:
        return GateResult("markdown", "fail", "; ".join(failures), metrics)
    return GateResult("markdown", "pass", "no six-column finding detail table", metrics)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-docx", type=Path, help="assert DOCX layout contract")
    parser.add_argument("--check-pdf", type=Path, help="assert PDF layout contract")
    parser.add_argument("--check-md", type=Path, help="assert Markdown layout contract")
    parser.add_argument("--write", type=Path, help="write environment JSON to this path")
    args = parser.parse_args()

    tools, visual_available = check_tools()
    fonts = _scan_fonts()

    environment = {
        "task": "task067",
        "stage": "T00",
        "tools": {t.name: {"path": t.path, "available": t.available} for t in tools},
        "visual_conversion_available": visual_available,
        "visual_conversion_status": "AVAILABLE" if visual_available else "BLOCKED_BY_TOOLING",
        "cjk_font_assets": [f.__dict__ for f in fonts],
        "cjk_font_assets_note": (
            "No dedicated CJK font asset in version control. Latin-only PDF.js "
            "Liberation Sans is present but cannot render Chinese headings/body. "
            "A redistributable CJK font must be added before the PDF gate can pass."
        ),
    }

    gates: list[GateResult] = []
    if args.check_docx:
        gates.append(_check_docx(args.check_docx))
    if args.check_pdf:
        gates.append(_check_pdf(args.check_pdf))
    if args.check_md:
        gates.append(_check_md(args.check_md))

    report = {"environment": environment, "gates": [g.__dict__ for g in gates]}

    # Determine exit code.
    exit_code = 0
    if not visual_available:
        exit_code = 2
    for gate in gates:
        if gate.status == "fail":
            exit_code = 1 if exit_code == 0 else exit_code

    write_path = args.write or (STATUS_DIR / "environment.json")
    write_path.parent.mkdir(parents=True, exist_ok=True)
    write_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Human-readable summary.
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not visual_available:
        print(
            "\n⚠  BLOCKED_BY_TOOLING: libreoffice/soffice not found. "
            "DOCX visual acceptance cannot be marked PASS; only XML/openability "
            "gates are executable on this machine.",
            file=sys.stderr,
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
