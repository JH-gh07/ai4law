"""Review → Markdown integration (T04).

The canonical v4 ``DocumentIR`` produced by the review adapter must render to
Markdown through the shared renderer without six-column tables, raw JSON,
absolute paths, or the legacy duplicate "九" chapter. Finding/citation/section
sets stay equal to the IR, ``basis_entries`` render one entry per line (no
``；``-joined label wall, I068-22), and a fixed-time input is byte-stable.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from backend.common.citation.registry import CitationRegistry
from backend.common.reporting import DocumentCompiler
from backend.common.reporting.renderers.markdown import MarkdownRenderer
from backend.domains.cn.document_review.schema_first import build_document_review_ir
from backend.schemas.review import (
    AggregatedReview,
    ClauseType,
    ReviewIssue,
    ReviewSeverity,
    StructuredCitation,
)

TS = datetime(2026, 8, 8, tzinfo=timezone.utc)


def _citation(article: str, snippet: str) -> StructuredCitation:
    return StructuredCitation(
        source_id="CN-LAW-003",
        source_title="个人信息保护法",
        article=article,
        snippet=snippet,
        source_type="statute",
    )


def _issue(index: int, severity: ReviewSeverity, citations: list[StructuredCitation]) -> ReviewIssue:
    return ReviewIssue(
        issue_id=f"DR-{index:03d}",
        clause_id=f"cl-{index:03d}",
        file_id="file-01",
        severity=severity,
        clause_type=ClauseType.CROSS_BORDER_TRANSFER,
        title=f"合规问题 {index}",
        problem_type="MISSING_REQUIREMENT",
        original_excerpt="（未找到相关条款）",
        risk_analysis=f"第{index}个问题的风险分析。",
        citation_sources=[f"《个人信息保护法》{c.article}" for c in citations],
        structured_citations=citations,
        recommendation="补充合规条款。",
    )


def _review() -> AggregatedReview:
    multi = [
        _citation("第17条", "个人信息可携带权条款摘录。"),
        _citation("第38条", "跨境传输需进行安全评估。"),
        _citation("第13条", "处理个人信息应当取得个人同意。"),
    ]
    return AggregatedReview(
        overall_rating="高风险",
        overall_risk_score=81.0,
        summary="共识别多个问题。",
        issues=[_issue(1, ReviewSeverity.HIGH, multi)],
        issue_counts={"HIGH": 1, "MEDIUM": 0, "LOW": 0},
        priority_actions=["补充数据出境告知条款"],
        document_profile={
            "document_type": "隐私政策",
            "document_title": "隐私协议_测试.docx",
            "total_clauses": "48",
            "total_issues_found": "1",
            "total_missing_items": "0",
        },
        clauses_summary={"CROSS_BORDER_TRANSFER": 1},
        review_metadata={"review_mode": "llm"},
    )


def _build():
    review = _review()
    doc, registry = build_document_review_ir(
        task_id="phase4-md",
        document_title="隐私协议_测试.docx",
        review=review,
        citation_registry=CitationRegistry(),
        model="deepseek-v3",
        generated_at=TS,
    )
    result = DocumentCompiler().compile(doc, registry)
    assert result.status == "success", [d.code for d in result.diagnostics]
    markdown = MarkdownRenderer().render(doc, registry)
    return doc, registry, markdown


def _tables(markdown: str) -> list[list[list[str]]]:
    tables: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in markdown.splitlines():
        if line.lstrip().startswith("|") and line.rstrip().endswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(c == "---" for c in cells):
                continue
            current.append(cells)
        else:
            if current:
                tables.append(current)
                current = []
    if current:
        tables.append(current)
    return tables


def test_markdown_renders_without_forbidden_artifacts() -> None:
    doc, _, markdown = _build()

    # No six-column finding table (I068-01/I068-06 residual).
    for table in _tables(markdown):
        assert len(table[0]) < 6, f"发现六列长表: {table[0]}"

    # No raw JSON dump or absolute/workspace paths in the body.
    assert '"issue_id"' not in markdown
    assert '"risk_analysis"' not in markdown
    assert "{{" not in markdown and "}}" not in markdown
    for forbidden in ("/Users/", "/tmp/", "outputs/", "storage/"):
        assert forbidden not in markdown, f"正文泄漏内部路径: {forbidden}"

    # I068-05: exactly one top-level "9" chapter, no duplicate 九.
    assert "9 法规依据汇总" in markdown
    assert markdown.count("# 9 ") == 1
    assert "九 法规依据汇总" not in markdown


def test_markdown_sets_equal_ir() -> None:
    doc, _, markdown = _build()

    section_ids = [s.section_id for s in doc.sections]
    section_titles = [s.title for s in doc.sections]
    for title in section_titles:
        assert title in markdown
    assert len(section_ids) == len(set(section_ids)) == 10

    for finding in doc.findings:
        assert finding.finding_id in markdown
        assert finding.title in markdown

    for citation in doc.citations:
        assert citation.title in markdown


def test_basis_entries_render_one_per_line_not_joined_wall() -> None:
    doc, _, markdown = _build()
    finding = doc.findings[0]
    assert len(finding.basis_entries) == 3

    # The three citations must each appear on their own line, not joined by "；".
    legal_basis_block = markdown.split("法规依据：", 1)[1]
    # cut at the next field label
    legal_basis_block = legal_basis_block.split("\n整改建议：", 1)[0]
    for basis in finding.basis_entries:
        assert basis.label in legal_basis_block
        assert basis.rationale in legal_basis_block
    assert "；" not in legal_basis_block, f"法规依据被压成标签墙:\n{legal_basis_block}"


def test_markdown_is_byte_stable_for_fixed_time() -> None:
    def _render() -> str:
        review = _review()
        doc, registry = build_document_review_ir(
            task_id="phase4-md",
            document_title="隐私协议_测试.docx",
            review=review,
            citation_registry=CitationRegistry(),
            model="deepseek-v3",
            generated_at=TS,
        )
        return MarkdownRenderer().render(doc, registry)

    a = _render()
    b = _render()
    assert a == b
    assert hashlib.sha256(a.encode("utf-8")).hexdigest() == hashlib.sha256(b.encode("utf-8")).hexdigest()
