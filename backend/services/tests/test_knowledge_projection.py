"""Pins the JP/KR quarantine surfacing in the user-facing source catalog.

Quarantined sources (`review_status=metadata_review_required`) must never be
presented as "可直接引用条文号" regardless of any stale CSV `usage`/`report_usage`
wording — the citation policy is authoritative over static metadata text.
"""
from __future__ import annotations

from backend.services.knowledge_projection import build_user_source_catalog

QUARANTINED = {
    "JP-LAW-008",
    "JP-LAW-009",
    "JP-GUIDE-004",
    "JP-GUIDE-005",
    "JP-GUIDE-006",
    "JP-GUIDE-007",
    "KR-GUIDE-004",
    "KR-GUIDE-005",
    "KR-GUIDE-006",
    "KR-LAW-007",
}


def test_quarantined_sources_are_not_presented_as_citable() -> None:
    catalog = {row["source_id"]: row for row in build_user_source_catalog()}
    # Metadata-only quarantined sources (no PDF, no articles) are excluded from the
    # user catalog entirely — they can never be cited. The rest must be surfaced as
    # internal-only.
    for sid in sorted(QUARANTINED):
        row = catalog.get(sid)
        if row is None:
            assert sid in {"JP-LAW-009", "KR-GUIDE-006"}, sid
            continue
        assert row["report_usage"] == "不直接写入正式报告", (sid, row["report_usage"])
        assert row["usage"] == "仅供内部参考", (sid, row["usage"])


def test_non_quarantined_sources_keep_csv_report_usage() -> None:
    catalog = {row["source_id"]: row for row in build_user_source_catalog()}
    # JP-LAW-001 is a normal citable JP law; it must keep its CSV wording.
    assert catalog["JP-LAW-001"]["report_usage"] == "可直接引用条文号"
    assert catalog["JP-LAW-001"]["usage"] == "审查基准"
