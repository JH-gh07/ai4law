"""CPRALegalRetriever — domain-specific dynamic regulation retrieval."""

from __future__ import annotations

import os

from backend.modules.cpra.schema import CPRAGapItem

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

        from backend.common.rag.retriever import retrieve_regulations

        base = _DOMAIN_QUERIES.get(domain, "CPRA CCPA consumer privacy compliance")
        query = f"{base} {extra_context}"[:500]

        try:
            hits = retrieve_regulations(query, top_k=3, jurisdiction="us", path="all")
        except Exception:
            self._retrieve_cache[cache_key] = []
            return []

        results = [
            {"source": f"{item.title}{item.article}", "snippet": (item.content or "")[:200]}
            for item in hits
        ]
        self._retrieve_cache[cache_key] = results
        return results

    def retrieve_all(self, domains: list[str]) -> dict[str, list[dict]]:
        return {d: self.retrieve(d) for d in domains}

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
