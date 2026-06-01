from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from backend.common.rag.embedding import HashingEmbedder, normalize_text, tokenize_text
from backend.common.rag.ingest import build_regulation_index
from backend.common.rag.reranker import HeuristicReranker, RerankCandidate
from backend.common.rag.vector_store import LocalVectorStore
from backend.core.settings import Settings, get_settings

if TYPE_CHECKING:
    from backend.services.legal_api_service import DeliLegalService


_default_legal_service: object = None
_default_legal_service_loaded: bool = False


def _get_default_legal_service() -> object:
    global _default_legal_service, _default_legal_service_loaded
    if _default_legal_service_loaded:
        return _default_legal_service
    _default_legal_service_loaded = True
    try:
        from backend.services.legal_api_service import DeliLegalService

        _default_legal_service = DeliLegalService(get_settings())
    except Exception:
        _default_legal_service = None
    return _default_legal_service


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
    keywords: tuple[str, ...] = field(default_factory=tuple)


ROOT = Path(__file__).resolve().parents[3]
RAG_LOG_DIR_ENV = "AI4LAW_RAG_LOG_DIR"
RAG_LOG_ENABLE_ENV = "AI4LAW_RAG_LOG"
DEFAULT_RAG_LOG_DIR = ROOT / "outputs" / "qa"

DEFAULT_SCORE_FLOOR_BY_MODE = {
    "vector": 0.05,
    "hybrid": 0.1,
    "lexical": 2.0,
}

OFF_TOPIC_HINTS: tuple[str, ...] = (
    "weather",
    "python",
    "docker",
    "mysql",
    "nginx",
    "laptop",
    "battery",
    "steak",
    "cake",
    "macbook",
)

JURISDICTION_STRONG_HINTS: dict[str, tuple[str, ...]] = {
    "cn": (
        "数据出境",
        "个人信息",
        "重要数据",
        "网信",
        "标准合同",
        "安全评估",
        "认证",
        "pipl",
    ),
    "eu": (
        "gdpr",
        "edpb",
        "bcr",
        "dpia",
        "tia",
        "article 35",
        "article 47",
    ),
    "us": (
        "cpra",
        "ccpa",
        "california",
        "eo 14117",
        "covered person",
        "restricted transaction",
    ),
}

PATH_STRONG_HINTS: dict[str, tuple[str, ...]] = {
    "assessment": ("安全评估", "assessment", "重要数据", "100万", "10万敏感"),
    "scc": ("标准合同", "认证", "scc", "备案", "个人信息出境"),
    "review": ("合同审查", "条款", "协议", "合规审查", "review"),
}


def _contains_any_hint(query_l: str, hints: tuple[str, ...]) -> bool:
    return any(hint.lower() in query_l for hint in hints)


def _normalize(text: str) -> str:
    return normalize_text(text or "")


def _extract_article_hint(query: str) -> Optional[str]:
    match = re.search(r"第[一二三四五六七八九十百千万零0-9]{1,10}条", query or "")
    return match.group(0) if match else None


def _extract_law_hint(query: str) -> str:
    value = re.sub(r"第[一二三四五六七八九十百千万零0-9]{1,10}条", "", query or "")
    return re.sub(r"[\s,，。；;（）()\[\]]", "", value).strip()


def _is_off_topic_query(query: str) -> bool:
    return _contains_any_hint((query or "").lower(), OFF_TOPIC_HINTS)


def _is_jurisdiction_mismatch(query: str, jurisdiction: Optional[str]) -> bool:
    if not jurisdiction:
        return False
    query_l = (query or "").lower()
    matched = {
        name for name, hints in JURISDICTION_STRONG_HINTS.items() if _contains_any_hint(query_l, hints)
    }
    if not matched:
        return False
    return jurisdiction.lower() not in matched


def _is_path_mismatch(query: str, path: Optional[str]) -> bool:
    if not path or path not in PATH_STRONG_HINTS:
        return False
    query_l = (query or "").lower()
    matched = {
        name for name, hints in PATH_STRONG_HINTS.items() if _contains_any_hint(query_l, hints)
    }
    if not matched:
        return False
    return path.lower() not in matched


def _rewrite_query(query: str, jurisdiction: Optional[str], path: Optional[str]) -> str:
    value = query or ""
    additions: list[str] = []

    if jurisdiction:
        for hint in JURISDICTION_STRONG_HINTS.get(jurisdiction, ()):
            if hint.lower() not in value.lower():
                additions.append(hint)
    if path:
        for hint in PATH_STRONG_HINTS.get(path, ()):
            if hint.lower() not in value.lower():
                additions.append(hint)
    if not additions:
        return value
    return f"{value} {' '.join(additions)}"


def _passes_filter(
    doc: RegulationDoc,
    jurisdiction: Optional[str],
    path: Optional[str],
    doc_type: Optional[str],
    source: Optional[str] = None,
) -> bool:
    if jurisdiction and doc.jurisdiction and _normalize(doc.jurisdiction) != _normalize(jurisdiction):
        return False
    if path and doc.path and doc.path not in {path, "all", "general", "review"}:
        return False
    if doc_type and doc.doc_type and _normalize(doc_type) not in _normalize(doc.doc_type):
        return False
    if source and doc.doc_type:
        if source == "regulatory" and doc.doc_type == "external":
            return False
        if source == "user" and doc.doc_type == "external":
            return True
    return True


def _lexical_score(query: str, doc: RegulationDoc) -> float:
    query_n = _normalize(query)
    if not query_n:
        return 0.0

    title_n = _normalize(doc.title)
    article_n = _normalize(doc.article)
    content_n = _normalize(doc.content)
    query_tokens = set(tokenize_text(query))

    score = 0.0
    law_hint = _normalize(_extract_law_hint(query))
    article_hint = _normalize(_extract_article_hint(query) or "")
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
        keyword_n = _normalize(keyword)
        if keyword_n and keyword_n in query_n:
            score += 0.4

    return score


class RegulationRAGService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.embedder = HashingEmbedder(settings.rag_embedding_dimension)
        self.vector_store = LocalVectorStore(settings.rag_index_path, self.embedder)
        self.reranker = HeuristicReranker()
        self._enhanced_retriever = None

    def _get_enhanced_retriever(self):
        if self._enhanced_retriever is None:
            from backend.common.rag.hybrid_retriever import EnhancedHybridRetriever
            from backend.core.db import build_engine, build_session_factory
            try:
                engine = build_engine(self.settings.database_url)
                session_factory = build_session_factory(engine)
                self._enhanced_retriever = EnhancedHybridRetriever(
                    self.settings, db_session=session_factory()
                )
            except Exception:
                self._enhanced_retriever = EnhancedHybridRetriever(self.settings, db_session=None)
        return self._enhanced_retriever

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 8,
        jurisdiction: Optional[str] = None,
        path: Optional[str] = None,
        doc_type: Optional[str] = None,
        source: Optional[str] = None,
        mode: str = "hybrid",
        score_floor: Optional[float] = None,
    ) -> list[RegulationDoc]:
        if mode == "hybrid_enhanced":
            return self._get_enhanced_retriever().search(
                query,
                top_k=top_k,
                jurisdiction=jurisdiction,
                path=path,
                doc_type=doc_type,
                source=source,
            )
        if _is_off_topic_query(query) or _is_jurisdiction_mismatch(query, jurisdiction):
            return []

        entries = self._ensure_entries()
        vector_hits = self.vector_store.search(
            query,
            list(entries),
            top_k=max(top_k, self.settings.rag_candidate_pool_size),
        )

        candidates: list[RerankCandidate] = []
        for vector_score, entry in vector_hits:
            doc = self._payload_to_doc(entry.payload)
            if not _passes_filter(doc, jurisdiction=jurisdiction, path=path, doc_type=doc_type, source=source):
                continue
            lexical_score = _lexical_score(query, doc)
            if mode == "vector":
                base_score = vector_score
            elif mode == "lexical":
                base_score = lexical_score
            else:
                base_score = vector_score * 0.7 + lexical_score * 0.3
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
            identity = f"{_normalize(doc.title)}::{_normalize(doc.article)}"
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
    source: Optional[str] = None,
    mode: str = "hybrid",
    score_floor: Optional[float] = None,
    legal_service: Optional["DeliLegalService"] = None,
    min_local: int = 3,
) -> list[RegulationDoc]:
    rewritten_query = _rewrite_query(query, jurisdiction, path)
    if _is_off_topic_query(rewritten_query):
        return []
    if _is_jurisdiction_mismatch(rewritten_query, jurisdiction):
        return []
    if _is_path_mismatch(rewritten_query, path):
        return []

    docs = _service().retrieve(
        rewritten_query,
        top_k=top_k,
        jurisdiction=jurisdiction,
        path=path,
        doc_type=doc_type,
        source=source,
        mode=mode,
        score_floor=score_floor,
    )

    effective_legal_service = legal_service if legal_service is not None else _get_default_legal_service()
    if (
        effective_legal_service
        and getattr(effective_legal_service, "enabled", False)
        and len(docs) < min_local
    ):
        existing_titles = {_normalize(doc.title) for doc in docs}
        remote_hits = effective_legal_service.search_laws(query, size=max(top_k - len(docs), 0) + 2)
        for hit in remote_hits:
            title = str(hit.get("title", "")).strip()
            if not title or _normalize(title) in existing_titles:
                continue
            docs.append(
                RegulationDoc(
                    id=f"delilegal-{_normalize(title)[:20]}",
                    title=title,
                    article="",
                    content=str(hit.get("summary", "")),
                    jurisdiction=jurisdiction or "",
                    path=path or "all",
                    doc_type="external",
                )
            )
            existing_titles.add(_normalize(title))
            if len(docs) >= top_k:
                break

    _log_rag_hits(
        query=query,
        rewritten_query=rewritten_query,
        jurisdiction=jurisdiction,
        path=path,
        doc_type=doc_type,
        mode=mode,
        score_floor=score_floor,
        top_k=top_k,
        results=docs,
    )
    return docs


def rebuild_regulation_index() -> Path:
    return _service().rebuild_index()


def _log_rag_hits(
    query: str,
    rewritten_query: str,
    jurisdiction: Optional[str],
    path: Optional[str],
    doc_type: Optional[str],
    mode: str,
    score_floor: Optional[float],
    top_k: int,
    results: list[RegulationDoc],
) -> None:
    enabled_flag = os.getenv(RAG_LOG_ENABLE_ENV, "").strip().lower()
    log_dir_value = os.getenv(RAG_LOG_DIR_ENV, "").strip()
    if enabled_flag not in {"1", "true", "yes"} and not log_dir_value:
        return

    log_dir = Path(log_dir_value) if log_dir_value else DEFAULT_RAG_LOG_DIR
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return

    log_path = log_dir / f"rag_hits_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    payload = {
        "ts": datetime.now().isoformat(),
        "query": query,
        "rewritten_query": rewritten_query,
        "jurisdiction": jurisdiction,
        "path": path,
        "doc_type": doc_type,
        "mode": mode,
        "score_floor": score_floor,
        "top_k": top_k,
        "hit_count": len(results),
        "hits": [
            {
                "id": doc.id,
                "title": doc.title,
                "article": doc.article,
                "content": doc.content[:200],
                "jurisdiction": doc.jurisdiction,
                "path": doc.path,
                "doc_type": doc.doc_type,
                "source_url": doc.source_url,
                "snapshot_path": doc.snapshot_path,
            }
            for doc in results
        ],
    }
    try:
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError:
        return
