"""Schema-first PIPIA adapter tests — golden snapshot + compiler gate + production shape."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

import pytest

from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry
from backend.common.reporting import DocumentCompiler
from backend.domains.cn.pipia.report_renderer import PIPIAReportRenderer
from backend.domains.cn.pipia.schema import (
    PIPIAAttachment,
    PIPIAChapter,
    PIPIACompanyProfile,
    PIPIAEmergencyPlan,
    PIPIAPersonalInfoScope,
    PIPIARequest,
    PIPIARightsProtection,
    PIPIATransferContext,
)
from backend.domains.cn.pipia.schema_first import build_pipia_document_ir

FIXTURES = Path(__file__).parent / "fixtures"
GOLDEN   = FIXTURES / "pipia_document_ir.golden.json"

CID = "CIT-CN-PIPL-ART39-P01"


def _registry() -> CitationRegistry:
    r = CitationRegistry()
    r.register(CitationItem(citation_id=CID, source_id="CN-LAW-003",
        citation_type="law_article", title="个人信息保护法", article_no="39",
        authority_level="high", binding_force="mandatory", external_report_allowed=True))
    r.assign_footnote_number(CID)
    return r


def _chapters() -> list[PIPIAChapter]:
    """Production-shape chapters for adapter-level tests (registry has [1] assigned)."""
    return [
        PIPIAChapter(chapter_no=1, title="出境活动基础信息",
                     content="本次出境活动依据个人信息保护法开展 [1]。",
                     citations=[], risk_level="HIGH"),
        PIPIAChapter(chapter_no=2, title="风险结论",
                     content="需补充境外接收方保护能力证明。",
                     citations=[], risk_level="MEDIUM"),
    ]


def _chapters_plain() -> list[PIPIAChapter]:
    """Plain-text chapters for renderer tests.

    PIPIA's service pipeline calls generate_chapter without a CitationRegistry
    and never calls convert_citation_markers, so production chapter content
    carries no {{CIT-*}} or [N] tokens. The renderer gate must pass on this
    plain-text shape.
    """
    return [
        PIPIAChapter(chapter_no=1, title="出境活动基础信息",
                     content="本次出境活动依据个人信息保护法相关规定开展。",
                     citations=[], risk_level="HIGH"),
        PIPIAChapter(chapter_no=2, title="风险结论",
                     content="需补充境外接收方保护能力证明。",
                     citations=[], risk_level="MEDIUM"),
    ]


def _payload() -> PIPIARequest:
    return PIPIARequest(
        route_type="scc_filing",
        company_profile=PIPIACompanyProfile(company_name="测试公司", company_uscc="91110000000000000X"),
        transfer_context=PIPIATransferContext(
            purpose="跨境客服",
            recipient_name="境外公司",
            recipient_country_region="Singapore",
            legal_basis="标准合同",
        ),
        personal_info_scope=PIPIAPersonalInfoScope(
            pi_categories=["姓名", "联系方式"],
            spi_categories=[],
            subject_volume=10000,
        ),
        rights_protection=PIPIARightsProtection(
            notice_mechanism="隐私政策",
            consent_mechanism="明示同意",
            dsar_channel="邮件",
            retention_policy="离职后1年",
        ),
        emergency_plan=PIPIAEmergencyPlan(
            incident_response_sla_hours=24,
            escalation_path="法务 → CEO",
        ),
        attachments=[PIPIAAttachment(
            file_role="scc_contract",
            file_name="scc.pdf",
            file_format="pdf",
            storage_uri="uploads/scc.pdf",
        )],
    )


def test_pipia_document_ir_matches_golden_snapshot() -> None:
    document, reporting_registry = build_pipia_document_ir(
        task_id="task-golden", company_name="测试公司",
        chapters=_chapters(), citation_registry=_registry(),
        generated_at=datetime(2026, 8, 8, tzinfo=timezone.utc), model="test-model",
    )
    actual = {"document": document.model_dump(mode="json"),
              "footnote_map": reporting_registry.footnote_map()}
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert actual == expected


def test_production_footnote_shape_yields_claim_block(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    reg = _registry()
    doc, rep = build_pipia_document_ir(
        task_id="t", company_name="测试公司", chapters=_chapters(),
        citation_registry=reg,
        generated_at=datetime(2026, 8, 8, tzinfo=timezone.utc), model="m",
    )
    block = doc.sections[0].blocks[0]
    assert type(block).__name__ == "ClaimBlock"
    assert block.citation_refs == [CID]
    assert "[1]" not in block.text
    cr = DocumentCompiler().compile(doc, rep)
    assert cr.status == "success"
    assert not cr.diagnostics


def test_both_citation_shapes_produce_identical_ir() -> None:
    def build(content):
        r = _registry()
        d, _ = build_pipia_document_ir(
            task_id="t", company_name="测试公司",
            chapters=[PIPIAChapter(chapter_no=1, title="T", content=content,
                                    citations=[], risk_level="HIGH")],
            citation_registry=r,
            generated_at=datetime(2026, 8, 8, tzinfo=timezone.utc), model="m",
        )
        return d.model_dump(mode="json")
    raw  = f"本次出境活动 {{{{{CID}}}}}。"
    prod = "本次出境活动 [1]。"
    assert build(raw) == build(prod)


def test_renderer_writes_document_ir_when_flag_enabled(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    renderer = PIPIAReportRenderer(schema_first_enabled=True, model_name="test-model")
    outputs = renderer.render(
        task_id="task-sf", payload=_payload(), chapters=_chapters_plain(),
        overall_risk_level="HIGH", attachment_notes=[],
    )
    data = json.loads(Path(outputs["document_ir_json"]).read_text(encoding="utf-8"))
    assert data["document_id"] == "pipia:task-sf"
    assert data["report_type"] == "pipia"
    assert data["diagnostics"] == []
    with ZipFile(outputs["zip"]) as z:
        assert "document_ir.json" in z.namelist()


def test_renderer_omits_document_ir_when_flag_disabled(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    renderer = PIPIAReportRenderer()
    outputs = renderer.render(
        task_id="task-leg", payload=_payload(), chapters=_chapters_plain(),
        overall_risk_level="HIGH", attachment_notes=[],
    )
    assert "document_ir_json" not in outputs
    with ZipFile(outputs["zip"]) as z:
        assert "document_ir.json" not in z.namelist()


def test_renderer_blocks_unregistered_citations_when_flag_enabled(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    renderer = PIPIAReportRenderer(schema_first_enabled=True)
    with pytest.raises(ValueError, match="CITATION_NOT_REGISTERED"):
        renderer.render(
            task_id="t", payload=_payload(),
            chapters=[PIPIAChapter(chapter_no=1, title="T",
                                    content=f"引用 {{{{{CID}}}}}。",
                                    citations=[], risk_level="HIGH")],
            overall_risk_level="HIGH", attachment_notes=[],
            # empty registry — will trigger compiler block
        )
