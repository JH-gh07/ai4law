from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.common.citation.output import normalize_citation_item
from backend.core.dependencies import get_current_user, get_db
from backend.schemas.auth import AuthUser
from backend.schemas.citation import CitationDetailResponse, CitationMapResponse
from backend.services.task_access import require_task_access

router = APIRouter()

_KNOWN_MODULES = (
    "assessment",
    "dpia",
    "cn_flow",
    "eu_scc",
    "us_14117",
    "pipia",
    "tia",
    "bcr",
    "cpra",
)


class BatchCitationRequest(BaseModel):
    citation_ids: list[str]
    task_id: str
    module: str | None = None


class BatchCitationResponse(BaseModel):
    items: dict[str, CitationDetailResponse]
    not_found: list[str]


def _candidate_paths(task_id: str, module: str | None) -> list[tuple[str, Path]]:
    modules = [module] if module else list(_KNOWN_MODULES)
    candidates: list[tuple[str, Path]] = []
    for item in modules:
        if not item:
            continue
        path = Path("outputs") / item / task_id / "outputs" / "citation_map.json"
        candidates.append((item, path))
    return candidates


def _find_citation_map(task_id: str, module: str | None = None) -> tuple[str, dict] | tuple[None, None]:
    for resolved_module, path in _candidate_paths(task_id, module):
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        return resolved_module, data
    return None, None


def _build_detail(item: dict, *, module: str, footnote_number: int | None = None) -> CitationDetailResponse:
    normalized = normalize_citation_item(item, module=module)
    return CitationDetailResponse(
        citation_id=normalized.get("citation_id", ""),
        module=normalized.get("module", module),
        source_id=normalized.get("source_id", ""),
        jurisdiction=normalized.get("jurisdiction", ""),
        display_label=normalized.get("display_label", ""),
        citation_type=normalized.get("citation_type", "law_article"),
        title=normalized.get("title", ""),
        article_no=normalized.get("article_no", ""),
        quote_text=normalized.get("quote_text", ""),
        authority_level=normalized.get("authority_level", "medium"),
        binding_force=normalized.get("binding_force", "recommended"),
        related_issue_ids=normalized.get("related_issue_ids", []),
        related_fact_ids=normalized.get("related_fact_ids", []),
        related_evidence_ids=normalized.get("related_evidence_ids", []),
        confidence_score=normalized.get("confidence_score", 0.0),
        footnote_number=footnote_number,
        source_kind=normalized.get("source_kind", "law_article"),
        allowed_usage=normalized.get("allowed_usage", []),
        can_enter_external_report=normalized.get("can_enter_external_report", True),
        external_report_allowed=normalized.get("external_report_allowed", True),
        confidence_threshold=normalized.get("confidence_threshold", 0.20),
        knowledge_url=normalized.get("knowledge_url", ""),
        anchor=normalized.get("anchor", ""),
        section_id=normalized.get("section_id", ""),
        clause_id=normalized.get("clause_id", ""),
        open_mode=normalized.get("open_mode", "in_app"),
        can_jump=normalized.get("can_jump", False),
        source_url=normalized.get("source_url", ""),
        resolution=normalized.get("resolution", {}),
    )


@router.get("/reports/{task_id}", response_model=CitationMapResponse)
def get_report_citations(
    task_id: str,
    module: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
) -> CitationMapResponse:
    require_task_access(db, task_id=task_id, user_id=current_user.id)
    resolved_module, data = _find_citation_map(task_id, module)
    target_module = resolved_module or module or ""
    if data is None:
        return CitationMapResponse(task_id=task_id, module=target_module, footnote_map={}, citation_count=0)

    footnote_map_raw: dict = data.get("footnote_map", {})

    result: dict[str, CitationDetailResponse] = {}
    for num_str, item in footnote_map_raw.items():
        result[num_str] = _build_detail(
            item,
            module=resolved_module or module or str(data.get("module", "")),
            footnote_number=int(num_str) if num_str.isdigit() else None,
        )

    return CitationMapResponse(
        task_id=task_id,
        module=resolved_module or module or str(data.get("module", "")),
        footnote_map=result,
        citation_count=len(result),
    )


@router.post("/batch", response_model=BatchCitationResponse)
def get_citations_batch(
    body: BatchCitationRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
) -> BatchCitationResponse:
    """Fetch multiple citation details in a single request."""
    require_task_access(db, task_id=body.task_id, user_id=current_user.id)
    resolved_module, data = _find_citation_map(body.task_id, body.module)
    if data is None:
        return BatchCitationResponse(items={}, not_found=list(body.citation_ids))

    all_items: list[dict] = data.get("all_items", [])
    items_by_id: dict[str, dict] = {item.get("citation_id", ""): item for item in all_items}

    # Build footnote number lookup
    id_to_footnote: dict[str, int] = {}
    for num_str, fn_item in data.get("footnote_map", {}).items():
        cid = fn_item.get("citation_id", "")
        if cid and num_str.isdigit():
            id_to_footnote[cid] = int(num_str)

    result: dict[str, CitationDetailResponse] = {}
    not_found: list[str] = []

    for cid in body.citation_ids:
        item = items_by_id.get(cid)
        if item is None:
            not_found.append(cid)
        else:
            result[cid] = _build_detail(
                item,
                module=resolved_module or body.module or str(data.get("module", "")),
                footnote_number=id_to_footnote.get(cid),
            )

    return BatchCitationResponse(items=result, not_found=not_found)


@router.get("/{citation_id}", response_model=CitationDetailResponse)
def get_citation_detail(
    citation_id: str,
    task_id: Optional[str] = Query(None),
    module: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
) -> CitationDetailResponse:
    if not task_id:
        raise HTTPException(status_code=400, detail="task_id query parameter is required")
    require_task_access(db, task_id=task_id, user_id=current_user.id)

    resolved_module, data = _find_citation_map(task_id, module)
    if data is None:
        raise HTTPException(status_code=404, detail=f"No citation map found for task {task_id}")

    all_items: list[dict] = data.get("all_items", [])
    for item in all_items:
        if item.get("citation_id") == citation_id:
            footnote_number: int | None = None
            for num_str, fn_item in data.get("footnote_map", {}).items():
                if fn_item.get("citation_id") == citation_id:
                    footnote_number = int(num_str) if num_str.isdigit() else None
                    break
            return _build_detail(
                item,
                module=resolved_module or module or str(data.get("module", "")),
                footnote_number=footnote_number,
            )

    raise HTTPException(status_code=404, detail=f"Citation {citation_id} not found")
