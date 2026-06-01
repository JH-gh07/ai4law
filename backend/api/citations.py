from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.schemas.citation import CitationDetailResponse, CitationMapResponse

router = APIRouter()

_OUTPUT_BASE = Path("outputs/assessment")


class BatchCitationRequest(BaseModel):
    citation_ids: list[str]
    task_id: str


class BatchCitationResponse(BaseModel):
    items: dict[str, CitationDetailResponse]
    not_found: list[str]


def _find_citation_map(task_id: str) -> dict | None:
    path = _OUTPUT_BASE / task_id / "outputs" / "citation_map.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _build_detail(item: dict, footnote_number: int | None = None) -> CitationDetailResponse:
    return CitationDetailResponse(
        citation_id=item.get("citation_id", ""),
        source_id=item.get("source_id", ""),
        citation_type=item.get("citation_type", "law_article"),
        title=item.get("title", ""),
        article_no=item.get("article_no", ""),
        quote_text=item.get("quote_text", ""),
        authority_level=item.get("authority_level", "medium"),
        binding_force=item.get("binding_force", "recommended"),
        related_issue_ids=item.get("related_issue_ids", []),
        related_fact_ids=item.get("related_fact_ids", []),
        related_evidence_ids=item.get("related_evidence_ids", []),
        confidence_score=item.get("confidence_score", 0.0),
        footnote_number=footnote_number,
    )


@router.get("/reports/{task_id}", response_model=CitationMapResponse)
def get_report_citations(task_id: str) -> CitationMapResponse:
    data = _find_citation_map(task_id)
    if data is None:
        return CitationMapResponse(task_id=task_id, footnote_map={}, citation_count=0)

    footnote_map_raw: dict = data.get("footnote_map", {})
    result: dict[str, CitationDetailResponse] = {}
    for num_str, item in footnote_map_raw.items():
        result[num_str] = _build_detail(
            item,
            footnote_number=int(num_str) if num_str.isdigit() else None,
        )

    return CitationMapResponse(
        task_id=task_id,
        footnote_map=result,
        citation_count=len(result),
    )


@router.post("/batch", response_model=BatchCitationResponse)
def get_citations_batch(body: BatchCitationRequest) -> BatchCitationResponse:
    """Fetch multiple citation details in a single request."""
    data = _find_citation_map(body.task_id)
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
            result[cid] = _build_detail(item, footnote_number=id_to_footnote.get(cid))

    return BatchCitationResponse(items=result, not_found=not_found)


@router.get("/{citation_id}", response_model=CitationDetailResponse)
def get_citation_detail(citation_id: str, task_id: Optional[str] = Query(None)) -> CitationDetailResponse:
    if not task_id:
        raise HTTPException(status_code=400, detail="task_id query parameter is required")

    data = _find_citation_map(task_id)
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
            return _build_detail(item, footnote_number=footnote_number)

    raise HTTPException(status_code=404, detail=f"Citation {citation_id} not found")
