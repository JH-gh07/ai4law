"""Citation quality validator — checks whether citations truly support their associated issues.

Provides CitationSupportLevel grading: exact_support, partial_support, background_only, irrelevant.
Ensures external reports only use exact_support and partial_support citations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

CitationSupportLevel = Literal["exact_support", "partial_support", "background_only", "irrelevant"]


# ── Citation requirement map — per issue category, which articles must be cited ──
_CATEGORY_REQUIRED_ARTICLES: dict[str, list[dict[str, Any]]] = {
    "consent": [
        {"title": "个人信息保护法", "article": "第三十九条", "level": "exact_support"},
        {"title": "个人信息保护法", "article": "第十三条", "level": "partial_support"},
        {"title": "个人信息保护法", "article": "第十七条", "level": "partial_support"},
    ],
    "legal_document": [
        {"title": "数据出境安全评估办法", "article": "第九条", "level": "exact_support"},
        {"title": "个人信息保护法", "article": "第三十八条", "level": "partial_support"},
    ],
    "contract": [
        {"title": "数据出境安全评估办法", "article": "第九条", "level": "exact_support"},
        {"title": "个人信息出境标准合同办法", "article": "第六条", "level": "partial_support"},
    ],
    "onward_transfer": [
        {"title": "数据出境安全评估办法", "article": "第九条", "level": "exact_support"},
        {"title": "个人信息保护法", "article": "第三十八条", "level": "partial_support"},
    ],
    "data_scope": [
        {"title": "数据出境安全评估办法", "article": "第五条", "level": "exact_support"},
        {"title": "个人信息保护法", "article": "第六条", "level": "partial_support"},
    ],
    "data_classification": [
        {"title": "数据安全法", "article": "第二十一条", "level": "exact_support"},
        {"title": "数据出境安全评估办法", "article": "第四条", "level": "partial_support"},
    ],
    "necessity": [
        {"title": "个人信息保护法", "article": "第六条", "level": "exact_support"},
        {"title": "数据出境安全评估办法", "article": "第五条", "level": "partial_support"},
    ],
    "recipient": [
        {"title": "数据出境安全评估办法", "article": "第五条", "level": "exact_support"},
        {"title": "个人信息保护法", "article": "第三十八条", "level": "partial_support"},
    ],
    "security_measure": [
        {"title": "数据出境安全评估办法", "article": "第五条", "level": "exact_support"},
        {"title": "个人信息保护法", "article": "第五十一条", "level": "partial_support"},
        {"title": "网络安全法", "article": "第二十一条", "level": "partial_support"},
    ],
    "documentation": [
        {"title": "数据出境安全评估办法", "article": "第六条", "level": "exact_support"},
        {"title": "数据出境安全评估申报指南", "article": "", "level": "partial_support"},
    ],
    "internal_approval": [
        {"title": "数据出境安全评估办法", "article": "第八条", "level": "partial_support"},
    ],
}


@dataclass
class CitationValidation:
    issue_id: str
    citation_title: str
    citation_article: str
    support_level: CitationSupportLevel
    reason: str = ""
    recommended_citation: str = ""


def _normalize(text: str) -> str:
    return (text or "").replace("《", "").replace("》", "").strip().lower()


def validate_citation_for_issue(
    issue_id: str,
    issue_category: str,
    citation_title: str,
    citation_article: str,
) -> CitationSupportLevel:
    """Check whether a citation provides adequate support for a given issue.

    Returns: exact_support | partial_support | background_only | irrelevant
    """
    required = _CATEGORY_REQUIRED_ARTICLES.get(issue_category, [])
    if not required:
        return "background_only"

    title_norm = _normalize(citation_title)
    article_norm = _normalize(citation_article)

    for req in required:
        req_title = _normalize(req["title"])
        req_article = _normalize(req.get("article", ""))

        # Exact match: title and article both match
        if req_title in title_norm and (not req_article or req_article in article_norm):
            return req["level"]

        # Partial match: title matches but article doesn't
        if req_title in title_norm:
            return "partial_support"

    # No match in required articles — check if it's at least tangentially related
    cn_law_keywords = ["个人信息保护法", "数据安全法", "网络安全法", "安全评估办法", "标准合同办法"]
    is_china_data_law = any(kw in title_norm for kw in cn_law_keywords)
    if is_china_data_law:
        return "background_only"

    return "irrelevant"


def validate_all_citations(
    issues: list[Any],
    legal_grounding: dict[str, Any] | None,
) -> list[CitationValidation]:
    """Validate citation relevance for all issues in the legal grounding."""
    validations: list[CitationValidation] = []

    by_issue = (legal_grounding or {}).get("by_issue", {})
    for issue in issues:
        bindings = by_issue.get(issue.issue_id, [])
        if not isinstance(bindings, list):
            continue

        for binding in bindings:
            if not isinstance(binding, dict):
                continue
            title = binding.get("title", "")
            article = binding.get("article", "")
            level = validate_citation_for_issue(
                issue.issue_id, issue.category, title, article
            )
            validations.append(CitationValidation(
                issue_id=issue.issue_id,
                citation_title=title,
                citation_article=article,
                support_level=level,
                reason=f"Category '{issue.category}' requires specific articles; got '{title} {article}'",
            ))

    return validations


def filter_external_citations(
    validations: list[CitationValidation],
) -> list[CitationValidation]:
    """Keep only exact_support and partial_support for external reports."""
    return [v for v in validations if v.support_level in ("exact_support", "partial_support")]


def get_weak_citation_warnings(
    validations: list[CitationValidation],
) -> list[str]:
    """Generate warnings for weak/irrelevant citations."""
    warnings: list[str] = []
    for v in validations:
        if v.support_level in ("background_only", "irrelevant"):
            warnings.append(
                f"Issue '{v.issue_id}' uses '{v.citation_title} {v.citation_article}' "
                f"— support level: {v.support_level}. {v.reason}"
            )
    return warnings
