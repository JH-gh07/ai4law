"""Contract tests for extract_citation_refs — the two production citation shapes.

Regression guard for ISSUE-REPORTING-001.

The chapter generators call ``convert_citation_markers`` BEFORE the chapter is
stored, so ``chapter.content`` reaching a schema-first adapter carries resolved
footnotes (``[1]``), not raw ``{{CIT-...}}`` markers. An adapter that only
recognises the raw-marker shape silently loses every citation ref on real
content, and the ``[1]`` residue then trips the semantic-block validator.

Both shapes must therefore resolve to the same citation_refs.
"""

from __future__ import annotations

from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry
from backend.common.reporting.compat import extract_citation_refs


def _item(cid: str, article: str) -> CitationItem:
    return CitationItem(
        citation_id=cid,
        source_id="EU-LAW-001",
        citation_type="law_article",
        title="GDPR (EU) 2016/679",
        article_no=article,
        authority_level="high",
        binding_force="mandatory",
        external_report_allowed=True,
    )


def _registry_with_footnotes(*cids: str) -> CitationRegistry:
    """Register cids and assign footnote numbers in argument order."""
    registry = CitationRegistry()
    for index, cid in enumerate(cids, start=1):
        registry.register(_item(cid, str(index)))
    for cid in cids:
        registry.assign_footnote_number(cid)
    return registry


CID_A = "CIT-EU-GDPR-ART35-P01"
CID_B = "CIT-EU-GDPR-ART36-P01"


# ── raw {{CIT-*}} shape (fixtures, pre-conversion content) ──


def test_raw_marker_shape_yields_refs_and_strips_marker() -> None:
    registry = _registry_with_footnotes(CID_A)

    text, refs = extract_citation_refs(
        f"该处理活动属于大规模处理特殊类别数据 {{{{{CID_A}}}}}。", registry
    )

    assert refs == [CID_A]
    assert text == "该处理活动属于大规模处理特殊类别数据。"


# ── production [N] shape (post convert_citation_markers) ──


def test_footnote_shape_resolves_back_to_citation_id() -> None:
    registry = _registry_with_footnotes(CID_A)

    text, refs = extract_citation_refs(
        "该处理活动属于大规模处理特殊类别数据 [1]。", registry
    )

    assert refs == [CID_A], "footnote [1] must resolve back to its citation_id"
    assert text == "该处理活动属于大规模处理特殊类别数据。"


def test_both_shapes_produce_identical_refs() -> None:
    """The core invariant: pre- and post-conversion content agree."""
    registry = _registry_with_footnotes(CID_A)

    _, raw_refs = extract_citation_refs(f"事实陈述 {{{{{CID_A}}}}}。", registry)
    _, prod_refs = extract_citation_refs("事实陈述 [1]。", registry)

    assert raw_refs == prod_refs == [CID_A]


def test_multiple_footnotes_keep_first_appearance_order() -> None:
    registry = _registry_with_footnotes(CID_A, CID_B)

    _, refs = extract_citation_refs("先看 [2]，再看 [1]。", registry)

    assert refs == [CID_B, CID_A], "order follows appearance in text, not registry"


def test_repeated_footnote_is_deduplicated() -> None:
    registry = _registry_with_footnotes(CID_A)

    _, refs = extract_citation_refs("依据 [1]，并再次依据 [1]。", registry)

    assert refs == [CID_A]


# ── failure modes must stay observable, never silently dropped ──


def test_unregistered_marker_survives_as_ref_so_compiler_fails_closed() -> None:
    """An unknown marker must reach the compiler, not be swallowed here."""
    registry = _registry_with_footnotes(CID_A)
    unknown = "CIT-EU-GDPR-ART99-P01"

    _, refs = extract_citation_refs(f"未注册引用 {{{{{unknown}}}}}。", registry)

    assert refs == [unknown]


def test_unmapped_footnote_number_is_left_in_text_as_diagnostic() -> None:
    """[9] with no registry entry is NOT a citation; it must not be invented."""
    registry = _registry_with_footnotes(CID_A)

    text, refs = extract_citation_refs("疑似引用 [9]。", registry)

    assert refs == []
    assert "[9]" in text, "unresolvable footnote must stay visible, not vanish"


def test_bracketed_non_footnote_text_is_not_treated_as_citation() -> None:
    registry = _registry_with_footnotes(CID_A)

    text, refs = extract_citation_refs("参见附件 [附录A] 说明。", registry)

    assert refs == []
    assert "[附录A]" in text


def test_no_registry_falls_back_to_raw_markers_only() -> None:
    """Without a registry, [N] cannot be resolved and must be left alone."""
    _, refs = extract_citation_refs(f"事实 {{{{{CID_A}}}}} 与 [1]。", None)

    assert refs == [CID_A]


def test_empty_text_is_safe() -> None:
    registry = _registry_with_footnotes(CID_A)

    text, refs = extract_citation_refs("", registry)

    assert text == ""
    assert refs == []
