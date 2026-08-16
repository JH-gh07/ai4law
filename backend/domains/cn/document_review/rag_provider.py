import json
import re

from backend.common.knowledge.v2 import RetrievalRequest
from backend.common.knowledge.registry import ensure_source_registry
from backend.common.rag.service import LegalRetrievalService
from backend.schemas.review import ClauseType
from backend.integrations.delilegal import DeliLegalService
from backend.core.resource_paths import rule_resource_path


def _build_canonical_title_map() -> dict[str, str]:
    """Map short/full source titles to the canonical registered title.

    The rulebook cites "个人信息保护法" while RAG hits carry the full registered
    name "中华人民共和国个人信息保护法". Normalizing here keeps the LLM prompt
    (and any downstream raw-citation consumer) from emitting both spellings.
    """
    mapping: dict[str, str] = {}
    for entry in ensure_source_registry():
        clean = entry.title.replace("《", "").replace("》", "").strip()
        if not clean:
            continue
        mapping[clean] = clean
        if clean.startswith("中华人民共和国"):
            mapping[clean[len("中华人民共和国"):]] = clean
    return mapping


_CANONICAL_TITLE_MAP = _build_canonical_title_map()


def _normalize_citation(raw: str) -> str:
    """Rewrite a "《source》article" string to the canonical source title."""
    if not raw:
        return raw
    m = re.match(r"《(.+?)》(.*)", raw)
    if not m:
        return raw
    title = m.group(1).replace("《", "").replace("》", "").strip()
    article = m.group(2).strip()
    canonical = _CANONICAL_TITLE_MAP.get(title, title)
    return f"《{canonical}》{article}".strip()


class LocalRegulationKnowledgeBase:
    def __init__(self, legal_api_service: DeliLegalService | None = None) -> None:
        path = rule_resource_path("cn", "review_rulebook.json")
        self.rulebook = json.loads(path.read_text(encoding="utf-8"))
        self.legal_api_service = legal_api_service
        self._cache: dict[tuple[str, str, bool], dict] = {}
        self.retrieval_service = LegalRetrievalService()

    def lookup(
        self,
        clause_type: ClauseType,
        clause_text: str | None = None,
        enrich: bool = True,
        *,
        jurisdiction: str | None = None,
        module: str | None = None,
        document_type: str = "other",
    ) -> dict:
        resolved_jurisdiction = self._resolve_jurisdiction(clause_text or "", jurisdiction)
        resolved_module = self._resolve_module(clause_type, clause_text or "", resolved_jurisdiction, module, document_type)
        cache_key = (f"{resolved_jurisdiction}:{resolved_module}:{clause_type.value}", (clause_text or "")[:160], enrich)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return dict(cached)

        clause_types = self.rulebook.get("clause_types", {})
        if clause_type.value in clause_types:
            config = dict(clause_types[clause_type.value])
        else:
            config = {
                "display_name": "Other Clause",
                "required_groups": [],
                "citations": ["Personal Information Protection Law and related rules"],
            }

        rag_citations: list[str] = []
        structured_citations: list[dict] = []
        workflow_rules: list[dict] = []
        standard_clause_candidates: list[dict] = []
        should_enrich = enrich and clause_type != ClauseType.OTHER and bool(clause_text and len(clause_text.strip()) >= 40)
        if should_enrich:
            path = "review"
            issue_result = self.retrieval_service.retrieve_with_fallback(
                RetrievalRequest(
                    module=resolved_module,
                    task_stage="issue_discovery",
                    query=f"{config.get('display_name', clause_type.value)} {clause_text[:400]}",
                    document_type=document_type,
                    environment="production",
                    top_k=4,
                    jurisdiction=resolved_jurisdiction,
                    path=path,
                )
            )
            issue_bundle = issue_result.bundle
            compare_result = self.retrieval_service.retrieve(
                RetrievalRequest(
                    module=resolved_module,
                    task_stage="clause_compare",
                    query=f"{config.get('display_name', clause_type.value)} {clause_text[:400]}",
                    document_type=document_type,
                    environment="production",
                    top_k=4,
                    jurisdiction=resolved_jurisdiction,
                    path=path,
                )
            )
            compare_bundle = compare_result.bundle
            rag_hits = issue_bundle.legal_grounding
            rag_citations = []
            for item in rag_hits:
                if hasattr(item, "article") and not hasattr(item, "article_no"):
                    title = item.title
                    article = item.article
                    source_id = item.id
                    snippet = item.content
                else:
                    title = item.title
                    article = item.citation_anchor or item.article_no
                    source_id = item.source_id
                    snippet = item.content
                    structured_citations.append(
                        {
                            "source_id": source_id,
                            "source_title": title,
                            "article": article,
                            "snippet": snippet[:200],
                            "source_type": item.source_kind,
                        }
                    )
                if title or article:
                    rag_citations.append(f"《{title}》{article}".strip())
            workflow_rules = [item.model_dump() for item in issue_bundle.workflow_rules]
            standard_clause_candidates = [item.model_dump() for item in compare_bundle.standard_clauses]

        raw_citations = list(config.get("citations", []))
        citations = [
            f"《{item.get('source', '')}》{item.get('article', '')}".strip()
            if isinstance(item, dict) else str(item)
            for item in raw_citations
            if item
        ]
        if rag_citations:
            citations = list(dict.fromkeys([*citations, *rag_citations]))

        # DeliLegal court-case search is reference material, NOT a legal citation.
        # Keep it in a separate field so the renderer can show it as "参考案例"
        # instead of dumping judgment titles into the "法规依据" column.
        reference_cases: list[dict] = []
        if self.legal_api_service and self.legal_api_service.enabled and should_enrich:
            hits = self.legal_api_service.search_cases(clause_text[:80], size=2)
            if hits:
                reference_cases = [
                    {
                        "source": str(item.get("source", "")),
                        "title": str(item.get("title", "")),
                        "summary": str(item.get("summary", "")),
                    }
                    for item in hits
                ]
            elif self.legal_api_service.last_error:
                reference_cases = [
                    {
                        "source": "DeliLegal",
                        "title": "案例检索失败",
                        "summary": self.legal_api_service.last_error,
                    }
                ]

        config["citations"] = list(dict.fromkeys(_normalize_citation(c) for c in citations))
        config["structured_citations"] = structured_citations
        config["reference_cases"] = reference_cases
        config["workflow_rules"] = workflow_rules
        config["standard_clause_candidates"] = standard_clause_candidates
        config["usage_policy_debug"] = {
            "jurisdiction": resolved_jurisdiction,
            "module": resolved_module,
            "workflow_rule_count": len(workflow_rules),
            "standard_clause_candidate_count": len(standard_clause_candidates),
            "structured_citation_count": len(structured_citations),
            "issue_retrieval_manifest": (
                issue_result.manifest.model_dump() if should_enrich else {}
            ),
            "compare_retrieval_manifest": (
                compare_result.manifest.model_dump() if should_enrich else {}
            ),
        }
        self._cache[cache_key] = dict(config)
        return dict(config)

    @staticmethod
    def _resolve_jurisdiction(clause_text: str, explicit: str | None) -> str:
        if explicit in {"cn", "eu", "us"}:
            return explicit
        lowered = clause_text.lower()
        if any(token in lowered for token in ("gdpr", "edpb", "binding corporate rules", "bcr", "scc", "onward transfer")):
            return "eu"
        if any(token in lowered for token in ("cpra", "ccpa", "privacy notice", "vendor agreement", "eo 14117", "data brokerage")):
            return "us"
        return "cn"

    @staticmethod
    def _resolve_module(
        clause_type: ClauseType,
        clause_text: str,
        jurisdiction: str,
        explicit: str | None,
        document_type: str,
    ) -> str:
        if explicit:
            return explicit
        lowered = clause_text.lower()
        if jurisdiction == "cn":
            return "cn_review"
        if jurisdiction == "eu":
            if "binding corporate rules" in lowered or "bcr" in lowered:
                return "eu_bcr"
            if clause_type == ClauseType.SUPPLEMENTARY_MEASURES:
                return "eu_tia"
            return "eu_scc" if document_type == "scc_contract" or clause_type in {ClauseType.ONWARD_TRANSFER, ClauseType.GOVERNMENT_ACCESS} else "eu_bcr"
        if "eo 14117" in lowered or "data brokerage" in lowered or document_type == "vendor_agreement":
            return "us_14117"
        if document_type == "privacy_policy" or clause_type in {ClauseType.RIGHTS_REQUEST, ClauseType.SENSITIVE_PI}:
            return "us_cpra"
        return "us_vendor_review"
