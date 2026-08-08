from __future__ import annotations

from datetime import date

from backend.common.citation.output import (
    _is_recent_effective_date,
    normalize_citation_item,
)


def test_exact_article_backfills_official_url_and_source_metadata() -> None:
    result = normalize_citation_item(
        {
            "source_id": "CN-LAW-003",
            "title": "中华人民共和国个人信息保护法",
            "article_no": "六十六",
        },
        module="test",
    )

    assert result["citation_granularity"] == "article"
    assert result["source_url"] == "https://www.cac.gov.cn/2021-08/20/c_1631050028355286.htm"
    assert result["publish_date"] == "2021-08-20"
    assert result["effective_date"] == "2021-11-01"
    assert result["source_status"] == "effective"
    assert result["amendment_note"] == ""


def test_source_level_citation_has_explicit_semantics_and_catalog_url() -> None:
    result = normalize_citation_item(
        {
            "source_id": "CN-LAW-003",
            "title": "中华人民共和国个人信息保护法",
        },
        module="test",
    )

    assert result["citation_granularity"] == "source"
    assert result["resolution"]["resolution_type"] == "source_overview"
    assert result["resolution"]["failure_reason"] == "source_level_by_design"
    assert result["source_url"] == "https://www.cac.gov.cn/2021-08/20/c_1631050028355286.htm"


def test_unsafe_item_url_falls_back_to_safe_registry_url() -> None:
    result = normalize_citation_item(
        {
            "source_id": "CN-LAW-003",
            "title": "中华人民共和国个人信息保护法",
            "article_no": "66",
            "source_url": "javascript:alert(1)",
        },
        module="test",
    )

    assert result["source_url"] == "https://www.cac.gov.cn/2021-08/20/c_1631050028355286.htm"
    assert "open_official_source" in result["resolution"]["available_actions"]


def test_item_specific_safe_url_takes_precedence() -> None:
    result = normalize_citation_item(
        {
            "source_id": "CN-LAW-003",
            "title": "中华人民共和国个人信息保护法",
            "article_no": "66",
            "source_url": "https://example.test/pipl/article-66",
        },
        module="test",
    )

    assert result["source_url"] == "https://example.test/pipl/article-66"


def test_source_metadata_exposes_amendment_and_recent_status() -> None:
    result = normalize_citation_item(
        {
            "source_id": "CN-LAW-001",
            "title": "中华人民共和国网络安全法（2025修正）",
            "article_no": "1",
        },
        module="test",
    )

    assert result["amendment_note"] == "2025修正"
    assert result["is_recent"] is _is_recent_effective_date(
        "2025-12-29",
        as_of=date.today(),
    )


def test_recent_effective_date_uses_a_bounded_twelve_month_window() -> None:
    as_of = date(2026, 8, 8)

    assert _is_recent_effective_date("2025-12-29", as_of=as_of) is True
    assert _is_recent_effective_date("2024-12-29", as_of=as_of) is False
    assert _is_recent_effective_date("2027-01-01", as_of=as_of) is False
    assert _is_recent_effective_date("invalid", as_of=as_of) is False
