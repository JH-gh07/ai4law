"""RunInputManifest — the single traceable inventory of a run's inputs (task068).

The material tree must not show "已提交材料 0" when a run actually consumed a
dev-preset scenario, a shared scenario, or an uploaded file. This manifest is
built at the *same* run boundary as the request (never reconstructed client-side
after the fact) and is persisted so task-space recovery returns the same facts.

Privacy/security invariants:
    - absolute paths, access tokens and raw large JSON never enter user-facing
      report text; ``storage_uri`` is internal-only and ``public_locator`` is the
      controlled display key.
    - ``sha256`` covers the bytes actually handed to the service; inline inputs
      use a canonical JSON hash.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SourceKind = Literal["uploaded", "dev_preset", "shared_scenario", "inline"]
ParserStatus = Literal["parsed", "failed", "skipped", "pending"]


class RunInputEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    display_name: str = Field(min_length=1)
    role: str = Field(min_length=1)
    source_kind: SourceKind
    media_type: str = ""
    size_bytes: int | None = None
    sha256: str = ""
    storage_uri: str = ""
    public_locator: str = ""
    consumed_by_service: bool = False
    parser_status: ParserStatus = "pending"
    provenance: dict = Field(default_factory=dict)


class RunInputIntegrity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonicalization: str = "JCS-RFC8785"
    hash_algorithm: str = "SHA-256"
    manifest_hash: str = ""


class RunInputManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    run_id: str = Field(min_length=1)
    task_id: str | None = None
    module_key: str = Field(min_length=1)
    scenario_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    request_hash: str = ""
    entries: list[RunInputEntry] = Field(default_factory=list)
    integrity: RunInputIntegrity = Field(default_factory=RunInputIntegrity)

    @model_validator(mode="after")
    def _no_duplicate_input_ids(self) -> "RunInputManifest":
        seen: set[str] = set()
        for entry in self.entries:
            if entry.input_id in seen:
                raise ValueError(f"重复的 input_id: {entry.input_id}")
            seen.add(entry.input_id)
        return self


# ── Public view (API display DTO) ──────────────────────────────────────────
#
# The manifest holds internal facts (absolute ``storage_uri``, token-bearing
# provenance). The API must never return those; it returns this view, which
# exposes only the controlled ``public_locator`` and identity/hash fields.
# ``provenance`` is sanitized to drop any key that looks like an absolute path.

_SAFE_PROVENANCE_KEYS = {"uploaded_file_id", "preset_id", "scenario_id", "scenario_name"}


class RunInputEntryPublic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_id: str
    display_name: str
    role: str
    source_kind: SourceKind
    media_type: str = ""
    size_bytes: int | None = None
    sha256: str = ""
    public_locator: str = ""
    consumed_by_service: bool = False
    parser_status: ParserStatus = "pending"
    provenance: dict = Field(default_factory=dict)


class RunInputManifestPublic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    run_id: str
    task_id: str | None = None
    module_key: str
    scenario_id: str | None = None
    created_at: datetime
    request_hash: str = ""
    entries: list[RunInputEntryPublic] = Field(default_factory=list)
    integrity: RunInputIntegrity = Field(default_factory=RunInputIntegrity)


def _sanitize_provenance(provenance: dict) -> dict:
    safe: dict = {}
    for key, value in provenance.items():
        if key not in _SAFE_PROVENANCE_KEYS:
            continue
        if isinstance(value, str) and (value.startswith("/") or ":" in value[:3]):
            continue  # drop absolute path / URI-like tokens
        safe[key] = value
    return safe


def public_entry(entry: RunInputEntry) -> RunInputEntryPublic:
    """Project one internal entry to its controlled public view."""
    return RunInputEntryPublic(
        input_id=entry.input_id,
        display_name=entry.display_name,
        role=entry.role,
        source_kind=entry.source_kind,
        media_type=entry.media_type,
        size_bytes=entry.size_bytes,
        sha256=entry.sha256,
        public_locator=entry.public_locator,
        consumed_by_service=entry.consumed_by_service,
        parser_status=entry.parser_status,
        provenance=_sanitize_provenance(entry.provenance),
    )


def public_manifest(manifest: RunInputManifest) -> RunInputManifestPublic:
    """Project a manifest to its controlled public view (no ``storage_uri``)."""
    return RunInputManifestPublic(
        schema_version=manifest.schema_version,
        run_id=manifest.run_id,
        task_id=manifest.task_id,
        module_key=manifest.module_key,
        scenario_id=manifest.scenario_id,
        created_at=manifest.created_at,
        request_hash=manifest.request_hash,
        entries=[public_entry(e) for e in manifest.entries],
        integrity=manifest.integrity,
    )


def canonical_entry_dict(entry: RunInputEntry) -> dict:
    """Canonicalize one entry for hashing (JCS-friendly ordering).

    Only the integrity-relevant identity fields participate; provenance and
    display fields do not change the input identity.
    """
    return {
        "input_id": entry.input_id,
        "role": entry.role,
        "source_kind": entry.source_kind,
        "media_type": entry.media_type,
        "size_bytes": entry.size_bytes,
        "sha256": entry.sha256,
        "consumed_by_service": entry.consumed_by_service,
        "parser_status": entry.parser_status,
    }


def canonical_manifest_dict(manifest: RunInputManifest) -> dict:
    """Serialize the manifest to a canonical dict for the integrity hash."""
    return {
        "schema_version": manifest.schema_version,
        "run_id": manifest.run_id,
        "task_id": manifest.task_id,
        "module_key": manifest.module_key,
        "scenario_id": manifest.scenario_id,
        "request_hash": manifest.request_hash,
        "entries": [canonical_entry_dict(e) for e in manifest.entries],
    }


def compute_manifest_hash(manifest: RunInputManifest) -> str:
    """Compute the canonical JSON hash over the manifest's identity fields."""
    canonical = canonical_manifest_dict(manifest)
    serialized = json.dumps(
        canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def seal_manifest(manifest: RunInputManifest) -> RunInputManifest:
    """Set the integrity hash from the current entries and return the manifest."""
    manifest.integrity.manifest_hash = compute_manifest_hash(manifest)
    return manifest


def verify_manifest_hash(manifest: RunInputManifest) -> bool:
    """True iff the recorded integrity hash matches a recomputed one."""
    expected = manifest.integrity.manifest_hash
    if not expected:
        return False
    return compute_manifest_hash(manifest) == expected
