"""Output protocol regression for the CPRA schema-first adapter.

task081 T081-05: Markdown、citation marker、未知法规引用进入
``ParagraphBlock`` / ``DocumentIR`` 前必须被清理或拒绝。历史缺陷是 LLM
输出中的 ``**bold**`` / ``# heading`` / ``{{CIT-...}}`` / ``[N]`` 残留直接
喂给 ``ParagraphBlock``，触发 ``semantic block text must not contain
Markdown or citation markers`` 的 Pydantic 校验崩溃。

本文件把三条防线固化为回归用例：

1. ``_semantic_text`` 清掉内联/块级 Markdown（heading、bold、code、残余
   分隔符）；
2. 未知 ``[N]`` 脚注残留不能进入块文本（由 ``build_cpra_document_ir``
   的 ``_FOOTNOTE_RESIDUE_RE`` 兜底）；
3. 完整 ``build_cpra_document_ir`` 产物里任何块文本都不含 Markdown 或
   citation marker。
"""

from __future__ import annotations

import pytest

from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry
from backend.domains.us.cpra.schema import CPRAChapter
from backend.domains.us.cpra.schema_first import _semantic_text, build_cpra_document_ir

_CID = "CIT-US-CPRA-ART1798_100-P01"

# 与 ParagraphBlock._validate_semantic_text 保持一致的反向断言锚点。
_FORBIDDEN_FRAGMENTS = ("**", "__", "`", "{{CIT-", "# ")


def _registry() -> CitationRegistry:
    reg = CitationRegistry()
    reg.register(CitationItem(
        citation_id=_CID,
        source_id="US-REG-001",
        citation_type="law_article",
        title="CPRA (California Privacy Rights Act)",
        article_no="1798.100",
        authority_level="high",
        binding_force="mandatory",
        external_report_allowed=True,
    ))
    reg.assign_footnote_number(_CID)
    return reg


def _blocks(doc_ir):
    return [blk for section in doc_ir.sections for blk in section.blocks]


# ── 1. `_semantic_text` strips inline + block markdown ────────────────────────


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("**加粗**正文", "加粗正文"),
        ("__下划线__正文", "下划线正文"),
        ("`代码`正文", "代码正文"),
        ("## 二级标题正文", "二级标题正文"),
        ("###  三级标题正文", "三级标题正文"),
        ("结尾残余分隔符**", "结尾残余分隔符"),
        ("`代码` 与 **加粗**", "代码 与 加粗"),
    ],
)
def test_semantic_text_strips_markdown(raw: str, expected: str) -> None:
    assert _semantic_text(raw) == expected


def test_semantic_text_does_not_mangle_plain_prose() -> None:
    plain = "TechCo 在加州收集消费者个人信息，符合 CPRA §1798.100 通知义务。"
    assert _semantic_text(plain) == plain


# ── 2. citation markers + unknown footnote residue never enter block text ────


def test_build_ir_cleans_markdown_and_citation_markers() -> None:
    chapter = CPRAChapter(
        chapter_no=1,
        title="CPRA 通知义务",
        content=(
            "## 通知义务\n\n"
            "TechCo 收集消费者个人信息，符合 **CPRA §1798.100** 的通知义务"
            "{{CIT-US-CPRA-ART1798_100-P01}}。\n\n"
            "消费者可在线行使`删除权` [1]。"
        ),
        citations=["CPRA §1798.100"],
        citation_refs=[],
        risk_level="MEDIUM",
    )

    doc_ir, reporting_reg = build_cpra_document_ir(
        task_id="regression-cpra",
        company_name="TechCo Inc.",
        chapters=[chapter],
        citation_registry=_registry(),
        model="deepseek-v3",
    )

    blocks = _blocks(doc_ir)
    # 标题段 + 两段正文 + 引用附录，全部段落都必须是合法语义文本。
    assert len(blocks) >= 2
    for blk in blocks:
        if blk.type in ("paragraph", "claim"):
            for fragment in _FORBIDDEN_FRAGMENTS:
                assert fragment not in blk.text, f"{blk.block_id} 泄露 {fragment!r}: {blk.text!r}"

    # 引用 marker 被识别为 claim，且引用编号可解析。
    claims = [blk for blk in blocks if blk.type == "claim"]
    assert any(_CID in blk.citation_refs for blk in claims)
    assert reporting_reg.resolve(_CID) is not None


def test_unknown_footnote_residue_does_not_leak_into_block_text() -> None:
    # [9] 不在 registry 里：`extract_citation_refs` 会保留它，但
    # `build_cpra_document_ir` 的 _FOOTNOTE_RESIDUE_RE 必须在写入块前清掉，
    # 否则 ParagraphBlock 校验会抛 ValueError。
    chapter = CPRAChapter(
        chapter_no=1,
        title="未注册引用",
        content="报告结论依赖某个未登记法规 [9]。",
        citations=[],
        citation_refs=[],
        risk_level="LOW",
    )

    doc_ir, _ = build_cpra_document_ir(
        task_id="regression-cpra-unknown",
        company_name="TechCo Inc.",
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
