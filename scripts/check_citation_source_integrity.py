#!/usr/bin/env python3
"""Check citation knowledge-base integrity.

Outputs metrics required by the migration plan Phase 4:

  source_count
  article_row_count
  duplicate_source_article_count   -- must be 0 to pass
  missing_article_ref_count        -- rows with empty article_ref
  missing_source_url_count
  invalid_article_number_count     -- article_ref not parseable to an Arabic number
  article_classification           -- resolution-capability breakdown per source
  chinese_numeral_articles         -- articles with Chinese numeral references
  non_numeric_articles             -- articles with no digit in article_ref
  url_coverage_by_source           -- per-source URL completeness

Exit code: 0 if all blocking checks pass, 1 if any blocking check fails.

Usage
-----
  uv run python scripts/check_citation_source_integrity.py
  uv run python scripts/check_citation_source_integrity.py --json
  uv run python scripts/check_citation_source_integrity.py --verbose
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Allow running from repo root without install
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.common.knowledge.paths import regulation_articles_jsonl_path
from backend.services.knowledge_index import _normalize_article_lookup_key

# Chinese numeral set for detection
_CHINESE_NUMERALS = set("一二三四五六七八九十百千万零〇两")

# Source type labels (jurisdiction prefix)
_JURISDICTION_LABELS = {
    "CN": "中国大陆", "EU": "欧盟", "US": "美国",
    "HK": "中国香港", "TW": "中国台湾", "MO": "中国澳门",
    "JP": "日本", "KR": "韩国", "SG": "新加坡",
    "MY": "马来西亚",
}

_SOURCE_TYPE_LABELS = {
    "LAW": "法律", "REG": "法规/规章", "GUIDE": "指南",
    "QA": "问答", "SUP": "补充资料", "TPL": "模板",
    "GOV": "政府文件", "OPS": "操作规范",
    "CA": "州法律", "FED": "联邦法律",
}


def _load_rows() -> list[dict]:
    path = regulation_articles_jsonl_path()
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _classify_articles(rows: list[dict]) -> dict:
    """Classify articles by resolution capability (Phase 4 task 7).

    Returns three categories matching the plan's terminology:
      - article_not_found: article_ref present but normalization yields empty
      - article_not_unique: (source_id, normalized_article) pair appears >1 time
      - article_missing: article_ref is empty/blank
    Also reports: chinese_numeral_count, non_numeric_count, resolution_success_rate.
    """
    missing: list[int] = []       # article_missing
    not_found: list[int] = []     # article_not_found
    norm_buckets: dict[tuple[str, str], list[int]] = defaultdict(list)
    chinese_numeral: list[int] = []
    non_numeric: list[int] = []

    for i, r in enumerate(rows):
        ref = str(r.get("article_ref", "")).strip()
        if not ref:
            missing.append(i)
            continue

        if any(c in _CHINESE_NUMERALS for c in ref):
            chinese_numeral.append(i)

        if not any(c.isdigit() for c in ref):
            non_numeric.append(i)

        norm = _normalize_article_lookup_key(ref)
        if not norm:
            not_found.append(i)
            continue

        key = (r.get("source_id", ""), norm)
        norm_buckets[key].append(i)

    not_unique = {k: v for k, v in norm_buckets.items() if len(v) > 1}
    unique_pairs = len(norm_buckets) - len(not_unique)
    duplicate_extra = sum(len(v) - 1 for v in not_unique.values())
    resolvable = len(rows) - len(missing) - len(not_found) - duplicate_extra

    return {
        # Per the plan's terminology
        "article_missing_count": len(missing),          # empty article_ref
        "article_not_found_count": len(not_found),      # normalization yields empty
        "article_not_unique_pairs": len(not_unique),    # duplicate (source, norm) pairs
        "article_not_unique_extra_rows": duplicate_extra,
        # Additional classification
        "chinese_numeral_article_count": len(chinese_numeral),
        "non_numeric_article_count": len(non_numeric),
        "unique_resolvable_pairs": unique_pairs,
        "total_resolvable_rows": resolvable,
        "resolution_success_rate": round(
            resolvable / max(len(rows), 1) * 100, 1
        ),
        # Detail
        "_article_missing_sample": [
            {"source_id": rows[i].get("source_id", "?"),
             "article_ref": rows[i].get("article_ref", ""),
             "row": i}
            for i in missing[:5]
        ],
        "_article_not_found_sample": [
            {"source_id": rows[i].get("source_id", "?"),
             "article_ref": rows[i].get("article_ref", ""),
             "row": i}
            for i in not_found[:5]
        ],
    }


def _url_coverage_by_source(rows: list[dict]) -> dict:
    """Per-source URL coverage analysis."""
    src_data: dict[str, dict] = defaultdict(lambda: {"total": 0, "with_url": 0})
    for r in rows:
        sid = r.get("source_id", "")
        src_data[sid]["total"] += 1
        if str(r.get("source_url", "")).strip():
            src_data[sid]["with_url"] += 1
        src_data[sid]["jurisdiction"] = sid.split("-")[0] if "-" in sid else "?"
        src_data[sid]["source_type"] = (
            sid.split("-")[1] if len(sid.split("-")) > 1 else "?"
        )
        if "source_title" not in src_data[sid]:
            src_data[sid]["source_title"] = r.get("law_name", "?")

    fully_covered = [sid for sid, d in src_data.items() if d["with_url"] == d["total"] > 0]
    partially_covered = [sid for sid, d in src_data.items() if 0 < d["with_url"] < d["total"]]
    zero_covered = [sid for sid, d in src_data.items() if d["with_url"] == 0]

    return {
        "fully_covered_sources": len(fully_covered),
        "partially_covered_sources": len(partially_covered),
        "zero_url_sources": len(zero_covered),
        "fully_covered_rows": sum(src_data[s]["total"] for s in fully_covered),
        "zero_url_rows": sum(src_data[s]["total"] for s in zero_covered),
        "url_coverage_pct": round(
            sum(d["with_url"] for d in src_data.values())
            / max(sum(d["total"] for d in src_data.values()), 1) * 100, 1
        ),
        "_zero_url_sources": sorted([
            {"source_id": s, "article_count": src_data[s]["total"],
             "jurisdiction": src_data[s]["jurisdiction"],
             "title": src_data[s].get("source_title", "?")}
            for s in zero_covered
        ], key=lambda x: x["article_count"], reverse=True),
    }


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
        return bool(_normalize_article_lookup_key(str(ref)))

    invalid_num = [
        i for i, r in enumerate(rows)
        if not _looks_valid_article(r.get("article_ref", ""))
    ]

    classification = _classify_articles(rows)
    url_coverage = _url_coverage_by_source(rows)

    # Jurisdiction and source type distribution
    juris_dist = Counter(
        r["source_id"].split("-")[0] if "-" in r.get("source_id", "") else "?"
        for r in rows
    )
    type_dist = Counter(
        r["source_id"].split("-")[1] if len(r.get("source_id", "").split("-")) > 1 else "?"
        for r in rows
    )

    return {
        # Core metrics
        "source_count": len(sources),
        "article_row_count": len(rows),
        "duplicate_source_article_count": sum(len(v) - 1 for v in duplicates.values()),
        "duplicate_pair_count": len(duplicates),
        "missing_article_ref_count": len(missing_ref),
        "missing_source_url_count": len(missing_url),
        "invalid_article_number_count": len(invalid_num),
        # Classification (Phase 4 task 7)
        "article_classification": classification,
        # URL coverage
        "url_coverage": url_coverage,
        # Distributions
        "jurisdiction_distribution": {
            j: {"count": c, "label": _JURISDICTION_LABELS.get(j, j)}
            for j, c in juris_dist.most_common()
        },
        "source_type_distribution": {
            t: {"count": c, "label": _SOURCE_TYPE_LABELS.get(t, t)}
            for t, c in type_dist.most_common()
        },
        # Detail for repair scripts
        "_duplicate_keys": [
            {"source_id": sid, "article_no": art, "row_indices": idxs}
            for (sid, art), idxs in sorted(duplicates.items())
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Citation source integrity check")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Show classification breakdown")
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
        ac = result["article_classification"]
        uc = result["url_coverage"]

        print(f"source_count:                   {result['source_count']}")
        print(f"article_row_count:              {result['article_row_count']}")
        print(f"duplicate_source_article_count: {result['duplicate_source_article_count']}"
              f"  (pair_count={result['duplicate_pair_count']})")
        print(f"missing_article_ref_count:      {result['missing_article_ref_count']}")
        print(f"missing_source_url_count:       {result['missing_source_url_count']}")
        print(f"invalid_article_number_count:   {result['invalid_article_number_count']}")
        print()
        print("── Article resolution classification ──")
        print(f"article_missing (empty ref):    {ac['article_missing_count']}")
        print(f"article_not_found (norm=empty): {ac['article_not_found_count']}")
        print(f"article_not_unique pairs:       {ac['article_not_unique_pairs']}"
              f"  (extra rows: {ac['article_not_unique_extra_rows']})")
        print(f"unique resovable pairs:         {ac['unique_resolvable_pairs']}")
        print(f"resolvable rows:                {ac['total_resolvable_rows']}")
        print(f"resolution success rate:        {ac['resolution_success_rate']}%")
        print(f"chinese numeral articles:       {ac['chinese_numeral_article_count']}")
        print(f"non-numeric articles:           {ac['non_numeric_article_count']}")
        print()
        print("── URL coverage ──")
        print(f"fully covered sources:          {uc['fully_covered_sources']}"
              f"  ({uc['fully_covered_rows']} rows)")
        print(f"zero URL sources:               {uc['zero_url_sources']}"
              f"  ({uc['zero_url_rows']} rows)")
        print(f"overall URL coverage:           {uc['url_coverage_pct']}%")
        print()
        if args.verbose:
            print("── Jurisdiction distribution ──")
            for j, info in result["jurisdiction_distribution"].items():
                print(f"  {j} ({info['label']}): {info['count']} articles")
            print()
            print("── Source type distribution ──")
            for t, info in result["source_type_distribution"].items():
                print(f"  {t} ({info['label']}): {info['count']} articles")
            print()
            print("── Zero-URL sources (top 10) ──")
            for s in uc["_zero_url_sources"][:10]:
                print(f"  {s['source_id']} ({s['jurisdiction']})"
                      f" [{s['article_count']}]: {s['title']}")
            if len(uc["_zero_url_sources"]) > 10:
                print(f"  ... and {len(uc['_zero_url_sources']) - 10} more")
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
