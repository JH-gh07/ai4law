from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from backend.common.knowledge.registry import ROOT, ensure_source_registry
from backend.common.knowledge.v2 import KnowledgeChunkV2, SourceRegistryEntry
from backend.common.rag.embedding import HashingEmbedder, normalize_text, tokenize_text
from backend.common.rag.vector_store import LocalVectorStore, VectorIndexEntry
from backend.core.settings import get_settings
from backend.services.knowledge_index import load_practice_cases, read_text_preview

RAG_V3_DIR = ROOT / "storage" / "rag" / "v3"


_CATEGORY_LABELS = {
    ("L1_regulatory_evidence", "law_article"): "法规依据",
    ("L1_regulatory_evidence", "official_guide"): "官方指南",
    ("L1_regulatory_evidence", "standard_clause"): "标准条款",
    ("L2_business_rule", "workflow_rule"): "适用说明",
    ("L3_testcase", "testcase"): "典型案例",
    ("L4_template", "template_slot"): "官方模板",
}

_JURISDICTION_LABELS = {
    "cn": "中国",
    "eu": "欧盟",
    "us": "美国",
}

_AUTHORITY_LABELS = {
    "high": "高权威",
    "medium": "中权威",
    "low": "参考信息",
}

_BINDING_LABELS = {
    "mandatory": "强制要求",
    "recommended": "官方建议",
    "reference": "参考说明",
}

_USAGE_LABELS = {
    "external_report": "可作为正式依据",
    "legal_grounding": "可用于法律依据",
    "internal_review": "可用于内部研判",
    "structure_control": "可用于正式结构",
    "internal_drafting": "仅供起草参考",
    "few_shot": "仅供评测参考",
    "evaluator": "仅供评测参考",
    "risk_explanation": "可用于风险说明",
}


def _vector_index_path(index_name: str) -> Path:
    return RAG_V3_DIR / f"{index_name}.vector.json"


def _iter_chunk_files() -> list[Path]:
    if not RAG_V3_DIR.exists():
        return []
    return sorted(RAG_V3_DIR.glob("*.jsonl"))


def _load_all_chunks() -> list[KnowledgeChunkV2]:
    chunks: list[KnowledgeChunkV2] = []
    for path in _iter_chunk_files():
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                chunks.append(KnowledgeChunkV2.model_validate(json.loads(line)))
    return chunks


def _category_for_chunk(chunk: KnowledgeChunkV2) -> str:
    if chunk.layer == "L4_template":
        return "官方模板" if chunk.template_type == "official_template" else "参考模板"
    return _CATEGORY_LABELS.get((chunk.layer, str(chunk.source_kind)), "知识条目")


def _jurisdiction_label(value: str) -> str:
    return _JURISDICTION_LABELS.get(value, value.upper() if value else "未标注")


def _authority_label(value: str) -> str:
    return _AUTHORITY_LABELS.get(value, "参考信息")


def _binding_label(value: str) -> str:
    return _BINDING_LABELS.get(value, "参考说明")


def _usage_labels(usages: list[str]) -> list[str]:
    labels: list[str] = []
    for item in usages:
        label = _USAGE_LABELS.get(item)
        if label and label not in labels:
            labels.append(label)
    return labels


def _search_text(chunk: KnowledgeChunkV2) -> str:
    return " ".join(
        [
            chunk.title,
            chunk.content,
            chunk.citation_anchor,
            " ".join(chunk.reference_ids),
            " ".join(chunk.scenario_tags),
            " ".join(chunk.keywords),
        ]
    ).strip()


def _lexical_score(query: str, chunk: KnowledgeChunkV2) -> float:
    query_n = normalize_text(query)
    if not query_n:
        return 0.0
    body = normalize_text(" ".join([chunk.title, chunk.citation_anchor, chunk.content, " ".join(chunk.keywords)]))
    score = 0.0
    if query_n in body or body[:80] in query_n:
        score += 3.0
    overlap = 0
    for token in set(tokenize_text(query)):
        if token and token in body:
            overlap += 1
    score += min(overlap * 0.35, 4.0)
    return score


def _status_label(status: str, is_current_version: bool = True) -> str:
    if not status:
        return "状态待确认"
    if status == "effective" and is_current_version:
        return "现行有效"
    if status == "effective":
        return "有效但非当前版本"
    if status == "repealed":
        return "已失效"
    return status


def _summarize_source(
    entry: SourceRegistryEntry,
    chunks: list[KnowledgeChunkV2],
) -> dict[str, str]:
    first_chunk = chunks[0] if chunks else None
    metadata = dict(entry.metadata or {})
    category = _category_for_chunk(first_chunk) if first_chunk else "知识条目"
    category = str(metadata.get("category") or category)
    scenario_text = "、".join(sorted({_scenario_label(chunk) for chunk in chunks if _scenario_label(chunk)}))
    scenario_text = str(metadata.get("suitable_for") or scenario_text)
    usage_text = "、".join(_usage_labels([str(item) for item in entry.allowed_usage]))
    usage_text = str(metadata.get("usage") or usage_text)
    article_count = sum(1 for chunk in chunks if chunk.article_no)
    template_hint = ""
    if first_chunk and first_chunk.layer == "L4_template":
        template_hint = "用于正式文档结构组织。" if first_chunk.template_type == "official_template" else "用于内部起草参考。"
    description = (
        metadata.get("summary")
        or metadata.get("description")
        or metadata.get("notes")
        or first_chunk.content[:120] if first_chunk and first_chunk.content else ""
    )
    return {
        "source_id": entry.source_id,
        "title": entry.title,
        "category": category,
        "jurisdiction": _jurisdiction_label(entry.jurisdiction),
        "jurisdiction_code": entry.jurisdiction,
        "authority": _authority_label(entry.authority_level),
        "authority_level": entry.authority_level,
        "binding_force": _binding_label(entry.binding_force),
        "binding_force_code": entry.binding_force,
        "status": _status_label(entry.status, entry.is_current_version),
        "status_code": entry.status,
        "publisher": str(metadata.get("publisher") or metadata.get("source_org") or ""),
        "source_org": str(metadata.get("source_org") or ""),
        "publish_date": str(metadata.get("publish_date") or ""),
        "effective_date": str(metadata.get("effective_date") or ""),
        "source_url": str(metadata.get("source_url") or ""),
        "url": str(metadata.get("source_url") or ""),
        "snapshot_path": str(metadata.get("snapshot_path") or ""),
        "module": str(metadata.get("module") or ""),
        "knowledge_url": str(metadata.get("knowledge_url") or ""),
        "suitable_for": scenario_text or "通用参考",
        "usage": usage_text or ("可作为正式依据" if entry.can_be_cited else "仅供内部参考"),
        "report_usage": str(metadata.get("report_usage") or ("可直接用于正式报告" if entry.can_enter_external_report else "不直接写入正式报告")),
        "summary": (description or template_hint or entry.title)[:180],
        "highlights": f"{article_count} 个重点条文" if article_count else template_hint or "查看详情了解适用方式",
        "doc_type": str(metadata.get("doc_type") or ""),
        "notes": (description or template_hint or entry.title)[:180],
        "layer": entry.layer,
        "path": str(metadata.get("path") or ""),
    }


def _scenario_label(chunk: KnowledgeChunkV2) -> str:
    tags = list(chunk.scenario_tags or [])
    if "assessment" in tags:
        return "评估申报"
    if "review" in tags:
        return "文档审查"
    if "scc_contract" in tags:
        return "标准合同"
    if "privacy_policy" in tags:
        return "隐私政策"
    if "dpa" in tags:
        return "数据处理协议"
    return ""


def build_user_source_catalog() -> list[dict[str, str]]:
    registry_entries = ensure_source_registry()
    chunks = _load_all_chunks()
    by_source: dict[str, list[KnowledgeChunkV2]] = defaultdict(list)
    for chunk in chunks:
        by_source[chunk.source_id].append(chunk)
    rows = [_summarize_source(entry, by_source.get(entry.source_id, [])) for entry in registry_entries]
    rows.sort(key=lambda item: (item["jurisdiction"], item["category"], item["title"]))
    return rows


def build_user_case_catalog() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for raw in load_practice_cases():
        expected_modules = [item.strip() for item in raw.get("expected_module", "").split("|") if item.strip()]
        scenario_labels: list[str] = []
        for module in expected_modules:
            if "assessment" in module:
                scenario_labels.append("评估申报")
            elif "review" in module or module in {"scc", "bcr"}:
                scenario_labels.append("文档审查")
            elif "diagnosis" in module:
                scenario_labels.append("路径判断")
        rows.append(
            {
                "case_id": raw.get("case_id", ""),
                "title": raw.get("case_title", ""),
                "case_title": raw.get("case_title", ""),
                "category": raw.get("category", "") or "典型案例",
                "jurisdiction": _jurisdiction_label(raw.get("jurisdiction", "").split("-")[0]),
                "jurisdiction_code": raw.get("jurisdiction", "").split("-")[0],
                "publisher": raw.get("publisher", "") or raw.get("source_org", ""),
                "source_org": raw.get("source_org", ""),
                "publish_date": raw.get("publish_date", ""),
                "suitable_for": raw.get("suitable_for", "") or "、".join(dict.fromkeys(scenario_labels)) or "业务参考",
                "usage": raw.get("usage", "") or "仅供案例参考",
                "report_usage": raw.get("report_usage", "") or "不直接写入正式报告",
                "summary": raw.get("summary", "") or raw.get("available_artifacts", "") or raw.get("limitations", "") or raw.get("case_title", ""),
                "limitations": raw.get("limitations", ""),
                "source_url": raw.get("url", ""),
                "url": raw.get("url", ""),
                "snapshot_path": raw.get("snapshot_path", ""),
                "knowledge_url": raw.get("knowledge_url", ""),
                "scenario": "、".join(expected_modules),
                "expected_module": "、".join(expected_modules),
                "case_type": raw.get("case_type", ""),
                "available_artifacts": raw.get("available_artifacts", ""),
            }
        )
    rows.sort(key=lambda item: (item["jurisdiction"], item["title"]))
    return rows


def get_user_source_detail(source_id: str) -> dict[str, str] | None:
    rows = build_user_source_catalog()
    return next((row for row in rows if row.get("source_id") == source_id), None)


def get_user_case_detail(case_id: str) -> dict[str, str] | None:
    rows = build_user_case_catalog()
    return next((row for row in rows if row.get("case_id") == case_id), None)


def get_user_source_preview(source_id: str, *, limit: int = 600) -> str:
    detail = get_user_source_detail(source_id)
    if not detail:
        return ""
    return read_text_preview(detail.get("snapshot_path", ""), limit=limit)


def get_user_case_preview(case_id: str, *, limit: int = 600) -> str:
    detail = get_user_case_detail(case_id)
    if not detail:
        return ""
    return read_text_preview(detail.get("snapshot_path", ""), limit=limit)


def search_user_articles(
    query: str,
    *,
    jurisdiction: str | None = None,
    path: str | None = None,
    top_k: int = 8,
) -> list[KnowledgeChunkV2]:
    settings = get_settings()
    embedder = HashingEmbedder(settings.rag_embedding_dimension)
    candidate_pool = max(top_k * 3, settings.rag_candidate_pool_size)
    index_names = ["legal_index_cn", "legal_index_eu", "legal_index_us"]
    if jurisdiction in {"cn", "eu", "us"}:
        index_names = [f"legal_index_{jurisdiction}"]

    merged_scores: dict[str, float] = {}
    payloads: dict[str, dict] = {}
    for index_name in index_names:
        index_path = _vector_index_path(index_name)
        if not index_path.exists():
            continue
        store = LocalVectorStore(index_path=index_path, embedder=embedder)
        entries = list(store.load())
        if not entries:
            continue
        vector_hits = store.search(query, entries, top_k=candidate_pool)
        lexical_hits = sorted(
            ((_lexical_score(query, KnowledgeChunkV2.model_validate(entry.payload)), entry) for entry in entries),
            key=lambda item: item[0],
            reverse=True,
        )[:candidate_pool]
        for rank, (_score, entry) in enumerate(vector_hits, start=1):
            merged_scores[entry.doc_id] = merged_scores.get(entry.doc_id, 0.0) + 1.0 / (60 + rank)
            payloads[entry.doc_id] = entry.payload
        for rank, (score, entry) in enumerate(lexical_hits, start=1):
            if score <= 0:
                continue
            merged_scores[entry.doc_id] = merged_scores.get(entry.doc_id, 0.0) + 1.0 / (60 + rank)
            payloads[entry.doc_id] = entry.payload

    ordered = sorted(merged_scores.items(), key=lambda item: item[1], reverse=True)
    results: list[KnowledgeChunkV2] = []
    seen: set[str] = set()
    for doc_id, _ in ordered:
        payload = payloads.get(doc_id)
        if not payload:
            continue
        chunk = KnowledgeChunkV2.model_validate(payload)
        if jurisdiction and chunk.jurisdiction != jurisdiction:
            continue
        if path and chunk.path not in {path, "all", "general"}:
            continue
        identity = f"{chunk.source_id}::{chunk.article_no or chunk.citation_anchor or chunk.chunk_id}"
        if identity in seen:
            continue
        seen.add(identity)
        results.append(chunk)
        if len(results) >= top_k:
            break
    return results


def resolve_user_citation(query: str) -> dict[str, str] | None:
    text = (query or "").strip().lower()
    if not text:
        return None
    rows = build_user_source_catalog()
    for row in rows:
        source_id = (row.get("source_id") or "").lower()
        title = (row.get("title") or "").lower()
        if source_id and source_id in text:
            return row
        if title and title in text:
            return row
    return None
