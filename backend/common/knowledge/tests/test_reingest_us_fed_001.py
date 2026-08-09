from scripts.reingest_us_fed_001 import (
    ECFR_API_URL,
    FEDERAL_REGISTER_URL,
    SECTION_NUMBERS,
    build_entries,
    extract_sections_from_xml,
    parse_snapshot,
    render_snapshot,
    replace_source_entries,
)


def _section_xml(number: str) -> str:
    body = "The regulated transaction must satisfy the requirements. " * 8
    return (
        f'<DIV8 N="{number}" TYPE="SECTION">'
        f"<HEAD>§ {number} Test heading.</HEAD>"
        f"<P>(a) {body}</P>"
        "</DIV8>"
    )


def test_us_fed_001_round_trips_exact_ecfr_locators() -> None:
    raw_xml = "<DIV5>" + "".join(_section_xml(number) for number in SECTION_NUMBERS) + "</DIV5>"

    sections = extract_sections_from_xml(raw_xml)
    restored = parse_snapshot(render_snapshot(sections))

    assert list(restored) == list(SECTION_NUMBERS)
    assert all(content.startswith(f"§ {number}") for number, content in restored.items())


def test_us_fed_001_replaces_legacy_paragraph_rows_with_exact_sections() -> None:
    raw_xml = "<DIV5>" + "".join(_section_xml(number) for number in SECTION_NUMBERS) + "</DIV5>"
    entries = build_entries(extract_sections_from_xml(raw_xml))
    current = [
        '{"source_id":"OTHER","article_ref":"Article 1"}',
        '{"source_id":"US-FED-001","article_ref":"段落1"}',
        '{"source_id":"US-FED-001","article_ref":"段落2"}',
    ]

    updated = replace_source_entries(current, entries)

    assert len(updated) == len(SECTION_NUMBERS) + 1
    assert all("段落" not in line for line in updated)
    assert any('"article_ref": "202.301"' in line for line in updated)
    assert any('"article_ref": "202.1101"' in line for line in updated)


def test_us_fed_001_entries_use_official_exact_section_urls() -> None:
    raw_xml = "<DIV5>" + "".join(_section_xml(number) for number in SECTION_NUMBERS) + "</DIV5>"

    entries = build_entries(extract_sections_from_xml(raw_xml))

    assert ECFR_API_URL.startswith("https://www.ecfr.gov/api/versioner/")
    assert "/2024-31486/" in FEDERAL_REGISTER_URL
    assert all(entry["article_ref"] in SECTION_NUMBERS for entry in entries)
    assert all(
        entry["source_url"].endswith(f"/section-{entry['article_ref']}")
        for entry in entries
    )
