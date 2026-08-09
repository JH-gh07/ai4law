from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry, registry_from_documents
from backend.common.rag.retriever import RegulationDoc


def _sample_citation(citation_id: str, title: str, article_no: str) -> CitationItem:
    return CitationItem(
        citation_id=citation_id,
        source_id="CN-LAW-001-001",
        title=title,
        article_no=article_no,
    )


def test_registry_register_and_get() -> None:
    reg = CitationRegistry()
    item = _sample_citation("CIT-CN-PIPL-ART39-P01", "个人信息保护法", "39")
    reg.register(item)
    assert reg.get("CIT-CN-PIPL-ART39-P01") is item
    assert reg.get("nonexistent") is None
    assert len(reg) == 1


def test_registry_build_marker_list_empty() -> None:
    reg = CitationRegistry()
    assert "暂无" in reg.build_marker_list()


def test_registry_build_marker_list_with_items() -> None:
    reg = CitationRegistry()
    reg.register(_sample_citation("CIT-CN-PIPL-ART39-P01", "个人信息保护法", "39"))
    reg.register(_sample_citation("CIT-CN-DSL-ART21-P01", "数据安全法", "21"))
    marker_list = reg.build_marker_list()
    assert "{{CIT-CN-PIPL-ART39-P01}}" in marker_list
    assert "个人信息保护法" in marker_list
    assert "第39条" in marker_list
    assert "{{CIT-CN-DSL-ART21-P01}}" in marker_list
    assert "数据安全法" in marker_list
    assert "第21条" in marker_list


def test_registry_build_footnote_map_orders_by_first_appearance() -> None:
    reg = CitationRegistry()
    pipel_item = _sample_citation("CIT-CN-PIPL-ART39-P01", "个人信息保护法", "39")
    dsl_item = _sample_citation("CIT-CN-DSL-ART21-P01", "数据安全法", "21")
    reg.register(pipel_item)
    reg.register(dsl_item)

    text = "根据{{CIT-CN-DSL-ART21-P01}}和{{CIT-CN-PIPL-ART39-P01}}，同时参考{{CIT-CN-DSL-ART21-P01}}。"
    footnote_map = reg.build_footnote_map(text)

    # DSL appears first → [1], PIPL second → [2]
    assert footnote_map[1] is dsl_item
    assert footnote_map[2] is pipel_item
    assert len(footnote_map) == 2


def test_registry_build_footnote_map_skips_unknown_markers() -> None:
    reg = CitationRegistry()
    reg.register(_sample_citation("CIT-CN-PIPL-ART39-P01", "个人信息保护法", "39"))

    text = "引用{{CIT-CN-PIPL-ART39-P01}}和{{CIT-CN-UNKNOWN-ART99-P01}}。"
    footnote_map = reg.build_footnote_map(text)
    assert len(footnote_map) == 1


def test_registry_build_footnote_map_empty_text() -> None:
    reg = CitationRegistry()
    reg.register(_sample_citation("CIT-CN-PIPL-ART39-P01", "个人信息保护法", "39"))
    assert reg.build_footnote_map("无引用文本") == {}


def test_registry_to_list() -> None:
    reg = CitationRegistry()
    reg.register(_sample_citation("CIT-CN-PIPL-ART39-P01", "个人信息保护法", "39"))
    result = reg.to_list()
    assert len(result) == 1
    assert result[0]["citation_id"] == "CIT-CN-PIPL-ART39-P01"
    assert result[0]["title"] == "个人信息保护法"


def test_registry_from_documents_builds_stable_citable_items() -> None:
    registry = registry_from_documents(
        [
            RegulationDoc(
                id="CN-LAW-003",
                title="个人信息保护法",
                article="第三十九条",
                content="向境外提供个人信息应当履行法定义务。",
                jurisdiction="cn",
                source_url="https://example.test/pipl",
            )
        ],
        jurisdiction="CN",
    )

    items = list(registry)
    assert len(items) == 1
    assert items[0].citation_id == "CIT-CN-CN_LAW_003-ART39-P01"
    assert items[0].article_no == "39"
    assert items[0].display_label == "个人信息保护法 第39条"
    assert items[0].source_url == "https://example.test/pipl"


def test_registry_from_documents_deduplicates_same_source_and_article() -> None:
    document = RegulationDoc(
        id="CN-LAW-003",
        title="个人信息保护法",
        article="39",
        content="条文内容",
    )

    registry = registry_from_documents([document, document], jurisdiction="CN")

    assert len(registry) == 1


def test_registry_from_documents_preserves_citation_governance_metadata() -> None:
    registry = registry_from_documents(
        [
            {
                "source_id": "EU-LAW-001",
                "title": "GDPR (EU) 2016/679",
                "article": "22",
                "snippet": "Automated decision-making safeguards.",
                "confidence_score": 0.88,
                "authority_level": "high",
                "binding_force": "mandatory",
                "source_kind": "law_article",
                "allowed_usage": ["external_report", "internal_review"],
                "can_enter_external_report": True,
                "confidence_threshold": 0.30,
                "external_report_allowed": True,
            }
        ],
        jurisdiction="EU",
    )

    item = next(iter(registry))
    assert item.confidence_score == 0.88
    assert item.authority_level == "high"
    assert item.binding_force == "mandatory"
    assert item.source_kind == "law_article"
    assert item.allowed_usage == ["external_report", "internal_review"]
    assert item.confidence_threshold == 0.30
    assert item.external_report_allowed is True


# ---------------------------------------------------------------------------
# RC-2 fix: register() must reject malformed IDs (fail-fast)
# ---------------------------------------------------------------------------

import pytest


def test_register_rejects_id_missing_art_prefix() -> None:
    """An ID without the ART/GEN token must raise ValueError."""
    reg = CitationRegistry()
    # Missing ART: "CIT-CN-PIPL-39-P01" has no ART prefix → invalid
    bad_item = _sample_citation("CIT-CN-PIPL-39-P01", "个人信息保护法", "39")
    with pytest.raises(ValueError, match="Invalid citation ID"):
        reg.register(bad_item)


def test_register_accepts_legacy_hyphen_abbr_id() -> None:
    """Legacy IDs with hyphens in the abbr segment (old format) stay valid for
    backward compatibility — the regex allows hyphens via backtracking."""
    reg = CitationRegistry()
    item = _sample_citation("CIT-CN-EXPORT-ASSESSMENT-ART5-P01", "数据出境安全评估办法", "5")
    reg.register(item)  # must NOT raise
    assert reg.get("CIT-CN-EXPORT-ASSESSMENT-ART5-P01") is item


def test_register_rejects_missing_p_segment() -> None:
    reg = CitationRegistry()
    bad_item = _sample_citation("CIT-CN-PIPL-ART39", "个人信息保护法", "39")
    with pytest.raises(ValueError, match="Invalid citation ID"):
        reg.register(bad_item)


def test_register_accepts_sanitized_abbr_with_underscore() -> None:
    reg = CitationRegistry()
    item = _sample_citation("CIT-CN-EXPORT_ASSESSMENT-ART5-P01", "数据出境安全评估办法", "5")
    reg.register(item)
    assert reg.get("CIT-CN-EXPORT_ASSESSMENT-ART5-P01") is item
