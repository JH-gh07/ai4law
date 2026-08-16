r"""Negative regression tests for the task077 validation-layer gates.

The task077 remediation plan (T06) fixed two fail-closed layers whose
automated coverage was previously only exercised manually:

* :class:`CitationRelevanceChecker` — a corrupted article locator
  ("处罚-17-1" / "第X条-ext-1") must fail relevance, and a ``relevant=False``
  verdict must always carry a human-readable reason (no blank
  "引用相关性警告").
* :class:`ReviewService._validate_citation_integrity` — the report-time final
  check must surface corrupted locators, template/case sources leaking into
  "法规依据", and per-issue citation counts exceeding the cap.
"""

from __future__ import annotations

from backend.domains.cn.document_review.citation_relevance_checker import (
    CitationRelevanceChecker,
)
from backend.domains.cn.document_review.service import ReviewService
from backend.schemas.review import (
    ClauseType,
    ReviewIssue,
    ReviewSeverity,
    StructuredCitation,
)


def _make_issue(
    *,
    clause_type: ClauseType = ClauseType.CROSS_BORDER_TRANSFER,
    structured_citations: list[StructuredCitation] | None = None,
    citation_sources: list[str] | None = None,
) -> ReviewIssue:
    return ReviewIssue(
        issue_id="ISS-1",
        clause_id="CL-1",
        file_id="F-1",
        clause_type=clause_type,
        severity=ReviewSeverity.HIGH,
        title="数据跨境传输",
        problem_type="NON_COMPLIANT",
        risk_analysis="未约定出境安全评估",
        original_excerpt="原文",
        recommendation="补充约定",
        structured_citations=structured_citations or [],
        citation_sources=citation_sources or [],
    )


def _citation(
    *,
    source_id: str = "CN-LAW-003",
    source_title: str = "个人信息保护法",
    article: str = "第38条",
    source_type: str = "statute",
) -> StructuredCitation:
    return StructuredCitation(
        source_id=source_id,
        source_title=source_title,
        article=article,
        source_type=source_type,
    )


# ---------------------------------------------------------------------------
# CitationRelevanceChecker — corrupted locator + empty-gap
# ---------------------------------------------------------------------------


def test_corrupted_structured_article_fails_relevance() -> None:
    checker = CitationRelevanceChecker()
    issue = _make_issue(
        structured_citations=[_citation(article="处罚-17-1")],
    )

    result = checker.check(issue)

    assert result["relevant"] is False
    assert any("非法条号" in msg for msg in result["issues"])


def test_corrupted_citation_source_fails_relevance() -> None:
    checker = CitationRelevanceChecker()
    issue = _make_issue(
        citation_sources=["《个人信息保护法》处罚-17-1"],
    )

    result = checker.check(issue)

    assert result["relevant"] is False
    assert any("非法条号" in msg for msg in result["issues"])


def test_relevant_false_always_carries_a_reason() -> None:
    """The old code could emit ``relevant=False, issues=[]`` (blank warning).

    A citation that scores >= 0.3 individually (no "关联度低" issue) but whose
    average drops below the 0.4 threshold used to produce an empty issue list.
    The fix must guarantee a human-readable reason in every fail path.
    """
    checker = CitationRelevanceChecker()
    # Source/article/snippet share no keyword or character overlap with the
    # CROSS_BORDER_TRANSFER issue, so the score stays at the 0.3 base floor.
    issue = _make_issue(
        structured_citations=[
            _citation(
                source_id="CN-OTHER-001",
                source_title="测试法",
                article="第999条",
            ),
        ],
    )

    result = checker.check(issue)

    assert result["relevant"] is False
    assert result["issues"], "relevant=False must never render an empty warning"
    assert any("相关性不足" in msg for msg in result["issues"])


def test_relevant_true_with_legit_citation() -> None:
    """A matching cross-border citation stays relevant and issue-free."""
    checker = CitationRelevanceChecker()
    issue = _make_issue(
        structured_citations=[_citation(article="第38条")],
        citation_sources=["《个人信息保护法》第38条"],
    )

    result = checker.check(issue)

    assert result["relevant"] is True
    assert result["issues"] == []


# ---------------------------------------------------------------------------
# ReviewService._validate_citation_integrity — report-time fail-closed gate
# ---------------------------------------------------------------------------


def test_integrity_gate_detects_corrupted_locator() -> None:
    issue = _make_issue(
        structured_citations=[_citation(article="处罚-17-1")],
    )

    diagnostics = ReviewService._validate_citation_integrity([issue])

    assert any("非法条号" in msg for msg in diagnostics)


def test_integrity_gate_detects_corrupted_citation_source() -> None:
    issue = _make_issue(
        citation_sources=["《个人信息保护法》第38条-ext-1"],
    )

    diagnostics = ReviewService._validate_citation_integrity([issue])

    assert any("非法引用" in msg for msg in diagnostics)


def test_integrity_gate_detects_template_source() -> None:
    issue = _make_issue(
        structured_citations=[_citation(source_type="template_slot")],
    )

    diagnostics = ReviewService._validate_citation_integrity([issue])

    assert any("模板/案例来源" in msg for msg in diagnostics)


def test_integrity_gate_detects_case_source() -> None:
    issue = _make_issue(
        structured_citations=[_citation(source_type="case", article="")],
    )

    diagnostics = ReviewService._validate_citation_integrity([issue])

    assert any("模板/案例来源" in msg for msg in diagnostics)


def test_integrity_gate_detects_over_cap_citations() -> None:
    issue = _make_issue(
        structured_citations=[
            _citation(article=f"第{i}条") for i in range(1, 10)
        ],
    )

    diagnostics = ReviewService._validate_citation_integrity([issue])

    assert any("超过上限 8" in msg for msg in diagnostics)


def test_integrity_gate_passes_clean_citation() -> None:
    issue = _make_issue(
        structured_citations=[_citation(article="第38条")],
        citation_sources=["《个人信息保护法》第38条"],
    )

    assert ReviewService._validate_citation_integrity([issue]) == []
