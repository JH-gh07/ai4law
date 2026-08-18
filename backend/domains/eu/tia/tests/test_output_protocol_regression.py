"""Output protocol regression for the TIA schema-first adapter.

task081 T081-05: Markdown、citation marker、未知法规引用进入
``ParagraphBlock`` / ``DocumentIR`` 前必须被清理或拒绝。TIA 的
``build_tia_document_ir`` 与 CPRA 同构，同样会在 ``[N]`` 无法解析时由
``_FOOTNOTE_RESIDUE_RE`` 兜底，避免 ParagraphBlock 校验吃掉
``semantic block text must not contain Markdown or citation markers``。
"""

from __future__ import annotations

import pytest

from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry
from backend.domains.eu.tia.schema import TIAChapter
from backend.domains.eu.tia.schema_first import _semantic_text, build_tia_document_ir

_CID = "CIT-EU-GDPR-ART44-P01"

_FORBIDDEN_FRAGMENTS = ("**", "__", "`", "{{CIT-", "# ")


def _registry() -> CitationRegistry:
    reg = CitationRegistry()
    reg.register(CitationItem(
        citation_id=_CID,
        source_id="EU-LAW-001",
        citation_type="law_article",
        title="GDPR (EU) 2016/679",
        article_no="44",
        authority_level="high",
        binding_force="mandatory",
        external_report_allowed=True,
    ))
    reg.assign_footnote_number(_CID)
    return reg


def _blocks(doc_ir):
    return [blk for section in doc_ir.sections for blk in section.blocks]


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("**加粗**正文", "加粗正文"),
        ("__下划线__正文", "下划线正文"),
        ("`代码`正文", "代码正文"),
        ("## 二级标题正文", "二级标题正文"),
        ("###  三级标题正文", "三级标题正文"),
    ],
)
def test_semantic_text_strips_markdown(raw: str, expected: str) -> None:
    assert _semantic_text(raw) == expected


def test_build_ir_cleans_markdown_and_citation_markers() -> None:
    chapter = TIAChapter(
        chapter_no=1,
        title="传输概述",
        content=(
            "## 传输概述\n\n"
            "根据 **GDPR 第 44 条**，向第三国传输须确保保护水平不降低"
            "{{CIT-EU-GDPR-ART44-P01}}。\n\n"
            "采用 SCC 作为`传输工具` [1]。"
        ),
        citations=["GDPR Art 44"],
        citation_refs=[],
        risk_level="HIGH",
    )

    doc_ir, reporting_reg = build_tia_document_ir(
        task_id="regression-tia",
        exporter_profile="EU Exporter GmbH",
        chapters=[chapter],
        citation_registry=_registry(),
        model="deepseek-v3",
    )

    blocks = _blocks(doc_ir)
    assert len(blocks) >= 2
    for blk in blocks:
        if blk.type in ("paragraph", "claim"):
            for fragment in _FORBIDDEN_FRAGMENTS:
                assert fragment not in blk.text, f"{blk.block_id} 泄露 {fragment!r}: {blk.text!r}"

    claims = [blk for blk in blocks if blk.type == "claim"]
    assert any(_CID in blk.citation_refs for blk in claims)
    assert reporting_reg.resolve(_CID) is not None


def test_unknown_footnote_residue_does_not_leak_into_block_text() -> None:
    chapter = TIAChapter(
        chapter_no=1,
        title="未注册引用",
        content="该传输依赖某个未登记法规 [9]。",
        citations=[],
        citation_refs=[],
        risk_level="LOW",
    )

    doc_ir, _ = build_tia_document_ir(
        task_id="regression-tia-unknown",
        exporter_profile="EU Exporter GmbH",
        chapters=[chapter],
        citation_registry=_registry(),
        model="deepseek-v3",
    )

    blocks = _blocks(doc_ir)
    text_blocks = [blk for blk in blocks if blk.type in ("paragraph", "claim")]
    assert text_blocks
    blk = text_blocks[0]
    # 残留 [9] 被 fail-closed 地提升为引用身份，而非静默丢弃或泄入正文。
    assert blk.type == "claim"
    assert "[9]" in blk.citation_refs
    assert blk.verification == "missing_evidence"
    assert "[9]" not in blk.text
    assert "{{CIT-" not in blk.text
