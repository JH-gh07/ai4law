"""BCRClauseReviewer — clause-level compliance review for BCR documents."""

from __future__ import annotations

import logging
from uuid import uuid4

from backend.modules.bcr.bcr_rulebook_loader import BCRRulebookLoader
from backend.modules.bcr.schema import BCRFinding

logger = logging.getLogger(__name__)

_VAGUE_PATTERNS = [
    (r"as\s+appropriate", "vague_as_appropriate"),
    (r"where\s+feasible", "vague_where_feasible"),
    (r"reasonable\s+efforts", "vague_reasonable_efforts"),
    (r"to\s+the\s+extent\s+possible", "vague_extent_possible"),
    (r"as\s+soon\s+as\s+reasonably\s+practicable", "vague_timeline"),
]


class BCRClauseReviewer:
    def __init__(self, llm_client=None, rulebook: BCRRulebookLoader | None = None) -> None:
        self.llm_client = llm_client
        self.rulebook = rulebook or BCRRulebookLoader()

    def review_clause(
        self, clause_text: str, requirement: dict, bcr_type: str, legal_refs: list[dict] | None = None,
    ) -> list[BCRFinding]:
        findings: list[BCRFinding] = []
        req_id = requirement["requirement_id"]
        refs = legal_refs or []

        # 1. Vague language detection
        for pattern, check_id in _VAGUE_PATTERNS:
            import re
            if re.search(pattern, clause_text, re.IGNORECASE):
                findings.append(BCRFinding(
                    finding_id=f"BCR-VAGUE-{uuid4().hex[:8]}",
                    requirement_id=req_id,
                    location="",
                    clause_excerpt=clause_text[:200],
                    title=f"表述存在模糊空间 ({requirement['title']})",
                    risk_level="MEDIUM",
                    finding=f"使用了 '{check_id}' 等模糊表述，可能导致执行和追责标准不明确。",
                    legal_basis=[r.get("source", "") for r in refs[:2]],
                    recommendation=f"建议将模糊性表述替换为具体的、可验证的义务描述。",
                    review_confidence=0.85,
                ))
                break

        # 2. Key content missing check
        keywords = requirement.get("check_keywords", [])
        if keywords and not any(kw.lower() in clause_text.lower() for kw in keywords[:3]):
            findings.append(BCRFinding(
                finding_id=f"BCR-SUMMARY-{uuid4().hex[:8]}",
                requirement_id=req_id,
                location="",
                clause_excerpt=clause_text[:200],
                title=f"{requirement['title']} 描述不够具体",
                risk_level="MEDIUM",
                finding=f"未能涵盖 '{requirement['title']}' 的核心要素。",
                legal_basis=[r.get("source", "") for r in refs[:1]],
                recommendation=f"建议补充 {requirement['title']} 的详细描述。",
                review_confidence=0.75,
            ))

        return findings
