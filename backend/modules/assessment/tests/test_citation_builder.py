from backend.common.citation.models import CitationItem
from backend.common.workflow import EvidenceItem, FactItem, IssueItem
from backend.modules.assessment.citation_builder import (
    _extract_article_number,
    _infer_authority_level,
    _infer_binding_force,
    _infer_citation_type,
    build_citations,
)


def test_extract_article_number_digits() -> None:
    assert _extract_article_number("第三十九条") == "三十九"
    assert _extract_article_number("第5条") == "5"
    assert _extract_article_number("第五条") == "五"


def test_infer_citation_type() -> None:
    assert _infer_citation_type("个人信息保护法", "第三十九条") == "law_article"
    assert _infer_citation_type("数据出境安全评估指南", "第五条") == "official_guide"
    assert _infer_citation_type("个人信息安全规范", "第4条") == "standard_clause"
    assert _infer_citation_type("合同示范文本", "第一条") == "template_requirement"
    assert _infer_citation_type("数据出境安全评估办法", "第五条") == "law_article"


def test_infer_authority_level() -> None:
    assert _infer_authority_level("个人信息保护法") == "high"
    assert _infer_authority_level("数据出境安全评估办法") == "medium"
    assert _infer_authority_level("数据出境安全评估指南") == "low"


def test_infer_binding_force() -> None:
    assert _infer_binding_force("个人信息保护法") == "mandatory"
    assert _infer_binding_force("数据出境安全评估办法") == "mandatory"
    assert _infer_binding_force("数据出境安全评估指南") == "recommended"
    assert _infer_binding_force("某模板文件") == "reference"


def test_build_citations_with_empty_data() -> None:
    result = build_citations(legal_grounding=None, regulations=[], issues=[])
    assert result == []


def test_build_citations_from_legal_grounding() -> None:
    issues = [
        IssueItem(
            issue_id="ISSUE-consent-evidence-missing",
            title="个人信息出境单独同意记录证据不足",
            description="涉及个人信息出境时未验证是否已取得单独同意。",
            category="consent",
            severity="HIGH",
            fact_refs=["FACT-request-pii_count"],
            recommended_action="补充告知和单独同意记录。",
            affects_outputs=["necessity_legal_basis"],
        ),
    ]
    regulations = [
        {
            "source_id": "CN-LAW-002-001",
            "title": "个人信息保护法",
            "article": "第三十九条",
            "snippet": "个人信息处理者向境外提供个人信息的，应当向个人告知...",
        },
    ]
    legal_grounding = {
        "by_issue": {
            "ISSUE-consent-evidence-missing": [
                {
                    "issue_id": "ISSUE-consent-evidence-missing",
                    "rule_id": "CN-LAW-002-001",
                    "title": "个人信息保护法",
                    "article": "第三十九条",
                    "confidence_score": 0.85,
                    "relevance_reason": "关键词重合",
                    "source_version": "v2",
                    "query_context": "consent evidence missing query",
                },
            ],
        },
    }
    evidence_chain = [
        EvidenceItem(
            evidence_id="EVID-001",
            claim="单独同意记录缺失",
            fact_refs=["FACT-request-pii_count"],
            rule_refs=["CN-LAW-002-001"],
            conclusion="证据不足",
            confidence=0.3,
            used_by=["ISSUE-consent-evidence-missing"],
        ),
    ]

    result = build_citations(
        legal_grounding=legal_grounding,
        regulations=regulations,
        issues=issues,
        facts=[
            FactItem(
                fact_id="FACT-request-pii_count",
                source_type="schema",
                field_path="request.pii_count",
                value=200000,
                normalized_value=200000,
                evidence_status="user_claim_only",
                can_support_external_positive_claim=False,
            ),
        ],
        evidence_chain=evidence_chain,
    )

    assert len(result) == 1
    citation = result[0]
    assert citation.title == "个人信息保护法"
    assert citation.article_no == "三十九"
    assert citation.confidence_score == 0.85
    assert citation.citation_type == "law_article"
    assert citation.authority_level == "high"
    assert citation.binding_force == "mandatory"
    assert "ISSUE-consent-evidence-missing" in citation.related_issue_ids
    assert "FACT-request-pii_count" in citation.related_fact_ids
    assert "EVID-001" in citation.related_evidence_ids


def test_build_citations_deduplicates_by_title_and_article() -> None:
    legal_grounding = {
        "by_issue": {
            "ISSUE-1": [
                {
                    "issue_id": "ISSUE-1",
                    "rule_id": "CN-LAW-002-001",
                    "title": "个人信息保护法",
                    "article": "第三十九条",
                    "confidence_score": 0.7,
                    "relevance_reason": "",
                    "source_version": "v2",
                    "query_context": "",
                },
            ],
            "ISSUE-2": [
                {
                    "issue_id": "ISSUE-2",
                    "rule_id": "CN-LAW-002-001",
                    "title": "个人信息保护法",
                    "article": "第三十九条",
                    "confidence_score": 0.9,
                    "relevance_reason": "",
                    "source_version": "v2",
                    "query_context": "",
                },
            ],
        },
    }
    result = build_citations(
        legal_grounding=legal_grounding,
        regulations=[],
        issues=[
            IssueItem(
                issue_id="ISSUE-1",
                title="issue 1",
                description="desc",
                category="consent",
                severity="MEDIUM",
                fact_refs=[],
                recommended_action="action",
                affects_outputs=["overview"],
            ),
            IssueItem(
                issue_id="ISSUE-2",
                title="issue 2",
                description="desc",
                category="consent",
                severity="HIGH",
                fact_refs=[],
                recommended_action="action",
                affects_outputs=["overview"],
            ),
        ],
    )

    assert len(result) == 1
    # Should keep the higher confidence score
    assert result[0].confidence_score == 0.9
    # Should merge issue IDs
    assert "ISSUE-1" in result[0].related_issue_ids
    assert "ISSUE-2" in result[0].related_issue_ids
