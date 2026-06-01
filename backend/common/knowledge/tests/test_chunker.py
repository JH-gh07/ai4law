from backend.common.knowledge.chinese_legal_patterns import (
    ARTICLE_PATTERN,
    CHAPTER_PATTERN,
    detect_structure,
    extract_title_from_text,
)
from backend.common.knowledge.chunker import ChineseLegalChunker


def test_detect_article() -> None:
    level, label = detect_structure("第三十九条 个人信息处理者向境外提供个人信息的")
    assert level == "article"
    assert label == "第三十九条"


def test_detect_chapter() -> None:
    level, label = detect_structure("第二章 个人信息处理规则")
    assert level == "chapter"
    assert label == "第二章"


def test_detect_section() -> None:
    level, label = detect_structure("第一节 一般规定")
    assert level == "section"


def test_detect_item() -> None:
    level, label = detect_structure("（一）处理目的")
    assert level == "item"


def test_detect_item_english_parens() -> None:
    level, label = detect_structure("(1) purpose")
    assert level == "item"


def test_detect_plain_text() -> None:
    level, label = detect_structure("这是一段普通的描述性文字。")
    assert level is None


def test_extract_title_from_text() -> None:
    text = "《个人信息保护法》\n\n第一条 为了保护个人信息权益..."
    assert extract_title_from_text(text) == "个人信息保护法"


def test_chunker_splits_by_article() -> None:
    chunker = ChineseLegalChunker(source_id="CN-LAW-002", title="个人信息保护法")
    text = (
        "《个人信息保护法》\n\n"
        "第一章 总则\n\n"
        "第一条 为了保护个人信息权益，规范个人信息处理活动。\n\n"
        "第二条 自然人的个人信息受法律保护。\n\n"
        "第三条 在中华人民共和国境内处理自然人个人信息的活动，适用本法。\n"
    )
    chunks = chunker.chunk(text)
    # Should produce: chapter, article1, article2, article3
    article_chunks = [c for c in chunks if c.structural_level == "article"]
    assert len(article_chunks) == 3
    assert article_chunks[0].article_no == "一" or article_chunks[0].article_no == "1"


def test_chunker_returns_structural_path() -> None:
    chunker = ChineseLegalChunker(source_id="CN-LAW-002", title="个人信息保护法")
    text = (
        "第二章 个人信息处理规则\n\n"
        "第十三条 符合下列情形之一的，个人信息处理者方可处理个人信息：\n"
        "（一）取得个人的同意；\n"
        "（二）为订立、履行个人作为一方当事人的合同所必需。\n"
    )
    chunks = chunker.chunk(text)
    levels = {c.structural_level for c in chunks}
    assert "chapter" in levels
    assert "article" in levels


def test_article_pattern_matches_numeric() -> None:
    assert ARTICLE_PATTERN.match("第5条")
    assert ARTICLE_PATTERN.match("第十三条")


def test_chapter_pattern_matches() -> None:
    assert CHAPTER_PATTERN.match("第一章")
    assert CHAPTER_PATTERN.match("第十二章")
