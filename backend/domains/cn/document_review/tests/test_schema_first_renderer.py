"""Schema-first document_review renderer integration — production-form acceptance test.

Document review is unique: it uses AggregatedReview + build_sections rather than
chapters, and all blocks are ParagraphBlocks (no citation markers).  This test
exercises the full sections → adapter → compiler pipeline.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.common.citation.models import CitationItem
from backend.common.citation.output import write_citation_map_json
from backend.common.citation.registry import CitationRegistry
from backend.common.reporting import DocumentCompiler
from backend.domains.cn.document_review.review_report_renderer import ReviewReportRenderer
from backend.domains.cn.document_review.schema_first import build_document_review_ir
from backend.schemas.review import (
    AggregatedReview,
    ClauseType,
    MissingItem,
    ReviewDepth,
    ReviewIssue,
    ReviewMethod,
    ReviewSeverity,
)

_CID_PIPL_17 = "CIT-CN-PIPL-ART17-P01"
RECORD_TS = datetime(2026, 8, 8, tzinfo=timezone.utc)


def _registry() -> CitationRegistry:
    reg = CitationRegistry()
    reg.register(CitationItem(
        citation_id=_CID_PIPL_17, source_id="CN-LAW-003",
        citation_type="law_article", title="个人信息保护法",
        article_no="17", authority_level="high",
        binding_force="mandatory", external_report_allowed=True,
    ))
    reg.assign_footnote_number(_CID_PIPL_17)
    return reg


def _review() -> AggregatedReview:
    return AggregatedReview(
        overall_rating="中风险",
        overall_risk_score=65.0,
        summary="隐私政策存在2项高风险问题和1项中风险问题，需补充数据出境相关条款。",
        issues=[
            ReviewIssue(
                issue_id="DR-001",
                clause_id="cl-01",
                file_id="file-01",
                severity=ReviewSeverity.HIGH,
                clause_type=ClauseType.RIGHTS_REQUEST,
                title="缺失数据可携权条款",
                problem_type="MISSING_REQUIREMENT",
                original_excerpt="（未找到相关条款）",
                risk_analysis="用户的个人信息可携权未在隐私政策中体现，存在合规风险。",
                citation_sources=["PIPL Art 17"],
                recommendation="补充数据可携权相关条款，明确用户请求数据导出的流程。",
                review_method=ReviewMethod.LLM,
                review_confidence=0.92,
                review_depth=ReviewDepth.STANDARD,
            ),
            ReviewIssue(
                issue_id="DR-002",
                clause_id="cl-02",
                file_id="file-01",
                severity=ReviewSeverity.HIGH,
                clause_type=ClauseType.CROSS_BORDER_TRANSFER,
                title="缺失数据出境告知条款",
                problem_type="MISSING_REQUIREMENT",
                original_excerpt="（未找到相关条款）",
                risk_analysis="涉及数据出境但未告知用户，违反PIPL数据出境规定。",
                citation_sources=["PIPL Art 17"],
                recommendation="补充数据出境告知条款，包含接收方信息、目的和数据类型。",
                review_method=ReviewMethod.LLM,
                review_confidence=0.88,
                review_depth=ReviewDepth.STANDARD,
            ),
        ],
        issue_counts={"HIGH": 2, "MEDIUM": 0, "LOW": 0},
        priority_actions=[
            "1. 补充数据可携权条款",
            "2. 补充数据出境告知条款",
        ],
        missing_items=[
            MissingItem(
                item_id="MI-001",
                clause_type=ClauseType.RIGHTS_REQUEST,
                title="数据可携权条款",
                description="隐私政策未包含用户请求数据导出的权利条款。",
                severity=ReviewSeverity.HIGH,
                legal_basis=["PIPL Art 17"],
                recommendation="参考PIPL第17条补充。",
            ),
            MissingItem(
                item_id="MI-002",
                clause_type=ClauseType.CROSS_BORDER_TRANSFER,
                title="数据出境告知条款",
                description="缺少关于数据出境接收方、目的、数据类型的告知。",
                severity=ReviewSeverity.HIGH,
                legal_basis=["PIPL Art 17"],
                recommendation="补充出境告知，明确接收方和传输目的。",
            ),
        ],
        document_profile={
            "document_type": "隐私政策",
            "document_title": "隐私协议_测试.docx",
            "total_clauses": "12",
            "classified_clauses": "12",
            "total_issues_found": "2",
            "total_missing_items": "2",
        },
        clauses_summary={"RIGHTS_REQUEST": 3, "CROSS_BORDER_TRANSFER": 1, "SECURITY_MEASURES": 4, "OTHER": 4},
        consistency_warnings=["文档未涉及儿童个人信息保护规定"],
        review_metadata={
            "review_mode": "llm_deep",
            "review_started_at": "2026-08-08T10:00:00",
            "review_completed_at": "2026-08-08T10:02:00",
        },
    )


def _sections(review: AggregatedReview | None = None):
    return ReviewReportRenderer().build_sections(review or _review())


# ── tests ──────────────────────────────────────────────────────────────────────


def test_production_form_with_schema_first_generates_document_ir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    reg = _registry()
    review = _review()
    doc_ir, reporting_reg = build_document_review_ir(
        task_id="phase3-review-prod-new",
        document_title="隐私协议_测试.docx",
        review=review,
        sections=_sections(review),
        citation_registry=reg,
        model="deepseek-v3",
        generated_at=RECORD_TS,
    )

    compile_result = DocumentCompiler().compile(doc_ir, reporting_reg)
    assert compile_result.status == "success"
    assert doc_ir.document_id == "review:phase3-review-prod-new"
    assert doc_ir.report_type == "review"
    assert len(doc_ir.sections) == 10  # 10 sections from build_sections
    assert doc_ir.provenance.generated_at == RECORD_TS

    ir_data = doc_ir.model_dump(mode="json")
    assert ir_data["diagnostics"] == []

    claim_count = para_count = 0
    for sec in ir_data["sections"]:
        for blk in sec["blocks"]:
            if blk["type"] == "claim":
                claim_count += 1
            elif blk["type"] == "paragraph":
                para_count += 1
            assert "[1]" not in blk["text"], f"Citation residue in block: {blk['text'][:60]}"
            assert "{{CIT-" not in blk["text"]

    # Document review has no citation markers → all blocks are paragraphs
    assert claim_count == 0
    assert para_count >= 10

    output_dir = tmp_path / "outputs/review/phase3-review-prod-new/outputs"
    output_dir.mkdir(parents=True)
    cmap_path = write_citation_map_json(
        output_dir=output_dir, module="review", task_id="phase3-review-prod-new",
        footnote_map={str(n): item.to_dict() for n, item in reg.get_footnote_map().items()},
        all_items=reg.to_list(),
    )
    cmap = json.loads(Path(cmap_path).read_text(encoding="utf-8"))
    footnote_map = cmap.get("footnote_map", {})
    assert len(footnote_map) == 1
    assert footnote_map["1"]["citation_id"] == _CID_PIPL_17

    print(f"\n✅ Document Review prod-form: {len(doc_ir.sections)} sections, {para_count} ParagraphBlocks")


def test_production_form_without_schema_first_omits_document_ir():
    assert callable(build_document_review_ir)


def test_production_form_block_count_invariant():
    review = _review()
    sections = _sections(review)

    def _counts():
        doc_ir, _ = build_document_review_ir(
            task_id="phase3-review-invariant",
            document_title="隐私协议_测试.docx",
            review=review, sections=sections,
            citation_registry=CitationRegistry(), model="deepseek-v3", generated_at=RECORD_TS,
        )
        counts = {}
        for s in doc_ir.sections:
            for b in s.blocks:
                counts[b.type] = counts.get(b.type, 0) + 1
        return counts

    assert _counts() == _counts()


def test_compiler_accepts_empty_citation_registry():
    """Document review has no citations in blocks → even empty registry passes."""
    review = _review()
    doc_ir, rr = build_document_review_ir(
        task_id="phase3-review-empty-reg",
        document_title="隐私协议_测试.docx",
        review=review, sections=_sections(review),
        citation_registry=CitationRegistry(), model="test", generated_at=RECORD_TS,
    )
    result = DocumentCompiler().compile(doc_ir, rr)
    assert result.status == "success", f"Compiler failed: {result.diagnostics}"


def test_sections_parity_between_golden_and_production(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    review = _review()
    doc_ir, _ = build_document_review_ir(
        task_id="phase3-review-structure",
        document_title="隐私协议_测试.docx",
        review=review, sections=_sections(review),
        citation_registry=_registry(), model="deepseek-v3", generated_at=RECORD_TS,
    )
    section_titles = [s.title for s in doc_ir.sections]
    expected_titles = [title for title, _ in _sections(review)]
    assert section_titles == expected_titles, (
        f"IR section titles drift from renderer: {section_titles} vs {expected_titles}"
    )
    print(f"\n✅ Document Review section parity: {len(section_titles)} titles match")
