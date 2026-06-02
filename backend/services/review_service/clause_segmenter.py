"""Enhanced clause segmenter with multi‑language support, section hierarchy,
table detection, and sub‑clause splitting."""

from __future__ import annotations

import re
from uuid import uuid4

from backend.schemas.review import Clause, ClausePosition


# ── Chinese numbering patterns ──────────────────────────────────────────

_CN_CLAUSE_PATTERN = re.compile(
    r"(?=(?:第[一二三四五六七八九十百千万0-9]+条|[0-9]+[\.、]|[一二三四五六七八九十]+、|附录[一二三四五六七八九十]))"
)

_CN_APPENDIX_PATTERN = re.compile(
    r"^(附件[一二三四五六七八九十0-9]*|附录[一二三四五六七八九十0-9]*|附表[一二三四五六七八九十0-9]*)",
    re.IGNORECASE,
)


# ── English / international numbering patterns ───────────────────────────

_EN_CLAUSE_PATTERN = re.compile(
    r"(?=(?:Article\s+\d+|Section\s+\d+|Clause\s+\d+|Appendix\s+[A-Z0-9]+)[\.:\s\)])",
    re.IGNORECASE,
)

# ── Sub‑clause splitting ────────────────────────────────────────────────

_SUBCLAUSE_SPLIT_PATTERN = re.compile(
    r"(?<=[；;])\s*(?=[一-鿿]|[A-Z][a-z])",
)


# ── Structural noise patterns (expanded) ─────────────────────────────────

_SHORT_STRUCTURAL_NOISE_PATTERNS = (
    re.compile(r"^\d+([.)、]|\.\d+)*$"),
    re.compile(r"^(第[一二三四五六七八九十百千万0-9]+[章节条]|[一二三四五六七八九十]+、)$"),
    re.compile(r"^(article|section|clause)\s+\d+(\.\d+)*\.?$", re.IGNORECASE),
    re.compile(r"^(table of contents|contents|目录)$", re.IGNORECASE),
    re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$"),
    re.compile(r"^(https?://|www\.)\S+$", re.IGNORECASE),
    re.compile(r"^[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}$"),
    # NEW: page numbers, signature blocks, separators
    re.compile(r"^[-—–=]{3,}$"),
    re.compile(r"^(甲方|乙方|丙方|签约方).*(签章|盖章|签字|日期)", re.IGNORECASE),
    re.compile(r"^[pP]age\s*\d+", re.IGNORECASE),
    re.compile(r"^\d+\s*/\s*\d+$"),
    re.compile(r"^(\*|※|备注|说明|注|注意)(：|:)?$"),
)

# ── Table detection ─────────────────────────────────────────────────────

_TABLE_LINE_PATTERN = re.compile(
    r"^\s*\|.+\|\s*$"  # Markdown table
)

_TAB_SEPARATED_PATTERN = re.compile(
    r"\t.*\t"  # TSV / tab-separated
)

# ── Section hierarchy extraction ─────────────────────────────────────────

_SECTION_HEADING_PATTERNS = [
    (re.compile(r"^(第[一二三四五六七八九十百千万0-9]+章)\s*(.+)?$"), "chapter"),
    (re.compile(r"^(第[一二三四五六七八九十百千万0-9]+节)\s*(.+)?$"), "section"),
    (re.compile(r"^(第[一二三四五六七八九十百千万0-9]+条)"), "article"),
    (re.compile(r"^(Article\s+[IVXLCDM0-9]+)", re.IGNORECASE), "article"),
    (re.compile(r"^(Section\s+\d+)", re.IGNORECASE), "section"),
    (re.compile(r"^(Appendix\s+[A-Z0-9]+)", re.IGNORECASE), "appendix"),
    (re.compile(r"^(附件[一二三四五六七八九十0-9]*)"), "appendix"),
    (re.compile(r"^(附录[一二三四五六七八九十0-9]*)"), "appendix"),
]


class ClauseSegmenter:
    """Segment document text into structured clauses.

    Supports Chinese and English legal documents, preserving section
    hierarchy and detecting table / appendix content.
    """

    # Public patterns for external use (e.g. service.py noise filter)
    split_pattern = _CN_CLAUSE_PATTERN

    def __init__(self) -> None:
        self._current_hierarchy: list[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def segment(self, file_id: str, text: str) -> list[Clause]:
        """Split *text* into a list of Clause objects."""
        self._current_hierarchy = []

        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        segments = self._split_into_segments(normalized)
        clauses: list[Clause] = []
        position_counter = 0

        for segment in segments:
            if not segment.strip():
                continue

            # Update section hierarchy from headings in this segment
            self._update_hierarchy(segment)

            # Split long segments into sub‑clauses when semantically distinct
            sub_segments = self._split_sub_clauses(segment)

            for sub in sub_segments:
                text_part = sub.strip()
                if not text_part or self._is_noise(text_part):
                    continue

                position_counter += 1
                heading = self._extract_heading(text_part)
                clause_number = self._extract_clause_number(text_part)
                is_table = self._is_table_content(text_part)
                is_appendix = self._is_appendix_content(text_part)
                hierarchy = list(self._current_hierarchy)

                clauses.append(
                    Clause(
                        clause_id=str(uuid4()),
                        file_id=file_id,
                        text=text_part,
                        heading=heading,
                        position=ClausePosition(
                            page=None,
                            paragraph=position_counter,
                            clause_number=clause_number,
                        ),
                        section_hierarchy=hierarchy,
                        is_table_content=is_table,
                        is_appendix_content=is_appendix,
                    )
                )

        return clauses

    # ------------------------------------------------------------------
    # Segmentation
    # ------------------------------------------------------------------

    def _split_into_segments(self, text: str) -> list[str]:
        """Split text into coarse segments using multi‑language patterns."""
        # Try English pattern first (if multiple Article/Section markers found)
        en_markers = len(_EN_CLAUSE_PATTERN.findall(text[:4000]))
        cn_markers = len(_CN_CLAUSE_PATTERN.findall(text[:4000]))

        if en_markers > cn_markers and en_markers >= 2:
            parts = _EN_CLAUSE_PATTERN.split(text)
        else:
            parts = _CN_CLAUSE_PATTERN.split(text)

        parts = [p.strip() for p in parts if p.strip()]
        if not parts:
            return [text.strip()]

        return parts

    def _split_sub_clauses(self, text: str) -> list[str]:
        """Split a clause that contains multiple obligations into sub‑parts.

        Only splits when there are at least 2 sub‑parts and each is at
        least 60 characters long.
        """
        if len(text) < 200:
            return [text]

        parts = _SUBCLAUSE_SPLIT_PATTERN.split(text)
        if len(parts) < 2:
            return [text]

        # Only split if resulting parts are substantial
        substantial = [p.strip() for p in parts if len(p.strip()) >= 60]
        if len(substantial) >= 2:
            return substantial

        return [text]

    # ------------------------------------------------------------------
    # Heading / clause number extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_heading(text: str) -> str | None:
        """Extract heading from the first line (max 120 chars)."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if not lines:
            return None
        first = lines[0]
        return first[:120] if len(first) > 120 else first

    @staticmethod
    def _extract_clause_number(text: str) -> str | None:
        """Extract a legal clause number from the text start."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if not lines:
            return None

        first_line = lines[0]
        for pattern in [
            re.compile(r"^(第[^\s]+条)"),
            re.compile(r"^(\d+[\.、])"),
            re.compile(r"^([一二三四五六七八九十]+、)"),
            re.compile(r"^(Article\s+\d+)", re.IGNORECASE),
            re.compile(r"^(Section\s+\d+)", re.IGNORECASE),
            re.compile(r"^(Clause\s+\d+)", re.IGNORECASE),
            re.compile(r"^(Appendix\s+[A-Z0-9]+)", re.IGNORECASE),
        ]:
            m = pattern.match(first_line)
            if m:
                return m.group(1)

        return None

    # ------------------------------------------------------------------
    # Section hierarchy
    # ------------------------------------------------------------------

    def _update_hierarchy(self, text: str) -> None:
        """Update the current section hierarchy from heading markers in text."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if not lines:
            return

        first_line = lines[0]
        for pattern, level in _SECTION_HEADING_PATTERNS:
            m = pattern.match(first_line)
            if m:
                label = m.group(1)

                # Remove lower-level entries when a higher one is found
                if level == "chapter":
                    self._current_hierarchy = [label]
                elif level == "section" and self._current_hierarchy:
                    # Keep only chapter and add section
                    if len(self._current_hierarchy) > 0:
                        self._current_hierarchy = self._current_hierarchy[:1]
                    self._current_hierarchy.append(label)
                elif level == "article":
                    # Replace previous article-level entry (keep chapter + section)
                    prefix = [h for h in self._current_hierarchy
                              if not (h.startswith("第") and h.endswith("条"))]
                    self._current_hierarchy = prefix + [label]
                    if len(self._current_hierarchy) > 3:
                        self._current_hierarchy = self._current_hierarchy[-3:]
                elif level == "appendix":
                    self._current_hierarchy = [label, "appendix"]
                break

    def get_hierarchy(self) -> list[str]:
        """Return a copy of the current section hierarchy."""
        return list(self._current_hierarchy)

    # ------------------------------------------------------------------
    # Content classification helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_table_content(text: str) -> bool:
        """Check if text appears to be table content."""
        lines = [l for l in text.split("\n") if l.strip()]
        if not lines:
            return False

        # Markdown table
        md_table_lines = sum(1 for l in lines if _TABLE_LINE_PATTERN.match(l))
        if md_table_lines >= 2:
            return True

        # Tab-separated
        tab_lines = sum(1 for l in lines if _TAB_SEPARATED_PATTERN.search(l))
        if tab_lines >= 2:
            return True

        return False

    @staticmethod
    def _is_appendix_content(text: str) -> bool:
        """Check if text appears to be appendix content."""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if not lines:
            return False

        first_line = lines[0]
        return bool(_CN_APPENDIX_PATTERN.match(first_line)) or bool(
            re.match(r"^(Appendix|Annex)\s+[A-Z0-9]+", first_line, re.IGNORECASE)
        )

    @staticmethod
    def _is_noise(text: str) -> bool:
        """Check if the segment is structural noise (page numbers, separators, etc.)."""
        stripped = text.strip()
        if len(stripped) < 3:
            return True
        if len(stripped) >= 64:
            return False
        return any(p.fullmatch(stripped) for p in _SHORT_STRUCTURAL_NOISE_PATTERNS)
