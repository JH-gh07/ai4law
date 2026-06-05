from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from backend.common.citation.id_generator import generate_citation_id
from backend.common.citation.models import CitationItem
from backend.common.citation.output import build_knowledge_url
from backend.common.citation.registry import CitationRegistry


@dataclass
class ModuleIssue:
    issue_id: str
    category: str
    title: str
    description: str
    severity: str | None = None
    legal_basis: str | None = None
    recommendation: str | None = None
    facts: list[str] = field(default_factory=list)


@dataclass
class LegalBinding:
    issue_id: str
    rule_id: str
    title: str
    article: str
    content: str
    jurisdiction: str
    confidence_score: float
    relevance_reason: str
    source_kind: str
    authority_level: str
    binding_force: str
    allowed_usage: list[str] = field(default_factory=list)
    can_enter_external_report: bool = True
    confidence_threshold: float = 0.20
    confidence_passed: bool = True
    external_report_allowed: bool = True
    display_label: str = ""


@dataclass
class CitationBundle:
    registry: CitationRegistry
    items: list[CitationItem]
    bindings_by_issue: dict[str, list[LegalBinding]]
    citation_ids_by_issue: dict[str, list[str]]
    labels_by_issue: dict[str, list[str]]
    prompt_block: str


_MODULE_LEGAL_SOURCE_MAP: dict[str, dict[str, list[dict[str, Any]]]] = {
    "cpra": {
        "opt_out": [
            {"title": "CPRA", "article": "1798.120", "weight": 1.0},
            {"title": "CPPA", "article": "7004", "weight": 0.70},
        ],
        "sale_or_share": [
            {"title": "CPRA", "article": "1798.120", "weight": 1.0},
        ],
        "spi_risk": [
            {"title": "CPRA", "article": "1798.121", "weight": 1.0},
        ],
        "vendor_contract": [
            {"title": "CPRA", "article": "1798.140", "weight": 0.90},
            {"title": "CPPA", "article": "7051", "weight": 0.70},
        ],
        "dark_pattern": [
            {"title": "CPPA", "article": "7004", "weight": 1.0},
        ],
        "other": [
            {"title": "CPRA", "article": "1798.100", "weight": 0.75},
        ],
    }
}

_AUTHORITY_WEIGHTS = {"high": 0.15, "medium": 0.10, "low": 0.05}
_BINDING_WEIGHTS = {"mandatory": 0.08, "recommended": 0.04, "reference": 0.02}
_SOURCE_USAGE_POLICY: dict[str, dict[str, Any]] = {
    "law_article": {
        "allowed_usage": ["external_report", "internal_review", "risk_explanation"],
        "can_enter_external_report": True,
        "confidence_threshold": 0.20,
    },
    "official_guide": {
        "allowed_usage": ["external_report", "internal_review", "risk_explanation"],
        "can_enter_external_report": True,
        "confidence_threshold": 0.30,
    },
    "case_reference": {
        "allowed_usage": ["internal_review", "risk_explanation"],
        "can_enter_external_report": False,
        "confidence_threshold": 0.40,
    },
}


def _tokens(value: str) -> set[str]:
    text = re.sub(r"[\s,，。；;：:（）()\[\]【】\"'“”§\.]", " ", value or "").lower()
    return {token for token in text.split() if token}


def _extract_article_number(article: str, jurisdiction: str) -> str:
    text = str(article or "").strip()
    if not text:
        return ""
    if jurisdiction.upper() == "US":
        match = re.search(r"§\s*([0-9]+(?:\.[0-9]+)*)", text)
        if match:
            return match.group(1)
        match = re.search(r"\bArt\.?\s*([0-9]+(?:\.[0-9]+)*)", text, re.I)
        if match:
            return match.group(1)
        match = re.search(r"\bArticle\s+([0-9]+(?:\.[0-9]+)*)", text, re.I)
        if match:
            return match.group(1)
    digits = re.findall(r"[0-9]+(?:\.[0-9]+)*", text)
    return digits[0] if digits else text


def _normalize_article_token(article_no: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", (article_no or "").upper()).strip("_") or "GEN"


def _infer_authority(title: str, source_id: str) -> str:
    upper = (title or "").upper()
    if source_id == "us_cpra" or "CPRA" in upper or "CCPA" in upper:
        return "high"
    if source_id == "us_cppa_regulations" or "CPPA" in upper:
        return "medium"
    return "medium"


def _infer_binding_force(title: str, source_id: str) -> str:
    if source_id == "us_cpra":
        return "mandatory"
    if source_id == "us_cppa_regulations":
        return "recommended"
    return "mandatory"


def _display_label(title: str, article_no: str, source_id: str, raw_article: str) -> str:
    if source_id == "us_cppa_regulations":
        return f"CPPA {raw_article or f'Art.{article_no}'}".strip()
    if source_id == "us_cpra":
        return f"CPRA {raw_article or f'§{article_no}'}".strip()
    return f"{title} {raw_article}".strip() if raw_article else title


def _citation_abbr(source_id: str, title: str) -> str:
    if source_id == "us_cpra":
        return "CPRA"
    if source_id == "us_cppa_regulations":
        return "CPPA"
    upper = (title or "").upper()
    if "CPPA" in upper:
        return "CPPA"
    if "CPRA" in upper or "CCPA" in upper:
        return "CPRA"
    return "REG"


def _source_policy(source_kind: str) -> dict[str, Any]:
    return _SOURCE_USAGE_POLICY.get(source_kind, _SOURCE_USAGE_POLICY["law_article"])


def _stage1_source_match(module: str, issue: ModuleIssue, regulation: dict[str, Any]) -> tuple[float, str]:
    score = 0.0
    reasons: list[str] = []
    entries = _MODULE_LEGAL_SOURCE_MAP.get(module, {}).get(issue.category) or _MODULE_LEGAL_SOURCE_MAP.get(module, {}).get("other", [])
    reg_title = str(regulation.get("source_title") or regulation.get("title") or "")
    reg_article = str(regulation.get("article_no") or regulation.get("article") or "")
    for entry in entries:
        if entry["title"].lower() in reg_title.lower() or reg_title.lower() in entry["title"].lower():
            score += 0.25 * float(entry.get("weight", 1.0))
            reasons.append(f"S1:法规匹配({entry['title']})")
            if entry.get("article") and entry["article"] in reg_article:
                score += 0.10
                reasons.append(f"S1:条文匹配({entry['article']})")
            break
    return min(score, 0.40), " + ".join(reasons) if reasons else ""


def _stage2_content_relevance(issue: ModuleIssue, regulation: dict[str, Any]) -> tuple[float, str]:
    query = " ".join(
        part for part in [
            issue.title,
            issue.description,
            issue.legal_basis or "",
            issue.recommendation or "",
            " ".join(issue.facts),
        ]
        if part
    )
    source_text = " ".join(
        str(regulation.get(key, "") or "")
        for key in ("source_title", "title", "article", "article_no", "snippet", "content", "display_label")
    )
    overlap = [token for token in _tokens(query) if len(token) >= 2 and token in source_text.lower()]
    if not overlap:
        return 0.0, ""
    score = min(len(overlap) * 0.04, 0.30)
    return score, f"S2:关键词({len(overlap)}个)"


def _stage3_authority_adjustment(issue: ModuleIssue, regulation: dict[str, Any]) -> tuple[float, str]:
    authority = str(regulation.get("authority_level") or _infer_authority(str(regulation.get("title") or ""), str(regulation.get("source_id") or "")))
    binding_force = str(regulation.get("binding_force") or _infer_binding_force(str(regulation.get("title") or ""), str(regulation.get("source_id") or "")))
    score = _AUTHORITY_WEIGHTS.get(authority, 0.05) + _BINDING_WEIGHTS.get(binding_force, 0.02)
    reasons = [f"S3:权威({authority})"]
    if binding_force != "reference":
        reasons.append(f"S3:约束力({binding_force})")
    if (issue.severity or "").upper() in {"HIGH", "BLOCKER"}:
        score += 0.05
        reasons.append("S3:严重度")
    return min(score, 0.28), " | ".join(reasons)


def build_module_legal_grounding(
    *,
    module: str,
    jurisdiction: str,
    issues: list[ModuleIssue],
    regulations_by_issue: dict[str, list[dict[str, Any]]],
) -> dict[str, list[LegalBinding]]:
    bindings_by_issue: dict[str, list[LegalBinding]] = {}
    for issue in issues:
        candidates: list[LegalBinding] = []
        for regulation in regulations_by_issue.get(issue.issue_id, []):
            s1, r1 = _stage1_source_match(module, issue, regulation)
            s2, r2 = _stage2_content_relevance(issue, regulation)
            s3, r3 = _stage3_authority_adjustment(issue, regulation)
            confidence = min(s1 + s2 + s3, 0.98)
            if confidence <= 0:
                continue
            source_kind = str(regulation.get("source_kind") or "law_article")
            policy = _source_policy(source_kind)
            source_title = str(regulation.get("source_title") or regulation.get("title") or "引用依据")
            article = str(regulation.get("article") or regulation.get("article_no") or "")
            display_label = str(regulation.get("display_label") or _display_label(source_title, regulation.get("article_no", ""), regulation.get("source_id", ""), article))
            binding = LegalBinding(
                issue_id=issue.issue_id,
                rule_id=str(regulation.get("source_id") or regulation.get("rule_id") or ""),
                title=source_title,
                article=article,
                content=str(regulation.get("content") or regulation.get("snippet") or ""),
                jurisdiction=jurisdiction.upper(),
                confidence_score=round(confidence, 3),
                relevance_reason=" | ".join(part for part in (r1, r2, r3) if part),
                source_kind=source_kind,
                authority_level=str(regulation.get("authority_level") or _infer_authority(source_title, str(regulation.get("source_id") or ""))),
                binding_force=str(regulation.get("binding_force") or _infer_binding_force(source_title, str(regulation.get("source_id") or ""))),
                allowed_usage=list(policy["allowed_usage"]),
                can_enter_external_report=bool(policy["can_enter_external_report"]),
                confidence_threshold=float(policy["confidence_threshold"]),
                confidence_passed=confidence >= float(policy["confidence_threshold"]),
                external_report_allowed=bool(policy["can_enter_external_report"]) and confidence >= float(policy["confidence_threshold"]),
                display_label=display_label,
            )
            candidates.append(binding)
        candidates.sort(key=lambda item: item.confidence_score, reverse=True)
        bindings_by_issue[issue.issue_id] = candidates[:5]
    return bindings_by_issue


def build_module_citation_bundle(
    *,
    module: str,
    jurisdiction: str,
    issues: list[ModuleIssue],
    regulations_by_issue: dict[str, list[dict[str, Any]]],
) -> CitationBundle:
    registry = CitationRegistry()
    bindings_by_issue = build_module_legal_grounding(
        module=module,
        jurisdiction=jurisdiction,
        issues=issues,
        regulations_by_issue=regulations_by_issue,
    )
    items: list[CitationItem] = []
    citation_ids_by_issue: dict[str, list[str]] = {}
    labels_by_issue: dict[str, list[str]] = {}
    seen_by_key: dict[tuple[str, str], CitationItem] = {}

    for issue in issues:
        issue_ids: list[str] = []
        issue_labels: list[str] = []
        for binding in bindings_by_issue.get(issue.issue_id, []):
            source_id = binding.rule_id
            article_no = _extract_article_number(binding.article, jurisdiction)
            citation_key = (source_id, article_no)
            existing = seen_by_key.get(citation_key)
            if existing is None:
                article_token = _normalize_article_token(article_no)
                citation_id = generate_citation_id(
                    jurisdiction.upper(),
                    _citation_abbr(source_id, binding.title),
                    article_token or "GEN",
                    1,
                )
                item = CitationItem(
                    citation_id=citation_id,
                    source_id=source_id,
                    jurisdiction=jurisdiction.upper(),
                    display_label=binding.display_label,
                    citation_type="law_article",
                    title=binding.title,
                    article_no=article_no,
                    quote_text=binding.content[:500],
                    related_issue_ids=[issue.issue_id],
                    confidence_score=binding.confidence_score,
                    authority_level=binding.authority_level,
                    binding_force=binding.binding_force,
                    source_kind=binding.source_kind,
                    allowed_usage=list(binding.allowed_usage),
                    can_enter_external_report=binding.can_enter_external_report,
                    confidence_threshold=binding.confidence_threshold,
                    external_report_allowed=binding.external_report_allowed,
                )
                registry.register(item)
                seen_by_key[citation_key] = item
                items.append(item)
                existing = item
            elif issue.issue_id not in existing.related_issue_ids:
                existing.related_issue_ids.append(issue.issue_id)
                if binding.confidence_score > existing.confidence_score:
                    existing.confidence_score = binding.confidence_score

            issue_ids.append(existing.citation_id)
            issue_labels.append(existing.display_label or binding.display_label)
        citation_ids_by_issue[issue.issue_id] = issue_ids
        labels_by_issue[issue.issue_id] = issue_labels

    for item in items:
        item_dict = item.to_dict()
        item_dict["knowledge_url"] = build_knowledge_url(source_id=item.source_id, article_no=item.article_no) or ""

    return CitationBundle(
        registry=registry,
        items=items,
        bindings_by_issue=bindings_by_issue,
        citation_ids_by_issue=citation_ids_by_issue,
        labels_by_issue=labels_by_issue,
        prompt_block=registry.build_marker_list(),
    )
