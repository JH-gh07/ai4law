"""task068 T10 — cross-format collection gate + body-content fail-closed mutations.

Complements ``test_render_manifest.py`` (hash/equivalence) and
``test_compiler_v4.py`` (finding/clause/action gates). This file covers the
T10 automatic-gate additions:

- duplicate section ``ordinal`` is rejected (no silent section shadowing);
- raw request JSON / absolute filesystem paths are rejected from body text
  (defense-in-depth below the adapter sanitization of T09);
- ``basis_entries`` render per-citation (one label per line), never a ``；``
  label wall (I068-22);
- the render manifest records per-citation basis identity and proves it reaches
  Markdown / DOCX / PDF (and that deleting one flips the equivalence gate).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.common.reporting import (
    CitationLocator,
    CitationNoteBlock,
    CitationRecord,
    CitationRegistry,
    DocumentCompiler,
    DocumentIR,
    FindingBasis,
    FindingDetailBlock,
    FindingRecord,
    Provenance,
    ReportMetadata,
    SectionIR,
)
from backend.common.reporting.render_manifest import build_render_manifest, verify_render_manifest
from backend.common.reporting.renderers.markdown import MarkdownRenderer

TS = datetime(2026, 8, 8, tzinfo=timezone.utc)


def _citation(cid: str, title: str) -> CitationRecord:
    return CitationRecord(
        citation_id=cid,
        source_id=f"SRC-{cid}",
        source_type="regulation",
        title=title,
        locator=CitationLocator(article="1"),
        authority_level="high",
        binding_force="mandatory",
        can_enter_external_report=True,
    )


def _registry() -> CitationRegistry:
    return CitationRegistry([
        _citation("cit-1", "个人信息保护法"),
        _citation("cit-2", "数据出境安全评估办法"),
    ])


def _finding(fid: str, *, basis_entries: list[FindingBasis]) -> FindingRecord:
    return FindingRecord(
        finding_id=fid,
        requirement_id=f"R-{fid}",
        title=f"问题 {fid}",
        risk_level="HIGH",
        risk_score=60.0,
        statement="现状不合规，需要整改。",
        legal_basis=[basis.label for basis in basis_entries],
        recommendation="补齐合规要求。",
        citation_refs=[basis.citation_ref for basis in basis_entries if basis.citation_ref],
        basis_entries=basis_entries,
    )


def _document(*, findings=None, sections_extra=None) -> tuple[DocumentIR, CitationRegistry]:
    registry = _registry()
    findings = findings or []
    sections: list[SectionIR] = []
    if findings:
        sections.append(SectionIR(section_id="s-detail", title="详细 finding", level=1, ordinal="1", blocks=[
            FindingDetailBlock(block_id=f"detail-{f.finding_id}", finding_ref=f.finding_id)
            for f in findings
        ]))
        # A citation appendix so the manifest's citation anchors actually render.
        sections.append(SectionIR(section_id="s-cite", title="引用法规与条文", level=1, ordinal="2", blocks=[
            CitationNoteBlock(block_id="cite", citation_refs=["cit-1", "cit-2"]),
        ]))
    sections.extend(sections_extra or [])
    document = DocumentIR(
        compiler_version="0.1.0",
        prompt_version="test",
        template_version="test",
        model="test-model",
        document_id="doc-t10",
        report_type="review",
        metadata=ReportMetadata(title="T10 门禁测试"),
        provenance=Provenance(generated_at=TS),
        findings=findings,
        citations=list(registry.records().values()),
        sections=sections,
    )
    return document, registry


def _two_basis_finding() -> FindingRecord:
    return _finding("F-1", basis_entries=[
        FindingBasis(label="《个人信息保护法》第38条", citation_ref="cit-1",
                     rationale="未约定安全评估，不满足出境条件。"),
        FindingBasis(label="《数据出境安全评估办法》第4条", citation_ref="cit-2",
                     rationale="需完成安全评估后方可出境。"),
    ])


# ── compiler: duplicate ordinal ──────────────────────────────────────────────


def test_duplicate_section_ordinal_is_rejected() -> None:
    document, registry = _document(sections_extra=[
        SectionIR(section_id="s-a", title="甲", level=1, ordinal="2", blocks=[]),
        SectionIR(section_id="s-b", title="乙", level=1, ordinal="2", blocks=[]),
    ])
    result = DocumentCompiler().compile(document, registry)
    assert result.status == "error"
    assert any(d.code == "SECTION_ORDINAL_DUPLICATE" for d in result.diagnostics)


# ── compiler: raw JSON / absolute path in body ───────────────────────────────


@pytest.mark.parametrize("body", [
    '{"business_model": "B2B", "storage_uri": "/data/x.pdf"}',
    '[{"risk": "HIGH"}, {"risk": "LOW"}]',
    "请查阅 /Users/foo/Downloads/contract.docx",
    "文件位于 C:\\Users\\foo\\Desktop\\a.docx",
    "see file:///tmp/secret.txt",
])
def test_raw_json_or_absolute_path_in_body_is_rejected(body: str) -> None:
    from backend.common.reporting import ParagraphBlock
    document, registry = _document(sections_extra=[
        SectionIR(section_id="s-body", title="正文", level=1, ordinal="2", blocks=[
            ParagraphBlock(block_id="p-leak", text=body),
        ]),
    ])
    result = DocumentCompiler().compile(document, registry)
    assert result.status == "error"
    codes = {d.code for d in result.diagnostics}
    assert codes & {"BODY_RAW_JSON", "BODY_ABSOLUTE_PATH", "BODY_DEBUG_FIELD"}


def test_semantic_prose_body_passes_body_content_gate() -> None:
    from backend.common.reporting import ParagraphBlock
    document, registry = _document(sections_extra=[
        SectionIR(section_id="s-body", title="正文", level=1, ordinal="2", blocks=[
            ParagraphBlock(block_id="p-ok", text="本报告不含原始请求 JSON 或绝对路径。"),
        ]),
    ])
    result = DocumentCompiler().compile(document, registry)
    assert result.status == "success", [d.code for d in result.diagnostics]


# ── basis_entries per-citation rendering (I068-22) ────────────────────────────


def test_basis_entries_render_per_citation_not_joined() -> None:
    document, registry = _document(findings=[_two_basis_finding()])
    markdown = MarkdownRenderer().render(document, registry)

    assert "《个人信息保护法》第38条" in markdown
    assert "《数据出境安全评估办法》第4条" in markdown
    # The two labels must NOT be collapsed into a single "；"-joined wall.
    joined = "《个人信息保护法》第38条；《数据出境安全评估办法》第4条"
    assert joined not in markdown.replace("\n", "")


# ── render manifest records basis identity + cross-format equivalence ────────


def _docx_text(blob: bytes) -> str:
    from io import BytesIO

    from docx import Document

    doc = Document(BytesIO(blob))
    return "\n".join(p.text for p in doc.paragraphs)


def _pdf_text(blob: bytes) -> str:
    from io import BytesIO

    from pypdf import PdfReader

    return "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(blob)).pages)


def test_manifest_records_basis_entry_identity(tmp_path: Path) -> None:
    document, registry = _document(findings=[_two_basis_finding()])
    manifest = build_render_manifest(document, registry, tmp_path / "out", module="review", task_id="t1")

    assert [entry.model_dump(mode="json") for entry in manifest.basis_entry_identities] == [
        {"label": "《个人信息保护法》第38条", "citation_ref": "cit-1"},
        {"label": "《数据出境安全评估办法》第4条", "citation_ref": "cit-2"},
    ]

    equivalence = next(gate for gate in manifest.gates if gate.name == "equivalence")
    assert equivalence.status == "pass", equivalence.diagnostics


def test_basis_labels_reach_all_three_formats(tmp_path: Path) -> None:
    document, registry = _document(findings=[_two_basis_finding()])
    build_render_manifest(document, registry, tmp_path / "out", module="review", task_id="t1")

    md = (tmp_path / "out" / "report.md").read_text(encoding="utf-8")
    docx = _docx_text((tmp_path / "out" / "report.docx").read_bytes())
    pdf = _pdf_text((tmp_path / "out" / "report.pdf").read_bytes())

    for text, label in ((md, "markdown"), (docx, "docx"), (pdf, "pdf")):
        assert "《个人信息保护法》第38条" in text, label
        assert "《数据出境安全评估办法》第4条" in text, label


def test_deleted_basis_label_flips_equivalence_gate(tmp_path: Path) -> None:
    document, registry = _document(findings=[_two_basis_finding()])
    manifest = build_render_manifest(document, registry, tmp_path / "out", module="review", task_id="t1")

    md_path = tmp_path / "out" / "report.md"
    md_path.write_text(
        md_path.read_text(encoding="utf-8").replace("《数据出境安全评估办法》第4条", "《被删除的依据》"),
        encoding="utf-8",
    )

    gates = verify_render_manifest(manifest, tmp_path / "out")
    equivalence = next(gate for gate in gates if gate.name == "equivalence")
    assert equivalence.status == "fail"
    assert any("《数据出境安全评估办法》第4条" in diag for diag in equivalence.diagnostics)
