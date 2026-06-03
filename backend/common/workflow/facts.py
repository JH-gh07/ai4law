"""L1 Platform base model — Fact layer.

Every piece of information that enters the compliance platform must be represented
as a FactItem before any downstream module consumes it.  This guarantees that
every conclusion in the final report can be traced back to its origin.

Source-type priority (FactMerger uses this order to resolve conflicts):
    1. user_confirmed        – human manually verified
    2. document_extracted    – parsed from an authoritative file
    3. user_declared         – input through a form field
    4. agent_assisted        – inferred by an Agent (medium confidence)
    5. rule_inferred          – derived by the deterministic rule engine
    6. system_default         – platform fallback value
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


# ── Enumerations ──────────────────────────────────────────────────────────

FactSourceType = Literal[
    "schema",            # user form field
    "attachment",        # extracted from uploaded document
    "user_text",         # user free-text input
    "diagnosis",         # carried from path-diagnosis result
    "derived",           # inferred by rule engine
]

EvidenceStatus = Literal[
    "user_claim_only",       # stated by user, no supporting material
    "partial_evidence",      # some evidence exists but incomplete
    "documented_evidence",   # backed by an uploaded document / contract / policy
    "verified_evidence",     # verified by third-party audit or official certification
]


# ── Core models ───────────────────────────────────────────────────────────

class FactItem(BaseModel):
    """A single structured fact, the atomic unit of the platform.

    Every fact must declare *how we know it* (source_type / evidence_status)
    so that the report generator can decide whether a statement can be
    written as a positive claim or must be hedged.
    """

    fact_id: str = Field(min_length=1, description="Unique fact identifier")

    # ── Provenance ──
    source_type: FactSourceType = Field(
        description="How the fact entered the system"
    )
    source_ref: str | None = Field(
        default=None,
        description="Specific origin: field path, file name, rule id, or agent name",
    )
    field_path: str | None = Field(
        default=None,
        description="Dotted path to the originating field, e.g. 'request.pii_count'",
    )

    # ── Value ──
    value: Any = Field(description="Original value as provided")
    normalized_value: Any | None = Field(
        default=None,
        description="Standardised representation (e.g. '1,200,000' → 1200000)",
    )

    # ── Confidence & evidence ──
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0,
        description="How certain the system is about this fact (1.0 = verified)",
    )
    evidence_status: EvidenceStatus = Field(
        default="user_claim_only",
        description="Maturity of supporting evidence",
    )
    supporting_material_refs: list[str] = Field(
        default_factory=list,
        description="References to files/paragraphs that back this fact",
    )

    # ── Usage control ──
    can_support_external_positive_claim: bool = Field(
        default=False,
        description=(
            "If False, this fact CANNOT be used to write a positive assertion "
            "in the external report (e.g. '已具备完善的安全保障体系')."
        ),
    )
    requires_user_confirmation: bool = Field(
        default=False,
        description="If True, the system inferred this; user must confirm before it can be used externally",
    )

    # ── Annotation ──
    notes: str | None = Field(
        default=None,
        description="Human-readable annotation (warnings, caveats, extraction notes)",
    )
    jurisdiction: str = Field(
        default="",
        description="Applicable legal jurisdiction: CN / EU / US / MULTI",
    )


class FactPack(BaseModel):
    """Module-level collection of facts with summary metadata.

    Built once per module run by aggregating form fields, document
    extractions, and Agent enrichments.  The summary counters let
    downstream stages quickly assess input quality.
    """

    module: str = Field(min_length=1, description="Module key, e.g. 'scc_cn'")
    jurisdiction: str = Field(default="", description="CN / EU / US / MULTI")
    facts: list[FactItem] = Field(default_factory=list)

    # ── Quality counters ──
    fact_count_by_source: dict[str, int] = Field(default_factory=dict)
    fact_count_by_evidence: dict[str, int] = Field(default_factory=dict)
    uncertain_fact_ids: list[str] = Field(
        default_factory=list,
        description="Fact IDs with confidence < 0.65 or requires_user_confirmation=True",
    )

    # ── Warnings ──
    extraction_warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal warnings logged during fact extraction",
    )

    def summarize(self) -> str:
        total = len(self.facts)
        by_src = ", ".join(f"{k}: {v}" for k, v in self.fact_count_by_source.items())
        by_ev = ", ".join(f"{k}: {v}" for k, v in self.fact_count_by_evidence.items())
        return (
            f"FactPack({self.module}): {total} facts | "
            f"sources: {{{by_src}}} | "
            f"evidence: {{{by_ev}}} | "
            f"uncertain: {len(self.uncertain_fact_ids)}"
        )


# ── Fact merge log (for multi-source conflict resolution) ─────────────────

class FactMergeCandidate(BaseModel):
    """Record of a single source's claim for a given field path."""

    source_type: FactSourceType
    source_ref: str | None = None
    value: Any = None
    confidence: float = 0.0


class FactMergeLog(BaseModel):
    """Resolution record when multiple sources claim the same field path.

    The merger selects the winner according to source-type priority and
    keeps the full candidate list so the decision is auditable.
    """

    field_path: str
    candidates: list[FactMergeCandidate] = Field(default_factory=list)
    winner_source_type: FactSourceType | None = None
    winner_value: Any = None
    resolution_note: str = ""
