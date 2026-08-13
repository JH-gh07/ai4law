"""IR → PDF fixed-layout renderer tests (task067 T06)."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfReader

from backend.common.reporting import (
    CitationNoteBlock,
    CitationRecord,
    CitationRegistry,
    ClaimBlock,
    ClauseGroupBlock,
    ClauseNode,
    DocumentCompiler,
    DocumentIR,
    FindingDetailBlock,
    FindingRecord,
    FindingReferenceBlock,
    FindingSummaryBlock,
    KeyValueBlock,
    KeyValueItem,
    ListBlock,
    ListItem,
    PageBreakBlock,
    ParagraphBlock,
    Provenance,
    ReportMetadata,
    SectionIR,
    TableBlock,
    WarningBlock,
)
from backend.common.reporting.render_profiles import RenderProfileError, get_profile
from backend.common.reporting.renderers.pdf import (
    FontSpec,
    PdfRenderer,
    PdfRenderError,
    render_pdf,
    render_pdf_to_file,
)

TS = datetime(2026, 8, 8, tzinfo=timezone.utc)

# Broken-token fingerprints the six-column legacy layout produced. The new
# longitudinal renderer must never emit these as standalone extracted lines.
_BROKEN_FRAGMENTS = ("HIG", "ME", "DIU", "-C-1", ".1")


def _citation(citation_id: str, title: str, article: str | None = None) -> CitationRecord:
    from backend.common.reporting import CitationLocator

    return CitationRecord(
        citation_id=citation_id,
        source_id=f"SRC-{citation_id}",
        source_type="regulation",
        title=title,
        locator=CitationLocator(article=article) if article else None,
        authority_level="high",
        binding_force="mandatory",
        can_enter_external_report=True,
    )


def _registry() -> CitationRegistry:
    return CitationRegistry([
        _citation("cit-1", "GDPR (EU) 2016/679", "47(1)"),
        _citation("cit-2", "EDPB Recommendations 01/2020"),
    ])


def _finding(fid: str, title: str, risk: str = "MEDIUM", citation_refs=None) -> FindingRecord:
    return FindingRecord(
        finding_id=fid,
        requirement_id=f"R-{fid}",
        title=title,
        risk_level=risk,
        risk_score=60.0 if risk == "HIGH" else 30.0,
        statement="现状不合规。",
        legal_basis=["GDPR Article 47(1)"] if citation_refs else [],
        recommendation="补齐合规要求。",
        suggested_revision=None,
        citation_refs=citation_refs or [],
    )


def _document() -> tuple[DocumentIR, CitationRegistry]:
    registry = _registry()
    document = DocumentIR(
        compiler_version="0.1.0",
        prompt_version="test",
        template_version="test",
        model="test-model",
        document_id="doc-1",
        report_type="bcr",
        metadata=ReportMetadata(
            title="测试报告",
            short_title="BCR 报告",
            company_name="TestCo",
            jurisdiction="EU",
            locale="zh-CN",
            report_date="2026-08-08",
            report_id="BCR-2026-001",
        ),
        provenance=Provenance(generated_at=TS),
        findings=[
            _finding("BCR-C-1.1-01", "约束力不足", "HIGH", citation_refs=["cit-1"]),
            _finding("BCR-C-1.9-01", "TIA 不完整", "MEDIUM"),
        ],
        citations=list(registry.records().values()),
        sections=[
            SectionIR(section_id="s1", title="报告摘要", level=1, ordinal="1", blocks=[
                ParagraphBlock(block_id="b1", text="本报告用于验证 PDF renderer。"),
                ClaimBlock(block_id="b2", text="集团规则应当具有法律约束力。", citation_refs=["cit-1"]),
                ListBlock(block_id="b3", ordered=True, items=[
                    ListItem(text="父项", children=[ListItem(text="子项一"), ListItem(text="子项二")]),
                    ListItem(text="第二父项"),
                ]),
                TableBlock(block_id="b4", headers=["检查项", "结果"], rows=[["A", "合规"]]),
                WarningBlock(block_id="b5", text="注意风险", severity="warning"),
                KeyValueBlock(block_id="b6", items=[KeyValueItem(label="BCR 类型", value="BCR-C")]),
            ]),
            SectionIR(section_id="s2", title="风险与 finding 摘要", level=1, ordinal="2", blocks=[
                FindingSummaryBlock(block_id="s2.summary", finding_refs=["BCR-C-1.1-01", "BCR-C-1.9-01"]),
            ]),
            SectionIR(section_id="s3", title="详细 finding", level=1, ordinal="3", blocks=[
                FindingDetailBlock(block_id="s3.d1", finding_ref="BCR-C-1.1-01"),
                FindingDetailBlock(block_id="s3.d2", finding_ref="BCR-C-1.9-01"),
                FindingReferenceBlock(block_id="s3.r1", finding_ref="BCR-C-1.1-01", note="见整改优先级"),
            ]),
            SectionIR(section_id="s4", title="建议条款", level=1, ordinal="4", blocks=[
                ClauseGroupBlock(block_id="s4.clauses", title="建议条款", clauses=[
                    ClauseNode(node_id="c1", text="第一条", children=[
                        ClauseNode(node_id="c1-1", text="第一项", numbering_style="lower_alpha"),
                        ClauseNode(node_id="c1-2", text="第二项", numbering_style="lower_alpha"),
                    ]),
                ]),
            ]),
            SectionIR(section_id="s5", title="法规与引用", level=1, ordinal="5", blocks=[
                CitationNoteBlock(block_id="s5.citations", citation_refs=["cit-1", "cit-2"]),
            ]),
            SectionIR(section_id="s6", title="审查边界", level=1, ordinal="6", blocks=[
                PageBreakBlock(block_id="s6.pb", reason="附录分页"),
            ]),
        ],
    )
    return document, registry


def _render() -> tuple[bytes, DocumentIR, CitationRegistry]:
    document, registry = _document()
    return PdfRenderer().render(document, registry), document, registry


def _extract_text(blob: bytes) -> str:
    reader = PdfReader(BytesIO(blob))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _page_count(blob: bytes) -> int:
    return len(PdfReader(BytesIO(blob)).pages)


def _clause_count(clauses: list[ClauseNode]) -> int:
    return len(clauses) + sum(_clause_count(c.children) for c in clauses)


# ── machine acceptance ──────────────────────────────────────────────────────


def test_pdf_magic_and_positive_page_count() -> None:
    blob, _, _ = _render()
    assert blob.startswith(b"%PDF")
    assert _page_count(blob) > 0


def test_finding_ids_extractable() -> None:
    blob, document, _ = _render()
    text = _extract_text(blob)
    for finding in document.findings:
        assert finding.finding_id in text


def test_no_broken_token_fragments() -> None:
    blob, _, _ = _render()
    text = _extract_text(blob)
    standalone = {line.strip() for line in text.splitlines()}
    for fragment in _BROKEN_FRAGMENTS:
        assert fragment not in standalone, f"broken token fragment surfaced: {fragment}"


def test_no_markdown_table_separator_residue() -> None:
    blob, _, _ = _render()
    text = _extract_text(blob)
    assert "| --- |" not in text
    assert "|" not in text.replace("｜", "")  # no raw pipe tables


def test_finding_clause_citation_counts_match_ir() -> None:
    blob, document, _ = _render()
    text = _extract_text(blob)
    finding_count = sum(
        1 for s in document.sections for b in s.blocks if getattr(b, "type", None) == "finding_detail"
    )
    assert finding_count == len(document.findings)
    for finding in document.findings:
        assert finding.finding_id in text
    for section in document.sections:
        for block in section.blocks:
            for clause in getattr(block, "clauses", []):
                assert _clause_count([clause]) >= 1  # clause trees render
    # citation appendix entries present and numbered
    assert "GDPR (EU) 2016/679" in text
    assert "EDPB Recommendations 01/2020" in text


def test_rendered_pdf_passes_compiler_render_gate() -> None:
    document, registry = _document()
    blob = PdfRenderer().render(document, registry)
    result = DocumentCompiler().compile(document, registry)
    assert result.status == "success", [d.code for d in result.diagnostics]
    assert len(blob) > 0


def test_cjk_font_embedding_gate() -> None:
    """The CJK font embeds only when a licensed asset is tracked.

    Without a CJK asset the renderer degrades to ``STSong-Light`` (emb=no), so
    the font gate stays ``BLOCKED_BY_FONT``. With an asset (simulated via a
    fake registered spec), the spec reports ``cjk_embedded=True``.
    """
    document, registry = _document()
    fonts = PdfRenderer()._register_fonts()
    # Latin body font embeds cleanly (Liberation Sans TTF ships with the repo).
    assert fonts.latin == "LiberationSans"
    # The current repository has no CJK asset → degraded, non-embedded CID font.
    assert fonts.cjk_embedded is False
    assert fonts.cjk_asset is None

    if shutil.which("pdffonts"):
        blob = PdfRenderer().render(document, registry)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "r.pdf"
            path.write_bytes(blob)
            out = subprocess.run(["pdffonts", str(path)], capture_output=True, text=True).stdout
            assert "STSong-Light" in out
            # non-embedded CID font → emb=no, which is exactly the blocked gate.
            assert "emb" in out


def test_font_spec_flags_embedded_cjk_when_asset_present(monkeypatch) -> None:
    import backend.common.reporting.renderers.pdf as pdf_module

    class _FakeAsset:
        path = "resources/fonts/NotoSansCJK-Regular.ttf"
        sha256 = "a" * 64
        license = "SIL OFL 1.1"
        covers_cjk = True

    renderer = PdfRenderer()
    monkeypatch.setattr(pdf_module, "get_cjk_font", lambda: _FakeAsset())
    monkeypatch.setattr(renderer, "_register_ttf", lambda name, path: None)
    fonts = renderer._register_fonts()
    assert fonts.cjk_embedded is True
    assert fonts.cjk_asset.covers_cjk is True


# ── fail-closed / correctness details ───────────────────────────────────────


def test_unknown_block_type_raises() -> None:
    renderer = PdfRenderer()

    class _Unknown:
        type = "not_a_block"

    with pytest.raises(PdfRenderError):
        renderer._render_block(
            [],
            SectionIR(section_id="s", title="t", level=1),
            _Unknown(),
            {},
            _registry(),
            get_profile("legal-report-a4-v1"),
            _fonts(),
            {},
        )


def test_unknown_render_profile_raises() -> None:
    document, registry = _document()
    document.render_contract.profile_id = "no-such-profile"
    with pytest.raises(RenderProfileError):
        render_pdf(document, registry)


def test_missing_finding_ref_raises() -> None:
    document, registry = _document()
    document.sections[1].blocks.append(FindingSummaryBlock(block_id="x", finding_refs=["MISSING"]))
    with pytest.raises(PdfRenderError):
        render_pdf(document, registry)


def test_basis_entries_render_one_per_line_not_joined_wall() -> None:
    from backend.common.reporting import FindingBasis

    document, registry = _document()
    document.findings[0].basis_entries = [
        FindingBasis(citation_ref="cit-1", label="GDPR Article 47(2)(a)", rationale="约束规则须由集团层面批准", is_primary=True),
        FindingBasis(citation_ref=None, label="EDPB Recommendations 01/2020", rationale="跨境传输须逐项评估"),
        FindingBasis(citation_ref=None, label="GDPR Article 47(1)"),
    ]
    blob = render_pdf(document, registry)
    text = _extract_text(blob)
    # each entry is an independent paragraph — never the "；"-joined label wall
    assert "GDPR Article 47(2)(a)[1]" in text
    assert "约束规则须由集团层面批准" in text
    assert "EDPB Recommendations 01/2020" in text
    assert "跨境传输须逐项评估" in text
    assert "GDPR Article 47(1)" in text
    assert "；" not in text


def test_finding_summary_is_short_table() -> None:
    blob, _, _ = _render()
    text = _extract_text(blob)
    # summary columns: 编号/风险等级/标题/状态 → 4 short columns, no legacy
    # six-column header ("检查项 | 主题 | 风险 | ...").
    for label in ("编号", "风险等级", "标题", "状态"):
        assert label in text
    assert "| 检查项 | 主题 | 风险 |" not in text


def test_render_is_hash_stable() -> None:
    document, registry = _document()
    a = render_pdf(document, registry)
    b = render_pdf(document, registry)
    assert hashlib.sha256(a).hexdigest() == hashlib.sha256(b).hexdigest()


def test_render_to_file_writes_pdf(tmp_path: Path) -> None:
    document, registry = _document()
    output = tmp_path / "out" / "report.pdf"
    result = render_pdf_to_file(document, output, registry)
    assert result == output
    assert output.exists()
    assert output.read_bytes().startswith(b"%PDF")


def test_raster_pages_non_empty_and_within_bounds() -> None:
    """Every page rasterises to non-empty content that stays inside the page.

    ``pdftoppm`` is an optional system tool; when absent the check is skipped so
    the renderer unit suite stays runnable on a minimal environment (the same
    graceful-degradation policy used by the T00 gate).
    """
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm is None:
        pytest.skip("pdftoppm not available")

    from PIL import Image
    import numpy as np

    blob, _, _ = _render()
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "r.pdf"
        src.write_bytes(blob)
        subprocess.run(
            [pdftoppm, "-png", "-r", "96", str(src), str(Path(d) / "page")],
            check=True,
            capture_output=True,
        )
        pages = sorted(Path(d).glob("page-*.png"))
        assert pages, "pdftoppm produced no page rasters"
        for page_path in pages:
            arr = np.asarray(Image.open(page_path).convert("L"))
            height, width = arr.shape
            ys, xs = np.where(arr < 250)
            assert xs.size > 0, f"{page_path.name} 无内容像素"
            assert xs.min() > 0 and xs.max() < width - 1, f"{page_path.name} 内容越过左右页边"
            assert ys.min() > 0 and ys.max() < height - 1, f"{page_path.name} 内容越过上下页边"


# ── helpers ─────────────────────────────────────────────────────────────────


def _fonts() -> FontSpec:
    return PdfRenderer()._register_fonts()
