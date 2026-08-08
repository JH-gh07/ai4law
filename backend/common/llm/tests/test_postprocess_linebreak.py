"""Test P0-3: Line break regex should not shatter version numbers."""

from backend.common.llm.postprocess import normalize_legal_markdown_structure


def test_tls_version_not_broken():
    """TLS 1.3, v1.2.3, ISO 27001 should survive intact."""
    input_md = "采用 TLS 1.3 加密传输。"
    result = normalize_legal_markdown_structure(input_md)
    assert "TLS 1.3" in result
    assert "TLS\n" not in result
    assert "1. 3" not in result


def test_version_numbers_survive():
    """Various version number patterns should not be split."""
    cases = [
        ("软件版本 v1.2.3 已发布。", "v1.2.3"),
        ("符合 GB/T 35273-2020 标准。", "35273-2020"),
        ("通过 ISO 27001 认证。", "27001"),
    ]
    for input_text, expected_fragment in cases:
        result = normalize_legal_markdown_structure(input_text)
        assert expected_fragment in result, f"Expected '{expected_fragment}' intact in: {result}"


def test_legal_paragraph_locators_are_not_treated_as_numbered_lists():
    input_md = "责任实体应承担GDPR第47(1)(b)及47(2)(f)条规定的责任。"
    result = normalize_legal_markdown_structure(input_md)
    assert "47(1)(b)" in result
    assert "47(2)(f)" in result
    assert "47(\n" not in result


def test_real_numbered_lists_still_work():
    """Legitimate numbered lists should still be split."""
    input_md = "安全措施包括：1. 数据加密 2. 访问控制 3. 审计日志"
    result = normalize_legal_markdown_structure(input_md)
    # Should split into separate lines
    assert "1. 数据加密" in result
    assert "2. 访问控制" in result
    assert "3. 审计日志" in result


def test_chinese_enumeration_顿号_still_works():
    """Chinese enumeration with 顿号 should still split."""
    input_md = "包括：一、数据分类二、风险评估三、安全措施"
    result = normalize_legal_markdown_structure(input_md)
    assert "一、" in result
    assert "二、" in result
    assert "三、" in result


def test_pipeless_table_repair():
    """P0-4: Pipe-less tables should be repaired with leading pipes."""
    input_md = """项目 | 内容
企业名称 | 测试公司
行业 | 互联网"""
    result = normalize_legal_markdown_structure(input_md)
    # Should add leading pipes and keep lines together
    assert "| 项目 | 内容" in result
    assert "| 企业名称 | 测试公司" in result
    assert "| 行业 | 互联网" in result
    # Lines should be consecutive (single \n separator, not \n\n)
    assert "| 项目 | 内容\n| 企业名称" in result
    assert "| 企业名称 | 测试公司\n| 行业" in result
