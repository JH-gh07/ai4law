from scripts.reingest_us_ca_001 import (
    SECTION_NUMBERS,
    build_entries,
    extract_sections_from_html,
    parse_snapshot,
    render_snapshot,
    replace_source_entries,
)


def _section(number: str) -> str:
    return f"{number}.\nTitle\n" + ("A consumer has an enforceable privacy right. " * 8)


def test_us_ca_001_round_trips_exact_civil_code_locators() -> None:
    raw_html = "".join(
        f'<div align="left"><p><h6>{number}.</h6></p><p>{"rule " * 80}</p></div>'
        for number in SECTION_NUMBERS
    )

    sections = extract_sections_from_html(raw_html)
    restored = parse_snapshot(render_snapshot(sections))

    assert list(restored) == list(SECTION_NUMBERS)
    assert all(content.startswith(f"{number}.") for number, content in restored.items())


def test_us_ca_001_replaces_legacy_paragraph_rows_with_exact_sections() -> None:
    sections = {number: _section(number) for number in SECTION_NUMBERS}
    entries = build_entries(sections)
    current = [
        '{"source_id":"OTHER","article_ref":"Article 1"}',
        '{"source_id":"US-CA-001","article_ref":"段落1"}',
        '{"source_id":"US-CA-001","article_ref":"段落2"}',
    ]

    updated = replace_source_entries(current, entries)

    assert len(updated) == len(SECTION_NUMBERS) + 1
    assert all("段落" not in line for line in updated)
    assert any('"article_ref": "1798.120"' in line for line in updated)
    assert any('"article_ref": "1798.121"' in line for line in updated)
