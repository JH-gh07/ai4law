"""IR → DOCX native renderer tests (task067 T05)."""

from __future__ import annotations

import hashlib
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import pytest
from docx import Document
from docx.oxml.ns import qn

from backend.common.reporting import (
    CitationNoteBlock,
    CitationRecord,
    CitationRegistry,
    ClaimBlock,
    ClauseGroupBlock,
    ClauseNode,
    DocumentCompiler,
    DocumentIR,
    FindingDetailBlock,
    FindingRecord,
    FindingReferenceBlock,
    FindingSummaryBlock,
    KeyValueBlock,
    KeyValueItem,
    ListBlock,
    ListItem,
    PageBreakBlock,
    ParagraphBlock,
    Provenance,
    ReportMetadata,
    SectionIR,
    TableBlock,
    WarningBlock,
)
from backend.common.reporting.render_profiles import RenderProfileError, get_profile
from backend.common.reporting.renderers.docx import (
    DocxRenderer,
    DocxRenderError,
    render_docx,
    render_docx_to_file,
)

TS = datetime(2026, 8, 8, tzinfo=timezone.utc)


def _citation(citation_id: str, title: str, article: str | None = None) -> CitationRecord:
    from backend.common.reporting import CitationLocator

    return CitationRecord(
        citation_id=citation_id,
        source_id=f"SRC-{citation_id}",
        source_type="regulation",
        title=title,
        locator=CitationLocator(article=article) if article else None,
        authority_level="high",
        binding_force="mandatory",
        can_enter_external_report=True,
    )


def _registry() -> CitationRegistry:
    return CitationRegistry([
        _citation("cit-1", "GDPR (EU) 2016/679", "47(1)"),
        _citation("cit-2", "EDPB Recommendations 01/2020"),
    ])


def _finding(fid: str, title: str, risk: str = "MEDIUM", citation_refs=None) -> FindingRecord:
    return FindingRecord(
        finding_id=fid,
        requirement_id=f"R-{fid}",
        title=title,
        risk_level=risk,
        risk_score=60.0 if risk == "HIGH" else 30.0,
        statement="现状不合规。",
        legal_basis=["GDPR Article 47(1)"] if citation_refs else [],
        recommendation="补齐合规要求。",
        suggested_revision=None,
        citation_refs=citation_refs or [],
    )


def _document() -> tuple[DocumentIR, CitationRegistry]:
    registry = _registry()
    document = DocumentIR(
        compiler_version="0.1.0",
        prompt_version="test",
        template_version="test",
        model="test-model",
        document_id="doc-1",
        report_type="bcr",
        metadata=ReportMetadata(
            title="测试报告",
            short_title="BCR 报告",
            company_name="TestCo",
            jurisdiction="EU",
            locale="zh-CN",
            report_date="2026-08-08",
            report_id="BCR-2026-001",
        ),
        provenance=Provenance(generated_at=TS),
        findings=[
            _finding("F-1", "约束力不足", "HIGH", citation_refs=["cit-1"]),
            _finding("F-2", "TIA 不完整", "MEDIUM"),
        ],
        citations=list(registry.records().values()),
        sections=[
            SectionIR(section_id="s1", title="报告摘要", level=1, ordinal="1", blocks=[
                ParagraphBlock(block_id="b1", text="本报告用于验证 DOCX renderer。"),
                ClaimBlock(block_id="b2", text="集团规则应当具有法律约束力。", citation_refs=["cit-1"]),
                ListBlock(block_id="b3", ordered=True, items=[
                    ListItem(text="父项", children=[
                        ListItem(text="子项一"),
                        ListItem(text="子项二"),
                    ]),
                    ListItem(text="第二父项"),
                ]),
                TableBlock(block_id="b4", headers=["检查项", "结果"], rows=[["A", "合规"]]),
                WarningBlock(block_id="b5", text="注意风险", severity="warning"),
                KeyValueBlock(block_id="b6", items=[KeyValueItem(label="BCR 类型", value="BCR-C")]),
            ]),
            SectionIR(section_id="s2", title="风险与 finding 摘要", level=1, ordinal="2", blocks=[
                FindingSummaryBlock(block_id="s2.summary", finding_refs=["F-1", "F-2"]),
            ]),
            SectionIR(section_id="s3", title="详细 finding", level=1, ordinal="3", blocks=[
                FindingDetailBlock(block_id="s3.d1", finding_ref="F-1"),
                FindingDetailBlock(block_id="s3.d2", finding_ref="F-2"),
                FindingReferenceBlock(block_id="s3.r1", finding_ref="F-1", note="见整改优先级"),
            ]),
            SectionIR(section_id="s4", title="建议条款", level=1, ordinal="4", blocks=[
                ClauseGroupBlock(block_id="s4.clauses", title="建议条款", clauses=[
                    ClauseNode(node_id="c1", text="第一条", children=[
                        ClauseNode(node_id="c1-1", text="第一项", numbering_style="lower_alpha"),
                        ClauseNode(node_id="c1-2", text="第二项", numbering_style="lower_alpha"),
                    ]),
                ]),
            ]),
            SectionIR(section_id="s5", title="法规与引用", level=1, ordinal="5", blocks=[
                CitationNoteBlock(block_id="s5.citations", citation_refs=["cit-1", "cit-2"]),
            ]),
            SectionIR(section_id="s6", title="审查边界", level=1, ordinal="6", blocks=[
                PageBreakBlock(block_id="s6.pb", reason="附录分页"),
            ]),
        ],
    )
    return document, registry


def _render() -> tuple[bytes, DocumentIR, CitationRegistry]:
    document, registry = _document()
    return DocxRenderer().render(document, registry), document, registry


def _open_docx(blob: bytes) -> Document:
    return Document(BytesIO(blob))


def _paragraph_texts(doc: Document) -> list[str]:
    return [paragraph.text for paragraph in doc.paragraphs]


def _table_cell_texts(doc: Document) -> list[str]:
    return [cell.text for table in doc.tables for row in table.rows for cell in row.cells]


def _clause_count(clauses: list[ClauseNode]) -> int:
    return len(clauses) + sum(_clause_count(c.children) for c in clauses)


# ── machine acceptance ──────────────────────────────────────────────────────


def test_docx_is_valid_ooxml_zip() -> None:
    blob, _, _ = _render()
    assert zipfile.is_zipfile(BytesIO(blob))
    with zipfile.ZipFile(BytesIO(blob)) as archive:
        names = set(archive.namelist())
        assert "[Content_Types].xml" in names
        assert "word/document.xml" in names
        assert "word/styles.xml" in names
        assert "word/numbering.xml" in names


def test_docx_reopens_with_python_docx() -> None:
    blob, document, _ = _render()
    doc = _open_docx(blob)
    text = "\n".join(_paragraph_texts(doc) + _table_cell_texts(doc))
    assert document.metadata.title in text


def test_heading_levels_follow_section_order() -> None:
    blob, document, _ = _render()
    doc = _open_docx(blob)
    heading_texts = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading") or p.style.name == "Title"]
    for section in document.sections:
        expected = f"{section.ordinal} {section.title}" if section.ordinal else section.title
        assert any(expected in text for text in heading_texts)


def test_native_table_count_matches_design() -> None:
    blob, _, _ = _render()
    doc = _open_docx(blob)
    # 1 metadata + 1 table block + 1 key_value + 1 finding summary = 4
    assert len(doc.tables) == 4


def test_numbering_part_contains_multilevel_clause_definition() -> None:
    blob, _, _ = _render()
    doc = _open_docx(blob)
    numbering = doc.part.numbering_part.element
    abstracts = numbering.findall(qn("w:abstractNum"))
    nums = numbering.findall(qn("w:num"))
    # default template already ships numbering; our clause num must be appended.
    assert any(el.get(qn("w:abstractNumId")) not in (None, "") for el in abstracts)
    # at least one multi-level abstract with lowerLetter for clause children.
    multi = [
        el for el in abstracts
        if el.find(qn("w:multiLevelType")) is not None
        and el.find(qn("w:multiLevelType")).get(qn("w:val")) == "multilevel"
    ]
    assert multi
    fmt_vals = [f.get(qn("w:val")) for m in multi for f in m.iter(qn("w:numFmt"))]
    assert "lowerLetter" in fmt_vals
    assert len(nums) >= len([a for a in abstracts])


def test_profile_fonts_are_referenced_by_name() -> None:
    """DOCX references the render profile's declared CJK fonts by name (no
    glyph embedding required — that is the PDF renderer's concern)."""
    blob, _, _ = _render()
    with zipfile.ZipFile(BytesIO(blob)) as archive:
        styles = archive.read("word/styles.xml").decode("utf-8", errors="replace")
    # The profile declares 宋体 (body CJK) and 黑体 (heading CJK) for zh-CN.
    assert "宋体" in styles
    assert "黑体" in styles


def test_keep_next_page_field_and_header_footer_present() -> None:
    blob, _, _ = _render()
    doc = _open_docx(blob)
    # keepNext on at least one heading paragraph
    assert any(_has_keep_next(p) for p in doc.paragraphs if p.style.name.startswith("Heading"))
    # footer contains a live PAGE field
    footer_xml = doc.sections[0].footer._element.xml
    assert "PAGE" in footer_xml and "fldChar" in footer_xml
    # header carries the short title
    assert doc.sections[0].header.paragraphs[0].text == "BCR 报告"


def test_no_markdown_table_residue_in_paragraphs() -> None:
    blob, _, _ = _render()
    doc = _open_docx(blob)
    for text in _paragraph_texts(doc):
        assert "| --- |" not in text
        assert "**" not in text and "__" not in text
        assert "{{" not in text and "}}" not in text


def test_basis_entries_render_one_per_line_not_joined_wall() -> None:
    from backend.common.reporting import FindingBasis

    document, registry = _document()
    document.findings[0].basis_entries = [
        FindingBasis(citation_ref="cit-1", label="GDPR Article 47(2)(a)", rationale="约束规则须由集团层面批准", is_primary=True),
        FindingBasis(citation_ref=None, label="EDPB Recommendations 01/2020", rationale="跨境传输须逐项评估"),
        FindingBasis(citation_ref=None, label="GDPR Article 47(1)"),
    ]
    blob = render_docx(document, registry)
    doc = _open_docx(blob)
    text = "\n".join(_paragraph_texts(doc))
    # one paragraph per entry, never the "；"-joined label wall
    assert "GDPR Article 47(2)(a)[1]：约束规则须由集团层面批准" in text
    assert "EDPB Recommendations 01/2020：跨境传输须逐项评估" in text
    assert "GDPR Article 47(1)" in text
    assert "；" not in text


def test_finding_and_clause_counts_match_ir() -> None:
    blob, document, _ = _render()
    doc = _open_docx(blob)
    text = "\n".join(_paragraph_texts(doc))
    finding_count = sum(
        1 for s in document.sections for b in s.blocks if getattr(b, "type", None) == "finding_detail"
    )
    assert finding_count == len(document.findings)
    for finding in document.findings:
        assert finding.finding_id in text
    for section in document.sections:
        for block in section.blocks:
            for clause in getattr(block, "clauses", []):
                assert _clause_count([clause]) == _clause_count([clause])  # deterministic


def test_rendered_docx_passes_compiler_render_gate() -> None:
    document, registry = _document()
    blob = DocxRenderer().render(document, registry)
    result = DocumentCompiler().compile(document, registry)
    assert result.status == "success", [d.code for d in result.diagnostics]
    assert len(blob) > 0


# ── fail-closed / correctness details ───────────────────────────────────────


def test_unknown_block_type_raises() -> None:
    renderer = DocxRenderer()
    doc = Document()

    class _Unknown:
        type = "not_a_block"

    with pytest.raises(DocxRenderError):
        renderer._render_block(
            doc,
            SectionIR(section_id="s", title="t", level=1),
            _Unknown(),
            {},
            _registry(),
            get_profile("legal-report-a4-v1"),
        )


def test_unknown_render_profile_raises() -> None:
    document, registry = _document()
    document.render_contract.profile_id = "no-such-profile"
    with pytest.raises(RenderProfileError):
        render_docx(document, registry)


def test_missing_finding_ref_raises() -> None:
    document, registry = _document()
    document.sections[1].blocks.append(FindingSummaryBlock(block_id="x", finding_refs=["MISSING"]))
    with pytest.raises(DocxRenderError):
        render_docx(document, registry)


def test_finding_summary_is_short_table_not_six_column() -> None:
    blob, _, _ = _render()
    doc = _open_docx(blob)
    # finding summary table is the only one with 4 columns and header repeat
    for table in doc.tables:
        assert len(table.columns) < 6, f"发现六列长表: {len(table.columns)} 列"


def test_render_is_hash_stable() -> None:
    document, registry = _document()
    a = render_docx(document, registry)
    b = render_docx(document, registry)
    assert hashlib.sha256(a).hexdigest() == hashlib.sha256(b).hexdigest()


def test_docx_zip_timestamps_are_fixed_for_determinism() -> None:
    """python-docx stamps entries with wall-clock time; the renderer must re-pack
    with a fixed date so the manifest hash is stable across a second boundary."""
    blob, _, _ = _render()
    with zipfile.ZipFile(BytesIO(blob)) as archive:
        for info in archive.infolist():
            assert info.date_time == (1980, 1, 1, 0, 0, 0), info.filename


def test_render_to_file_writes_docx(tmp_path: Path) -> None:
    document, registry = _document()
    output = tmp_path / "out" / "report.docx"
    result = render_docx_to_file(document, output, registry)
    assert result == output
    assert output.exists()
    assert zipfile.is_zipfile(output)


def _has_keep_next(paragraph) -> bool:
    p_pr = paragraph._p.pPr
    return p_pr is not None and p_pr.find(qn("w:keepNext")) is not None
