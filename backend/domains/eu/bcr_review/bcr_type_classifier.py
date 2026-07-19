"""BCRTypeClassifier — determine BCR-C vs BCR-P type from document content."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from backend.domains.eu.bcr_review.bcr_rulebook_loader import BCRRulebookLoader
from backend.domains.eu.bcr_review.schema import BCRTypeClassification

if TYPE_CHECKING:
    from backend.common.llm.client import LLMClient

logger = logging.getLogger(__name__)


class BCRTypeClassifier:
    def __init__(self, rulebook_loader: BCRRulebookLoader | None = None,
                 llm_client: LLMClient | None = None) -> None:
        self.rulebook = rulebook_loader or BCRRulebookLoader()
        self.llm_client = llm_client

    def classify(self, text: str, declared_type: str | None = None) -> BCRTypeClassification:
        t = text[:8000].lower()
        c_signals = self.rulebook.get_bcr_c_signals()
        p_signals = self.rulebook.get_bcr_p_signals()

        # Weighted scoring: title signals ×2, body signals ×1
        title_t = t[:500].lower()
        c_hits = [s for s in c_signals if s.lower() in t]
        p_hits = [s for s in p_signals if s.lower() in t]
        c_score = sum(2.0 if s.lower() in title_t else 1.0 for s in c_hits)
        p_score = sum(2.0 if s.lower() in title_t else 1.0 for s in p_hits)

        if c_score >= p_score + 1.0:
            actual = "BCR-C"
        elif p_score >= c_score + 1.0:
            actual = "BCR-P"
        elif c_score > 0:
            actual = "BCR-C"
        elif p_score > 0:
            actual = "BCR-P"
        else:
            actual = "unknown"

        declared = declared_type or "unknown"
        if declared == actual:
            consistency = "consistent"
            risk = "LOW"
        elif actual == "unknown":
            consistency = "uncertain"
            risk = "MEDIUM"
        else:
            consistency = "mismatch"
            risk = "HIGH"

        evidence: list[str] = []
        if c_hits: evidence.append(f"BCR-C 信号: {c_hits[:3]}")
        if p_hits: evidence.append(f"BCR-P 信号: {p_hits[:3]}")

        recommendation = ""
        if consistency == "mismatch":
            recommendation = f"文档标题或声明为 {declared}，但内容检测为 {actual}。建议重新评估业务角色并相应修订 BCR。"

        return BCRTypeClassification(
            declared_bcr_type=declared,
            actual_bcr_type=actual,
            type_consistency=consistency,
            risk_level=risk,
            evidence=evidence,
            recommendation=recommendation,
        )
