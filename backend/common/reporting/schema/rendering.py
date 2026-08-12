"""Render contract and profile models for the v4 DocumentIR."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ArtifactFormat = Literal["MARKDOWN", "DOCX", "PDF", "HTML", "ANNOTATED_DOCX"]


class RenderContract(BaseModel):
    """Declares which artifacts a module must produce, and how to render them.

    The renderer must not invent artifacts not declared here, and a declared
    required artifact that is missing/empty must fail the render.
    """

    model_config = ConfigDict(extra="forbid")

    profile_id: str = Field(default="legal-report-a4-v1", min_length=1)
    template_id: str | None = None
    required_artifacts: list[ArtifactFormat] = Field(default_factory=lambda: ["MARKDOWN", "DOCX", "PDF"])
    optional_artifacts: list[ArtifactFormat] = Field(default_factory=list)
    locale: str = "zh-CN"
    include_toc: bool = False
    include_page_numbers: bool = True
    include_citation_appendix: bool = True
    external_visibility_policy: Literal["ONLY_EXTERNAL_ALLOWED_EVIDENCE", "INTERNAL_ONLY"] = (
        "ONLY_EXTERNAL_ALLOWED_EVIDENCE"
    )
