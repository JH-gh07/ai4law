from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from time import perf_counter
from typing import Callable, Literal

from pydantic import BaseModel, Field

from backend.common.knowledge.v2 import (
    KnowledgeChunkV2,
    ModuleKey,
    RetrievalBundle,
    RetrievalRequest,
    TaskStage,
)
from backend.common.rag.constants import MULTI_INDEX_SCHEMA_VERSION
from backend.common.rag.orchestrator import RetrievalOrchestrator
from backend.common.rag.retriever import (
    RegulationDoc,
    RegulationRAGService,
    retrieve_regulations,
)
from backend.core.settings import get_settings

RetrievalBackend = Literal[
    "multi_index",
    "single_index",
    "enriched_compatibility",
]
Retriever = Callable[..., list[RegulationDoc]]


@lru_cache(maxsize=1)
def _single_index_service() -> RegulationRAGService:
    return RegulationRAGService(get_settings())


def _retrieve_with_single_index(
    query: str,
    **kwargs: object,
) -> list[RegulationDoc]:
    return _single_index_service().retrieve(query, **kwargs)


class RetrievalManifest(BaseModel):
    backend: RetrievalBackend
    module: str
    task_stage: str
    query: str
    jurisdiction: str
    path: str
    top_k: int
    hit_count: int
    fallback_reason: str = ""
    index_schema_version: str = ""
    duration_ms: int = Field(ge=0)


class LegalRetrievalResult(BaseModel):
    bundle: RetrievalBundle
    manifest: RetrievalManifest


@dataclass(frozen=True)
class LegalDocumentRetrievalResult:
    documents: list[RegulationDoc]
    manifest: RetrievalManifest


class LegalRetrievalService:
    """Stable retrieval boundary for business modules and benchmark adapters."""

    def __init__(
        self,
        orchestrator: RetrievalOrchestrator | None = None,
        single_index_retriever: Retriever = _retrieve_with_single_index,
        enriched_compatibility_retriever: Retriever = retrieve_regulations,
    ) -> None:
        self.orchestrator = orchestrator or RetrievalOrchestrator()
        self.single_index_retriever = single_index_retriever
        self.enriched_compatibility_retriever = enriched_compatibility_retriever

    def retrieve(
        self,
        request: RetrievalRequest,
        *,
        backend: RetrievalBackend = "multi_index",
        retriever_options: dict[str, object] | None = None,
    ) -> LegalRetrievalResult:
        started = perf_counter()

        if backend == "multi_index":
            bundle = self.orchestrator.retrieve(request)
        else:
            retriever = (
                self.single_index_retriever
                if backend == "single_index"
                else self.enriched_compatibility_retriever
            )
            options: dict[str, object] = {
                "top_k": request.top_k,
                "jurisdiction": request.jurisdiction,
                "path": request.path,
            }
            if request.document_type != "other":
                options["doc_type"] = request.document_type
            options.update(retriever_options or {})
            if backend == "single_index":
                options.pop("legal_service", None)
                options.pop("min_local", None)
            docs = retriever(request.query, **options)
            bundle = RetrievalBundle(
                legal_grounding=[
                    self._regulation_doc_to_chunk(
                        doc,
                        module=request.module,
                        adapter_source=backend,
                    )
                    for doc in docs
                ]
            )

        hit_count = sum(
            len(items)
            for items in (
                bundle.legal_grounding,
                bundle.workflow_rules,
                bundle.standard_clauses,
                bundle.templates,
                bundle.testcases,
            )
        )
        duration_ms = max(0, round((perf_counter() - started) * 1000))
        manifest = RetrievalManifest(
            backend=backend,
            module=request.module,
            task_stage=request.task_stage,
            query=request.query,
            jurisdiction=request.jurisdiction,
            path=request.path,
            top_k=request.top_k,
            hit_count=hit_count,
            index_schema_version=(
                MULTI_INDEX_SCHEMA_VERSION
                if backend == "multi_index"
                else ""
            ),
            duration_ms=duration_ms,
        )
        return LegalRetrievalResult(bundle=bundle, manifest=manifest)

    def retrieve_with_fallback(
        self,
        request: RetrievalRequest,
        *,
        backend: RetrievalBackend = "multi_index",
        fallback_backend: RetrievalBackend | None = "single_index",
        retriever_options: dict[str, object] | None = None,
    ) -> LegalRetrievalResult:
        primary = self.retrieve(
            request,
            backend=backend,
            retriever_options=retriever_options,
        )
        if primary.bundle.legal_grounding or fallback_backend is None:
            return primary
        if fallback_backend == backend:
            return primary

        fallback = self.retrieve(
            request,
            backend=fallback_backend,
            retriever_options=retriever_options,
        )
        fallback.manifest.fallback_reason = (
            f"{backend}_returned_no_legal_grounding"
        )
        fallback.manifest.duration_ms += primary.manifest.duration_ms
        if (
            fallback.bundle.legal_grounding
            or fallback_backend == "enriched_compatibility"
        ):
            return fallback

        compatibility = self.retrieve(
            request,
            backend="enriched_compatibility",
            retriever_options=retriever_options,
        )
        compatibility.manifest.fallback_reason = (
            f"{backend}_and_{fallback_backend}"
            "_returned_no_legal_grounding"
        )
        compatibility.manifest.duration_ms += fallback.manifest.duration_ms
        return compatibility

    def retrieve_documents(
        self,
        request: RetrievalRequest,
        *,
        backend: RetrievalBackend = "multi_index",
        fallback_backend: RetrievalBackend | None = "single_index",
        retriever_options: dict[str, object] | None = None,
    ) -> LegalDocumentRetrievalResult:
        result = self.retrieve_with_fallback(
            request,
            backend=backend,
            fallback_backend=fallback_backend,
            retriever_options=retriever_options,
        )
        documents = [
            self._chunk_to_regulation_doc(chunk)
            for chunk in result.bundle.legal_grounding
        ]
        return LegalDocumentRetrievalResult(
            documents=documents,
            manifest=result.manifest,
        )

    @staticmethod
    def _regulation_doc_to_chunk(
        doc: RegulationDoc,
        *,
        module: str,
        adapter_source: RetrievalBackend,
    ) -> KnowledgeChunkV2:
        return KnowledgeChunkV2(
            chunk_id=f"{adapter_source}:{doc.id}",
            source_id=doc.id or f"{adapter_source}:{doc.title}",
            title=doc.title,
            content=doc.content,
            layer="L1_regulatory_evidence",
            source_kind="regulation",
            module=module,
            jurisdiction=doc.jurisdiction or "cn",
            doc_type=doc.doc_type,
            authority_level="medium",
            binding_force="unknown",
            allowed_usage=["legal_grounding"],
            can_be_cited=True,
            citation_anchor=doc.article,
            article_no=doc.article,
            path=doc.path or "all",
            source_url=doc.source_url,
            snapshot_path=doc.snapshot_path,
            keywords=list(doc.keywords),
            structured_payload={"adapter_source": adapter_source},
        )

    @staticmethod
    def _chunk_to_regulation_doc(
        chunk: KnowledgeChunkV2,
    ) -> RegulationDoc:
        return RegulationDoc(
            id=chunk.source_id or chunk.chunk_id,
            title=chunk.title,
            article=chunk.citation_anchor or chunk.article_no,
            content=chunk.content,
            jurisdiction=chunk.jurisdiction,
            path=chunk.path,
            doc_type=chunk.doc_type,
            source_url=chunk.source_url,
            snapshot_path=chunk.snapshot_path,
            keywords=tuple(chunk.keywords),
        )


@lru_cache(maxsize=1)
def get_legal_retrieval_service() -> LegalRetrievalService:
    return LegalRetrievalService()

def retrieve_legal_documents(
    query: str,
    *,
    module: ModuleKey,
    task_stage: TaskStage = "legal_grounding",
    top_k: int = 8,
    jurisdiction: str = "cn",
    path: str = "all",
    facts: dict[str, object] | None = None,
    document_type: str = "other",
    retriever_options: dict[str, object] | None = None,
) -> LegalDocumentRetrievalResult:
    request = RetrievalRequest(
        module=module,
        task_stage=task_stage,
        query=query,
        facts=facts or {},
        document_type=document_type,
        top_k=top_k,
        jurisdiction=jurisdiction,
        path=path,
    )
    return get_legal_retrieval_service().retrieve_documents(
        request,
        retriever_options=retriever_options,
    )
