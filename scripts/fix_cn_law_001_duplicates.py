#!/usr/bin/env python3
"""Mark duplicate regulation_articles.jsonl rows without corrupting article_ref.

Legacy behavior appended ``-处罚-N``/``-ext-N`` onto ``article_ref`` to make
``(source_id, normalized_article_no)`` unique. That suffix leaked downstream as
an invalid article locator ("处罚-23-1") and rendered verbatim into reports.

With the article splitter now anchoring on line-start headings, cross-reference
fragments are no longer emitted as separate rows, so duplicates are no longer
expected. If duplicates still appear, this script marks the non-primary row with
``structured_payload.role="penalty_extension"`` and a ``disambiguation`` ordinal,
leaving ``article_ref`` as the real article number.

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
    marked = 0

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
            # Never rewrite article_ref into an invalid anchor. The old code
            # produced "处罚-23-1"/"第X条-处罚-1" which downstream treated as a
            # real article locator and rendered verbatim into reports. Keep the
            # real article number and record disambiguation in structured_payload.
            payload = dict(rows[idx].get("structured_payload") or {})
            payload["role"] = "penalty_extension"
            payload["disambiguation"] = ext_n
            rows[idx]["structured_payload"] = payload
            marked += 1
            print(f"  {sid} row {idx+1}: {old_ref!r} (role=penalty_extension, disambiguation={ext_n})")
            print(f"    content[:50]: {str(rows[idx].get('content',''))[:50]!r}")

    print(f"\nTotal rows marked (article_ref unchanged): {marked}")

    if args.dry_run:
        print("(dry-run: no file written)")
        return

    new_content = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n"
    path.write_text(new_content, encoding="utf-8")
    print(f"\nWritten {len(rows)} rows → {path}")


if __name__ == "__main__":
    main()
