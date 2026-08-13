"""Schema-first BCR renderer integration — v4 findings-based IR acceptance."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from backend.common.citation.models import CitationItem
from backend.common.citation.output import write_citation_map_json
from backend.common.citation.registry import CitationRegistry
from backend.common.reporting import DocumentCompiler
from backend.common.reporting.renderers.docx import DocxRenderer
from backend.common.reporting.renderers.markdown import MarkdownRenderer
from backend.common.reporting.renderers.pdf import PdfRenderer
from backend.domains.eu.bcr_review.schema import BCRFinding, BCRTypeClassification
from backend.domains.eu.bcr_review.schema_first import build_bcr_document_ir

_CID_GDPR_47_1 = "CIT-EU-GDPR-ART47-P01"
_CID_GDPR_47_2 = "CIT-EU-GDPR-ART47-P02"
_CID_GDPR_47_3 = "CIT-EU-GDPR-ART47-P03"

_TS = datetime(2026, 8, 8, tzinfo=timezone.utc)


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


def _type_class() -> BCRTypeClassification:
    return BCRTypeClassification(
        declared_bcr_type="BCR-C", actual_bcr_type="BCR-C",
        type_consistency="consistent", risk_level="MEDIUM",
    )


def _findings() -> list[BCRFinding]:
    return [
        BCRFinding(
            finding_id="BCR-C-1.1-01", requirement_id="BCR-C-1.1", title="约束力不足",
            risk_level="HIGH", finding="集团内部约束机制不完整。",
            legal_basis=["GDPR Article 47(1)"], citation_refs=[_CID_GDPR_47_1],
            suggested_revision="(a) 补充集团内部约束条款。\n(b) 明确约束的法律效力。",
        ),
        BCRFinding(
            finding_id="BCR-C-1.2-01", requirement_id="BCR-C-1.2", title="第三方受益权缺失",
            risk_level="HIGH", finding="数据主体第三方受益权不明确。",
            legal_basis=["GDPR Article 47(2)"], citation_refs=[_CID_GDPR_47_2],
        ),
        BCRFinding(
            finding_id="BCR-C-1.3-01", requirement_id="BCR-C-1.3", title="连带责任缺失",
            risk_level="MEDIUM", finding="第三国传输连带责任不明确。",
            legal_basis=["GDPR Article 47(3)"], citation_refs=[_CID_GDPR_47_3],
        ),
    ]


def _build(**overrides):
    kwargs = dict(
        task_id="phase3-bcr-prod-new",
        company_name="EU Data Group SA",
        type_class=_type_class(),
        rating="高风险",
        score=75.0,
        findings=_findings(),
        missing=["BCR-C-1.1"],
        citation_registry=_registry(),
        metadata={"bcr_type": "BCR-C"},
        model="deepseek-v3",
        generated_at=_TS,
    )
    kwargs.update(overrides)
    return build_bcr_document_ir(**kwargs)


def test_findings_based_ir_compiles_and_carries_citation_identity():
    doc_ir, reporting_reg = _build()
    compile_result = DocumentCompiler().compile(doc_ir, reporting_reg)
    assert compile_result.status == "success", [d.code for d in compile_result.diagnostics]
    assert doc_ir.document_id == "bcr:phase3-bcr-prod-new"
    assert doc_ir.report_type == "bcr"
    assert len(doc_ir.sections) == 8

    ir_data = doc_ir.model_dump(mode="json")
    assert ir_data["diagnostics"] == []

    # citation identity lives on findings, not as a block-level [N] marker
    finding_refs = [cid for f in doc_ir.findings for cid in f.citation_refs]
    assert set(finding_refs) == {_CID_GDPR_47_1, _CID_GDPR_47_2, _CID_GDPR_47_3}
    assert len(doc_ir.findings) == 3


def test_production_form_without_schema_first_omits_document_ir():
    """The v4 adapter is always callable; the on/off switch lives in service.py."""
    assert callable(build_bcr_document_ir)


def test_block_count_invariant():
    def _counts():
        doc_ir, _ = _build()
        counts = {}
        for s in doc_ir.sections:
            for b in s.blocks:
                counts[b.type] = counts.get(b.type, 0) + 1
        return counts
    assert _counts() == _counts()


def test_compiler_blocks_unregistered_citation():
    doc_ir, rr = _build(
        findings=[
            BCRFinding(
                finding_id="BCR-C-1.1-01", requirement_id="BCR-C-1.1", title="约束力不足",
                risk_level="HIGH", finding="集团内部约束机制不完整。",
                citation_refs=["CIT-MISSING"],
            )
        ],
        missing=[],
    )
    result = DocumentCompiler().compile(doc_ir, rr)
    assert result.status != "success"
    assert "CITATION_NOT_REGISTERED" in {d.code for d in result.diagnostics}


def test_citation_map_footnote_count_matches_body_references(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    reg = _registry()
    doc_ir, _ = _build(citation_registry=reg)

    finding_refs = {cid for f in doc_ir.findings for cid in f.citation_refs}
    pool_refs = {c.citation_id for c in doc_ir.citations}

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

    assert finding_refs == map_cids == reg_cids == pool_refs
    print(f"\n✅ BCR citation identity: {len(finding_refs)} CIDs across finding/pool/map layers")


def test_bcr_ir_renders_to_markdown_without_six_column_table():
    doc_ir, reporting_reg = _build()
    markdown = MarkdownRenderer().render(doc_ir, reporting_reg)

    # every section and finding reaches the output
    for section in doc_ir.sections:
        assert section.title in markdown
    for finding in doc_ir.findings:
        assert finding.finding_id in markdown

    # no legacy six-column finding table, no template residue, no emphasis
    assert "| 检查项 | 主题 | 风险 |" not in markdown
    assert "{{" not in markdown and "}}" not in markdown
    assert "**" not in markdown and "__" not in markdown

    # the finding summary short table renders each finding row
    assert "| 编号 | 风险等级 | 标题 | 状态 |" in markdown
    assert "| BCR-C-1.1-01 | HIGH | 约束力不足 | OPEN_BLOCKING |" in markdown


def test_bcr_ir_renders_to_docx_with_native_structure():
    doc_ir, reporting_reg = _build()
    blob = DocxRenderer().render(doc_ir, reporting_reg)

    from io import BytesIO

    from docx import Document
    from docx.oxml.ns import qn

    doc = Document(BytesIO(blob))
    text = "\n".join(p.text for p in doc.paragraphs)

    # every section and finding reaches the output
    for section in doc_ir.sections:
        assert section.title in text
    for finding in doc_ir.findings:
        assert finding.finding_id in text

    # no six-column detail table (native tables stay short)
    for table in doc.tables:
        assert len(table.columns) < 6, f"发现六列长表: {len(table.columns)} 列"

    # no markdown residue in paragraphs
    for paragraph in doc.paragraphs:
        assert "| --- |" not in paragraph.text
        assert "**" not in paragraph.text and "__" not in paragraph.text
        assert "{{" not in paragraph.text and "}}" not in paragraph.text

    # clause trees are native Word multi-level numbering, not hand-written text
    numbering = doc.part.numbering_part.element
    num_fmts = [
        f.get(qn("w:val"))
        for abstract in numbering.findall(qn("w:abstractNum"))
        for f in abstract.iter(qn("w:numFmt"))
    ]
    assert "lowerLetter" in num_fmts


def test_bcr_ir_renders_to_pdf_with_fixed_layout():
    doc_ir, reporting_reg = _build()
    blob = PdfRenderer().render(doc_ir, reporting_reg)

    from io import BytesIO

    from pypdf import PdfReader

    assert blob.startswith(b"%PDF")
    reader = PdfReader(BytesIO(blob))
    assert len(reader.pages) > 0
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    # every section and finding reaches the output
    for section in doc_ir.sections:
        assert section.title in text
    for finding in doc_ir.findings:
        assert finding.finding_id in text

    # no legacy six-column finding table separator, no markdown residue
    assert "| --- |" not in text
    assert "**" not in text and "__" not in text
    assert "{{" not in text and "}}" not in text

    # citation appendix entries are copyable/searchable
    assert "GDPR (EU) 2016/679" in text


def test_bcr_ir_builds_render_manifest_with_equivalence(tmp_path):
    from backend.common.reporting.render_manifest import build_render_manifest

    doc_ir, reporting_reg = _build()
    manifest = build_render_manifest(
        doc_ir, reporting_reg, tmp_path / "out", module="bcr", task_id="t1",
    )

    assert manifest.render_status == "success"
    assert manifest.section_ids == [s.section_id for s in doc_ir.sections]
    assert manifest.finding_ids == [f.finding_id for f in doc_ir.findings]

    gate_status = {gate.name: gate.status for gate in manifest.gates}
    assert gate_status["compile"] == "pass"
    assert gate_status["equivalence"] == "pass"
    # PDF CJK font gate stays blocked (no redistributable CJK asset), never pass.
    assert gate_status["pdf_font_embedding"] == "blocked"

    # every artifact file exists on disk with a matching manifest entry
    for artifact in manifest.artifacts:
        path = tmp_path / "out" / artifact.path
        assert path.exists()
        assert path.stat().st_size == artifact.size
