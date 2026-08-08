#!/usr/bin/env python3
"""Check citation knowledge-base integrity.

Outputs six metrics required by the migration plan §13.2:

  source_count
  article_row_count
  duplicate_source_article_count   -- must be 0 to pass
  missing_article_ref_count        -- rows with empty article_ref
  missing_source_url_count
  invalid_article_number_count     -- article_ref not parseable to an Arabic number

Exit code: 0 if all blocking checks pass, 1 if any blocking check fails.

Usage
-----
  uv run python scripts/check_citation_source_integrity.py
  uv run python scripts/check_citation_source_integrity.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

# Allow running from repo root without install
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.common.knowledge.paths import regulation_articles_jsonl_path
from backend.services.knowledge_index import _normalize_article_lookup_key


def _load_rows() -> list[dict]:
    path = regulation_articles_jsonl_path()
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def run_checks(rows: list[dict]) -> dict:
    sources = {r.get("source_id", "") for r in rows}

    norm_buckets: dict[tuple[str, str], list[int]] = defaultdict(list)
    for i, r in enumerate(rows):
        key = (
            r.get("source_id", ""),
            _normalize_article_lookup_key(str(r.get("article_ref", ""))),
        )
        norm_buckets[key].append(i)

    duplicates = {k: v for k, v in norm_buckets.items() if len(v) > 1}

    missing_ref = [
        i for i, r in enumerate(rows)
        if not str(r.get("article_ref", "")).strip()
    ]

    missing_url = [
        i for i, r in enumerate(rows)
        if not str(r.get("source_url", "")).strip()
    ]

    def _looks_valid_article(ref: str) -> bool:
        """True if the reference resolves to a non-empty normalized key."""
        return bool(_normalize_article_lookup_key(str(ref)))

    invalid_num = [
        i for i, r in enumerate(rows)
        if not _looks_valid_article(r.get("article_ref", ""))
    ]

    return {
        "source_count": len(sources),
        "article_row_count": len(rows),
        "duplicate_source_article_count": sum(len(v) - 1 for v in duplicates.values()),
        "duplicate_pair_count": len(duplicates),
        "missing_article_ref_count": len(missing_ref),
        "missing_source_url_count": len(missing_url),
        "invalid_article_number_count": len(invalid_num),
        # Detail for repair scripts
        "_duplicate_keys": [
            {"source_id": sid, "article_no": art, "row_indices": idxs}
            for (sid, art), idxs in sorted(duplicates.items())
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Citation source integrity check")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    rows = _load_rows()
    result = run_checks(rows)

    BLOCKING_CHECKS = [
        ("duplicate_source_article_count", 0,
         "Duplicate (source_id, article_no) pairs — must be 0"),
        ("missing_article_ref_count", 0,
         "Rows with empty article_ref — must be 0"),
    ]

    passed = True
    failures = []
    for key, threshold, label in BLOCKING_CHECKS:
        val = result[key]
        if val > threshold:
            passed = False
            failures.append(f"FAIL: {label}: {val} (threshold={threshold})")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"source_count:                   {result['source_count']}")
        print(f"article_row_count:              {result['article_row_count']}")
        print(f"duplicate_source_article_count: {result['duplicate_source_article_count']}"
              f"  (pair_count={result['duplicate_pair_count']})")
        print(f"missing_article_ref_count:      {result['missing_article_ref_count']}")
        print(f"missing_source_url_count:       {result['missing_source_url_count']}")
        print(f"invalid_article_number_count:   {result['invalid_article_number_count']}")
        print()
        if failures:
            for f in failures:
                print(f)
        else:
            print("All blocking checks PASSED.")

        if result["_duplicate_keys"]:
            print(f"\nDuplicate pairs ({result['duplicate_pair_count']}):")
            for entry in result["_duplicate_keys"][:10]:
                print(f"  {entry['source_id']} / {entry['article_no']!r}"
                      f"  rows={entry['row_indices']}")
            if result["duplicate_pair_count"] > 10:
                print(f"  ... and {result['duplicate_pair_count'] - 10} more")

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
