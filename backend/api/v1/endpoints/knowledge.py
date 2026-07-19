from fastapi import APIRouter, HTTPException, Query

from backend.services.knowledge_index import (
    get_article_detail,
    get_knowledge_sync_meta,
    refresh_knowledge_cache,
)
from backend.services.knowledge_projection import (
    build_user_case_catalog,
    build_user_source_catalog,
    get_user_case_detail,
    get_user_case_preview,
    get_user_source_detail,
    get_user_source_preview,
    resolve_user_citation,
    search_user_articles,
)
from backend.schemas.knowledge import (
    ArticleDetailResponse,
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



def _sanitize_knowledge_row(row: dict[str, str]) -> dict[str, str]:
    return {key: value for key, value in row.items() if key not in {"usage_priority", "priority"}}


def _build_source_options(rows: list[dict[str, str]]) -> KnowledgeSourceOptions:
    return KnowledgeSourceOptions(
        categories=sorted({row.get("category", "") for row in rows if row.get("category")}),
        jurisdictions=sorted({row.get("jurisdiction", "") for row in rows if row.get("jurisdiction")}),
        usages=sorted({row.get("usage", "") for row in rows if row.get("usage")}),
    )


def _build_case_options(rows: list[dict[str, str]]) -> KnowledgeCaseOptions:
    jurisdictions: set[str] = set()
    scenarios: set[str] = set()
    for row in rows:
        jurisdiction = row.get("jurisdiction", "").strip()
        if jurisdiction:
            jurisdictions.add(jurisdiction)
        for scenario in row.get("suitable_for", "").split("、"):
            scenario = scenario.strip()
            if scenario:
                scenarios.add(scenario)

    return KnowledgeCaseOptions(
        jurisdictions=sorted(jurisdictions),
        scenarios=sorted(scenarios),
    )


@router.get("/index", response_model=KnowledgeIndexResponse)
def get_knowledge_index() -> KnowledgeIndexResponse:
    return _build_index_response(cache_refreshed=False)


@router.post("/sync", response_model=KnowledgeIndexResponse)
def sync_knowledge_index() -> KnowledgeIndexResponse:
    refresh_knowledge_cache()
    return _build_index_response(cache_refreshed=True)


def _build_index_response(*, cache_refreshed: bool) -> KnowledgeIndexResponse:
    sources = [_sanitize_knowledge_row(row) for row in build_user_source_catalog()]
    cases = [_sanitize_knowledge_row(row) for row in build_user_case_catalog()]

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
    item = get_user_source_detail(source_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Source not found: {source_id}")

    preview = get_user_source_preview(source_id, limit=600)
    return KnowledgeSourceDetailResponse(item=_sanitize_knowledge_row(item), preview=preview)


@router.get("/cases/{case_id}", response_model=KnowledgeCaseDetailResponse)
def get_case_detail(case_id: str) -> KnowledgeCaseDetailResponse:
    item = get_user_case_detail(case_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")

    preview = get_user_case_preview(case_id, limit=600)
    return KnowledgeCaseDetailResponse(item=_sanitize_knowledge_row(item), preview=preview)


@router.get("/search", response_model=KnowledgeSearchResponse)
def search_regulations(
    q: str = Query(default=""),
    jurisdiction: str | None = Query(default=None),
    path: str | None = Query(default=None),
    source: str | None = Query(default=None),
    top_k: int = Query(default=8, ge=1, le=20),
    mode: str = Query(default="hybrid"),
) -> KnowledgeSearchResponse:
    query = q.strip()
    if not query:
        return KnowledgeSearchResponse(query=q, hit_count=0)

    chunks = search_user_articles(
        query,
        jurisdiction=jurisdiction or None,
        path=path or None,
        top_k=top_k,
    )

    items = [
        KnowledgeSearchItem(
            id=chunk.chunk_id,
            title=chunk.title,
            article=chunk.article_no or chunk.citation_anchor,
            content=chunk.content,
            jurisdiction=chunk.jurisdiction,
            path=chunk.path,
            doc_type=chunk.doc_type,
            source_url=chunk.source_url,
            keywords=list(chunk.keywords),
        )
        for chunk in chunks
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

    matched = resolve_user_citation(text)
    if not matched:
        return KnowledgeCitationResponse(query=query, matched=None, preview="")

    matched = _sanitize_knowledge_row(matched)
    preview = get_user_source_preview(matched.get("source_id", ""), limit=600)
    return KnowledgeCitationResponse(query=query, matched=matched, preview=preview)


@router.get("/sources/{source_id}/articles/{article_no}", response_model=ArticleDetailResponse)
def get_source_article(source_id: str, article_no: str) -> ArticleDetailResponse:
    """Retrieve a specific article from a knowledge source by source_id and article number.

    Returns the full article text with surrounding context (previous/next article)
    for in-context reading. Used by the citation display system when a user clicks
    a citation marker to view the original legal text.
    """
    detail = get_article_detail(source_id, article_no)
    if detail is None:
        raise HTTPException(
            status_code=404,
            detail=f"Article {article_no} not found in source {source_id}",
        )
    return ArticleDetailResponse(**detail)
