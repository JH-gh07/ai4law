from datetime import datetime, timezone

from backend.common.reporting.compiler import DocumentCompiler
from backend.common.reporting.schema import (
    ClaimBlock,
    CitationRecord,
    CitationRegistry,
    DocumentIR,
    ParagraphBlock,
    Provenance,
    ReportMetadata,
    SectionIR,
)


def _document(*sections: SectionIR) -> DocumentIR:
    return DocumentIR(
        compiler_version="0.1.0",
        prompt_version="test",
        template_version="test",
        model="test-model",
        document_id="doc-1",
        report_type="assessment",
        metadata=ReportMetadata(title="测试报告"),
        sections=list(sections),
        provenance=Provenance(generated_at=datetime.now(timezone.utc)),
    )


def _registry() -> CitationRegistry:
    return CitationRegistry(
        [
            CitationRecord(
                citation_id="cit-law-1",
                source_id="law-1",
                source_type="regulation",
                title="测试法",
            )
        ]
    )


def test_compiler_rejects_unregistered_citation_and_does_not_number_it() -> None:
    document = _document(
        SectionIR(
            section_id="s1",
            title="第一节",
            level=2,
            blocks=[ClaimBlock(block_id="s1_b1", text="无权威依据的主张。", citation_refs=["cit-missing"])],
        )
    )

    result = DocumentCompiler().compile(document, _registry())

    assert result.status == "error"
    assert {item.code for item in result.diagnostics} == {"CITATION_NOT_REGISTERED"}


def test_compiler_assigns_citations_by_section_order() -> None:
    document = _document(
        SectionIR(
            section_id="s1",
            title="第一节",
            level=2,
            blocks=[ClaimBlock(block_id="s1_b1", text="主张一。", citation_refs=["cit-law-1"])],
        )
    )
    registry = _registry()

    result = DocumentCompiler().compile(document, registry)

    assert result.status == "success"
    assert registry.footnote_map() == {"cit-law-1": 1}


def test_compiler_rejects_duplicate_single_use_content() -> None:
    document = _document(
        SectionIR(
            section_id="s1",
            title="第一节",
            level=2,
            blocks=[ParagraphBlock(block_id="s1_b1", text="同一段只应出现一次。")],
        ),
        SectionIR(
            section_id="s2",
            title="第二节",
            level=2,
            blocks=[ParagraphBlock(block_id="s2_b1", text="同一段只应出现一次。")],
        ),
    )

    result = DocumentCompiler().compile(document, _registry())

    assert result.status == "error"
    assert any(item.code == "BLOCK_DUPLICATE_SINGLE_USE" for item in result.diagnostics)


def test_compiler_rejects_heading_level_skip() -> None:
    document = _document(
        SectionIR(section_id="s1", title="第一节", level=2),
        SectionIR(section_id="s1_a", title="跳级小节", level=4),
    )

    result = DocumentCompiler().compile(document, _registry())

    assert result.status == "error"
    assert any(item.code == "SECTION_LEVEL_SKIP" for item in result.diagnostics)


def test_compiler_fails_closed_on_render_residue() -> None:
    document = _document(SectionIR(section_id="s1", title="第一节", level=2))

    result = DocumentCompiler().compile(document, _registry(), rendered_text="输出 {{CIT-cit-law-1}}")

    assert result.status == "fatal"
    assert any(item.code == "RENDER_MARKER_RESIDUE" for item in result.diagnostics)


def test_compiler_accepts_clean_document_and_preserves_legacy_path_by_not_touching_it() -> None:
    document = _document(
        SectionIR(
            section_id="s1",
            title="第一节",
            level=2,
            blocks=[ParagraphBlock(block_id="s1_b1", text="这是一个结构化语义段落。")],
        )
    )

    result = DocumentCompiler().compile(document, _registry(), rendered_text="这是最终展示文本。")

    assert result.status == "success"
    assert result.document is document
