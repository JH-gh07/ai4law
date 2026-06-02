from __future__ import annotations

from backend.common.knowledge.v2 import EnvironmentType, KnowledgeChunkV2, UsageScope, UsageScopedContext


class UsagePolicyFilter:
    """Centralized usage guard for layered knowledge chunks."""

    @staticmethod
    def filter(
        chunks: list[KnowledgeChunkV2],
        *,
        usage: UsageScope | str,
        environment: EnvironmentType = "production",
    ) -> UsageScopedContext:
        accepted: list[KnowledgeChunkV2] = []
        rejected: list[str] = []

        for chunk in chunks:
            if not UsagePolicyFilter._is_allowed(chunk, usage=usage, environment=environment):
                rejected.append(chunk.chunk_id)
                continue
            accepted.append(chunk)

        return UsageScopedContext(
            usage=usage,
            environment=environment,
            chunks=accepted,
            rejected_chunk_ids=rejected,
            debug={
                "requested_usage": usage,
                "environment": environment,
                "accepted_count": len(accepted),
                "rejected_count": len(rejected),
            },
        )

    @staticmethod
    def _is_allowed(
        chunk: KnowledgeChunkV2,
        *,
        usage: UsageScope | str,
        environment: EnvironmentType,
    ) -> bool:
        if environment == "production" and chunk.layer == "L3_testcase":
            return False

        if usage == "external_report":
            return (
                chunk.layer == "L1_regulatory_evidence"
                and chunk.can_enter_external_report
                and chunk.can_be_cited
            )

        if usage == "legal_grounding":
            return (
                chunk.layer == "L1_regulatory_evidence"
                and chunk.can_be_cited
                and chunk.source_kind in {"law_article", "official_guide", "regulation", "standard_clause"}
            )

        if usage == "internal_review":
            if chunk.layer in {"L1_regulatory_evidence", "L2_business_rule"}:
                return True
            return environment != "production" and chunk.layer == "L3_testcase"

        if usage == "few_shot":
            return environment in {"dev", "eval"} and chunk.layer == "L3_testcase"

        if usage == "evaluator":
            return environment == "eval" and chunk.layer == "L3_testcase"

        if usage == "structure_control":
            return (
                chunk.layer == "L4_template"
                and chunk.template_type == "official_template"
            )

        if usage == "internal_drafting":
            return chunk.layer == "L4_template"

        if usage == "risk_explanation":
            return chunk.layer in {"L1_regulatory_evidence", "L2_business_rule"}

        return usage in set(chunk.allowed_usage or [])
