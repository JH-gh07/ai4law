"""task073 T06-A — SourceIdentityResolver 单元测试（registered/unregistered/ineligible）。"""
from __future__ import annotations

from backend.common.citation.source_identity import SourceIdentityResolver
from backend.common.knowledge.v2 import SourceRegistryEntry


def _resolver(entries: list[SourceRegistryEntry]) -> SourceIdentityResolver:
    return SourceIdentityResolver(entries=entries)


def _entry(source_id: str, **overrides) -> SourceRegistryEntry:
    base = {
        "source_id": source_id,
        "title": f"法规-{source_id}",
        "layer": "L1_regulatory_evidence",
        "source_kind": "law_article",
    }
    base.update(overrides)
    return SourceRegistryEntry(**base)


def test_registered_returns_authoritative_identity():
    resolver = _resolver([
        _entry(
            "CN-LAW-002-001",
            review_status="published",
            can_be_cited=True,
            can_enter_external_report=True,
            allowed_usage=["external_report", "internal_review"],
        ),
    ])
    identity = resolver.resolve("CN-LAW-002-001")
    assert identity.status == "REGISTERED"
    assert identity.registry_source_id == "CN-LAW-002-001"
    assert identity.can_be_cited is True
    assert identity.can_enter_external_report is True
    assert identity.allowed_usage == ["external_report", "internal_review"]


def test_unregistered_returns_unregistered():
    resolver = _resolver([_entry("CN-LAW-002-001")])
    identity = resolver.resolve("delilegal-law-某未注册法规")
    assert identity.status == "UNREGISTERED"
    assert identity.registry_source_id is None
    assert identity.can_be_cited is False
    assert identity.can_enter_external_report is False


def test_metadata_review_required_is_ineligible():
    resolver = _resolver([
        _entry("JP-REG-001", review_status="metadata_review_required", can_be_cited=True),
    ])
    identity = resolver.resolve("JP-REG-001")
    assert identity.status == "INELIGIBLE"
    assert identity.can_be_cited is False
    assert identity.can_enter_external_report is False
    assert identity.allowed_usage == ["internal_review"]


def test_can_be_cited_false_is_ineligible():
    resolver = _resolver([
        _entry("CN-SRC-009", review_status="published", can_be_cited=False),
    ])
    identity = resolver.resolve("CN-SRC-009")
    assert identity.status == "INELIGIBLE"
    assert identity.registry_source_id == "CN-SRC-009"
    assert identity.can_be_cited is False


def test_no_fuzzy_promotion_for_partial_match():
    """近似 source_id 绝不 fuzzy 提升为已注册。"""
    resolver = _resolver([_entry("CN-LAW-002-001")])
    identity = resolver.resolve("CN-LAW-002-001-x")
    assert identity.status == "UNREGISTERED"
    assert identity.registry_source_id is None


def test_contains_membership():
    resolver = _resolver([_entry("CN-LAW-002-001")])
    assert "CN-LAW-002-001" in resolver
    assert "CN-LAW-999" not in resolver
