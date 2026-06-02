from backend.common.knowledge.usage_policy import UsagePolicyFilter
from backend.common.knowledge.v2 import KnowledgeChunkV2


def _chunk(
    *,
    chunk_id: str,
    layer: str,
    template_type: str = "none",
    source_kind: str = "law_article",
    can_be_cited: bool = True,
    can_enter_external_report: bool = True,
    allowed_usage: list[str] | None = None,
) -> KnowledgeChunkV2:
    return KnowledgeChunkV2(
        chunk_id=chunk_id,
        source_id=chunk_id,
        title=chunk_id,
        content="content",
        layer=layer,
        template_type=template_type,
        source_kind=source_kind,
        module="cn_assessment",
        allowed_usage=allowed_usage or ["legal_grounding", "external_report", "internal_review"],
        can_be_cited=can_be_cited,
        can_enter_external_report=can_enter_external_report,
        chunk_strategy="test",
    )


def test_usage_policy_blocks_non_l1_from_external_report() -> None:
    chunks = [
        _chunk(chunk_id="l1", layer="L1_regulatory_evidence"),
        _chunk(chunk_id="l2", layer="L2_business_rule", can_be_cited=False, can_enter_external_report=False),
        _chunk(chunk_id="l3", layer="L3_testcase", can_be_cited=False, can_enter_external_report=False),
        _chunk(chunk_id="l4", layer="L4_template", can_be_cited=False, can_enter_external_report=False),
    ]
    scoped = UsagePolicyFilter.filter(chunks, usage="external_report", environment="production")
    assert [item.chunk_id for item in scoped.chunks] == ["l1"]
    assert set(scoped.rejected_chunk_ids) == {"l2", "l3", "l4"}


def test_usage_policy_blocks_l3_in_production() -> None:
    testcase = _chunk(
        chunk_id="tc",
        layer="L3_testcase",
        source_kind="testcase",
        allowed_usage=["evaluator", "few_shot"],
        can_be_cited=False,
        can_enter_external_report=False,
    )
    scoped = UsagePolicyFilter.filter([testcase], usage="internal_review", environment="production")
    assert scoped.chunks == []
    assert scoped.rejected_chunk_ids == ["tc"]


def test_usage_policy_distinguishes_official_and_example_templates() -> None:
    official = _chunk(
        chunk_id="tpl-official",
        layer="L4_template",
        template_type="official_template",
        source_kind="template_slot",
        allowed_usage=["structure_control"],
        can_be_cited=False,
        can_enter_external_report=False,
    )
    example = _chunk(
        chunk_id="tpl-example",
        layer="L4_template",
        template_type="example",
        source_kind="template_slot",
        allowed_usage=["internal_drafting"],
        can_be_cited=False,
        can_enter_external_report=False,
    )
    scoped = UsagePolicyFilter.filter([official, example], usage="structure_control", environment="production")
    assert [item.chunk_id for item in scoped.chunks] == ["tpl-official"]
    assert scoped.rejected_chunk_ids == ["tpl-example"]
