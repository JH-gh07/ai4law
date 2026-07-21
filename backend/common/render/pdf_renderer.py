"""Thin PDF entry point reusing the repository's proven ReportLab renderer."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from backend.common.render.artifacts import render_pdf_report
from backend.common.render.report import render_markdown_template


class PdfRenderer:
    def from_markdown(self, markdown: str, output_path: Path, title: str = "") -> Path:
        return render_pdf_report(output_path, title, [("", markdown)])

    def from_sections(
        self,
        output_path: Path,
        title: str,
        sections: list[tuple[str, str]],
    ) -> Path:
        return render_pdf_report(output_path, title, sections)

    def from_template(
        self,
        output_path: Path,
        title: str,
        template_md: Path,
        mapping: dict[str, str],
    ) -> Path:
        with TemporaryDirectory() as directory:
            markdown_path = Path(directory) / "rendered.md"
            render_markdown_template(markdown_path, template_md, mapping)
            return self.from_markdown(
                markdown_path.read_text(encoding="utf-8"), output_path, title
            )


_PDF_RENDERER = PdfRenderer()


def get_pdf_renderer() -> PdfRenderer:
    return _PDF_RENDERER
