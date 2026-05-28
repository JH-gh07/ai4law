from __future__ import annotations

import csv
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES_CSV = ROOT / "doc/knowledge/index/sources.csv"
CASES_CSV = ROOT / "doc/knowledge/index/practice_cases.csv"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mtime_iso(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    except FileNotFoundError:
        return ""


def get_knowledge_sync_meta(*, cache_refreshed: bool) -> dict[str, object]:
    return {
        "synced_at": _now_iso(),
        "cache_refreshed": cache_refreshed,
        "sources_csv_path": str(SOURCES_CSV),
        "cases_csv_path": str(CASES_CSV),
        "sources_csv_exists": SOURCES_CSV.exists(),
        "cases_csv_exists": CASES_CSV.exists(),
        "sources_csv_mtime": _mtime_iso(SOURCES_CSV),
        "cases_csv_mtime": _mtime_iso(CASES_CSV),
    }


def refresh_knowledge_cache() -> None:
    _load_sources_index.cache_clear()
    _load_practice_cases.cache_clear()


def load_sources_index() -> list[dict[str, str]]:
    return list(_load_sources_index())


def load_practice_cases() -> list[dict[str, str]]:
    return list(_load_practice_cases())


@lru_cache(maxsize=1)
def _load_sources_index() -> tuple[dict[str, str], ...]:
    if not SOURCES_CSV.exists():
        return ()
    with SOURCES_CSV.open("r", encoding="utf-8", newline="") as fp:
        return tuple({k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(fp))


@lru_cache(maxsize=1)
def _load_practice_cases() -> tuple[dict[str, str], ...]:
    if not CASES_CSV.exists():
        return ()
    with CASES_CSV.open("r", encoding="utf-8", newline="") as fp:
        return tuple({k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(fp))


def read_text_preview(snapshot_path: str, *, limit: int = 600) -> str:
    raw = (snapshot_path or "").strip()
    if not raw:
        return ""
    path = Path(raw)
    if not path.is_absolute():
        path = (ROOT / path).resolve()
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        return ""
    return (text[: max(0, limit)]).replace("\r\n", "\n").replace("\r", "\n")


def resolve_citation(query: str, *, sources: list[dict[str, str]]) -> dict[str, str] | None:
    """Best-effort citation resolver for the Knowledge Center UI.

    This endpoint is primarily for mapping a free-form citation string back to a row
    in `sources.csv`. It intentionally stays lightweight and local.
    """
    text = (query or "").strip()
    if not text:
        return None

    lowered = text.lower()
    for row in sources:
        source_id = (row.get("source_id") or "").strip()
        title = (row.get("title") or "").strip()
        if source_id and source_id.lower() in lowered:
            return row
        if title and title.lower() in lowered:
            return row
    return None

