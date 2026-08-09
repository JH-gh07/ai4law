from backend.domains.eu.tia.deterministic_chapters import select_reliable_chapter


def test_truncated_model_chapter_uses_structured_fallback() -> None:
    fallback = "## 第三国法律与实践\n\n- 国家风险：HIGH\n\n证据缺失时不得放行。"

    assert select_reliable_chapter("分析显示风险较高，因此最终结论要求暂停", fallback) == fallback
    assert select_reliable_chapter("措施尚未证明已有效部署。在获得并审查证明S", fallback) == fallback


def test_internal_review_marker_uses_structured_fallback() -> None:
    fallback = "## 传输场景与角色\n\n缺失项保持未确认。"

    assert select_reliable_chapter("该传输必须进一步评估。【待核验：缺少法规依据】", fallback) == fallback


def test_complete_model_chapter_is_preserved() -> None:
    generated = (
        "## 法律分析\n\n"
        "现有证据不足以证明补充措施已经有效实施 [3]。"
        "虽然用户声明采用端到端加密和欧盟密钥管理，但尚未提交技术架构、"
        "密钥托管配置、独立审计记录或适用的合同附件。"
        "在这些材料得到核验前，不能仅凭结构化勾选认定传输已经达到实质等同保护水平。"
    )

    assert select_reliable_chapter(generated, "fallback") == generated
