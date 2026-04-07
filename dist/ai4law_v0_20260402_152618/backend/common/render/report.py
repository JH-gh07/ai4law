from pathlib import Path
from typing import Iterable

from docx import Document


def render_markdown_report(output_path: Path, title: str, sections: Iterable[tuple[str, str]]) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", ""]
    for header, content in sections:
        lines.append(f"## {header}")
        lines.append(content)
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def render_docx_report(output_path: Path, title: str, sections: Iterable[tuple[str, str]]) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    doc.add_heading(title, level=0)

    for header, content in sections:
        doc.add_heading(header, level=1)
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("- "):
                doc.add_paragraph(stripped[2:], style="List Bullet")
            else:
                doc.add_paragraph(stripped)

    doc.save(str(output_path))
    return output_path
