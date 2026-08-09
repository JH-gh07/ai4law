from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from backend.common.knowledge.builders_v2 import (
    build_legal_chunks_cn,
    build_legal_chunks_eu,
    build_legal_chunks_us,
    build_standard_clause_chunks_cn,
    build_standard_clause_chunks_eu,
    build_standard_clause_chunks_us,
    build_template_chunks_cn,
    build_template_chunks_eu,
    build_template_chunks_us,
    build_testcase_chunks_cn,
    build_testcase_chunks_eu,
    build_testcase_chunks_us,
    build_workflow_chunks_cn,
    build_workflow_chunks_eu,
    build_workflow_chunks_us,
)
from backend.common.knowledge.usage_policy import UsagePolicyFilter
from backend.common.knowledge.v2 import KnowledgeChunkV2, RetrievalBundle, RetrievalRequest
from backend.common.knowledge.paths import (
    regulation_articles_jsonl_path,
    source_registry_path,
    sources_csv_path,
)
from backend.common.rag.constants import MULTI_INDEX_SCHEMA_VERSION
from backend.common.rag.embedding import HashingEmbedder, normalize_text, tokenize_text
from backend.common.rag.vector_store import LocalVectorStore, VectorIndexEntry, content_fingerprint
from backend.core.settings import Settings, get_settings

INDEX_NAMES = (
    "legal_index_cn",
    "workflow_index_cn",
    "standard_clause_index_cn",
    "template_index_cn",
    "testcase_index_cn",
    "legal_index_eu",
    "workflow_index_eu",
    "standard_clause_index_eu",
    "template_index_eu",
    "testcase_index_eu",
    "legal_index_us",
    "workflow_index_us",
    "standard_clause_index_us",
    "template_index_us",
    "testcase_index_us",
)
LEGAL_INDEX_NAMES = frozenset({"legal_index_cn", "legal_index_eu", "legal_index_us"})


def legal_source_fingerprint() -> str:
    return content_fingerprint(
        [
            regulation_articles_jsonl_path(),
            sources_csv_path(),
            source_registry_path(),
        ]
    )



def _lexical_score(query: str, chunk: KnowledgeChunkV2) -> float:
    q = normalize_text(query or "")
    if not q:
        return 0.0
    body = normalize_text(" ".join([chunk.title, chunk.citation_anchor, chunk.content, " ".join(chunk.keywords)]))
    score = 0.0
    if q in body or body[:80] in q:
        score += 3.0
    overlap = 0
    for token in set(tokenize_text(query)):
        if token and token in body:
            overlap += 1
    score += min(overlap * 0.35, 4.0)
    for tag in chunk.scenario_tags:
        if normalize_text(tag) in q:
            score += 0.5
    return score


def _payload_to_chunk(payload: dict) -> KnowledgeChunkV2:
    return KnowledgeChunkV2.model_validate(payload)


class RetrievalOrchestrator:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.embedder = HashingEmbedder(self.settings.rag_embedding_dimension)
        self.rag_dir = self.settings.rag_v3_dir

    def retrieve(self, request: RetrievalRequest) -> RetrievalBundle:
        if request.module == "cn_diagnosis":
            return self._retrieve_cn_diagnosis(request)
        if request.module == "cn_assessment":
            return self._retrieve_cn_assessment(request)
        if request.module == "cn_review":
            return self._retrieve_cn_review(request)
        if request.module in {"eu_scc", "eu_bcr", "eu_dpia", "eu_tia"}:
            return self._retrieve_eu(request)
        if request.module in {"us_eo14117", "us_vendor_review", "us_cpra"}:
            return self._retrieve_us(request)
        return RetrievalBundle(debug={"unsupported_module": request.module})

    def retrieve_legal_chunks(
        self,
        *,
        query: str,
        top_k: int = 8,
        path: str = "all",
        module: str = "cn_assessment",
    ) -> list[KnowledgeChunkV2]:
        request = RetrievalRequest(
            module=module,  # type: ignore[arg-type]
            task_stage="legal_grounding",
            query=query,
            top_k=top_k,
            path=path,
        )
        return self.retrieve(request).legal_grounding

    def _retrieve_cn_diagnosis(self, request: RetrievalRequest) -> RetrievalBundle:
        workflow = self._search_index(
            "workflow_index_cn",
            request.query,
            top_k=max(4, request.top_k),
            filters={"module": "cn_diagnosis"},
        )
        legal = self._legal_by_reference_ids(workflow)
        legal_ctx = UsagePolicyFilter.filter(legal, usage="legal_grounding", environment=request.environment)
        workflow_ctx = UsagePolicyFilter.filter(workflow, usage="internal_review", environment=request.environment)
        return RetrievalBundle(
            legal_grounding=legal_ctx.chunks,
            workflow_rules=workflow_ctx.chunks,
            debug={
                "stage": request.task_stage,
                "workflow_rejected": workflow_ctx.rejected_chunk_ids,
                "legal_rejected": legal_ctx.rejected_chunk_ids,
            },
        )

    def _retrieve_cn_assessment(self, request: RetrievalRequest) -> RetrievalBundle:
        bundle = RetrievalBundle(debug={"stage": request.task_stage})
        if request.task_stage in {"issue_discovery", "legal_grounding"}:
            workflow = self._search_index(
                "workflow_index_cn",
                request.query,
                top_k=max(4, request.top_k),
                filters={"module": "cn_assessment"},
            )
            bundle.workflow_rules = UsagePolicyFilter.filter(
                workflow,
                usage="internal_review",
                environment=request.environment,
            ).chunks
            legal = self._search_index(
                "legal_index_cn",
                request.query,
                top_k=request.top_k,
                filters={"path": "assessment"},
            )
            legal.extend(self._legal_by_reference_ids(bundle.workflow_rules))
            bundle.legal_grounding = self._dedupe_chunks(
                UsagePolicyFilter.filter(
                    self._dedupe_chunks(legal),
                    usage="legal_grounding",
                    environment=request.environment,
                ).chunks
            )
        if request.task_stage == "report_generation":
            templates = self._search_index(
                "template_index_cn",
                request.query or "安全评估 模板 章节 结构",
                top_k=request.top_k,
                filters={"module": "cn_assessment"},
            )
            bundle.templates = UsagePolicyFilter.filter(
                templates,
                usage="structure_control",
                environment=request.environment,
            ).chunks
        if request.task_stage == "evaluation":
            testcases = self._search_index(
                "testcase_index_cn",
                request.query,
                top_k=request.top_k,
                filters={"module": "cn_assessment"},
            )
            bundle.testcases = UsagePolicyFilter.filter(
                testcases,
                usage="evaluator",
                environment=request.environment,
            ).chunks
        return bundle

    def _retrieve_cn_review(self, request: RetrievalRequest) -> RetrievalBundle:
        bundle = RetrievalBundle(debug={"stage": request.task_stage, "document_type": request.document_type})
        if request.task_stage in {"issue_discovery", "legal_grounding"}:
            workflow = self._search_index(
                "workflow_index_cn",
                request.query,
                top_k=max(4, request.top_k),
                filters={"module": "cn_review"},
            )
            if request.document_type and request.document_type != "other":
                workflow = [
                    chunk
                    for chunk in workflow
                    if not chunk.structured_payload.get("document_type")
                    or chunk.structured_payload.get("document_type") == request.document_type
                ] or workflow
            bundle.workflow_rules = UsagePolicyFilter.filter(
                workflow,
                usage="internal_review",
                environment=request.environment,
            ).chunks
            legal = self._search_index(
                "legal_index_cn",
                request.query,
                top_k=request.top_k,
                filters={"path": "review"},
            )
            legal.extend(self._legal_by_reference_ids(bundle.workflow_rules))
            bundle.legal_grounding = self._dedupe_chunks(
                UsagePolicyFilter.filter(
                    self._dedupe_chunks(legal),
                    usage="legal_grounding",
                    environment=request.environment,
                ).chunks
            )
        if request.task_stage == "clause_compare":
            standard = self._search_index(
                "standard_clause_index_cn",
                request.query,
                top_k=max(3, request.top_k),
                filters={"module": "cn_review"},
            )
            if request.document_type and request.document_type != "other":
                standard = [
                    chunk
                    for chunk in standard
                    if request.document_type in chunk.scenario_tags or "other" in chunk.scenario_tags
                ] or standard
            bundle.standard_clauses = UsagePolicyFilter.filter(
                standard,
                usage="legal_grounding",
                environment=request.environment,
            ).chunks
            bundle.legal_grounding = self._dedupe_chunks(
                self._legal_by_reference_ids(bundle.standard_clauses)
            )
        if request.task_stage == "report_generation":
            templates = self._search_index(
                "template_index_cn",
                request.query or "审查 报告 模板",
                top_k=request.top_k,
                filters={"module": "cn_review"},
            )
            bundle.templates = UsagePolicyFilter.filter(
                templates,
                usage="structure_control",
                environment=request.environment,
            ).chunks
        if request.task_stage == "evaluation":
            testcases = self._search_index(
                "testcase_index_cn",
                request.query,
                top_k=request.top_k,
                filters={"module": "cn_review"},
            )
            bundle.testcases = UsagePolicyFilter.filter(
                testcases,
                usage="evaluator",
                environment=request.environment,
            ).chunks
        return bundle

    def _retrieve_eu(self, request: RetrievalRequest) -> RetrievalBundle:
        bundle = RetrievalBundle(debug={"stage": request.task_stage, "module": request.module, "jurisdiction": "eu"})
        if request.task_stage in {"issue_discovery", "legal_grounding"}:
            workflow = self._search_index(
                "workflow_index_eu",
                request.query,
                top_k=max(4, request.top_k),
                filters={"module": request.module},
            )
            bundle.workflow_rules = UsagePolicyFilter.filter(
                workflow,
                usage="internal_review",
                environment=request.environment,
            ).chunks
            legal = self._search_index(
                "legal_index_eu",
                request.query,
                top_k=request.top_k,
                filters={"module": request.module},
            )
            legal.extend(self._legal_by_reference_ids_for_index(bundle.workflow_rules, "legal_index_eu"))
            bundle.legal_grounding = self._dedupe_chunks(
                UsagePolicyFilter.filter(
                    self._dedupe_chunks(legal),
                    usage="legal_grounding",
                    environment=request.environment,
                ).chunks
            )
            if request.task_stage == "issue_discovery":
                standard = self._search_index(
                    "standard_clause_index_eu",
                    request.query,
                    top_k=max(3, request.top_k),
                    filters={"module": request.module},
                )
                bundle.standard_clauses = UsagePolicyFilter.filter(
                    standard,
                    usage="legal_grounding",
                    environment=request.environment,
                ).chunks
                bundle.legal_grounding = self._dedupe_chunks(
                    [
                        *bundle.legal_grounding,
                        *self._legal_by_reference_ids_for_index(bundle.standard_clauses, "legal_index_eu"),
                    ]
                )
        if request.task_stage == "clause_compare":
            standard = self._search_index(
                "standard_clause_index_eu",
                request.query,
                top_k=max(3, request.top_k),
                filters={"module": request.module},
            )
            bundle.standard_clauses = UsagePolicyFilter.filter(
                standard,
                usage="legal_grounding",
                environment=request.environment,
            ).chunks
            bundle.legal_grounding = self._dedupe_chunks(
                self._legal_by_reference_ids_for_index(bundle.standard_clauses, "legal_index_eu")
            )
        if request.task_stage == "report_generation":
            templates = self._search_index(
                "template_index_eu",
                request.query or "EU template structure",
                top_k=request.top_k,
                filters={"module": request.module},
            )
            bundle.templates = UsagePolicyFilter.filter(
                templates,
                usage="structure_control",
                environment=request.environment,
            ).chunks
        if request.task_stage == "evaluation":
            testcases = self._search_index(
                "testcase_index_eu",
                request.query,
                top_k=request.top_k,
                filters={"module": request.module},
            )
            bundle.testcases = UsagePolicyFilter.filter(
                testcases,
                usage="evaluator",
                environment=request.environment,
            ).chunks
        return bundle

    def _retrieve_us(self, request: RetrievalRequest) -> RetrievalBundle:
        bundle = RetrievalBundle(debug={"stage": request.task_stage, "module": request.module, "jurisdiction": "us"})
        if request.task_stage in {"issue_discovery", "legal_grounding"}:
            workflow = self._search_index(
                "workflow_index_us",
                request.query,
                top_k=max(4, request.top_k),
                filters={"module": request.module},
            )
            bundle.workflow_rules = UsagePolicyFilter.filter(
                workflow,
                usage="internal_review",
                environment=request.environment,
            ).chunks
            legal = self._search_index(
                "legal_index_us",
                request.query,
                top_k=request.top_k,
                filters={"module": request.module},
            )
            legal.extend(self._legal_by_reference_ids_for_index(bundle.workflow_rules, "legal_index_us"))
            bundle.legal_grounding = self._dedupe_chunks(
                UsagePolicyFilter.filter(
                    self._dedupe_chunks(legal),
                    usage="legal_grounding",
                    environment=request.environment,
                ).chunks
            )
            if request.task_stage == "issue_discovery":
                standard = self._search_index(
                    "standard_clause_index_us",
                    request.query,
                    top_k=max(3, request.top_k),
                    filters={"module": request.module},
                )
                bundle.standard_clauses = UsagePolicyFilter.filter(
                    standard,
                    usage="legal_grounding",
                    environment=request.environment,
                ).chunks
                bundle.legal_grounding = self._dedupe_chunks(
                    [
                        *bundle.legal_grounding,
                        *self._legal_by_reference_ids_for_index(bundle.standard_clauses, "legal_index_us"),
                    ]
                )
        if request.task_stage == "clause_compare":
            standard = self._search_index(
                "standard_clause_index_us",
                request.query,
                top_k=max(3, request.top_k),
                filters={"module": request.module},
            )
            bundle.standard_clauses = UsagePolicyFilter.filter(
                standard,
                usage="legal_grounding",
                environment=request.environment,
            ).chunks
            bundle.legal_grounding = self._dedupe_chunks(
                self._legal_by_reference_ids_for_index(bundle.standard_clauses, "legal_index_us")
            )
        if request.task_stage == "report_generation":
            templates = self._search_index(
                "template_index_us",
                request.query or "US template structure",
                top_k=request.top_k,
                filters={"module": request.module},
            )
            bundle.templates = UsagePolicyFilter.filter(
                templates,
                usage="structure_control",
                environment=request.environment,
            ).chunks
        if request.task_stage == "evaluation":
            testcases = self._search_index(
                "testcase_index_us",
                request.query,
                top_k=request.top_k,
                filters={"module": request.module},
            )
            bundle.testcases = UsagePolicyFilter.filter(
                testcases,
                usage="evaluator",
                environment=request.environment,
            ).chunks
        return bundle

    def _index_path(self, name: str) -> Path:
        return self.rag_dir / f"{name}.vector.json"

    def _ensure_multi_indexes(self) -> None:
        from backend.common.rag.ingest import build_multi_index_v3

        if all(self._is_index_current(name) for name in INDEX_NAMES):
            return
        build_multi_index_v3(self.settings)
        self._load_entries.cache_clear()  # type: ignore[attr-defined]

    def _is_index_current(self, name: str) -> bool:
        index_path = self._index_path(name)
        if not index_path.exists():
            return False
        try:
            payload = json.loads(index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False
        metadata = payload.get("metadata", {})
        is_current = (
            metadata.get("schema_version") == MULTI_INDEX_SCHEMA_VERSION
            and metadata.get("embedding_version") == self.embedder.version
            and metadata.get("embedding_dimension") == self.embedder.dimension
        )
        if name in LEGAL_INDEX_NAMES:
            is_current = is_current and metadata.get("source_fingerprint") == legal_source_fingerprint()
        return is_current

    @lru_cache(maxsize=None)
    def _load_entries(self, name: str) -> tuple[VectorIndexEntry, ...]:
        self._ensure_multi_indexes()
        store = LocalVectorStore(self._index_path(name), self.embedder)
        return tuple(store.load())

    def _search_index(
        self,
        index_name: str,
        query: str,
        *,
        top_k: int,
        filters: dict[str, str] | None = None,
    ) -> list[KnowledgeChunkV2]:
        entries = self._load_entries(index_name)
        if not entries:
            return []
        store = LocalVectorStore(self._index_path(index_name), self.embedder)
        vector_hits = store.search(query, list(entries), top_k=max(top_k * 3, self.settings.rag_candidate_pool_size))
        lexical_hits = sorted(
            ((_lexical_score(query, _payload_to_chunk(entry.payload)), entry) for entry in entries),
            key=lambda item: item[0],
            reverse=True,
        )[: max(top_k * 3, self.settings.rag_candidate_pool_size)]
        merged_scores: dict[str, float] = {}
        payloads: dict[str, dict] = {}
        for rank, (score, entry) in enumerate(vector_hits, start=1):
            merged_scores[entry.doc_id] = merged_scores.get(entry.doc_id, 0.0) + 1.0 / (60 + rank)
            payloads[entry.doc_id] = entry.payload
        for rank, (score, entry) in enumerate(lexical_hits, start=1):
            if score <= 0:
                continue
            merged_scores[entry.doc_id] = merged_scores.get(entry.doc_id, 0.0) + 1.0 / (60 + rank)
            payloads[entry.doc_id] = entry.payload
        ordered = sorted(merged_scores.items(), key=lambda item: item[1], reverse=True)
        results: list[KnowledgeChunkV2] = []
        for doc_id, _ in ordered:
            chunk = _payload_to_chunk(payloads[doc_id])
            if not self._match_filters(chunk, filters or {}):
                continue
            results.append(chunk)
            if len(results) >= top_k:
                break
        return results

    @staticmethod
    def _match_filters(chunk: KnowledgeChunkV2, filters: dict[str, str]) -> bool:
        for key, expected in filters.items():
            if not expected:
                continue
            if key == "path":
                if chunk.path not in {expected, "all", "general"}:
                    return False
                continue
            value = getattr(chunk, key, None)
            if value is None:
                value = chunk.structured_payload.get(key)
            if value is None:
                continue
            if str(value) != str(expected):
                return False
        return True

    def _legal_by_reference_ids(self, chunks: Iterable[KnowledgeChunkV2]) -> list[KnowledgeChunkV2]:
        return self._legal_by_reference_ids_for_index(chunks, "legal_index_cn")

    def _legal_by_reference_ids_for_index(self, chunks: Iterable[KnowledgeChunkV2], index_name: str) -> list[KnowledgeChunkV2]:
        ref_ids = {ref for chunk in chunks for ref in chunk.reference_ids}
        if not ref_ids:
            return []
        entries = self._load_entries(index_name)
        results: list[KnowledgeChunkV2] = []
        for entry in entries:
            chunk = _payload_to_chunk(entry.payload)
            if chunk.source_id in ref_ids or chunk.chunk_id in ref_ids:
                results.append(chunk)
        return self._dedupe_chunks(results)

    @staticmethod
    def _dedupe_chunks(chunks: list[KnowledgeChunkV2]) -> list[KnowledgeChunkV2]:
        deduped: list[KnowledgeChunkV2] = []
        seen: set[str] = set()
        for chunk in chunks:
            if chunk.chunk_id in seen:
                continue
            seen.add(chunk.chunk_id)
            deduped.append(chunk)
        return deduped

    @staticmethod
    def dedupe_by_source(chunks: list[KnowledgeChunkV2]) -> list[KnowledgeChunkV2]:
        deduped: list[KnowledgeChunkV2] = []
        seen: set[str] = set()
        for chunk in chunks:
            source_key = chunk.source_id or chunk.chunk_id
            if source_key in seen:
                continue
            seen.add(source_key)
            deduped.append(chunk)
        return deduped


def build_chunk_sets() -> dict[str, list[KnowledgeChunkV2]]:
    return {
        "legal_index_cn": build_legal_chunks_cn(),
        "workflow_index_cn": build_workflow_chunks_cn(),
        "standard_clause_index_cn": build_standard_clause_chunks_cn(),
        "template_index_cn": build_template_chunks_cn(),
        "testcase_index_cn": build_testcase_chunks_cn(),
        "legal_index_eu": build_legal_chunks_eu(),
        "workflow_index_eu": build_workflow_chunks_eu(),
        "standard_clause_index_eu": build_standard_clause_chunks_eu(),
        "template_index_eu": build_template_chunks_eu(),
        "testcase_index_eu": build_testcase_chunks_eu(),
        "legal_index_us": build_legal_chunks_us(),
        "workflow_index_us": build_workflow_chunks_us(),
        "standard_clause_index_us": build_standard_clause_chunks_us(),
        "template_index_us": build_template_chunks_us(),
        "testcase_index_us": build_testcase_chunks_us(),
    }
