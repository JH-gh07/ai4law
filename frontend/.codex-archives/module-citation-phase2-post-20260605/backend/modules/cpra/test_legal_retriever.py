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


def test_cpra_legal_retriever_extracts_us_article_and_source_metadata() -> None:
    retriever = CPRALegalRetriever()

    class _Hit:
        title = "CPPA Regulations"
        article = "Art.7004"
        content = "Dark patterns are prohibited."
        score = 0.64
        id = "cppa_7004"

    result = retriever._normalize_hit(_Hit())  # noqa: SLF001

    assert result["source_id"] == "us_cppa_regulations"
    assert result["article_no"] == "7004"
    assert result["display_label"] == "CPPA Art.7004"
    assert result["confidence_score"] == 0.64
