from pathlib import Path
from typing import Iterable


def render_markdown_report(output_path: Path, title: str, sections: Iterable[tuple[str, str]]) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", ""]
    for header, content in sections:
        lines.append(f"## {header}")
        lines.append(content)
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
