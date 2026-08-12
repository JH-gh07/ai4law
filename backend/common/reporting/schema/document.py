"""DocumentIR v4 — the versioned cross-format report contract.

v4 is a *major* upgrade over v3.0 (five generic blocks). It adds the BCR
layout slice: identity/lifecycle, structured findings/actions, a citation
record pool, a render contract, an integrity record, and the finding /
clause / key-value / page-break block types.

For a bounded transition, the v3 constructor surface is preserved: existing
schema-first adapters may keep passing ``document_id`` / ``report_type`` /
inline ``SectionIR.blocks`` without change. The BCR adapter populates the new
fields directly; other modules remain valid v3-style inputs that carry
``migrated_from_schema="3.0"`` when read through ``migrate_v3_document``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.common.reporting.schema.blocks import Block
from backend.common.reporting.schema.citations import CitationRecord
from backend.common.reporting.schema.diagnostics import Diagnostic
from backend.common.reporting.schema.findings import ActionRecord, FindingRecord
from backend.common.reporting.schema.rendering import RenderContract


class Identity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1)
    report_id: str | None = None
    run_id: str | None = None
    task_id: str | None = None
    module_key: str = Field(min_length=1)
    module_id: str | None = None


class Lifecycle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: Literal["DRAFT", "BLOCKED", "COMPLETED"] = "DRAFT"
    report_status: Literal["DRAFT", "FINAL"] = "DRAFT"
    is_degraded: bool = False
    degradation_reasons: list[str] = Field(default_factory=list)
    created_at: datetime
    completed_at: datetime | None = None


class ReportMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    short_title: str = ""
    company_name: str = ""
    jurisdiction: str = ""
    locale: str = "zh-CN"
    report_date: str = ""
    report_id: str = ""


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    facts_version: str | None = None
    issues_version: str | None = None
    evidence_version: str | None = None


class Integrity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonicalization: str = "JCS-RFC8785"
    hash_algorithm: str = "SHA-256"
    input_hash: str | None = None
    report_ir_hash: str | None = None


class SectionIR(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    level: int = Field(ge=1, le=6)
    ordinal: str | None = None
    purpose: str | None = None
    reuse_policy: Literal["single_use", "summary", "reference", "verbatim"] = "single_use"
    visibility: Literal["EXTERNAL_AND_INTERNAL", "INTERNAL_ONLY"] = "EXTERNAL_AND_INTERNAL"
    # Inline blocks are the v3-compatible storage. v4 adds the finding/clause
    # block types; blocks remain section-local (no cross-section block pool).
    blocks: list[Block] = Field(default_factory=list)


class DocumentIR(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "4.0"

    # ── v3-compatible identity (kept so existing adapters construct unchanged) ──
    document_id: str = Field(min_length=1)
    report_type: str = Field(min_length=1)

    # ── v4 additions ─────────────────────────────────────────────────────────
    identity: Identity | None = None
    lifecycle: Lifecycle | None = None
    findings: list[FindingRecord] = Field(default_factory=list)
    actions: list[ActionRecord] = Field(default_factory=list)
    citations: list[CitationRecord] = Field(default_factory=list)
    render_contract: RenderContract = Field(default_factory=RenderContract)
    integrity: Integrity | None = None
    migrated_from_schema: str | None = None

    # ── shared fields ───────────────────────────────────────────────────────
    metadata: ReportMetadata
    sections: list[SectionIR] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    provenance: Provenance

    # Generation context (execution slice). Recorded by the adapter, never the
    # renderer.
    compiler_version: str
    prompt_version: str
    template_version: str
    model: str
