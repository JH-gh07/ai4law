"""CPRALegalRetriever — domain-specific dynamic regulation retrieval."""

from __future__ import annotations

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

    def retrieve(self, domain: str, extra_context: str = "") -> list[dict]:
        from backend.common.rag.retriever import retrieve_regulations

        base = _DOMAIN_QUERIES.get(domain, "CPRA CCPA consumer privacy compliance")
        query = f"{base} {extra_context}"[:500]

        try:
            hits = retrieve_regulations(query, top_k=3, jurisdiction="us", path="all")
        except Exception:
            return []

        return [
            {"source": f"{item.title}{item.article}", "snippet": (item.content or "")[:200]}
            for item in hits
        ]

    def retrieve_all(self, domains: list[str]) -> dict[str, list[dict]]:
        return {d: self.retrieve(d) for d in domains}
