"""DocumentIR and section models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.common.reporting.schema.blocks import Block
from backend.common.reporting.schema.diagnostics import Diagnostic


class SectionIR(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    level: int = Field(ge=1, le=6)
    ordinal: str | None = None
    reuse_policy: Literal["single_use", "summary", "reference", "verbatim"] = "single_use"
    blocks: list[Block] = Field(default_factory=list)


class ReportMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    company_name: str = ""
    report_date: str = ""
    report_id: str = ""


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    facts_version: str | None = None
    issues_version: str | None = None
    evidence_version: str | None = None


class DocumentIR(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "3.0"
    compiler_version: str
    prompt_version: str
    template_version: str
    model: str
    document_id: str
    report_type: str
    metadata: ReportMetadata
    sections: list[SectionIR]
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    provenance: Provenance
    input_hash: str | None = None
    document_ir_hash: str | None = None
