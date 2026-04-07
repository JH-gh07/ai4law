from __future__ import annotations

import json
import re
import os
from datetime import datetime
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from backend.services.legal_api_service import DeliLegalService

_default_legal_service: object = None
_default_legal_service_loaded: bool = False


def _get_default_legal_service() -> object:
    """Return a lazily-created DeliLegalService singleton, or None if unavailable."""
    global _default_legal_service, _default_legal_service_loaded
    if _default_legal_service_loaded:
        return _default_legal_service
    _default_legal_service_loaded = True
    try:
        from backend.core.settings import get_settings
        from backend.services.legal_api_service import DeliLegalService
        _default_legal_service = DeliLegalService(get_settings())
    except Exception:
        _default_legal_service = None
    return _default_legal_service


@dataclass
class RegulationDoc:
    id: str
    title: str
    article: str
    content: str
    jurisdiction: str = ""
    path: str = ""
    doc_type: str = ""
    source_url: str = ""
    snapshot_path: str = ""
    usage_priority: str = "P1"
    keywords: tuple[str, ...] = field(default_factory=tuple)


ROOT = Path(__file__).resolve().parents[3]
NORMALIZED_JSONL = ROOT / "doc/knowledge/normalized/regulation_articles.jsonl"
RAG_LOG_DIR_ENV = "AI4LAW_RAG_LOG_DIR"
RAG_LOG_ENABLE_ENV = "AI4LAW_RAG_LOG"
DEFAULT_RAG_LOG_DIR = ROOT / "outputs/qa"
DEFAULT_SCORE_FLOOR_BY_MODE = {
    "vector": 4,
    "hybrid": 2,
    "lexical": 2,
}

JURISDICTION_STRONG_HINTS: dict[str, tuple[str, ...]] = {
    "cn": (
        "数据出境",
        "网信",
        "个人信息保护法",
        "数据安全法",
        "网络安全法",
        "标准合同",
        "个人信息出境",
        "pipia",
    ),
    "eu": (
        "gdpr",
        "edpb",
        "bcr",
        "dpia",
        "transfer impact assessment",
        "tia",
        "article 35",
        "article 47",
    ),
    "us": (
        "cpra",
        "ccpa",
        "california",
        "eo 14117",
        "covered person",
        "restricted transactions",
    ),
}

PATH_STRONG_HINTS: dict[str, tuple[str, ...]] = {
    "scc": ("标准合同", "scc", "pipia"),
    "assessment": ("安全评估", "security assessment"),
    "bcr": ("bcr", "约束性公司规则"),
    "dpia": ("dpia", "data protection impact assessment", "article 35"),
    "tia": ("tia", "transfer impact assessment", "edpb"),
    "cpra": ("cpra", "ccpa", "california"),
    "cn_flow": ("cn flow", "中国数据流转", "回流", "本地化"),
}

OFF_TOPIC_HINTS: tuple[str, ...] = (
    "火锅",
    "天气",
    "python",
    "docker",
    "mysql",
    "nginx",
    "laptop",
    "battery",
    "steak",
    "cake",
    "macbook",
    "爬虫",
)


LEGACY_DB = [
    RegulationDoc(
        id="pipl-40",
        title="个人信息保护法",
        article="第40条",
        content="关键信息基础设施运营者和处理个人信息达到国家网信部门规定数量的处理者，应当通过国家网信部门组织的安全评估。",
        jurisdiction="cn",
        path="assessment",
        doc_type="law",
        usage_priority="P0",
    ),
    RegulationDoc(
        id="dsl-21",
        title="数据安全法",
        article="第21条",
        content="国家建立数据分类分级保护制度，对重要数据实行重点保护。",
        jurisdiction="cn",
        path="all",
        doc_type="law",
        usage_priority="P0",
    ),
    RegulationDoc(
        id="scc-measures-7",
        title="个人信息出境标准合同办法",
        article="第7条",
        content="个人信息处理者向境外提供个人信息前，应开展个人信息保护影响评估。",
        jurisdiction="cn",
        path="scc",
        doc_type="administrative_regulation",
        usage_priority="P0",
    ),
    RegulationDoc(
        id="security-assessment-measures-4",
        title="数据出境安全评估办法",
        article="第4条",
        content="数据处理者向境外提供重要数据或者达到个人信息数量门槛的，应当申报数据出境安全评估。",
        jurisdiction="cn",
        path="assessment",
        doc_type="administrative_regulation",
        usage_priority="P0",
    ),
    RegulationDoc(
        id="gbt-46068",
        title="GB/T 46068-2025",
        article="通则",
        content="规定个人信息跨境处理活动的认证框架与要求。",
        jurisdiction="cn",
        path="scc",
        doc_type="guide",
        usage_priority="P1",
    ),
]


def _normalize(text: str) -> str:
    lowered = (text or "").lower()
    lowered = lowered.replace("（", "(").replace("）", ")")
    return re.sub(r"\s+", "", lowered)


def _char_bigrams(text: str) -> set[str]:
    value = _normalize(text)
    if len(value) < 2:
        return set()
    return {value[idx : idx + 2] for idx in range(len(value) - 1)}


def _extract_law_hint(query: str) -> str:
    value = query.strip()
    value = re.sub(r"第[一二三四五六七八九十百千万零〇0-9]{1,10}条", "", value)
    value = re.sub(r"[：:，,。；;（）()\\[\\]\\s]", "", value)
    return value


def _extract_article_hint(query: str) -> Optional[str]:
    match = re.search(r"第[一二三四五六七八九十百千万零〇0-9]{1,10}条", query)
    if not match:
        return None
    return match.group(0)


def _cn_num_to_int(value: str) -> Optional[int]:
    value = value.strip()
    if not value:
        return None
    if value.isdigit():
        return int(value)

    chars = value.replace("零", "〇")
    num_map = {"〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}

    if chars == "十":
        return 10
    if "十" in chars:
        left, right = chars.split("十", 1)
        tens = num_map.get(left, 1 if left == "" else -1)
        ones = num_map.get(right, 0 if right == "" else -1)
        if tens < 0 or ones < 0:
            return None
        return tens * 10 + ones

    total = 0
    for ch in chars:
        if ch not in num_map:
            return None
        total = total * 10 + num_map[ch]
    return total


def _rewrite_query(query: str, jurisdiction: Optional[str], path: Optional[str]) -> str:
    """Append strong hints to improve lexical match for sparse CN queries."""
    value = query or ""
    additions: list[str] = []

    if jurisdiction:
        for hint in JURISDICTION_STRONG_HINTS.get(jurisdiction, ()):
            if hint.lower() not in value.lower():
                additions.append(hint)

    if path:
        for hint in PATH_STRONG_HINTS.get(path, ()):
            if hint.lower() not in value.lower():
                additions.append(hint)

    if not additions:
        return value
    return f"{value} {' '.join(additions)}"


def _article_number(article_ref: str) -> Optional[int]:
    match = re.search(r"第([一二三四五六七八九十百千万零〇0-9]{1,10})条", article_ref)
    if not match:
        return None
    return _cn_num_to_int(match.group(1))


def _split_paths(raw_path: str) -> set[str]:
    return {part.strip() for part in raw_path.split("|") if part.strip()}


def _priority_weight(priority: str) -> int:
    mapping = {"P0": 3, "P1": 2, "P2": 1}
    return mapping.get(priority or "", 0)


def _contains_any_hint(query_l: str, hints: tuple[str, ...]) -> bool:
    for hint in hints:
        if hint.lower() in query_l:
            return True
    return False


def _is_off_topic_query(query: str) -> bool:
    query_l = query.lower()
    return _contains_any_hint(query_l, OFF_TOPIC_HINTS)


def _is_jurisdiction_mismatch(query: str, jurisdiction: Optional[str]) -> bool:
    if not jurisdiction:
        return False
    query_l = query.lower()
    matched: set[str] = set()
    for j, hints in JURISDICTION_STRONG_HINTS.items():
        if _contains_any_hint(query_l, hints):
            matched.add(j)
    if not matched:
        return False
    return jurisdiction.lower() not in matched


def _is_path_mismatch(query: str, path: Optional[str]) -> bool:
    if not path or path in {"all", "diagnosis", "general", "review"}:
        return False
    query_l = query.lower()
    matched_paths = {p for p, hints in PATH_STRONG_HINTS.items() if _contains_any_hint(query_l, hints)}
    if not matched_paths:
        return False
    return path not in matched_paths


@lru_cache(maxsize=1)
def _load_normalized_docs() -> list[RegulationDoc]:
    if not NORMALIZED_JSONL.exists():
        return []

    docs: list[RegulationDoc] = []
    with NORMALIZED_JSONL.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue

            docs.append(
                RegulationDoc(
                    id=str(row.get("article_id", "")),
                    title=str(row.get("law_name", "")),
                    article=str(row.get("article_ref", "通则")),
                    content=str(row.get("content", "")),
                    jurisdiction=str(row.get("jurisdiction", "")),
                    path=str(row.get("path", "")),
                    doc_type=str(row.get("doc_type", "")),
                    source_url=str(row.get("source_url", "")),
                    snapshot_path=str(row.get("snapshot_path", "")),
                    usage_priority=str(row.get("usage_priority", "P1")),
                    keywords=tuple(str(k) for k in row.get("keywords", []) if str(k).strip()),
                )
            )
    return docs


def _lexical_score(query: str, doc: RegulationDoc) -> int:
    query_n = _normalize(query)
    if not query_n:
        return 0

    title_n = _normalize(doc.title)
    article_n = _normalize(doc.article)
    content_n = _normalize(doc.content)

    score = 0

    law_hint = _extract_law_hint(query)
    article_hint = _extract_article_hint(query)

    if law_hint:
        law_hint_n = _normalize(law_hint)
        if law_hint_n and law_hint_n in title_n:
            score += 30
        elif law_hint_n:
            score -= 8

    if article_hint:
        expected_no = _article_number(article_hint)
        doc_no = _article_number(doc.article)
        if expected_no is not None and doc_no is not None:
            if expected_no == doc_no:
                score += 18
            else:
                score -= 5

    if title_n and title_n in query_n:
        score += 14
    if article_n and article_n in query_n:
        score += 4
    if query_n and query_n in content_n:
        score += 8

    return score


def _semantic_score(query: str, doc: RegulationDoc) -> int:
    query_n = _normalize(query)
    if not query_n:
        return 0

    query_pairs = _char_bigrams(query_n)
    doc_pairs = _char_bigrams(f"{doc.title}{doc.article}{doc.content[:800]}")
    overlap = len(query_pairs & doc_pairs)

    score = min(overlap, 20)

    if doc.keywords:
        keyword_overlap = sum(1 for kw in doc.keywords if _normalize(kw) and _normalize(kw) in query_n)
        score += min(keyword_overlap * 2, 10)

    return score


def _score_doc(query: str, doc: RegulationDoc, mode: str = "hybrid") -> int:
    lexical = _lexical_score(query, doc)
    semantic = _semantic_score(query, doc)

    if mode == "vector":
        base = semantic
    elif mode == "lexical":
        base = lexical
    else:
        # Weighted merge for production default.
        base = int(semantic * 0.65 + lexical * 0.35)

    return base + _priority_weight(doc.usage_priority)


def _passes_filter(
    doc: RegulationDoc,
    jurisdiction: Optional[str],
    path: Optional[str],
    doc_type: Optional[str],
) -> bool:
    if jurisdiction and doc.jurisdiction and _normalize(doc.jurisdiction) != _normalize(jurisdiction):
        return False

    if path:
        doc_paths = _split_paths(doc.path)
        if doc_paths and "all" not in doc_paths and path not in doc_paths:
            return False

    if doc_type and doc.doc_type and _normalize(doc_type) not in _normalize(doc.doc_type):
        return False

    return True


def retrieve_regulations(
    query: str,
    top_k: int = 8,
    jurisdiction: Optional[str] = None,
    path: Optional[str] = None,
    doc_type: Optional[str] = None,
    mode: str = "hybrid",
    score_floor: Optional[int] = None,
    legal_service: Optional["DeliLegalService"] = None,
    min_local: int = 3,
) -> list[RegulationDoc]:
    rewritten_query = _rewrite_query(query, jurisdiction, path)
    if _is_off_topic_query(rewritten_query):
        return []
    if _is_jurisdiction_mismatch(rewritten_query, jurisdiction):
        return []
    if _is_path_mismatch(rewritten_query, path):
        return []

    docs = _load_normalized_docs() or LEGACY_DB
    effective_floor = score_floor
    if effective_floor is None:
        effective_floor = DEFAULT_SCORE_FLOOR_BY_MODE.get(mode, 1)

    scored: list[tuple[int, RegulationDoc]] = []
    for doc in docs:
        if not _passes_filter(doc, jurisdiction=jurisdiction, path=path, doc_type=doc_type):
            continue
        score = _score_doc(rewritten_query, doc, mode=mode)
        if score >= effective_floor:
            scored.append((score, doc))

    scored.sort(key=lambda item: (item[0], _priority_weight(item[1].usage_priority)), reverse=True)

    deduped: list[RegulationDoc] = []
    seen_titles: set[str] = set()
    for _, doc in scored:
        title_key = _normalize(doc.title)
        identity_key = f"{title_key}:{_normalize(doc.article)}"
        if identity_key in seen_titles:
            continue
        seen_titles.add(identity_key)
        deduped.append(doc)
        if len(deduped) >= top_k:
            break

    # Supplement with DeliLegal law search when local results are sparse
    effective_legal_service = legal_service if legal_service is not None else _get_default_legal_service()
    if effective_legal_service and effective_legal_service.enabled and len(deduped) < min_local:
        needed = top_k - len(deduped)
        existing_titles = {_normalize(d.title) for d in deduped}
        remote_hits = effective_legal_service.search_laws(query, size=needed + 2)
        for hit in remote_hits:
            title = hit.get("title", "")
            if _normalize(title) in existing_titles:
                continue
            deduped.append(
                RegulationDoc(
                    id=f"delilegal-{_normalize(title)[:20]}",
                    title=title,
                    article="",
                    content=hit.get("summary", ""),
                    jurisdiction=jurisdiction or "",
                    path=path or "all",
                    doc_type="external",
                    usage_priority="P2",
                )
            )
            existing_titles.add(_normalize(title))
            if len(deduped) >= top_k:
                break

    _log_rag_hits(
        query=query,
        rewritten_query=rewritten_query,
        jurisdiction=jurisdiction,
        path=path,
        doc_type=doc_type,
        mode=mode,
        score_floor=effective_floor,
        top_k=top_k,
        results=deduped,
    )

    return deduped


def _log_rag_hits(
    query: str,
    rewritten_query: str,
    jurisdiction: Optional[str],
    path: Optional[str],
    doc_type: Optional[str],
    mode: str,
    score_floor: Optional[int],
    top_k: int,
    results: list[RegulationDoc],
) -> None:
    enabled_flag = os.getenv(RAG_LOG_ENABLE_ENV, "").strip().lower()
    log_dir_value = os.getenv(RAG_LOG_DIR_ENV, "").strip()
    if enabled_flag not in {"1", "true", "yes"} and not log_dir_value:
        return

    log_dir = Path(log_dir_value) if log_dir_value else DEFAULT_RAG_LOG_DIR
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"rag_hits_{timestamp}.jsonl"

    payload = {
        "ts": datetime.now().isoformat(),
        "query": query,
        "rewritten_query": rewritten_query,
        "jurisdiction": jurisdiction,
        "path": path,
        "doc_type": doc_type,
        "mode": mode,
        "score_floor": score_floor,
        "top_k": top_k,
        "hit_count": len(results),
        "hits": [
            {
                "id": doc.id,
                "title": doc.title,
                "article": doc.article,
                "content": doc.content[:200],
                "jurisdiction": doc.jurisdiction,
                "path": doc.path,
                "doc_type": doc.doc_type,
                "source_url": doc.source_url,
                "snapshot_path": doc.snapshot_path,
                "usage_priority": doc.usage_priority,
                "score": _score_doc(rewritten_query, doc, mode=mode),
            }
            for doc in results
        ],
    }
    try:
        with log_path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError:
        return
