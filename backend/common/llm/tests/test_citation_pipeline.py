from __future__ import annotations

import pytest

from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry
from backend.common.llm.postprocess import (
    CitationPipelineError,
    apply_citation_pipeline,
)


def _registry() -> CitationRegistry:
    registry = CitationRegistry()
    registry.register(
        CitationItem(
            citation_id="CIT-CN-PIPL-ART39-P01",
            source_id="CN-LAW-003",
            title="个人信息保护法",
            article_no="39",
        )
    )
    return registry


def _us_registry() -> CitationRegistry:
    registry = CitationRegistry()
    registry.register(
        CitationItem(
            citation_id="CIT-US-US_FED_001-ART202_303-P01",
            source_id="US-FED-001",
            title="28 CFR Part 202 - EO 14117 implementing rule",
            article_no="202.303",
        )
    )
    return registry


def test_pipeline_converts_marker_and_runs_claim_gate_once() -> None:
    result = apply_citation_pipeline(
        "依据《个人信息保护法》第三十九条，企业应当完成评估。{{CIT-CN-PIPL-ART39-P01}}",
        registry=_registry(),
        allowed_citations=["个人信息保护法第39条"],
    )

    assert "[1]" in result.text
    assert "{{CIT-" not in result.text
    assert "【依据：" not in result.text
    assert "【待核验：缺少法规依据】" not in result.text
    assert result.violations == []


def test_pipeline_preserves_underscores_inside_registered_marker() -> None:
    registry = CitationRegistry()
    citation_id = "CIT-CN-CN_LAW_003-ART39-P01"
    registry.register(
        CitationItem(
            citation_id=citation_id,
            source_id="CN-LAW-003",
            title="个人信息保护法",
            article_no="39",
        )
    )

    result = apply_citation_pipeline(
        f"企业应当取得单独同意。{{{{{citation_id}}}}}",
        registry=registry,
        allowed_citations=["个人信息保护法第39条"],
    )

    assert result.text == "企业应当取得单独同意。[1]"
    assert registry.get_footnote_map()[1].citation_id == citation_id


def test_pipeline_resolves_legacy_basis_text_to_the_same_registry_number() -> None:
    result = apply_citation_pipeline(
        "企业应当完成评估。【依据：个人信息保护法 第39条】",
        registry=_registry(),
    )

    assert result.text == "企业应当完成评估。[1]"
    assert "【依据：" not in result.text
    assert result.violations == []


def test_pipeline_resolves_us_cfr_decimal_section_basis() -> None:
    result = apply_citation_pipeline(
        "该交易属于禁止的人类组学数据交易。【依据：28 CFR § 202.303】",
        registry=_us_registry(),
    )

    assert result.text == "该交易属于禁止的人类组学数据交易。[1]"
    assert result.violations == []


def test_pipeline_does_not_leave_unregistered_marker_or_basis_text() -> None:
    result = apply_citation_pipeline(
        "企业应当完成评估。{{CIT-CN-PIPL-ART99-P01}}【依据：虚构法律 第1条】",
        registry=_registry(),
    )

    assert "{{CIT-" not in result.text
    assert "CIT-CN-PIPL-ART99-P01" not in result.text
    assert "【依据：" not in result.text
    assert "【待核验：引用无法映射】" in result.text
    assert "【待核验：缺少法规依据】" not in result.text
    assert any(item.code == "required_citation_missing" for item in result.violations)


def test_pipeline_requires_registry_when_citation_syntax_is_present() -> None:
    with pytest.raises(CitationPipelineError, match="CitationRegistry"):
        apply_citation_pipeline(
            "企业应当完成评估。{{CIT-CN-PIPL-ART39-P01}}",
            registry=None,
        )


def test_pipeline_replaces_truncated_citation_marker_with_pending_status() -> None:
    result = apply_citation_pipeline(
        "企业应当完成评估。{{CIT-CN-PIPL-ART39",
        registry=_registry(),
    )

    assert "CIT-CN-PIPL-ART39" not in result.text
    assert result.text == "企业应当完成评估。【待核验：引用格式不完整】"
    assert [item.code for item in result.violations] == ["required_citation_missing"]
