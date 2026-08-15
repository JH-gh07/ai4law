"""task068 T11 — shared shadow render + diff audit + switch/rollback primitive.

The BCR shadow switch (task067 T09) is generalised into
``backend.common.reporting.shadow_render`` so CPRA / EO 14117 / DPIA / Review
share one non-destructive switch/rollback discipline. These tests prove the
module is module-agnostic and never mutates a legal conclusion.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from backend.common.reporting import (
    CitationLocator,
    CitationNoteBlock,
    CitationRecord,
    CitationRegistry,
    DocumentIR,
    FindingBasis,
    FindingDetailBlock,
    FindingRecord,
    Provenance,
    ReportMetadata,
    SectionIR,
)
from backend.common.reporting.shadow_render import (
    CollectionAudit,
    audit_ir_vs_legacy,
    render_ir_artifacts,
    write_audit_json,
)

TS = datetime(2026, 8, 10, tzinfo=timezone.utc)


def _document(module: str) -> tuple[DocumentIR, CitationRegistry]:
    registry = CitationRegistry([
        CitationRecord(
            citation_id="cit-1", source_id="SRC-1", source_type="regulation",
            title="Test Regulation", locator=CitationLocator(article="1"),
            authority_level="high", binding_force="mandatory",
            can_enter_external_report=True,
        )
    ])
    registry.assign_footnote_number("cit-1")
    finding = FindingRecord(
        finding_id="F-1", requirement_id="R-1", title="问题 1", risk_level="HIGH",
        risk_score=60.0, statement="现状不合规。", legal_basis=["Test Regulation Article 1"],
        recommendation="补齐合规要求。", citation_refs=["cit-1"],
        basis_entries=[FindingBasis(
            label="Test Regulation Article 1", citation_ref="cit-1",
            rationale="归因自既有风险分析。",
        )],
    )
    document = DocumentIR(
        compiler_version="0.1.0", prompt_version="test", template_version="test",
        model="test-model", document_id=f"doc-{module}", report_type="review",
        metadata=ReportMetadata(title=f"{module} 报告"),
        provenance=Provenance(generated_at=TS),
        findings=[finding],
        citations=list(registry.records().values()),
        sections=[
            SectionIR(section_id="s-detail", title="详细发现", level=1, ordinal="1", blocks=[
                FindingDetailBlock(block_id="detail", finding_ref="F-1"),
            ]),
            SectionIR(section_id="s-cite", title="引用", level=1, ordinal="2", blocks=[
                CitationNoteBlock(block_id="cite", citation_refs=["cit-1"]),
            ]),
        ],
    )
    return document, registry


def test_render_ir_artifacts_is_module_agnostic(tmp_path: Path) -> None:
    for module in ("cpra", "eo14117", "dpia", "review"):
        document, registry = _document(module)
        manifest = render_ir_artifacts(document, registry, tmp_path / module, module=module, task_id="t")
        assert manifest.render_status == "success"
        assert manifest.finding_ids == ["F-1"]
        assert (tmp_path / module / "render_manifest.json").exists()


def test_audit_records_missing_ids_and_pdf_gate_stays_blocked(tmp_path: Path) -> None:
    document, registry = _document("cpra")
    manifest = render_ir_artifacts(document, registry, tmp_path / "out", module="cpra", task_id="t")

    audit = audit_ir_vs_legacy(manifest, ["F-1", "LEGACY-ONLY"], rendering_mode="legacy", shadow=True)

    assert audit.finding_ids_equal is False
    assert audit.missing_in_ir == ["LEGACY-ONLY"]
    assert audit.missing_in_legacy == []
    assert audit.shadow is True
    assert audit.rendering_mode == "legacy"
    # PDF CJK font gate passes now that a redistributable CJK asset is tracked.
    assert audit.pdf_font_gate == "pass"


def test_write_audit_json_round_trips_without_sensitive_content(tmp_path: Path) -> None:
    audit = CollectionAudit(
        rendering_mode="ir", shadow=False, finding_ids_equal=True,
        ir_finding_ids=["F-1"], legacy_finding_ids=["F-1"],
        render_status="success", pdf_font_gate="blocked",
    )
    path = write_audit_json(audit, tmp_path / "render_audit.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["rendering_mode"] == "ir"
    assert data["shadow"] is False

    raw = path.read_text(encoding="utf-8")
    for forbidden in ("api_key", "token", "secret", "现状不合规"):
        assert forbidden not in raw
