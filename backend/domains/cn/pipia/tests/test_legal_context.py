from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry
from backend.domains.cn.pipia.legal_context import (
    PIPIA_PROMPT_CITATION_LIMIT,
    build_pipia_legal_prompt_context,
)


def test_pipia_prompt_context_keeps_full_registry_but_caps_model_candidates() -> None:
    registry = CitationRegistry()
    for article in range(1, 41):
        registry.register(
            CitationItem(
                citation_id=f"CIT-CN-CN_LAW_003-ART{article}-P01",
                source_id="CN-LAW-003",
                title="中华人民共和国个人信息保护法",
                article_no=str(article),
                display_label=f"中华人民共和国个人信息保护法 第{article}条",
                quote_text=f"第{article}条测试内容",
            )
        )

    context = build_pipia_legal_prompt_context(registry)

    assert len(registry) == 40
    assert len(context.citation_labels) == PIPIA_PROMPT_CITATION_LIMIT
    assert len(context.citation_ids) == PIPIA_PROMPT_CITATION_LIMIT
    assert "CIT-CN-CN_LAW_003-ART39-P01" in context.marker_section
    assert "中华人民共和国个人信息保护法 第39条" in context.regulation_snippet
    assert "CIT-CN-CN_LAW_003-ART30-P01" not in context.marker_section
