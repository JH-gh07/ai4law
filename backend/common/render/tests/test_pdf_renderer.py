from pathlib import Path

import pytest
from pypdf import PdfReader

from backend.common.render.pdf_renderer import PdfRenderer


def _assert_valid_pdf(path: Path) -> None:
    assert path.read_bytes().startswith(b"%PDF")
    assert len(PdfReader(str(path)).pages) >= 1


def test_pdf_renderer_accepts_markdown(tmp_path: Path) -> None:
    path = PdfRenderer().from_markdown(
        "## 风险\n\n- 第一项\n- 第二项\n\n| 项目 | 状态 |\n| --- | --- |\n| A | 高 |",
        tmp_path / "markdown.pdf",
        title="报告",
    )
    _assert_valid_pdf(path)


def test_pdf_renderer_accepts_sections(tmp_path: Path) -> None:
    path = PdfRenderer().from_sections(
        tmp_path / "sections.pdf",
        "报告",
        [("执行摘要", "结论")],
    )
    _assert_valid_pdf(path)


def test_pdf_renderer_accepts_markdown_template(tmp_path: Path) -> None:
    template = tmp_path / "template.md"
    template.write_text("# {{company}}\n\n{{content}}", encoding="utf-8")
    path = PdfRenderer().from_template(
        tmp_path / "template.pdf",
        "报告",
        template,
        {"company": "示例公司", "content": "合规内容"},
    )
    _assert_valid_pdf(path)


def test_pdf_renderer_surfaces_missing_template(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        PdfRenderer().from_template(
            tmp_path / "missing.pdf",
            "报告",
            tmp_path / "missing.md",
            {},
        )
