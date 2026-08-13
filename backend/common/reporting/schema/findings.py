"""Finding / action / clause models for the v4 DocumentIR layout contract.

These are the *business-judgment* objects that the renderers consume. They are
deliberately renderer-agnostic: no Markdown, no column widths, no display
numbering. Numbering (finding ordinals, clause labels) is derived by the
renderer or compiler, never stored in ``text``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RiskLevel = Literal["HIGH", "MEDIUM", "LOW"]
FindingStatus = Literal["OPEN_BLOCKING", "OPEN", "RESOLVED", "WONT_FIX"]
NumberingStyle = Literal["decimal", "lower_alpha", "lower_roman", "none"]


class ClauseNode(BaseModel):
    """Recursive clause node; multi-level legal numbering is expressed via
    ``children`` + ``numbering_style``, never by hand-written ``1.``/``(a)``."""

    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    label: str | None = None
    text: str = Field(min_length=1)
    numbering_style: NumberingStyle = "decimal"
    citation_refs: list[str] = Field(default_factory=list)
    children: list["ClauseNode"] = Field(default_factory=list)


class FindingBasis(BaseModel):
    """One per-citation legal basis with an *attribution* rationale.

    task068 I068-22: ``legal_basis: list[str]`` can only express a label list,
    which collapses a finding's multiple citations into a ``；``-joined wall.
    ``FindingBasis`` upgrades that to ``(citation, label, rationale)`` so the
    renderer can emit each citation with "why this applies" without inventing
    legal conclusions.

    ``rationale`` is an *attribution* — the adapter must derive it from an
    existing business field (``ReviewIssue.risk_analysis`` /
    ``StructuredCitation.snippet``). Neither the renderer nor the compiler may
    generate it, and the compiler rejects LLM refusal/placeholder signatures.
    """

    model_config = ConfigDict(extra="forbid")

    citation_ref: str | None = None
    label: str = Field(min_length=1)
    rationale: str = ""
    is_primary: bool = False


class FindingRecord(BaseModel):
    """One structured finding. A finding has exactly one primary display."""

    model_config = ConfigDict(extra="forbid")

    finding_id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    requirement_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    risk_level: RiskLevel = "MEDIUM"
    risk_score: float = 0.0
    statement: str = Field(min_length=1)
    legal_basis: list[str] = Field(default_factory=list)
    recommendation: str = ""
    suggested_revision: str | None = None
    facts_uncertain: bool = False
    review_confidence: float = 0.85
    citation_refs: list[str] = Field(default_factory=list)
    status: FindingStatus = "OPEN"
    # Compiler derives this; it must equal 1 after validation.
    primary_display_count: int = 0
    # task068 T01 — structured per-citation basis (I068-22). ``legal_basis`` is
    # kept as a backward-compatible label shim; renderers must prefer
    # ``basis_entries`` when non-empty.
    basis_entries: list[FindingBasis] = Field(default_factory=list)
    # task068 T01 — Review-specific lossless fields (I068-02). Optional so the
    # other eight module fixtures remain unchanged.
    original_excerpt: str | None = None
    clause_type: str | None = None
    problem_type: str | None = None
    # Review source locators / method metadata. Kept typed (not re-flattened into
    # ``statement``) so no ``ReviewIssue`` field is silently dropped.
    clause_id: str | None = None
    file_id: str | None = None
    source_position: dict | None = None
    secondary_clause_types: list[str] = Field(default_factory=list)
    uncertainty_rationale: str | None = None
    review_method: str | None = None
    review_depth: str | None = None


class ActionRecord(BaseModel):
    """A remediation action bound to at least one finding."""

    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    finding_refs: list[str] = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = ""
    priority: Literal["P0", "P1", "P2", "P3"] = "P1"
    status: Literal["OPEN", "DONE"] = "OPEN"


ClauseNode.model_rebuild()
