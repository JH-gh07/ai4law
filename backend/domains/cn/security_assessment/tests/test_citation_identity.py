"""task073 T06-A — build_citations 关系 union + canonical identity fail-closed。"""
from __future__ import annotations

from backend.common.citation.source_identity import SourceIdentityResolver
from backend.common.knowledge.v2 import SourceRegistryEntry
from backend.common.workflow import EvidenceItem, FactItem, IssueItem
from backend.domains.cn.security_assessment.citation_builder import build_citations


def _issue(issue_id: str, fact_refs: list[str]) -> IssueItem:
    return IssueItem(
        issue_id=issue_id,
        title=f"issue {issue_id}",
        description="desc",
        category="consent",
        severity="HIGH",
        fact_refs=fact_refs,
        recommended_action="action",
        affects_outputs=["overview"],
    )


def test_duplicate_merge_unions_all_three_relations_even_when_lower_confidence():
    """低置信度重复项也要 union issue/fact/evidence 三类关系（修复 continue 吞关系）。"""
    issues = [
        _issue("ISSUE-1", ["FACT-1"]),
        _issue("ISSUE-2", ["FACT-2"]),
    ]
    legal_grounding = {
        "by_issue": {
            "ISSUE-1": [
                {
                    "issue_id": "ISSUE-1",
                    "rule_id": "CN-LAW-002-001",
                    "title": "个人信息保护法",
                    "article": "第三十九条",
                    "confidence_score": 0.9,
                },
            ],
            "ISSUE-2": [
                {
                    "issue_id": "ISSUE-2",
                    "rule_id": "CN-LAW-002-001",
                    "title": "个人信息保护法",
                    "article": "第三十九条",
                    "confidence_score": 0.7,  # 更低，旧代码会 continue 吞掉关系
                },
            ],
        },
    }
    facts = [
        FactItem(fact_id="FACT-1", source_type="schema", field_path="a", value=1),
        FactItem(fact_id="FACT-2", source_type="schema", field_path="b", value=2),
    ]
    evidence_chain = [
        EvidenceItem(
            evidence_id="EVID-1",
            claim="c1",
            fact_refs=["FACT-1"],
            rule_refs=["CN-LAW-002-001"],
            conclusion="x",
            confidence=0.3,
            used_by=["ISSUE-1"],
        ),
        EvidenceItem(
            evidence_id="EVID-2",
            claim="c2",
            fact_refs=["FACT-2"],
            rule_refs=["CN-LAW-002-001"],
            conclusion="x",
            confidence=0.3,
            used_by=["ISSUE-2"],
        ),
    ]

    result = build_citations(
        legal_grounding=legal_grounding,
        regulations=[],
        issues=issues,
        facts=facts,
        evidence_chain=evidence_chain,
    )

    assert len(result) == 1
    citation = result[0]
    assert citation.confidence_score == 0.9  # 保留最高置信度
    assert set(citation.related_issue_ids) == {"ISSUE-1", "ISSUE-2"}
    assert set(citation.related_fact_ids) == {"FACT-1", "FACT-2"}
    assert set(citation.related_evidence_ids) == {"EVID-1", "EVID-2"}


def _resolver(*entries: SourceRegistryEntry) -> SourceIdentityResolver:
    return SourceIdentityResolver(entries=list(entries))


def _single_issue_grounding(rule_id: str) -> dict:
    return {
        "by_issue": {
            "ISSUE-1": [
                {
                    "issue_id": "ISSUE-1",
                    "rule_id": rule_id,
                    "title": "个人信息保护法",
                    "article": "第三十九条",
                    "confidence_score": 0.85,
                },
            ],
        },
    }


def test_registered_citation_gets_registry_source_id_and_authoritative_policy():
    resolver = _resolver(
        SourceRegistryEntry(
            source_id="CN-LAW-002-001",
            title="个人信息保护法",
            layer="L1_regulatory_evidence",
            source_kind="law_article",
            review_status="published",
            can_be_cited=True,
            can_enter_external_report=False,  # 权威值：禁止外部报告
            allowed_usage=["internal_review"],
        ),
    )
    result = build_citations(
        legal_grounding=_single_issue_grounding("CN-LAW-002-001"),
        regulations=[],
        issues=[_issue("ISSUE-1", [])],
        source_identity_resolver=resolver,
    )
    assert len(result) == 1
    citation = result[0]
    assert citation.registry_source_id == "CN-LAW-002-001"
    assert citation.can_enter_external_report is False
    assert citation.external_report_allowed is False
    assert citation.allowed_usage == ["internal_review"]


def test_unregistered_citation_fails_closed():
    resolver = _resolver(
        SourceRegistryEntry(
            source_id="CN-LAW-002-001",
            title="个人信息保护法",
            layer="L1_regulatory_evidence",
            source_kind="law_article",
        ),
    )
    result = build_citations(
        legal_grounding=_single_issue_grounding("delilegal-law-某未注册法规"),
        regulations=[],
        issues=[_issue("ISSUE-1", [])],
        source_identity_resolver=resolver,
    )
    assert len(result) == 1
    citation = result[0]
    assert citation.registry_source_id is None
    assert citation.can_enter_external_report is False
    assert citation.external_report_allowed is False
    assert citation.allowed_usage == ["internal_review"]


def test_ineligible_citation_fails_closed():
    resolver = _resolver(
        SourceRegistryEntry(
            source_id="CN-LAW-002-001",
            title="个人信息保护法",
            layer="L1_regulatory_evidence",
            source_kind="law_article",
            review_status="metadata_review_required",
            can_be_cited=True,
        ),
    )
    result = build_citations(
        legal_grounding=_single_issue_grounding("CN-LAW-002-001"),
        regulations=[],
        issues=[_issue("ISSUE-1", [])],
        source_identity_resolver=resolver,
    )
    assert len(result) == 1
    citation = result[0]
    assert citation.registry_source_id == "CN-LAW-002-001"
    assert citation.can_enter_external_report is False
    assert citation.external_report_allowed is False


def test_no_resolver_keeps_legacy_behavior():
    """未传 resolver 时 registry_source_id 保持 None（公共链无行为变化）。"""
    result = build_citations(
        legal_grounding=_single_issue_grounding("CN-LAW-002-001"),
        regulations=[],
        issues=[_issue("ISSUE-1", [])],
    )
    assert len(result) == 1
    assert result[0].registry_source_id is None
