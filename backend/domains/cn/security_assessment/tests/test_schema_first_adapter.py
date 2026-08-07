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
