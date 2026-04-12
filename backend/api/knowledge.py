from fastapi import APIRouter, HTTPException, Query

from app_streamlit.services.knowledge import (
    get_knowledge_sync_meta,
    load_practice_cases,
    load_sources_index,
    read_text_preview,
    refresh_knowledge_cache,
    resolve_citation,
)
from backend.schemas.knowledge import (
    KnowledgeCaseDetailResponse,
    KnowledgeCaseOptions,
    KnowledgeCitationResponse,
    KnowledgeIndexResponse,
    KnowledgeSourceDetailResponse,
    KnowledgeSourceOptions,
    KnowledgeSummary,
    KnowledgeSyncMeta,
)

router = APIRouter()


def _find_by_id(rows: list[dict[str, str]], key: str, value: str) -> dict[str, str] | None:
    return next((row for row in rows if row.get(key) == value), None)


def _build_source_options(rows: list[dict[str, str]]) -> KnowledgeSourceOptions:
    return KnowledgeSourceOptions(
        layers=sorted({row.get("layer", "") for row in rows if row.get("layer")}),
        paths=sorted({row.get("path", "") for row in rows if row.get("path")}),
        priorities=sorted({row.get("usage_priority", "") for row in rows if row.get("usage_priority")}),
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
        priorities=sorted({row.get("priority", "") for row in rows if row.get("priority")}),
    )


@router.get("/index", response_model=KnowledgeIndexResponse)
def get_knowledge_index() -> KnowledgeIndexResponse:
    return _build_index_response(cache_refreshed=False)


@router.post("/sync", response_model=KnowledgeIndexResponse)
def sync_knowledge_index() -> KnowledgeIndexResponse:
    refresh_knowledge_cache()
    return _build_index_response(cache_refreshed=True)


def _build_index_response(*, cache_refreshed: bool) -> KnowledgeIndexResponse:
    sources = load_sources_index()
    cases = load_practice_cases()

    summary = KnowledgeSummary(
        source_count=len(sources),
        case_count=len(cases),
        p0_source_count=sum(1 for row in sources if row.get("usage_priority") == "P0"),
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
    sources = load_sources_index()
    item = _find_by_id(sources, key="source_id", value=source_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Source not found: {source_id}")

    preview = read_text_preview(item.get("snapshot_path", ""), limit=600)
    return KnowledgeSourceDetailResponse(item=item, preview=preview)


@router.get("/cases/{case_id}", response_model=KnowledgeCaseDetailResponse)
def get_case_detail(case_id: str) -> KnowledgeCaseDetailResponse:
    cases = load_practice_cases()
    item = _find_by_id(cases, key="case_id", value=case_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")

    preview = read_text_preview(item.get("snapshot_path", ""), limit=600)
    return KnowledgeCaseDetailResponse(item=item, preview=preview)


@router.get("/citation", response_model=KnowledgeCitationResponse)
def match_citation(query: str = Query(default="")) -> KnowledgeCitationResponse:
    text = query.strip()
    if not text:
        return KnowledgeCitationResponse(query=query, matched=None, preview="")

    sources = load_sources_index()
    matched = resolve_citation(text, sources=sources)
    if not matched:
        return KnowledgeCitationResponse(query=query, matched=None, preview="")

    preview = read_text_preview(matched.get("snapshot_path", ""), limit=600)
    return KnowledgeCitationResponse(query=query, matched=matched, preview=preview)
