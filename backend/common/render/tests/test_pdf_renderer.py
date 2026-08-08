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


def test_pdf_renderer_accepts_five_column_remediation_table(tmp_path: Path) -> None:
    markdown = """\
| 序号 | 已识别风险项 | 具体整改措施 | 责任部门 | 计划完成时间 |
| --- | --- | --- | --- | --- |
| 1 | 告知不充分：隐私政策未明确列明境外接收方SeaCommerce Pte. Ltd.的名称与联系方式。 | 依据《中华人民共和国个人信息保护法》第三十九条，修订并发布新版《隐私政策》，在“个人信息跨境提供”章节单独、明确告知境外接收方的完整名称、所在地、联系方式及处理目的 [8]。 | 法务合规部、产品部 | 2025年XX月XX日 |
| 2 | 同意管理缺陷：缺乏覆盖全部50万目标用户的批量同意记录证明；敏感个人信息（如推断健康状态的偏好标签）的单独同意获取存疑。 | 1. 系统后台生成并归档覆盖本次出境全部用户的同意记录日志，确保可验证、可审计。<br>2. 重新评估“ProductCategoryPreference”等字段，对确属敏感个人信息的，设计并实施单独的告知与同意流程，确保取得符合法律要求的单独同意 [13]。 | 技术部、数据合规部 | 2025年XX月XX日 |
"""

    path = PdfRenderer().from_markdown(
        markdown,
        tmp_path / "five-column-table.pdf",
        title="PIPIA 整改计划",
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
