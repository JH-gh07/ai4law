"""Schema-first DPIA adapter tests — golden snapshot + compiler gate contracts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

import pytest

from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry
from backend.domains.eu.dpia.report_renderer import DPIAReportRenderer
from backend.domains.eu.dpia.schema import DPIAChapterContent, DPIAProjectProfile
from backend.domains.eu.dpia.schema_first import build_dpia_document_ir
from backend.common.reporting import DocumentCompiler

FIXTURES = Path(__file__).parent / "fixtures"
GOLDEN = FIXTURES / "dpia_document_ir.golden.json"


def _profile() -> DPIAProjectProfile:
    return DPIAProjectProfile(
        project_name="员工健康评估系统",
        project_goal="通过算法对员工健康数据进行分级评估",
        processing_flow_description="收集体检报告与可穿戴设备数据，生成健康风险评分",
        data_categories=["体检数据", "心率"],
        special_category_data=True,
        special_category_types=["健康数据"],
    )


def _citation_registry() -> CitationRegistry:
    registry = CitationRegistry()
    registry.register(CitationItem(
        citation_id="CIT-EU-GDPR-ART35-P01",
        source_id="EU-LAW-001",
        citation_type="law_article",
        title="GDPR (EU) 2016/679",
        article_no="段落3",
        authority_level="high",
        binding_force="mandatory",
        external_report_allowed=True,
    ))
    return registry


def _chapters() -> list[DPIAChapterContent]:
    return [
        DPIAChapterContent(
            chapter_no=1,
            title="DPIA 必要性判断",
            content="该处理活动属于大规模处理特殊类别数据 {{CIT-EU-GDPR-ART35-P01}}。",
            citations=["GDPR Art 35"],
            risk_level="high",
        ),
        DPIAChapterContent(
            chapter_no=2,
            title="缓解措施",
            content="需补充算法公平性审计报告。",
            citations=[],
            risk_level="medium",
        ),
    ]


# ── Step 5/6: adapter + golden snapshot ──

def test_dpia_document_ir_matches_golden_snapshot() -> None:
    document, reporting_registry = build_dpia_document_ir(
        task_id="task-golden",
        project_name="员工健康评估系统",
        chapters=_chapters(),
        citation_registry=_citation_registry(),
        generated_at=datetime(2026, 8, 8, tzinfo=timezone.utc),
        model="test-model",
    )

    actual = {
        "document": document.model_dump(mode="json"),
        "footnote_map": reporting_registry.footnote_map(),
    }
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert actual == expected


def test_dpia_document_ir_keeps_unregistered_marker_for_compiler_diagnostic() -> None:
    document, _ = build_dpia_document_ir(
        task_id="task-missing",
        project_name="员工健康评估系统",
        chapters=[DPIAChapterContent(
            chapter_no=1,
            title="风险结论",
            content="该活动须整改 {{CIT-EU-UNKNOWN-ART1-P01}}。",
            risk_level="high",
        )],
        citation_registry=CitationRegistry(),
        generated_at=datetime(2026, 8, 8, tzinfo=timezone.utc),
        model="test-model",
    )

    block = document.sections[0].blocks[0]
    assert block.citation_refs == ["CIT-EU-UNKNOWN-ART1-P01"]
    assert block.verification == "missing_evidence"


def test_dpia_adapter_does_not_leak_markers_into_block_text() -> None:
    document, _ = build_dpia_document_ir(
        task_id="task-clean",
        project_name="员工健康评估系统",
        chapters=_chapters(),
        citation_registry=_citation_registry(),
        generated_at=datetime(2026, 8, 8, tzinfo=timezone.utc),
        model="test-model",
    )
    for section in document.sections:
        for block in section.blocks:
            assert "{{CIT-" not in block.text
            assert not block.text.lstrip().startswith("#")


# ── Step 7/10: compiler gate + feature flag ──

def test_renderer_writes_document_ir_when_schema_first_is_enabled(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    renderer = DPIAReportRenderer(schema_first_enabled=True, model_name="test-model")

    outputs = renderer.render(
        task_id="task-schema-first",
        profile=_profile(),
        chapters=_chapters(),
        citation_registry=_citation_registry(),
    )

    payload = json.loads(Path(outputs["document_ir_json"]).read_text(encoding="utf-8"))
    assert payload["document_id"] == "dpia:task-schema-first"
    assert payload["report_type"] == "dpia"
    assert payload["diagnostics"] == []
    with ZipFile(outputs["zip"]) as bundle:
        assert "document_ir.json" in bundle.namelist()


def test_renderer_omits_document_ir_when_schema_first_is_disabled(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    renderer = DPIAReportRenderer()

    outputs = renderer.render(
        task_id="task-legacy",
        profile=_profile(),
        chapters=_chapters(),
        citation_registry=_citation_registry(),
    )

    assert "document_ir_json" not in outputs
    with ZipFile(outputs["zip"]) as bundle:
        assert "document_ir.json" not in bundle.namelist()


def test_renderer_blocks_unregistered_citations_when_schema_first_is_enabled(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    renderer = DPIAReportRenderer(schema_first_enabled=True)

    with pytest.raises(ValueError, match="CITATION_NOT_REGISTERED"):
        renderer.render(
            task_id="task-schema-first-invalid",
            profile=_profile(),
            chapters=_chapters(),
            citation_registry=CitationRegistry(),
        )


def test_production_footnote_shape_yields_claim_block_with_refs() -> None:
    """Regression: production content carries [N], not {{CIT-*}}.

    The generator converts markers to footnotes before the renderer sees the
    chapter, so an adapter that only recognises {{CIT-*}} would emit a
    ParagraphBlock with no citation_refs -- or raise, because [N] is itself a
    forbidden token in semantic block text. See status/check/ISSUE-reporting-001.
    """
    registry = _citation_registry()
    assert registry.assign_footnote_number("CIT-EU-GDPR-ART35-P01") == 1

    chapters = [DPIAChapterContent(
        chapter_no=1,
        title="DPIA 必要性判断",
        content="该处理活动属于大规模处理特殊类别数据 [1]。",
        citations=["GDPR Art 35"],
        risk_level="high",
    )]

    document, reporting_registry = build_dpia_document_ir(
        task_id="task-prod-shape",
        project_name="员工健康评估系统",
        chapters=chapters,
        citation_registry=registry,
        generated_at=datetime(2026, 8, 8, tzinfo=timezone.utc),
        model="test-model",
    )

    block = document.sections[0].blocks[0]
    assert type(block).__name__ == "ClaimBlock"
    assert block.citation_refs == ["CIT-EU-GDPR-ART35-P01"]
    assert "[1]" not in block.text
    assert block.text == "该处理活动属于大规模处理特殊类别数据。"

    compile_result = DocumentCompiler().compile(document, reporting_registry)
    assert compile_result.status == "success"
    assert not compile_result.diagnostics


def test_both_citation_shapes_produce_identical_document_ir() -> None:
    """Marker form and footnote form must be indistinguishable downstream."""
    def _build(content: str):
        registry = _citation_registry()
        registry.assign_footnote_number("CIT-EU-GDPR-ART35-P01")
        document, _ = build_dpia_document_ir(
            task_id="task-shape-parity",
            project_name="员工健康评估系统",
            chapters=[DPIAChapterContent(
                chapter_no=1,
                title="DPIA 必要性判断",
                content=content,
                citations=["GDPR Art 35"],
                risk_level="high",
            )],
            citation_registry=registry,
            generated_at=datetime(2026, 8, 8, tzinfo=timezone.utc),
            model="test-model",
        )
        return document.model_dump(mode="json")

    marker_form = _build("该处理活动属于大规模处理特殊类别数据 {{CIT-EU-GDPR-ART35-P01}}。")
    footnote_form = _build("该处理活动属于大规模处理特殊类别数据 [1]。")
    assert marker_form == footnote_form
