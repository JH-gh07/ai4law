"""Shadow render + diff audit + switch/rollback primitives (task068 T11).

Shared, module-agnostic helpers for the *non-destructive* migration from a
legacy template writer to the canonical IR renderers. This is the generalised
form of the task067 BCR shadow switch, so CPRA / EO 14117 / DPIA / Review can
stage the IR renderer without switching the official writer until the
environment gates (licensed+hashed CJK font, LibreOffice headless) pass.

Contract (identical to the BCR original):

* **Shadow (stage A)** — render the same ``DocumentIR`` into an *isolated*
  directory (``shadow_ir/`` by default). Those files are never registered as
  user artifacts. A collection audit compares IR finding identity against the
  legacy findings and *records* differences; it never mutates a legal
  conclusion.
* **Switch (stage B)** — when the module's IR-rendering flag is on, the formal
  ``output_files`` point at the IR artifacts and the legacy templates are parked
  under ``shadow_legacy/`` (still written, never registered).
* **Rollback** — turning the flag off leaves the generated IR/manifest artifacts
  on disk and makes the legacy templates official again; nothing is deleted.

This module is pure with respect to business content: it never mutates a
finding, never rewrites a legacy artifact in place, and never stores uploaded
source bodies or secrets in the audit/manifest.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.common.reporting.render_manifest import RenderManifest, build_render_manifest
from backend.common.reporting.schema import DocumentIR
from backend.common.reporting.schema.citations import CitationRegistry

RenderingMode = Literal["legacy", "ir"]


class CollectionAudit(BaseModel):
    """Finding/section/citation identity comparison (diff recorded, not acted on)."""

    model_config = ConfigDict(extra="forbid")

    rendering_mode: RenderingMode
    shadow: bool = True
    finding_ids_equal: bool
    ir_finding_ids: list[str] = Field(default_factory=list)
    legacy_finding_ids: list[str] = Field(default_factory=list)
    missing_in_ir: list[str] = Field(default_factory=list)
    missing_in_legacy: list[str] = Field(default_factory=list)
    ir_section_ids: list[str] = Field(default_factory=list)
    ir_citation_ids: list[str] = Field(default_factory=list)
    ir_citation_count: int = 0
    render_status: str = "success"
    pdf_font_gate: str = "blocked"
    differences: list[str] = Field(default_factory=list)


def render_ir_artifacts(
    document_ir: DocumentIR,
    reporting_registry: CitationRegistry,
    output_dir: Path | str,
    *,
    module: str = "bcr",
    task_id: str = "",
) -> RenderManifest:
    """Render the full IR artifact set (MD/DOCX/PDF/IR/citation_map + manifest).

    Thin, testable wrapper over :func:`build_render_manifest` so services and
    tests share one entry point for the shadow/switch render.
    """
    return build_render_manifest(
        document_ir, reporting_registry, output_dir, module=module, task_id=task_id,
    )


def audit_ir_vs_legacy(
    manifest: RenderManifest,
    legacy_finding_ids: list[str],
    *,
    rendering_mode: RenderingMode = "legacy",
    shadow: bool = True,
) -> CollectionAudit:
    """Compare IR identity inventory against the legacy finding id list.

    The legal conclusion lives in the finding set; the audit asserts set equality
    and *records* the differences (missing IDs in either direction). Section and
    citation identity are informational (the IR side is authoritative for the
    render manifest).
    """
    ir_finding_ids = list(manifest.finding_ids)
    legacy_finding_ids = sorted(set(legacy_finding_ids))

    ir_set = set(ir_finding_ids)
    legacy_set = set(legacy_finding_ids)

    missing_in_ir = sorted(legacy_set - ir_set)
    missing_in_legacy = sorted(ir_set - legacy_set)

    differences: list[str] = []
    if missing_in_ir:
        differences.append(f"legacy 有但 IR 缺 finding: {missing_in_ir}")
    if missing_in_legacy:
        differences.append(f"IR 有但 legacy 缺 finding: {missing_in_legacy}")

    pdf_gate = next(
        (gate.status for gate in manifest.gates if gate.name == "pdf_font_embedding"),
        "blocked",
    )

    return CollectionAudit(
        rendering_mode=rendering_mode,
        shadow=shadow,
        finding_ids_equal=(ir_set == legacy_set),
        ir_finding_ids=ir_finding_ids,
        legacy_finding_ids=legacy_finding_ids,
        missing_in_ir=missing_in_ir,
        missing_in_legacy=missing_in_legacy,
        ir_section_ids=list(manifest.section_ids),
        ir_citation_ids=list(manifest.citation_ids),
        ir_citation_count=manifest.citation_count,
        render_status=manifest.render_status,
        pdf_font_gate=pdf_gate,
        differences=differences,
    )


def write_audit_json(audit: CollectionAudit, path: Path | str) -> Path:
    """Write the audit record (no secret/token content)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(audit.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


__all__ = [
    "CollectionAudit",
    "RenderingMode",
    "audit_ir_vs_legacy",
    "render_ir_artifacts",
    "write_audit_json",
]
