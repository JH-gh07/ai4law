"""v3 → v4 DocumentIR migration reader.

v3 had no identity, lifecycle, findings, actions, citations, render contract
or integrity record. v4 adds them (with the finding/clause block types). This
module is the single sanctioned reader for v3 input; it never guesses a
missing field silently.

Any input that is not an explicit v3 document is rejected with ``ValueError``
rather than being coerced into a half-valid v4 IR. Section-local inline blocks
remain inline (the v4 contract keeps blocks section-local); v3 → v4 therefore
preserves block placement exactly.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from backend.common.reporting.schema import (
    DocumentIR,
    Identity,
    Integrity,
    Lifecycle,
    Provenance,
    ReportMetadata,
    RenderContract,
    SectionIR,
)


def _parse(raw: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(raw, str):
        return json.loads(raw)
    if not isinstance(raw, dict):
        raise ValueError("v3 migration input must be a dict or JSON string")
    return raw


def _as_datetime(value: Any) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


def migrate_v3_document(raw: dict[str, Any] | str) -> DocumentIR:
    """Migrate a v3 DocumentIR payload to v4.

    Raises ``ValueError`` for any non-v3 input (explicit rejection).
    """
    data = _parse(raw)
    if data.get("schema_version") != "3.0":
        raise ValueError(
            f"unsupported schema_version for v3 migration: {data.get('schema_version')!r}"
        )

    generated_at = _as_datetime((data.get("provenance") or {}).get("generated_at"))
    metadata = data.get("metadata", {})
    sections = [
        SectionIR(
            section_id=s["section_id"],
            title=s["title"],
            level=s["level"],
            ordinal=s.get("ordinal"),
            reuse_policy=s.get("reuse_policy", "single_use"),
            blocks=s.get("blocks", []),
        )
        for s in data.get("sections", [])
    ]

    return DocumentIR(
        schema_version="4.0",
        document_id=data["document_id"],
        report_type=data.get("report_type", "unknown"),
        identity=Identity(
            document_id=data["document_id"],
            module_key=data.get("report_type", "unknown"),
        ),
        lifecycle=Lifecycle(created_at=generated_at),
        metadata=ReportMetadata(
            title=metadata.get("title", ""),
            company_name=metadata.get("company_name", ""),
            report_date=metadata.get("report_date", ""),
            report_id=metadata.get("report_id", ""),
        ),
        sections=sections,
        render_contract=RenderContract(),
        integrity=Integrity(
            input_hash=data.get("input_hash"),
            report_ir_hash=data.get("document_ir_hash"),
        ),
        provenance=Provenance(generated_at=generated_at),
        migrated_from_schema="3.0",
        compiler_version=data.get("compiler_version", "unknown"),
        prompt_version=data.get("prompt_version", "unknown"),
        template_version=data.get("template_version", "unknown"),
        model=data.get("model", "unknown"),
    )
