from backend.schemas.review import ClausePosition, ClauseType, ClassifiedClause
from backend.domains.cn.document_review.standard_clause import StandardClauseDiffer, StandardClauseLocator
from backend.common.knowledge.v2 import KnowledgeChunkV2


def _candidate() -> KnowledgeChunkV2:
    return KnowledgeChunkV2(
        chunk_id="STD-001",
        source_id="STD-001",
        title="标准合同优先性保护",
        content="不得约定其他协议优先于标准合同，不得通过责任上限削弱保护义务。",
        layer="L1_regulatory_evidence",
        template_type="none",
        source_kind="standard_clause",
        module="cn_review",
        allowed_usage=["legal_grounding", "internal_review", "external_report"],
        can_be_cited=True,
        can_enter_external_report=True,
        chunk_strategy="standard_clause",
        structured_payload={
            "clause_type": "CROSS_BORDER_TRANSFER",
            "protected_obligations": [
                "standard_contract_priority",
                "no_conflicting_master_agreement",
                "no_excessive_liability_cap",
            ],
        },
    )


def test_standard_clause_locator_matches_clause_type() -> None:
    locator = StandardClauseLocator()
    clause = ClassifiedClause(
        clause_id="c1",
        file_id="f1",
        text="如本协议与主服务协议不一致，以主服务协议为准。",
        clause_type=ClauseType.CROSS_BORDER_TRANSFER,
        position=ClausePosition(),
    )
    matched = locator.locate(clause, [_candidate()])
    assert matched is not None
    assert matched.chunk_id == "STD-001"


def test_standard_clause_differ_detects_missing_weakened_and_risky_changes() -> None:
    differ = StandardClauseDiffer()
    clause = ClassifiedClause(
        clause_id="c1",
        file_id="f1",
        text="如本协议与主服务协议不一致，以主服务协议为准。乙方赔偿责任总额不超过年度服务费二倍。",
        clause_type=ClauseType.CROSS_BORDER_TRANSFER,
        position=ClausePosition(),
    )
    diff = differ.diff(clause, _candidate())
    assert "standard_contract_priority" in diff.missing_obligations or "no_conflicting_master_agreement" in diff.weakened_obligations
    assert "no_excessive_liability_cap" in diff.weakened_obligations
    assert any("主服务协议为准" in item or "责任总额不超过" in item for item in diff.added_risky_modifications)
