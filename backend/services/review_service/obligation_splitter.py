"""ObligationSplitter — split compound clauses into obligation units.

A long legal clause may contain multiple distinct obligations. This
splitter uses semantic trigger words to separate them, enabling more
precise per‑obligation review.
"""

from __future__ import annotations

import re
from uuid import uuid4

from backend.schemas.review import Clause, ClausePosition

# ── Obligation trigger words ────────────────────────────────────────────

_OBLIGATION_TRIGGERS = [
    "应当", "不得", "未经", "除非", "必须", "可以",
    "负责", "承担", "通知", "删除", "返还", "保存",
    "转移", "披露", "提供", "委托", "再转移", "须",
    "应", "确保", "保障", "采取",
]

# ── Split patterns — try trigger‑word split first, fall back to sentence boundary ──

_SPLIT_ON_TRIGGER = re.compile(
    r"(?<=[。；;])\s*(?=" + "|".join(_OBLIGATION_TRIGGERS) + ")",
)

_SPLIT_ON_SEMICOLON = re.compile(r"[；;]")  # split on semicolons only (more conservative)


class ObligationUnit:
    """A single obligation extracted from a clause."""

    def __init__(
        self,
        unit_id: str = "",
        text: str = "",
        obligation_type: str = "general",
        parent_clause_id: str = "",
        parent_file_id: str = "",
    ) -> None:
        self.unit_id = unit_id
        self.text = text
        self.obligation_type = obligation_type  # "prohibition" | "duty" | "permission" | "general"
        self.parent_clause_id = parent_clause_id
        self.parent_file_id = parent_file_id


class ObligationSplitter:
    """Split clauses into obligation units based on semantic triggers."""

    def split_clause(self, clause: Clause) -> list[ObligationUnit]:
        """Split a clause into multiple obligation units."""
        text = clause.text
        if len(text) < 50:
            return [self._make_unit(text, clause)]

        # Split on semicolons (Chinese  ； or ASCII ;) — conservative boundary
        parts = _SPLIT_ON_SEMICOLON.split(text)
        parts = [p.strip() for p in parts if p.strip() and len(p.strip()) >= 10]

        if len(parts) < 2:
            return [self._make_unit(text, clause)]

        units: list[ObligationUnit] = []
        for part in parts:
            unit = self._make_unit(part, clause)
            unit.obligation_type = self._classify_obligation(part)
            units.append(unit)

        return units

    def _make_unit(self, text: str, clause: Clause) -> ObligationUnit:
        return ObligationUnit(
            unit_id=f"OBL-{uuid4().hex[:8]}",
            text=text,
            parent_clause_id=clause.clause_id,
            parent_file_id=clause.file_id,
        )

    @staticmethod
    def _classify_obligation(text: str) -> str:
        """Classify obligation type from text content."""
        text_short = text[:80]
        if any(kw in text_short for kw in ["不得", "禁止", "未经", "不得擅自"]):
            return "prohibition"
        if any(kw in text_short for kw in ["应当", "必须", "负责", "承担", "须"]):
            return "duty"
        if any(kw in text_short for kw in ["可以", "有权"]):
            return "permission"
        return "general"

    def convert_to_clauses(
        self, clause: Clause, units: list[ObligationUnit],
    ) -> list[Clause]:
        """Convert obligation units back to Clause objects for downstream processing."""
        return [
            Clause(
                clause_id=unit.unit_id,
                file_id=clause.file_id,
                text=unit.text,
                heading=clause.heading,
                position=clause.position,
                section_hierarchy=clause.section_hierarchy,
                is_table_content=clause.is_table_content,
                is_appendix_content=clause.is_appendix_content,
            )
            for unit in units
        ]
