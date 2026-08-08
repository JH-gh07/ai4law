"""Schema-first PIPIA renderer integration — production-form acceptance test."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry
from backend.domains.cn.pipia.report_renderer import PIPIAReportRenderer
from backend.domains.cn.pipia.schema import (
    PIPIAChapter,
    PIPIACompanyProfile,
    PIPIATransferContext,
    PIPIAPersonalInfoScope,
    PIPIARightsProtection,
    PIPIAEmergencyPlan,
    PIPIAAttachment,
    PIPIARequest,
)

_CID_PIPL_38 = "CIT-CN-PIPL-ART38-P01"
_CID_PIPL_39 = "CIT-CN-PIPL-ART39-P01"
_CID_PIPL_55 = "CIT-CN-PIPL-ART55-P01"


def _registry() -> CitationRegistry:
    reg = CitationRegistry()
    items = [
        (_CID_PIPL_38, "CN-LAW-003", "个人信息保护法", "38"),
        (_CID_PIPL_39, "CN-LAW-003", "个人信息保护法", "39"),
        (_CID_PIPL_55, "CN-LAW-003", "个人信息保护法", "55"),
    ]
    for cid, source, title, article in items:
        reg.register(CitationItem(
            citation_id=cid, source_id=source, citation_type="law_article",
            title=title, article_no=article, authority_level="high",
            binding_force="mandatory", external_report_allowed=True,
        ))
    for cid, _, _, _ in items:
        reg.assign_footnote_number(cid)
    return reg


def _payload() -> PIPIARequest:
    return PIPIARequest(
        route_type="scc_filing",
        company_profile=PIPIACompanyProfile(
            company_name="数规通科技（测试用）",
            company_uscc="91110000MA12345678",
            is_ciio=False,
            processing_person_count=500000,
            outbound_pi_count=200000,
            outbound_spi_count=5000,
            industry="互联网",
        ),
        transfer_context=PIPIATransferContext(
            purpose="客户服务与业务分析",
            recipient_name="Singapore Data Services Ltd.",
            recipient_country_region="新加坡",
            legal_basis="个人信息保护法第38条",
        ),
        personal_info_scope=PIPIAPersonalInfoScope(
            pi_categories=["姓名", "手机号", "邮箱", "地址"],
            spi_categories=["身份证号", "银行账号"],
            subject_volume=500000,
        ),
        rights_protection=PIPIARightsProtection(
            notice_mechanism="隐私政策弹窗+勾选同意",
            consent_mechanism="单独同意+明示同意",
            dsar_channel="在线申请+客服热线",
            retention_policy="业务终止后6个月删除",
        ),
        emergency_plan=PIPIAEmergencyPlan(
            incident_response_sla_hours=48,
            escalation_path="数据保护官→合规委员会→监管机构",
        ),
        attachments=[PIPIAAttachment(
            file_role="scc_contract",
            file_name="pipia_scc.pdf",
            file_format="pdf",
            storage_uri="storage://uploads/pipia_scc.pdf",
        )],
    )


def _chapters() -> list[PIPIAChapter]:
    return [
        PIPIAChapter(chapter_no=1, title="个人信息保护影响评估概述",
                     content=(
                         "数规通科技拟通过标准合同备案路径向新加坡传输个人信息 [1]。"
                         "涉及普通个人信息约20万人、敏感个人信息约5000人。"
                     ),
                     citations=["PIPL Art 38"], risk_level="MEDIUM"),
        PIPIAChapter(chapter_no=2, title="个人信息处理合法性基础",
                     content=(
                         "数据处理基于用户明示同意，符合PIPL第13条告知要求 [2]。"
                     ),
                     citations=["PIPL Art 39"], risk_level="MEDIUM"),
        PIPIAChapter(chapter_no=3, title="出境必要性评估",
                     content=(
                         "出境为客户服务核心业务必需，已通过最小必要原则审查。"
                     ),
                     citations=[], risk_level="LOW"),
        PIPIAChapter(chapter_no=4, title="接收方保护能力评估",
                     content=(
                         "新加坡接收方已通过PDPA合规认证，具备等效保护能力 [1] [3]。"
                         "根据PIPL第55条，境外接收方需接受中国监管机构监督 [3]。"
                     ),
                     citations=["PIPL Art 38", "PIPL Art 55"], risk_level="MEDIUM"),
        PIPIAChapter(chapter_no=5, title="个人信息主体权益保障",
                     content=(
                         "已建立完整的DSAR响应机制，符合PIPL第39条要求 [2] [1]。"
                     ),
                     citations=["PIPL Art 38", "PIPL Art 39"], risk_level="MEDIUM"),
        PIPIAChapter(chapter_no=6, title="安全措施与应急预案",
                     content=(
                         "AES-256加密传输、访问控制、48小时内应急响应 [3]。"
                     ),
                     citations=["PIPL Art 55"], risk_level="LOW"),
        PIPIAChapter(chapter_no=7, title="评估结论与建议",
                     content=(
                         "综合评估：个人信息出境风险可控 [1] [2] [3]。"
                         "建议补充年度合规审计。"
                     ),
                     citations=["PIPL Art 38", "PIPL Art 39", "PIPL Art 55"], risk_level="LOW"),
    ]


# ── tests ──────────────────────────────────────────────────────────────────────


def test_production_form_with_schema_first_generates_document_ir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # PIPIA template files do not exist yet; renderer falls back gracefully.
    reg = _registry()
    renderer = PIPIAReportRenderer(schema_first_enabled=True, model_name="deepseek-v3")
    start_time = time.perf_counter()

    outputs = renderer.render(
        task_id="phase3-pipia-prod-new",
        payload=_payload(),
        chapters=_chapters(),
        overall_risk_level="MEDIUM",
        attachment_notes=[],
        citation_registry=reg,
    )

    elapsed_s = round(time.perf_counter() - start_time, 2)

    ir_path = Path(outputs["document_ir_json"])
    assert ir_path.exists()
    ir_data = json.loads(ir_path.read_text(encoding="utf-8"))
    assert ir_data["document_id"] == "pipia:phase3-pipia-prod-new"
    assert ir_data["report_type"] == "pipia"
    assert ir_data["diagnostics"] == []
    assert len(ir_data["sections"]) == 7

    all_refs: list[str] = []
    claim_count = para_count = 0
    for sec in ir_data["sections"]:
        for blk in sec.get("blocks", []):
            if blk["type"] == "claim":
                claim_count += 1
                all_refs.extend(blk.get("citation_refs", []))
            elif blk["type"] == "paragraph":
                para_count += 1

    assert _CID_PIPL_38 in all_refs
    assert _CID_PIPL_39 in all_refs
    assert _CID_PIPL_55 in all_refs
    assert claim_count >= 4

    cmap_path = Path(outputs["citation_map_json"])
    assert cmap_path.exists()
    cmap = json.loads(cmap_path.read_text(encoding="utf-8"))
    footnote_map = cmap.get("footnote_map", {})
    assert len(footnote_map) == 3
    assert footnote_map["1"]["citation_id"] == _CID_PIPL_38
    assert footnote_map["2"]["citation_id"] == _CID_PIPL_39
    assert footnote_map["3"]["citation_id"] == _CID_PIPL_55

    for key in ("markdown", "docx", "pdf", "zip"):
        assert key in outputs
        assert Path(outputs[key]).exists()

    from zipfile import ZipFile
    with ZipFile(outputs["zip"]) as z:
        names = set(z.namelist())
    assert "document_ir.json" in names

    ir_cids = set(all_refs)
    map_cids = {v["citation_id"] for v in footnote_map.values()}
    reg_cids = {v.citation_id for v in reg.get_footnote_map().values()}
    assert ir_cids == map_cids == reg_cids

    print(f"\n✅ PIPIA prod-form: {elapsed_s}s, {claim_count} ClaimBlocks, {para_count} ParagraphBlocks")


def test_production_form_without_schema_first_omits_document_ir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    renderer = PIPIAReportRenderer(schema_first_enabled=False, model_name="legacy")
    outputs = renderer.render(
        task_id="phase3-pipia-prod-old",
        payload=_payload(),
        chapters=_chapters(),
        overall_risk_level="MEDIUM",
        attachment_notes=[],
        citation_registry=_registry(),
    )

    assert "document_ir_json" not in outputs
    from zipfile import ZipFile
    with ZipFile(outputs["zip"]) as z:
        assert "document_ir.json" not in z.namelist()
    assert Path(outputs["markdown"]).exists()


def test_production_form_block_count_invariant(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    reg = _registry()
    ch = _chapters()

    def _counts():
        r = PIPIAReportRenderer(schema_first_enabled=True, model_name="deepseek-v3")
        out = r.render(
            task_id="phase3-pipia-invariant",
            payload=_payload(), chapters=ch,
            overall_risk_level="MEDIUM", attachment_notes=[],
            citation_registry=reg,
        )
        ir = json.loads(Path(out["document_ir_json"]).read_text(encoding="utf-8"))
        counts = {}
        for s in ir["sections"]:
            for b in s["blocks"]:
                counts[b["type"]] = counts.get(b["type"], 0) + 1
        return counts

    assert _counts() == _counts()


def test_compiler_blocks_unregistered_citation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    chapters = [PIPIAChapter(
        chapter_no=1, title="概述",
        content="需要评估 [999]。",
        citations=[], risk_level="HIGH",
    )]

    renderer = PIPIAReportRenderer(schema_first_enabled=True, model_name="test")
    with pytest.raises(ValueError, match="CITATION_NOT_REGISTERED"):
        renderer.render(
            task_id="phase3-pipia-blocked",
            payload=_payload(),
            chapters=chapters,
            overall_risk_level="HIGH",
            attachment_notes=[],
            citation_registry=CitationRegistry(),
        )


def test_citation_map_footnote_count_matches_body_references(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    reg = _registry()
    renderer = PIPIAReportRenderer(schema_first_enabled=True, model_name="deepseek-v3")
    outputs = renderer.render(
        task_id="phase3-pipia-footnote-count",
        payload=_payload(), chapters=_chapters(),
        overall_risk_level="MEDIUM", attachment_notes=[],
        citation_registry=reg,
    )

    ir = json.loads(Path(outputs["document_ir_json"]).read_text(encoding="utf-8"))
    ir_cids: set[str] = set()
    for s in ir["sections"]:
        for b in s["blocks"]:
            if b["type"] == "claim":
                ir_cids.update(b.get("citation_refs", []))

    cmap = json.loads(Path(outputs["citation_map_json"]).read_text(encoding="utf-8"))
    map_cids = {v["citation_id"] for v in cmap.get("footnote_map", {}).values()}
    reg_cids = {v.citation_id for v in reg.get_footnote_map().values()}

    assert ir_cids == map_cids == reg_cids
    print(f"\n✅ PIPIA citation identity: {len(ir_cids)} CIDs across 3 layers")
