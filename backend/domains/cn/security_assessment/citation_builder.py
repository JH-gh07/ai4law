from __future__ import annotations

from typing import Any

from backend.common.citation.id_generator import generate_citation_id, resolve_abbreviation
from backend.common.citation.models import AuthorityLevel, BindingForce, CitationItem, CitationType
from backend.common.citation.source_identity import SourceIdentityResolver
from backend.common.workflow import EvidenceItem, FactItem, IssueItem


def _infer_citation_type(title: str, article: str) -> CitationType:
    """Infer citation type from regulation title and article reference."""
    t = (title or "").replace("《", "").replace("》", "")
    if "指南" in t:
        return "official_guide"
    if "标准" in t or "规范" in t:
        return "standard_clause"
    if "模板" in t or "示范" in t:
        return "template_requirement"
    if any(kw in t for kw in ("法", "办法", "条例", "规定", "细则", "办法")):
        return "law_article"
    return "law_article"


def _infer_authority_level(title: str) -> AuthorityLevel:
    t = (title or "").replace("《", "").replace("》", "")
    if "法" in t and "办法" not in t:
        return "high"
    if any(kw in t for kw in ("办法", "条例", "规定")):
        return "medium"
    return "low"


def _infer_binding_force(title: str) -> BindingForce:
    t = (title or "").replace("《", "").replace("》", "")
    if "法" in t and "办法" not in t:
        return "mandatory"
    if any(kw in t for kw in ("办法", "条例", "规定")):
        return "mandatory"
    if any(kw in t for kw in ("指南", "标准", "规范")):
        return "recommended"
    return "reference"


def _extract_article_number(article: str) -> str:
    """Extract a clean article number from a Chinese legal article reference."""
    if not article:
        return ""
    # Already numeric
    digits = "".join(ch for ch in article if ch.isdigit())
    if digits:
        return digits
    # Chinese numeral conversion could be added, but for now keep the raw text
    return article.replace("第", "").replace("条", "").strip()


def _build_fact_map(facts: list[FactItem]) -> dict[str, FactItem]:
    return {fact.fact_id: fact for fact in facts}


def _infer_source_kind_from_title(title: str) -> str:
    """Infer source_kind from regulation title (mirrors legal_grounding._infer_source_kind)."""
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


def _usage_policy_for_kind(source_kind: str) -> tuple[list[str], bool]:
    """Return (allowed_usage, can_enter_external_report) for a source_kind."""
    if source_kind == "case_reference":
        return ["internal_review", "risk_explanation"], False
    return ["external_report", "internal_review", "risk_explanation"], True


def _build_citation_from_binding(
    binding: dict[str, Any],
    issue_id: str,
    issue: IssueItem | None,
    evidence_by_issue: dict[str, list[str]],
) -> CitationItem | None:
    """Build a CitationItem from a single grounding binding."""
    title = str(binding.get("title", "")).strip()
    article = str(binding.get("article", "")).strip()
    if not title:
        return None

    article_no = _extract_article_number(article) if article else ""
    confidence = float(binding.get("confidence_score", 0.0))
    source_id = str(binding.get("rule_id", ""))
    snippet = str(binding.get("query_context", ""))[:200]

    # Use source_kind from binding if present, otherwise infer from title
    source_kind = str(binding.get("source_kind", _infer_source_kind_from_title(title)))
    allowed_usage, can_enter_external = _usage_policy_for_kind(source_kind)
    confidence_threshold = float(binding.get("confidence_threshold", 0.20))
    external_report_allowed = bool(binding.get("external_report_allowed", can_enter_external))

    abbr = resolve_abbreviation(title)
    citation_id = generate_citation_id(
        jurisdiction="CN",
        abbr=abbr,
        article_no=article_no or "0",
        seq=1,
    )

    related_fact_ids: list[str] = []
    related_evidence_ids: list[str] = []
    if issue is not None:
        related_fact_ids = list(issue.fact_refs)
        related_evidence_ids = evidence_by_issue.get(issue_id, [])

    return CitationItem(
        citation_id=citation_id,
        source_id=source_id,
        citation_type=_infer_citation_type(title, article),
        title=title,
        article_no=article_no,
        quote_text=snippet,
        related_issue_ids=[issue_id],
        related_fact_ids=related_fact_ids,
        related_evidence_ids=related_evidence_ids,
        confidence_score=confidence,
        authority_level=_infer_authority_level(title),
        binding_force=_infer_binding_force(title),
        source_kind=source_kind,
        allowed_usage=allowed_usage,
        can_enter_external_report=can_enter_external,
        confidence_threshold=confidence_threshold,
        external_report_allowed=external_report_allowed,
    )


def build_citations(
    *,
    legal_grounding: dict[str, Any] | None,
    regulations: list[dict],
    issues: list[IssueItem],
    facts: list[FactItem] | None = None,
    evidence_chain: list[EvidenceItem] | None = None,
    case_grounding: dict[str, Any] | None = None,
    source_identity_resolver: SourceIdentityResolver | None = None,
) -> list[CitationItem]:
    """Build CitationItem list from pipeline legal and case grounding data.

    Merges both legal_grounding and case_grounding bindings.
    case_grounding items get can_enter_external_report=False.
    Deduplicates by (title, article_no), keeping the highest confidence_score
    and set-unioning related issue/fact/evidence ids.

    If ``source_identity_resolver`` is provided, each citation's canonical
    registry identity is resolved (exact membership only) and fail-closed policy
    is applied; ``registry_source_id`` records the authoritative source id.
    """
    facts = facts or []
    evidence_chain = evidence_chain or []

    issue_by_id: dict[str, IssueItem] = {issue.issue_id: issue for issue in issues}
    fact_by_id = _build_fact_map(facts)
    evidence_by_issue: dict[str, list[str]] = {}
    for evidence in evidence_chain:
        for issue_id in evidence.used_by or []:
            evidence_by_issue.setdefault(issue_id, []).append(evidence.evidence_id)

    # Collect candidate citations: keyed by (title, article_no)
    candidates: dict[tuple[str, str], CitationItem] = {}

    def _process_bindings(bindings_source: dict[str, Any], default_source_kind: str = "regulation"):
        by_issue = bindings_source.get("by_issue", {})
        for issue_id, bindings in by_issue.items():
            issue = issue_by_id.get(issue_id)
            for binding in bindings:
                # Ensure binding has source_kind if not set by legal_grounding
                if "source_kind" not in binding:
                    binding["source_kind"] = binding.get("source_kind", default_source_kind)

                citation = _build_citation_from_binding(
                    binding, issue_id, issue, evidence_by_issue,
                )
                if citation is None:
                    continue

                key = (citation.title, citation.article_no)
                if key in candidates:
                    existing = candidates[key]
                    existing.related_issue_ids = sorted(
                        set(existing.related_issue_ids) | set(citation.related_issue_ids)
                    )
                    existing.related_fact_ids = sorted(
                        set(existing.related_fact_ids) | set(citation.related_fact_ids)
                    )
                    existing.related_evidence_ids = sorted(
                        set(existing.related_evidence_ids)
                        | set(citation.related_evidence_ids)
                    )
                    if citation.confidence_score > existing.confidence_score:
                        existing.confidence_score = citation.confidence_score
                    continue

                candidates[key] = citation

    # Process legal grounding first, then case grounding
    _process_bindings(legal_grounding or {})
    _process_bindings(case_grounding or {})

    citations = sorted(
        candidates.values(), key=lambda c: c.confidence_score, reverse=True
    )

    if source_identity_resolver is not None:
        for citation in citations:
            _apply_source_identity(citation, source_identity_resolver)

    return citations


def _apply_source_identity(
    citation: CitationItem,
    resolver: SourceIdentityResolver,
) -> None:
    """Resolve canonical registry identity and apply fail-closed citation policy.

    - REGISTERED：``registry_source_id`` = 权威 source_id，并从 Registry 读取
      ``can_enter_external_report`` / ``allowed_usage`` 权威值。
    - UNREGISTERED / INELIGIBLE：``can_enter_external_report=False``、
      ``external_report_allowed=False``、``allowed_usage=["internal_review"]``。
    """
    identity = resolver.resolve(citation.source_id)
    citation.registry_source_id = identity.registry_source_id

    if identity.status == "REGISTERED":
        if not identity.can_enter_external_report:
            citation.can_enter_external_report = False
            citation.external_report_allowed = False
        if identity.allowed_usage:
            citation.allowed_usage = list(identity.allowed_usage)
        return

    # UNREGISTERED / INELIGIBLE：fail-closed，不得作为正式外部报告依据。
    citation.can_enter_external_report = False
    citation.external_report_allowed = False
    citation.allowed_usage = ["internal_review"]
