"""Markdown renderer tests (task067 T03)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import pytest

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
from backend.common.reporting.renderers.markdown import MarkdownRenderer, RenderError, render_markdown

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
        metadata=ReportMetadata(title="测试报告", company_name="TestCo", jurisdiction="EU"),
        provenance=Provenance(generated_at=TS),
        findings=[
            _finding("F-1", "约束力不足", "HIGH", citation_refs=["cit-1"]),
            _finding("F-2", "TIA 不完整", "MEDIUM"),
        ],
        citations=list(registry.records().values()),
        sections=[
            SectionIR(section_id="s1", title="报告摘要", level=1, ordinal="1", blocks=[
                ParagraphBlock(block_id="b1", text="本报告用于验证 Markdown renderer。"),
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


def _render() -> tuple[str, DocumentIR, CitationRegistry]:
    document, registry = _document()
    return MarkdownRenderer().render(document, registry), document, registry


# ── acceptance: sets match IR ──────────────────────────────────────────────


def test_section_finding_clause_citation_sets_match_ir() -> None:
    markdown, document, _ = _render()

    for section in document.sections:
        assert section.title in markdown

    for finding in document.findings:
        assert finding.finding_id in markdown

    for section in document.sections:
        for block in section.blocks:
            for clause in getattr(block, "clauses", []):
                assert clause.text in markdown

    # citation appendix carries both registered citations, first-use numbered.
    assert "GDPR (EU) 2016/679" in markdown
    assert "EDPB Recommendations 01/2020" in markdown
    assert "1. GDPR (EU) 2016/679 — Article 47(1)" in markdown
    assert "2. EDPB Recommendations 01/2020" in markdown


def test_no_six_column_finding_table() -> None:
    markdown, _, _ = _render()
    assert "| 检查项 | 主题 | 风险 |" not in markdown
    for table in _tables(markdown):
        assert len(table[0]) < 6, f"发现六列长表: {table[0]}"


def test_nested_list_indentation_is_structural() -> None:
    markdown, _, _ = _render()
    lines = markdown.splitlines()
    # ordered list inherits markers for children; nesting is expressed by a
    # 4-space indent (CommonMark-safe nested list continuation).
    parent_idx = lines.index("1. 父项")
    assert lines[parent_idx + 1] == "    1. 子项一"
    assert lines[parent_idx + 2] == "    2. 子项二"
    assert lines[parent_idx + 3] == "2. 第二父项"


def test_markdown_lint_passes() -> None:
    markdown, _, _ = _render()
    assert _lint(markdown) == []


def test_render_is_hash_stable() -> None:
    document, registry = _document()
    a = render_markdown(document, registry)
    b = render_markdown(document, registry)
    assert a == b
    assert hashlib.sha256(a.encode("utf-8")).hexdigest() == hashlib.sha256(b.encode("utf-8")).hexdigest()


# ── compiler render gate integration ───────────────────────────────────────


def test_rendered_output_passes_compiler_render_gate() -> None:
    document, registry = _document()
    markdown = MarkdownRenderer().render(document, registry)
    result = DocumentCompiler().compile(document, registry, rendered_text=markdown)
    assert result.status == "success", [d.code for d in result.diagnostics]


# ── fail-closed / correctness details ──────────────────────────────────────


def test_claim_emits_footnote_markers_without_template_residue() -> None:
    markdown, _, _ = _render()
    assert "具有法律约束力。[1]" in markdown
    assert "{{" not in markdown and "}}" not in markdown


def test_finding_detail_renders_field_blocks_not_flat_paragraph() -> None:
    markdown, _, _ = _render()
    assert "## F-1 约束力不足" in markdown
    assert "现状：现状不合规。" in markdown
    assert "法规依据：GDPR Article 47(1)[1]" in markdown
    assert "整改建议：补齐合规要求。" in markdown


def test_unknown_block_type_raises() -> None:
    renderer = MarkdownRenderer()

    class _Unknown:
        type = "not_a_block"

    with pytest.raises(RenderError):
        renderer._render_block(
            SectionIR(section_id="s", title="t", level=1),
            _Unknown(),
            {},
            _registry(),
            [],
        )


def test_missing_finding_ref_raises() -> None:
    document, registry = _document()
    document.sections[1].blocks.append(FindingSummaryBlock(block_id="x", finding_refs=["MISSING"]))
    with pytest.raises(RenderError):
        render_markdown(document, registry)


# ── lightweight helpers (no external CommonMark dependency) ────────────────


def _tables(markdown: str) -> list[list[list[str]]]:
    """Extract pipe tables as lists of row cell lists."""
    tables: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in markdown.splitlines():
        if line.lstrip().startswith("|") and line.rstrip().endswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(c == "---" for c in cells):
                continue  # separator
            current.append(cells)
        else:
            if current:
                tables.append(current)
                current = []
    if current:
        tables.append(current)
    return tables


def _lint(markdown: str) -> list[str]:
    issues: list[str] = []
    for index, line in enumerate(markdown.splitlines(), start=1):
        if "{{" in line or "}}" in line:
            issues.append(f"{index}: template residue")
        if "**" in line or "__" in line:
            issues.append(f"{index}: emphasis marker")
        if line != line.rstrip():
            issues.append(f"{index}: trailing whitespace")
        if "\t" in line:
            issues.append(f"{index}: tab character")
        if line.startswith("#" * 7):
            issues.append(f"{index}: heading level > 6")
    return issues
