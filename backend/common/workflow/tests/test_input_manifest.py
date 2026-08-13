"""task068 T01 — RunInputManifest contract (run-input traceability).

The manifest must be built at the *run* boundary (never reconstructed
client-side), fail-closed on unknown source kinds / duplicate IDs, and round-trip
its integrity hash so task-space recovery returns the same facts.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.common.workflow.input_manifest import (
    RunInputEntry,
    RunInputManifest,
    compute_manifest_hash,
    public_manifest,
    seal_manifest,
    verify_manifest_hash,
)


def _entry(input_id: str = "in-1", **kw) -> RunInputEntry:
    base = dict(
        display_name="合同.pdf",
        role="contract",
        source_kind="uploaded",
        media_type="application/pdf",
        size_bytes=2048,
        sha256="a" * 64,
        consumed_by_service=True,
        parser_status="parsed",
    )
    base.update(kw)
    return RunInputEntry(input_id=input_id, **base)


def _manifest(*entries, **kw) -> RunInputManifest:
    base = dict(run_id="run-1", module_key="review", scenario_id="scenario-1")
    base.update(kw)
    m = RunInputManifest(entries=list(entries), **base)
    return m


def test_entry_rejects_unknown_source_kind() -> None:
    with pytest.raises(ValidationError):
        _entry(source_kind="ftp")


def test_entry_rejects_unknown_parser_status() -> None:
    with pytest.raises(ValidationError):
        _entry(parser_status="zombie")


def test_entry_is_forbid_extra() -> None:
    with pytest.raises(ValidationError):
        RunInputEntry(input_id="in-1", display_name="x", role="contract",
                      source_kind="uploaded", token="secret")


def test_manifest_rejects_duplicate_input_ids() -> None:
    a = _entry("in-1")
    b = _entry("in-1")
    with pytest.raises(ValidationError, match="input_id"):
        _manifest(a, b)


def test_manifest_entries_default_empty() -> None:
    m = _manifest()
    assert m.entries == []
    assert m.integrity.manifest_hash == ""


def test_seal_then_verify_round_trip() -> None:
    m = seal_manifest(_manifest(_entry("in-1"), _entry("in-2")))
    assert m.integrity.manifest_hash
    assert verify_manifest_hash(m) is True


def test_tampering_breaks_verify() -> None:
    m = seal_manifest(_manifest(_entry("in-1")))
    assert verify_manifest_hash(m) is True
    # Mutate an integrity-relevant field.
    m.entries[0].sha256 = "b" * 64
    assert verify_manifest_hash(m) is False


def test_display_fields_do_not_change_identity() -> None:
    m = seal_manifest(_manifest(_entry("in-1")))
    original_hash = m.integrity.manifest_hash
    # display_name and public_locator are presentation-only, excluded from hash.
    m.entries[0].display_name = "renamed.pdf"
    m.entries[0].public_locator = "/public/renamed.pdf"
    assert verify_manifest_hash(m) is True
    assert m.integrity.manifest_hash == original_hash


def test_verify_fails_without_seal() -> None:
    m = _manifest(_entry("in-1"))
    assert verify_manifest_hash(m) is False


def test_compute_hash_is_stable_across_key_order() -> None:
    m1 = seal_manifest(_manifest(_entry("in-1", role="contract")))
    m2 = RunInputManifest(
        run_id="run-1",
        module_key="review",
        scenario_id="scenario-1",
        entries=[_entry("in-1", role="contract")],
    )
    m2 = seal_manifest(m2)
    assert compute_manifest_hash(m1) == compute_manifest_hash(m2)
    assert m1.integrity.manifest_hash == m2.integrity.manifest_hash


# ── Public view (task068 T03) ───────────────────────────────────────────────


def test_public_view_drops_storage_uri_and_absolute_provenance() -> None:
    entry = RunInputEntry(
        input_id="in-1",
        display_name="合同.pdf",
        role="contract",
        source_kind="uploaded",
        storage_uri="/secret/absolute/path/合同.pdf",
        public_locator="合同.pdf",
        provenance={"uploaded_file_id": "f-1", "secret_path": "/secret/absolute/path"},
    )
    m = seal_manifest(_manifest(entry))
    public = public_manifest(m)

    dumped = public.model_dump()
    assert "storage_uri" not in dumped["entries"][0]
    assert public.entries[0].public_locator == "合同.pdf"
    # absolute-path provenance is stripped; safe keys survive
    assert public.entries[0].provenance == {"uploaded_file_id": "f-1"}


def test_public_view_preserves_integrity_hash() -> None:
    m = seal_manifest(_manifest(_entry("in-1")))
    public = public_manifest(m)
    assert public.integrity.manifest_hash == m.integrity.manifest_hash
