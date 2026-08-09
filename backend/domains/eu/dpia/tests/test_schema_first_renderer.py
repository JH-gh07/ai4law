"""Schema-first DPIA renderer integration — production-form acceptance test.

Companion to ``test_schema_first_adapter.py``.  Exercises the full
DPIAReportRenderer pipeline with production-shaped [N] footnotes, with
``schema_first_enabled`` both on and off.  Multi-chapter, multi-citation.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry
from backend.domains.eu.dpia.report_renderer import DPIAReportRenderer
from backend.domains.eu.dpia.schema import DPIAChapterContent, DPIAProjectProfile

# ── production-shaped fixtures ───────────────────────────────────────────────

_CID_GDPR_35 = "CIT-EU-GDPR-ART35-P01"
_CID_GDPR_5  = "CIT-EU-GDPR-ART5-P01"
_CID_GDPR_32 = "CIT-EU-GDPR-ART32-P01"


def _profile() -> DPIAProjectProfile:
    return DPIAProjectProfile(
        project_name="员工健康评估系统",
        project_goal="通过算法对员工健康数据进行分级评估，生成健康风险评分与干预建议",
        processing_flow_description="从可穿戴设备和体检系统收集心率/血氧/体检报告，经算法引擎生成评分",
        data_categories=["体检数据", "心率", "血氧", "健康风险评分"],
        special_category_data=True,
        special_category_types=["健康数据"],
    )


def _registry() -> CitationRegistry:
    reg = CitationRegistry()
    items = [
        (_CID_GDPR_35, "EU-LAW-001", "GDPR (EU) 2016/679", "35"),
        (_CID_GDPR_5,  "EU-LAW-001", "GDPR (EU) 2016/679", "5"),
        (_CID_GDPR_32, "EU-LAW-001", "GDPR (EU) 2016/679", "32"),
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


def _chapters() -> list[DPIAChapterContent]:
    """Production-shaped chapters with [N] footnotes, as produced by chapter_generator."""
    return [
        DPIAChapterContent(chapter_no=1, title="DPIA 必要性判断",
                           content=(
                               "员工健康评估系统处理大规模特殊类别数据（健康数据），"
                               "依据 GDPR 第 35 条，必须进行数据保护影响评估 [1]。"
                           ),
                           citations=["GDPR Art 35"], risk_level="high"),
        DPIAChapterContent(chapter_no=2, title="数据处理描述",
                           content=(
                               "系统从可穿戴设备收集心率与血氧数据，"
                               "从体检系统收集体检报告，依据 GDPR 第 5 条，"
                               "处理应遵循合法、公正、透明原则 [2]。"
                           ),
                           citations=["GDPR Art 5"], risk_level="high"),
        DPIAChapterContent(chapter_no=3, title="风险评估",
                           content=(
                               "主要风险包括：未经授权的健康数据访问 [1]、"
                               "算法偏差导致错误分级 [2]、数据传输过程中断 [3]。"
                           ),
                           citations=["GDPR Art 35", "GDPR Art 5", "GDPR Art 32"],
                           risk_level="high"),
        DPIAChapterContent(chapter_no=4, title="安全措施",
                           content=(
                               "依据 GDPR 第 32 条实施适当技术与组织措施 [3]："
                               "AES-256 加密、访问控制、定期安全审计。"
                           ),
                           citations=["GDPR Art 32"], risk_level="medium"),
        DPIAChapterContent(chapter_no=5, title="数据主体权利",
                           content=(
                               "保障数据主体访问权、更正权与删除权 [2]。"
                               "提供在线隐私门户供员工管理数据偏好。"
                           ),
                           citations=["GDPR Art 5"], risk_level="medium"),
        DPIAChapterContent(chapter_no=6, title="缓解措施",
                           content=(
                               "实施算法公平性审计 [1]、隐私影响最小化设计 [2]、"
                               "数据泄露应急响应计划 [3]。"
                           ),
                           citations=["GDPR Art 35", "GDPR Art 5", "GDPR Art 32"],
                           risk_level="medium"),
        DPIAChapterContent(chapter_no=7, title="结论与建议",
                           content=(
                               "在实施上述安全与组织措施的前提下，"
                               "该数据处理活动的残余风险为可接受水平 [1] [2] [3]。"
                           ),
                           citations=["GDPR Art 35", "GDPR Art 5", "GDPR Art 32"],
                           risk_level="low"),
    ]


# ── tests ────────────────────────────────────────────────────────────────────


def test_production_form_with_schema_first_generates_document_ir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    reg = _registry()
    chapters = _chapters()

    renderer = DPIAReportRenderer(schema_first_enabled=True, model_name="deepseek-v3")
    start_time = time.perf_counter()

    outputs = renderer.render(
        task_id="phase3-prod-new",
        profile=_profile(),
        chapters=chapters,
        citation_registry=reg,
    )

    elapsed_s = round(time.perf_counter() - start_time, 2)

    # ── document_ir.json ──
    ir_path = Path(outputs["document_ir_json"])
    assert ir_path.exists()
    ir_data = json.loads(ir_path.read_text(encoding="utf-8"))
    assert ir_data["document_id"] == "dpia:phase3-prod-new"
    assert ir_data["report_type"] == "dpia"
    assert ir_data["diagnostics"] == []
    assert len(ir_data["sections"]) == 7

    # ── every [N] captured as ClaimBlock citation_ref ──
    all_refs: list[str] = []
    claim_count = para_count = 0
    for sec in ir_data["sections"]:
        for blk in sec.get("blocks", []):
            if blk["type"] == "claim":
                claim_count += 1
                all_refs.extend(blk.get("citation_refs", []))
            elif blk["type"] == "paragraph":
                para_count += 1
    assert _CID_GDPR_35 in all_refs
    assert _CID_GDPR_5 in all_refs
    assert _CID_GDPR_32 in all_refs
    assert claim_count >= 5, f"expected >= 5 ClaimBlocks, got {claim_count}"

    # ── citation_map.json ──
    cmap_path = Path(outputs["citation_map_json"])
    assert cmap_path.exists()
    cmap = json.loads(cmap_path.read_text(encoding="utf-8"))
    footnote_map = cmap.get("footnote_map", {})
    assert len(footnote_map) == 3
    assert footnote_map["1"]["citation_id"] == _CID_GDPR_35
    assert footnote_map["2"]["citation_id"] == _CID_GDPR_5
    assert footnote_map["3"]["citation_id"] == _CID_GDPR_32

    # ── user artifacts ──
    for key in ("markdown", "zip"):
        assert key in outputs
        assert Path(outputs[key]).exists()
    markdown = Path(outputs["markdown"]).read_text(encoding="utf-8")
    assert "{{CIT-" not in markdown
    assert "CIT-EU-" not in markdown

    from zipfile import ZipFile
    with ZipFile(outputs["zip"]) as z:
        names = set(z.namelist())
    assert "document_ir.json" in names

    # ── citation identity: ir refs == footnote_map CIDs ──
    ir_cids = set(all_refs)
    map_cids = {v["citation_id"] for v in footnote_map.values()}
    assert ir_cids == map_cids, f"IR {sorted(ir_cids)} != map {sorted(map_cids)}"

    print(f"\n✅ DPIA prod-form: {elapsed_s}s, {claim_count} ClaimBlocks, {para_count} ParagraphBlocks, {len(all_refs)} total refs")


def test_production_form_without_schema_first_omits_document_ir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    renderer = DPIAReportRenderer(schema_first_enabled=False, model_name="legacy")
    outputs = renderer.render(
        task_id="phase3-prod-old",
        profile=_profile(),
        chapters=_chapters(),
        citation_registry=_registry(),
    )

    assert "document_ir_json" not in outputs
    from zipfile import ZipFile
    with ZipFile(outputs["zip"]) as z:
        assert "document_ir.json" not in z.namelist()
    assert Path(outputs["markdown"]).exists()

    print(f"\n✅ DPIA schema_first=False: document_ir.json correctly absent")


def test_production_form_block_count_invariant(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    reg = _registry()
    chapters = _chapters()

    def _counts():
        r = DPIAReportRenderer(schema_first_enabled=True, model_name="deepseek-v3")
        out = r.render(
            task_id="phase3-invariant",
            profile=_profile(),
            chapters=chapters,
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

    chapters = [DPIAChapterContent(
        chapter_no=1, title="概述",
        content="需要评估 [999]。",
        citations=[], risk_level="high",
    )]

    renderer = DPIAReportRenderer(schema_first_enabled=True, model_name="test")
    with pytest.raises(ValueError, match="CITATION_NOT_REGISTERED"):
        renderer.render(
            task_id="phase3-blocked",
            profile=_profile(),
            chapters=chapters,
            citation_registry=CitationRegistry(),
        )


def test_citation_map_footnote_count_matches_body_references(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    reg = _registry()
    chapters = _chapters()

    renderer = DPIAReportRenderer(schema_first_enabled=True, model_name="deepseek-v3")
    outputs = renderer.render(
        task_id="phase3-footnote-count",
        profile=_profile(),
        chapters=chapters,
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
        f"ir={sorted(ir_cids)} map={sorted(map_cids)} reg={sorted(reg_cids)}"
    )
    print(f"\n✅ DPIA citation identity: {len(ir_cids)} CIDs match across all 3 layers")
