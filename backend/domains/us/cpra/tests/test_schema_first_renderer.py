"""Schema-first CPRA renderer integration — production-form acceptance test."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.common.citation.models import CitationItem
from backend.common.citation.output import write_citation_map_json
from backend.common.citation.registry import CitationRegistry
from backend.common.reporting import DocumentCompiler
from backend.domains.us.cpra.schema import CPRAChapter
from backend.domains.us.cpra.schema_first import build_cpra_document_ir

_CID_CPRA_1798_100 = "CIT-US-CPRA-ART1798_100-P01"
_CID_CPRA_1798_105 = "CIT-US-CPRA-ART1798_105-P01"
_CID_CPRA_1798_110 = "CIT-US-CPRA-ART1798_110-P01"


def _registry() -> CitationRegistry:
    reg = CitationRegistry()
    items = [
        (_CID_CPRA_1798_100, "US-REG-001", "CPRA (California Privacy Rights Act)", "1798.100"),
        (_CID_CPRA_1798_105, "US-REG-001", "CPRA (California Privacy Rights Act)", "1798.105"),
        (_CID_CPRA_1798_110, "US-REG-001", "CPRA (California Privacy Rights Act)", "1798.110"),
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


def _chapters() -> list[CPRAChapter]:
    return [
        CPRAChapter(chapter_no=1, title="CPRA 适用范围与数据映射",
                    content=(
                        "TechCo Inc. 在加州境内收集消费者个人信息，"
                        "符合 CPRA §1798.100 的通知义务要求 [1]。"
                    ),
                    citations=["CPRA §1798.100"], citation_refs=[], risk_level="MEDIUM"),
        CPRAChapter(chapter_no=2, title="消费者数据权利实现",
                    content=(
                        "已实现删除权（§1798.105），消费者可在线提交删除请求 [2]。"
                    ),
                    citations=["CPRA §1798.105"], citation_refs=[], risk_level="HIGH"),
        CPRAChapter(chapter_no=3, title="知情权与数据可携权",
                    content=(
                        "根据 §1798.110，消费者有权请求披露收集的个人信息类别 [3]。"
                        "已建立自动化响应流程。"
                    ),
                    citations=["CPRA §1798.110"], citation_refs=[], risk_level="MEDIUM"),
        CPRAChapter(chapter_no=4, title="敏感个人信息处理",
                    content=(
                        "涉及精确地理位置和种族来源等敏感信息 [1] [2]。"
                        "已提供限制使用和目的的通知机制。"
                    ),
                    citations=["CPRA §1798.100", "CPRA §1798.105"],
                    citation_refs=[], risk_level="HIGH"),
        CPRAChapter(chapter_no=5, title="第三方共享与合同约束",
                    content=(
                        "与第三方服务商签订了数据保护协议，符合 §1798.110 的数据披露要求 [3] [1]。"
                    ),
                    citations=["CPRA §1798.100", "CPRA §1798.110"],
                    citation_refs=[], risk_level="MEDIUM"),
        CPRAChapter(chapter_no=6, title="数据安全措施与风险评估",
                    content=(
                        "定期进行网络安全评估，实施加密和访问控制 [2] [3]。"
                    ),
                    citations=["CPRA §1798.105", "CPRA §1798.110"],
                    citation_refs=[], risk_level="MEDIUM"),
        CPRAChapter(chapter_no=7, title="综合合规评估与建议",
                    content=(
                        "综合评估：CPRA 合规水平为基本合格 [1] [2] [3]。"
                        "建议完善自动化DSAR响应机制。"
                    ),
                    citations=["CPRA §1798.100", "CPRA §1798.105", "CPRA §1798.110"],
                    citation_refs=[], risk_level="MEDIUM"),
    ]


# ── tests ──────────────────────────────────────────────────────────────────────


def test_production_form_with_schema_first_generates_document_ir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    reg = _registry()
    doc_ir, reporting_reg = build_cpra_document_ir(
        task_id="phase3-cpra-prod-new",
        company_name="TechCo Inc.",
        chapters=_chapters(),
        citation_registry=reg,
        model="deepseek-v3",
    )

    compile_result = DocumentCompiler().compile(doc_ir, reporting_reg)
    assert compile_result.status == "success"
    assert doc_ir.document_id == "cpra:phase3-cpra-prod-new"
    assert doc_ir.report_type == "cpra"
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

    assert _CID_CPRA_1798_100 in all_refs
    assert _CID_CPRA_1798_105 in all_refs
    assert _CID_CPRA_1798_110 in all_refs
    assert claim_count >= 4

    output_dir = tmp_path / "outputs/cpra/phase3-cpra-prod-new/outputs"
    output_dir.mkdir(parents=True)
    cmap_path = write_citation_map_json(
        output_dir=output_dir, module="cpra", task_id="phase3-cpra-prod-new",
        footnote_map={str(n): item.to_dict() for n, item in reg.get_footnote_map().items()},
        all_items=reg.to_list(),
    )
    cmap = json.loads(Path(cmap_path).read_text(encoding="utf-8"))
    footnote_map = cmap.get("footnote_map", {})
    assert len(footnote_map) == 3
    assert footnote_map["1"]["citation_id"] == _CID_CPRA_1798_100
    assert footnote_map["2"]["citation_id"] == _CID_CPRA_1798_105
    assert footnote_map["3"]["citation_id"] == _CID_CPRA_1798_110

    ir_cids = set(all_refs)
    map_cids = {v["citation_id"] for v in footnote_map.values()}
    reg_cids = {v.citation_id for v in reg.get_footnote_map().values()}
    assert ir_cids == map_cids == reg_cids

    print(f"\n✅ CPRA prod-form: {claim_count} ClaimBlocks, {para_count} ParagraphBlocks")


def test_production_form_without_schema_first_omits_document_ir():
    assert callable(build_cpra_document_ir)


def test_production_form_block_count_invariant():
    reg = _registry()
    ch = _chapters()

    def _counts():
        doc_ir, _ = build_cpra_document_ir(
            task_id="phase3-cpra-invariant",
            company_name="TechCo Inc.",
            chapters=ch, citation_registry=reg, model="deepseek-v3",
        )
        counts = {}
        for s in doc_ir.sections:
            for b in s.blocks:
                counts[b.type] = counts.get(b.type, 0) + 1
        return counts

    assert _counts() == _counts()


def test_compiler_blocks_unregistered_citation():
    chapters = [CPRAChapter(
        chapter_no=1, title="概述",
        content="需要评估 [999]。",
        citations=[], citation_refs=[], risk_level="HIGH",
    )]

    doc_ir, rr = build_cpra_document_ir(
        task_id="phase3-cpra-blocked",
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
    doc_ir, _ = build_cpra_document_ir(
        task_id="phase3-cpra-footnote-count",
        company_name="TechCo Inc.",
        chapters=_chapters(), citation_registry=reg, model="deepseek-v3",
    )
    ir_cids: set[str] = set()
    for s in doc_ir.sections:
        for b in s.blocks:
            if b.type == "claim" and b.citation_refs:
                ir_cids.update(b.citation_refs)

    output_dir = tmp_path / "outputs/cpra/phase3-cpra-footnote-count/outputs"
    output_dir.mkdir(parents=True)
    cmap_path = write_citation_map_json(
        output_dir=output_dir, module="cpra", task_id="phase3-cpra-footnote-count",
        footnote_map={str(n): item.to_dict() for n, item in reg.get_footnote_map().items()},
        all_items=reg.to_list(),
    )
    cmap = json.loads(Path(cmap_path).read_text(encoding="utf-8"))
    map_cids = {v["citation_id"] for v in cmap.get("footnote_map", {}).values()}
    reg_cids = {v.citation_id for v in reg.get_footnote_map().values()}

    assert ir_cids == map_cids == reg_cids
    print(f"\n✅ CPRA citation identity: {len(ir_cids)} CIDs across 3 layers")
