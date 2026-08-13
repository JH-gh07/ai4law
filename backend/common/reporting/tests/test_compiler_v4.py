"""v4 compiler gates (task067 T01): finding / clause / render-contract invariants."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.common.reporting import (
    ActionRecord,
    CitationNoteBlock,
    CitationRecord,
    ClauseGroupBlock,
    ClauseNode,
    DocumentCompiler,
    DocumentIR,
    FindingDetailBlock,
    FindingRecord,
    FindingReferenceBlock,
    FindingSummaryBlock,
    Provenance,
    ReportMetadata,
    RenderContract,
    SectionIR,
)


def _document(*, findings=None, actions=None, sections=None, render_contract=None, citations=None) -> DocumentIR:
    return DocumentIR(
        compiler_version="0.1.0",
        prompt_version="test",
        template_version="test",
        model="test-model",
        document_id="doc-1",
        report_type="bcr",
        metadata=ReportMetadata(title="测试报告"),
        provenance=Provenance(generated_at=datetime.now(timezone.utc)),
        findings=findings or [],
        actions=actions or [],
        sections=sections or [],
        citations=citations or [],
        render_contract=render_contract or RenderContract(),
    )


def _finding(fid: str = "F-1", **kw) -> FindingRecord:
    base = dict(
        finding_id=fid,
        requirement_id=f"R-{fid[-1]}",
        title=f"发现 {fid}",
        statement="现状不合规。",
    )
    base.update(kw)
    return FindingRecord(**base)


def _detail(fid: str, block_id: str) -> FindingDetailBlock:
    return FindingDetailBlock(block_id=block_id, finding_ref=fid)


def test_v4_fixture_compiles_clean_and_records_primary_display_count() -> None:
    document = _document(
        findings=[_finding("F-1"), _finding("F-2")],
        actions=[
            ActionRecord(action_id="A-1", finding_refs=["F-1", "F-2"], title="整改一")
        ],
        sections=[
            SectionIR(section_id="s1", title="发现摘要", level=1, blocks=[
                FindingSummaryBlock(block_id="b1", finding_refs=["F-1", "F-2"]),
            ]),
            SectionIR(section_id="s2", title="发现详情", level=1, blocks=[
                _detail("F-1", "b2"),
                _detail("F-2", "b3"),
                ClauseGroupBlock(block_id="b4", title="建议条款", clauses=[
                    ClauseNode(
                        node_id="cl-1",
                        text="第一款",
                        children=[ClauseNode(node_id="cl-1-1", text="第一项", numbering_style="lower_alpha")],
                    )
                ]),
            ]),
        ],
    )

    result = DocumentCompiler().compile(document)

    assert result.status == "success", [d.code for d in result.diagnostics]
    assert [f.primary_display_count for f in document.findings] == [1, 1]


def test_duplicate_finding_id_is_rejected() -> None:
    document = _document(
        findings=[_finding("F-1"), _finding("F-1", title="重复 ID 不同标题")],
        sections=[
            SectionIR(section_id="s1", title="详情", level=1, blocks=[_detail("F-1", "b1")])
        ],
    )
    result = DocumentCompiler().compile(document)
    assert result.status == "error"
    assert any(d.code == "FINDING_ID_DUPLICATE" for d in result.diagnostics)


def test_finding_without_primary_display_is_rejected() -> None:
    document = _document(findings=[_finding("F-1")], sections=[])
    result = DocumentCompiler().compile(document)
    assert result.status == "error"
    assert any(d.code == "FINDING_PRIMARY_DISPLAY_COUNT" for d in result.diagnostics)


def test_finding_with_two_primary_displays_is_rejected() -> None:
    document = _document(
        findings=[_finding("F-1")],
        sections=[
            SectionIR(section_id="s1", title="详情", level=1, blocks=[
                _detail("F-1", "b1"),
                _detail("F-1", "b2"),
            ])
        ],
    )
    result = DocumentCompiler().compile(document)
    assert result.status == "error"
    assert any(d.code == "FINDING_PRIMARY_DISPLAY_COUNT" for d in result.diagnostics)


def test_finding_reference_does_not_inflate_primary_display_count() -> None:
    document = _document(
        findings=[_finding("F-1")],
        sections=[
            SectionIR(section_id="s1", title="详情", level=1, blocks=[
                _detail("F-1", "b1"),
                FindingReferenceBlock(block_id="b2", finding_ref="F-1", note="见整改优先级"),
            ])
        ],
    )
    result = DocumentCompiler().compile(document)
    assert result.status == "success", [d.code for d in result.diagnostics]
    assert document.findings[0].primary_display_count == 1


def test_summary_referencing_missing_finding_is_rejected() -> None:
    document = _document(
        findings=[_finding("F-1")],
        sections=[
            SectionIR(section_id="s1", title="摘要", level=1, blocks=[
                FindingSummaryBlock(block_id="b1", finding_refs=["F-1", "F-MISSING"]),
            ]),
            SectionIR(section_id="s2", title="详情", level=1, blocks=[_detail("F-1", "b2")]),
        ],
    )
    result = DocumentCompiler().compile(document)
    assert result.status == "error"
    assert any(d.code == "FINDING_REF_NOT_REGISTERED" for d in result.diagnostics)


def test_detail_referencing_missing_finding_is_rejected() -> None:
    document = _document(
        findings=[_finding("F-1")],
        sections=[
            SectionIR(section_id="s1", title="详情", level=1, blocks=[
                _detail("F-1", "b1"),
                _detail("F-MISSING", "b2"),
            ])
        ],
    )
    result = DocumentCompiler().compile(document)
    assert result.status == "error"
    assert any(d.code == "FINDING_REF_NOT_REGISTERED" for d in result.diagnostics)


def test_clause_depth_exceeding_limit_is_rejected() -> None:
    deep = ClauseNode(node_id="cl-1", text="一", children=[
        ClauseNode(node_id="cl-1-1", text="二", children=[
            ClauseNode(node_id="cl-1-1-1", text="三", children=[
                ClauseNode(node_id="cl-1-1-1-1", text="四", children=[
                    ClauseNode(node_id="cl-1-1-1-1-1", text="五", children=[
                        ClauseNode(node_id="cl-1-1-1-1-1-1", text="六"),
                    ]),
                ]),
            ]),
        ]),
    ])
    document = _document(
        sections=[SectionIR(section_id="s1", title="条款", level=1, blocks=[
            ClauseGroupBlock(block_id="b1", title="建议", clauses=[deep]),
        ])],
    )
    result = DocumentCompiler().compile(document)
    assert result.status == "error"
    assert any(d.code == "CLAUSE_DEPTH_EXCEEDED" for d in result.diagnostics)


def test_duplicate_clause_node_id_is_rejected() -> None:
    document = _document(
        sections=[SectionIR(section_id="s1", title="条款", level=1, blocks=[
            ClauseGroupBlock(block_id="b1", title="建议", clauses=[
                ClauseNode(node_id="cl-dup", text="一"),
                ClauseNode(node_id="cl-dup", text="二"),
            ]),
        ])],
    )
    result = DocumentCompiler().compile(document)
    assert result.status == "error"
    assert any(d.code == "CLAUSE_NODE_ID_DUPLICATE" for d in result.diagnostics)


def test_action_referencing_missing_finding_is_rejected() -> None:
    document = _document(
        findings=[_finding("F-1")],
        actions=[ActionRecord(action_id="A-1", finding_refs=["F-MISSING"], title="整改")],
        sections=[SectionIR(section_id="s1", title="详情", level=1, blocks=[_detail("F-1", "b1")])],
    )
    result = DocumentCompiler().compile(document)
    assert result.status == "error"
    assert any(d.code == "ACTION_FINDING_REF_NOT_REGISTERED" for d in result.diagnostics)


def test_unknown_render_profile_is_fatal() -> None:
    document = _document(
        render_contract=RenderContract(profile_id="no-such-profile")
    )
    result = DocumentCompiler().compile(document)
    assert result.status == "fatal"
    assert any(d.code == "RENDER_PROFILE_UNKNOWN" for d in result.diagnostics)


def test_unknown_block_type_is_rejected_at_schema_level() -> None:
    with pytest.raises(ValidationError):
        SectionIR(section_id="s1", title="x", level=1, blocks=[
            {"block_id": "b1", "type": "not_a_real_block", "text": "x"}
        ])


def test_citation_note_refs_are_validated() -> None:
    document = _document(
        citations=[
            CitationRecord(
                citation_id="cit-1", source_id="law-1", source_type="regulation", title="法"
            )
        ],
        sections=[
            SectionIR(section_id="s1", title="附录", level=1, blocks=[
                CitationNoteBlock(block_id="b1", citation_refs=["cit-1"]),
            ]),
        ],
    )
    result = DocumentCompiler().compile(document)
    assert result.status == "success"

    broken = _document(
        sections=[
            SectionIR(section_id="s1", title="附录", level=1, blocks=[
                CitationNoteBlock(block_id="b1", citation_refs=["cit-missing"]),
            ]),
        ],
    )
    result_broken = DocumentCompiler().compile(broken)
    assert result_broken.status == "error"
    assert any(d.code == "CITATION_NOT_REGISTERED" for d in result_broken.diagnostics)
