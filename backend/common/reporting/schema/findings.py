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
