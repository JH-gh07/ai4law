"""IR renderers (task067 T03-T06).

Each renderer consumes a v4 ``DocumentIR`` and produces one output format.
Renderers read only the IR (plus the citation registry needed to resolve
stable citation IDs), never legacy chapter/template strings.
"""

from backend.common.reporting.renderers.docx import (
    DocxRenderer,
    DocxRenderError,
    render_docx,
    render_docx_to_file,
)
from backend.common.reporting.renderers.markdown import (
    MarkdownRenderer,
    RenderError,
    render_markdown,
)
from backend.common.reporting.renderers.pdf import (
    FontSpec,
    PdfRenderer,
    PdfRenderError,
    render_pdf,
    render_pdf_to_file,
)

__all__ = [
    "DocxRenderer",
    "DocxRenderError",
    "FontSpec",
    "MarkdownRenderer",
    "PdfRenderer",
    "PdfRenderError",
    "RenderError",
    "render_docx",
    "render_docx_to_file",
    "render_markdown",
    "render_pdf",
    "render_pdf_to_file",
]
