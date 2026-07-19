"""CPRALegalRetriever — domain-specific dynamic regulation retrieval."""

from __future__ import annotations

import os
import re

from backend.common.rag.service import retrieve_legal_documents

from backend.domains.us.cpra.schema import CPRAGapItem

_DOMAIN_QUERIES = {
    "applicability": "CPRA business threshold annual revenue 25 million consumers §1798.140",
    "dsr": "CPRA consumer rights request methods 45 days toll-free number §1798.130",
    "opt_out": "CPRA do not sell or share global privacy control opt-out link §1798.120",
    "spi": "CPRA sensitive personal information limit use §1798.121",
    "vendor": "CPRA service provider contractor contract requirements DPA audit delete §1798.140",
    "dark_patterns": "CPPA dark patterns consent regulations §7004",
    "exemptions": "CPRA HIPAA GLBA exemption scope §1798.145",
    "notice": "CPRA notice at collection categories purposes retention §1798.100",
    "data_mapping": "CPRA data minimization purpose limitation retention §1798.100",
}


class CPRALegalRetriever:
    def __init__(self) -> None:
        self._retrieve_cache: dict[tuple[str, str], list[dict]] = {}
        self._gap_cache: dict[str, list[dict]] = {}

    def retrieve(self, domain: str, extra_context: str = "") -> list[dict]:
        if os.getenv("AI4LAW_CPRA_FAST_RETRIEVE") == "1":
            return []
        cache_key = (domain, extra_context[:500])
        if cache_key in self._retrieve_cache:
            return self._retrieve_cache[cache_key]

        base = _DOMAIN_QUERIES.get(domain, "CPRA CCPA consumer privacy compliance")
        query = f"{base} {extra_context}"[:500]

        try:
            hits = retrieve_legal_documents(
                query,
                module="us_privacy_review",
                top_k=3,
                jurisdiction="us",
                path="all",
            ).documents
        except Exception:
            self._retrieve_cache[cache_key] = []
            return []

        results = [
            self._normalize_hit(item)
            for item in hits
        ]
        self._retrieve_cache[cache_key] = results
        return results


    def retrieve_for_gap(self, gap: CPRAGapItem) -> list[dict]:
        query = self._build_gap_query(gap)
        return self.retrieve(gap.domain, extra_context=query)

    def retrieve_for_gaps(self, gaps: list[CPRAGapItem]) -> dict[str, list[dict]]:
        results: dict[str, list[dict]] = {}
        for idx, gap in enumerate(gaps):
            key = self._gap_key(gap, idx)
            if key not in self._gap_cache:
                self._gap_cache[key] = self.retrieve_for_gap(gap)
            results[key] = self._gap_cache[key]
        return results

    @staticmethod
    def _gap_key(gap: CPRAGapItem, index: int) -> str:
        return f"{index}:{gap.domain}:{gap.risk_level}:{gap.legal_basis}"

    @staticmethod
    def _build_gap_query(gap: CPRAGapItem) -> str:
        parts = [gap.domain, gap.gap, gap.legal_basis]
        if gap.recommendation:
            parts.append(gap.recommendation)
        return " ".join(part for part in parts if part)[:400]

    @classmethod
    def _normalize_hit(cls, item) -> dict:
        title = str(getattr(item, "title", "") or "").strip()
        article = str(getattr(item, "article", "") or "").strip()
        content = str(getattr(item, "content", "") or "").strip()
        score = float(getattr(item, "score", 0.0) or 0.0)
        source_id = cls._normalize_source_id(getattr(item, "source_id", "") or getattr(item, "id", "") or title)
        article_no = cls._extract_article_no(article or title)
        display_label = cls._build_display_label(title, article, article_no)
        source_title = cls._normalize_source_title(title)
        return {
            "source": display_label,
            "source_id": source_id,
            "source_title": source_title,
            "title": title,
            "article": article,
            "article_no": article_no,
            "display_label": display_label,
            "snippet": content[:500],
            "content": content,
            "score": score,
            "confidence_score": score,
            "retrieval_score": score,
            "jurisdiction": "US",
            "authority_level": cls._infer_authority_level(source_id, title),
            "binding_force": "mandatory",
            "citation_type": "law_article",
            "source_kind": "law_article",
        }

    @staticmethod
    def _normalize_source_title(title: str) -> str:
        value = (title or "").strip()
        if not value:
            return "California Consumer Privacy Act / CPRA"
        upper = value.upper()
        if "CPPA" in upper:
            return "California Privacy Protection Agency Regulations"
        if "CCPA" in upper or "CPRA" in upper:
            return "California Consumer Privacy Act / CPRA"
        return value

    @staticmethod
    def _normalize_source_id(source: str) -> str:
        value = str(source or "").strip()
        lower = value.lower()
        if "cppa" in lower or "700" in lower:
            return "us_cppa_regulations"
        if "ccpa" in lower or "cpra" in lower or "1798." in lower:
            return "us_cpra"
        return re.sub(r"[^a-z0-9]+", "_", lower).strip("_") or "us_cpra"

    @staticmethod
    def _extract_article_no(value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        match = re.search(r"§\s*([0-9]+(?:\.[0-9]+)*)", text)
        if match:
            return match.group(1)
        match = re.search(r"\bArt\.?\s*([0-9]+(?:\.[0-9]+)*)", text, re.I)
        if match:
            return match.group(1)
        match = re.search(r"\bArticle\s+([0-9]+(?:\.[0-9]+)*)", text, re.I)
        if match:
            return match.group(1)
        match = re.search(r"\b([0-9]{3,}(?:\.[0-9]+)*)\b", text)
        if match:
            return match.group(1)
        return ""

    @classmethod
    def _build_display_label(cls, title: str, article: str, article_no: str) -> str:
        upper = (title or "").upper()
        if "CPPA" in upper:
            if article:
                return f"CPPA {article}".strip()
            if article_no:
                return f"CPPA Art.{article_no}"
        if article:
            if "CPRA" in upper or "CCPA" in upper or "1798." in article:
                return f"CPRA {article}".strip()
            return f"{title} {article}".strip()
        if article_no:
            return f"CPRA §{article_no}"
        return title.strip() or "CPRA"

    @staticmethod
    def _infer_authority_level(source_id: str, title: str) -> str:
        if source_id == "us_cpra":
            return "high"
        if source_id == "us_cppa_regulations":
            return "medium"
        if "regulation" in title.lower():
            return "medium"
        return "high"
