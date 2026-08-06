"""Test P0-7: Citation policy should not flag generic descriptive prose."""
import pytest
from backend.common.llm.postprocess import apply_citation_policy


def test_generic_risk_level_not_flagged():
    """Generic risk level descriptions should not require citations."""
    text = "整体风险等级为中等。"
    result = apply_citation_policy(text, allowed_citations=None)
    assert "【待核验：缺少法规依据】" not in result.text
    assert len([v for v in result.violations if v.code == "required_citation_missing"]) == 0


def test_generic_should_statement_not_flagged():
    """Generic recommendations with 应当 should not require citations."""
    text = "企业应当补充相关材料。"
    result = apply_citation_policy(text, allowed_citations=None)
    assert "【待核验：缺少法规依据】" not in result.text
    assert len([v for v in result.violations if v.code == "required_citation_missing"]) == 0


def test_specific_legal_obligation_requires_citation():
    """Specific legal obligations citing laws SHOULD require citations."""
    text = "依据《个人信息保护法》第三十八条，企业应当进行个人信息保护影响评估。"
    result = apply_citation_policy(text, allowed_citations=None)
    assert "【待核验：缺少法规依据】" in result.text
    violations = [v for v in result.violations if v.code == "required_citation_missing"]
    assert len(violations) == 1
    assert violations[0].claim_type == "LEGAL_RULE"


def test_specific_legal_obligation_with_valid_citation():
    """Legal obligations with valid citations should not be flagged."""
    text = "依据《个人信息保护法》第三十八条，企业应当进行个人信息保护影响评估。【依据：《个人信息保护法》第三十八条】"
    result = apply_citation_policy(
        text,
        allowed_citations=["《个人信息保护法》第三十八条"]
    )
    assert "【待核验：缺少法规依据】" not in result.text
    assert len([v for v in result.violations if v.code == "required_citation_missing"]) == 0


def test_definitive_risk_judgment_requires_citation():
    """Definitive risk assessment conclusions should require citations."""
    text = "经评估，本次数据出境活动属于高风险。"
    result = apply_citation_policy(text, allowed_citations=None)
    assert "【待核验：缺少法规依据】" in result.text
    violations = [v for v in result.violations if v.code == "required_citation_missing"]
    assert len(violations) == 1
    assert violations[0].claim_type == "RISK_JUDGMENT"


def test_fallback_chapter_prose_not_flagged():
    """Fallback chapter descriptive prose should not be flagged."""
    text = """科技有限公司属于互联网行业，当前拟将境内收集和产生的数据传输至美国，主要目的为业务运营支持。

结合诊断结果，系统当前推荐路径为标准合同，整体风险等级为中等。

从现有输入看，本次出境活动的核心关注点包括：ISSUE-001（个人信息保护影响评估）：需补充相关事实、证据和整改安排。"""

    result = apply_citation_policy(text, allowed_citations=None)
    # None of these paragraphs should be flagged
    assert result.text.count("【待核验：缺少法规依据】") == 0
    assert len([v for v in result.violations if v.code == "required_citation_missing"]) == 0
