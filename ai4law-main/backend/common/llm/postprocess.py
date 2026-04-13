from __future__ import annotations

import re


def ensure_paragraph_citations(
    text: str,
    citations: list[str] | None,
    max_items: int = 3,
) -> str:
    if not text:
        return text
    items = [str(c).strip() for c in (citations or []) if str(c).strip()]
    basis = "；".join(items[:max_items]) if items else "未检索到"

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    rendered: list[str] = []
    for paragraph in paragraphs:
        if "【依据：" in paragraph:
            rendered.append(paragraph)
            continue
        rendered.append(f"{paragraph} 【依据：{basis}】")
    return "\n\n".join(rendered)
