from backend.domains.us.cpra.legal_retriever import CPRALegalRetriever
from backend.domains.us.cpra.schema import CPRAGapItem


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


def test_cpra_legal_retriever_preserves_canonical_registry_source_id() -> None:
    retriever = CPRALegalRetriever()

    class _Hit:
        title = "California Civil Code — CCPA"
        article = "§ 1798.120"
        content = "Consumers may direct a business not to sell or share personal information."
        score = 0.91
        id = "US-CA-001"

    result = retriever._normalize_hit(_Hit())  # noqa: SLF001

    assert result["source_id"] == "US-CA-001"
    assert result["article_no"] == "1798.120"
    assert result["display_label"] == "CPRA § 1798.120"


def test_cpra_legal_retriever_uses_product_registry_module(monkeypatch) -> None:
    calls: list[dict] = []

    def _retrieve(query: str, **kwargs):
        calls.append({"query": query, **kwargs})
        return type("Hits", (), {"documents": []})()

    monkeypatch.setattr(
        "backend.domains.us.cpra.legal_retriever.retrieve_legal_documents",
        _retrieve,
    )

    CPRALegalRetriever().retrieve("opt_out")

    assert calls[0]["module"] == "us_cpra"


def test_cpra_legal_retriever_prioritizes_the_requested_exact_locator(monkeypatch) -> None:
    class _Hit:
        def __init__(self, article: str, score: float) -> None:
            self.title = "California Civil Code — CCPA/CPRA"
            self.article = article
            self.content = f"Rule for {article}"
            self.score = score
            self.id = "US-CA-001"

    def _retrieve(_query: str, **_kwargs):
        return type(
            "Hits",
            (),
            {"documents": [_Hit("1798.130", 0.99), _Hit("1798.100", 0.70)]},
        )()

    monkeypatch.setattr(
        "backend.domains.us.cpra.legal_retriever.retrieve_legal_documents",
        _retrieve,
    )

    results = CPRALegalRetriever().retrieve("notice", "Civil Code § 1798.100")

    assert results[0]["article_no"] == "1798.100"
