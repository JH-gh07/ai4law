from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry
from backend.domains.us.cpra.deterministic_chapters import (
    build_deterministic_cpra_chapters,
    is_usable_cpra_chapter,
)
from backend.domains.us.cpra.schema import CPRACitationRef


def test_deterministic_cpra_chapters_are_complete_and_evidence_linked() -> None:
    citation_id = "CIT-US-CPRA-ART1798_100-P01"
    registry = CitationRegistry()
    registry.register(
        CitationItem(
            citation_id=citation_id,
            source_id="US-CA-001",
            title="California Civil Code — CCPA/CPRA",
            article_no="1798.100",
            display_label="CPRA §1798.100",
        )
    )
    ref = CPRACitationRef(
        citation_id=citation_id,
        source_id="US-CA-001",
        source_title="California Civil Code — CCPA/CPRA",
        article_no="1798.100",
        display_label="CPRA §1798.100",
    )
    context = """【企业信息】
- 企业名称：测试公司
- 业务模型：电商
- 数据生命周期：收集、使用、共享、删除
- 告知与同意现状：告知不完整
- 消费者权利流程：仅邮箱受理
- 出售或共享现状：存在广告共享
- 供应商管理现状：仅有 DPA 名称
【合规差距摘要】
- [HIGH] notice｜收集告知不完整｜CPRA §1798.100｜补齐收集时告知
【风险等级】HIGH
"""

    chapters = build_deterministic_cpra_chapters(
        context=context,
        level="HIGH",
        citations=[ref],
        registry=registry,
    )

    assert [chapter.chapter_no for chapter in chapters] == [1, 2, 3, 4, 5, 6]
    assert all("占位" not in chapter.content for chapter in chapters)
    assert "补齐收集时告知" in chapters[-1].content
    assert "[1]" in chapters[2].content
    assert chapters[2].citations == [citation_id]


def test_cpra_chapter_quality_gate_rejects_placeholder_and_short_text() -> None:
    assert not is_usable_cpra_chapter("（执行摘要：LLM未配置，此处为占位内容）")
    assert not is_usable_cpra_chapter("过短正文")
    assert is_usable_cpra_chapter("完整且可交付的正文。" * 20)
