from pathlib import Path

from backend.common.rag.embedding import HashingEmbedder
from backend.common.rag.ingest import build_regulation_index
from backend.common.rag import retriever as retriever_module
from backend.common.rag.retriever import RegulationRAGService
from backend.core.settings import Settings
from backend.schemas.review import ClauseType
from backend.services.review_service.rag_provider import LocalRegulationKnowledgeBase


def _write_fixture(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                '{"article_id":"pipl-39","law_name":"个人信息保护法","article_ref":"第39条","content":"向境外提供个人信息前，应当告知境外接收方名称、联系方式、处理目的和处理方式，并取得单独同意。","jurisdiction":"cn","path":"review","doc_type":"law","usage_priority":"P0","keywords":["单独同意","境外接收方","联系方式"]}',
                '{"article_id":"pipl-44","law_name":"个人信息保护法","article_ref":"第44条","content":"个人有权查阅、复制其个人信息。","jurisdiction":"cn","path":"review","doc_type":"law","usage_priority":"P1","keywords":["查阅","复制"]}',
                '{"article_id":"dsl-21","law_name":"数据安全法","article_ref":"第21条","content":"国家建立数据分类分级保护制度，对重要数据实施重点保护。","jurisdiction":"cn","path":"assessment","doc_type":"law","usage_priority":"P0","keywords":["重要数据","分类分级"]}',
            ]
        ),
        encoding="utf-8",
    )


def test_hashing_embedder_is_deterministic() -> None:
    embedder = HashingEmbedder(dimension=128)
    left = embedder.embed("境外接收方 联系方式 单独同意")
    right = embedder.embed("境外接收方 联系方式 单独同意")
    assert left == right
    assert embedder.similarity(left, right) > 0.99


def test_rag_service_builds_vector_index_and_retrieves_exact_article(tmp_path: Path) -> None:
    source = tmp_path / "regulation_articles.jsonl"
    index = tmp_path / "regulation_index_v2.json"
    _write_fixture(source)

    settings = Settings(
        rag_source_jsonl=source,
        rag_index_path=index,
        rag_embedding_dimension=128,
        rag_candidate_pool_size=8,
        rag_rerank_candidate_count=5,
        rag_auto_build_index=True,
    )
    build_regulation_index(settings)
    service = RegulationRAGService(settings)

    hits = service.retrieve(
        "个人信息出境时应如何告知境外接收方联系方式并取得单独同意",
        top_k=2,
        jurisdiction="cn",
        path="review",
        mode="hybrid",
    )

    assert hits
    assert hits[0].id == "pipl-39"
    assert index.exists()


def test_review_knowledge_base_appends_vector_citations(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "regulation_articles.jsonl"
    index = tmp_path / "regulation_index_v2.json"
    _write_fixture(source)

    settings = Settings(
        rag_source_jsonl=source,
        rag_index_path=index,
        rag_embedding_dimension=128,
        rag_candidate_pool_size=8,
        rag_rerank_candidate_count=5,
        rag_auto_build_index=True,
    )
    build_regulation_index(settings)

    monkeypatch.setattr(retriever_module, "get_settings", lambda: settings)
    retriever_module._service.cache_clear()

    knowledge_base = LocalRegulationKnowledgeBase()
    result = knowledge_base.lookup(
        ClauseType.CONSENT_NOTICE,
        "境外接收方应当披露联系方式，并取得个人的单独同意。",
    )

    assert any("个人信息保护法" in citation for citation in result["citations"])
