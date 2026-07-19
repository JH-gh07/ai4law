import json
from pathlib import Path

from backend.common.knowledge.v2 import RetrievalRequest
from backend.common.rag.service import LegalRetrievalService
from backend.schemas.review import ClauseType
from backend.integrations.delilegal import DeliLegalService
from backend.core.resource_paths import rule_resource_path


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

        if self.legal_api_service and self.legal_api_service.enabled and should_enrich:
            hits = self.legal_api_service.search_cases(clause_text[:80], size=2)
            if hits:
                external_citations = [
                    f"{item['source']}: {item['title']}"
                    for item in hits
                ]
                citations = list(dict.fromkeys([*citations, *external_citations]))
            elif self.legal_api_service.last_error:
                citations = list(
                    dict.fromkeys(
                        [
                            *citations,
                            f"DeliLegal API failed: {self.legal_api_service.last_error}",
                        ]
                    )
                )

        config["citations"] = citations
        config["structured_citations"] = structured_citations
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
            return "us_eo14117"
        if document_type == "privacy_policy" or clause_type in {ClauseType.RIGHTS_REQUEST, ClauseType.SENSITIVE_PI}:
            return "us_privacy_review"
        return "us_vendor_review"
