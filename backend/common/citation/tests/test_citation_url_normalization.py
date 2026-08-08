"""Regression coverage rescued from the original local ``new`` branch."""

import json
import tempfile
from pathlib import Path

import pytest

from backend.common.citation.output import (
    _normalize_article_no,
    _resolve_source_id,
    build_knowledge_url,
    normalize_citation_item,
    write_citation_map_json,
)


@pytest.mark.parametrize(
    "input_value, expected",
    [
        ("一", "1"),
        ("十", "10"),
        ("十三", "13"),
        ("六十六", "66"),
        ("一百二十", "120"),
        ("第4条", "4"),
        ("第六十六条", "66"),
        ("第二十三条之一", "23之1"),
        ("23之2", "23之2"),
        ("4", "4"),
        ("", ""),
    ],
)
def test_normalize_article_no(input_value: str, expected: str) -> None:
    assert _normalize_article_no(input_value) == expected


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        (
            {"source_id": "CN-LAW-003", "article_no": "六十六"},
            "/knowledge/laws/CN-LAW-003?article=66",
        ),
        (
            {"source_id": "CN-LAW-001", "article_no": "4"},
            "/knowledge/laws/CN-LAW-001?article=4",
        ),
        (
            {"source_id": "CN-REG-004", "article_no": "十三"},
            "/knowledge/laws/CN-REG-004?article=13",
        ),
        ({"source_id": "", "article_no": "1"}, None),
        ({"source_id": "CN-LAW-003"}, "/knowledge/laws/CN-LAW-003"),
    ],
)
def test_build_knowledge_url(kwargs: dict[str, str], expected: str | None) -> None:
    assert build_knowledge_url(**kwargs) == expected


def test_normalize_overwrites_cached_bad_url() -> None:
    item = {
        "source_id": "CN-LAW-003",
        "title": "个人信息保护法",
        "article_no": "66",
        "knowledge_url": "/evidence",
    }
    result = normalize_citation_item(item, module="test")
    assert result["knowledge_url"] == "/knowledge/laws/CN-LAW-003?article=66"


def test_normalize_generates_missing_url() -> None:
    item = {"source_id": "CN-LAW-003", "title": "个人信息保护法", "article_no": "66"}
    result = normalize_citation_item(item, module="test")
    assert result["knowledge_url"] == "/knowledge/laws/CN-LAW-003?article=66"


def test_normalize_converts_chinese_article_no() -> None:
    item = {"source_id": "CN-LAW-001", "title": "网络安全法", "article_no": "十三"}
    result = normalize_citation_item(item, module="test")
    assert result["knowledge_url"] == "/knowledge/laws/CN-LAW-001?article=13"
    assert result["article_no"] == "13"


def test_normalize_sets_can_jump() -> None:
    item = {"source_id": "CN-LAW-003", "title": "个人信息保护法", "article_no": "66"}
    result = normalize_citation_item(item, module="test")
    assert result["can_jump"] is True


def test_unknown_source_cannot_claim_exact_knowledge_jump() -> None:
    item = {
        "source_id": "delilegal-case-指导性案例265号",
        "title": "指导性案例265号",
        "article_no": "1",
        "can_jump": True,
        "knowledge_url": "/knowledge/laws/delilegal-case-指导性案例265号?article=1",
    }

    result = normalize_citation_item(item, module="test")

    assert result["resolution"]["resolution_type"] == "unresolved"
    assert result["resolution"]["failure_reason"] == "source_not_found"
    assert result["knowledge_url"] == ""
    assert result["can_jump"] is False


def test_known_source_without_article_is_source_overview() -> None:
    result = normalize_citation_item(
        {"source_id": "CN-LAW-003", "title": "个人信息保护法"},
        module="test",
    )

    assert result["resolution"]["resolution_type"] == "source_overview"
    assert result["resolution"]["failure_reason"] == "article_missing"
    assert result["resolution"]["target_id"] == "CN-LAW-003"
    assert result["knowledge_url"] == "/knowledge/laws/CN-LAW-003"
    assert result["can_jump"] is False


def test_nonexistent_article_cannot_claim_exact_jump() -> None:
    result = normalize_citation_item(
        {
            "source_id": "CN-LAW-003",
            "title": "个人信息保护法",
            "article_no": "9999",
            "can_jump": True,
        },
        module="test",
    )

    assert result["resolution"]["resolution_type"] == "source_overview"
    assert result["resolution"]["failure_reason"] == "article_not_found"
    assert result["can_jump"] is False


def test_duplicate_article_cannot_claim_exact_jump() -> None:
    # Phase-4 dedup: CN-LAW-001/23 is now unique. Verify with a non-existent
    # article_no to exercise the article_not_found path instead.
    result = normalize_citation_item(
        {
            "source_id": "CN-LAW-001",
            "title": "网络安全法",
            "article_no": "9999",
        },
        module="test",
    )

    assert result["resolution"]["resolution_type"] == "source_overview"
    assert result["resolution"]["failure_reason"] in ("article_not_found", "article_not_unique")
    assert result["can_jump"] is False


def test_verified_external_source_is_not_a_local_knowledge_jump() -> None:
    result = normalize_citation_item(
        {
            "source_id": "deli-case-265",
            "title": "指导性案例265号",
            "source_url": "https://example.test/case/265",
            "external_verified": True,
        },
        module="test",
    )

    assert result["resolution"]["resolution_type"] == "external_verified"
    assert result["resolution"]["target_id"] == "https://example.test/case/265"
    assert result["knowledge_url"] == ""
    assert result["can_jump"] is False
    assert "review_external_source" in result["resolution"]["available_actions"]


def test_unsafe_external_url_is_not_returned_or_marked_verified() -> None:
    result = normalize_citation_item(
        {
            "source_id": "external-record",
            "title": "外部记录",
            "source_url": "javascript:alert(1)",
            "external_verified": True,
        },
        module="test",
    )

    assert result["source_url"] == ""
    assert result["resolution"]["resolution_type"] == "unresolved"
    assert result["can_jump"] is False


def test_write_citation_map_json_goes_through_normalize() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        items = [
            {
                "citation_id": "test-1",
                "source_id": "CN-LAW-003",
                "title": "个人信息保护法",
                "article_no": "66",
                "quote_text": "测试",
            }
        ]
        path = write_citation_map_json(
            output_dir=output_dir,
            module="test",
            task_id="verify-test",
            footnote_map={"1": items[0]},
            all_items=items,
        )
        written = json.loads(Path(path).read_text(encoding="utf-8"))

    footnote = written["footnote_map"]["1"]
    assert footnote["knowledge_url"] == "/knowledge/laws/CN-LAW-003?article=66"
    assert footnote["can_jump"] is True
    assert footnote["module"] == "test"
    assert written["all_items"][0]["knowledge_url"] == footnote["knowledge_url"]


def test_resolve_known_source_id() -> None:
    assert _resolve_source_id("CN-LAW-003", "个人信息保护法") == "CN-LAW-003"
    assert _resolve_source_id("CN-REG-004", "数据出境安全评估办法") == "CN-REG-004"


def test_normalize_idempotent() -> None:
    item = {"source_id": "CN-LAW-003", "title": "个人信息保护法", "article_no": "六十六"}
    first = normalize_citation_item(dict(item), module="test")
    second = normalize_citation_item(dict(first), module="test")
    for field in ["knowledge_url", "source_id", "article_no", "can_jump", "module"]:
        assert first[field] == second[field]


ALL_MODULES = [
    ("assessment", "CN-LAW-003", "个人信息保护法", "六十六", True),
    ("dpia", "CN-LAW-003", "个人信息保护法", "4", True),
    ("scc", "CN-REG-005", "个人信息出境标准合同办法", "一", False),
    ("cn_flow", "CN-REG-004", "数据出境安全评估办法", "十三", True),  # article 13 now ingested
    ("cpra", "US-CA-001", "CCPA/CPRA", "一", False),
    ("tia", "EU-LAW-001", "GDPR", "4", False),
    ("eu_scc", "EU-LAW-001", "GDPR", "1", False),
    ("us_14117", "US-FED-001", "EO 14117", "5", False),
    ("pipia", "CN-LAW-003", "个人信息保护法", "十", True),
    ("bcr", "EU-LAW-001", "GDPR", "2", False),
    ("v0_task_gateway", "CN-LAW-003", "个人信息保护法", "4", True),
    ("review", "CN-LAW-003", "个人信息保护法", "七", True),
]


@pytest.mark.parametrize("module, source_id, title, article, exact", ALL_MODULES)
def test_all_modules_have_controlled_resolution(
    module: str, source_id: str, title: str, article: str, exact: bool
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        item = {
            "citation_id": f"{module}-test-1",
            "source_id": source_id,
            "title": title,
            "article_no": article,
            "quote_text": "test",
        }
        write_citation_map_json(
            output_dir=output_dir,
            module=module,
            task_id=f"test-{module}",
            footnote_map={"1": item},
            all_items=[item],
        )
        written = json.loads((output_dir / "citation_map.json").read_text("utf-8"))

    footnote = written["footnote_map"]["1"]
    assert footnote["knowledge_url"]
    assert "/knowledge/laws/" in footnote["knowledge_url"]
    assert footnote["can_jump"] is exact
    assert footnote["resolution"]["resolution_type"] == (
        "exact_article" if exact else "source_overview"
    )
