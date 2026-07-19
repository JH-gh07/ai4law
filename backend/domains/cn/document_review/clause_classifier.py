"""Enhanced multi‑label clause classifier with confidence scoring."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from backend.schemas.review import Clause, ClassifiedClause, ClauseType
from backend.domains.cn.document_review.rulebook_loader import RulebookLoader

if TYPE_CHECKING:
    from backend.common.llm.client import LLMClient

logger = logging.getLogger(__name__)

# ── Threshold for secondary type inclusion ─────────────────────────────
_SECONDARY_KEYWORD_THRESHOLD = 2  # minimum keywords to add as secondary type
_PRIMARY_CONFIDENCE_MIN = 0.3  # minimum confidence for any type match


class ClauseClassifier:
    """Classify clauses into primary + secondary types using keyword matching.

    Enhanced from single‑label to multi‑label:
    - primary type = type with most matching keywords
    - secondary types = types with ≥ THRESHOLD keyword matches
    - type_confidence = matched / total keywords for the type
    - LLM fallback for ambiguous OTHER clauses with substantial text
    """

    def __init__(
        self,
        rulebook_loader: RulebookLoader | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.rulebook = rulebook_loader or RulebookLoader()
        self.llm_client = llm_client

    def classify(self, clause: Clause) -> ClassifiedClause:
        """Classify a single clause, returning ClassifiedClause with multi‑labels."""
        text = clause.text

        # Build type → keyword match count mapping
        type_scores: dict[str, int] = {}
        type_matched_keywords: dict[str, list[str]] = {}

        for ct_name in self.rulebook.get_all_clause_types():
            keywords = self.rulebook.get_keywords(ct_name)
            matched = [kw for kw in keywords if kw in text]
            if matched:
                type_scores[ct_name] = len(matched)
                type_matched_keywords[ct_name] = matched

        if not type_scores:
            # No keywords matched at all → OTHER
            return self._build_other(clause)

        # Primary type = most matched keywords
        primary_type = max(type_scores, key=lambda k: type_scores[k])
        primary_keywords = type_matched_keywords[primary_type]
        primary_conf = self._compute_confidence(primary_type, len(primary_keywords))

        # Secondary types
        secondary_types: list[ClauseType] = []
        for ct_name, count in type_scores.items():
            if ct_name == primary_type:
                continue
            if count >= _SECONDARY_KEYWORD_THRESHOLD:
                try:
                    secondary_types.append(ClauseType(ct_name))
                except ValueError:
                    pass

        # Cross‑type label enrichment (from multi_label_keywords)
        cross_labels = self._detect_cross_labels(text, primary_type)
        for label in cross_labels:
            try:
                ct = ClauseType(label)
                if ct not in secondary_types:
                    secondary_types.append(ct)
            except ValueError:
                pass

        return ClassifiedClause(
            **clause.model_dump(),
            clause_type=ClauseType(primary_type),
            matched_keywords=primary_keywords,
            secondary_types=secondary_types,
            type_confidence=round(primary_conf, 2),
        )

    # ------------------------------------------------------------------
    # Confidence computation
    # ------------------------------------------------------------------

    def _compute_confidence(self, clause_type: str, matched_count: int) -> float:
        """Compute classification confidence 0–1 using matched count."""
        total = len(self.rulebook.get_keywords(clause_type))
        if total == 0:
            return 0.5 if matched_count > 0 else 0.3
        # Base confidence 0.4 + up to 0.5 from match ratio, capped at 0.95
        ratio = matched_count / min(total, 10)
        return min(0.4 + ratio * 0.5, 0.95)

    # ------------------------------------------------------------------
    # Cross‑label detection
    # ------------------------------------------------------------------

    def _detect_cross_labels(self, text: str, primary_type: str) -> list[str]:
        """Detect additional clause types through multi_label_keywords."""
        additional: list[str] = []
        cross_map = self.rulebook.get_multi_label_keywords(primary_type)
        if not cross_map:
            return additional

        for other_type, keywords in cross_map.items():
            if other_type == primary_type:
                continue
            matched = sum(1 for kw in keywords if kw in text)
            if matched >= 1:  # lower threshold for cross‑labels
                additional.append(other_type)

        return additional

    # ------------------------------------------------------------------
    # Fallback classification
    # ------------------------------------------------------------------

    def _build_other(self, clause: Clause) -> ClassifiedClause:
        """Build an OTHER classification, optionally using LLM for long text."""
        if self.llm_client and self.llm_client.enabled and len(clause.text.strip()) >= 200:
            llm_type = self._classify_with_llm(clause.text)
            if llm_type:
                try:
                    return ClassifiedClause(
                        **clause.model_dump(),
                        clause_type=ClauseType(llm_type),
                        matched_keywords=["LLM 辅助分类"],
                        type_confidence=0.5,
                    )
                except ValueError:
                    pass

        return ClassifiedClause(
            **clause.model_dump(),
            clause_type=ClauseType.OTHER,
            matched_keywords=[],
            type_confidence=0.3,
        )

    def _classify_with_llm(self, text: str) -> str | None:
        """Use LLM to determine clause type for ambiguous text."""
        if not self.llm_client or not self.llm_client.enabled:
            return None

        type_list = "、".join(self.rulebook.get_all_clause_types()[:15])
        prompt = f"""分析以下合同条款，判断其条款类型。

可选的条款类型: {type_list}, OTHER

条款文本:
{text[:600]}

请仅输出一个条款类型枚举值，不含其他文字。"""

        try:
            raw = self.llm_client.chat(
                system="你是一名中国数据合规专家。仅输出条款类型枚举值。",
                user=prompt,
                temperature=0.0,
                max_tokens=30,
            )
            result = raw.strip().upper()
            for ct_name in self.rulebook.get_all_clause_types():
                if ct_name in result:
                    return ct_name
            return None
        except Exception as exc:
            logger.warning("LLM clause classification failed: %s", exc)
            return None
