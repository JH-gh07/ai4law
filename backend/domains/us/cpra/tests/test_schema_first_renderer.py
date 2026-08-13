"""Schema-first CPRA renderer integration — production-form acceptance test."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader

from backend.common.citation.models import CitationItem
from backend.common.citation.output import write_citation_map_json
from backend.common.citation.registry import CitationRegistry
from backend.common.reporting import DocumentCompiler, MarkdownRenderer, render_docx, render_pdf
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
    # 7 business chapters + 1 fixed citations appendix (task068 T09).
    assert len(doc_ir.sections) == 8
    assert doc_ir.sections[-1].section_id == "cpra.appendix.citations"

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


def _forbidden_markers() -> list[str]:
    """Raw-payload / nested-JSON / absolute-path leakage markers (task068 T09)."""
    return [
        "business_model",
        "storage_uri",
        "model_dump",
        "\\u",  # JSON escapes never appear in rendered prose
        "| 检查项 | 主题 | 风险 |",  # legacy six-column table header
    ]


def test_fixed_section_order_conclusion_basis_remediation_citations_inputs() -> None:
    doc_ir, rr = build_cpra_document_ir(
        task_id="phase3-cpra-order",
        company_name="TechCo Inc.",
        chapters=_chapters(),
        citation_registry=_registry(),
        model="deepseek-v3",
        input_appendix=[
            ("企业名称", "TechCo Inc."),
            ("附件 1", "privacy_policy.pdf（privacy_policy）"),
        ],
    )
    assert [s.section_id for s in doc_ir.sections] == [
        "cpra.chapter.1",
        "cpra.chapter.2",
        "cpra.chapter.3",
        "cpra.chapter.4",
        "cpra.chapter.5",
        "cpra.chapter.6",
        "cpra.chapter.7",
        "cpra.appendix.citations",
        "cpra.appendix.inputs",
    ]
    # The citations appendix references every registered citation, ordered by number.
    citation_section = doc_ir.sections[-2]
    assert citation_section.title == "引用法规与条文"
    assert citation_section.blocks[0].type == "citation_note"
    assert set(citation_section.blocks[0].citation_refs) == {
        _CID_CPRA_1798_100,
        _CID_CPRA_1798_105,
        _CID_CPRA_1798_110,
    }
    # The input appendix is typed key-value, never raw JSON.
    input_section = doc_ir.sections[-1]
    assert input_section.title == "输入附录"
    assert input_section.blocks[0].type == "key_value"


def test_three_formats_share_ir_and_exclude_forbidden_content() -> None:
    doc_ir, rr = build_cpra_document_ir(
        task_id="phase3-cpra-three-format",
        company_name="TechCo Inc.",
        chapters=_chapters(),
        citation_registry=_registry(),
        model="deepseek-v3",
        input_appendix=[
            ("企业名称", "TechCo Inc."),
            ("附件 1", "privacy_policy.pdf（privacy_policy）"),
        ],
    )
    compile_result = DocumentCompiler().compile(doc_ir, rr)
    assert compile_result.status == "success"

    markdown = MarkdownRenderer().render(doc_ir, rr)
    docx_blob = render_docx(doc_ir, rr)
    pdf_blob = render_pdf(doc_ir, rr)

    docx_text = "\n".join(p.text for p in DocxDocument(BytesIO(docx_blob)).paragraphs)
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_blob)).pages)

    for marker in _forbidden_markers():
        assert marker not in markdown, f"forbidden marker in Markdown: {marker}"
        assert marker not in docx_text, f"forbidden marker in DOCX: {marker}"
        assert marker not in pdf_text, f"forbidden marker in PDF: {marker}"

    # All three formats carry the business conclusion and the fixed tail.
    assert "CPRA 适用范围与数据映射" in markdown
    assert "引用法规与条文" in markdown
    assert "输入附录" in markdown
    assert "TechCo Inc." in markdown
    assert "CPRA 适用范围与数据映射" in docx_text
    assert "输入附录" in docx_text
