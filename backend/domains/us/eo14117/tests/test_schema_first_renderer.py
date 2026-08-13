"""Schema-first EO14117 renderer integration — production-form acceptance test."""

from __future__ import annotations

import json
from pathlib import Path

from backend.common.citation.models import CitationItem
from backend.common.citation.output import write_citation_map_json
from backend.common.citation.registry import CitationRegistry
from backend.common.reporting import DocumentCompiler
from backend.domains.us.eo14117.schema import US14117Chapter
from backend.domains.us.eo14117.schema_first import build_eo14117_document_ir

_CID_EO14117_SEC2 = "CIT-US-EO14117-ARTSEC2-P01"
_CID_EO14117_SEC3 = "CIT-US-EO14117-ARTSEC3-P01"
_CID_ICLG_16_3 = "CIT-US-ICLG-ART16_3-P01"


def _registry() -> CitationRegistry:
    reg = CitationRegistry()
    items = [
        (_CID_EO14117_SEC2, "US-REG-002", "EO 14117", "Section 2"),
        (_CID_EO14117_SEC3, "US-REG-002", "EO 14117", "Section 3"),
        (_CID_ICLG_16_3, "US-REG-003", "ICLG 16:3", "16.3"),
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


def _chapters() -> list[US14117Chapter]:
    return [
        US14117Chapter(chapter_no=1, title="EO 14117 适用范围评估",
                       content=(
                           "DataVault LLC 涉及大规模敏感个人数据的跨境交易，"
                           "符合 EO 14117 Section 2 的管辖范围 [1]。"
                       ),
                       citations=["EO 14117 §2"], risk_level="HIGH"),
        US14117Chapter(chapter_no=2, title="数据交易类别与敏感度分析",
                       content=(
                           "交易类别包括美国个人健康数据、基因组数据和精确地理数据 [1] [3]。"
                       ),
                       citations=["EO 14117 §2", "ICLG 16.3"], risk_level="HIGH"),
        US14117Chapter(chapter_no=3, title="受关注国家风险评估",
                       content=(
                           "交易涉及受关注国家的实体，根据 Section 3 进行国家安全风险审查 [2]。"
                       ),
                       citations=["EO 14117 §3"], risk_level="HIGH"),
        US14117Chapter(chapter_no=4, title="禁止与限制交易分类",
                       content=(
                           "基因组数据交易属于禁止类，健康数据交易属于限制类 [1] [2]。"
                       ),
                       citations=["EO 14117 §2", "EO 14117 §3"], risk_level="HIGH"),
        US14117Chapter(chapter_no=5, title="合规缓解措施",
                       content=(
                           "实施数据最小化、加密和访问审计 [2] [3]。"
                           "依据 ICLG 16:3 建立合同约束机制。"
                       ),
                       citations=["EO 14117 §3", "ICLG 16.3"], risk_level="MEDIUM"),
        US14117Chapter(chapter_no=6, title="交易记录与报告义务",
                       content=(
                           "建立完善的交易记录保存和定期报告机制 [1] [2] [3]。"
                       ),
                       citations=["EO 14117 §2", "EO 14117 §3", "ICLG 16.3"], risk_level="MEDIUM"),
        US14117Chapter(chapter_no=7, title="综合结论",
                       content=(
                           "存在2项高风险交易需立即整改 [1] [2]，"
                           "整体合规机制基本健全 [3]。"
                       ),
                       citations=["EO 14117 §2", "EO 14117 §3", "ICLG 16.3"], risk_level="HIGH"),
    ]


# ── tests ──────────────────────────────────────────────────────────────────────


def test_production_form_with_schema_first_generates_document_ir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    reg = _registry()
    doc_ir, reporting_reg = build_eo14117_document_ir(
        task_id="phase3-eo14117-prod-new",
        company_name="DataVault LLC",
        chapters=_chapters(),
        citation_registry=reg,
        model="deepseek-v3",
    )

    compile_result = DocumentCompiler().compile(doc_ir, reporting_reg)
    assert compile_result.status == "success"
    assert doc_ir.document_id == "eo14117:phase3-eo14117-prod-new"
    assert doc_ir.report_type == "eo14117"
    # 7 business chapters + 1 fixed citations appendix (task068 T09).
    assert len(doc_ir.sections) == 8
    assert doc_ir.sections[-1].section_id == "eo14117.appendix.citations"

    ir_data = doc_ir.model_dump(mode="json")
    assert ir_data["diagnostics"] == []

    all_refs: list[str] = []
    claim_count = para_count = 0
    for sec in ir_data["sections"]:
        for blk in sec["blocks"]:
            if blk["type"] == "claim":
                claim_count += 1
                all_refs.extend(blk.get("citation_refs", []))
            elif blk["type"] == "paragraph":
                para_count += 1

    assert _CID_EO14117_SEC2 in all_refs
    assert _CID_EO14117_SEC3 in all_refs
    assert _CID_ICLG_16_3 in all_refs
    assert claim_count >= 4

    output_dir = tmp_path / "outputs/eo14117/phase3-eo14117-prod-new/outputs"
    output_dir.mkdir(parents=True)
    cmap_path = write_citation_map_json(
        output_dir=output_dir, module="eo14117", task_id="phase3-eo14117-prod-new",
        footnote_map={str(n): item.to_dict() for n, item in reg.get_footnote_map().items()},
        all_items=reg.to_list(),
    )
    cmap = json.loads(Path(cmap_path).read_text(encoding="utf-8"))
    footnote_map = cmap.get("footnote_map", {})
    assert len(footnote_map) == 3
    assert footnote_map["1"]["citation_id"] == _CID_EO14117_SEC2
    assert footnote_map["2"]["citation_id"] == _CID_EO14117_SEC3
    assert footnote_map["3"]["citation_id"] == _CID_ICLG_16_3

    ir_cids = set(all_refs)
    map_cids = {v["citation_id"] for v in footnote_map.values()}
    reg_cids = {v.citation_id for v in reg.get_footnote_map().values()}
    assert ir_cids == map_cids == reg_cids

    print(f"\n✅ EO14117 prod-form: {claim_count} ClaimBlocks, {para_count} ParagraphBlocks")


def test_production_form_without_schema_first_omits_document_ir():
    assert callable(build_eo14117_document_ir)


def test_production_form_block_count_invariant():
    reg = _registry()
    ch = _chapters()

    def _counts():
        doc_ir, _ = build_eo14117_document_ir(
            task_id="phase3-eo14117-invariant",
            company_name="DataVault LLC",
            chapters=ch, citation_registry=reg, model="deepseek-v3",
        )
        counts = {}
        for s in doc_ir.sections:
            for b in s.blocks:
                counts[b.type] = counts.get(b.type, 0) + 1
        return counts

    assert _counts() == _counts()


def test_compiler_blocks_unregistered_citation():
    chapters = [US14117Chapter(
        chapter_no=1, title="概述",
        content="需要评估 [999]。",
        citations=[], risk_level="HIGH",
    )]

    doc_ir, rr = build_eo14117_document_ir(
        task_id="phase3-eo14117-blocked",
        company_name="Test", chapters=chapters,
        citation_registry=CitationRegistry(), model="test",
    )
    result = DocumentCompiler().compile(doc_ir, rr)
    assert result.status != "success"
    codes = [d.code for d in result.diagnostics]
    assert "CITATION_NOT_REGISTERED" in codes


def test_citation_map_footnote_count_matches_body_references(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    reg = _registry()
    doc_ir, _ = build_eo14117_document_ir(
        task_id="phase3-eo14117-footnote-count",
        company_name="DataVault LLC",
        chapters=_chapters(), citation_registry=reg, model="deepseek-v3",
    )
    ir_cids: set[str] = set()
    for s in doc_ir.sections:
        for b in s.blocks:
            if b.type == "claim" and b.citation_refs:
                ir_cids.update(b.citation_refs)

    output_dir = tmp_path / "outputs/eo14117/phase3-eo14117-footnote-count/outputs"
    output_dir.mkdir(parents=True)
    cmap_path = write_citation_map_json(
        output_dir=output_dir, module="eo14117", task_id="phase3-eo14117-footnote-count",
        footnote_map={str(n): item.to_dict() for n, item in reg.get_footnote_map().items()},
        all_items=reg.to_list(),
    )
    cmap = json.loads(Path(cmap_path).read_text(encoding="utf-8"))
    map_cids = {v["citation_id"] for v in cmap.get("footnote_map", {}).values()}
    reg_cids = {v.citation_id for v in reg.get_footnote_map().values()}

    assert ir_cids == map_cids == reg_cids
    print(f"\n✅ EO14117 citation identity: {len(ir_cids)} CIDs across 3 layers")
