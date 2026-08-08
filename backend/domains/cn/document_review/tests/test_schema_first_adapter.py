"""Schema-first document_review adapter tests."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from backend.common.citation.registry import CitationRegistry
from backend.common.reporting import DocumentCompiler
from backend.domains.cn.document_review.review_report_renderer import ReviewReportRenderer
from backend.domains.cn.document_review.schema_first import build_document_review_ir
from backend.schemas.review import AggregatedReview

GOLDEN = Path(__file__).parent / "schema_first_fixtures" / "review_document_ir.golden.json"
TS = datetime(2026, 8, 8, tzinfo=timezone.utc)


def _review() -> AggregatedReview:
    return AggregatedReview(
        overall_rating="HIGH",
        overall_risk_score=72.0,
        summary="合同存在数据出境条款缺失等高风险问题，需整改后方可使用。",
        issues=[],
        issue_counts={"HIGH": 2, "MEDIUM": 1, "LOW": 0},
        priority_actions=["补充数据出境条款", "明确数据处理者义务"],
    )


def _sections(review: AggregatedReview | None = None):
    return ReviewReportRenderer().build_sections(review or _review())


def test_document_review_ir_matches_golden_snapshot() -> None:
    doc, rep = build_document_review_ir(
        task_id="task-golden", document_title="隐私协议_测试.docx",
        review=_review(), sections=_sections(),
        citation_registry=CitationRegistry(), model="test-model", generated_at=TS,
    )
    actual = {"document": doc.model_dump(mode="json"), "footnote_map": rep.footnote_map()}
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert actual == expected


def test_compiler_gate_passes_on_review_output() -> None:
    doc, rep = build_document_review_ir(
        task_id="t", document_title="D", review=_review(), sections=_sections(),
        citation_registry=CitationRegistry(), model="m", generated_at=TS,
    )
    cr = DocumentCompiler().compile(doc, rep)
    assert cr.status == "success"
    assert not cr.diagnostics


def test_review_ir_has_expected_structure() -> None:
    doc, _ = build_document_review_ir(
        task_id="t", document_title="D", review=_review(), sections=_sections(),
        citation_registry=CitationRegistry(), model="m", generated_at=TS,
    )
    assert doc.document_id == "review:t"
    assert doc.report_type == "review"
    assert len(doc.sections) == 10
    for section in doc.sections:
        assert section.blocks, f"section '{section.title}' has no blocks"
        for block in section.blocks:
            assert "[1]" not in block.text
            assert "{{CIT-" not in block.text
