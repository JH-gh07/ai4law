from backend.common.knowledge.v2 import (
    KnowledgeChunkV2,
    RetrievalBundle,
    RetrievalRequest,
)
from backend.common.rag.retriever import RegulationDoc
from backend.common.rag.service import LegalRetrievalService


def _request() -> RetrievalRequest:
    return RetrievalRequest(
        module="cn_diagnosis",
        task_stage="legal_grounding",
        query="cross-border transfer",
        top_k=3,
    )


def _doc() -> RegulationDoc:
    return RegulationDoc(
        id="law-40",
        title="PIPL",
        article="40",
        content="content",
        jurisdiction="cn",
        path="all",
        keywords=("transfer",),
    )


def test_orchestrator_result_includes_manifest() -> None:
    chunk = KnowledgeChunkV2(
        chunk_id="chunk-1",
        source_id="source-1",
        layer="L1_regulatory_evidence",
        source_kind="law_article",
    )

    class StubOrchestrator:
        def retrieve(self, request: RetrievalRequest) -> RetrievalBundle:
            return RetrievalBundle(legal_grounding=[chunk])

    service = LegalRetrievalService(orchestrator=StubOrchestrator())
    result = service.retrieve(_request())

    assert result.bundle.legal_grounding == [chunk]
    assert result.manifest.backend == "multi_index"
    assert result.manifest.hit_count == 1
    assert result.manifest.query == "cross-border transfer"
    assert result.manifest.index_schema_version


def test_single_index_dispatch_is_distinct_from_enriched_compatibility() -> None:
    calls: list[str] = []

    def single_index_retriever(query: str, **kwargs: object) -> list[RegulationDoc]:
        calls.append("single_index")
        return [_doc()]

    def enriched_compatibility_retriever(
        query: str,
        **kwargs: object,
    ) -> list[RegulationDoc]:
        calls.append("enriched_compatibility")
        return [_doc()]

    service = LegalRetrievalService(
        single_index_retriever=single_index_retriever,
        enriched_compatibility_retriever=enriched_compatibility_retriever,
    )

    single_index_result = service.retrieve(_request(), backend="single_index")
    compatibility_result = service.retrieve(
        _request(),
        backend="enriched_compatibility",
    )

    assert calls == ["single_index", "enriched_compatibility"]
    assert single_index_result.manifest.backend == "single_index"
    assert compatibility_result.manifest.backend == "enriched_compatibility"
    assert single_index_result.manifest.fallback_reason == ""
    assert compatibility_result.manifest.fallback_reason == ""
    assert (
        single_index_result.bundle.legal_grounding[0].structured_payload["adapter_source"]
        == "single_index"
    )
    assert (
        compatibility_result.bundle.legal_grounding[0]
        .structured_payload["adapter_source"]
        == "enriched_compatibility"
    )


def test_document_retrieval_records_real_fallback() -> None:
    class EmptyOrchestrator:
        def retrieve(self, request: RetrievalRequest) -> RetrievalBundle:
            return RetrievalBundle()

    def single_index_retriever(
        query: str,
        **kwargs: object,
    ) -> list[RegulationDoc]:
        return [_doc()]

    service = LegalRetrievalService(
        orchestrator=EmptyOrchestrator(),
        single_index_retriever=single_index_retriever,
    )
    result = service.retrieve_documents(_request())

    assert result.documents[0].id == "law-40"
    assert result.manifest.backend == "single_index"
    assert (
        result.manifest.fallback_reason
        == "multi_index_returned_no_legal_grounding"
    )


def test_document_retrieval_uses_compatibility_after_empty_single_index() -> None:
    class EmptyOrchestrator:
        def retrieve(self, request: RetrievalRequest) -> RetrievalBundle:
            return RetrievalBundle()

    def empty_single_index(
        query: str,
        **kwargs: object,
    ) -> list[RegulationDoc]:
        return []

    def compatibility(
        query: str,
        **kwargs: object,
    ) -> list[RegulationDoc]:
        return [_doc()]

    service = LegalRetrievalService(
        orchestrator=EmptyOrchestrator(),
        single_index_retriever=empty_single_index,
        enriched_compatibility_retriever=compatibility,
    )
    result = service.retrieve_documents(_request())

    assert result.documents[0].id == "law-40"
    assert result.manifest.backend == "enriched_compatibility"
    assert (
        result.manifest.fallback_reason
        == (
            "multi_index_and_single_index"
            "_returned_no_legal_grounding"
        )
    )
