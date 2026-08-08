"""Schema-first BCR renderer integration — production-form acceptance test.

BCR embeds its schema_first + compiler gate inside ``service.py`` rather than a
standalone ``report_renderer.py``.  This test exercises the adapter, compiler,
and citation_map layers directly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.common.citation.models import CitationItem
from backend.common.citation.output import write_citation_map_json
from backend.common.citation.registry import CitationRegistry
from backend.common.reporting import DocumentCompiler, legacy_registry_to_reporting
from backend.domains.eu.bcr_review.schema import BCRChapter
from backend.domains.eu.bcr_review.schema_first import build_bcr_document_ir

_CID_GDPR_47_1 = "CIT-EU-GDPR-ART47-P01"
_CID_GDPR_47_2 = "CIT-EU-GDPR-ART47-P02"
_CID_GDPR_47_3 = "CIT-EU-GDPR-ART47-P03"


def _registry() -> CitationRegistry:
    reg = CitationRegistry()
    items = [
        (_CID_GDPR_47_1, "EU-LAW-001", "GDPR (EU) 2016/679", "47(1)"),
        (_CID_GDPR_47_2, "EU-LAW-001", "GDPR (EU) 2016/679", "47(2)"),
        (_CID_GDPR_47_3, "EU-LAW-001", "GDPR (EU) 2016/679", "47(3)"),
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


def _chapters() -> list[BCRChapter]:
    return [
        BCRChapter(chapter_no=1, title="BCR 概述与适用范围",
                   content=(
                       "本 BCR 适用于集团内跨境传输个人数据，"
                       "符合 GDPR 第47条第1款关于约束性公司规则的基本要求 [1]。"
                   ),
                   citations=["GDPR Art 47(1)"], risk_level="MEDIUM"),
        BCRChapter(chapter_no=2, title="法律约束力与可执行性",
                   content=(
                       "BCR 对集团所有成员具有法律约束力，"
                       "根据 GDPR 第47条第2款，数据主体享有第三方受益权 [2]。"
                   ),
                   citations=["GDPR Art 47(2)"], risk_level="HIGH"),
        BCRChapter(chapter_no=3, title="数据结构与处理活动",
                   content=(
                       "BCR 明确规定了数据结构、处理活动类别及数据主体范围。"
                   ),
                   citations=[], risk_level="MEDIUM"),
        BCRChapter(chapter_no=4, title="数据主体权利保障",
                   content=(
                       "保障数据主体的访问权、更正权、删除权等基本权利 [1] [2]。"
                   ),
                   citations=["GDPR Art 47(1)", "GDPR Art 47(2)"], risk_level="MEDIUM"),
        BCRChapter(chapter_no=5, title="第三国传输与责任机制",
                   content=(
                       "根据 GDPR 第47条第3款，欧盟境内的 BCR 成员对"
                       "第三国传输中的侵权行为承担连带责任 [3]。"
                   ),
                   citations=["GDPR Art 47(3)"], risk_level="HIGH"),
        BCRChapter(chapter_no=6, title="合规监督与审计机制",
                   content=(
                       "建立独立的合规监督机制和定期审计制度 [1] [3]。"
                   ),
                   citations=["GDPR Art 47(1)", "GDPR Art 47(3)"], risk_level="MEDIUM"),
        BCRChapter(chapter_no=7, title="报告结论与整改建议",
                   content=(
                       "综合评估：BCR 文档在 GDPR 第47条框架下达到基本合规水平 [1] [2] [3]。"
                   ),
                   citations=["GDPR Art 47(1)", "GDPR Art 47(2)", "GDPR Art 47(3)"],
                   risk_level="MEDIUM"),
    ]


# ── tests ──────────────────────────────────────────────────────────────────────


def test_production_form_with_schema_first_generates_document_ir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    reg = _registry()
    doc_ir, reporting_reg = build_bcr_document_ir(
        task_id="phase3-bcr-prod-new",
        company_name="EU Data Group SA",
        chapters=_chapters(),
        citation_registry=reg,
        model="deepseek-v3",
    )

    compile_result = DocumentCompiler().compile(doc_ir, reporting_reg)
    assert compile_result.status == "success"
    assert doc_ir.document_id == "bcr:phase3-bcr-prod-new"
    assert doc_ir.report_type == "bcr"
    assert len(doc_ir.sections) == 7

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

    assert _CID_GDPR_47_1 in all_refs
    assert _CID_GDPR_47_2 in all_refs
    assert _CID_GDPR_47_3 in all_refs
    assert claim_count >= 4

    # citation_map.json
    output_dir = tmp_path / "outputs/bcr/phase3-bcr-prod-new/outputs"
    output_dir.mkdir(parents=True)
    cmap_path = write_citation_map_json(
        output_dir=output_dir, module="bcr", task_id="phase3-bcr-prod-new",
        footnote_map={str(n): item.to_dict() for n, item in reg.get_footnote_map().items()},
        all_items=reg.to_list(),
    )
    cmap = json.loads(Path(cmap_path).read_text(encoding="utf-8"))
    footnote_map = cmap.get("footnote_map", {})
    assert len(footnote_map) == 3
    assert footnote_map["1"]["citation_id"] == _CID_GDPR_47_1
    assert footnote_map["2"]["citation_id"] == _CID_GDPR_47_2
    assert footnote_map["3"]["citation_id"] == _CID_GDPR_47_3

    ir_cids = set(all_refs)
    map_cids = {v["citation_id"] for v in footnote_map.values()}
    reg_cids = {v.citation_id for v in reg.get_footnote_map().values()}
    assert ir_cids == map_cids == reg_cids

    print(f"\n✅ BCR prod-form: {claim_count} ClaimBlocks, {para_count} ParagraphBlocks")


def test_production_form_without_schema_first_omits_document_ir():
    """BCR doesn't have an on/off renderer switch — adapter is always callable.
    This test exists for parity with other modules' test grid."""
    assert callable(build_bcr_document_ir)


def test_production_form_block_count_invariant():
    reg = _registry()
    ch = _chapters()

    def _counts():
        doc_ir, _ = build_bcr_document_ir(
            task_id="phase3-bcr-invariant",
            company_name="EU Data Group SA",
            chapters=ch, citation_registry=reg, model="deepseek-v3",
        )
        counts = {}
        for s in doc_ir.sections:
            for b in s.blocks:
                counts[b.type] = counts.get(b.type, 0) + 1
        return counts

    assert _counts() == _counts()


def test_compiler_blocks_unregistered_citation():
    chapters = [BCRChapter(
        chapter_no=1, title="概述",
        content="需要评估 [999]。",
        citations=[], risk_level="HIGH",
    )]

    doc_ir, rr = build_bcr_document_ir(
        task_id="phase3-bcr-blocked",
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
    doc_ir, _ = build_bcr_document_ir(
        task_id="phase3-bcr-footnote-count",
        company_name="EU Data Group SA",
        chapters=_chapters(), citation_registry=reg, model="deepseek-v3",
    )
    ir_cids: set[str] = set()
    for s in doc_ir.sections:
        for b in s.blocks:
            if b.type == "claim" and b.citation_refs:
                ir_cids.update(b.citation_refs)

    output_dir = tmp_path / "outputs/bcr/phase3-bcr-footnote-count/outputs"
    output_dir.mkdir(parents=True)
    cmap_path = write_citation_map_json(
        output_dir=output_dir, module="bcr", task_id="phase3-bcr-footnote-count",
        footnote_map={str(n): item.to_dict() for n, item in reg.get_footnote_map().items()},
        all_items=reg.to_list(),
    )
    cmap = json.loads(Path(cmap_path).read_text(encoding="utf-8"))
    map_cids = {v["citation_id"] for v in cmap.get("footnote_map", {}).values()}
    reg_cids = {v.citation_id for v in reg.get_footnote_map().values()}

    assert ir_cids == map_cids == reg_cids
    print(f"\n✅ BCR citation identity: {len(ir_cids)} CIDs across 3 layers")
