from __future__ import annotations

from backend.harness.validators import (
    ASSERTION_OPERATORS,
    resolve_path,
    unknown_operators,
    validate_expected,
)


def test_resolve_path_reads_scalars_nested_values_and_projections() -> None:
    data = {
        "risk_level": "HIGH",
        "need_assessment": {"dpia_required": True},
        "chapters": [{"title": "第一章"}, {"title": "第二章"}, {}],
    }

    assert resolve_path(data, "risk_level") == "HIGH"
    assert resolve_path(data, "need_assessment.dpia_required") is True
    assert resolve_path(data, "chapters[].title") == ["第一章", "第二章"]
    assert resolve_path(data, "chapters") == data["chapters"]


def test_unknown_operator_fails_instead_of_being_ignored() -> None:
    outcome = validate_expected({"risk_level": "HIGH"}, {"citation_count": 3}, no_llm=True)

    assert not outcome.ok
    assert any("unknown assertion operator" in message for message in outcome.failed)


def test_absent_path_fails_rather_than_skipping() -> None:
    outcome = validate_expected(
        {"risk_level": "HIGH"},
        {"fields_equal": {"overall_traffic_light": "GREEN"}},
        no_llm=True,
    )

    assert not outcome.ok
    assert any("path absent from result" in message for message in outcome.failed)


def test_fields_equal_compares_nested_values() -> None:
    actual = {"need_assessment": {"dpia_required": True}, "rating": "部分缺失"}

    outcome = validate_expected(
        actual,
        {"fields_equal": {"need_assessment.dpia_required": True, "rating": "部分缺失"}},
        no_llm=True,
    )

    assert outcome.ok
    assert len(outcome.passed) == 2


def test_min_counts_accepts_lists_and_precomputed_counts() -> None:
    actual = {"legal_basis": ["a", "b", "c"], "chapters_count": 8}

    outcome = validate_expected(
        actual,
        {"min_counts": {"legal_basis": 2, "chapters_count": 8}},
        no_llm=True,
    )

    assert outcome.ok


def test_min_counts_rejects_shortfall_and_uncountable_values() -> None:
    outcome = validate_expected(
        {"legal_basis": ["a"], "risk_level": "HIGH"},
        {"min_counts": {"legal_basis": 3, "risk_level": 1}},
        no_llm=True,
    )

    assert len(outcome.failed) == 2
    assert any("expected >= 3, got 1" in message for message in outcome.failed)
    assert any("is not countable" in message for message in outcome.failed)


def test_max_counts_bounds_issue_lists() -> None:
    passing = validate_expected(
        {"consistency_issues": []}, {"max_counts": {"consistency_issues": 0}}, no_llm=True
    )
    failing = validate_expected(
        {"consistency_issues": ["a", "b"]},
        {"max_counts": {"consistency_issues": 1}},
        no_llm=True,
    )

    assert passing.ok
    assert not failing.ok
    assert any("expected <= 1, got 2" in message for message in failing.failed)


def test_list_contains_matches_substrings_over_projections() -> None:
    actual = {"chapters": [{"title": "第一章 出境概况"}, {"title": "第二章 风险"}]}

    outcome = validate_expected(
        actual, {"list_contains": {"chapters[].title": ["出境概况", "风险"]}}, no_llm=True
    )

    assert outcome.ok


def test_output_formats_reads_suffixes_from_output_files_values() -> None:
    actual = {
        "output_files": {
            "docx": "outputs/x/report.docx",
            "markdown": "outputs/x/report.md",
            "zip": "outputs/x/pack.zip",
        }
    }

    outcome = validate_expected(actual, {"output_formats": ["docx", "md"]}, no_llm=True)
    missing = validate_expected(actual, {"output_formats": ["pdf"]}, no_llm=True)

    assert outcome.ok
    assert not missing.ok


def test_output_roles_contains_reads_role_keys() -> None:
    actual = {"output_files": {"docx": "a.docx", "citation_map_json": "b.json"}}

    outcome = validate_expected(
        actual, {"output_roles_contains": ["docx", "citation_map_json"]}, no_llm=True
    )

    assert outcome.ok


def test_result_not_empty_accepts_any_populated_field() -> None:
    reporting_module = validate_expected(
        {"report_path": "outputs/x/report.md"}, {"result_not_empty": True}, no_llm=True
    )
    # diagnosis returns no report_path and no output_files, only a verdict.
    verdict_module = validate_expected(
        {"recommended_path": "exemption"}, {"result_not_empty": True}, no_llm=True
    )
    hollow = validate_expected(
        {"consistency_issues": [], "missing_facts": [], "report_path": ""},
        {"result_not_empty": True},
        no_llm=True,
    )

    assert reporting_module.ok
    assert verdict_module.ok
    assert not hollow.ok


def test_profile_contains_and_legal_basis_contains_are_sugar() -> None:
    actual = {
        "profile": {"company_name": "云帆数据科技有限公司", "is_ciio": False},
        "legal_basis": ["个人信息出境标准合同办法 第4条"],
    }

    outcome = validate_expected(
        actual,
        {
            "profile_contains": {"company_name": "云帆数据科技有限公司", "is_ciio": False},
            "legal_basis_contains": ["个人信息出境标准合同办法"],
        },
        no_llm=True,
    )

    assert outcome.ok
    assert len(outcome.passed) == 3


def test_llm_only_assertions_skip_offline_and_run_online() -> None:
    actual = {"chapters": [{"title": "生成章节"}]}
    expectation = {"list_contains": {"chapters[].title": ["生成章节"]}}

    offline = validate_expected(actual, {}, no_llm=True, expected_llm_only=expectation)
    online = validate_expected(actual, {}, no_llm=False, expected_llm_only=expectation)

    assert offline.ok
    assert offline.skipped == ["list_contains: skipped (no_llm mode)"]
    assert online.ok
    assert not online.skipped
    assert online.passed


def test_rule_derived_expectations_are_asserted_even_offline() -> None:
    outcome = validate_expected(
        {"risk_level": "LOW", "conclusion_source": "rule"},
        {"fields_equal": {"risk_level": "HIGH", "conclusion_source": "rule"}},
        no_llm=True,
    )

    assert not outcome.ok
    assert any("expected 'HIGH', got 'LOW'" in message for message in outcome.failed)


def test_list_excludes_rejects_placeholder_prose() -> None:
    passing = validate_expected(
        {"chapters": [{"content": "完整正文"}]},
        {"list_excludes": {"chapters[].content": ["占位内容"]}},
        no_llm=True,
    )
    failing = validate_expected(
        {"chapters": [{"content": "LLM未配置，此处为占位内容"}]},
        {"list_excludes": {"chapters[].content": ["占位内容"]}},
        no_llm=True,
    )

    assert passing.ok
    assert not failing.ok


def test_malformed_expectation_is_reported_not_raised() -> None:
    outcome = validate_expected({}, {"min_counts": ["legal_basis"]}, no_llm=True)

    assert not outcome.ok
    assert any("malformed expectation" in message for message in outcome.failed)


def test_unknown_operators_helper_lists_only_unsupported_keys() -> None:
    assert unknown_operators({"fields_equal": {}, "bogus": 1}) == ["bogus"]
    assert unknown_operators({key: None for key in ASSERTION_OPERATORS}) == []
