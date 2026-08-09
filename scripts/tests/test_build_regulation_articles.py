import json

from scripts import build_regulation_articles
from scripts.build_regulation_articles import _extract_article_chunks


def test_extract_article_chunks_recognizes_english_markdown_headings() -> None:
    text = """# GDPR excerpts

Source: https://eur-lex.europa.eu/

## Article 44 (General principle for transfers)

Any transfer of personal data shall comply with Chapter V.

## Article 46 (Transfers subject to appropriate safeguards)

A controller or processor may transfer personal data only if appropriate safeguards are provided.
"""

    chunks = _extract_article_chunks(text)

    assert [article_ref for article_ref, _ in chunks] == ["44", "46"]
    assert chunks[0][1].startswith("Article 44")
    assert chunks[1][1].startswith("Article 46")
    assert all("GDPR excerpts" not in content for _, content in chunks)
    assert all("Source:" not in content for _, content in chunks)


def test_extract_article_chunks_recognizes_markdown_step_headings() -> None:
    text = """# EDPB Recommendations 01/2020

## Step 1: Know your transfers

Map all transfers, including onward transfers and remote access.

## Step 3: Assess transfer tool effectiveness

Assess whether the Article 46 transfer tool is effective in practice.
"""

    chunks = _extract_article_chunks(text)

    assert [article_ref for article_ref, _ in chunks] == ["Step 1", "Step 3"]
    assert chunks[1][1].startswith("Step 3")
    assert "effective in practice" in chunks[1][1]


def test_replace_source_records_preserves_unrelated_rows(monkeypatch, tmp_path) -> None:
    output = tmp_path / "regulation_articles.jsonl"
    original_rows = [
        {"article_id": "OTHER-001", "source_id": "OTHER"},
        {"article_id": "TARGET-OLD", "source_id": "TARGET"},
        {"article_id": "OTHER-002", "source_id": "OTHER"},
    ]
    output.write_text(
        "".join(json.dumps(row) + "\n" for row in original_rows),
        encoding="utf-8",
    )
    monkeypatch.setattr(build_regulation_articles, "OUTPUT_JSONL", output)

    build_regulation_articles.replace_source_records(
        [{"article_id": "TARGET-NEW", "source_id": "TARGET"}],
        {"TARGET"},
    )

    actual_rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert actual_rows == [
        original_rows[0],
        {"article_id": "TARGET-NEW", "source_id": "TARGET"},
        original_rows[2],
    ]
