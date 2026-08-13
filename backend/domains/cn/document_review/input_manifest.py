"""Review run-input manifest builder (task068 T03).

The review pipeline resolves user uploads and external presets at the *run*
boundary (``_create_task_from_request`` / ``upload_file``). This module builds
the authoritative ``RunInputManifest`` from the actual ``UploadedFileModel``
records — never from the client-side payload after the fact — and seals it with
a canonical hash.

Privacy invariants:
    - absolute ``storage_uri`` stays internal; the API exposes only the
      controlled ``public_locator`` via ``public_manifest``.
    - ``sha256`` covers the bytes the service actually reads.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from backend.common.workflow.input_manifest import (
    RunInputEntry,
    RunInputManifest,
    SourceKind,
    seal_manifest,
)
from backend.models.review import UploadedFileModel

_INLINE_ID_PREFIX = "inline:"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json_hash(value: object) -> str:
    import json

    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256_bytes(serialized)


def _public_locator(file: UploadedFileModel) -> str:
    """Controlled display key — relative storage path or filename, never absolute."""
    raw = file.storage_path or ""
    try:
        return Path(raw).name or file.filename
    except (ValueError, OSError):
        return file.filename


def file_entry(
    file: UploadedFileModel,
    *,
    source_kind: SourceKind = "uploaded",
    role: str = "document",
    storage_uri: str | None = None,
) -> RunInputEntry:
    """Build one manifest entry from an uploaded-file record.

    ``consumed_by_service`` and ``parser_status`` reflect reality: a missing
    file is recorded as not consumed + failed, so the material tree and any
    integrity check can surface it instead of silently counting it.
    """
    uri = storage_uri or file.storage_path
    path = Path(uri) if uri else None
    exists = bool(path and path.exists() and path.is_file())
    size_bytes: int | None = None
    sha256 = ""
    if exists:
        data = path.read_bytes()
        size_bytes = len(data)
        sha256 = _sha256_bytes(data)

    parser_status = "parsed" if (exists and file.extracted_text) else ("failed" if exists else "pending")
    return RunInputEntry(
        input_id=file.id,
        display_name=file.filename,
        role=role,
        source_kind=source_kind,
        media_type=file.content_type or "",
        size_bytes=size_bytes,
        sha256=sha256,
        storage_uri=uri or "",
        public_locator=_public_locator(file),
        consumed_by_service=exists,
        parser_status=parser_status,
        provenance={"uploaded_file_id": file.id},
    )


def inline_scenario_entry(request_context: dict | None) -> RunInputEntry | None:
    """Record an inline scenario/config input (no file on disk)."""
    scenario = (request_context or {}).get("scenario_context")
    if not scenario:
        return None
    return RunInputEntry(
        input_id=f"{_INLINE_ID_PREFIX}scenario",
        display_name="审查场景（内联）",
        role="scenario",
        source_kind="inline",
        media_type="application/json",
        size_bytes=None,
        sha256=_canonical_json_hash(scenario),
        storage_uri="",
        public_locator="",
        consumed_by_service=True,
        parser_status="parsed",
        provenance={"scenario_name": str(scenario.get("document_title") or "")[:80] or None},
    )


def build_review_input_manifest(
    *,
    task_id: str,
    files: list[UploadedFileModel],
    request_context: dict | None = None,
    source_kinds: dict[str, SourceKind] | None = None,
    module_key: str = "review",
) -> RunInputManifest:
    """Build + seal the run-input manifest for a review task."""
    kinds = source_kinds or {}
    entries: list[RunInputEntry] = [
        file_entry(
            file,
            source_kind=kinds.get(file.id, "uploaded"),
            storage_uri=file.storage_path,
        )
        for file in files
    ]
    scenario = inline_scenario_entry(request_context)
    if scenario is not None:
        entries.append(scenario)

    manifest = RunInputManifest(
        run_id=task_id,
        task_id=task_id,
        module_key=module_key,
        request_hash=_canonical_json_hash(request_context or {}),
        entries=entries,
    )
    return seal_manifest(manifest)


def verify_review_manifest(manifest: RunInputManifest) -> list[dict]:
    """Re-read disk bytes and report any integrity drift.

    Returns a list of problems (empty means the manifest matches reality):
    ``missing`` / ``not_file`` / ``hash_changed`` / ``not_consumed``. Inline
    entries are skipped (no disk backing).
    """
    problems: list[dict] = []
    for entry in manifest.entries:
        if entry.source_kind == "inline":
            continue
        path = Path(entry.storage_uri) if entry.storage_uri else None
        if not path or not path.exists():
            problems.append({"input_id": entry.input_id, "kind": "missing"})
            continue
        if not path.is_file():
            problems.append({"input_id": entry.input_id, "kind": "not_file"})
            continue
        actual = _sha256_bytes(path.read_bytes())
        if actual != entry.sha256:
            problems.append({"input_id": entry.input_id, "kind": "hash_changed"})
        if not entry.consumed_by_service:
            problems.append({"input_id": entry.input_id, "kind": "not_consumed"})
    return problems
