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


def test_pipeline_resolves_legacy_basis_text_to_the_same_registry_number() -> None:
    result = apply_citation_pipeline(
        "企业应当完成评估。【依据：个人信息保护法 第39条】",
        registry=_registry(),
    )

    assert result.text == "企业应当完成评估。[1]"
    assert "【依据：" not in result.text
    assert result.violations == []


def test_pipeline_does_not_leave_unregistered_marker_or_basis_text() -> None:
    result = apply_citation_pipeline(
        "企业应当完成评估。{{CIT-CN-PIPL-ART99-P01}}【依据：虚构法律 第1条】",
        registry=_registry(),
    )

    assert "{{CIT-" not in result.text
    assert "【依据：" not in result.text
    assert "【待核验：缺少法规依据】" in result.text
    assert any(item.code == "required_citation_missing" for item in result.violations)


def test_pipeline_requires_registry_when_citation_syntax_is_present() -> None:
    with pytest.raises(CitationPipelineError, match="CitationRegistry"):
        apply_citation_pipeline(
            "企业应当完成评估。{{CIT-CN-PIPL-ART39-P01}}",
            registry=None,
        )
