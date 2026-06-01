from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from backend.schemas.citation import CitationDetailResponse, CitationMapResponse

router = APIRouter()

_OUTPUT_BASE = Path("outputs/assessment")


def _find_citation_map(task_id: str) -> dict | None:
    path = _OUTPUT_BASE / task_id / "outputs" / "citation_map.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


@router.get("/reports/{task_id}", response_model=CitationMapResponse)
def get_report_citations(task_id: str) -> CitationMapResponse:
    data = _find_citation_map(task_id)
    if data is None:
        return CitationMapResponse(task_id=task_id, footnote_map={}, citation_count=0)

    footnote_map_raw: dict = data.get("footnote_map", {})
    result: dict[str, CitationDetailResponse] = {}
    for num_str, item in footnote_map_raw.items():
        result[num_str] = CitationDetailResponse(
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
            footnote_number=int(num_str) if num_str.isdigit() else None,
        )

    return CitationMapResponse(
        task_id=task_id,
        footnote_map=result,
        citation_count=len(result),
    )


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
            # Find footnote number
            footnote_number: int | None = None
            for num_str, fn_item in data.get("footnote_map", {}).items():
                if fn_item.get("citation_id") == citation_id:
                    footnote_number = int(num_str) if num_str.isdigit() else None
                    break

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

    raise HTTPException(status_code=404, detail=f"Citation {citation_id} not found")
