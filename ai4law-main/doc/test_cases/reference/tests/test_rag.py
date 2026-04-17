from backend.schemas.rag import RagSearchFilters
from backend.services.rag_service import LocalLegalRAG


def test_local_rag_retrieves_cross_border_standard_contract_chunks():
    rag = LocalLegalRAG()
    hits = rag.search(
        "个人信息出境 标准合同 备案 影响评估",
        top_k=3,
        filters=RagSearchFilters(module_tag="review", contract_type="PERSONAL_INFO_SCC"),
    )
    assert hits
    assert any("标准合同" in hit.chunk.title or "备案" in hit.chunk.content for hit in hits)


def test_local_rag_applies_clause_type_filter():
    rag = LocalLegalRAG()
    hits = rag.search(
        "查询 删除 撤回同意 权利行使",
        top_k=5,
        filters=RagSearchFilters(module_tag="review", clause_type="RIGHTS_REQUEST"),
    )
    assert hits
    assert all("RIGHTS_REQUEST" in hit.chunk.clause_types for hit in hits)
