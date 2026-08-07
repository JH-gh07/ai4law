from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry
from backend.domains.cn.security_assessment.schema import ChapterContent
from backend.domains.cn.security_assessment.schema_first import build_assessment_document_ir

FIXTURE = Path(__file__).parent / "fixtures" / "assessment_document_ir.golden.json"


def test_assessment_document_ir_matches_golden_snapshot() -> None:
    legacy_registry = CitationRegistry()
    legacy_registry.register(CitationItem(
        citation_id="CIT-CN-EXPORT-ASSESSMENT-ART5-P01",
        source_id="CN-REG-001",
        citation_type="law_article",
        title="数据出境安全评估办法",
        article_no="5",
        authority_level="high",
        binding_force="mandatory",
        external_report_allowed=True,
    ))
    chapters = [
        ChapterContent(
            chapter_no=1,
            title="出境活动概述",
            content="企业应当开展申报前评估 {{CIT-CN-EXPORT-ASSESSMENT-ART5-P01}}。",
            risk_level="HIGH",
        ),
        ChapterContent(
            chapter_no=2,
            title="整改建议",
            content="补充境外接收方安全能力证明。",
            risk_level="MEDIUM",
        ),
    ]

    document, reporting_registry = build_assessment_document_ir(
        task_id="task-golden",
        company_name="测试公司",
        chapters=chapters,
        citation_registry=legacy_registry,
        generated_at=datetime(2026, 8, 8, tzinfo=timezone.utc),
        model="test-model",
    )

    actual = {
        "document": document.model_dump(mode="json"),
        "footnote_map": reporting_registry.footnote_map(),
    }
    expected = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert actual == expected


def test_assessment_document_ir_keeps_unregistered_marker_for_compiler_diagnostic() -> None:
    document, _ = build_assessment_document_ir(
        task_id="task-missing",
        company_name="测试公司",
        chapters=[ChapterContent(
            chapter_no=1,
            title="风险结论",
            content="该处理活动必须整改 {{CIT-CN-UNKNOWN-ART1-P01}}。",
            risk_level="HIGH",
        )],
        citation_registry=CitationRegistry(),
        generated_at=datetime(2026, 8, 8, tzinfo=timezone.utc),
        model="test-model",
    )

    block = document.sections[0].blocks[0]
    assert block.citation_refs == ["CIT-CN-UNKNOWN-ART1-P01"]


# ---------------------------------------------------------------------------
# Regression: production chapter content carries [N] footnotes, not raw
# {{CIT-*}} markers, because chapter_generator.py:445 already ran
# convert_citation_markers(). Before ISSUE-reporting-001 this adapter regexed
# only for {{CIT-*}}, so real content lost every citation_ref and then raised
# ValidationError on the surviving "[1]" text. Keep both shapes pinned.
# ---------------------------------------------------------------------------

_PROD_CID = "CIT-CN-EXPORT-ASSESSMENT-ART5-P01"


def _prod_registry() -> CitationRegistry:
    registry = CitationRegistry()
    registry.register(CitationItem(
        citation_id=_PROD_CID,
        source_id="CN-REG-001",
        citation_type="law_article",
        title="数据出境安全评估办法",
        article_no="5",
        authority_level="high",
        binding_force="mandatory",
        external_report_allowed=True,
    ))
    return registry


def _build_prod(content: str):
    registry = _prod_registry()
    # Mirror the generator: assign the footnote number before adapting.
    registry.assign_footnote_number(_PROD_CID)
    return build_assessment_document_ir(
        task_id="task-prod-shape",
        company_name="测试公司",
        chapters=[ChapterContent(
            chapter_no=1,
            title="出境活动概述",
            content=content,
            risk_level="HIGH",
        )],
        citation_registry=registry,
        generated_at=datetime(2026, 8, 8, tzinfo=timezone.utc),
        model="test-model",
    )


def test_production_footnote_shape_yields_claim_block_with_refs() -> None:
    document, reporting_registry = _build_prod("企业应当开展申报前评估 [1]。")

    block = document.sections[0].blocks[0]
    assert type(block).__name__ == "ClaimBlock", (
        "production [N] content must still produce a ClaimBlock"
    )
    assert block.citation_refs == [_PROD_CID]
    assert "[1]" not in block.text
    assert block.text == "企业应当开展申报前评估。"

    from backend.common.reporting import DocumentCompiler

    compile_result = DocumentCompiler().compile(document, reporting_registry)
    assert compile_result.status == "success"
    assert not compile_result.diagnostics


def test_marker_and_footnote_shapes_agree() -> None:
    marker_doc, _ = _build_prod("企业应当开展申报前评估 {{%s}}。" % _PROD_CID)
    footnote_doc, _ = _build_prod("企业应当开展申报前评估 [1]。")

    marker_block = marker_doc.sections[0].blocks[0]
    footnote_block = footnote_doc.sections[0].blocks[0]

    assert marker_block.citation_refs == footnote_block.citation_refs
    assert marker_block.text == footnote_block.text
