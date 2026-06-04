from backend.modules.cpra.legal_retriever import CPRALegalRetriever
from backend.modules.cpra.schema import CPRAGapItem


def test_cpra_legal_retriever_caches_gap_level_results(monkeypatch) -> None:
    retriever = CPRALegalRetriever()
    calls = {"count": 0}

    def _fake_retrieve(domain: str, extra_context: str = "") -> list[dict]:
        calls["count"] += 1
        return [{"source": f"{domain}:{extra_context}", "snippet": "cached"}]

    monkeypatch.setattr(retriever, "retrieve", _fake_retrieve)

    gap = CPRAGapItem(
        domain="spi_review",
        risk_level="HIGH",
        gap="敏感个人信息高风险共享",
        legal_basis="CPRA §1798.121",
        recommendation="补充限制使用和退出机制",
        phase="short_term",
    )

    first = retriever.retrieve_for_gaps([gap])
    second = retriever.retrieve_for_gaps([gap])

    assert calls["count"] == 1
    assert first == second
