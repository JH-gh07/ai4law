import json
from pathlib import Path

from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry
from backend.domains.cn.security_assessment.report_renderer import (
    _write_citation_map_json as write_assessment_citation_map,
)
from backend.domains.eu.dpia.report_renderer import (
    _write_citation_map_json as write_dpia_citation_map,
)
from backend.domains.eu.scc_review.service import _eu_scc_ref_from_item
from backend.domains.eu.tia.service import _tia_ref_from_item
from backend.domains.us.cpra import service as cpra_service


def _citation_item() -> CitationItem:
    return CitationItem(
        citation_id="CIT-CN-PIPL-ART66-P01",
        source_id="CN-LAW-003",
        title="个人信息保护法",
        article_no="六十六",
    )


def _citation_registry() -> CitationRegistry:
    registry = CitationRegistry()
    item = _citation_item()
    registry.register(item)
    registry.assign_footnote_number(item.citation_id)
    return registry


def _assert_normalized_map(path: str | Path, module: str) -> None:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    footnote = payload["footnote_map"]["1"]
    assert payload["module"] == module
    assert footnote["article_no"] == "66"
    assert footnote["knowledge_url"] == "/evidence?source=CN-LAW-003&article=66"
    assert footnote["can_jump"] is True


def test_assessment_writer_uses_common_citation_normalization(tmp_path: Path) -> None:
    path = write_assessment_citation_map(_citation_registry(), tmp_path)
    _assert_normalized_map(path, "assessment")


def test_dpia_writer_uses_common_citation_normalization(tmp_path: Path) -> None:
    path = write_dpia_citation_map(_citation_registry(), tmp_path)
    _assert_normalized_map(path, "dpia")


def test_cpra_refs_have_knowledge_url() -> None:
    ref = cpra_service._cpra_ref_from_item(_citation_item())
    assert ref.knowledge_url == "/evidence?source=CN-LAW-003&article=66"


def test_tia_refs_have_knowledge_url() -> None:
    ref = _tia_ref_from_item(_citation_item())
    assert ref.knowledge_url == "/evidence?source=CN-LAW-003&article=66"


def test_eu_scc_refs_have_knowledge_url() -> None:
    ref = _eu_scc_ref_from_item(_citation_item())
    assert ref.knowledge_url == "/evidence?source=CN-LAW-003&article=66"
