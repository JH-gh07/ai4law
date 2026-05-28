from fastapi import APIRouter, HTTPException, Query

from backend.services.knowledge_index import (
    get_knowledge_sync_meta,
    load_practice_cases,
    load_sources_index,
    read_text_preview,
    refresh_knowledge_cache,
    resolve_citation,
)
from backend.common.rag.retriever import retrieve_regulations
from backend.schemas.knowledge import (
    KnowledgeCaseDetailResponse,
    KnowledgeCaseOptions,
    KnowledgeCitationResponse,
    KnowledgeIndexResponse,
    KnowledgeSearchItem,
    KnowledgeSearchResponse,
    KnowledgeSourceDetailResponse,
    KnowledgeSourceOptions,
    KnowledgeSummary,
    KnowledgeSyncMeta,
)

router = APIRouter()


def _find_by_id(rows: list[dict[str, str]], key: str, value: str) -> dict[str, str] | None:
    return next((row for row in rows if row.get(key) == value), None)


def _sanitize_knowledge_row(row: dict[str, str]) -> dict[str, str]:
    return {key: value for key, value in row.items() if key not in {"usage_priority", "priority"}}


def _build_source_options(rows: list[dict[str, str]]) -> KnowledgeSourceOptions:
    return KnowledgeSourceOptions(
        layers=sorted({row.get("layer", "") for row in rows if row.get("layer")}),
        paths=sorted({row.get("path", "") for row in rows if row.get("path")}),
    )


def _build_case_options(rows: list[dict[str, str]]) -> KnowledgeCaseOptions:
    modules: set[str] = set()
    for row in rows:
        for module in row.get("expected_module", "").split("|"):
            module = module.strip()
            if module:
                modules.add(module)

    return KnowledgeCaseOptions(
        modules=sorted(modules),
    )


@router.get("/index", response_model=KnowledgeIndexResponse)
def get_knowledge_index() -> KnowledgeIndexResponse:
    return _build_index_response(cache_refreshed=False)


@router.post("/sync", response_model=KnowledgeIndexResponse)
def sync_knowledge_index() -> KnowledgeIndexResponse:
    refresh_knowledge_cache()
    return _build_index_response(cache_refreshed=True)


def _build_index_response(*, cache_refreshed: bool) -> KnowledgeIndexResponse:
    sources = [_sanitize_knowledge_row(row) for row in load_sources_index()]
    cases = [_sanitize_knowledge_row(row) for row in load_practice_cases()]

    summary = KnowledgeSummary(
        source_count=len(sources),
        case_count=len(cases),
    )
    sync_meta = KnowledgeSyncMeta.model_validate(get_knowledge_sync_meta(cache_refreshed=cache_refreshed))

    return KnowledgeIndexResponse(
        summary=summary,
        sync_meta=sync_meta,
        source_options=_build_source_options(sources),
        case_options=_build_case_options(cases),
        sources=sources,
        cases=cases,
    )


@router.get("/sources/{source_id}", response_model=KnowledgeSourceDetailResponse)
def get_source_detail(source_id: str) -> KnowledgeSourceDetailResponse:
    sources = [_sanitize_knowledge_row(row) for row in load_sources_index()]
    item = _find_by_id(sources, key="source_id", value=source_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Source not found: {source_id}")

    preview = read_text_preview(item.get("snapshot_path", ""), limit=600)
    return KnowledgeSourceDetailResponse(item=item, preview=preview)


@router.get("/cases/{case_id}", response_model=KnowledgeCaseDetailResponse)
def get_case_detail(case_id: str) -> KnowledgeCaseDetailResponse:
    cases = [_sanitize_knowledge_row(row) for row in load_practice_cases()]
    item = _find_by_id(cases, key="case_id", value=case_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")

    preview = read_text_preview(item.get("snapshot_path", ""), limit=600)
    return KnowledgeCaseDetailResponse(item=item, preview=preview)


@router.get("/search", response_model=KnowledgeSearchResponse)
def search_regulations(
    q: str = Query(default=""),
    jurisdiction: str | None = Query(default=None),
    path: str | None = Query(default=None),
    top_k: int = Query(default=8, ge=1, le=20),
    mode: str = Query(default="hybrid"),
) -> KnowledgeSearchResponse:
    query = q.strip()
    if not query:
        return KnowledgeSearchResponse(query=q, hit_count=0)

    docs = retrieve_regulations(
        query,
        top_k=top_k,
        jurisdiction=jurisdiction or None,
        path=path or None,
        mode=mode,
    )

    items = [
        KnowledgeSearchItem(
            id=doc.id,
            title=doc.title,
            article=doc.article,
            content=doc.content,
            jurisdiction=doc.jurisdiction,
            path=doc.path,
            doc_type=doc.doc_type,
            source_url=doc.source_url,
            keywords=list(doc.keywords),
        )
        for doc in docs
    ]

    return KnowledgeSearchResponse(
        query=query,
        jurisdiction=jurisdiction,
        path=path,
        mode=mode,
        top_k=top_k,
        hit_count=len(items),
        items=items,
    )


@router.get("/citation", response_model=KnowledgeCitationResponse)
def match_citation(query: str = Query(default="")) -> KnowledgeCitationResponse:
    text = query.strip()
    if not text:
        return KnowledgeCitationResponse(query=query, matched=None, preview="")

    sources = load_sources_index()
    matched = resolve_citation(text, sources=sources)
    if not matched:
        return KnowledgeCitationResponse(query=query, matched=None, preview="")

    matched = _sanitize_knowledge_row(matched)
    preview = read_text_preview(matched.get("snapshot_path", ""), limit=600)
    return KnowledgeCitationResponse(query=query, matched=matched, preview=preview)
