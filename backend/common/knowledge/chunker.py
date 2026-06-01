"""Chinese legal structure-aware chunker.

Splits legal documents by their semantic structure — chapter → article →
paragraph → item — rather than by arbitrary token counts.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.common.knowledge.chinese_legal_patterns import (
    LEVEL_ORDER,
    detect_structure,
    extract_title_from_text,
)


@dataclass
class LegalChunk:
    chunk_id: str
    structural_level: str  # chapter, section, article, paragraph, item, text
    structural_path: str  # e.g. "CN-LAW-002/CH5/AR39"
    title: str  # e.g. "个人信息保护法"
    article_no: str  # e.g. "39"
    content: str
    parent_chunk_ids: list[str] = field(default_factory=list)
    page_no: int = 0
    children: list[LegalChunk] = field(default_factory=list)


class ChineseLegalChunker:
    """Split Chinese legal texts into structure-aware chunks.

    Usage:
        chunker = ChineseLegalChunker(source_id="CN-LAW-002", title="个人信息保护法")
        chunks = chunker.chunk(parsed_text)
    """

    def __init__(self, source_id: str = "", title: str = "") -> None:
        self.source_id = source_id
        self.title = title
        self._stack: list[LegalChunk] = []
        self._chunks: list[LegalChunk] = []

    def chunk(
        self,
        text: str,
        *,
        max_article_chars: int = 800,
    ) -> list[LegalChunk]:
        """Split text into legal structure chunks.

        If an article exceeds max_article_chars, it is split into sub-chunks
        (paragraph-level) sharing the same article_id.
        """
        self._stack = []
        self._chunks = []

        # Auto-extract title if not set
        if not self.title:
            extracted = extract_title_from_text(text)
            if extracted:
                self.title = extracted

        lines = text.split("\n")
        buffer: list[str] = []
        current_level: str | None = None

        for line in lines:
            level, label = detect_structure(line)

            if level is not None:
                # Flush buffer as text chunk at current or parent level
                self._flush_buffer(buffer, current_level)
                buffer = []

                # Create a new chunk for this structure boundary
                chunk = self._create_chunk(level, label or line.strip(), line.strip())
                current_level = level
                self._adjust_stack(chunk)
            else:
                if line.strip():
                    buffer.append(line.strip())

        # Flush remaining buffer
        self._flush_buffer(buffer, current_level)

        return list(self._chunks)

    def _create_chunk(self, level: str, label: str, content: str) -> LegalChunk:
        parent_ids = [c.chunk_id for c in self._stack]
        structural_path = self._build_structural_path(level, label)

        article_no = ""
        if level == "article":
            article_no = label.replace("第", "").replace("条", "")

        chunk = LegalChunk(
            chunk_id=f"{self.source_id}/{structural_path}" if self.source_id else structural_path,
            structural_level=level,
            structural_path=structural_path,
            title=self.title,
            article_no=article_no,
            content=content,
            parent_chunk_ids=parent_ids,
        )

        self._chunks.append(chunk)
        return chunk

    def _build_structural_path(self, level: str, label: str) -> str:
        parts: list[str] = []
        for ancestor in self._stack:
            parts.append(self._abbreviate_level(ancestor.structural_level, ancestor.content))
        parts.append(self._abbreviate_level(level, label))
        return "/".join(parts)

    @staticmethod
    def _abbreviate_level(level: str, label: str) -> str:
        """Convert 'article' + '第三十九条' → 'AR39'."""
        prefixes = {
            "chapter": "CH",
            "section": "SEC",
            "article": "AR",
            "paragraph": "PA",
            "item": "IT",
        }
        prefix = prefixes.get(level, "TX")
        # Extract numeric part
        digits = "".join(ch for ch in label if ch.isdigit())
        if not digits:
            # Try Chinese numeral extraction — simplified fallback
            cn_digits = label.replace("第", "").replace("章", "").replace("节", "")
            cn_digits = cn_digits.replace("条", "").replace("款", "").replace(" ", "")
            if not cn_digits:
                cn_digits = "0"
            return f"{prefix}{cn_digits}"
        return f"{prefix}{digits}"

    def _adjust_stack(self, chunk: LegalChunk) -> None:
        level = chunk.structural_level
        # Pop stack until we find a level that can be the parent
        while self._stack:
            top_level = self._stack[-1].structural_level
            if LEVEL_ORDER.get(level, 99) > LEVEL_ORDER.get(top_level, 99):
                break
            self._stack.pop()
        self._stack.append(chunk)

    def _flush_buffer(self, buffer: list[str], current_level: str | None) -> None:
        if not buffer:
            return
        content = "\n".join(buffer)
        level = current_level or "text"

        parent_ids = [c.chunk_id for c in self._stack]
        path_parts = [self._abbreviate_level(c.structural_level, c.content) for c in self._stack]
        path_parts.append("TEXT")
        structural_path = "/".join(path_parts)

        chunk = LegalChunk(
            chunk_id=f"{self.source_id}/{structural_path}" if self.source_id else structural_path,
            structural_level="text",
            structural_path=structural_path,
            title=self.title,
            article_no="",
            content=content,
            parent_chunk_ids=parent_ids,
        )
        self._chunks.append(chunk)
