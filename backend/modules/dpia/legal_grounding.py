"""DPIA legal grounding — three-stage rerank of GDPR/WP/EDPB/ICO regulations against DPIA issues.

Reuses the assessment module's three-stage scoring architecture but replaces the
legal source map with EU GDPR sources.
"""

from __future__ import annotations

import re
from typing import Any

from backend.common.workflow import FactItem, IssueItem
from backend.modules.dpia.schema import RegulationHit


# ── DPIA Issue → EU GDPR / WP29 / EDPB Legal Source Map ──
# Maps each DPIA issue category to its primary authoritative legal basis
# with article-level granularity. Used in Stage 1 rerank.
DPIA_ISSUE_LEGAL_SOURCE_MAP: dict[str, list[dict[str, Any]]] = {
    "automated_decision": [
        {"title": "GDPR", "article": "Article 22", "weight": 1.0},
        {"title": "WP251", "article": "", "weight": 0.9},
        {"title": "EDPB Guidelines", "article": "automated decision", "weight": 0.8},
    ],
    "profiling": [
        {"title": "GDPR", "article": "Article 22", "weight": 1.0},
        {"title": "WP251", "article": "", "weight": 0.9},
        {"title": "GDPR", "article": "Article 35", "weight": 0.85},
    ],
    "special_category": [
        {"title": "GDPR", "article": "Article 9", "weight": 1.0},
        {"title": "GDPR", "article": "Article 35", "weight": 0.85},
        {"title": "WP248", "article": "", "weight": 0.8},
    ],
    "large_scale": [
        {"title": "WP248", "article": "", "weight": 1.0},
        {"title": "GDPR", "article": "Article 35", "weight": 0.9},
        {"title": "ICO DPIA Guidance", "article": "large scale", "weight": 0.75},
    ],
    "systematic_monitoring": [
        {"title": "WP248", "article": "", "weight": 1.0},
        {"title": "GDPR", "article": "Article 35", "weight": 0.9},
        {"title": "EDPB Guidelines", "article": "video surveillance", "weight": 0.75},
    ],
    "data_matching": [
        {"title": "WP248", "article": "", "weight": 1.0},
        {"title": "GDPR", "article": "Article 5", "weight": 0.85},
        {"title": "GDPR", "article": "Article 35", "weight": 0.8},
    ],
    "new_technology": [
        {"title": "GDPR", "article": "Article 35(1)", "weight": 1.0},
        {"title": "WP248", "article": "", "weight": 0.85},
        {"title": "EDPB Guidelines", "article": "new technology", "weight": 0.75},
    ],
    "vulnerable_subjects": [
        {"title": "WP248", "article": "", "weight": 1.0},
        {"title": "GDPR", "article": "Recital 75", "weight": 0.85},
        {"title": "ICO DPIA Guidance", "article": "vulnerable", "weight": 0.75},
    ],
    "necessity_proportionality": [
        {"title": "GDPR", "article": "Article 35(7)(b)", "weight": 1.0},
        {"title": "GDPR", "article": "Article 5", "weight": 0.9},
        {"title": "GDPR", "article": "Article 5(c)", "weight": 0.85},
        {"title": "ICO DPIA Guidance", "article": "necessity", "weight": 0.75},
    ],
    "lawful_basis": [
        {"title": "GDPR", "article": "Article 6", "weight": 1.0},
        {"title": "GDPR", "article": "Article 9(2)", "weight": 0.9},
        {"title": "GDPR", "article": "Article 7", "weight": 0.85},
        {"title": "EDPB Guidelines", "article": "consent", "weight": 0.8},
    ],
    "transparency": [
        {"title": "GDPR", "article": "Article 13", "weight": 1.0},
        {"title": "GDPR", "article": "Article 14", "weight": 0.95},
        {"title": "GDPR", "article": "Article 12", "weight": 0.9},
        {"title": "WP260", "article": "transparency", "weight": 0.8},
    ],
    "discrimination": [
        {"title": "GDPR", "article": "Article 22(4)", "weight": 1.0},
        {"title": "GDPR", "article": "Recital 71", "weight": 0.9},
        {"title": "GDPR", "article": "Article 9", "weight": 0.85},
    ],
    "cross_border": [
        {"title": "GDPR", "article": "Article 44", "weight": 1.0},
        {"title": "GDPR", "article": "Article 46", "weight": 0.95},
        {"title": "GDPR", "article": "Article 45", "weight": 0.9},
        {"title": "GDPR", "article": "Article 49", "weight": 0.8},
    ],
    "mitigation_gap": [
        {"title": "GDPR", "article": "Article 35(7)(d)", "weight": 1.0},
        {"title": "GDPR", "article": "Article 24", "weight": 0.85},
        {"title": "ICO DPIA Guidance", "article": "mitigation", "weight": 0.75},
    ],
    "prior_consultation": [
        {"title": "GDPR", "article": "Article 36", "weight": 1.0},
        {"title": "WP248", "article": "", "weight": 0.85},
        {"title": "EDPB Guidelines", "article": "prior consultation", "weight": 0.8},
    ],
    "dpia_trigger": [
        {"title": "GDPR", "article": "Article 35", "weight": 1.0},
        {"title": "WP248", "article": "", "weight": 0.9},
        {"title": "ICO DPIA Guidance", "article": "when is DPIA required", "weight": 0.75},
    ],
    "documentation": [
        {"title": "GDPR", "article": "Article 35(2)", "weight": 1.0},
        {"title": "GDPR", "article": "Article 39", "weight": 0.85},
        {"title": "GDPR", "article": "Article 30", "weight": 0.8},
    ],
}


# ── Category hints for keyword-based relevance scoring (Stage 2) ──
_CATEGORY_HINTS: dict[str, tuple[str, ...]] = {
    "dpia_trigger": (
        "DPIA", "data protection impact assessment", "high risk",
        "Article 35", "WP248", "processing likely to result in high risk",
    ),
    "automated_decision": (
        "automated", "decision", "profiling", "legal effect",
        "Article 22", "human intervention", "meaningful",
    ),
    "profiling": (
        "profiling", "evaluation", "scoring", "ranking", "prediction",
        "systematic", "personal aspects", "WP251",
    ),
    "special_category": (
        "special category", "sensitive data", "Article 9",
        "racial", "ethnic", "health", "biometric", "genetic",
        "political", "religious", "trade union", "sexual orientation",
    ),
    "large_scale": (
        "large scale", "number of data subjects", "volume",
        "geographical extent", "duration", "data minimisation",
    ),
    "systematic_monitoring": (
        "systematic monitoring", "public area", "video surveillance",
        "CCTV", "tracking", "observation", "WP248",
    ),
    "data_matching": (
        "data matching", "combination", "re-identification",
        "purpose compatibility", "secondary use", "linking",
    ),
    "new_technology": (
        "new technology", "innovative", "novel", "AI",
        "machine learning", "facial recognition", "biometric",
        "Internet of Things", "IoT", "blockchain",
    ),
    "vulnerable_subjects": (
        "vulnerable", "children", "employee", "patient",
        "power imbalance", "elderly", "disability",
    ),
    "necessity_proportionality": (
        "necessity", "proportionality", "data minimisation",
        "purpose limitation", "storage limitation", "Article 5",
        "strictly necessary", "less intrusive",
    ),
    "lawful_basis": (
        "lawful basis", "legal basis", "Article 6", "consent",
        "legitimate interest", "contract", "legal obligation",
        "vital interest", "public task", "freely given",
    ),
    "transparency": (
        "transparency", "information", "notice", "Article 13",
        "Article 14", "data subject", "fair processing",
        "privacy notice", "layered notice",
    ),
    "discrimination": (
        "discrimination", "bias", "fairness", "equality",
        "Article 22", "special category", "algorithmic",
        "adverse impact", "disparate treatment",
    ),
    "cross_border": (
        "cross border", "transfer", "third country", "Article 44",
        "adequacy", "SCC", "standard contractual clause",
        "BCR", "binding corporate rules", "international",
    ),
    "mitigation_gap": (
        "mitigation", "measure", "safeguard", "residual risk",
        "Article 35(7)(d)", "risk treatment", "control",
        "pseudonymisation", "encryption", "access control",
    ),
    "prior_consultation": (
        "prior consultation", "Article 36", "supervisory authority",
        "residual risk", "cannot mitigate", "DPA",
    ),
    "documentation": (
        "DPO", "data protection officer", "documentation",
        "record", "Article 30", "Article 39", "sign off",
    ),
}

# Authority level weights for GDPR / EU sources
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

# Minimum confidence thresholds for external report inclusion
_MIN_CONFIDENCE_THRESHOLDS: dict[str, float] = {
    "law_article": 0.20,
    "regulation": 0.20,
    "official_guide": 0.30,
    "template_requirement": 0.25,
    "standard_clause": 0.30,
    "case_reference": 0.40,
    "user_material": 0.15,
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
    return " ".join([
        issue.title,
        issue.description,
        issue.recommended_action,
        issue.category,
        hints,
        fact_text,
    ])


def _infer_source_kind(title: str) -> str:
    t = (title or "").lower()
    if any(kw in t for kw in ("regulation", "gdpr")):
        return "law_article"
    if any(kw in t for kw in ("guidelines", "guidance", "wp248", "wp251", "wp260")):
        return "official_guide"
    if any(kw in t for kw in ("ico", "edpb")):
        return "official_guide"
    if any(kw in t for kw in ("template",)):
        return "template_requirement"
    if any(kw in t for kw in ("standard", "code of conduct", "certification")):
        return "standard_clause"
    if any(kw in t for kw in ("case", "judgment", "decision", "ruling")):
        return "case_reference"
    return "regulation"


def _infer_authority(title: str) -> str:
    t = (title or "").lower()
    if "gdpr" in t and "article" in t:
        return "high"
    if any(kw in t for kw in ("wp248", "wp251", "wp260", "edpb", "ico")):
        return "medium"
    return "low"


def _infer_binding(title: str) -> str:
    t = (title or "").lower()
    if "gdpr" in t:
        return "mandatory"
    if any(kw in t for kw in ("wp248", "wp251", "wp260", "edpb guidelines")):
        return "recommended"
    if any(kw in t for kw in ("ico", "template", "standard")):
        return "recommended"
    return "reference"


# ── Three-stage rerank engine ──


def _stage1_primary_source_match(issue: IssueItem, regulation: RegulationHit) -> tuple[float, str]:
    """Stage 1: Match against DPIA authoritative legal source map (0–0.40)."""
    score = 0.0
    reasons: list[str] = []

    # Direct rule_refs match
    if regulation.source_id in issue.rule_refs:
        score += 0.30
        reasons.append("S1:直接引用")

    # Primary legal source map match
    source_entries = DPIA_ISSUE_LEGAL_SOURCE_MAP.get(issue.category, [])
    reg_title_clean = (regulation.title or "").lower()
    reg_article = (regulation.article or "").lower()

    for entry in source_entries:
        entry_title = (entry["title"] or "").lower()
        if entry_title in reg_title_clean or reg_title_clean in entry_title:
            title_score = 0.25 * float(entry.get("weight", 0.8))
            score += title_score
            reasons.append(f"S1:法规匹配({entry['title']})")

            entry_article = (entry.get("article") or "").lower()
            if entry_article and entry_article in reg_article:
                score += 0.10
                reasons.append(f"S1:条文匹配({entry['article']})")
            break

    return min(score, 0.40), " + ".join(reasons) if reasons else ""


def _stage2_content_relevance(query: str, source_text: str, issue: IssueItem) -> tuple[float, str]:
    """Stage 2: Semantic and keyword relevance (0–0.30)."""
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
    """Stage 3: Authority level and binding force adjustment (0–0.28)."""
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
    """Three-stage rerank: primary-source → content → authority. Total capped at 0.98."""
    source_text = f"{regulation.title} {regulation.article} {regulation.snippet}"

    s1, r1 = _stage1_primary_source_match(issue, regulation)
    s2, r2 = _stage2_content_relevance(query, source_text, issue)
    s3, r3 = _stage3_authority_adjustment(issue, regulation)

    total = s1 + s2 + s3
    reason_parts = [part for part in (r1, r2, r3) if part]
    reason = " | ".join(reason_parts) if reason_parts else "候选法规与问题文本弱相关"

    return min(total, 0.98), reason


def _annotate_binding(binding: dict[str, Any], source_kind: str) -> dict[str, Any]:
    policy = _SOURCE_USAGE_POLICY.get(source_kind, _SOURCE_USAGE_POLICY["regulation"])
    threshold = _MIN_CONFIDENCE_THRESHOLDS.get(source_kind, 0.30)
    score = binding.get("confidence_score", 0.0)

    binding["source_kind"] = source_kind
    binding["allowed_usage"] = policy["allowed_usage"]
    binding["can_enter_external_report"] = policy["can_enter_external_report"]
    binding["confidence_threshold"] = threshold
    binding["confidence_passed"] = score >= threshold
    binding["external_report_allowed"] = (
        policy["can_enter_external_report"] and score >= threshold
    )
    return binding


# Usage policy per source kind (EU context)
_SOURCE_USAGE_POLICY: dict[str, dict[str, Any]] = {
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


def _context_binding_lookup(
    legal_grounding_context: list[dict[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    by_rule: dict[str, dict[str, Any]] = {}
    for item in legal_grounding_context or []:
        source_id = str(item.get("source_id") or "")
        chunk_id = str(item.get("chunk_id") or "")
        if source_id:
            by_rule[source_id] = item
        if chunk_id:
            by_rule[chunk_id] = item
    return by_rule


def build_dpia_legal_grounding(
    *,
    issues: list[IssueItem],
    facts: list[FactItem],
    regulations: list[RegulationHit],
    source_version: str = "eu-gdpr-regulation-index-v1",
    per_issue_rag: dict[str, dict] | None = None,
    legal_grounding_context: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build legal grounding and case grounding for DPIA issues.

    Returns:
        (legal_grounding, case_grounding) tuple.
    """
    facts_by_id = {fact.fact_id: fact for fact in facts}
    context_by_rule = _context_binding_lookup(legal_grounding_context)
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
            context_item = context_by_rule.get(regulation.source_id)
            source_kind = (
                str(context_item.get("source_kind"))
                if context_item
                else _infer_source_kind(regulation.title)
            )
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
                    "authority_level": (
                        context_item.get("authority_level")
                        if context_item
                        else _infer_authority(regulation.title)
                    ),
                    "binding_force": (
                        context_item.get("binding_force")
                        if context_item
                        else _infer_binding(regulation.title)
                    ),
                    "can_be_cited": bool(context_item.get("can_be_cited", True)) if context_item else True,
                    "allowed_usage": list(context_item.get("allowed_usage", [])) if context_item else [],
                    "layer": context_item.get("layer") if context_item else "L1_regulatory_evidence",
                },
                source_kind,
            )
            if not binding.get("can_be_cited", True):
                continue
            if binding.get("layer") != "L1_regulatory_evidence":
                continue
            if binding["can_enter_external_report"] or binding["confidence_passed"]:
                legal_candidates.append(binding)
            else:
                case_candidates.append(binding)

        legal_candidates.sort(key=lambda item: item["confidence_score"], reverse=True)
        case_candidates.sort(key=lambda item: item["confidence_score"], reverse=True)
        by_issue_legal[issue.issue_id] = legal_candidates[:5]
        if case_candidates:
            by_issue_case[issue.issue_id] = case_candidates[:3]

    legal_grounding = {
        "grounding_version": "dpia-v1",
        "source_version": source_version,
        "by_issue": by_issue_legal,
    }
    case_grounding = {
        "grounding_version": "dpia-v1",
        "source_version": source_version,
        "by_issue": by_issue_case,
    }
    return legal_grounding, case_grounding
