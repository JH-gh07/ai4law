from pathlib import Path

import pytest

from backend.core.resource_paths import (
    KNOWLEDGE_ROOT,
    PROJECT_ROOT,
    REPORT_TEMPLATE_ROOT,
    PRODUCT_SMOKE_BENCHMARK_ROOT,
    RAG_RETRIEVAL_BENCHMARK_ROOT,
    report_template_path,
)


def test_resource_roots_are_absolute_and_inside_project() -> None:
    assert PROJECT_ROOT.is_absolute()
    assert KNOWLEDGE_ROOT.is_relative_to(PROJECT_ROOT)
    assert REPORT_TEMPLATE_ROOT.is_relative_to(PROJECT_ROOT)
    assert PRODUCT_SMOKE_BENCHMARK_ROOT.is_relative_to(PROJECT_ROOT)
    assert RAG_RETRIEVAL_BENCHMARK_ROOT.is_relative_to(PROJECT_ROOT)
    assert KNOWLEDGE_ROOT.is_dir()
    assert REPORT_TEMPLATE_ROOT.is_dir()
    assert PRODUCT_SMOKE_BENCHMARK_ROOT.is_dir()
    assert RAG_RETRIEVAL_BENCHMARK_ROOT.is_dir()


@pytest.mark.parametrize(
    "jurisdiction,file_name",
    [
        ("cn", "2.2_risk_assessment_template_v0.docx"),
        ("cn", "2.2_risk_assessment_template_v0.md"),
        ("cn", "3.1_scc_review_template_v0.docx"),
        ("cn", "3.1_scc_review_template_v0.md"),
        ("eu", "3.2_bcr_review_template_v0.docx"),
        ("eu", "3.2_bcr_review_template_v0.md"),
        ("eu", "3.4_tia_template_v0.docx"),
        ("eu", "3.4_tia_template_v0.md"),
        ("us", "4.1_cn_flow_compliance_template_v0.docx"),
        ("us", "4.1_cn_flow_compliance_template_v0.md"),
        ("us", "4.2_cpra_panorama_template_v0.docx"),
        ("us", "4.2_cpra_panorama_template_v0.md"),
        ("us", "4.2_us_14117_compliance_template_v0.md"),
    ],
)
def test_active_report_template_exists(jurisdiction: str, file_name: str) -> None:
    assert report_template_path(jurisdiction, file_name).is_file()


def test_report_template_rejects_directory_traversal() -> None:
    with pytest.raises(ValueError, match="must not contain directory segments"):
        report_template_path("cn", "../template.docx")


def test_active_backend_has_no_direct_legacy_or_research_resource_paths() -> None:
    forbidden_literals = (
        "doc/knowledge",
        "doc/v2/assets/templates",
        "resources/research",
    )
    offenders: list[str] = []
    for path in (PROJECT_ROOT / "backend").rglob("*.py"):
        if "tests" in path.parts:
            continue
        source = path.read_text(encoding="utf-8")
        if any(literal in source for literal in forbidden_literals):
            offenders.append(str(path.relative_to(PROJECT_ROOT)))
    assert offenders == []