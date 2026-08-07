"""Schema-first EO 14117 compliance adapter tests."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry
from backend.common.reporting import DocumentCompiler
from backend.domains.us.eo14117.schema import US14117Chapter
from backend.domains.us.eo14117.schema_first import build_eo14117_document_ir

GOLDEN = Path(__file__).parent / "fixtures" / "eo14117_document_ir.golden.json"
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


def _chapters() -> list[US14117Chapter]:
    return [
        US14117Chapter(chapter_no=1, title="BCR 类型判断", content="本BCR遵循GDPR第47条 [1]。", risk_level="HIGH"),
        US14117Chapter(chapter_no=2, title="整改建议", content="补充数据主体权利机制说明。", risk_level="LOW"),
    ]


def test_eo14117_document_ir_matches_golden_snapshot() -> None:
    doc, rep = build_eo14117_document_ir(
        task_id="task-golden", company_name="TestCo",
        chapters=_chapters(), citation_registry=_reg(),
        generated_at=datetime(2026, 8, 8, tzinfo=timezone.utc), model="test-model",
    )
    actual = {"document": doc.model_dump(mode="json"), "footnote_map": rep.footnote_map()}
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert actual == expected


def test_production_footnote_shape_yields_claim_block() -> None:
    doc, rep = build_eo14117_document_ir(
        task_id="t", company_name="C",
        chapters=[US14117Chapter(chapter_no=1, title="T", content="法规依据 [1]。", risk_level="HIGH")],
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
        doc, _ = build_eo14117_document_ir(
            task_id="t", company_name="C",
            chapters=[US14117Chapter(chapter_no=1, title="T", content=content, risk_level="HIGH")],
            citation_registry=_reg(), generated_at=datetime(2026, 8, 8, tzinfo=timezone.utc), model="m",
        )
        return doc.model_dump(mode="json")
    assert build("{{CIT-EU-GDPR-ART35-P01}} 法规依据。") == build("法规依据 [1]。")
