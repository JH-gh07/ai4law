#!/usr/bin/env python3
"""Deduplicate regulation_articles.jsonl for CN-LAW-001.

CN-LAW-001 contains both primary articles (e.g. "第二十三条 国家实行...")
and penalty/enforcement provisions that reference the same article numbers
(e.g. "第二十三条的规定外..."). The latter get a unique suffix so
(source_id, normalized_article_no) is unique.

Usage
-----
    uv run python scripts/fix_cn_law_001_duplicates.py --dry-run   # preview
    uv run python scripts/fix_cn_law_001_duplicates.py              # apply
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.common.knowledge.paths import regulation_articles_jsonl_path
from backend.services.knowledge_index import _normalize_article_lookup_key

_ART_STARTS_RE = re.compile(r"^第[一二三四五六七八九十百千万零〇两0-9]+条\s")


def _is_primary(content: str) -> bool:
    """True if the content starts with the article ordinal — i.e. is the main article."""
    return bool(_ART_STARTS_RE.match(content.strip()))


def main() -> None:
    parser = argparse.ArgumentParser(description="Fix CN-LAW-001 duplicate article keys")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print changes without writing")
    args = parser.parse_args()

    path = regulation_articles_jsonl_path()
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]

    # Build normalized key buckets
    buckets: dict[tuple[str, str], list[int]] = defaultdict(list)
    for i, r in enumerate(rows):
        key = (r.get("source_id", ""),
               _normalize_article_lookup_key(str(r.get("article_ref", ""))))
        buckets[key].append(i)

    dups = {k: v for k, v in buckets.items() if len(v) > 1}
    if not dups:
        print("No duplicates found — nothing to do.")
        return

    print(f"Found {len(dups)} duplicate (source_id, article_no) keys.")
    changes: list[tuple[int, str, str]] = []  # (row_idx, old_ref, new_ref)

    for (sid, art_no), indices in sorted(dups.items()):
        primary_idx = None
        others = []
        for idx in indices:
            content = str(rows[idx].get("content", ""))
            if _is_primary(content) and primary_idx is None:
                primary_idx = idx
            else:
                others.append(idx)

        if primary_idx is None:
            # No clear primary — treat first as primary, rest as extensions
            primary_idx = indices[0]
            others = indices[1:]

        for ext_n, idx in enumerate(others, start=1):
            old_ref = str(rows[idx].get("article_ref", ""))
            new_ref = f"{old_ref}-处罚-{ext_n}" if ext_n == 1 else f"{old_ref}-ext-{ext_n}"
            changes.append((idx, old_ref, new_ref))
            print(f"  {sid} row {idx+1}: {old_ref!r} → {new_ref!r}")
            print(f"    content[:50]: {str(rows[idx].get('content',''))[:50]!r}")

    print(f"\nTotal rows to rename: {len(changes)}")

    if args.dry_run:
        print("(dry-run: no file written)")
        return

    # Apply
    for idx, old_ref, new_ref in changes:
        rows[idx]["article_ref"] = new_ref
        # Update article_id if present
        old_id = str(rows[idx].get("article_id", ""))
        if old_id:
            rows[idx]["article_id"] = old_id.replace(
                _normalize_article_lookup_key(old_ref),
                _normalize_article_lookup_key(new_ref),
            )

    new_content = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n"
    path.write_text(new_content, encoding="utf-8")
    print(f"\nWritten {len(rows)} rows → {path}")


if __name__ == "__main__":
    main()
