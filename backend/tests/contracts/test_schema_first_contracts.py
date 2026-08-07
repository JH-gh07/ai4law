"""Cross-module contract tests for schema-first adapters.

Two enforcement layers:

1. Behavioural layer (parametrised per registered adapter)
   - Both citation shapes (raw {{CIT-*}} and production [N]) produce identical
     ClaimBlocks with correct citation_refs.
   - The Compiler Gate passes (no diagnostics) on registered citations.
   - Unregistered citations are preserved as citation_refs (fail-closed).

2. Static layer (automatic — scans every *schema_first.py in backend/domains)
   - No adapter is allowed to define its own citation-marker regex; it must use
     extract_citation_refs from backend.common.reporting.
   - Catches hand-rolled patterns that would re-introduce ISSUE-reporting-001.
   - Does NOT require manual registration — picks up new adapters automatically.

Adding a new adapter:
  1. Write backend/domains/<loc>/<mod>/schema_first.py (static layer auto-covers it).
  2. Add one entry to ADAPTER_CASES below (behavioural layer).
"""

from __future__ import annotations

import ast
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pytest

from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry
from backend.common.reporting import DocumentCompiler

# ---------------------------------------------------------------------------
# 1. Adapter case registry
#    Each entry: (adapter_id, build_fn, chapters_fn, cid)
#    build_fn(**kwargs) -> (DocumentIR, reporting_registry)
#    chapters_fn(content: str) -> list of chapter objects
# ---------------------------------------------------------------------------

CID_ASSESS = "CIT-CN-EXPORT-ASSESSMENT-ART5-P01"
CID_DPIA   = "CIT-EU-GDPR-ART35-P01"
CID_TIA    = "CIT-EU-GDPR-ART46-P01"
CID_PIPIA  = "CIT-CN-PIPL-ART39-P01"


def _reg_with(cid: str, art: str = "1") -> CitationRegistry:
    r = CitationRegistry()
    r.register(CitationItem(
        citation_id=cid, source_id="SRC-001", citation_type="law_article",
        title="Test Law", article_no=art, authority_level="high",
        binding_force="mandatory", external_report_allowed=True,
    ))
    r.assign_footnote_number(cid)   # mirrors generator
    return r


def _assessment_case(content: str):
    from backend.domains.cn.security_assessment.schema import ChapterContent
    from backend.domains.cn.security_assessment.schema_first import build_assessment_document_ir
    return build_assessment_document_ir(
        task_id="t", company_name="TestCo",
        chapters=[ChapterContent(chapter_no=1, title="T", content=content, risk_level="HIGH")],
        citation_registry=_reg_with(CID_ASSESS),
        generated_at=datetime(2026, 8, 8, tzinfo=timezone.utc), model="m",
    )


def _dpia_case(content: str):
    from backend.domains.eu.dpia.schema import DPIAChapterContent
    from backend.domains.eu.dpia.schema_first import build_dpia_document_ir
    return build_dpia_document_ir(
        task_id="t", project_name="TestProject",
        chapters=[DPIAChapterContent(chapter_no=1, title="T", content=content, risk_level="high")],
        citation_registry=_reg_with(CID_DPIA),
        generated_at=datetime(2026, 8, 8, tzinfo=timezone.utc), model="m",
    )


def _tia_case(content: str):
    from backend.domains.eu.tia.schema import TIAChapter
    from backend.domains.eu.tia.schema_first import build_tia_document_ir
    return build_tia_document_ir(
        task_id="t", exporter_profile="TestCo",
        chapters=[TIAChapter(chapter_no=1, title="T", content=content,
                              citations=[], citation_refs=[], risk_level="HIGH")],
        citation_registry=_reg_with(CID_TIA),
        generated_at=datetime(2026, 8, 8, tzinfo=timezone.utc), model="m",
    )


def _pipia_case(content: str):
    from backend.domains.cn.pipia.schema import PIPIAChapter
    from backend.domains.cn.pipia.schema_first import build_pipia_document_ir
    return build_pipia_document_ir(
        task_id="t", company_name="TestCo",
        chapters=[PIPIAChapter(chapter_no=1, title="T", content=content,
                               citations=[], risk_level="HIGH")],
        citation_registry=_reg_with(CID_PIPIA),
        generated_at=datetime(2026, 8, 8, tzinfo=timezone.utc), model="m",
    )


ADAPTER_CASES: list[tuple[str, Callable, str]] = [
    ("assessment", _assessment_case, CID_ASSESS),
    ("dpia",       _dpia_case,       CID_DPIA),
    ("tia",        _tia_case,        CID_TIA),
    ("pipia",      _pipia_case,      CID_PIPIA),
]


# ---------------------------------------------------------------------------
# 2. Behavioural layer
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("adapter_id,build,cid", ADAPTER_CASES,
                         ids=[x[0] for x in ADAPTER_CASES])
def test_production_footnote_shape_produces_claim_block(
    adapter_id: str, build: Callable, cid: str
) -> None:
    """Production content carries [N]; must yield ClaimBlock, not raise."""
    doc, rep = build(f"法规依据陈述 [1]。")

    block = doc.sections[0].blocks[0]
    assert type(block).__name__ == "ClaimBlock", (
        f"{adapter_id}: [N] content must produce ClaimBlock, got {type(block).__name__}"
    )
    assert block.citation_refs == [cid]
    assert "[1]" not in block.text

    cr = DocumentCompiler().compile(doc, rep)
    assert cr.status == "success"
    assert not cr.diagnostics


@pytest.mark.parametrize("adapter_id,build,cid", ADAPTER_CASES,
                         ids=[x[0] for x in ADAPTER_CASES])
def test_both_shapes_produce_identical_ir(
    adapter_id: str, build: Callable, cid: str
) -> None:
    raw  = f"法规依据陈述 {{{{{cid}}}}}。"
    prod = "法规依据陈述 [1]。"
    assert build(raw)[0].model_dump(mode="json") == build(prod)[0].model_dump(mode="json")


@pytest.mark.parametrize("adapter_id,build,cid", ADAPTER_CASES,
                         ids=[x[0] for x in ADAPTER_CASES])
def test_unregistered_citation_reaches_compiler(
    adapter_id: str, build: Callable, cid: str
) -> None:
    """Unknown IDs must survive as citation_refs — never swallowed — so the
    compiler can emit a CITATION_NOT_REGISTERED diagnostic."""
    unknown = "CIT-EU-UNKNOWN-ART99-P01"
    doc, _ = build(f"无效引用 {{{{{unknown}}}}}。")
    block = doc.sections[0].blocks[0]
    assert block.citation_refs == [unknown]


# ---------------------------------------------------------------------------
# 3. Static layer — no hand-rolled marker regex in any schema_first.py
# ---------------------------------------------------------------------------

_SCHEMA_FIRST_FILES = list(
    Path(__file__).parents[2].glob("domains/**/schema_first.py")
)


def test_schema_first_files_are_discoverable() -> None:
    assert len(_SCHEMA_FIRST_FILES) >= 1, (
        "No schema_first.py found under backend/domains — "
        "update the glob if the layout changed."
    )


@pytest.mark.parametrize("path", _SCHEMA_FIRST_FILES,
                         ids=[p.parent.name for p in _SCHEMA_FIRST_FILES])
def test_adapter_uses_shared_extraction_not_hand_rolled_regex(path: Path) -> None:
    """Adapters must not define their own {{CIT-*}} regex.

    If a new adapter redefines the pattern locally, the [N] shape will be
    silently lost again — exactly the root cause of ISSUE-reporting-001.
    """
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    # Check no module-level regex that looks like a citation marker pattern
    _CIT_PATTERN_RE = re.compile(r"\{\{.*?CIT.*?\}\}")
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    # reject module-level assignments like _CITATION_MARKER_RE = re.compile(...)
                    if isinstance(node.value, ast.Call):
                        call_src = ast.unparse(node.value)
                        if "CIT" in call_src and "re.compile" in call_src:
                            pytest.fail(
                                f"{path.relative_to(Path(__file__).parents[3])}: "
                                f"defines its own citation regex '{t.id}' — "
                                "use extract_citation_refs from backend.common.reporting instead."
                            )

    # Confirm the file imports extract_citation_refs (unless it has no citations at all)
    imports_extract = "extract_citation_refs" in source
    has_cit_marker_code = "CIT-" in source
    if has_cit_marker_code:
        assert imports_extract, (
            f"{path.relative_to(Path(__file__).parents[3])}: "
            "references CIT markers but does not import extract_citation_refs — "
            "the [N] production shape will be silently lost."
        )
