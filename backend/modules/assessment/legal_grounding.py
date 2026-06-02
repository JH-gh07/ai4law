from __future__ import annotations

import re
from typing import Any, Literal

from backend.common.workflow import FactItem, IssueItem
from backend.modules.assessment.schema import RegulationHit

SourceKind = Literal[
    "law_article",
    "regulation",
    "official_guide",
    "template_requirement",
    "standard_clause",
    "case_reference",
    "user_material",
]

# Usage policy per source kind
_SOURCE_USAGE_POLICY: dict[SourceKind, dict[str, Any]] = {
    "law_article": {
        "allowed_usage": ["external_report", "internal_review", "risk_explanation"],
        "can_enter_external_report": True,
    },
    "regulation": {
        "allowed_usage": ["external_report", "internal_review", "risk_explanation"],
        "can_enter_external_report": True,
    },
    "official_guide": {
        "allowed_usage": ["external_report", "internal_review", "risk_explanation"],
        "can_enter_external_report": True,
    },
    "template_requirement": {
        "allowed_usage": ["external_report", "internal_review", "risk_explanation"],
        "can_enter_external_report": True,
    },
    "standard_clause": {
        "allowed_usage": ["external_report", "internal_review", "risk_explanation"],
        "can_enter_external_report": True,
    },
    "case_reference": {
        "allowed_usage": ["internal_review", "risk_explanation"],
        "can_enter_external_report": False,
    },
    "user_material": {
        "allowed_usage": ["external_report", "internal_review"],
        "can_enter_external_report": True,
    },
}


def _infer_source_kind(title: str) -> SourceKind:
    """Infer source_kind from regulation title text."""
    t = (title or "").replace("《", "").replace("》", "")
    if any(kw in t for kw in ("指南", "指引")):
        return "official_guide"
    if any(kw in t for kw in ("标准", "规范")):
        return "standard_clause"
    if any(kw in t for kw in ("模板", "示范")):
        return "template_requirement"
    if any(kw in t for kw in ("法", "办法", "条例", "规定", "细则")):
        return "law_article"
    if any(kw in t for kw in ("案例", "判例", "裁定", "判决")):
        return "case_reference"
    return "regulation"


_CATEGORY_HINTS: dict[str, tuple[str, ...]] = {
    "path": ("安全评估", "申报", "CIIO", "关键信息基础设施", "重要数据", "个人信息"),
    "data_scope": ("个人信息", "敏感个人信息", "重要数据", "数据项", "匿名化", "去标识化"),
    "consent": ("告知", "单独同意", "个人信息", "个人权利", "第三十九条"),
    "recipient": ("境外接收方", "安全保障能力", "管理措施", "技术措施", "所在国家"),
    "contract": ("法律文件", "合同", "再转移", "保存期限", "违约责任", "第九条"),
    "security_measure": ("加密", "访问控制", "应急处置", "安全措施", "审计"),
    "documentation": ("申报材料", "自评估报告", "附件", "证明材料"),
    "expression": ("风险", "整改", "材料", "结论", "审慎"),
}

# ── Issue → Authoritative Legal Source Map ──
# Maps each issue category to its primary legal basis with article-level granularity.
# Used in Stage 1 rerank to boost the correct legal source for each issue type.
_ISSUE_LEGAL_SOURCE_MAP: dict[str, list[dict[str, Any]]] = {
    "path": [
        {"title": "数据出境安全评估办法", "article": "第四条", "weight": 1.0},
        {"title": "数据安全法", "article": "第二十一条", "weight": 0.9},
        {"title": "个人信息保护法", "article": "第三十八条", "weight": 0.9},
        {"title": "数据出境安全评估申报指南", "article": "", "weight": 0.75},
    ],
    "data_scope": [
        {"title": "个人信息保护法", "article": "第四条", "weight": 1.0},
        {"title": "数据安全法", "article": "第二十一条", "weight": 0.95},
        {"title": "数据出境安全评估办法", "article": "第五条", "weight": 0.85},
        {"title": "个人信息保护法", "article": "第二十八条", "weight": 0.8},
    ],
    "consent": [
        {"title": "个人信息保护法", "article": "第三十九条", "weight": 1.0},
        {"title": "个人信息保护法", "article": "第十三条", "weight": 0.95},
        {"title": "个人信息保护法", "article": "第三十八条", "weight": 0.9},
        {"title": "数据出境安全评估办法", "article": "第八条", "weight": 0.7},
    ],
    "recipient": [
        {"title": "数据出境安全评估办法", "article": "第五条", "weight": 1.0},
        {"title": "数据出境安全评估办法", "article": "第八条", "weight": 0.9},
        {"title": "个人信息保护法", "article": "第三十八条", "weight": 0.85},
        {"title": "个人信息保护法", "article": "第五十三条", "weight": 0.75},
    ],
    "contract": [
        {"title": "数据出境安全评估办法", "article": "第九条", "weight": 1.0},
        {"title": "个人信息保护法", "article": "第三十八条", "weight": 0.85},
        {"title": "个人信息保护法", "article": "第三十九条", "weight": 0.75},
    ],
    "security_measure": [
        {"title": "数据出境安全评估办法", "article": "第五条", "weight": 1.0},
        {"title": "数据出境安全评估办法", "article": "第八条", "weight": 0.95},
        {"title": "数据安全法", "article": "第二十七条", "weight": 0.9},
        {"title": "个人信息保护法", "article": "第五十一条", "weight": 0.85},
    ],
    "documentation": [
        {"title": "数据出境安全评估办法", "article": "第六条", "weight": 1.0},
        {"title": "数据出境安全评估申报指南", "article": "", "weight": 0.9},
        {"title": "数据出境安全评估办法", "article": "第七条", "weight": 0.8},
    ],
    "expression": [
        {"title": "数据出境安全评估办法", "article": "第四条", "weight": 1.0},
        {"title": "个人信息保护法", "article": "第三十八条", "weight": 0.85},
        {"title": "数据安全法", "article": "第二十一条", "weight": 0.8},
    ],
}

# Authority level scoring weights for Stage 3
_AUTHORITY_WEIGHTS: dict[str, float] = {
    "high": 0.15,
    "medium": 0.10,
    "low": 0.05,
}

_BINDING_FORCE_WEIGHTS: dict[str, float] = {
    "mandatory": 0.08,
    "recommended": 0.04,
    "reference": 0.02,
}


def _tokens(value: str) -> set[str]:
    text = re.sub(r"[\s,，。；;：:（）()\[\]【】\"'“”]", " ", value or "").lower()
    return {token for token in text.split() if token}


def _fact_value(fact: FactItem | None) -> str:
    if fact is None:
        return ""
    value = fact.normalized_value if fact.normalized_value is not None else fact.value
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return str(value or "")


def _issue_query(issue: IssueItem, facts_by_id: dict[str, FactItem]) -> str:
    fact_text = " ".join(_fact_value(facts_by_id.get(ref)) for ref in issue.fact_refs)
    hints = " ".join(_CATEGORY_HINTS.get(issue.category, ()))
    return " ".join(
        [
            issue.title,
            issue.description,
            issue.recommended_action,
            issue.category,
            hints,
            fact_text,
        ]
    )


def _infer_authority(title: str) -> str:
    """Infer authority level from regulation title (local copy, see citation_builder for canonical)."""
    t = (title or "").replace("《", "").replace("》", "")
    if "法" in t and "办法" not in t:
        return "high"
    if any(kw in t for kw in ("办法", "条例", "规定")):
        return "medium"
    return "low"


def _infer_binding(title: str) -> str:
    """Infer binding force from regulation title (local copy, see citation_builder for canonical)."""
    t = (title or "").replace("《", "").replace("》", "")
    if "法" in t and "办法" not in t:
        return "mandatory"
    if any(kw in t for kw in ("办法", "条例", "规定")):
        return "mandatory"
    if any(kw in t for kw in ("指南", "标准", "规范")):
        return "recommended"
    return "reference"


def _stage1_primary_source_match(issue: IssueItem, regulation: RegulationHit) -> tuple[float, str]:
    """Stage 1: Match against the authoritative legal source map for the issue category.

    Returns (score_0_to_0_40, reason_string).
    """
    score = 0.0
    reasons: list[str] = []

    # Direct rule_refs match (strong signal)
    if regulation.source_id in issue.rule_refs:
        score += 0.30
        reasons.append("S1:直接引用")

    # Primary legal source map match
    source_entries = _ISSUE_LEGAL_SOURCE_MAP.get(issue.category, [])
    reg_title_clean = (regulation.title or "").replace("《", "").replace("》", "")
    reg_article = regulation.article or ""

    for entry in source_entries:
        entry_title = (entry["title"] or "").replace("《", "").replace("》", "")
        if entry_title in reg_title_clean or reg_title_clean in entry_title:
            # Title matched — apply weight
            title_score = 0.25 * entry["weight"]
            score += title_score
            reasons.append(f"S1:法规匹配({entry['title']})")

            # Article-level bonus
            entry_article = entry.get("article", "")
            if entry_article and entry_article in reg_article:
                score += 0.10
                reasons.append(f"S1:条文匹配({entry_article})")
            break  # Only match the first (highest weight) entry

    return min(score, 0.40), " + ".join(reasons) if reasons else ""


def _stage2_content_relevance(query: str, source_text: str, issue: IssueItem) -> tuple[float, str]:
    """Stage 2: Semantic and keyword relevance between issue query and regulation text.

    Returns (score_0_to_0_30, reason_string).
    """
    score = 0.0
    reasons: list[str] = []

    query_tokens = _tokens(query)
    source_l = source_text.lower()
    overlap = [token for token in query_tokens if len(token) >= 2 and token in source_l]
    if overlap:
        keyword_score = min(len(overlap) * 0.04, 0.25)
        score += keyword_score
        reasons.append(f"S2:关键词({len(overlap)}个)")

    for hint in _CATEGORY_HINTS.get(issue.category, ()):
        if hint.lower() in source_l:
            score += 0.05
            reasons.append(f"S2:类别命中({hint})")
            break

    return min(score, 0.30), " + ".join(reasons) if reasons else ""


def _stage3_authority_adjustment(issue: IssueItem, regulation: RegulationHit) -> tuple[float, str]:
    """Stage 3: Adjust score based on authority level, binding force, and issue severity.

    Returns (score_0_to_0_28, reason_string).
    """
    score = 0.0
    reasons: list[str] = []

    authority = _infer_authority(regulation.title)
    binding = _infer_binding(regulation.title)

    auth_weight = _AUTHORITY_WEIGHTS.get(authority, 0.05)
    score += auth_weight
    reasons.append(f"S3:权威({authority})")

    bind_weight = _BINDING_FORCE_WEIGHTS.get(binding, 0.02)
    score += bind_weight
    if binding != "reference":
        reasons.append(f"S3:约束力({binding})")

    if issue.severity in {"HIGH", "BLOCKER"}:
        score += 0.05
        reasons.append("S3:严重度")

    return min(score, 0.28), " + ".join(reasons) if reasons else ""


def _score_regulation(issue: IssueItem, query: str, regulation: RegulationHit) -> tuple[float, str]:
    """Three-stage rerank for regulation-to-issue relevance scoring.

    Stage 1 — Primary source match (0–0.40): authoritative legal basis for the issue category.
    Stage 2 — Content relevance (0–0.30): keyword overlap and category hints.
    Stage 3 — Authority adjustment (0–0.28): authority level, binding force, severity boost.

    Total capped at 0.98.
    """
    source_text = f"{regulation.title} {regulation.article} {regulation.snippet}"

    s1, r1 = _stage1_primary_source_match(issue, regulation)
    s2, r2 = _stage2_content_relevance(query, source_text, issue)
    s3, r3 = _stage3_authority_adjustment(issue, regulation)

    total = s1 + s2 + s3
    reason_parts = [part for part in (r1, r2, r3) if part]
    reason = " | ".join(reason_parts) if reason_parts else "候选法规与问题文本弱相关"

    return min(total, 0.98), reason


def _annotate_binding(binding: dict[str, Any], source_kind: SourceKind) -> dict[str, Any]:
    """Annotate a binding dict with source_kind, allowed_usage, and can_enter_external_report."""
    policy = _SOURCE_USAGE_POLICY.get(source_kind, _SOURCE_USAGE_POLICY["regulation"])
    binding["source_kind"] = source_kind
    binding["allowed_usage"] = policy["allowed_usage"]
    binding["can_enter_external_report"] = policy["can_enter_external_report"]
    return binding


def build_legal_grounding(
    *,
    issues: list[IssueItem],
    facts: list[FactItem],
    regulations: list[RegulationHit],
    source_version: str = "local-regulation-index-v2",
    per_issue_rag: dict[str, dict] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build legal grounding and case grounding for assessment issues.

    Returns:
        (legal_grounding, case_grounding) tuple.
        legal_grounding contains only law/regulation/guide/template/standard/user_material bindings
        (can_enter_external_report=True).
        case_grounding contains only case/penalty/judgment references
        (can_enter_external_report=False).
    """
    facts_by_id = {fact.fact_id: fact for fact in facts}
    by_issue_legal: dict[str, list[dict[str, Any]]] = {}
    by_issue_case: dict[str, list[dict[str, Any]]] = {}

    for issue in issues:
        query = _issue_query(issue, facts_by_id)
        legal_candidates: list[dict[str, Any]] = []
        case_candidates: list[dict[str, Any]] = []

        for regulation in regulations:
            confidence, reason = _score_regulation(issue, query, regulation)
            if confidence <= 0:
                continue
            source_kind = _infer_source_kind(regulation.title)
            binding = _annotate_binding(
                {
                    "issue_id": issue.issue_id,
                    "rule_id": regulation.source_id,
                    "title": regulation.title,
                    "article": regulation.article,
                    "confidence_score": round(confidence, 3),
                    "relevance_reason": reason,
                    "source_version": source_version,
                    "query_context": query,
                },
                source_kind,
            )
            legal_candidates.append(binding)

        # Merge per-issue DeliLegal results, splitting by source_kind
        if per_issue_rag and issue.issue_id in per_issue_rag:
            rag_result = per_issue_rag[issue.issue_id]
            for law in rag_result.get("laws", []):
                binding = _annotate_binding(
                    {
                        "issue_id": issue.issue_id,
                        "rule_id": f"delilegal-law-{law.get('title', 'unknown')}",
                        "title": law.get("title", "未知法规"),
                        "article": "",
                        "confidence_score": 0.85,
                        "relevance_reason": f"DeliLegal 法规检索：{law.get('summary', '')[:80]}",
                        "source_version": "delilegal-api",
                        "query_context": query,
                    },
                    "law_article",
                )
                legal_candidates.append(binding)
            for case in rag_result.get("cases", []):
                binding = _annotate_binding(
                    {
                        "issue_id": issue.issue_id,
                        "rule_id": f"delilegal-case-{case.get('title', 'unknown')}",
                        "title": case.get("title", "未命名案例"),
                        "article": "",
                        "confidence_score": 0.75,
                        "relevance_reason": f"DeliLegal 案例检索：{case.get('summary', '')[:80]}",
                        "source_version": "delilegal-api",
                        "query_context": query,
                    },
                    "case_reference",
                )
                case_candidates.append(binding)

        legal_candidates.sort(key=lambda item: item["confidence_score"], reverse=True)
        case_candidates.sort(key=lambda item: item["confidence_score"], reverse=True)
        by_issue_legal[issue.issue_id] = legal_candidates[:5]
        if case_candidates:
            by_issue_case[issue.issue_id] = case_candidates[:3]

    legal_grounding = {
        "grounding_version": "v4",
        "source_version": source_version,
        "by_issue": by_issue_legal,
    }
    case_grounding = {
        "grounding_version": "v4",
        "source_version": source_version,
        "by_issue": by_issue_case,
    }
    return legal_grounding, case_grounding
