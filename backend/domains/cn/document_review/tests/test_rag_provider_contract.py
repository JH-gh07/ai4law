from backend.schemas.review import ClauseType
from backend.domains.cn.document_review.rag_provider import LocalRegulationKnowledgeBase


def test_lookup_returns_old_and_new_fields_together() -> None:
    kb = LocalRegulationKnowledgeBase()
    result = kb.lookup(
        ClauseType.CROSS_BORDER_TRANSFER,
        "如本协议与主服务协议不一致，以主服务协议为准。乙方赔偿责任总额不超过年度服务费二倍。",
        enrich=True,
    )
    assert "citations" in result
    assert "structured_citations" in result
    assert "workflow_rules" in result
    assert "standard_clause_candidates" in result
    assert "usage_policy_debug" in result
    assert isinstance(result["citations"], list)


def test_lookup_tracks_resolved_jurisdiction_and_module() -> None:
    kb = LocalRegulationKnowledgeBase()
    result = kb.lookup(
        ClauseType.RIGHTS_REQUEST,
        "The privacy notice explains access and deletion rights but omits any consumer right to limit the use of sensitive personal information.",
        enrich=True,
        document_type="privacy_policy",
    )
    assert result["usage_policy_debug"]["jurisdiction"] == "us"
    assert result["usage_policy_debug"]["module"] == "us_cpra"
