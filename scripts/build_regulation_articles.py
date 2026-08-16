#!/usr/bin/env python3
"""Build normalized regulation article JSONL from sources.csv and raw snapshots."""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.common.knowledge.paths import regulation_articles_jsonl_path, sources_csv_path  # noqa: E402

SOURCES_CSV = sources_csv_path()
OUTPUT_JSONL = regulation_articles_jsonl_path()

# Anchor the article heading to the start of a line so that in-sentence
# cross-references ("违反本法第二十三条规定…") are NOT mistaken for a new
# article. The un-anchored form produced duplicate/false fragments that later
# had to be renamed into invalid anchors like "处罚-23-1".
ARTICLE_PATTERN = re.compile(
    r"(?m)^[ \t]*(第[一二三四五六七八九十百千万零〇0-9]{1,10}条)"
)
ENGLISH_ARTICLE_HEADING_PATTERN = re.compile(
    r"(?im)^[ \t]*(?:#{1,6}[ \t]+)?Article[ \t]+([0-9]+(?:\.[0-9]+)*)\b[^\n]*"
)
MARKDOWN_STEP_HEADING_PATTERN = re.compile(
    r"(?im)^[ \t]*#{1,6}[ \t]+Step[ \t]+([0-9]+(?:\.[0-9]+)*)\b[^\n]*"
)
WHITESPACE_PATTERN = re.compile(r"[ \t\x0b\x0c\r]+")
# Bidi/zero-width format characters that survive HTML unescaping in official
# CAC markdown snapshots. They sit between a newline and an article heading
# (e.g. "…组成部分。\n‏第一条 定义"), which silently defeats a
# line-anchored heading regex. Strip them; normalize NBSP to a real space.
_INVISIBLE_PATTERN = re.compile(r"[‎‏​­﻿]")
TAG_PATTERN = re.compile(r"<[^>]+>")
SCRIPT_PATTERN = re.compile(r"<script[^>]*>.*?</script>", flags=re.IGNORECASE | re.DOTALL)
STYLE_PATTERN = re.compile(r"<style[^>]*>.*?</style>", flags=re.IGNORECASE | re.DOTALL)
COMMENT_PATTERN = re.compile(r"<!--.*?-->", flags=re.DOTALL)


def _normalize_space(text: str) -> str:
    text = WHITESPACE_PATTERN.sub(" ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _html_to_text(raw: str) -> str:
    text = COMMENT_PATTERN.sub(" ", raw)
    text = SCRIPT_PATTERN.sub(" ", text)
    text = STYLE_PATTERN.sub(" ", text)
    text = re.sub(r"</(p|div|li|h1|h2|h3|h4|h5|h6|tr|table|section|article|br)>", "\n", text, flags=re.IGNORECASE)
    text = TAG_PATTERN.sub(" ", text)
    text = html.unescape(text)
    text = text.replace("\u3000", " ")
    text = _INVISIBLE_PATTERN.sub("", text)
    text = text.replace("\u00a0", " ")
    return _normalize_space(text)


def _extract_heading_chunks(
    text: str,
    matches: list[re.Match[str]],
    *,
    reference_prefix: str,
) -> list[tuple[str, str]]:
    chunks: list[tuple[str, str]] = []
    for idx, match in enumerate(matches):
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        content = text[match.start():end].strip()
        content = re.sub(r"^#{1,6}[ \t]+", "", content)
        if len(content) >= 40:
            article_ref = f"{reference_prefix}{match.group(1)}"
            chunks.append((article_ref, content[:2500]))
    return chunks


def _extract_article_chunks(text: str) -> list[tuple[str, str]]:
    step_matches = list(MARKDOWN_STEP_HEADING_PATTERN.finditer(text))
    if step_matches:
        chunks = _extract_heading_chunks(text, step_matches, reference_prefix="Step ")
        if chunks:
            return chunks

    english_matches = list(ENGLISH_ARTICLE_HEADING_PATTERN.finditer(text))
    if english_matches:
        chunks = _extract_heading_chunks(text, english_matches, reference_prefix="")
        if chunks:
            return chunks

    matches = list(ARTICLE_PATTERN.finditer(text))
    chunks: list[tuple[str, str]] = []

    if matches:
        for idx, match in enumerate(matches):
            start = match.start()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            article_ref = match.group(1)
            content = text[start:end].strip()
            if len(content) >= 40:
                chunks.append((article_ref, content[:2500]))
        if chunks:
            return chunks

    paragraphs = [line.strip() for line in text.splitlines() if len(line.strip()) >= 30]
    if not paragraphs:
        return [("通则", text[:2500])]

    for idx, para in enumerate(paragraphs[:30], start=1):
        chunks.append((f"段落{idx}", para[:2500]))
    return chunks


def _derive_keywords(row: dict[str, str], article_ref: str, content: str) -> list[str]:
    candidates = [
        row.get("title", ""),
        row.get("path", ""),
        row.get("doc_type", ""),
        article_ref,
    ]
    candidates.extend(re.findall(r"[A-Za-z]{2,}|[\u4e00-\u9fff]{2,8}", content[:200]))

    keywords: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        word = item.strip()
        if not word:
            continue
        lower = word.lower()
        if lower in seen:
            continue
        seen.add(lower)
        keywords.append(word)
        if len(keywords) >= 20:
            break
    return keywords


def build_records(*, source_ids: set[str] | None = None) -> list[dict[str, object]]:
    if not SOURCES_CSV.exists():
        raise FileNotFoundError(f"sources csv not found: {SOURCES_CSV}")

    records: list[dict[str, object]] = []

    with SOURCES_CSV.open("r", encoding="utf-8", newline="") as fp:
        rows = list(csv.DictReader(fp))

    for row in rows:
        source_id = row.get("source_id", "UNKNOWN")
        if source_ids is not None and source_id not in source_ids:
            continue
        snapshot_rel = row.get("snapshot_path", "").strip()
        snapshot_path = ROOT / snapshot_rel if snapshot_rel else None

        if snapshot_path is None or not snapshot_path.exists():
            continue

        raw = snapshot_path.read_text(encoding="utf-8", errors="ignore")
        plain = _html_to_text(raw)
        if not plain:
            continue

        chunks = _extract_article_chunks(plain)
        for idx, (article_ref, content) in enumerate(chunks, start=1):
            article_id = f"{source_id}-{idx:03d}"
            records.append(
                {
                    "article_id": article_id,
                    "jurisdiction": row.get("jurisdiction", ""),
                    "path": row.get("path", ""),
                    "law_name": row.get("title", ""),
                    "article_ref": article_ref,
                    "content": content,
                    "keywords": _derive_keywords(row, article_ref, content),
                    "source_url": row.get("url", ""),
                    "snapshot_path": snapshot_rel,
                    "publish_date": row.get("publish_date", ""),
                    "effective_date": row.get("effective_date", ""),
                    "status": row.get("status", "effective") or "effective",
                    "source_id": source_id,
                    "doc_type": row.get("doc_type", ""),
                    "usage_priority": row.get("usage_priority", "P1"),
                    "layer": row.get("layer", ""),
                }
            )

    return records


def write_jsonl(records: list[dict[str, object]]) -> None:
    OUTPUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_JSONL.open("w", encoding="utf-8") as fp:
        for item in records:
            fp.write(json.dumps(item, ensure_ascii=False) + "\n")


def replace_source_records(records: list[dict[str, object]], source_ids: set[str]) -> None:
    """Replace selected sources without changing unrelated registry rows."""
    generated_by_source = {
        source_id: [row for row in records if row.get("source_id") == source_id]
        for source_id in source_ids
    }
    missing = sorted(source_id for source_id, rows in generated_by_source.items() if not rows)
    if missing:
        raise ValueError(f"no records generated for source_ids: {', '.join(missing)}")

    existing: list[dict[str, object]] = []
    if OUTPUT_JSONL.exists():
        existing = [
            json.loads(line)
            for line in OUTPUT_JSONL.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    merged: list[dict[str, object]] = []
    inserted: set[str] = set()
    for row in existing:
        source_id = str(row.get("source_id", ""))
        if source_id not in source_ids:
            merged.append(row)
            continue
        if source_id not in inserted:
            merged.extend(generated_by_source[source_id])
            inserted.add(source_id)
    for source_id in sorted(source_ids - inserted):
        merged.extend(generated_by_source[source_id])
    write_jsonl(merged)


def print_summary(records: list[dict[str, object]]) -> None:
    by_source: dict[str, int] = defaultdict(int)
    for item in records:
        by_source[str(item.get("source_id", "UNKNOWN"))] += 1

    print(f"generated: {OUTPUT_JSONL}")
    print(f"total_records: {len(records)}")
    print("top_sources:")
    for source_id, count in sorted(by_source.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  - {source_id}: {count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-id",
        action="append",
        dest="source_ids",
        help="Rebuild only this source_id; may be specified more than once.",
    )
    args = parser.parse_args()
    selected_source_ids = set(args.source_ids) if args.source_ids else None
    built = build_records(source_ids=selected_source_ids)
    if selected_source_ids is None:
        write_jsonl(built)
    else:
        replace_source_records(built, selected_source_ids)
    print_summary(built)
