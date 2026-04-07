from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

from backend.common.rag.embedding import HashingEmbedder, normalize_text, tokenize_text
from backend.common.rag.ingest import build_regulation_index
from backend.common.rag.reranker import HeuristicReranker, RerankCandidate
from backend.common.rag.vector_store import LocalVectorStore
from backend.core.settings import Settings, get_settings


@dataclass
class RegulationDoc:
    id: str
    title: str
    article: str
    content: str
    jurisdiction: str = ""
    path: str = ""
    doc_type: str = ""
    source_url: str = ""
    snapshot_path: str = ""
    usage_priority: str = "P1"
    keywords: tuple[str, ...] = field(default_factory=tuple)


DEFAULT_SCORE_FLOOR_BY_MODE = {
    "vector": 0.05,
    "hybrid": 0.1,
    "lexical": 2.0,
}

OFF_TOPIC_HINTS: tuple[str, ...] = (
    "火锅",
    "天气",
    "python",
    "docker",
    "mysql",
    "nginx",
    "laptop",
    "battery",
    "steak",
    "cake",
    "macbook",
    "爬虫",
)

JURISDICTION_STRONG_HINTS: dict[str, tuple[str, ...]] = {
    "cn": ("数据出境", "网信", "个人信息保护法", "数据安全法", "网络安全法", "标准合同", "个人信息出境", "pipia"),
    "eu": ("gdpr", "edpb", "bcr", "dpia", "transfer impact assessment", "tia", "article 35", "article 47"),
    "us": ("cpra", "ccpa", "california", "eo 14117", "covered person", "restricted transactions"),
}


def _contains_any_hint(query_l: str, hints: tuple[str, ...]) -> bool:
    return any(hint.lower() in query_l for hint in hints)


def _priority_weight(priority: str) -> float:
    return {"P0": 0.6, "P1": 0.3, "P2": 0.1}.get(priority or "", 0.0)


def _extract_article_hint(query: str) -> Optional[str]:
    match = re.search(r"第[一二三四五六七八九十百千万零0-9]{1,10}条", query)
    return match.group(0) if match else None


def _extract_law_hint(query: str) -> str:
    value = re.sub(r"第[一二三四五六七八九十百千万零0-9]{1,10}条", "", query)
    return re.sub(r"[\s,，。；;（）()\[\]]", "", value).strip()


def _is_off_topic_query(query: str) -> bool:
    return _contains_any_hint(query.lower(), OFF_TOPIC_HINTS)


def _is_jurisdiction_mismatch(query: str, jurisdiction: Optional[str]) -> bool:
    if not jurisdiction:
        return False
    query_l = query.lower()
    matched = {name for name, hints in JURISDICTION_STRONG_HINTS.items() if _contains_any_hint(query_l, hints)}
    if not matched:
        return False
    return jurisdiction.lower() not in matched


def _passes_filter(doc: RegulationDoc, jurisdiction: Optional[str], path: Optional[str], doc_type: Optional[str]) -> bool:
    if jurisdiction and doc.jurisdiction and normalize_text(doc.jurisdiction) != normalize_text(jurisdiction):
        return False
    if path and doc.path and doc.path not in {path, "all", "general", "review"}:
        return False
    if doc_type and doc.doc_type and normalize_text(doc_type) not in normalize_text(doc.doc_type):
        return False
    return True


def _lexical_score(query: str, doc: RegulationDoc) -> float:
    query_n = normalize_text(query)
    if not query_n:
        return 0.0

    title_n = normalize_text(doc.title)
    article_n = normalize_text(doc.article)
    content_n = normalize_text(doc.content)
    query_tokens = set(tokenize_text(query))

    score = 0.0
    law_hint = normalize_text(_extract_law_hint(query))
    article_hint = normalize_text(_extract_article_hint(query) or "")
    if law_hint and law_hint in title_n:
        score += 6.0
    if article_hint and article_hint in article_n:
        score += 3.0
    if query_n in title_n or title_n in query_n:
        score += 4.0

    overlap = 0
    for token in query_tokens:
        if token and (token in title_n or token in article_n or token in content_n):
            overlap += 1
    score += min(overlap * 0.35, 6.0)

    for keyword in doc.keywords:
        keyword_n = normalize_text(keyword)
        if keyword_n and keyword_n in query_n:
            score += 0.4
    return score


class RegulationRAGService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.embedder = HashingEmbedder(settings.rag_embedding_dimension)
        self.vector_store = LocalVectorStore(settings.rag_index_path, self.embedder)
        self.reranker = HeuristicReranker()

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 8,
        jurisdiction: Optional[str] = None,
        path: Optional[str] = None,
        doc_type: Optional[str] = None,
        mode: str = "hybrid",
        score_floor: Optional[float] = None,
    ) -> list[RegulationDoc]:
        if _is_off_topic_query(query) or _is_jurisdiction_mismatch(query, jurisdiction):
            return []

        entries = self._ensure_entries()
        vector_hits = self.vector_store.search(query, list(entries), top_k=max(top_k, self.settings.rag_candidate_pool_size))

        candidates: list[RerankCandidate] = []
        for vector_score, entry in vector_hits:
            doc = self._payload_to_doc(entry.payload)
            if not _passes_filter(doc, jurisdiction=jurisdiction, path=path, doc_type=doc_type):
                continue
            lexical_score = _lexical_score(query, doc)
            if mode == "vector":
                base_score = vector_score + _priority_weight(doc.usage_priority)
            elif mode == "lexical":
                base_score = lexical_score + _priority_weight(doc.usage_priority)
            else:
                base_score = vector_score * 0.7 + lexical_score * 0.3 + _priority_weight(doc.usage_priority)
            candidates.append(
                RerankCandidate(
                    payload=entry.payload,
                    vector_score=vector_score,
                    lexical_score=lexical_score,
                    base_score=base_score,
                )
            )

        if not candidates:
            return []

        floor = DEFAULT_SCORE_FLOOR_BY_MODE.get(mode, 0.0) if score_floor is None else score_floor
        filtered = [candidate for candidate in candidates if candidate.base_score >= floor]
        if not filtered:
            return []

        reranked = self.reranker.rerank(
            query,
            filtered[: self.settings.rag_rerank_candidate_count],
            jurisdiction=jurisdiction,
            path=path,
            top_k=top_k,
        )

        deduped: list[RegulationDoc] = []
        seen: set[str] = set()
        for candidate in reranked:
            doc = self._payload_to_doc(candidate.payload)
            identity = f"{normalize_text(doc.title)}::{normalize_text(doc.article)}"
            if identity in seen:
                continue
            seen.add(identity)
            deduped.append(doc)
            if len(deduped) >= top_k:
                break
        return deduped

    def rebuild_index(self) -> Path:
        path = build_regulation_index(self.settings)
        self._ensure_entries.cache_clear()  # type: ignore[attr-defined]
        return path

    @lru_cache(maxsize=1)
    def _ensure_entries(self) -> tuple:
        if self.settings.rag_auto_build_index and not self.vector_store.exists():
            build_regulation_index(self.settings)
        return tuple(self.vector_store.load())

    @staticmethod
    def _payload_to_doc(payload: dict) -> RegulationDoc:
        return RegulationDoc(
            id=str(payload.get("id", "")),
            title=str(payload.get("title", "")),
            article=str(payload.get("article", "")),
            content=str(payload.get("content", "")),
            jurisdiction=str(payload.get("jurisdiction", "")),
            path=str(payload.get("path", "")),
            doc_type=str(payload.get("doc_type", "")),
            source_url=str(payload.get("source_url", "")),
            snapshot_path=str(payload.get("snapshot_path", "")),
            usage_priority=str(payload.get("usage_priority", "P1")),
            keywords=tuple(str(item) for item in payload.get("keywords", [])),
        )


@lru_cache(maxsize=1)
def _service() -> RegulationRAGService:
    return RegulationRAGService(get_settings())


def retrieve_regulations(
    query: str,
    top_k: int = 8,
    jurisdiction: Optional[str] = None,
    path: Optional[str] = None,
    doc_type: Optional[str] = None,
    mode: str = "hybrid",
    score_floor: Optional[float] = None,
) -> list[RegulationDoc]:
    return _service().retrieve(
        query,
        top_k=top_k,
        jurisdiction=jurisdiction,
        path=path,
        doc_type=doc_type,
        mode=mode,
        score_floor=score_floor,
    )


def rebuild_regulation_index() -> Path:
    return _service().rebuild_index()
