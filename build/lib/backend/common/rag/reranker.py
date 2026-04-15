from __future__ import annotations

from dataclasses import dataclass

from backend.common.rag.embedding import normalize_text, tokenize_text


@dataclass
class RerankCandidate:
    payload: dict
    vector_score: float
    lexical_score: float
    base_score: float


class HeuristicReranker:
    def rerank(
        self,
        query: str,
        candidates: list[RerankCandidate],
        *,
        jurisdiction: str | None = None,
        path: str | None = None,
        top_k: int = 8,
    ) -> list[RerankCandidate]:
        query_n = normalize_text(query)
        query_tokens = set(tokenize_text(query))
        rescored: list[tuple[float, RerankCandidate]] = []

        for candidate in candidates:
            payload = candidate.payload
            title = normalize_text(str(payload.get("title", "")))
            article = normalize_text(str(payload.get("article", "")))
            content = normalize_text(str(payload.get("content", "")))
            keywords = [normalize_text(str(item)) for item in payload.get("keywords", [])]

            phrase_bonus = 0.0
            if title and title in query_n:
                phrase_bonus += 2.0
            if article and article in query_n:
                phrase_bonus += 1.2

            overlap = 0
            for token in query_tokens:
                if token and (token in title or token in article or token in content):
                    overlap += 1
            overlap_bonus = min(overlap * 0.15, 2.4)

            keyword_bonus = min(sum(0.3 for keyword in keywords if keyword and keyword in query_n), 1.2)

            metadata_bonus = 0.0
            candidate_jurisdiction = str(payload.get("jurisdiction", ""))
            candidate_path = str(payload.get("path", ""))
            if jurisdiction and candidate_jurisdiction == jurisdiction:
                metadata_bonus += 0.4
            if path and candidate_path in {path, "all", "general", "review"}:
                metadata_bonus += 0.4

            rescored.append(
                (
                    candidate.base_score + phrase_bonus + overlap_bonus + keyword_bonus + metadata_bonus,
                    candidate,
                )
            )

        rescored.sort(key=lambda item: item[0], reverse=True)
        return [candidate for _, candidate in rescored[:top_k]]
