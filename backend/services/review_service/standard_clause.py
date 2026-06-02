from __future__ import annotations

from dataclasses import dataclass

from backend.common.knowledge.v2 import KnowledgeChunkV2
from backend.schemas.review import ClassifiedClause, ClauseType


@dataclass
class StandardClauseDiffResult:
    missing_obligations: list[str]
    weakened_obligations: list[str]
    added_risky_modifications: list[str]
    matched_chunk: KnowledgeChunkV2 | None = None


class StandardClauseLocator:
    def locate(
        self,
        clause: ClassifiedClause,
        candidates: list[KnowledgeChunkV2],
    ) -> KnowledgeChunkV2 | None:
        if not candidates:
            return None
        clause_type = clause.clause_type.value
        typed_candidates = [
            candidate
            for candidate in candidates
            if str(candidate.structured_payload.get("clause_type") or "") == clause_type
        ]
        pool = typed_candidates or candidates
        scored = sorted(
            pool,
            key=lambda candidate: self._score_candidate(clause.text, candidate),
            reverse=True,
        )
        return scored[0] if scored else None

    @staticmethod
    def _score_candidate(text: str, candidate: KnowledgeChunkV2) -> int:
        lower_text = text.lower()
        score = 0
        for token in (
            candidate.title,
            candidate.content,
            *candidate.keywords,
            *candidate.scenario_tags,
            *candidate.structured_payload.get("protected_obligations", []),
        ):
            token_l = str(token).lower()
            if token_l and token_l in lower_text:
                score += 3
        heuristics = {
            "STD-CN-SCC-PRIORITY": ("主服务协议", "优先", "不一致", "标准合同"),
            "STD-CN-SCC-RIGHTS": ("权利请求", "查阅", "删除", "更正", "暂缓"),
            "STD-CN-SCC-LIABILITY": ("赔偿责任", "责任总额", "免责", "责任上限"),
            "STD-CN-DPA-DELETION": ("删除", "返还", "证明", "销毁"),
            "STD-CN-DPA-COMPLIANCE": ("安全评估", "标准合同", "受托方", "单独负责"),
        }
        for hint in heuristics.get(candidate.chunk_id, ()):
            if hint.lower() in lower_text:
                score += 5
        return score


class StandardClauseDiffer:
    _RISKY_PATTERNS = (
        "以本协议为准",
        "以本合同为准",
        "主服务协议为准",
        "责任总额不超过",
        "赔偿责任总额不超过",
        "暂缓处理",
        "酌情处理",
        "视情况",
        "无需另行同意",
    )

    def diff(self, clause: ClassifiedClause, standard_clause: KnowledgeChunkV2 | None) -> StandardClauseDiffResult:
        if standard_clause is None:
            return StandardClauseDiffResult([], [], [])
        text = clause.text
        obligations = [
            str(item) for item in standard_clause.structured_payload.get("protected_obligations", [])
        ]
        missing: list[str] = []
        weakened: list[str] = []
        risky: list[str] = []

        token_hints = {
            "standard_contract_priority": ["标准合同", "优先", "不一致"],
            "no_conflicting_master_agreement": ["主服务协议", "不一致", "为准"],
            "timely_response": ["及时", "响应", "处理"],
            "no_unbounded_delay": ["暂缓", "视情况", "酌情"],
            "rights_request_process": ["权利请求", "删除", "更正", "查阅"],
            "no_excessive_liability_cap": ["责任总额不超过", "赔偿责任总额不超过", "责任上限"],
            "no_full_exemption": ["不承担", "免责"],
            "effective_remedy": ["救济", "赔偿", "责任"],
            "delete_or_return": ["删除", "返还"],
            "completion_proof": ["证明", "确认", "完成"],
            "retention_limit": ["保存期限", "期限"],
            "controller_primary_responsibility": ["个人信息处理者", "负责", "安全评估", "标准合同"],
            "no_full_responsibility_shift": ["乙方负责", "受托方负责", "单独负责"],
        }

        lower_text = text.lower()
        for obligation in obligations:
            hints = token_hints.get(obligation, [obligation])
            if not any(hint.lower() in lower_text for hint in hints):
                missing.append(obligation)
            if obligation in {"no_unbounded_delay", "no_excessive_liability_cap", "no_full_responsibility_shift"}:
                if any(hint.lower() in lower_text for hint in hints):
                    weakened.append(obligation)
            if obligation == "no_conflicting_master_agreement" and any(hint.lower() in lower_text for hint in hints):
                weakened.append(obligation)

        for pattern in self._RISKY_PATTERNS:
            if pattern.lower() in lower_text:
                risky.append(pattern)

        return StandardClauseDiffResult(
            missing_obligations=missing,
            weakened_obligations=weakened,
            added_risky_modifications=risky,
            matched_chunk=standard_clause,
        )
