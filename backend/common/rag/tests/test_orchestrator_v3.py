from backend.common.rag.orchestrator import RetrievalOrchestrator
from backend.common.knowledge.v2 import RetrievalRequest
from backend.common.knowledge.v2 import KnowledgeChunkV2


def test_cn_assessment_routes_to_workflow_and_templates() -> None:
    orchestrator = RetrievalOrchestrator()
    legal_bundle = orchestrator.retrieve(
        RetrievalRequest(
            module="cn_assessment",
            task_stage="legal_grounding",
            query="安全评估 申报材料 接收方 安全能力",
            top_k=5,
            path="assessment",
        )
    )
    assert legal_bundle.workflow_rules
    assert legal_bundle.legal_grounding

    template_bundle = orchestrator.retrieve(
        RetrievalRequest(
            module="cn_assessment",
            task_stage="report_generation",
            query="安全评估 模板 章节",
            top_k=5,
            path="assessment",
        )
    )
    assert template_bundle.templates
    assert all(item.template_type == "official_template" for item in template_bundle.templates)


def test_cn_review_clause_compare_prefers_standard_clause_index() -> None:
    orchestrator = RetrievalOrchestrator()
    bundle = orchestrator.retrieve(
        RetrievalRequest(
            module="cn_review",
            task_stage="clause_compare",
            query="主服务协议不一致的以主服务协议为准 赔偿责任总额不超过",
            document_type="scc_contract",
            top_k=5,
            path="review",
        )
    )
    assert bundle.standard_clauses
    assert all(item.source_kind == "standard_clause" for item in bundle.standard_clauses)


def test_dedupe_by_source_keeps_first_chunk_per_source() -> None:
    orchestrator = RetrievalOrchestrator()
    chunks = [
        KnowledgeChunkV2(
            chunk_id="A-1",
            source_id="SRC-A",
            title="A1",
            content="",
            layer="L1_regulatory_evidence",
            source_kind="law_article",
            module="cn_assessment",
            allowed_usage=["legal_grounding"],
        ),
        KnowledgeChunkV2(
            chunk_id="A-2",
            source_id="SRC-A",
            title="A2",
            content="",
            layer="L1_regulatory_evidence",
            source_kind="law_article",
            module="cn_assessment",
            allowed_usage=["legal_grounding"],
        ),
        KnowledgeChunkV2(
            chunk_id="B-1",
            source_id="SRC-B",
            title="B1",
            content="",
            layer="L1_regulatory_evidence",
            source_kind="law_article",
            module="cn_assessment",
            allowed_usage=["legal_grounding"],
        ),
    ]
    deduped = orchestrator.dedupe_by_source(chunks)
    assert [item.chunk_id for item in deduped] == ["A-1", "B-1"]
