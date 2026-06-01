from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry


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
