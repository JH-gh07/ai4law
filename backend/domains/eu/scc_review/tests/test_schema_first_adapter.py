"""Schema-first SCC review adapter tests."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry
from backend.common.reporting import DocumentCompiler
from backend.domains.eu.scc_review.schema import SCCChapter
from backend.domains.eu.scc_review.schema_first import build_scc_document_ir

GOLDEN = Path(__file__).parent / "fixtures" / "scc_document_ir.golden.json"
CID = "CIT-EU-GDPR-ART35-P01"


def _reg() -> CitationRegistry:
    r = CitationRegistry()
    r.register(CitationItem(
        citation_id=CID, source_id="SRC", citation_type="law_article",
        title="GDPR (EU) 2016/679", article_no="35",
        authority_level="high", binding_force="mandatory", external_report_allowed=True,
    ))
    r.assign_footnote_number(CID)
    return r


def _chapters() -> list[SCCChapter]:
    return [
        SCCChapter(chapter_no=1, title="BCR 类型判断", content="本BCR遵循GDPR第47条 [1]。", risk_level="HIGH"),
        SCCChapter(chapter_no=2, title="整改建议", content="补充数据主体权利机制说明。", risk_level="LOW"),
    ]


def test_scc_document_ir_matches_golden_snapshot() -> None:
    doc, rep = build_scc_document_ir(
        task_id="task-golden", company_name="TestCo",
        chapters=_chapters(), citation_registry=_reg(),
        generated_at=datetime(2026, 8, 8, tzinfo=timezone.utc), model="test-model",
    )
    actual = {"document": doc.model_dump(mode="json"), "footnote_map": rep.footnote_map()}
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert actual == expected


def test_production_footnote_shape_yields_claim_block() -> None:
    doc, rep = build_scc_document_ir(
        task_id="t", company_name="C",
        chapters=[SCCChapter(chapter_no=1, title="T", content="法规依据 [1]。", risk_level="HIGH")],
        citation_registry=_reg(), generated_at=datetime(2026, 8, 8, tzinfo=timezone.utc), model="m",
    )
    block = doc.sections[0].blocks[0]
    assert type(block).__name__ == "ClaimBlock"
    assert block.citation_refs == [CID]
    assert "[1]" not in block.text
    cr = DocumentCompiler().compile(doc, rep)
    assert cr.status == "success"
    assert not cr.diagnostics


def test_both_citation_shapes_produce_identical_ir() -> None:
    def build(content: str):
        doc, _ = build_scc_document_ir(
            task_id="t", company_name="C",
            chapters=[SCCChapter(chapter_no=1, title="T", content=content, risk_level="HIGH")],
            citation_registry=_reg(), generated_at=datetime(2026, 8, 8, tzinfo=timezone.utc), model="m",
        )
        return doc.model_dump(mode="json")
    assert build("{{CIT-EU-GDPR-ART35-P01}} 法规依据。") == build("法规依据 [1]。")


def test_findings_section_allows_repeated_field_labels() -> None:
    content = (
        "### 1. Clause 15\n\n风险等级: HIGH\n\n"
        "### 2. Annex II\n\n风险等级: HIGH"
    )
    doc, registry = build_scc_document_ir(
        task_id="findings",
        company_name="C",
        chapters=[
            SCCChapter(
                chapter_no=3,
                title="条款级审查发现",
                content=content,
                risk_level="HIGH",
            )
        ],
        citation_registry=_reg(),
        generated_at=datetime(2026, 8, 8, tzinfo=timezone.utc),
        model="m",
    )

    assert doc.sections[0].reuse_policy == "reference"
    assert DocumentCompiler().compile(doc, registry).status == "success"
