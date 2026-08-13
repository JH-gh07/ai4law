"""task068 T01 — FindingBasis / basis_entries schema + compiler gates (I068-22).

``FindingBasis`` upgrades ``legal_basis: list[str]`` into ``(citation, label,
rationale)`` so a finding's multiple citations can carry a per-citation "why
this applies" attribution without the adapter inventing legal conclusions.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.common.reporting import (
    CitationRecord,
    DocumentCompiler,
    DocumentIR,
    FindingBasis,
    FindingDetailBlock,
    FindingRecord,
    Provenance,
    ReportMetadata,
    SectionIR,
)


def _doc(*, findings=None, citations=None) -> DocumentIR:
    return DocumentIR(
        compiler_version="0.1.0",
        prompt_version="test",
        template_version="test",
        model="test-model",
        document_id="doc-1",
        report_type="review",
        metadata=ReportMetadata(title="测试报告"),
        provenance=Provenance(generated_at=datetime.now(timezone.utc)),
        findings=findings or [],
        citations=citations or [],
        sections=[
            SectionIR(section_id="s1", title="详情", level=1, blocks=[
                FindingDetailBlock(block_id="b1", finding_ref=f.finding_id)
            ])
            for f in (findings or [])
        ],
    )


def _citation(cid: str = "CIT-1") -> CitationRecord:
    return CitationRecord(
        citation_id=cid,
        source_id="SRC-1",
        source_type="regulation",
        title="个人信息保护法",
    )


def _basis(**kw) -> FindingBasis:
    base = dict(label="《个人信息保护法》第38条", rationale="未约定安全评估，不满足出境条件。")
    base.update(kw)
    return FindingBasis(**base)


def test_finding_basis_is_forbid_extra() -> None:
    with pytest.raises(ValidationError):
        FindingBasis(label="x", rationale="r", unexpected_field="boom")


def test_finding_record_accepts_basis_entries_and_review_fields() -> None:
    f = FindingRecord(
        finding_id="REV-1",
        requirement_id="R-1",
        title="数据出境缺失",
        statement="现状",
        legal_basis=["《个人信息保护法》第38条"],
        basis_entries=[_basis()],
        original_excerpt="（合成条款）",
        clause_type="CROSS_BORDER_TRANSFER",
        problem_type="MISSING_REQUIREMENT",
    )
    assert f.basis_entries[0].label == "《个人信息保护法》第38条"
    assert f.original_excerpt == "（合成条款）"
    assert f.clause_type == "CROSS_BORDER_TRANSFER"
    assert f.problem_type == "MISSING_REQUIREMENT"


def test_finding_record_carries_all_review_lossless_fields() -> None:
    """task068 T01 — every ``ReviewIssue`` field has a typed destination.

    This is the schema-level half of the "no field silently dropped" freeze; the
    adapter (T02) is what populates them. All are optional so the other eight
    modules' golden fixtures stay unchanged.
    """
    f = FindingRecord(
        finding_id="REV-1",
        requirement_id="R-1",
        title="数据出境缺失",
        statement="风险分析…",
        legal_basis=["《个人信息保护法》第38条"],
        recommendation="整改建议…",
        original_excerpt="（合成条款）",
        clause_type="CROSS_BORDER_TRANSFER",
        problem_type="MISSING_REQUIREMENT",
        clause_id="clause-7",
        file_id="file-1",
        source_position={"start": 0, "end": 42},
        secondary_clause_types=["THIRD_PARTY_SHARING"],
        uncertainty_rationale="需用户补充确认",
        review_method="rule",
        review_depth="standard",
        risk_score=80.0,
        review_confidence=0.7,
        facts_uncertain=True,
    )
    assert f.clause_id == "clause-7"
    assert f.file_id == "file-1"
    assert f.secondary_clause_types == ["THIRD_PARTY_SHARING"]
    assert f.uncertainty_rationale == "需用户补充确认"
    assert f.review_method == "rule"
    assert f.review_depth == "standard"


def test_valid_basis_entries_compile_clean() -> None:
    f = FindingRecord(
        finding_id="REV-1",
        requirement_id="R-1",
        title="数据出境缺失",
        statement="现状",
        basis_entries=[_basis(citation_ref="CIT-1")],
    )
    result = DocumentCompiler().compile(_doc(findings=[f], citations=[_citation()]))
    assert result.status == "success", [d.code for d in result.diagnostics]


def test_basis_citation_not_registered_is_rejected() -> None:
    f = FindingRecord(
        finding_id="REV-1",
        requirement_id="R-1",
        title="数据出境缺失",
        statement="现状",
        basis_entries=[_basis(citation_ref="CIT-MISSING")],
    )
    result = DocumentCompiler().compile(_doc(findings=[f], citations=[_citation()]))
    assert result.status == "error"
    assert any(d.code == "BASIS_CITATION_NOT_REGISTERED" for d in result.diagnostics)


def test_basis_label_only_entry_without_citation_ref_is_allowed() -> None:
    f = FindingRecord(
        finding_id="REV-1",
        requirement_id="R-1",
        title="数据出境缺失",
        statement="现状",
        basis_entries=[_basis(citation_ref=None)],
    )
    result = DocumentCompiler().compile(_doc(findings=[f], citations=[_citation()]))
    assert result.status == "success", [d.code for d in result.diagnostics]


@pytest.mark.parametrize(
    "rationale",
    [
        "作为人工智能，我无法提供法律意见。",
        "As an AI language model, I cannot answer that.",
        "I don't have enough context to determine this.",
        "无法确定该条款是否适用。",
        "待补充 TODO",
        "占位符：{{RATIONALE}}",
    ],
)
def test_basis_rationale_with_llm_or_placeholder_signature_is_rejected(rationale: str) -> None:
    f = FindingRecord(
        finding_id="REV-1",
        requirement_id="R-1",
        title="数据出境缺失",
        statement="现状",
        basis_entries=[_basis(citation_ref="CIT-1", rationale=rationale)],
    )
    result = DocumentCompiler().compile(_doc(findings=[f], citations=[_citation()]))
    assert result.status == "error"
    assert any(d.code == "BASIS_RATIONALE_ILLEGAL_GENERATED" for d in result.diagnostics)


def test_basis_rationale_attributed_from_business_field_passes() -> None:
    # A genuine attribution reads like a conclusion tied to the finding, not an
    # LLM refusal or a placeholder.
    f = FindingRecord(
        finding_id="REV-1",
        requirement_id="R-1",
        title="数据出境缺失",
        statement="现状",
        basis_entries=[_basis(citation_ref="CIT-1", rationale="未约定安全评估，不满足出境条件。")],
    )
    result = DocumentCompiler().compile(_doc(findings=[f], citations=[_citation()]))
    assert result.status == "success", [d.code for d in result.diagnostics]
