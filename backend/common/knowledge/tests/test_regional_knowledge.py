"""T10 — regional knowledge base closed-loop invariants.

These tests pin the non-pollution contract: regional jurisdictions (jp/my/kr/hk/
vn/sg/tw/mo) are registered and indexable, but they never leak into the CN/EU/US
retrieval module pools.
"""
from __future__ import annotations

from backend.common.knowledge.builders_v2 import build_legal_chunks_intl
from backend.common.knowledge.registry import (
    REGIONAL_JURISDICTIONS,
    build_source_registry_from_sources_csv,
)

# JP/KR identity quarantine (task065 remediation, Phase 1). These sources are
# isolated from formal legal conclusions and article-number citation until a
# legal-domain expert signs off their identity.
QUARANTINED_SOURCE_IDS = {
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


def test_registry_includes_all_regional_sources() -> None:
    entries = build_source_registry_from_sources_csv()
    regional = [e for e in entries if e.jurisdiction in REGIONAL_JURISDICTIONS]
    assert len(regional) == 51
    # All eight regional jurisdictions are represented.
    assert {e.jurisdiction for e in regional} == REGIONAL_JURISDICTIONS


def test_regional_sources_never_pollute_module_pools() -> None:
    entries = build_source_registry_from_sources_csv()
    for entry in entries:
        if entry.jurisdiction in REGIONAL_JURISDICTIONS:
            assert entry.modules == [], entry.source_id
            assert (entry.metadata or {}).get("intl_module", "").startswith("intl_"), entry.source_id


def test_regional_snapshot_paths_are_populated_when_pdf_exists() -> None:
    entries = build_source_registry_from_sources_csv()
    regional = [e for e in entries if e.jurisdiction in REGIONAL_JURISDICTIONS]
    with_snapshot = [e for e in regional if (e.metadata or {}).get("snapshot_path")]
    # 49 of 51 regional sources have an on-disk PDF; JP-LAW-009 and KR-GUIDE-006
    # are the two known expert-review gaps without a PDF.
    assert len(with_snapshot) == 49
    missing = sorted(e.source_id for e in regional if e not in with_snapshot)
    assert missing == ["JP-LAW-009", "KR-GUIDE-006"]


def test_intl_legal_chunks_are_isolated_and_citable() -> None:
    chunks = build_legal_chunks_intl()
    assert chunks
    for chunk in chunks:
        assert chunk.jurisdiction in REGIONAL_JURISDICTIONS, chunk.chunk_id
        assert chunk.module == "", chunk.chunk_id
        assert chunk.citation_anchor, chunk.chunk_id
        assert chunk.snapshot_path, chunk.chunk_id


def test_quarantined_sources_are_not_citable() -> None:
    entries = {
        e.source_id: e
        for e in build_source_registry_from_sources_csv()
        if e.source_id in QUARANTINED_SOURCE_IDS
    }
    assert set(entries) == QUARANTINED_SOURCE_IDS
    for sid, entry in entries.items():
        assert entry.review_status == "metadata_review_required", sid
        assert entry.can_be_cited is False, sid
        assert entry.can_enter_external_report is False, sid
        assert list(entry.allowed_usage) == ["internal_review"], sid


def test_quarantined_intl_chunks_are_not_citable() -> None:
    chunks = build_legal_chunks_intl()
    quarantined = [c for c in chunks if c.source_id in QUARANTINED_SOURCE_IDS]
    assert quarantined, "expected quarantined sources with articles to be present"
    for chunk in quarantined:
        assert chunk.can_be_cited is False, chunk.chunk_id
        assert chunk.can_enter_external_report is False, chunk.chunk_id
        assert list(chunk.allowed_usage) == ["internal_review"], chunk.chunk_id


def test_non_quarantined_sources_remain_citable() -> None:
    entries = [
        e
        for e in build_source_registry_from_sources_csv()
        if e.jurisdiction in REGIONAL_JURISDICTIONS and e.source_id not in QUARANTINED_SOURCE_IDS
    ]
    assert entries
    for entry in entries:
        assert entry.review_status == "published", entry.source_id
        assert entry.can_be_cited is True, entry.source_id
        assert entry.can_enter_external_report is True, entry.source_id
