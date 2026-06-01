from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry
from backend.common.llm.postprocess import convert_citation_markers, ensure_paragraph_citations


def test_ensure_paragraph_citations_still_works() -> None:
    """Legacy function should still work for backward compatibility."""
    result = ensure_paragraph_citations("这是测试文本。", ["个人信息保护法第三十九条"])
    assert "【依据：个人信息保护法第三十九条】" in result


def test_convert_citation_markers_replaces_single_marker() -> None:
    reg = CitationRegistry()
    reg.register(
        CitationItem(
            citation_id="CIT-CN-PIPL-ART39-P01",
            source_id="CN-LAW-002-001",
            title="个人信息保护法",
            article_no="39",
        )
    )
    text = "企业应依法取得个人单独同意{{CIT-CN-PIPL-ART39-P01}}。"
    result = convert_citation_markers(text, reg)
    assert "[1]" in result
    assert "{{CIT-CN-PIPL-ART39-P01}}" not in result


def test_convert_citation_markers_replaces_multiple_markers() -> None:
    reg = CitationRegistry()
    reg.register(
        CitationItem(
            citation_id="CIT-CN-PIPL-ART39-P01",
            source_id="CN-LAW-002-001",
            title="个人信息保护法",
            article_no="39",
        )
    )
    reg.register(
        CitationItem(
            citation_id="CIT-CN-DSL-ART21-P01",
            source_id="CN-LAW-003-001",
            title="数据安全法",
            article_no="21",
        )
    )
    text = (
        "根据{{CIT-CN-PIPL-ART39-P01}}，应取得单独同意；"
        "同时依据{{CIT-CN-DSL-ART21-P01}}，应建立数据安全管理制度。"
    )
    result = convert_citation_markers(text, reg)
    assert "[1]" in result
    assert "[2]" in result
    assert "{{CIT-CN-PIPL-ART39-P01}}" not in result
    assert "{{CIT-CN-DSL-ART21-P01}}" not in result


def test_convert_citation_markers_orders_by_first_appearance() -> None:
    reg = CitationRegistry()
    reg.register(
        CitationItem(
            citation_id="CIT-CN-DSL-ART21-P01",
            source_id="CN-LAW-003-001",
            title="数据安全法",
            article_no="21",
        )
    )
    reg.register(
        CitationItem(
            citation_id="CIT-CN-PIPL-ART39-P01",
            source_id="CN-LAW-002-001",
            title="个人信息保护法",
            article_no="39",
        )
    )
    # DSL appears first, so it should be [1]; PIPL second → [2]
    text = "依据{{CIT-CN-DSL-ART21-P01}}和{{CIT-CN-PIPL-ART39-P01}}。"
    result = convert_citation_markers(text, reg)
    # DSL should be [1]
    assert "依据[1]和[2]" in result or "依据 [1] 和 [2]" in result


def test_convert_citation_markers_skips_unknown_markers() -> None:
    reg = CitationRegistry()
    reg.register(
        CitationItem(
            citation_id="CIT-CN-PIPL-ART39-P01",
            source_id="CN-LAW-002-001",
            title="个人信息保护法",
            article_no="39",
        )
    )
    text = "引用{{CIT-CN-PIPL-ART39-P01}}和{{CIT-CN-UNKNOWN-ART99-P01}}。"
    result = convert_citation_markers(text, reg)
    assert "[1]" in result
    assert "{{CIT-CN-UNKNOWN-ART99-P01}}" not in result


def test_convert_citation_markers_empty_text() -> None:
    reg = CitationRegistry()
    reg.register(
        CitationItem(
            citation_id="CIT-CN-PIPL-ART39-P01",
            source_id="CN-LAW-002-001",
            title="个人信息保护法",
            article_no="39",
        )
    )
    assert convert_citation_markers("", reg) == ""


def test_convert_citation_markers_text_without_markers() -> None:
    reg = CitationRegistry()
    reg.register(
        CitationItem(
            citation_id="CIT-CN-PIPL-ART39-P01",
            source_id="CN-LAW-002-001",
            title="个人信息保护法",
            article_no="39",
        )
    )
    text = "这是没有引用标记的文本。"
    assert convert_citation_markers(text, reg) == text


def test_convert_citation_markers_reuses_same_number_for_repeated() -> None:
    reg = CitationRegistry()
    reg.register(
        CitationItem(
            citation_id="CIT-CN-PIPL-ART39-P01",
            source_id="CN-LAW-002-001",
            title="个人信息保护法",
            article_no="39",
        )
    )
    text = "参见{{CIT-CN-PIPL-ART39-P01}}，再次参见{{CIT-CN-PIPL-ART39-P01}}。"
    result = convert_citation_markers(text, reg)
    # Both should use [1]
    assert result.count("[1]") == 2
    assert "[2]" not in result
