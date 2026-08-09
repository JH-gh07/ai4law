import json

from backend.common.rag.orchestrator import RetrievalOrchestrator
from backend.common.knowledge.v2 import RetrievalRequest
from backend.common.knowledge.v2 import KnowledgeChunkV2
from backend.core.settings import Settings


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


def test_eu_module_returns_scaffold_debug_bundle() -> None:
    orchestrator = RetrievalOrchestrator()
    bundle = orchestrator.retrieve(
        RetrievalRequest(
            module="eu_scc",
            task_stage="clause_compare",
            query="onward transfer equivalent safeguards",
            path="review",
            jurisdiction="eu",
        )
    )
    assert bundle.standard_clauses
    assert bundle.debug["jurisdiction"] == "eu"
    assert any(item.module == "eu_scc" for item in bundle.standard_clauses)


def test_eu_tia_retrieves_current_gdpr_article_46() -> None:
    orchestrator = RetrievalOrchestrator()
    bundle = orchestrator.retrieve(
        RetrievalRequest(
            module="eu_tia",
            task_stage="legal_grounding",
            query="GDPR Article 46 appropriate safeguards SCC international transfer",
            path="all",
            jurisdiction="eu",
            top_k=8,
        )
    )

    assert any(
        chunk.source_id == "EU-LAW-001"
        and chunk.article_no == "46"
        and "appropriate safeguards" in chunk.content
        for chunk in bundle.legal_grounding
    )
    assert any(
        chunk.source_id == "EU-GUIDE-002"
        and chunk.article_no == "Step 3"
        and "transfer tool" in chunk.content
        for chunk in bundle.legal_grounding
    )


def test_us_module_returns_scaffold_debug_bundle() -> None:
    orchestrator = RetrievalOrchestrator()
    bundle = orchestrator.retrieve(
        RetrievalRequest(
            module="us_eo14117",
            task_stage="issue_discovery",
            query="restricted transaction vendor agreement data brokerage",
            path="review",
            jurisdiction="us",
        )
    )
    assert bundle.workflow_rules
    assert bundle.debug["jurisdiction"] == "us"
    assert any(item.module == "us_eo14117" for item in bundle.workflow_rules)


def test_orchestrator_rebuilds_generated_indexes_in_empty_storage(tmp_path) -> None:
    settings = Settings(rag_v3_dir=tmp_path / "rag" / "v3")
    orchestrator = RetrievalOrchestrator(settings)

    bundle = orchestrator.retrieve(
        RetrievalRequest(
            module="cn_diagnosis",
            task_stage="legal_grounding",
            query="关键信息基础设施运营者 重要数据 个人信息数量",
            path="diagnosis",
            top_k=3,
        )
    )

    assert bundle.legal_grounding
    assert (tmp_path / "rag" / "v3" / "legal_index_cn.jsonl").exists()
    vector_path = tmp_path / "rag" / "v3" / "legal_index_cn.vector.json"
    metadata = json.loads(vector_path.read_text(encoding="utf-8"))["metadata"]
    assert metadata["embedding_version"] == "sha256-v1"


def test_orchestrator_rejects_index_without_current_embedding_version(tmp_path) -> None:
    settings = Settings(rag_v3_dir=tmp_path / "rag" / "v3")
    orchestrator = RetrievalOrchestrator(settings)
    index_path = settings.rag_v3_dir / "legal_index_cn.vector.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps(
            {
                "metadata": {
                    "schema_version": "v3.2",
                    "embedding_dimension": orchestrator.embedder.dimension,
                },
                "entries": [],
            }
        ),
        encoding="utf-8",
    )

    assert orchestrator._is_index_current("legal_index_cn") is False


def test_orchestrator_rejects_legal_index_with_stale_source_fingerprint(tmp_path) -> None:
    settings = Settings(rag_v3_dir=tmp_path / "rag" / "v3")
    orchestrator = RetrievalOrchestrator(settings)
    index_path = settings.rag_v3_dir / "legal_index_eu.vector.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps(
            {
                "metadata": {
                    "schema_version": "v3.2",
                    "embedding_version": orchestrator.embedder.version,
                    "embedding_dimension": orchestrator.embedder.dimension,
                    "source_fingerprint": "stale",
                },
                "entries": [],
            }
        ),
        encoding="utf-8",
    )

    assert orchestrator._is_index_current("legal_index_eu") is False
