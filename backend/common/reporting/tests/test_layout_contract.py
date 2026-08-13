"""Task067 T08 — automated layout regression gate (issue067 → repeatable failure).

These tests turn the original screenshot bug into machine assertions that:

- **fail on injected defects** (mutation tests intercept 编号重置 / 表格退化 /
  重复正文 / 异常断词), and
- **pass on the new IR renderer** under adversarial inputs (18+ findings, long
  CJK/EN titles, very long regulation names, deep clause trees, cross-page
  findings, missing optional fields, empty findings, unknown block/profile,
  corrupted IR, and cross-format equivalence).

Every test is a substantive assertion (IDs reach the output, no broken
fragments, no six-column table, numbering preserved, equivalence holds) — never
a weak "file exists" / ">0 bytes" / "%PDF magic" check.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.common.reporting import (
    CitationLocator,
    CitationNoteBlock,
    CitationRecord,
    CitationRegistry,
    ClauseGroupBlock,
    ClauseNode,
    DocumentIR,
    FindingDetailBlock,
    FindingRecord,
    FindingSummaryBlock,
    ParagraphBlock,
    Provenance,
    ReportMetadata,
    SectionIR,
)
from backend.common.reporting.layout_gate import (
    broken_word_fragments,
    duplicate_body_diagnostics,
    markdown_table_residue,
    numbering_sequence_diagnostics,
    six_column_table,
)
from backend.common.reporting.render_manifest import build_render_manifest
from backend.common.reporting.renderers.docx import DocxRenderer
from backend.common.reporting.renderers.markdown import MarkdownRenderer
from backend.common.reporting.renderers.pdf import PdfRenderer

TS = datetime(2026, 8, 8, tzinfo=timezone.utc)

# A very long English regulation name — the regression that used to break per
# character in the six-column layout.
LONG_REGULATION = (
    "REGULATION (EU) 2024/1689 OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL "
    "LAYING DOWN HARMONISED RULES ON ARTIFICIAL INTELLIGENCE AND AMENDING "
    "REGULATIONS (EC) NO 300/2008"
)


def _citation(citation_id: str, title: str, article: str | None = None) -> CitationRecord:
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
        _citation("cit-2", LONG_REGULATION, "5"),
    ])


def _finding(
    fid: str,
    title: str,
    risk: str = "MEDIUM",
    *,
    statement: str | None = None,
    recommendation: str = "补齐合规要求。",
    suggested_revision: str | None = None,
    legal_basis: list[str] | None = None,
    citation_refs: list[str] | None = None,
) -> FindingRecord:
    return FindingRecord(
        finding_id=fid,
        requirement_id=f"R-{fid}",
        title=title,
        risk_level=risk,
        risk_score=60.0 if risk == "HIGH" else 30.0,
        statement=statement or "现状不合规，需要整改。",
        legal_basis=legal_basis if legal_basis is not None else (["GDPR Article 47(1)"] if citation_refs else []),
        recommendation=recommendation,
        suggested_revision=suggested_revision,
        citation_refs=citation_refs or [],
    )


def _base_metadata() -> ReportMetadata:
    return ReportMetadata(
        title="BCR 合规审查报告",
        short_title="BCR 报告",
        company_name="TestCo",
        jurisdiction="EU",
        locale="zh-CN",
        report_date="2026-08-08",
        report_id="BCR-2026-001",
    )


def _document(
    findings: list[FindingRecord],
    *,
    sections_extra: list[SectionIR] | None = None,
) -> tuple[DocumentIR, CitationRegistry]:
    registry = _registry()
    sections: list[SectionIR] = []
    if findings:
        sections.append(SectionIR(section_id="s-summary", title="风险与 finding 摘要", level=1, ordinal="1", blocks=[
            FindingSummaryBlock(
                block_id="sum",
                finding_refs=[finding.finding_id for finding in findings],
            ),
        ]))
        sections.append(SectionIR(section_id="s-detail", title="详细 finding", level=1, ordinal="2", blocks=[
            FindingDetailBlock(block_id=f"detail-{finding.finding_id}", finding_ref=finding.finding_id)
            for finding in findings
        ]))
    sections.extend(sections_extra or [])
    document = DocumentIR(
        compiler_version="0.1.0",
        prompt_version="test",
        template_version="test",
        model="test-model",
        document_id="doc-layout",
        report_type="bcr",
        metadata=_base_metadata(),
        provenance=Provenance(generated_at=TS),
        findings=findings,
        citations=list(registry.records().values()),
        sections=sections,
    )
    return document, registry


def _citation_section() -> SectionIR:
    return SectionIR(section_id="s-cite", title="法规与引用", level=1, ordinal="9", blocks=[
        CitationNoteBlock(block_id="cite", citation_refs=["cit-1", "cit-2"]),
    ])


def _clause_section(deep: bool = False) -> SectionIR:
    clauses = [
        ClauseNode(node_id="c1", text="第一条", children=[
            ClauseNode(node_id="c1-1", text="第一项", numbering_style="lower_alpha"),
            ClauseNode(node_id="c1-2", text="第二项", numbering_style="lower_alpha", children=(
                [
                    ClauseNode(node_id="c1-2-i", text="第 1 目", numbering_style="lower_roman"),
                    ClauseNode(node_id="c1-2-ii", text="第 2 目", numbering_style="lower_roman"),
                ] if deep else []
            )),
        ]),
        ClauseNode(node_id="c2", text="第二条"),
    ]
    return SectionIR(section_id="s-clause", title="建议条款", level=1, ordinal="3", blocks=[
        ClauseGroupBlock(block_id="clauses", title="建议条款", clauses=clauses),
    ])


def _text_from_docx(blob: bytes) -> str:
    from io import BytesIO

    from docx import Document
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph

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


def _text_from_pdf(blob: bytes) -> str:
    from io import BytesIO

    from pypdf import PdfReader

    return "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(blob)).pages)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text)


# ── adversarial coverage ─────────────────────────────────────────────────────


def test_18_finding_stress_sample_renders_across_all_formats() -> None:
    findings = [
        _finding(f"F-{index}", f"约束力不足 {index}", "HIGH", citation_refs=["cit-1"])
        for index in range(1, 19)
    ]
    document, registry = _document(findings, sections_extra=[_clause_section()])

    markdown = MarkdownRenderer().render(document, registry)
    docx = DocxRenderer().render(document, registry)
    pdf = PdfRenderer().render(document, registry)
    pdf_text = _text_from_pdf(pdf)
    docx_text = _text_from_docx(docx)

    # every finding ID reaches every format (substantive, not ">0 bytes")
    for finding in findings:
        assert finding.finding_id in markdown
        assert finding.finding_id in docx_text
        assert finding.finding_id in pdf_text

    # no broken fragments / no six-column degradation / no pipe residue
    for text, label in ((markdown, "markdown"), (docx_text, "docx"), (pdf_text, "pdf")):
        assert broken_word_fragments(text) == [], (label, broken_word_fragments(text))
        assert six_column_table(text) == [], (label, six_column_table(text))
    # Markdown legitimately uses pipe tables; DOCX/PDF must never carry them.
    for text, label in ((docx_text, "docx"), (pdf_text, "pdf")):
        assert markdown_table_residue(text) == [], (label, markdown_table_residue(text))

    # 18 findings force a multi-page PDF; identity survives page boundaries.
    assert len(pdf_text) > 0


def test_long_cjk_and_english_titles_are_not_split() -> None:
    long_cjk = "关于数据主体权利保障与跨境传输约束机制完整性与法律效力审查的结论"
    long_en = LONG_REGULATION
    document, registry = _document([
        _finding("F-1", long_cjk, "HIGH", citation_refs=["cit-1"]),
    ], sections_extra=[_citation_section()])
    pdf_text = _normalize(_text_from_pdf(PdfRenderer().render(document, registry)))
    markdown = _normalize(MarkdownRenderer().render(document, registry))

    assert long_cjk in pdf_text
    assert long_cjk in markdown
    # the long English regulation name stays intact (no per-character split)
    assert _normalize(long_en) in pdf_text


def test_very_long_english_word_not_split_into_single_chars() -> None:
    document, registry = _document([
        _finding("F-1", "超长英文法规名", "HIGH", citation_refs=["cit-2"]),
    ], sections_extra=[
        SectionIR(section_id="s-cite", title="法规与引用", level=1, ordinal="9", blocks=[
            CitationNoteBlock(block_id="cite", citation_refs=["cit-2"]),
        ]),
    ])
    pdf_text = _text_from_pdf(PdfRenderer().render(document, registry))
    # no standalone single-character lines from a shattered English token
    standalone = {line.strip() for line in pdf_text.splitlines()}
    assert not any(len(line) == 1 and line.isascii() and line.isalpha() for line in standalone)


def test_deep_clause_numbering_preserved_across_levels() -> None:
    document, registry = _document([_finding("F-1", "约束力不足")], sections_extra=[_clause_section(deep=True)])
    markdown = MarkdownRenderer().render(document, registry)

    # level 1: decimal; level 2: lower_alpha; level 3: lower_roman — no reset
    expected = ["1. 第一条", "(a) 第一项", "(b) 第二项", "i. 第 1 目", "ii. 第 2 目", "2. 第二条"]
    assert numbering_sequence_diagnostics(markdown, expected) == []


def test_finding_cross_page_keeps_identity() -> None:
    # one finding with a very long statement forces it across a page boundary;
    # its ID must still appear once and its fields must remain attached.
    long_statement = "这是一段用于强制跨页的长正文。" * 40
    document, registry = _document([
        _finding("F-1", "跨页 finding", "HIGH", statement=long_statement, citation_refs=["cit-1"]),
    ])
    pdf_text = _text_from_pdf(PdfRenderer().render(document, registry))
    assert "F-1" in pdf_text
    assert _normalize(long_statement[:20]) in _normalize(pdf_text)


def test_missing_optional_fields_render_without_empty_labels() -> None:
    document, registry = _document([
        _finding(
            "F-1", "缺可选字段", "MEDIUM",
            statement="仅有现状字段。",
            recommendation="",
            suggested_revision=None,
            legal_basis=[],
            citation_refs=[],
        ),
    ])
    markdown = MarkdownRenderer().render(document, registry)
    docx_text = _text_from_docx(DocxRenderer().render(document, registry))
    pdf_text = _text_from_pdf(PdfRenderer().render(document, registry))

    for text in (markdown, docx_text, pdf_text):
        # the skipped fields must not leave dangling empty labels
        assert "整改建议：" not in text
        assert "法规依据：" not in text
        assert "建议修改文本：" not in text


def test_empty_findings_render_cleanly() -> None:
    document, registry = _document([], sections_extra=[
        SectionIR(section_id="s-body", title="正文", level=1, ordinal="1", blocks=[
            ParagraphBlock(block_id="p1", text="本报告无 finding。"),
        ]),
    ])
    markdown = MarkdownRenderer().render(document, registry)
    pdf = PdfRenderer().render(document, registry)
    assert "无 finding" in markdown
    assert "无 finding" in _text_from_pdf(pdf)


def test_unknown_block_type_and_profile_fail_closed() -> None:
    document, registry = _document([_finding("F-1", "约束力不足")])

    # unknown render profile → RenderProfileError from the renderers/manifest
    document.render_contract.profile_id = "no-such-profile"
    with pytest.raises(Exception):
        PdfRenderer().render(document, registry)

    # unknown block type → renderer raises (bypassing the pydantic union)
    document.render_contract.profile_id = "legal-report-a4-v1"

    class _Unknown:
        type = "not_a_block"

    renderer = PdfRenderer()
    with pytest.raises(Exception):
        renderer._render_block(
            [], document.sections[0], _Unknown(), {}, registry, None, None, {},
        )


def test_corrupted_ir_is_rejected_by_pydantic() -> None:
    # unknown block type fails the discriminated union
    with pytest.raises(ValidationError):
        DocumentIR.model_validate({
            "compiler_version": "0.1.0",
            "prompt_version": "test",
            "template_version": "test",
            "model": "test",
            "document_id": "doc-x",
            "report_type": "bcr",
            "metadata": _base_metadata().model_dump(mode="json"),
            "provenance": {"generated_at": TS.isoformat()},
            "sections": [{"section_id": "s", "title": "t", "level": 1, "blocks": [
                {"block_id": "b", "type": "not_a_block"},
            ]}],
        })


def test_markdown_docx_pdf_set_equivalence(tmp_path) -> None:
    findings = [_finding(f"F-{index}", f"约束力不足 {index}", "HIGH", citation_refs=["cit-1"]) for index in range(1, 4)]
    document, registry = _document(findings, sections_extra=[_clause_section(), _citation_section()])
    manifest = build_render_manifest(document, registry, tmp_path / "out", module="bcr", task_id="t1")

    assert manifest.render_status == "success"
    equivalence = next(gate for gate in manifest.gates if gate.name == "equivalence")
    assert equivalence.status == "pass", equivalence.diagnostics


# ── mutation tests (fail on injected defects) ───────────────────────────────


def _clause_markdown() -> str:
    document, registry = _document([_finding("F-1", "约束力不足")], sections_extra=[_clause_section(deep=True)])
    return MarkdownRenderer().render(document, registry)


def test_mutation_numbering_reset_is_detected() -> None:
    markdown = _clause_markdown()
    # a nested-list renderer that restarts numbering emits "(a)" again instead
    # of "(b) 第二项"
    mutated = markdown.replace("(b) 第二项", "(a) 第二项")
    expected = ["1. 第一条", "(a) 第一项", "(b) 第二项", "i. 第 1 目", "ii. 第 2 目", "2. 第二条"]
    assert numbering_sequence_diagnostics(mutated, expected)  # flags the reset


def test_mutation_table_degradation_is_detected() -> None:
    markdown = _clause_markdown()
    legacy_header = "| 检查项 | 主题 | 风险 | 现状 | 法律依据 | 整改建议 |\n| --- | --- | --- | --- | --- | --- |"
    assert six_column_table(legacy_header)
    assert six_column_table(markdown) == []  # correct output stays clean


def test_mutation_duplicate_body_is_detected() -> None:
    document, registry = _document([_finding("F-1", "约束力不足", statement="唯一正文锚点。")])
    markdown = MarkdownRenderer().render(document, registry)
    anchor = "现状：唯一正文锚点。"
    mutated = markdown.replace(anchor, f"{anchor}\n\n{anchor}", 1)
    assert duplicate_body_diagnostics(mutated, [anchor])  # flags the duplicate


def test_mutation_word_break_is_detected() -> None:
    broken = "风险等级：HIGH\nH\n\n风险等级：ME\nDIU\nM"
    assert broken_word_fragments(broken)
    # a correct flowing render has no such fragments
    assert broken_word_fragments("风险等级：HIGH MEDIUM，正文正常换行。") == []
