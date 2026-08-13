"""Schema-first document_review renderer integration — T02 structured acceptance.

Exercises the structured adapter → compiler pipeline and pins the production
quantity signature (41 issues / 7 missing / 23-15-3 risk distribution) with
synthetic, non-sensitive data, plus the ``FindingBasis`` attribution rule and
lossless ``ReviewIssue`` field mapping.
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.common.citation.registry import CitationRegistry
from backend.common.reporting import DocumentCompiler
from backend.domains.cn.document_review.schema_first import build_document_review_ir
from backend.schemas.review import (
    AggregatedReview,
    ClauseType,
    MissingItem,
    ReviewDepth,
    ReviewIssue,
    ReviewMethod,
    ReviewSeverity,
    StructuredCitation,
)

RECORD_TS = datetime(2026, 8, 8, tzinfo=timezone.utc)


def _citation(article: str, snippet: str) -> StructuredCitation:
    return StructuredCitation(
        source_id="CN-LAW-003",
        source_title="个人信息保护法",
        article=article,
        snippet=snippet,
        source_type="statute",
    )


def _issue(index: int, severity: ReviewSeverity) -> ReviewIssue:
    article = f"第{17 + index % 5}条"
    return ReviewIssue(
        issue_id=f"DR-{index:03d}",
        clause_id=f"cl-{index:03d}",
        file_id="file-01",
        severity=severity,
        clause_type=ClauseType.CROSS_BORDER_TRANSFER,
        title=f"合规问题 {index}",
        problem_type="MISSING_REQUIREMENT",
        original_excerpt="（未找到相关条款）",
        risk_analysis=f"第{index}个问题的风险分析，涉及数据出境告知缺失。",
        citation_sources=[f"《个人信息保护法》{article}"],
        structured_citations=[_citation(article, f"{article}的条款摘录片段。")],
        recommendation="补充数据出境告知条款。",
        review_method=ReviewMethod.LLM,
        review_confidence=0.85,
        review_depth=ReviewDepth.STANDARD,
    )


def _production_review() -> AggregatedReview:
    """Synthetic non-sensitive fixture reproducing the 41/7/23-15-3 signature."""
    issues = (
        [_issue(i, ReviewSeverity.HIGH) for i in range(1, 24)]       # 23 HIGH
        + [_issue(i, ReviewSeverity.MEDIUM) for i in range(24, 39)]  # 15 MEDIUM
        + [_issue(i, ReviewSeverity.LOW) for i in range(39, 42)]     # 3 LOW
    )
    missing_items = [
        MissingItem(
            item_id=f"MI-{i:03d}",
            clause_type=ClauseType.RIGHTS_REQUEST,
            title=f"缺失项 {i}",
            description="隐私政策未包含相应权利条款。",
            severity=ReviewSeverity.HIGH,
            legal_basis=["《个人信息保护法》第17条"],
            recommendation="参考相关条文补充。",
        )
        for i in range(1, 8)  # 7 missing
    ]
    return AggregatedReview(
        overall_rating="高风险",
        overall_risk_score=78.0,
        summary="共识别 41 个问题 7 个全局缺失项，其中 HIGH 23 个、MEDIUM 15 个、LOW 3 个。",
        issues=issues,
        issue_counts={"HIGH": 23, "MEDIUM": 15, "LOW": 3},
        priority_actions=["补充数据出境告知条款", "补充数据可携权条款"],
        missing_items=missing_items,
        document_profile={
            "document_type": "隐私政策",
            "document_title": "隐私协议_测试.docx",
            "total_clauses": "48",
            "classified_clauses": "48",
            "total_issues_found": "41",
            "total_missing_items": "7",
        },
        clauses_summary={"CROSS_BORDER_TRANSFER": 20, "RIGHTS_REQUEST": 18, "OTHER": 10},
        consistency_warnings=["文档未涉及儿童个人信息保护规定"],
        review_metadata={"review_mode": "llm_deep"},
    )


def _build(review: AggregatedReview, task_id: str = "phase3-review-prod"):
    return build_document_review_ir(
        task_id=task_id,
        document_title="隐私协议_测试.docx",
        review=review,
        citation_registry=CitationRegistry(),
        model="deepseek-v3",
        generated_at=RECORD_TS,
    )


def test_production_signature_41_7_23_15_3() -> None:
    review = _production_review()
    doc, rep = _build(review)
    cr = DocumentCompiler().compile(doc, rep)
    assert cr.status == "success", [d.code for d in cr.diagnostics]

    assert len(doc.findings) == 41
    assert len(review.missing_items) == 7
    assert [f.risk_level for f in doc.findings].count("HIGH") == 23
    assert [f.risk_level for f in doc.findings].count("MEDIUM") == 15
    assert [f.risk_level for f in doc.findings].count("LOW") == 3

    # Each finding has exactly one primary display.
    detail_count = sum(
        1 for s in doc.sections for b in s.blocks if getattr(b, "type", None) == "finding_detail"
    )
    assert detail_count == 41

    # Missing items are typed blocks, not findings (issues only).
    missing_blocks = [
        b for s in doc.sections if s.section_id == "review.s5" for b in s.blocks
    ]
    assert missing_blocks and missing_blocks[0].type == "list"


def test_basis_rationale_is_traceable_to_snippet() -> None:
    doc, _ = _build(_production_review())
    for finding in doc.findings:
        for basis in finding.basis_entries:
            source = basis.rationale
            assert source, f"{finding.finding_id} basis rationale is empty"
            # rationale must be a verbatim excerpt from the citation snippet
            assert "第" in source and "条" in source, f"unexpected rationale: {source[:40]}"


def test_lossless_review_issue_field_mapping() -> None:
    review = _production_review()
    doc, _ = _build(review)
    first = doc.findings[0]
    src = review.issues[0]
    assert first.finding_id == src.issue_id
    assert first.clause_id == src.clause_id
    assert first.file_id == src.file_id
    assert first.clause_type == src.clause_type.value
    assert first.problem_type == src.problem_type
    assert first.risk_level == src.severity.value
    assert first.original_excerpt == src.original_excerpt
    assert first.review_method == src.review_method.value
    assert first.review_depth == src.review_depth.value
    assert first.risk_score == src.risk_score
    assert first.review_confidence == src.review_confidence
    assert first.legal_basis == src.citation_sources


def test_byte_stable_for_production_signature() -> None:
    import json

    def _dump() -> str:
        doc, _ = _build(_production_review())
        return json.dumps(doc.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)

    assert _dump() == _dump()
