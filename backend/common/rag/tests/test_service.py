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
    assert result.manifest.backend == "orchestrator_v3"
    assert result.manifest.hit_count == 1
    assert result.manifest.query == "cross-border transfer"
    assert result.manifest.index_schema_version


def test_legacy_v2_dispatch_is_distinct_from_compatibility_api() -> None:
    calls: list[str] = []

    def v2_retriever(query: str, **kwargs: object) -> list[RegulationDoc]:
        calls.append("legacy_v2")
        return [_doc()]

    def compatibility_retriever(
        query: str,
        **kwargs: object,
    ) -> list[RegulationDoc]:
        calls.append("compatibility_api")
        return [_doc()]

    service = LegalRetrievalService(
        legacy_v2_retriever=v2_retriever,
        compatibility_retriever=compatibility_retriever,
    )

    v2_result = service.retrieve(_request(), backend="legacy_v2")
    compatibility_result = service.retrieve(
        _request(),
        backend="compatibility_api",
    )

    assert calls == ["legacy_v2", "compatibility_api"]
    assert v2_result.manifest.backend == "legacy_v2"
    assert compatibility_result.manifest.backend == "compatibility_api"
    assert v2_result.manifest.fallback_reason == ""
    assert compatibility_result.manifest.fallback_reason == ""
    assert (
        v2_result.bundle.legal_grounding[0].structured_payload["adapter_source"]
        == "legacy_v2"
    )
    assert (
        compatibility_result.bundle.legal_grounding[0]
        .structured_payload["adapter_source"]
        == "compatibility_api"
    )


def test_document_retrieval_records_real_fallback() -> None:
    class EmptyOrchestrator:
        def retrieve(self, request: RetrievalRequest) -> RetrievalBundle:
            return RetrievalBundle()

    def legacy_v2_retriever(
        query: str,
        **kwargs: object,
    ) -> list[RegulationDoc]:
        return [_doc()]

    service = LegalRetrievalService(
        orchestrator=EmptyOrchestrator(),
        legacy_v2_retriever=legacy_v2_retriever,
    )
    result = service.retrieve_documents(_request())

    assert result.documents[0].id == "law-40"
    assert result.manifest.backend == "legacy_v2"
    assert (
        result.manifest.fallback_reason
        == "orchestrator_v3_returned_no_legal_grounding"
    )


def test_document_retrieval_uses_compatibility_after_empty_v2() -> None:
    class EmptyOrchestrator:
        def retrieve(self, request: RetrievalRequest) -> RetrievalBundle:
            return RetrievalBundle()

    def empty_v2(
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
        legacy_v2_retriever=empty_v2,
        compatibility_retriever=compatibility,
    )
    result = service.retrieve_documents(_request())

    assert result.documents[0].id == "law-40"
    assert result.manifest.backend == "compatibility_api"
    assert (
        result.manifest.fallback_reason
        == (
            "orchestrator_v3_and_legacy_v2"
            "_returned_no_legal_grounding"
        )
    )
