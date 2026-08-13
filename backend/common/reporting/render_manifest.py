"""Task067 T07 — render manifest + cross-format equivalence proof.

The manifest is the machine proof that the Markdown / DOCX / PDF / canonical IR
artifacts all derive from the *same* ``DocumentIR``, without relying on a human
eyeballing three documents side by side.

Responsibilities:

1. render every artifact declared in ``render_contract.required_artifacts``
   (plus the canonical ``document_ir.json`` and ``citation_map.json``);
2. record the canonical IR SHA-256 and each artifact's path / size / SHA-256 /
   MIME, plus structural stats (DOCX paragraph/heading/table/numbering counts,
   PDF page count / font embedding / text-extraction status);
3. run fail-closed gates: compiler gate, IR-hash immutability, required-artifact
   completeness, cross-format identity equivalence, and the PDF CJK font gate;
4. atomically write ``render_manifest.json`` only after every artifact is on
   disk (a torn render can never produce a "success" manifest).

The manifest stores only structural identity (IDs, short titles, clause node
IDs + derived logical numbering, citation IDs, hashes and stats). It never
stores finding statement/recommendation text, uploaded source bodies, tokens,
or configuration, so it is safe to keep as an internal audit artifact.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.common.reporting.compiler import DocumentCompiler
from backend.common.reporting.renderers.docx import DocxRenderer
from backend.common.reporting.renderers.markdown import MarkdownRenderer
from backend.common.reporting.renderers.pdf import PdfRenderer
from backend.common.reporting.schema import ClauseNode, DocumentIR
from backend.common.reporting.schema.citations import CitationRegistry

MANIFEST_VERSION = "1.0"
RENDERER_VERSION = "1.0"

ArtifactStatus = Literal["rendered", "missing", "failed"]
GateStatus = Literal["pass", "fail", "blocked"]


# ── manifest models ─────────────────────────────────────────────────────────


class ArtifactRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: str
    path: str
    size: int
    sha256: str
    mime: str
    status: ArtifactStatus = "rendered"


class DocxStats(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paragraph_count: int
    heading_count: int
    table_count: int
    numbering_def_count: int


class FontRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    embedded: bool


class PdfStats(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_count: int
    fonts: list[FontRecord] = Field(default_factory=list)
    text_extracted: bool = False
    finding_ids_found: list[str] = Field(default_factory=list)


class ClauseIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    logical_number: str
    text: str


class BasisEntryIdentity(BaseModel):
    """Structural identity of one ``FindingBasis`` (task068 T10).

    Only the label + optional citation_ref are recorded — never the rationale.
    ``rationale`` is an *attribution* from an existing business field; the
    renderers read it from the IR unchanged, so it cannot be "added" across
    formats, and persisting it would risk leaking finding analysis text into an
    audit artifact.
    """

    model_config = ConfigDict(extra="forbid")

    label: str
    citation_ref: str | None = None


class GateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    status: GateStatus
    diagnostics: list[str] = Field(default_factory=list)


class RenderManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest_version: str = MANIFEST_VERSION
    schema_version: str
    compiler_version: str
    renderer_version: str = RENDERER_VERSION
    profile_id: str
    template_id: str | None = None

    document_id: str
    report_type: str
    canonical_ir_sha256: str

    section_ids: list[str]
    finding_ids: list[str]
    clause_identities: list[ClauseIdentity]
    basis_entry_identities: list[BasisEntryIdentity] = Field(default_factory=list)
    citation_ids: list[str]
    citation_count: int

    artifacts: list[ArtifactRecord]
    docx_stats: DocxStats | None = None
    pdf_stats: PdfStats | None = None

    gates: list[GateResult]

    render_status: Literal["success", "error"] = "success"
    generated_at: datetime


# ── helpers ─────────────────────────────────────────────────────────────────


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _atomic_write_text(path: Path, text: str) -> None:
    _atomic_write_bytes(path, text.encode("utf-8"))


def _canonical_ir_json(document: DocumentIR) -> str:
    """Deterministic IR serialization; the same bytes feed the IR hash."""
    return json.dumps(document.model_dump(mode="json"), ensure_ascii=False, indent=2)


def _iter_clause_nodes(clauses: list[ClauseNode]):
    for clause in clauses:
        yield clause
        yield from _iter_clause_nodes(clause.children)


def _section_heading(section) -> str:
    return f"{section.ordinal} {section.title}".strip() if section.ordinal else section.title


# Numbering tokens mirror the three renderers so the manifest's "logical
# numbering" matches what actually appears in every output.
_ROMAN = (
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
    (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
    (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
)


def _to_roman(value: int) -> str:
    result = ""
    remainder = value
    for numeral, symbol in _ROMAN:
        while remainder >= numeral:
            result += symbol
            remainder -= numeral
    return result


def _clause_number_token(style: str, position: int) -> str:
    if style == "decimal":
        return f"{position}."
    if style == "lower_alpha":
        return f"({chr(96 + position)})"
    if style == "lower_roman":
        return f"{_to_roman(position).lower()}."
    return ""  # "none"


def _clause_identities(clauses: list[ClauseNode]) -> list[ClauseIdentity]:
    identities: list[ClauseIdentity] = []

    def _walk(nodes: list[ClauseNode]) -> None:
        for position, node in enumerate(nodes, start=1):
            identities.append(ClauseIdentity(
                node_id=node.node_id,
                logical_number=_clause_number_token(node.numbering_style, position),
                text=node.text,
            ))
            _walk(node.children)

    _walk(clauses)
    return identities


def _citation_ordered_ids(registry: CitationRegistry) -> list[str]:
    """Citation IDs in footnote-number order (mirrors the appendix)."""
    numbers = registry.footnote_map()
    return [citation_id for citation_id, _ in sorted(numbers.items(), key=lambda kv: kv[1])]


# ── artifact identity extraction (ordered) ──────────────────────────────────


def _normalize_ws(text: str) -> str:
    """Collapse all whitespace so wrapping never breaks a text-anchor match."""
    return re.sub(r"\s+", " ", text)


def _order_diagnostics(text: str, anchors: list[str], label: str) -> list[str]:
    diagnostics: list[str] = []
    text = _normalize_ws(text)
    last = -1
    for anchor in anchors:
        index = text.find(_normalize_ws(anchor))
        if index == -1:
            diagnostics.append(f"{label} 缺失: {anchor!r}")
        elif index < last:
            diagnostics.append(f"{label} 顺序错误: {anchor!r} 出现在 {index} < {last}")
        else:
            last = index
    return diagnostics


def _presence_diagnostics(text: str, anchors: list[str], label: str) -> list[str]:
    """Set-membership check (no ordering), whitespace-normalized.

    Clause text can legitimately also appear in a finding's ``suggested_revision``
    field (the BCR adapter derives the clause tree from it), so clause identity is
    proven by presence rather than first-occurrence order. Ordering for clauses
    is captured by the manifest's ordered ``clause_identities`` inventory.
    """
    text = _normalize_ws(text)
    return [
        f"{label} 缺失: {anchor!r}"
        for anchor in anchors
        if text.find(_normalize_ws(anchor)) == -1
    ]


def _extract_markdown_text(markdown: str) -> str:
    return markdown


def _extract_docx_text(blob: bytes) -> str:
    from docx import Document
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    from io import BytesIO

    doc = Document(BytesIO(blob))
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


def _extract_pdf_text(blob: bytes) -> str:
    from io import BytesIO

    from pypdf import PdfReader

    reader = PdfReader(BytesIO(blob))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _finding_anchors(document: DocumentIR) -> list[str]:
    return [finding.finding_id for finding in document.findings]


def _section_anchors(document: DocumentIR) -> list[str]:
    return [_section_heading(section) for section in document.sections]


def _clause_anchors(document: DocumentIR) -> list[str]:
    anchors: list[str] = []
    for section in document.sections:
        for block in section.blocks:
            clauses = getattr(block, "clauses", None)
            if clauses:
                anchors.extend(node.text for node in _iter_clause_nodes(clauses))
    return anchors


def _citation_anchors(document: DocumentIR, registry: CitationRegistry) -> list[str]:
    anchors: list[str] = []
    for citation_id in _citation_ordered_ids(registry):
        record = registry.resolve(citation_id)
        number = registry.footnote_map().get(citation_id)
        if record is not None and number is not None:
            anchors.append(f"{number}. {record.title}")
    return anchors


def _basis_entry_identities(document: DocumentIR) -> list[BasisEntryIdentity]:
    """Ordered per-citation basis identity (label + citation_ref, no rationale).

    A single finding's multiple citations must surface as *separate* entries —
    this is the structural proof that the adapter did not collapse them into a
    ``；``-joined label wall (I068-22).
    """
    identities: list[BasisEntryIdentity] = []
    for finding in document.findings:
        for basis in finding.basis_entries:
            identities.append(BasisEntryIdentity(
                label=basis.label,
                citation_ref=basis.citation_ref,
            ))
    return identities


def _basis_anchors(document: DocumentIR) -> list[str]:
    return [identity.label for identity in _basis_entry_identities(document)]


# ── stats ───────────────────────────────────────────────────────────────────


def _docx_stats(blob: bytes) -> DocxStats:
    from io import BytesIO

    from docx import Document
    from docx.oxml.ns import qn

    doc = Document(BytesIO(blob))
    heading_count = sum(
        1 for paragraph in doc.paragraphs
        if paragraph.style.name.startswith("Heading") or paragraph.style.name == "Title"
    )
    numbering_def_count = 0
    numbering = doc.part.numbering_part.element
    numbering_def_count = len(numbering.findall(qn("w:num")))
    return DocxStats(
        paragraph_count=len(doc.paragraphs),
        heading_count=heading_count,
        table_count=len(doc.tables),
        numbering_def_count=numbering_def_count,
    )


def _pdf_stats(blob: bytes, document: DocumentIR, fonts) -> PdfStats:
    from io import BytesIO

    from pypdf import PdfReader

    reader = PdfReader(BytesIO(blob))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    font_records = [
        FontRecord(name=fonts.body, embedded=fonts.cjk_embedded),
        FontRecord(name=fonts.latin, embedded=(fonts.latin != "Helvetica")),
    ]
    return PdfStats(
        page_count=len(reader.pages),
        fonts=font_records,
        text_extracted=bool(text.strip()),
        finding_ids_found=[fid for fid in _finding_anchors(document) if fid in text],
    )


# ── gates ───────────────────────────────────────────────────────────────────


def _evaluate_equivalence(
    document: DocumentIR,
    registry: CitationRegistry,
    markdown_text: str,
    docx_text: str,
    pdf_text: str,
) -> GateResult:
    diagnostics: list[str] = []
    section_anchors = _section_anchors(document)
    finding_anchors = _finding_anchors(document)
    clause_anchors = _clause_anchors(document)
    citation_anchors = _citation_anchors(document, registry)
    basis_anchors = _basis_anchors(document)

    for label, text in (
        ("MARKDOWN", markdown_text),
        ("DOCX", docx_text),
        ("PDF", pdf_text),
    ):
        diagnostics.extend(_order_diagnostics(text, section_anchors, f"{label} section"))
        diagnostics.extend(_order_diagnostics(text, finding_anchors, f"{label} finding"))
        diagnostics.extend(_order_diagnostics(text, citation_anchors, f"{label} citation"))
        diagnostics.extend(_presence_diagnostics(text, clause_anchors, f"{label} clause"))
        # task068 T10 — per-citation basis entries must appear (not be collapsed
        # into a ``；`` label wall). Presence check: a label is a rendered anchor,
        # not an ordered sequence.
        diagnostics.extend(_presence_diagnostics(text, basis_anchors, f"{label} basis"))

    return GateResult(
        name="equivalence",
        status="pass" if not diagnostics else "fail",
        diagnostics=diagnostics,
    )


def _render_manifest_gates(
    document: DocumentIR,
    registry: CitationRegistry,
    compile_result,
    ir_hash_before: str,
    ir_hash_after: str,
    rendered: dict[str, bytes],
    markdown_text: str,
    docx_text: str,
    pdf_text: str,
    pdf_fonts,
    required_artifacts: list[str],
) -> list[GateResult]:
    gates: list[GateResult] = []

    gates.append(GateResult(
        name="compile",
        status="pass" if compile_result.status == "success" else "fail",
        diagnostics=[item.code for item in compile_result.diagnostics],
    ))

    gates.append(GateResult(
        name="ir_hash_immutable",
        status="pass" if ir_hash_before == ir_hash_after else "fail",
        diagnostics=[] if ir_hash_before == ir_hash_after else ["renderer 修改了 IR hash"],
    ))

    missing = [fmt for fmt in required_artifacts if fmt not in rendered or not rendered[fmt]]
    gates.append(GateResult(
        name="required_artifacts",
        status="pass" if not missing else "fail",
        diagnostics=[f"缺少/空产物: {fmt}" for fmt in missing],
    ))

    gates.append(_evaluate_equivalence(
        document, registry, markdown_text, docx_text, pdf_text,
    ))

    # PDF CJK font gate: BLOCKED_BY_FONT until a licensed+hashed CJK asset is
    # tracked; never reported as pass while the CID font stays non-embedded.
    if pdf_fonts.cjk_embedded:
        font_gate = GateResult(name="pdf_font_embedding", status="pass", diagnostics=[])
    else:
        font_gate = GateResult(
            name="pdf_font_embedding",
            status="blocked",
            diagnostics=["BLOCKED_BY_FONT: 无可再分发 CJK 字体，CJK 退化为非嵌入 STSong-Light"],
        )
    gates.append(font_gate)

    return gates


def _artifact_status(gates: list[GateResult]) -> GateResult | None:
    for gate in gates:
        if gate.status == "fail":
            return gate
    return None


# ── public API ──────────────────────────────────────────────────────────────


def build_render_manifest(
    document: DocumentIR,
    registry: CitationRegistry | None = None,
    output_dir: Path | str | None = None,
    *,
    module: str = "bcr",
    task_id: str = "",
) -> RenderManifest:
    """Render all artifacts, write them, and atomically write the manifest.

    Returns the :class:`RenderManifest`. ``output_dir`` defaults to the plan's
    ``outputs/<module>/<task_id>/outputs`` layout when ``task_id`` is provided.
    """
    registry = registry or CitationRegistry(document.citations)
    output_dir = Path(output_dir) if output_dir is not None else (
        Path("outputs") / module / task_id / "outputs" if task_id else Path("outputs") / module / "outputs"
    )

    # 1. fail-closed compile gate.
    compile_result = DocumentCompiler().compile(document, registry)
    if compile_result.status != "success":
        manifest = RenderManifest(
            schema_version=document.schema_version,
            compiler_version=document.compiler_version,
            profile_id=document.render_contract.profile_id,
            template_id=document.render_contract.template_id,
            document_id=document.document_id,
            report_type=document.report_type,
            canonical_ir_sha256="",
            section_ids=[section.section_id for section in document.sections],
            finding_ids=[finding.finding_id for finding in document.findings],
            clause_identities=_clause_identities(_all_clauses(document)),
            basis_entry_identities=_basis_entry_identities(document),
            citation_ids=_citation_ordered_ids(registry),
            citation_count=len(registry.records()),
            artifacts=[],
            gates=[GateResult(
                name="compile",
                status="fail",
                diagnostics=[item.code for item in compile_result.diagnostics],
            )],
            render_status="error",
            generated_at=datetime.now(timezone.utc),
        )
        return manifest

    # 2. Canonical IR bytes (the single authoritative hash source).
    ir_json = _canonical_ir_json(document)
    ir_bytes = ir_json.encode("utf-8")
    ir_hash_before = _sha256_bytes(ir_bytes)

    # 3. Render each required format.
    markdown_text = MarkdownRenderer().render(document, registry)
    docx_bytes = DocxRenderer().render(document, registry)
    pdf_renderer = PdfRenderer()
    pdf_fonts = pdf_renderer._register_fonts()
    pdf_bytes = pdf_renderer.render(document, registry)

    ir_hash_after = _sha256_bytes(_canonical_ir_json(document).encode("utf-8"))

    # 4. Citation map (self-contained; footnote number → citation identity).
    footnote_map: dict[str, dict] = {}
    all_items: list[dict] = []
    for citation_id, number in registry.footnote_map().items():
        record = registry.resolve(citation_id)
        entry = {
            "citation_id": citation_id,
            "number": number,
            "title": record.title,
            "source_id": record.source_id,
            "source_type": record.source_type,
            "article": record.locator.article if record.locator else None,
            "paragraph": record.locator.paragraph if record.locator else None,
            "item": record.locator.item if record.locator else None,
        }
        footnote_map[str(number)] = entry
        all_items.append(entry)
    citation_map_json = json.dumps(
        {"task_id": task_id, "module": module, "footnote_map": footnote_map, "all_items": all_items},
        ensure_ascii=False,
        indent=2,
    )

    # 5. Artifact records.
    artifacts: list[ArtifactRecord] = [
        ArtifactRecord(
            format="DOCUMENT_IR", path="document_ir.json", size=len(ir_bytes),
            sha256=ir_hash_before, mime="application/json", status="rendered",
        ),
        ArtifactRecord(
            format="MARKDOWN", path="report.md", size=len(markdown_text.encode("utf-8")),
            sha256=_sha256_bytes(markdown_text.encode("utf-8")), mime="text/markdown", status="rendered",
        ),
        ArtifactRecord(
            format="DOCX", path="report.docx", size=len(docx_bytes),
            sha256=_sha256_bytes(docx_bytes),
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            status="rendered",
        ),
        ArtifactRecord(
            format="PDF", path="report.pdf", size=len(pdf_bytes),
            sha256=_sha256_bytes(pdf_bytes), mime="application/pdf", status="rendered",
        ),
        ArtifactRecord(
            format="CITATION_MAP", path="citation_map.json", size=len(citation_map_json.encode("utf-8")),
            sha256=_sha256_bytes(citation_map_json.encode("utf-8")), mime="application/json", status="rendered",
        ),
    ]

    # 6. Write artifacts (before the manifest).
    _atomic_write_text(output_dir / "document_ir.json", ir_json)
    _atomic_write_text(output_dir / "report.md", markdown_text)
    _atomic_write_bytes(output_dir / "report.docx", docx_bytes)
    _atomic_write_bytes(output_dir / "report.pdf", pdf_bytes)
    _atomic_write_text(output_dir / "citation_map.json", citation_map_json)

    # 7. Stats + equivalence.
    docx_text = _extract_docx_text(docx_bytes)
    pdf_text = _extract_pdf_text(pdf_bytes)
    docx_stats = _docx_stats(docx_bytes)
    pdf_stats = _pdf_stats(pdf_bytes, document, pdf_fonts)

    rendered = {"MARKDOWN": markdown_text.encode("utf-8"), "DOCX": docx_bytes, "PDF": pdf_bytes}
    gates = _render_manifest_gates(
        document=document,
        registry=registry,
        compile_result=compile_result,
        ir_hash_before=ir_hash_before,
        ir_hash_after=ir_hash_after,
        rendered=rendered,
        markdown_text=markdown_text,
        docx_text=docx_text,
        pdf_text=pdf_text,
        pdf_fonts=pdf_fonts,
        required_artifacts=document.render_contract.required_artifacts,
    )

    failed_gate = _artifact_status(gates)
    manifest = RenderManifest(
        schema_version=document.schema_version,
        compiler_version=document.compiler_version,
        profile_id=document.render_contract.profile_id,
        template_id=document.render_contract.template_id,
        document_id=document.document_id,
        report_type=document.report_type,
        canonical_ir_sha256=ir_hash_before,
        section_ids=[section.section_id for section in document.sections],
        finding_ids=[finding.finding_id for finding in document.findings],
        clause_identities=_clause_identities(_all_clauses(document)),
        basis_entry_identities=_basis_entry_identities(document),
        citation_ids=_citation_ordered_ids(registry),
        citation_count=len(registry.records()),
        artifacts=artifacts,
        docx_stats=docx_stats,
        pdf_stats=pdf_stats,
        gates=gates,
        render_status="error" if failed_gate is not None else "success",
        generated_at=datetime.now(timezone.utc),
    )

    # 8. Atomically write the manifest last.
    manifest_json = json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2)
    _atomic_write_text(output_dir / "render_manifest.json", manifest_json)
    return manifest


def _all_clauses(document: DocumentIR) -> list[ClauseNode]:
    clauses: list[ClauseNode] = []
    for section in document.sections:
        for block in section.blocks:
            block_clauses = getattr(block, "clauses", None)
            if block_clauses:
                clauses.extend(block_clauses)
    return clauses


def verify_render_manifest(manifest: RenderManifest, output_dir: Path | str) -> list[GateResult]:
    """Re-open artifacts and re-check hashes + equivalence from disk.

    Used by the acceptance tests to prove tampering any artifact (hash) or
    removing/reordering a finding (equivalence) flips the corresponding gate.
    """
    output_dir = Path(output_dir)
    gates: list[GateResult] = []

    # Hash gate.
    hash_diagnostics: list[str] = []
    for artifact in manifest.artifacts:
        path = output_dir / artifact.path
        if not path.exists():
            hash_diagnostics.append(f"产物缺失: {artifact.path}")
            continue
        actual = _sha256_file(path)
        if actual != artifact.sha256:
            hash_diagnostics.append(f"hash 不匹配: {artifact.path}")
    gates.append(GateResult(
        name="artifact_hash",
        status="pass" if not hash_diagnostics else "fail",
        diagnostics=hash_diagnostics,
    ))

    # Equivalence gate (re-extract from the three render formats).
    markdown_path = output_dir / "report.md"
    docx_path = output_dir / "report.docx"
    pdf_path = output_dir / "report.pdf"
    if not (markdown_path.exists() and docx_path.exists() and pdf_path.exists()):
        gates.append(GateResult(
            name="equivalence",
            status="fail",
            diagnostics=["产物缺失，无法做等价校验"],
        ))
        return gates

    diagnostics: list[str] = []
    # Finding identity is the tamper-sensitive anchor: deleting or reordering a
    # finding in any artifact breaks the ordered sequence check below.
    basis_anchors = [identity.label for identity in manifest.basis_entry_identities]
    for fmt, text in (
        ("MARKDOWN", markdown_path.read_text(encoding="utf-8")),
        ("DOCX", _extract_docx_text(docx_path.read_bytes())),
        ("PDF", _extract_pdf_text(pdf_path.read_bytes())),
    ):
        diagnostics.extend(_order_diagnostics(text, manifest.finding_ids, f"{fmt} finding"))
        diagnostics.extend(_presence_diagnostics(text, basis_anchors, f"{fmt} basis"))
    gates.append(GateResult(
        name="equivalence",
        status="pass" if not diagnostics else "fail",
        diagnostics=diagnostics,
    ))

    return gates


__all__ = [
    "MANIFEST_VERSION",
    "RENDERER_VERSION",
    "ArtifactRecord",
    "BasisEntryIdentity",
    "ClauseIdentity",
    "DocxStats",
    "FontRecord",
    "GateResult",
    "PdfStats",
    "RenderManifest",
    "build_render_manifest",
    "verify_render_manifest",
]
