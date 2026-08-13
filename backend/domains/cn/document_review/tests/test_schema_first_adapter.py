"""Schema-first document_review adapter tests — T02 structured IR contract.

The adapter must build ``FindingRecord[]`` from ``AggregatedReview.issues``
(never from the legacy ``build_sections`` paragraph shim), keep finding order,
give each finding exactly one ``FINDING_DETAIL``, and stay byte-stable for a
fixed time input.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from backend.common.citation.registry import CitationRegistry
from backend.common.reporting import DocumentCompiler
from backend.domains.cn.document_review.schema_first import build_document_review_ir
from backend.schemas.review import (
    AggregatedReview,
    ClauseType,
    ReviewDepth,
    ReviewIssue,
    ReviewMethod,
    ReviewSeverity,
    StructuredCitation,
)

GOLDEN = Path(__file__).parent / "schema_first_fixtures" / "review_document_ir.golden.json"
TS = datetime(2026, 8, 8, tzinfo=timezone.utc)


def _empty_review() -> AggregatedReview:
    return AggregatedReview(
        overall_rating="HIGH",
        overall_risk_score=72.0,
        summary="合同存在数据出境条款缺失等高风险问题，需整改后方可使用。",
        issues=[],
        issue_counts={"HIGH": 2, "MEDIUM": 1, "LOW": 0},
        priority_actions=["补充数据出境条款", "明确数据处理者义务"],
    )


def _issue(issue_id: str, severity: ReviewSeverity = ReviewSeverity.HIGH) -> ReviewIssue:
    sc = StructuredCitation(
        source_id="CN-LAW-003",
        source_title="个人信息保护法",
        article="第17条",
        snippet="个人信息可携带权条款摘录。",
        source_type="statute",
    )
    return ReviewIssue(
        issue_id=issue_id,
        clause_id=f"cl-{issue_id}",
        file_id="file-01",
        severity=severity,
        clause_type=ClauseType.RIGHTS_REQUEST,
        title=f"问题 {issue_id}",
        problem_type="MISSING_REQUIREMENT",
        original_excerpt="（未找到相关条款）",
        risk_analysis=f"{issue_id} 的风险分析。",
        citation_sources=["《个人信息保护法》第17条"],
        structured_citations=[sc],
        recommendation="补充条款。",
        review_method=ReviewMethod.LLM,
        review_confidence=0.9,
        review_depth=ReviewDepth.STANDARD,
    )


def test_document_review_ir_matches_golden_snapshot() -> None:
    doc, rep = build_document_review_ir(
        task_id="task-golden", document_title="隐私协议_测试.docx",
        review=_empty_review(), citation_registry=CitationRegistry(),
        model="test-model", generated_at=TS,
    )
    actual = {"document": doc.model_dump(mode="json"), "footnote_map": rep.footnote_map()}
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert actual == expected


def test_byte_stable_for_fixed_time() -> None:
    def _build() -> str:
        doc, _ = build_document_review_ir(
            task_id="t", document_title="D", review=_empty_review(),
            citation_registry=CitationRegistry(), model="m", generated_at=TS,
        )
        return json.dumps(doc.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)

    assert _build() == _build()


def test_compiler_gate_passes_on_empty_and_nonempty() -> None:
    for review in (_empty_review(), AggregatedReview(
        overall_rating="中风险", overall_risk_score=65.0, summary="摘要",
        issues=[_issue("DR-001")], issue_counts={"HIGH": 1, "MEDIUM": 0, "LOW": 0},
        priority_actions=["补充条款"],
    )):
        doc, rep = build_document_review_ir(
            task_id="t", document_title="D", review=review,
            citation_registry=CitationRegistry(), model="m", generated_at=TS,
        )
        cr = DocumentCompiler().compile(doc, rep)
        assert cr.status == "success", [d.code for d in cr.diagnostics]


def test_section_titles_are_unique_and_without_chinese_ordinal() -> None:
    doc, _ = build_document_review_ir(
        task_id="t", document_title="D", review=_empty_review(),
        citation_registry=CitationRegistry(), model="m", generated_at=TS,
    )
    titles = [s.title for s in doc.sections]
    assert len(titles) == len(set(titles)), f"duplicate titles: {titles}"
    for title in titles:
        assert "、" not in title, f"hand-written Chinese ordinal in title: {title}"
    # stable section ids, not Chinese ordinals
    assert [s.section_id for s in doc.sections] == [
        "review.s1", "review.s2", "review.s3", "review.s4", "review.s5",
        "review.s6", "review.s7", "review.s8", "review.s9", "review.s10",
    ]


def test_finding_count_and_order_match_issues() -> None:
    review = AggregatedReview(
        overall_rating="中风险", overall_risk_score=65.0, summary="摘要",
        issues=[_issue(f"DR-{i:03d}") for i in range(1, 4)],
        issue_counts={"HIGH": 3, "MEDIUM": 0, "LOW": 0},
        priority_actions=["补充条款"],
    )
    doc, _ = build_document_review_ir(
        task_id="t", document_title="D", review=review,
        citation_registry=CitationRegistry(), model="m", generated_at=TS,
    )
    assert [f.finding_id for f in doc.findings] == ["DR-001", "DR-002", "DR-003"]
    assert [f.clause_id for f in doc.findings] == ["cl-DR-001", "cl-DR-002", "cl-DR-003"]


def test_each_finding_has_exactly_one_detail_display() -> None:
    review = AggregatedReview(
        overall_rating="中风险", overall_risk_score=65.0, summary="摘要",
        issues=[_issue(f"DR-{i:03d}") for i in range(1, 4)],
        issue_counts={"HIGH": 3, "MEDIUM": 0, "LOW": 0},
        priority_actions=["补充条款"],
    )
    doc, rep = build_document_review_ir(
        task_id="t", document_title="D", review=review,
        citation_registry=CitationRegistry(), model="m", generated_at=TS,
    )
    detail_counts: dict[str, int] = {}
    for section in doc.sections:
        for block in section.blocks:
            if getattr(block, "type", None) == "finding_detail":
                detail_counts[block.finding_ref] = detail_counts.get(block.finding_ref, 0) + 1
    assert detail_counts == {"DR-001": 1, "DR-002": 1, "DR-003": 1}
    cr = DocumentCompiler().compile(doc, rep)
    assert cr.status == "success", [d.code for d in cr.diagnostics]
