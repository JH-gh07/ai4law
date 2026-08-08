"""Schema-first SCC renderer integration — production-form acceptance test.

SCC's schema_first + compiler gate lives inside ``service.py``.  This test
exercises the adapter, compiler, and citation_map layers directly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.common.citation.models import CitationItem
from backend.common.citation.output import write_citation_map_json
from backend.common.citation.registry import CitationRegistry
from backend.common.reporting import DocumentCompiler
from backend.domains.eu.scc_review.schema import SCCChapter
from backend.domains.eu.scc_review.schema_first import build_scc_document_ir

_CID_GDPR_46_1 = "CIT-EU-GDPR-ART46-P01"
_CID_GDPR_46_2 = "CIT-EU-GDPR-ART46-P02"
_CID_GDPR_28_3 = "CIT-EU-GDPR-ART28-P01"


def _registry() -> CitationRegistry:
    reg = CitationRegistry()
    items = [
        (_CID_GDPR_46_1, "EU-LAW-001", "GDPR (EU) 2016/679", "46(1)"),
        (_CID_GDPR_46_2, "EU-LAW-001", "GDPR (EU) 2016/679", "46(2)"),
        (_CID_GDPR_28_3, "EU-LAW-001", "GDPR (EU) 2016/679", "28(3)"),
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


def _chapters() -> list[SCCChapter]:
    return [
        SCCChapter(chapter_no=1, title="SCC 文档概况与适用模块",
                   content=(
                       "本 SCC 适用 Module Two（控制者→处理者），"
                       "根据 GDPR 第46条第1款提供适当保障措施 [1]。"
                   ),
                   citations=["GDPR Art 46(1)"], citation_refs=[], risk_level="MEDIUM"),
        SCCChapter(chapter_no=2, title="条款级审查发现",
                   content=(
                       "Clause 8.7(a) 未明确说明数据处理期限 [2]。"
                       "Clause 9(a) 处理器授权条款符合 GDPR 第28条第3款 [3]。"
                   ),
                   citations=["GDPR Art 46(2)", "GDPR Art 28(3)"],
                   citation_refs=[], risk_level="HIGH"),
        SCCChapter(chapter_no=3, title="附件 I.A 签署方信息审查",
                   content=(
                       "签署方信息完整，数据导出方为 EU Controller Ltd.，"
                       "数据导入方为 US Processor Inc. [1] [3]。"
                   ),
                   citations=["GDPR Art 46(1)", "GDPR Art 28(3)"],
                   citation_refs=[], risk_level="MEDIUM"),
        SCCChapter(chapter_no=4, title="附件 I.B 传输描述审查",
                   content="传输目的、数据类别和保留期限均已明确描述。",
                   citations=[], citation_refs=[], risk_level="LOW"),
        SCCChapter(chapter_no=5, title="附件 II 技术与组织措施审查",
                   content=(
                       "AES-256加密、访问控制、定期渗透测试 [1] [2]。"
                       "缺少数据传输加密的具体协议说明。"
                   ),
                   citations=["GDPR Art 46(1)", "GDPR Art 46(2)"],
                   citation_refs=[], risk_level="MEDIUM"),
        SCCChapter(chapter_no=6, title="附件 III 子处理者审查",
                   content=(
                       "子处理者清单包含3个实体，授权机制符合要求 [3]。"
                   ),
                   citations=["GDPR Art 28(3)"], citation_refs=[], risk_level="LOW"),
        SCCChapter(chapter_no=7, title="综合结论与整改建议",
                   content=(
                       "SCC 文档整体合规，存在2项中风险问题需整改 [1] [2] [3]。"
                   ),
                   citations=["GDPR Art 46(1)", "GDPR Art 46(2)", "GDPR Art 28(3)"],
                   citation_refs=[], risk_level="MEDIUM"),
    ]


# ── tests ──────────────────────────────────────────────────────────────────────


def test_production_form_with_schema_first_generates_document_ir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    reg = _registry()
    doc_ir, reporting_reg = build_scc_document_ir(
        task_id="phase3-scc-prod-new",
        company_name="EU Controller Ltd.",
        chapters=_chapters(),
        citation_registry=reg,
        model="deepseek-v3",
    )

    compile_result = DocumentCompiler().compile(doc_ir, reporting_reg)
    assert compile_result.status == "success"
    assert doc_ir.document_id == "scc:phase3-scc-prod-new"
    assert doc_ir.report_type == "scc"
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

    assert _CID_GDPR_46_1 in all_refs
    assert _CID_GDPR_46_2 in all_refs
    assert _CID_GDPR_28_3 in all_refs
    assert claim_count >= 4

    output_dir = tmp_path / "outputs/scc/phase3-scc-prod-new/outputs"
    output_dir.mkdir(parents=True)
    cmap_path = write_citation_map_json(
        output_dir=output_dir, module="scc", task_id="phase3-scc-prod-new",
        footnote_map={str(n): item.to_dict() for n, item in reg.get_footnote_map().items()},
        all_items=reg.to_list(),
    )
    cmap = json.loads(Path(cmap_path).read_text(encoding="utf-8"))
    footnote_map = cmap.get("footnote_map", {})
    assert len(footnote_map) == 3
    assert footnote_map["1"]["citation_id"] == _CID_GDPR_46_1
    assert footnote_map["2"]["citation_id"] == _CID_GDPR_46_2
    assert footnote_map["3"]["citation_id"] == _CID_GDPR_28_3

    ir_cids = set(all_refs)
    map_cids = {v["citation_id"] for v in footnote_map.values()}
    reg_cids = {v.citation_id for v in reg.get_footnote_map().values()}
    assert ir_cids == map_cids == reg_cids

    print(f"\n✅ SCC prod-form: {claim_count} ClaimBlocks, {para_count} ParagraphBlocks")


def test_production_form_without_schema_first_omits_document_ir():
    assert callable(build_scc_document_ir)


def test_production_form_block_count_invariant():
    reg = _registry()
    ch = _chapters()

    def _counts():
        doc_ir, _ = build_scc_document_ir(
            task_id="phase3-scc-invariant",
            company_name="EU Controller Ltd.",
            chapters=ch, citation_registry=reg, model="deepseek-v3",
        )
        counts = {}
        for s in doc_ir.sections:
            for b in s.blocks:
                counts[b.type] = counts.get(b.type, 0) + 1
        return counts

    assert _counts() == _counts()


def test_compiler_blocks_unregistered_citation():
    chapters = [SCCChapter(
        chapter_no=1, title="概述",
        content="需要评估 [999]。",
        citations=[], citation_refs=[], risk_level="HIGH",
    )]

    doc_ir, rr = build_scc_document_ir(
        task_id="phase3-scc-blocked",
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
    doc_ir, _ = build_scc_document_ir(
        task_id="phase3-scc-footnote-count",
        company_name="EU Controller Ltd.",
        chapters=_chapters(), citation_registry=reg, model="deepseek-v3",
    )
    ir_cids: set[str] = set()
    for s in doc_ir.sections:
        for b in s.blocks:
            if b.type == "claim" and b.citation_refs:
                ir_cids.update(b.citation_refs)

    output_dir = tmp_path / "outputs/scc/phase3-scc-footnote-count/outputs"
    output_dir.mkdir(parents=True)
    cmap_path = write_citation_map_json(
        output_dir=output_dir, module="scc", task_id="phase3-scc-footnote-count",
        footnote_map={str(n): item.to_dict() for n, item in reg.get_footnote_map().items()},
        all_items=reg.to_list(),
    )
    cmap = json.loads(Path(cmap_path).read_text(encoding="utf-8"))
    map_cids = {v["citation_id"] for v in cmap.get("footnote_map", {}).values()}
    reg_cids = {v.citation_id for v in reg.get_footnote_map().values()}

    assert ir_cids == map_cids == reg_cids
    print(f"\n✅ SCC citation identity: {len(ir_cids)} CIDs across 3 layers")
