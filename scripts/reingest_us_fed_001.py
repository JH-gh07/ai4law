#!/usr/bin/env python3
"""Rebuild US-FED-001 from exact 28 CFR Part 202 section locators.

The checked-in Markdown snapshot is the offline source of truth. Use --refresh
only when intentionally updating it from the official eCFR versioner API.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from xml.etree import ElementTree

import httpx

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "resources/legal/registry/regulation_articles.jsonl"
SNAPSHOT_PATH = ROOT / "resources/legal/sources/us/snapshots/fr_2025_01_08_eo14117_excerpts.md"
ECFR_API_URL = "https://www.ecfr.gov/api/versioner/v1/full/2025-04-08/title-28.xml?part=202"
ECFR_SECTION_URL = "https://www.ecfr.gov/current/title-28/chapter-I/part-202/section-{}"
FEDERAL_REGISTER_URL = (
    "https://www.federalregister.gov/documents/2025/01/08/2024-31486/"
    "preventing-access-to-us-sensitive-personal-data-and-government-related-data-by-countries-of-concern"
)
SECTION_NUMBERS = (
    "202.205",  # bulk thresholds
    "202.206",  # bulk U.S. sensitive personal data
    "202.209",  # country of concern
    "202.210",  # covered data transaction
    "202.211",  # covered person
    "202.214",  # data brokerage
    "202.219",  # exempt transaction
    "202.243",  # prohibited transaction
    "202.246",  # restricted transaction
    "202.248",  # security requirements
    "202.301",  # prohibited data brokerage
    "202.302",  # onward-transfer prohibition
    "202.303",  # human omic data prohibition
    "202.401",  # restricted transaction authorization
    "202.1001",  # due diligence
    "202.1002",  # audits
    "202.1101",  # recordkeeping
)


def _normalize_text(value: str) -> str:
    value = html.unescape(value).replace("\xa0", " ")
    value = re.sub(r"[\t\r ]+", " ", value)
    return "\n".join(line.strip() for line in value.splitlines() if line.strip())


def _element_text(element: ElementTree.Element) -> str:
    return _normalize_text("".join(element.itertext()))


def extract_sections_from_xml(raw_xml: str) -> dict[str, str]:
    root = ElementTree.fromstring(raw_xml)
    sections: dict[str, str] = {}
    for element in root.iter("DIV8"):
        number = str(element.attrib.get("N", "")).strip()
        if number not in SECTION_NUMBERS:
            continue
        parts = [_element_text(child) for child in element if child.tag in {"HEAD", "P", "FP"}]
        sections[number] = "\n".join(part for part in parts if part)
    _validate_sections(sections)
    return {number: sections[number] for number in SECTION_NUMBERS}


def render_snapshot(sections: dict[str, str]) -> str:
    parts = [
        "# 28 CFR Part 202 - EO 14117 implementing rule selected sections",
        "",
        f"eCFR source (version 2025-04-08): {ECFR_API_URL}",
        f"Federal Register final rule: {FEDERAL_REGISTER_URL}",
        "",
        "This checked-in snapshot is used for offline RAG rebuilds. Each heading is an exact eCFR locator.",
    ]
    for number in SECTION_NUMBERS:
        body = re.sub(rf"^§\s*{re.escape(number)}\s*", "", sections[number], count=1)
        parts.extend(["", f"## 28 CFR § {number}", "", body])
    return "\n".join(parts).rstrip() + "\n"


def parse_snapshot(snapshot: str) -> dict[str, str]:
    pattern = re.compile(
        r"^## 28 CFR § (202\.\d+)\s*\n\n(.*?)(?=\n## 28 CFR § |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    sections = {
        number: f"§ {number} {_normalize_text(body)}"
        for number, body in pattern.findall(snapshot)
        if number in SECTION_NUMBERS
    }
    _validate_sections(sections)
    return {number: sections[number] for number in SECTION_NUMBERS}


def _validate_sections(sections: dict[str, str]) -> None:
    missing = [number for number in SECTION_NUMBERS if number not in sections]
    if missing:
        raise ValueError(f"Missing 28 CFR Part 202 sections: {', '.join(missing)}")
    for number, content in sections.items():
        if len(content) < 100 or not content.startswith(f"§ {number}"):
            raise ValueError(f"Invalid 28 CFR Part 202 section: {number}")


def build_entries(sections: dict[str, str]) -> list[dict]:
    entries: list[dict] = []
    for index, number in enumerate(SECTION_NUMBERS, start=1):
        content = sections[number]
        tokens = re.findall(r"[A-Za-z][A-Za-z'-]{2,}|\d+(?:\.\d+)+", content)
        keywords = list(dict.fromkeys(["28 CFR Part 202", "EO 14117", number, *tokens]))[:20]
        entries.append(
            {
                "article_id": f"US-FED-001-{index:03d}",
                "jurisdiction": "us",
                "path": "all",
                "law_name": "28 CFR Part 202 - EO 14117 implementing rule",
                "article_ref": number,
                "content": content,
                "keywords": keywords,
                "source_url": ECFR_SECTION_URL.format(number),
                "snapshot_path": str(SNAPSHOT_PATH.relative_to(ROOT)),
                "publish_date": "2025-01-08",
                "effective_date": "2025-04-08",
                "status": "effective",
                "source_id": "US-FED-001",
                "doc_type": "administrative_regulation",
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
        if row.get("source_id") == "US-FED-001":
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
    parser.add_argument("--refresh", action="store_true", help="Refresh the snapshot from official eCFR XML")
    parser.add_argument("--dry-run", action="store_true", help="Validate and report without writing files")
    args = parser.parse_args()

    if args.refresh:
        response = httpx.get(ECFR_API_URL, follow_redirects=True, timeout=30)
        response.raise_for_status()
        sections = extract_sections_from_xml(response.text)
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
    print(f"Rebuilt US-FED-001 with {len(entries)} exact sections.")


if __name__ == "__main__":
    main()
