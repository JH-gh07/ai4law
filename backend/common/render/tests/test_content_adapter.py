from backend.common.render.content_adapter import ContentAdapter
from backend.common.render.markdown_renderer import MarkdownRenderer
from backend.common.render.report_model import (
    DividerBlock,
    HeadingBlock,
    ListBlock,
    Paragraph,
    TableBlock,
)


def test_from_chapters_preserves_nested_markdown_structure() -> None:
    document = ContentAdapter.from_chapters(
        title="诊断报告",
        chapters=[
            {
                "title": "结论",
                "content": (
                    "### 适用条件\n\n"
                    "这是**重要**结论。\n\n"
                    "- 条件一\n- 条件二\n\n"
                    "| 项目 | 状态 |\n| --- | --- |\n| 传输 | 高风险 |\n\n---"
                ),
            }
        ],
        module="diagnosis",
    )

    blocks = document.sections[0].blocks
    assert [type(block) for block in blocks] == [
        HeadingBlock,
        Paragraph,
        ListBlock,
        TableBlock,
        DividerBlock,
    ]
    assert MarkdownRenderer().render(document).count("### 适用条件") == 1
    assert "| 传输 | 高风险 |" in MarkdownRenderer().render(document)


def test_malformed_table_is_kept_as_text_instead_of_dropped() -> None:
    document = ContentAdapter.from_chapters(
        title="报告",
        chapters=[{"title": "内容", "content": "A | B\n只有一行"}],
    )

    assert isinstance(document.sections[0].blocks[0], Paragraph)
    assert "A | B" in MarkdownRenderer().render(document)


def test_review_adapter_keeps_each_review_paragraph_separate() -> None:
    document = ContentAdapter.from_review_sections(
        "审查报告",
        [("问题", ["第一项", "第二项"])],
        company_name="示例公司",
    )

    assert [block.text for block in document.sections[0].blocks] == ["第一项", "第二项"]
