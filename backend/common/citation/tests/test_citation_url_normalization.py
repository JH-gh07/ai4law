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
    ("assessment", "CN-LAW-003", "个人信息保护法", "六十六"),
    ("dpia", "CN-LAW-003", "个人信息保护法", "4"),
    ("scc", "CN-REG-005", "个人信息出境标准合同办法", "一"),
    ("cn_flow", "CN-REG-004", "数据出境安全评估办法", "十三"),
    ("cpra", "US-CA-001", "CCPA/CPRA", "一"),
    ("tia", "EU-LAW-001", "GDPR", "4"),
    ("eu_scc", "EU-LAW-001", "GDPR", "1"),
    ("us_14117", "US-FED-001", "EO 14117", "5"),
    ("pipia", "CN-LAW-003", "个人信息保护法", "十"),
    ("bcr", "EU-LAW-001", "GDPR", "2"),
    ("v0_task_gateway", "CN-LAW-003", "个人信息保护法", "4"),
    ("review", "CN-LAW-003", "个人信息保护法", "七"),
]


@pytest.mark.parametrize("module, source_id, title, article", ALL_MODULES)
def test_all_modules_have_valid_url(
    module: str, source_id: str, title: str, article: str
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
    assert footnote["can_jump"] is True
