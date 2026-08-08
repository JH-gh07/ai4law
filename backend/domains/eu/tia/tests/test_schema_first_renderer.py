"""Schema-first TIA renderer integration — production-form acceptance test.

Exercises the full TIAReportRenderer pipeline with production-shaped [N]
footnotes, multi-chapter, multi-citation, with ``schema_first_enabled``
both on and off.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry
from backend.domains.eu.tia.report_renderer import TIAReportRenderer
from backend.domains.eu.tia.schema import TIAChapter, TIAAttachment, TIARequest

# ── production-shaped fixtures ───────────────────────────────────────────────

_CID_GDPR_44 = "CIT-EU-GDPR-ART44-P01"
_CID_GDPR_45 = "CIT-EU-GDPR-ART45-P01"
_CID_GDPR_46 = "CIT-EU-GDPR-ART46-P01"


def _registry() -> CitationRegistry:
    reg = CitationRegistry()
    items = [
        (_CID_GDPR_44, "EU-LAW-001", "GDPR (EU) 2016/679", "44"),
        (_CID_GDPR_45, "EU-LAW-001", "GDPR (EU) 2016/679", "45"),
        (_CID_GDPR_46, "EU-LAW-001", "GDPR (EU) 2016/679", "46"),
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


def _payload() -> TIARequest:
    return TIARequest(
        transfer_tool="scc",
        data_exporter_profile="EU Exporter GmbH",
        data_importer_profile="US Importer Inc.",
        third_country_assessment="美国存在政府机构大规模访问风险(如 FISA 702)",
        supplementary_measures="端到端加密(AES-256) + HSM密钥管理 + 定期审计",
        final_conclusion="在补充措施有效实施的前提下，SCC可作为合法传输工具",
        attachments=[TIAAttachment(
            file_role="transfer_agreement",
            file_name="scc_agreement.pdf",
            file_format="pdf",
            storage_uri="storage://uploads/scc_agreement.pdf",
        )],
    )


def _chapters() -> list[TIAChapter]:
    """Production-shaped [N] footnote chapters after chapter_generator output."""
    return [
        TIAChapter(chapter_no=1, title="传输概述与法律框架",
                   content=(
                       "EU Exporter GmbH 拟通过 SCC 向美国传输客户关系管理数据。"
                       "根据 GDPR 第 44 条，个人数据向第三国传输须确保保护水平不降低 [1]。"
                   ),
                   citations=["GDPR Art 44"], citation_refs=[], risk_level="HIGH"),
        TIAChapter(chapter_no=2, title="第三国法律环境评估",
                   content=(
                       "美国法律环境存在大规模政府访问风险(FISA 702)。"
                       "根据 GDPR 第 45 条充分性认定标准 [2]，"
                       "美国尚未获得充分性认定。"
                   ),
                   citations=["GDPR Art 45"], citation_refs=[], risk_level="HIGH"),
        TIAChapter(chapter_no=3, title="传输工具适当性分析",
                   content=(
                       "SCC(2021版)提供合同保障，根据 GDPR 第 46 条适当保障措施 [3]，"
                       "可弥补第三国保护水平不足。"
                   ),
                   citations=["GDPR Art 46"], citation_refs=[], risk_level="MEDIUM"),
        TIAChapter(chapter_no=4, title="补充措施评估",
                   content=(
                       "端到端加密 + HSM密钥管理确保美国云服务商无法解密数据 [1] [3]。"
                       "定期独立审计验证措施有效性。"
                   ),
                   citations=["GDPR Art 44", "GDPR Art 46"], citation_refs=[], risk_level="MEDIUM"),
        TIAChapter(chapter_no=5, title="残余风险分析",
                   content=(
                       "即使有补充措施，元数据和流量模式仍可能被截获 [1] [2]。"
                       "残余风险为低至中等。"
                   ),
                   citations=["GDPR Art 44", "GDPR Art 45"], citation_refs=[], risk_level="LOW"),
        TIAChapter(chapter_no=6, title="结论与建议",
                   content=(
                       "在端到端加密、HSM密钥管理和定期审计有效实施的前提下 [3]，"
                       "SCC+补充措施可保障欧盟个人数据保护水平 [1] [2]。"
                   ),
                   citations=["GDPR Art 44", "GDPR Art 45", "GDPR Art 46"],
                   citation_refs=[], risk_level="LOW"),
    ]


# ── tests ────────────────────────────────────────────────────────────────────


def test_production_form_with_schema_first_generates_document_ir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    reg = _registry()
    renderer = TIAReportRenderer(schema_first_enabled=True, model_name="deepseek-v3")
    start_time = time.perf_counter()

    outputs = renderer.render(
        task_id="phase3-tia-prod-new",
        payload=_payload(),
        chapters=_chapters(),
        attachment_notes=[],
        citation_registry=reg,
    )

    elapsed_s = round(time.perf_counter() - start_time, 2)

    # ── document_ir.json ──
    ir_path = Path(outputs["document_ir_json"])
    assert ir_path.exists()
    ir_data = json.loads(ir_path.read_text(encoding="utf-8"))
    assert ir_data["document_id"] == "tia:phase3-tia-prod-new"
    assert ir_data["report_type"] == "tia"
    assert ir_data["diagnostics"] == []
    assert len(ir_data["sections"]) == 6

    # ── [N] citations captured ──
    all_refs: list[str] = []
    claim_count = para_count = 0
    for sec in ir_data["sections"]:
        for blk in sec.get("blocks", []):
            if blk["type"] == "claim":
                claim_count += 1
                all_refs.extend(blk.get("citation_refs", []))
            elif blk["type"] == "paragraph":
                para_count += 1

    assert _CID_GDPR_44 in all_refs
    assert _CID_GDPR_45 in all_refs
    assert _CID_GDPR_46 in all_refs
    assert claim_count >= 4, f"expected >=4 ClaimBlocks, got {claim_count}"

    # ── citation_map.json ──
    cmap_path = Path(outputs["citation_map_json"])
    assert cmap_path.exists()
    cmap = json.loads(cmap_path.read_text(encoding="utf-8"))
    footnote_map = cmap.get("footnote_map", {})
    assert len(footnote_map) == 3
    assert footnote_map["1"]["citation_id"] == _CID_GDPR_44
    assert footnote_map["2"]["citation_id"] == _CID_GDPR_45
    assert footnote_map["3"]["citation_id"] == _CID_GDPR_46

    # ── user artifacts ──
    for key in ("markdown", "docx", "pdf", "zip"):
        assert key in outputs
        assert Path(outputs[key]).exists()

    from zipfile import ZipFile
    with ZipFile(outputs["zip"]) as z:
        names = set(z.namelist())
    assert "document_ir.json" in names

    # ── citation identity across layers ──
    ir_cids = set(all_refs)
    map_cids = {v["citation_id"] for v in footnote_map.values()}
    reg_cids = {v.citation_id for v in reg.get_footnote_map().values()}
    assert ir_cids == map_cids == reg_cids, (
        f"ir={sorted(ir_cids)} map={sorted(map_cids)} reg={sorted(reg_cids)}"
    )

    print(f"\n✅ TIA prod-form: {elapsed_s}s, {claim_count} ClaimBlocks, {para_count} ParagraphBlocks")


def test_production_form_without_schema_first_omits_document_ir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    renderer = TIAReportRenderer(schema_first_enabled=False, model_name="legacy")
    outputs = renderer.render(
        task_id="phase3-tia-prod-old",
        payload=_payload(),
        chapters=_chapters(),
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
        r = TIAReportRenderer(schema_first_enabled=True, model_name="deepseek-v3")
        out = r.render(
            task_id="phase3-tia-invariant",
            payload=_payload(),
            chapters=ch,
            attachment_notes=[],
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

    chapters = [TIAChapter(
        chapter_no=1, title="概述",
        content="需要评估 [999]。",
        citations=[], citation_refs=[], risk_level="HIGH",
    )]

    renderer = TIAReportRenderer(schema_first_enabled=True, model_name="test")
    with pytest.raises(ValueError, match="CITATION_NOT_REGISTERED"):
        renderer.render(
            task_id="phase3-tia-blocked",
            payload=_payload(),
            chapters=chapters,
            attachment_notes=[],
            citation_registry=CitationRegistry(),
        )


def test_citation_map_footnote_count_matches_body_references(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    reg = _registry()
    renderer = TIAReportRenderer(schema_first_enabled=True, model_name="deepseek-v3")
    outputs = renderer.render(
        task_id="phase3-tia-footnote-count",
        payload=_payload(),
        chapters=_chapters(),
        attachment_notes=[],
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

    assert ir_cids == map_cids == reg_cids, (
        f"tia ir={sorted(ir_cids)} map={sorted(map_cids)} reg={sorted(reg_cids)}"
    )
    print(f"\n✅ TIA citation identity: {len(ir_cids)} CIDs across 3 layers")
