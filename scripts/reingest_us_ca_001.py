#!/usr/bin/env python3
"""Rebuild US-CA-001 from exact California Civil Code section locators.

The checked-in Markdown snapshot is the offline source of truth. Use --refresh
only when intentionally updating it from California Legislative Information.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "resources/legal/registry/regulation_articles.jsonl"
SNAPSHOT_PATH = ROOT / "resources/legal/sources/us/snapshots/ca_civil_code_cpra_sections.md"
SOURCE_URL = (
    "https://www.leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?"
    "article=&chapter=&division=3.&lawCode=CIV&part=4.&title=1.81.5."
)
SECTION_NUMBERS = (
    "1798.100",
    "1798.105",
    "1798.106",
    "1798.110",
    "1798.115",
    "1798.120",
    "1798.121",
    "1798.125",
    "1798.130",
    "1798.135",
    "1798.140",
    "1798.145",
)


class _SectionDivParser(HTMLParser):
    """Collect the top-level ``div align=left`` blocks used by LegInfo."""

    def __init__(self) -> None:
        super().__init__()
        self.depth = 0
        self.buffer: list[str] = []
        self.blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if self.depth:
            self.depth += 1
        elif tag == "div" and attributes.get("align") == "left":
            self.depth = 1
            self.buffer = []
        if self.depth and tag in {"br", "h6", "p"}:
            self.buffer.append("\n")

    def handle_endtag(self, _tag: str) -> None:
        if not self.depth:
            return
        self.depth -= 1
        if self.depth == 0:
            value = _normalize_lines("".join(self.buffer))
            if value:
                self.blocks.append(value)
            self.buffer = []

    def handle_data(self, data: str) -> None:
        if self.depth:
            self.buffer.append(data)


def _normalize_lines(value: str) -> str:
    value = html.unescape(value).replace("\xa0", " ")
    value = re.sub(r"[\t\r ]+", " ", value)
    return "\n".join(line.strip() for line in value.splitlines() if line.strip())


def extract_sections_from_html(raw_html: str) -> dict[str, str]:
    parser = _SectionDivParser()
    parser.feed(raw_html)
    sections: dict[str, str] = {}
    for block in parser.blocks:
        match = re.match(r"^(1798\.\d+)\.\s*\n", block)
        if match and match.group(1) in SECTION_NUMBERS:
            sections[match.group(1)] = block
    _validate_sections(sections)
    return sections


def render_snapshot(sections: dict[str, str]) -> str:
    parts = [
        "# California Civil Code — CCPA/CPRA selected sections",
        "",
        f"Source: {SOURCE_URL}",
        "",
        "This checked-in snapshot is used for offline RAG rebuilds. Each heading is an exact Civil Code locator.",
    ]
    for number in SECTION_NUMBERS:
        body = re.sub(rf"^{re.escape(number)}\.\s*\n", "", sections[number], count=1)
        parts.extend(["", f"## Civil Code § {number}", "", body])
    return "\n".join(parts).rstrip() + "\n"


def parse_snapshot(snapshot: str) -> dict[str, str]:
    pattern = re.compile(
        r"^## Civil Code § (1798\.\d+)\s*\n\n(.*?)(?=\n## Civil Code § |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    sections = {
        number: f"{number}.\n{_normalize_lines(body)}"
        for number, body in pattern.findall(snapshot)
        if number in SECTION_NUMBERS
    }
    _validate_sections(sections)
    return sections


def _validate_sections(sections: dict[str, str]) -> None:
    missing = [number for number in SECTION_NUMBERS if number not in sections]
    if missing:
        raise ValueError(f"Missing California Civil Code sections: {', '.join(missing)}")
    for number, content in sections.items():
        if len(content) < 200 or not content.startswith(f"{number}."):
            raise ValueError(f"Invalid California Civil Code section: {number}")


def build_entries(sections: dict[str, str]) -> list[dict]:
    entries: list[dict] = []
    for index, number in enumerate(SECTION_NUMBERS, start=1):
        content = sections[number]
        tokens = re.findall(r"[A-Za-z][A-Za-z'-]{2,}|\d+(?:\.\d+)+", content)
        keywords = list(dict.fromkeys(["California CPRA/CCPA", "cpra", number, *tokens]))[:20]
        entries.append(
            {
                "article_id": f"US-CA-001-{index:03d}",
                "jurisdiction": "us",
                "path": "privacy",
                "law_name": "California Civil Code — CCPA/CPRA",
                "article_ref": number,
                "content": content,
                "keywords": keywords,
                "source_url": SOURCE_URL,
                "snapshot_path": str(SNAPSHOT_PATH.relative_to(ROOT)),
                "publish_date": "",
                "effective_date": "",
                "status": "effective",
                "source_id": "US-CA-001",
                "doc_type": "law",
                "usage_priority": "P0",
                "layer": "legal_rules",
            }
        )
    return entries


def replace_source_entries(lines: list[str], entries: list[dict]) -> list[str]:
    result: list[str] = []
    inserted = False
    for line in lines:
        row = json.loads(line)
        if row.get("source_id") == "US-CA-001":
            if not inserted:
                result.extend(json.dumps(entry, ensure_ascii=False) for entry in entries)
                inserted = True
            continue
        result.append(line)
    if not inserted:
        result.extend(json.dumps(entry, ensure_ascii=False) for entry in entries)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Refresh the snapshot from official LegInfo")
    parser.add_argument("--dry-run", action="store_true", help="Validate and report without writing files")
    args = parser.parse_args()

    if args.refresh:
        response = httpx.get(SOURCE_URL, follow_redirects=True, timeout=30)
        response.raise_for_status()
        sections = extract_sections_from_html(response.text)
        snapshot = render_snapshot(sections)
    else:
        snapshot = SNAPSHOT_PATH.read_text(encoding="utf-8")
        sections = parse_snapshot(snapshot)

    entries = build_entries(sections)
    current_lines = [line for line in REGISTRY_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    updated_lines = replace_source_entries(current_lines, entries)
    if args.dry_run:
        print(f"Validated {len(entries)} exact sections; registry would contain {len(updated_lines)} rows.")
        return
    if args.refresh:
        SNAPSHOT_PATH.write_text(snapshot, encoding="utf-8")
    REGISTRY_PATH.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
    print(f"Rebuilt US-CA-001 with {len(entries)} exact sections.")


if __name__ == "__main__":
    main()
