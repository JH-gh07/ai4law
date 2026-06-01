"""Hybrid retriever combining vector, full-text, and metadata filtering.

Fusion strategy: RRF (Reciprocal Rank Fusion) with k=60, followed by
HeuristicReranker for final ordering.
"""

from __future__ import annotations

from typing import Optional

from backend.common.rag.embedding import HashingEmbedder
from backend.common.rag.fulltext_index import FulltextIndex
from backend.common.rag.reranker import HeuristicReranker, RerankCandidate
from backend.common.rag.retriever import (
    JURISDICTION_STRONG_HINTS,
    PATH_STRONG_HINTS,
    RegulationDoc,
    _is_jurisdiction_mismatch,
    _is_off_topic_query,
    _lexical_score,
    _normalize,
    _passes_filter,
    _rewrite_query,
)
from backend.common.rag.vector_store import LocalVectorStore
from backend.core.settings import Settings


def _rrf_fusion(
    vector_ranked: list[tuple[float, dict]],
    fts_ranked: list[tuple[float, dict]],
    k: int = 60,
) -> list[tuple[float, dict]]:
    """Merge two ranked lists using Reciprocal Rank Fusion."""
    scores: dict[str, float] = {}
    docs: dict[str, dict] = {}

    for rank, (score, doc) in enumerate(vector_ranked, start=1):
        doc_id = str(doc.get("id", ""))
        rrf = 1.0 / (k + rank)
        scores[doc_id] = scores.get(doc_id, 0.0) + rrf
        docs[doc_id] = doc

    for rank, (score, doc) in enumerate(fts_ranked, start=1):
        doc_id = str(doc.get("id", ""))
        rrf = 1.0 / (k + rank)
        scores[doc_id] = scores.get(doc_id, 0.0) + rrf
        docs[doc_id] = doc

    merged = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [(score, docs[doc_id]) for doc_id, score in merged]


class EnhancedHybridRetriever:
    """Combined vector + FTS5 + metadata filter hybrid retrieval."""

    def __init__(self, settings: Settings, db_session=None) -> None:
        self.settings = settings
        self.embedder = HashingEmbedder(settings.rag_embedding_dimension)
        self.vector_store = LocalVectorStore(settings.rag_index_path, self.embedder)
        self.reranker = HeuristicReranker()
        self.fts: FulltextIndex | None = FulltextIndex(db_session) if db_session else None

    def search(
        self,
        query: str,
        *,
        top_k: int = 8,
        jurisdiction: Optional[str] = None,
        path: Optional[str] = None,
        doc_type: Optional[str] = None,
        source: Optional[str] = None,
    ) -> list[RegulationDoc]:
        if _is_off_topic_query(query) or _is_jurisdiction_mismatch(query, jurisdiction):
            return []

        rewritten = _rewrite_query(query, jurisdiction, path)

        # Vector search
        entries = tuple(self.vector_store.load()) if self.vector_store.exists() else ()
        vector_hits = self.vector_store.search(
            rewritten,
            list(entries),
            top_k=max(top_k * 2, self.settings.rag_candidate_pool_size),
        )

        # FTS5 search
        fts_hits: list[tuple[float, dict]] = []
        if self.fts:
            fts_results = self.fts.search(rewritten, limit=top_k * 2)
            for hit in fts_results:
                payload = {
                    "id": hit.get("chunk_id", ""),
                    "title": hit.get("title", ""),
                    "article": hit.get("article_no", ""),
                    "content": hit.get("content", ""),
                    "jurisdiction": jurisdiction or "",
                    "path": path or "",
                    "doc_type": doc_type or "",
                }
                rank_score = float(hit.get("rank", 0))
                # Normalize FTS rank: lower rank (better) → higher score
                norm_score = 1.0 / (1.0 + abs(rank_score)) if rank_score else 0.1
                fts_hits.append((norm_score, payload))

        # RRF fusion
        merged = _rrf_fusion(vector_hits, fts_hits, k=60)

        # Filter and convert
        candidates: list[RerankCandidate] = []
        for rrf_score, payload in merged[: self.settings.rag_rerank_candidate_count]:
            doc = RegulationDoc(
                id=str(payload.get("id", "")),
                title=str(payload.get("title", "")),
                article=str(payload.get("article", "")),
                content=str(payload.get("content", "")),
                jurisdiction=str(payload.get("jurisdiction", "")),
                path=str(payload.get("path", "")),
                doc_type=str(payload.get("doc_type", "")),
            )
            if not _passes_filter(doc, jurisdiction=jurisdiction, path=path, doc_type=doc_type, source=source):
                continue
            lexical_score = _lexical_score(query, doc)
            candidates.append(
                RerankCandidate(
                    payload=payload,
                    vector_score=rrf_score,
                    lexical_score=lexical_score,
                    base_score=rrf_score * 0.7 + lexical_score * 0.3,
                )
            )

        if not candidates:
            return []

        reranked = self.reranker.rerank(
            query,
            candidates,
            jurisdiction=jurisdiction,
            path=path,
            top_k=top_k,
        )

        deduped: list[RegulationDoc] = []
        seen: set[str] = set()
        for candidate in reranked:
            doc = RegulationDoc(
                id=str(candidate.payload.get("id", "")),
                title=str(candidate.payload.get("title", "")),
                article=str(candidate.payload.get("article", "")),
                content=str(candidate.payload.get("content", "")),
                jurisdiction=str(candidate.payload.get("jurisdiction", "")),
                path=str(candidate.payload.get("path", "")),
                doc_type=str(candidate.payload.get("doc_type", "")),
            )
            identity = f"{_normalize(doc.title)}::{_normalize(doc.article)}"
            if identity in seen:
                continue
            seen.add(identity)
            deduped.append(doc)
            if len(deduped) >= top_k:
                break

        return deduped
