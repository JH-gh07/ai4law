from __future__ import annotations

import json
import re
from typing import Any


def dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def loads(raw: str | None, default: Any):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def repair_llm_json(text: str) -> str:
    """Repair common JSON formatting errors produced by LLM outputs.

    Handles (in order):
      1. Trailing commas before ``}`` or ``]``
      2. Missing commas between adjacent values (cross-line and same-line)
      3. Extra comma + newline before closing ``}`` or ``]``

    This is intentionally conservative — it should never alter valid JSON.
    """
    if not text:
        return text

    # 1. Remove trailing commas: ,} → }  and ,] → ]
    text = re.sub(r",(\s*[}\]])", r"\1", text)

    # 2. Insert missing comma between adjacent JSON values split across lines.
    #    Covers: "...<nl>  "...    "..."<nl>  {...    }<nl>  {...    ]<nl>  "...
    text = re.sub(r'("\s*\n\s*")', '",\n"', text)
    text = re.sub(r'("|]|}|\d)\s*\n\s*("|\{|\[)', r'\1,\n\2', text)

    # 3. Missing comma between two same-line key-value pairs
    #    "...": ... "..."  →  "...": ..., "..."
    text = re.sub(r'(")\s+(")', r'\1, \2', text)
    #    } "..."  →  }, "..."
    text = re.sub(r'(\}|\]|true|false|null|\d+)\s+(")', r'\1, \2', text)

    # 4. Extra comma + newline before closing (LLM hallucinated separator)
    text = re.sub(r",(\s*\n\s*})", r"\1", text)
    text = re.sub(r",(\s*\n\s*])", r"\1", text)

    return text
