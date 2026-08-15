"""Task067 T09 — shadow render, diff audit, and local switch.

These tests prove the switch is *non-destructive*: the shadow run keeps the same
user-artifact set, the diff audit records (never mutates) finding identity, and
the local flag points the official outputs at the IR renderer while the legacy
templates are parked under ``shadow_legacy/``.
"""

from __future__ import annotations

import json
from pathlib import Path

from backend.common.citation.registry import registry_from_documents
from backend.common.rag.retriever import RegulationDoc
from backend.domains.eu.bcr_review.schema import BCRFinding, BCRRequest
from backend.domains.eu.bcr_review.service import BCRService
from backend.domains.eu.bcr_review.shadow_render import (
    CollectionAudit,
    audit_ir_vs_legacy,
    render_ir_artifacts,
    write_audit_json,
)


class _DisabledLLM:
    enabled = False


def _payload() -> BCRRequest:
    return BCRRequest.model_validate(
        {"company_name": "影子渲染集团", "review_items": [], "attachments": []}
    )


def _legacy_registry() -> tuple:
    registry = registry_from_documents(
        [
            RegulationDoc(
                id="gdpr",
                title="General Data Protection Regulation",
                article="47",
                content="Binding corporate rules shall be legally binding.",
                jurisdiction="eu",
            )
        ],
        jurisdiction="EU",
    )
    citation_id = next(iter(registry)).citation_id
    registry.assign_footnote_number(citation_id)
    return registry, citation_id


def _finding(citation_id: str) -> BCRFinding:
    return BCRFinding(
        finding_id="BCR-T-01",
        requirement_id="BCR-C-1.1",
        title="约束力不足",
        risk_level="HIGH",
        finding="集团内部约束机制不完整。",
        legal_basis=["GDPR Article 47"],
        citation_refs=[citation_id],
    )


# ── module: audit + write ────────────────────────────────────────────────────


def test_audit_finding_sets_equal_when_ids_match(tmp_path) -> None:
    from backend.domains.eu.bcr_review.schema_first import build_bcr_document_ir
    from backend.domains.eu.bcr_review.schema import BCRTypeClassification

    registry, citation_id = _legacy_registry()
    doc_ir, reporting_reg = build_bcr_document_ir(
        task_id="t",
        company_name="影子渲染集团",
        type_class=BCRTypeClassification(),
        rating="高风险",
        score=80.0,
        findings=[_finding(citation_id)],
        missing=[],
        citation_registry=registry,
        metadata={"bcr_type": "BCR-C"},
        model="test",
    )
    manifest = render_ir_artifacts(doc_ir, reporting_reg, tmp_path / "out", module="bcr", task_id="t")

    audit = audit_ir_vs_legacy(manifest, ["BCR-T-01"], rendering_mode="legacy", shadow=True)

    assert audit.finding_ids_equal is True
    assert audit.missing_in_ir == []
    assert audit.missing_in_legacy == []
    assert audit.differences == []
    assert audit.shadow is True
    assert audit.render_status == "success"
    # PDF CJK font gate passes now that a redistributable CJK asset is tracked.
    assert audit.pdf_font_gate == "pass"
    assert audit.ir_section_ids == manifest.section_ids


def test_audit_records_missing_ids_in_both_directions(tmp_path) -> None:
    from backend.domains.eu.bcr_review.schema_first import build_bcr_document_ir
    from backend.domains.eu.bcr_review.schema import BCRTypeClassification

    registry, citation_id = _legacy_registry()
    doc_ir, reporting_reg = build_bcr_document_ir(
        task_id="t", company_name="影子渲染集团", type_class=BCRTypeClassification(),
        rating="高风险", score=80.0, findings=[_finding(citation_id)], missing=[],
        citation_registry=registry, metadata={"bcr_type": "BCR-C"}, model="test",
    )
    manifest = render_ir_artifacts(doc_ir, reporting_reg, tmp_path / "out", module="bcr", task_id="t")

    audit = audit_ir_vs_legacy(manifest, ["BCR-T-01", "BCR-LEGACY-ONLY"])

    assert audit.finding_ids_equal is False
    assert audit.missing_in_ir == ["BCR-LEGACY-ONLY"]
    assert audit.missing_in_legacy == []
    assert any("BCR-LEGACY-ONLY" in diff for diff in audit.differences)


def test_write_audit_json_round_trips_and_has_no_sensitive_content(tmp_path) -> None:
    audit = CollectionAudit(
        rendering_mode="ir", shadow=False, finding_ids_equal=True,
        ir_finding_ids=["F-1"], legacy_finding_ids=["F-1"],
        render_status="success", pdf_font_gate="blocked",
    )
    path = write_audit_json(audit, tmp_path / "shadow_audit.json")

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["finding_ids_equal"] is True
    assert data["rendering_mode"] == "ir"
    assert data["shadow"] is False
    # the audit carries structural identity only, never user正文/token/secret.
    raw = path.read_text(encoding="utf-8")
    for forbidden in ("api_key", "token", "secret", "集团内部约束机制不完整"):
        assert forbidden not in raw


# ── service: stage A shadow run (not registered) ──────────────────────────────


def test_stage_a_shadow_run_keeps_user_artifact_set_unchanged(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    service = BCRService(llm_client=_DisabledLLM())
    service.schema_first_enabled = True
    service.report_ir_rendering_enabled = False

    registry, citation_id = _legacy_registry()
    outputs = service._render_document_driven(
        "shadow-stage-a",
        _payload(),
        "高风险",
        [_finding(citation_id)],
        [],
        [(f"章节 {i}", ["审查内容"]) for i in range(8)],
        {"bcr_type": "BCR-C"},
        registry,
    )

    # Legacy template artifacts stay the official outputs (no IR keys leak in).
    assert "document_ir_json" not in outputs
    assert "render_manifest_json" not in outputs
    assert "zip" in outputs
    assert Path(outputs["docx"]).parent.name == "outputs"

    # The IR version + audit are shadow-rendered to an isolated directory.
    shadow_ir = Path("outputs/bcr") / "shadow-stage-a" / "shadow_ir"
    assert (shadow_ir / "document_ir.json").exists()
    assert (shadow_ir / "report.md").exists()
    assert (shadow_ir / "report.docx").exists()
    assert (shadow_ir / "report.pdf").exists()
    assert (shadow_ir / "render_manifest.json").exists()
    assert (shadow_ir / "render_audit.json").exists()

    audit = json.loads((shadow_ir / "render_audit.json").read_text(encoding="utf-8"))
    assert audit["shadow"] is True
    assert audit["rendering_mode"] == "legacy"
    assert audit["finding_ids_equal"] is True


# ── service: stage B local switch ─────────────────────────────────────────────


def test_stage_b_switch_points_official_outputs_at_ir(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    service = BCRService(llm_client=_DisabledLLM())
    service.schema_first_enabled = True
    service.report_ir_rendering_enabled = True

    registry, citation_id = _legacy_registry()
    outputs = service._render_document_driven(
        "shadow-stage-b",
        _payload(),
        "高风险",
        [_finding(citation_id)],
        [],
        [(f"章节 {i}", ["审查内容"]) for i in range(8)],
        {"bcr_type": "BCR-C"},
        registry,
    )

    official = Path("outputs/bcr") / "shadow-stage-b" / "outputs"

    # Official outputs now come from the IR renderer (fixed filenames).
    assert outputs["markdown"] == str(official / "report.md")
    assert outputs["docx"] == str(official / "report.docx")
    assert outputs["pdf"] == str(official / "report.pdf")
    assert outputs["citation_map_json"] == str(official / "citation_map.json")
    assert outputs["document_ir_json"] == str(official / "document_ir.json")
    assert outputs["render_manifest_json"] == str(official / "render_manifest.json")

    # No legacy zip is registered; legacy templates are parked, not official.
    assert "zip" not in outputs
    shadow_legacy = Path("outputs/bcr") / "shadow-stage-b" / "shadow_legacy"
    legacy_docx = list(shadow_legacy.glob("*.docx"))
    assert len(legacy_docx) == 1
    assert not list(official.glob("*影子*"))  # no date-stamped legacy file in official

    # IR artifacts + manifest are real files on disk.
    for key in ("markdown", "docx", "pdf", "citation_map_json", "document_ir_json", "render_manifest_json"):
        assert Path(outputs[key]).exists(), key

    # The manifest records the switch state via render_status / gates.
    manifest = json.loads((official / "render_manifest.json").read_text(encoding="utf-8"))
    assert manifest["render_status"] == "success"
    assert manifest["finding_ids"] == ["BCR-T-01"]

    # The render audit makes the switch state explicit and visible.
    render_audit = json.loads((official / "render_audit.json").read_text(encoding="utf-8"))
    assert render_audit["rendering_mode"] == "ir"
    assert render_audit["shadow"] is False
    assert render_audit["finding_ids_equal"] is True


def test_stage_b_switch_requires_schema_first(tmp_path, monkeypatch) -> None:
    """report_ir_rendering_enabled alone (without schema-first) stays legacy."""
    monkeypatch.chdir(tmp_path)
    service = BCRService(llm_client=_DisabledLLM())
    service.schema_first_enabled = False
    service.report_ir_rendering_enabled = True

    registry, citation_id = _legacy_registry()
    outputs = service._render_document_driven(
        "switch-without-schema",
        _payload(),
        "高风险",
        [_finding(citation_id)],
        [],
        [(f"章节 {i}", ["审查内容"]) for i in range(8)],
        {"bcr_type": "BCR-C"},
        registry,
    )

    # No IR was built, so the legacy template path remains official.
    assert "zip" in outputs
    assert "render_manifest_json" not in outputs
    assert Path(outputs["docx"]).parent.name == "outputs"
    assert not (Path("outputs/bcr") / "switch-without-schema" / "shadow_ir").exists()


def test_rollback_flag_off_restores_legacy_and_keeps_ir_artifacts(tmp_path, monkeypatch) -> None:
    """Rollback (flag off) never deletes the generated IR/manifest artifacts."""
    monkeypatch.chdir(tmp_path)
    registry, citation_id = _legacy_registry()
    args = (
        "rollback-task",
        _payload(),
        "高风险",
        [_finding(citation_id)],
        [],
        [(f"章节 {i}", ["审查内容"]) for i in range(8)],
        {"bcr_type": "BCR-C"},
        registry,
    )

    # 1) switch on → official outputs are IR files + manifest.
    switched_service = BCRService(llm_client=_DisabledLLM())
    switched_service.schema_first_enabled = True
    switched_service.report_ir_rendering_enabled = True
    switched = switched_service._render_document_driven(*args)
    official = Path("outputs/bcr") / "rollback-task" / "outputs"
    manifest_path = official / "render_manifest.json"
    assert "render_manifest_json" in switched
    assert manifest_path.exists()

    # 2) rollback flag off → legacy outputs become official again.
    rolled_back_service = BCRService(llm_client=_DisabledLLM())
    rolled_back_service.schema_first_enabled = True
    rolled_back_service.report_ir_rendering_enabled = False
    legacy = rolled_back_service._render_document_driven(*args)

    assert "zip" in legacy
    assert "render_manifest_json" not in legacy
    assert Path(legacy["docx"]).parent.name == "outputs"

    # The previously generated IR/manifest artifacts survive the rollback.
    assert manifest_path.exists()
    assert (official / "report.pdf").exists()

    # The rolled-back run still shadow-renders the IR version for comparison.
    shadow_ir = Path("outputs/bcr") / "rollback-task" / "shadow_ir"
    assert (shadow_ir / "render_manifest.json").exists()
    assert (shadow_ir / "render_audit.json").exists()
