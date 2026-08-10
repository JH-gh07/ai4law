"""L1 Platform base model — Evidence / Citation binding layer.

EvidenceItems connect compliance issues to their legal and documentary
foundations.  Each evidence item records which facts and rules it draws on,
which legal citations support the conclusion, and — critically — *how strongly*
each citation actually supports the finding.

This is the distinction between "having a reference" and "having a reference
that genuinely backs the conclusion."
"""

from typing import Literal

from pydantic import BaseModel, Field


# ── Enumerations ──────────────────────────────────────────────────────────

CitationSupportLevel = Literal[
    "exact_support",       # provision directly applies to this specific issue
    "partial_support",     # provision partially relevant, needs combination with others
    "background_only",     # only provides context; MUST NOT be used as sole basis
    "irrelevant",          # does not support; MUST NOT appear in report
]


# ── Sub-models ────────────────────────────────────────────────────────────

class CitationBinding(BaseModel):
    """A single legal citation linked to an evidence item.

    Stores not just the citation itself but the *strength* of its connection
    to the issue being evidenced, so the report generator can decide whether
    this citation can carry a conclusion or only provide background.
    """

    source_title: str = Field(
        min_length=1,
        description="Regulation / standard / guide title (e.g. '个人信息保护法')",
    )
    article: str = Field(
        default="",
        description="Specific article or section number (e.g. '第三十八条')",
    )
    snippet: str = Field(
        default="",
        description="Quoted excerpt from the source (max ~300 chars for prompt economy)",
    )
    support_level: CitationSupportLevel = Field(
        default="background_only",
        description=(
            "How strongly this citation supports the evidence item's conclusion.\n"
            "  exact_support     → can stand alone as the legal basis\n"
            "  partial_support   → needs pairing with other citations\n"
            "  background_only   → contextual; cannot carry the conclusion alone\n"
            "  irrelevant        → should not appear in any report"
        ),
    )
    jurisdiction: str = Field(
        default="",
        description="Legal jurisdiction: CN / EU / US",
    )
    effective_date: str = Field(
        default="",
        description="Date when this version became effective (e.g. '2021-11-01')",
    )
    version: str = Field(
        default="",
        description="Version label of the regulation (e.g. '2021修订版')",
    )
    superseded_by: str | None = Field(
        default=None,
        description="If this provision has been replaced, reference the newer one here",
    )


class DocumentRef(BaseModel):
    """A reference to a specific location in an uploaded file."""

    file_name: str = Field(min_length=1)
    page: int = Field(default=1, ge=1)
    paragraph_range: tuple[int, int] | None = None
    quote: str = Field(
        default="",
        description="Verbatim quote from the document at this location",
    )


# ── Core model ────────────────────────────────────────────────────────────

class EvidenceItem(BaseModel):
    """A chain element connecting facts and rules to a compliance conclusion.

    Each evidence item answers: "Given these facts and these rules/laws,
    what conclusion can we draw, and how confident are we?"

    Enhanced with full citation binding support for the Evidence Grounding
    layer (layer 7 in the platform data flow).
    """

    evidence_id: str = Field(min_length=1, description="Unique evidence identifier")
    claim: str = Field(
        min_length=1,
        description="The assertion being supported (e.g. '合同缺少再转移约束条款')",
    )

    # ── Reference chain ──
    fact_refs: list[str] = Field(
        default_factory=list,
        description="FactItem.fact_id values this evidence draws on",
    )
    rule_refs: list[str] = Field(
        default_factory=list,
        description="RuleHit.rule_id values that contributed to this conclusion",
    )
    issue_refs: list[str] = Field(
        default_factory=list,
        description="IssueItem.issue_id values that this evidence supports or refutes",
    )

    # ── Legal basis ──
    legal_basis: list[CitationBinding] = Field(
        default_factory=list,
        description="Regulatory citations that directly support this conclusion",
    )
    supporting_basis: list[CitationBinding] = Field(
        default_factory=list,
        description="Secondary citations that provide context but cannot stand alone",
    )
    discarded_basis: list[dict] = Field(
        default_factory=list,
        description="Citations that were retrieved but found irrelevant, with reasons",
    )

    # ── Document sourcing ──
    document_refs: list[DocumentRef] = Field(
        default_factory=list,
        description="Specific locations in uploaded files that support this evidence",
    )

    # ── RAG provenance ──
    rag_query_used: str = Field(
        default="",
        description="The exact RAG query that retrieved these citations",
    )
    rag_hits_count: int = Field(
        default=0,
        description="Number of results returned by the RAG query",
    )

    # ── Conclusion ──
    conclusion: str = Field(
        min_length=1,
        description="The reasoned conclusion this evidence supports",
    )
    usage_constraint: str = Field(
        default="",
        description=(
            "Constraint on how this evidence may be used in the report.\n"
            "e.g. '只能支撑路径适用性，不能用于违法定性'"
        ),
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0,
        description="Overall confidence in this evidence chain",
    )
    used_by: list[str] = Field(
        default_factory=list,
        description="Which report chapters or sections consume this evidence",
    )


# ── Evidence pack (module-level aggregation) ──────────────────────────────

class EvidencePack(BaseModel):
    """Module-level collection of evidence items with summary metadata."""

    module: str = Field(min_length=1)
    evidence_items: list[EvidenceItem] = Field(default_factory=list)

    # ── Quality counters ──
    exact_support_count: int = 0
    partial_support_count: int = 0
    background_only_count: int = 0
    low_confidence_count: int = 0


# ── Shared builders ────────────────────────────────────────────────────────

def regulation_to_citation(reg: object, *, support: CitationSupportLevel = "background_only") -> CitationBinding | None:
    """Convert a regulation hit (dict or object) to a CitationBinding.

    Accepts dicts with keys: source_id/title/law_name, article/article_no/art,
    snippet/content/quote_text, jurisdiction, effective_date, version.
    Also accepts objects with equivalent attributes (e.g. RegulationHit).

    Returns None if no source_title can be extracted (invalid/empty regulation).
    """
    def _get(key: str, *aliases: str) -> str:
        if isinstance(reg, dict):
            for k in (key, *aliases):
                val = reg.get(k, "")
                if val:
                    return str(val)
            return ""
        for k in (key, *aliases):
            val = getattr(reg, k, "")
            if val:
                return str(val)
        return ""

    source_title = _get("law_name", "title", "source_title")
    if not source_title.strip():
        return None

    return CitationBinding(
        source_title=source_title,
        article=_get("article", "article_no", "article_ref", "art"),
        snippet=_get("snippet", "content", "quote_text", "article_content")[:300],
        support_level=support,
        jurisdiction=_get("jurisdiction"),
        effective_date=_get("effective_date"),
        version=_get("version"),
    )


def build_citation_bindings(
    regulations: list[object],
    *,
    max_bindings: int = 5,
    support: CitationSupportLevel = "background_only",
) -> list[CitationBinding]:
    """Convert a list of regulation hits into CitationBinding objects.

    Filters out entries without a valid source_title and caps at max_bindings.
    """
    bindings: list[CitationBinding] = []
    for reg in regulations[: max_bindings * 2]:  # oversample in case some are invalid
        cb = regulation_to_citation(reg, support=support)
        if cb is not None:
            bindings.append(cb)
        if len(bindings) >= max_bindings:
            break
    return bindings
