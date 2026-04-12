from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path
from datetime import datetime, timezone

SOURCES_CSV = Path("doc/knowledge/index/sources.csv")
CASES_CSV = Path("doc/knowledge/index/practice_cases.csv")


@lru_cache(maxsize=4)
def _load_csv(path: str) -> list[dict[str, str]]:
    csv_path = Path(path)
    if not csv_path.exists():
        return []

    with open(csv_path, "r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        return [dict(row) for row in reader]


def load_sources_index() -> list[dict[str, str]]:
    return _load_csv(str(SOURCES_CSV))


def load_practice_cases() -> list[dict[str, str]]:
    return _load_csv(str(CASES_CSV))


def refresh_knowledge_cache() -> None:
    _load_csv.cache_clear()


def get_knowledge_sync_meta(*, cache_refreshed: bool) -> dict[str, str | bool]:
    source_exists = SOURCES_CSV.exists()
    case_exists = CASES_CSV.exists()
    source_mtime = (
        datetime.fromtimestamp(SOURCES_CSV.stat().st_mtime, tz=timezone.utc).isoformat()
        if source_exists
        else ""
    )
    case_mtime = (
        datetime.fromtimestamp(CASES_CSV.stat().st_mtime, tz=timezone.utc).isoformat()
        if case_exists
        else ""
    )
    return {
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "cache_refreshed": cache_refreshed,
        "sources_csv_path": str(SOURCES_CSV),
        "cases_csv_path": str(CASES_CSV),
        "sources_csv_exists": source_exists,
        "cases_csv_exists": case_exists,
        "sources_csv_mtime": source_mtime,
        "cases_csv_mtime": case_mtime,
    }


def _normalize(text: str) -> str:
    text = text or ""
    text = text.lower()
    text = text.replace("（", "(").replace("）", ")")
    return re.sub(r"\s+", "", text)


def _extract_law_name(citation: str) -> str:
    match = re.split(r"第\d+条|通则|article\s*\d+", citation, maxsplit=1, flags=re.IGNORECASE)
    if match:
        return match[0].strip()
    return citation.strip()


def resolve_citation(citation: str, sources: list[dict[str, str]] | None = None) -> dict[str, str] | None:
    if not citation.strip():
        return None

    rows = sources if sources is not None else load_sources_index()
    if not rows:
        return None

    citation_n = _normalize(citation)
    citation_law = _normalize(_extract_law_name(citation))

    scored: list[tuple[int, dict[str, str]]] = []

    for row in rows:
        title = row.get("title", "")
        title_n = _normalize(title)

        score = 0
        textual_match = False
        if title_n and title_n in citation_n:
            score += 4
            textual_match = True
        if citation_law and citation_law in title_n:
            score += 3
            textual_match = True

        if not textual_match:
            continue

        doc_type = _normalize(row.get("doc_type", ""))
        if "law" in doc_type or "administrative_regulation" in doc_type:
            score += 1

        priority = row.get("usage_priority", "")
        if priority == "P0":
            score += 1

        if score > 0:
            scored.append((score, row))

    if not scored:
        return None

    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1]


def get_report_records(output_root: str = "outputs") -> list[dict[str, str]]:
    root = Path(output_root)
    if not root.exists():
        return []

    records: list[dict[str, str]] = []
    for module_dir in sorted([path for path in root.iterdir() if path.is_dir()]):
        for file_path in sorted(module_dir.glob("*")):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in {".md", ".docx"}:
                continue
            records.append(
                {
                    "module": module_dir.name,
                    "filename": file_path.name,
                    "ext": file_path.suffix.lower(),
                    "path": str(file_path),
                    "mtime": str(int(file_path.stat().st_mtime)),
                }
            )
    return records


def read_text_preview(path: str, limit: int = 1200) -> str:
    file_path = Path(path)
    if not file_path.exists():
        return ""

    content = file_path.read_text(encoding="utf-8", errors="ignore")
    content = re.sub(r"<[^>]+>", " ", content)
    content = re.sub(r"\s+", " ", content).strip()
    return content[:limit]
