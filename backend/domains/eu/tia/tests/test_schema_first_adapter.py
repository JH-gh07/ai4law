"""Schema-first TIA adapter tests — golden snapshot + compiler gate + production shape."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

import pytest

from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry
from backend.common.reporting import DocumentCompiler
from backend.domains.eu.tia.report_renderer import TIAReportRenderer
from backend.domains.eu.tia.schema import TIAChapter, TIARequest
from backend.domains.eu.tia.schema_first import build_tia_document_ir

FIXTURES = Path(__file__).parent / "fixtures"
GOLDEN = FIXTURES / "tia_document_ir.golden.json"

CID = "CIT-EU-GDPR-ART46-P01"


# ── shared fixtures ──

def _registry() -> CitationRegistry:
    r = CitationRegistry()
    r.register(CitationItem(
        citation_id=CID, source_id="EU-LAW-001",
        citation_type="law_article", title="GDPR (EU) 2016/679", article_no="段落3",
        authority_level="high", binding_force="mandatory", external_report_allowed=True,
    ))
    return r


def _chapters_golden() -> list[TIAChapter]:
    """Chapters that match the golden snapshot fixture."""
    return [
        TIAChapter(chapter_no=1, title="传输工具适用性判断",
                   content=f"本次传输依赖标准合同条款 [1]。",
                   citations=[], citation_refs=[], risk_level="HIGH"),
        TIAChapter(chapter_no=2, title="补充措施建议",
                   content="需实施端到端加密。",
                   citations=[], citation_refs=[], risk_level="MEDIUM"),
    ]


def _payload() -> TIARequest:
    return TIARequest.model_validate({
        "transfer_tool": "scc",
        "data_exporter_profile": "欧洲子公司",
        "data_importer_profile": "中国母公司",
        "third_country_assessment": "已评估第三国法律环境与政府访问风险。",
        "supplementary_measures": "传输加密、静态加密、访问控制。",
        "final_conclusion": "在补充措施到位的前提下可以传输。",
        "attachments": [{"file_role": "transfer_agreement", "file_name": "scc.pdf",
                         "file_format": "pdf", "storage_uri": "uploads/scc.pdf"}],
    })


# ── §12 Steps 5+6: adapter + golden snapshot ──

def test_tia_document_ir_matches_golden_snapshot() -> None:
    reg = _registry()
    reg.assign_footnote_number(CID)   # mirrors chapter_generator

    document, reporting_registry = build_tia_document_ir(
        task_id="task-golden",
        exporter_profile="欧洲子公司",
        chapters=_chapters_golden(),
        citation_registry=reg,
        generated_at=datetime(2026, 8, 8, tzinfo=timezone.utc),
        model="test-model",
    )

    actual = {
        "document": document.model_dump(mode="json"),
        "footnote_map": reporting_registry.footnote_map(),
    }
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert actual == expected


def test_tia_adapter_strips_markers_from_block_text() -> None:
    reg = _registry()
    reg.assign_footnote_number(CID)

    document, _ = build_tia_document_ir(
        task_id="t", exporter_profile="E",
        chapters=[TIAChapter(chapter_no=1, title="T",
                             content="本次传输依赖标准合同条款 [1]。",
                             citations=[], citation_refs=[], risk_level="HIGH")],
        citation_registry=reg, model="m",
        generated_at=datetime(2026, 8, 8, tzinfo=timezone.utc),
    )
    block = document.sections[0].blocks[0]
    assert "{{" not in block.text
    assert "[1]" not in block.text
    assert not block.text.lstrip().startswith("#")


# ── ISSUE-reporting-001 regression: production [N] shape ──

def test_production_footnote_shape_resolves_to_claim_block() -> None:
    """Chapter content from generator carries [N], not {{CIT-*}}.  Must not raise."""
    reg = _registry()
    reg.assign_footnote_number(CID)   # production: generator already assigned [1]

    document, reporting_registry = build_tia_document_ir(
        task_id="task-prod", exporter_profile="欧洲子公司",
        chapters=[TIAChapter(chapter_no=1, title="传输工具",
                             content=f"本次传输依赖标准合同条款 [1]。",
                             citations=[], citation_refs=[], risk_level="HIGH")],
        citation_registry=reg,
        generated_at=datetime(2026, 8, 8, tzinfo=timezone.utc), model="m",
    )

    block = document.sections[0].blocks[0]
    assert type(block).__name__ == "ClaimBlock"
    assert block.citation_refs == [CID]
    assert "[1]" not in block.text

    compile_result = DocumentCompiler().compile(document, reporting_registry)
    assert compile_result.status == "success"
    assert not compile_result.diagnostics


def test_both_citation_shapes_produce_identical_ir() -> None:
    def build(content):
        reg = _registry()
        reg.assign_footnote_number(CID)
        doc, _ = build_tia_document_ir(
            task_id="t", exporter_profile="E",
            chapters=[TIAChapter(chapter_no=1, title="T", content=content,
                                  citations=[], citation_refs=[], risk_level="HIGH")],
            citation_registry=reg, model="m",
            generated_at=datetime(2026, 8, 8, tzinfo=timezone.utc),
        )
        return doc.model_dump(mode="json")

    raw = f"本次传输依赖标准合同条款 {{{{{CID}}}}}。"
    prod = "本次传输依赖标准合同条款 [1]。"
    assert build(raw) == build(prod)


# ── §12 Step 7+10: renderer gate + feature flag ──

def test_renderer_writes_document_ir_when_flag_enabled(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    renderer = TIAReportRenderer(schema_first_enabled=True, model_name="test-model")
    reg = _registry()
    reg.assign_footnote_number(CID)

    outputs = renderer.render(
        task_id="task-schema-first",
        payload=_payload(),
        chapters=_chapters_golden(),
        attachment_notes=[],
        citation_registry=reg,
    )

    payload = json.loads(Path(outputs["document_ir_json"]).read_text(encoding="utf-8"))
    assert payload["document_id"] == "tia:task-schema-first"
    assert payload["report_type"] == "tia"
    assert payload["diagnostics"] == []

    with ZipFile(outputs["zip"]) as bundle:
        assert "document_ir.json" in bundle.namelist()


def test_renderer_omits_document_ir_when_flag_disabled(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    renderer = TIAReportRenderer()   # default: schema_first_enabled=False
    reg = _registry()

    outputs = renderer.render(
        task_id="task-legacy",
        payload=_payload(),
        chapters=_chapters_golden(),
        attachment_notes=[],
        citation_registry=reg,
    )

    assert "document_ir_json" not in outputs
    with ZipFile(outputs["zip"]) as bundle:
        assert "document_ir.json" not in bundle.namelist()


def test_renderer_blocks_unregistered_citations_when_flag_enabled(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    renderer = TIAReportRenderer(schema_first_enabled=True)

    with pytest.raises(ValueError, match="CITATION_NOT_REGISTERED"):
        renderer.render(
            task_id="task-bad",
            payload=_payload(),
            chapters=[TIAChapter(chapter_no=1, title="T",
                                  content=f"引用 {{{{{CID}}}}}。",
                                  citations=[], citation_refs=[], risk_level="HIGH")],
            attachment_notes=[],
            citation_registry=CitationRegistry(),   # empty registry
        )
