from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry
from backend.common.llm.postprocess import (
    apply_citation_policy,
    convert_citation_markers,
    ensure_paragraph_citations,
    normalize_legal_markdown_structure,
)
from backend.common.render.summary import attach_citations


def test_legacy_helper_does_not_mechanically_attach_retrieval_results() -> None:
    result = ensure_paragraph_citations("这是测试文本。", ["个人信息保护法第三十九条"])
    assert "【依据：" not in result


def test_policy_never_emits_missing_retrieval_as_a_citation() -> None:
    result = ensure_paragraph_citations("根据法律要求，企业应当完成评估。", [])

    assert "【依据：未检索到】" not in result
    assert "【待核验：缺少法规依据】" in result


def test_policy_removes_legacy_placeholder_citation() -> None:
    result = apply_citation_policy(
        "企业应当完成评估。【依据：未检索到】",
        [],
    )

    assert "【依据：未检索到】" not in result.text
    assert [item.code for item in result.violations] == [
        "citation_placeholder",
        "required_citation_missing",
    ]


def test_policy_does_not_trust_unregistered_numeric_footnotes() -> None:
    result = apply_citation_policy(
        "企业应当完成评估。[999]",
        ["个人信息保护法第五十五条"],
    )

    assert "【待核验：缺少法规依据】" in result.text
    assert result.violations[0].code == "required_citation_missing"


def test_policy_preserves_only_an_explicit_allowed_citation() -> None:
    result = apply_citation_policy(
        "企业应当履行告知义务。【依据：个人信息保护法第十七条】",
        ["个人信息保护法第十七条"],
    )

    assert "【依据：个人信息保护法第十七条】" in result.text
    assert result.violations == []


def test_policy_rejects_an_unprovided_citation_and_marks_claim_pending() -> None:
    result = apply_citation_policy(
        "企业应当立即停止处理。【依据：虚构法律第一条】",
        ["个人信息保护法第十七条"],
    )

    assert "虚构法律" not in result.text
    assert "【待核验：缺少法规依据】" in result.text
    assert [item.code for item in result.violations] == [
        "citation_not_allowed",
        "required_citation_missing",
    ]


def test_policy_does_not_force_citations_onto_transition_text() -> None:
    result = apply_citation_policy(
        "下文将进一步说明整改计划。",
        ["个人信息保护法第十七条"],
    )

    assert result.text == "下文将进一步说明整改计划。"
    assert result.violations == []


def test_summary_helper_does_not_assign_global_retrieval_hits_as_proof() -> None:
    result = attach_citations(
        "企业应当完成个人信息保护影响评估。",
        ["个人信息保护法第五十五条"],
    )

    assert "【依据：个人信息保护法第五十五条】" not in result
    assert "【待核验：缺少法规依据】" in result


def test_summary_helper_uses_registry_when_provided() -> None:
    registry = CitationRegistry()
    registry.register(
        CitationItem(
            citation_id="CIT-CN-PIPL-ART55-P01",
            source_id="CN-LAW-003",
            title="个人信息保护法",
            article_no="55",
        )
    )

    result = attach_citations(
        "企业应当完成影响评估。",
        ["个人信息保护法第55条"],
        registry=registry,
    )

    assert result == "企业应当完成影响评估。[1]"


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
    assert "CIT-CN-UNKNOWN-ART99-P01" not in result
    assert "【待核验：引用无法映射】" in result


def test_convert_citation_markers_accepts_hyphenated_registry_abbreviation() -> None:
    reg = CitationRegistry()
    reg.register(CitationItem(
        citation_id="CIT-CN-EXPORT-ASSESSMENT-ART5-P01",
        source_id="CN-REG-001",
        title="数据出境安全评估办法",
        article_no="5",
    ))

    result = convert_citation_markers(
        "依据 {{CIT-CN-EXPORT-ASSESSMENT-ART5-P01}}。",
        reg,
    )

    assert result == "依据 [1]。"


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


def test_normalize_legal_markdown_structure_splits_packed_legal_outline() -> None:
    text = "第一章 个人信息出境活动说明一、数据处理者基本情况（一）处理活动说明1. 数据类型【依据：个人信息保护法第三十九条】"
    result = normalize_legal_markdown_structure(text)
    assert "# 第一章 个人信息出境活动说明" in result
    assert "## 一、数据处理者基本情况" in result
    assert "### （一）处理活动说明" in result
    assert "1. 数据类型" in result
    assert "【依据：个人信息保护法第三十九条】" in result


def test_convert_citation_markers_normalizes_heading_breaks() -> None:
    reg = CitationRegistry()
    reg.register(
        CitationItem(
            citation_id="CIT-CN-PIPL-ART39-P01",
            source_id="CN-LAW-002-001",
            title="个人信息保护法",
            article_no="39",
        )
    )
    text = "第一章 个人信息出境活动说明一、数据处理者基本情况企业应取得单独同意{{CIT-CN-PIPL-ART39-P01}}。"
    result = convert_citation_markers(text, reg)
    assert "# 第一章 个人信息出境活动说明" in result
    assert "## 一、数据处理者基本情况" in result
    assert "[1]" in result
