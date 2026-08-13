"""IR render manifest + cross-format equivalence proof (task067 T07)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from backend.common.reporting import (
    CitationLocator,
    CitationNoteBlock,
    CitationRecord,
    CitationRegistry,
    ClaimBlock,
    ClauseGroupBlock,
    ClauseNode,
    DocumentIR,
    FindingDetailBlock,
    FindingRecord,
    FindingSummaryBlock,
    KeyValueBlock,
    KeyValueItem,
    ListBlock,
    ListItem,
    ParagraphBlock,
    Provenance,
    ReportMetadata,
    SectionIR,
    TableBlock,
    WarningBlock,
)
from backend.common.reporting.render_manifest import (
    RenderManifest,
    build_render_manifest,
    verify_render_manifest,
)

TS = datetime(2026, 8, 8, tzinfo=timezone.utc)


def _citation(citation_id: str, title: str, article: str | None = None) -> CitationRecord:
    return CitationRecord(
        citation_id=citation_id,
        source_id=f"SRC-{citation_id}",
        source_type="regulation",
        title=title,
        locator=CitationLocator(article=article) if article else None,
        authority_level="high",
        binding_force="mandatory",
        can_enter_external_report=True,
    )


def _registry() -> CitationRegistry:
    return CitationRegistry([
        _citation("cit-1", "GDPR (EU) 2016/679", "47(1)"),
        _citation("cit-2", "EDPB Recommendations 01/2020"),
    ])


def _finding(fid: str, title: str, risk: str = "MEDIUM", citation_refs=None) -> FindingRecord:
    return FindingRecord(
        finding_id=fid,
        requirement_id=f"R-{fid}",
        title=title,
        risk_level=risk,
        risk_score=60.0 if risk == "HIGH" else 30.0,
        statement="现状不合规，需要整改。",
        legal_basis=["GDPR Article 47(1)"] if citation_refs else [],
        recommendation="补齐合规要求。",
        suggested_revision=None,
        citation_refs=citation_refs or [],
    )


def _document() -> tuple[DocumentIR, CitationRegistry]:
    registry = _registry()
    document = DocumentIR(
        compiler_version="0.1.0",
        prompt_version="test",
        template_version="test",
        model="test-model",
        document_id="doc-1",
        report_type="bcr",
        metadata=ReportMetadata(
            title="测试报告",
            short_title="BCR 报告",
            company_name="TestCo",
            jurisdiction="EU",
            locale="zh-CN",
            report_date="2026-08-08",
            report_id="BCR-2026-001",
        ),
        provenance=Provenance(generated_at=TS),
        findings=[
            _finding("F-1", "约束力不足", "HIGH", citation_refs=["cit-1"]),
            _finding("F-2", "TIA 不完整", "MEDIUM"),
        ],
        citations=list(registry.records().values()),
        sections=[
            SectionIR(section_id="s1", title="报告摘要", level=1, ordinal="1", blocks=[
                ParagraphBlock(block_id="b1", text="本报告用于验证 render manifest。"),
                ClaimBlock(block_id="b2", text="集团规则应当具有法律约束力。", citation_refs=["cit-1"]),
                ListBlock(block_id="b3", ordered=True, items=[
                    ListItem(text="父项", children=[ListItem(text="子项一"), ListItem(text="子项二")]),
                    ListItem(text="第二父项"),
                ]),
                TableBlock(block_id="b4", headers=["检查项", "结果"], rows=[["A", "合规"]]),
                WarningBlock(block_id="b5", text="注意风险", severity="warning"),
                KeyValueBlock(block_id="b6", items=[KeyValueItem(label="BCR 类型", value="BCR-C")]),
            ]),
            SectionIR(section_id="s2", title="风险与 finding 摘要", level=1, ordinal="2", blocks=[
                FindingSummaryBlock(block_id="s2.summary", finding_refs=["F-1", "F-2"]),
            ]),
            SectionIR(section_id="s3", title="详细 finding", level=1, ordinal="3", blocks=[
                FindingDetailBlock(block_id="s3.d1", finding_ref="F-1"),
                FindingDetailBlock(block_id="s3.d2", finding_ref="F-2"),
            ]),
            SectionIR(section_id="s4", title="建议条款", level=1, ordinal="4", blocks=[
                ClauseGroupBlock(block_id="s4.clauses", title="建议条款", clauses=[
                    ClauseNode(node_id="c1", text="第一条", children=[
                        ClauseNode(node_id="c1-1", text="第一项", numbering_style="lower_alpha"),
                        ClauseNode(node_id="c1-2", text="第二项", numbering_style="lower_alpha"),
                    ]),
                ]),
            ]),
            SectionIR(section_id="s5", title="法规与引用", level=1, ordinal="5", blocks=[
                CitationNoteBlock(block_id="s5.citations", citation_refs=["cit-1", "cit-2"]),
            ]),
        ],
    )
    return document, registry


def _build(tmp_path: Path) -> tuple[RenderManifest, Path]:
    document, registry = _document()
    output_dir = tmp_path / "outputs"
    manifest = build_render_manifest(document, registry, output_dir, module="bcr", task_id="t1")
    return manifest, output_dir


# ── manifest structure + atomic writes ───────────────────────────────────────


def test_manifest_records_all_artifacts_and_identity(tmp_path: Path) -> None:
    manifest, output_dir = _build(tmp_path)
    assert manifest.render_status == "success"

    assert {artifact.path for artifact in manifest.artifacts} == {
        "document_ir.json", "report.md", "report.docx", "report.pdf", "citation_map.json",
    }
    # every artifact file is on disk with non-zero size
    for artifact in manifest.artifacts:
        path = output_dir / artifact.path
        assert path.exists()
        assert path.stat().st_size == artifact.size
        assert artifact.status == "rendered"

    # structural identity
    assert manifest.section_ids == ["s1", "s2", "s3", "s4", "s5"]
    assert manifest.finding_ids == ["F-1", "F-2"]
    assert [c.node_id for c in manifest.clause_identities] == ["c1", "c1-1", "c1-2"]
    assert manifest.clause_identities[0].logical_number == "1."
    assert manifest.clause_identities[1].logical_number == "(a)"
    assert manifest.citation_ids == ["cit-1", "cit-2"]
    assert manifest.citation_count == 2


def test_manifest_is_written_atomically_after_artifacts(tmp_path: Path) -> None:
    manifest, output_dir = _build(tmp_path)
    manifest_path = output_dir / "render_manifest.json"
    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["document_id"] == "doc-1"
    assert data["render_status"] == "success"
    # no stray tmp files left behind
    assert not list(output_dir.glob("*.tmp"))


def test_docx_and_pdf_stats_recorded(tmp_path: Path) -> None:
    manifest, _ = _build(tmp_path)
    assert manifest.docx_stats is not None
    assert manifest.docx_stats.paragraph_count > 0
    assert manifest.docx_stats.heading_count >= 4
    assert manifest.docx_stats.table_count >= 2
    assert manifest.docx_stats.numbering_def_count > 0

    assert manifest.pdf_stats is not None
    assert manifest.pdf_stats.page_count > 0
    assert manifest.pdf_stats.text_extracted is True
    assert manifest.pdf_stats.finding_ids_found == ["F-1", "F-2"]
    assert {font.name for font in manifest.pdf_stats.fonts} == {"STSong-Light", "LiberationSans"}


def test_all_equivalence_and_hash_gates_pass(tmp_path: Path) -> None:
    manifest, _ = _build(tmp_path)
    gate_names = {gate.name for gate in manifest.gates}
    assert "compile" in gate_names
    assert "ir_hash_immutable" in gate_names
    assert "required_artifacts" in gate_names
    assert "equivalence" in gate_names
    assert "pdf_font_embedding" in gate_names

    for gate in manifest.gates:
        if gate.name == "pdf_font_embedding":
            assert gate.status == "blocked"  # BLOCKED_BY_FONT (no CJK asset)
        else:
            assert gate.status == "pass", (gate.name, gate.diagnostics)


def test_pdf_font_gate_is_blocked_not_pass_without_cjk_asset(tmp_path: Path) -> None:
    manifest, _ = _build(tmp_path)
    font_gate = next(gate for gate in manifest.gates if gate.name == "pdf_font_embedding")
    assert font_gate.status == "blocked"
    assert any("BLOCKED_BY_FONT" in diag for diag in font_gate.diagnostics)


# ── determinism ──────────────────────────────────────────────────────────────


def test_canonical_ir_hash_and_non_time_fields_stable(tmp_path: Path) -> None:
    document_a, registry_a = _document()
    document_b, registry_b = _document()
    manifest_a = build_render_manifest(document_a, registry_a, tmp_path / "a", module="bcr", task_id="t1")
    manifest_b = build_render_manifest(document_b, registry_b, tmp_path / "b", module="bcr", task_id="t1")

    assert manifest_a.canonical_ir_sha256 == manifest_b.canonical_ir_sha256
    # non-time fields are byte-for-byte identical
    assert manifest_a.model_dump(mode="json", exclude={"generated_at"}) == \
        manifest_b.model_dump(mode="json", exclude={"generated_at"})


# ── tamper / equivalence fail-closed ─────────────────────────────────────────


def test_tampered_artifact_fails_hash_gate(tmp_path: Path) -> None:
    manifest, output_dir = _build(tmp_path)
    docx_path = output_dir / "report.docx"
    docx_path.write_bytes(docx_path.read_bytes() + b"\x00")

    gates = verify_render_manifest(manifest, output_dir)
    hash_gate = next(gate for gate in gates if gate.name == "artifact_hash")
    assert hash_gate.status == "fail"
    assert any("report.docx" in diag for diag in hash_gate.diagnostics)


def test_deleted_finding_fails_equivalence_gate(tmp_path: Path) -> None:
    manifest, output_dir = _build(tmp_path)
    md_path = output_dir / "report.md"
    md_path.write_text(md_path.read_text(encoding="utf-8").replace("F-1", "F-X"), encoding="utf-8")

    gates = verify_render_manifest(manifest, output_dir)
    equivalence = next(gate for gate in gates if gate.name == "equivalence")
    assert equivalence.status == "fail"
    assert any("F-1" in diag for diag in equivalence.diagnostics)


def test_reordered_finding_fails_equivalence_gate(tmp_path: Path) -> None:
    manifest, output_dir = _build(tmp_path)
    md_path = output_dir / "report.md"
    text = md_path.read_text(encoding="utf-8")
    # swap the two finding IDs' first occurrences to break order
    swapped = text.replace("F-1", "__TMP__").replace("F-2", "F-1").replace("__TMP__", "F-2")
    md_path.write_text(swapped, encoding="utf-8")

    gates = verify_render_manifest(manifest, output_dir)
    equivalence = next(gate for gate in gates if gate.name == "equivalence")
    assert equivalence.status == "fail"
    assert any("顺序错误" in diag for diag in equivalence.diagnostics)


# ── sensitive-content hygiene ────────────────────────────────────────────────


def test_manifest_contains_no_finding_body_or_secrets(tmp_path: Path) -> None:
    document, registry = _document()
    # plant a distinctive "upload body"-like statement on a finding
    document.findings[0].statement = "SECRET-UPLOAD-BODY-abc123"
    manifest = build_render_manifest(document, registry, tmp_path / "out", module="bcr", task_id="t1")

    raw = json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False)
    assert "SECRET-UPLOAD-BODY-abc123" not in raw
    assert "现状不合规" not in raw  # finding statement text is never persisted
    for marker in ("password", "api_key", "Bearer ", "PRIVATE KEY", "sk-"):
        assert marker.lower() not in raw.lower()


# ── compile gate fail-closed ─────────────────────────────────────────────────


def test_compile_blocked_ir_writes_no_artifacts_and_error_status(tmp_path: Path) -> None:
    document, registry = _document()
    document.render_contract.profile_id = "no-such-profile"
    output_dir = tmp_path / "out"
    manifest = build_render_manifest(document, registry, output_dir, module="bcr", task_id="t1")

    assert manifest.render_status == "error"
    compile_gate = next(gate for gate in manifest.gates if gate.name == "compile")
    assert compile_gate.status == "fail"
    assert "RENDER_PROFILE_UNKNOWN" in compile_gate.diagnostics
    # no artifacts were produced for a blocked render
    assert not (output_dir / "report.pdf").exists()
    assert not (output_dir / "render_manifest.json").exists()
