"""Schema-first BCR adapter tests — v4 findings-based IR (T02)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry
from backend.common.reporting import DocumentCompiler
from backend.domains.eu.bcr_review.schema import BCRFinding, BCRTypeClassification
from backend.domains.eu.bcr_review.schema_first import build_bcr_document_ir

GOLDEN = Path(__file__).parent / "fixtures" / "bcr_document_ir.golden.json"
CID = "CIT-EU-GDPR-ART47-P01"
TS = datetime(2026, 8, 8, tzinfo=timezone.utc)


def _reg() -> CitationRegistry:
    r = CitationRegistry()
    r.register(CitationItem(
        citation_id=CID, source_id="EU-LAW-001", citation_type="law_article",
        title="GDPR (EU) 2016/679", article_no="47(1)",
        authority_level="high", binding_force="mandatory", external_report_allowed=True,
    ))
    r.assign_footnote_number(CID)
    return r


def _type_class() -> BCRTypeClassification:
    return BCRTypeClassification(
        declared_bcr_type="BCR-C",
        actual_bcr_type="BCR-C",
        type_consistency="consistent",
        risk_level="MEDIUM",
    )


def _findings() -> list[BCRFinding]:
    return [
        BCRFinding(
            finding_id="BCR-C-1.1-01",
            requirement_id="BCR-C-1.1",
            title="约束力不足",
            risk_level="HIGH",
            risk_score=60.0,
            finding="集团内部约束机制不完整。",
            legal_basis=["GDPR Article 47(1)"],
            recommendation="补充集团内部约束条款。",
            suggested_revision="(a) 指定欧盟责任主体\n(b) 明确第三方受益权",
            citation_refs=[CID],
        ),
        BCRFinding(
            finding_id="BCR-C-1.9-01",
            requirement_id="BCR-C-1.9",
            title="TIA 不完整",
            risk_level="MEDIUM",
            finding="第三国法律评估不完整。",
            legal_basis=["EDPB Recommendations 01/2020 Step 3"],
            recommendation="补充第三国法律评估。",
        ),
    ]


def _build(**overrides):
    kwargs = dict(
        task_id="task-golden",
        company_name="TestCo",
        type_class=_type_class(),
        rating="部分缺失",
        score=55.0,
        findings=_findings(),
        missing=["BCR-C-1.9"],
        citation_registry=_reg(),
        metadata={"bcr_type": "BCR-C"},
        model="test-model",
        generated_at=TS,
    )
    kwargs.update(overrides)
    return build_bcr_document_ir(**kwargs)


def test_bcr_document_ir_matches_golden_snapshot() -> None:
    doc, rep = _build()
    actual = {"document": doc.model_dump(mode="json"), "footnote_map": rep.footnote_map()}
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert actual == expected


def test_finding_count_and_order_match_input() -> None:
    doc, _ = _build()
    assert [f.finding_id for f in doc.findings] == ["BCR-C-1.1-01", "BCR-C-1.9-01"]


def test_each_finding_has_exactly_one_primary_display() -> None:
    doc, rep = _build()
    result = DocumentCompiler().compile(doc, rep)
    assert result.status == "success", [d.code for d in result.diagnostics]
    assert [f.primary_display_count for f in doc.findings] == [1, 1]


def test_ir_has_no_markdown_table_separator() -> None:
    doc, _ = _build()
    payload = json.dumps(doc.model_dump(mode="json"), ensure_ascii=False)
    assert "| --- |" not in payload
    assert "\n|---" not in payload


def test_citation_ids_kept_not_display_numbers() -> None:
    doc, _ = _build()
    assert doc.findings[0].citation_refs == [CID]
    # no [N] or raw markers leak into any semantic block text
    for section in doc.sections:
        for block in section.blocks:
            if hasattr(block, "text"):
                assert "[1]" not in block.text
                assert "{{" not in block.text


def test_suggested_revision_becomes_multi_level_clause() -> None:
    doc, _ = _build()
    clause_blocks = [b for s in doc.sections for b in s.blocks if b.type == "clause_group"]
    assert len(clause_blocks) == 1
    clauses = clause_blocks[0].clauses
    assert clauses[0].node_id == "clause.BCR-C-1.1-01"
    assert [child.node_id for child in clauses[0].children] == [
        "clause.BCR-C-1.1-01.1",
        "clause.BCR-C-1.1-01.2",
    ]
    assert [child.numbering_style for child in clauses[0].children] == ["lower_alpha", "lower_alpha"]


def test_byte_stable_for_fixed_input() -> None:
    a, _ = _build()
    b, _ = _build()
    assert a.model_dump(mode="json") == b.model_dump(mode="json")


def test_compiler_rejects_unknown_citation() -> None:
    doc, rep = _build(
        findings=[
            BCRFinding(
                finding_id="F-1", requirement_id="BCR-C-1.1", title="X",
                risk_level="HIGH", finding="现状不合规。",
                citation_refs=["CIT-MISSING"],
            )
        ],
        missing=[],
    )
    result = DocumentCompiler().compile(doc, rep)
    assert result.status == "error"
    assert any(d.code == "CITATION_NOT_REGISTERED" for d in result.diagnostics)
