"""AnnotatedDocxBuilder — render DOCX with inline review comments."""

from __future__ import annotations

import logging
from pathlib import Path

from backend.common.render.docx_comments import DocxComment, render_commented_docx
from backend.schemas.review import ReviewIssue

logger = logging.getLogger(__name__)


class AnnotatedDocxBuilder:
    """Build an annotated DOCX with inline review comments from issues.

    Uses the existing render_commented_docx() utility from
    backend/common/render/docx_comments.py.
    """

    def build(
        self,
        source_docx_path: Path,
        issues: list[ReviewIssue],
        output_path: Path,
        author: str = "AI合规审查系统",
        initials: str = "AI",
    ) -> Path:
        """Render an annotated DOCX with issues as inline comments.

        Returns the output path on success, or raises FileNotFoundError
        if the source DOCX doesn't exist.
        """
        if not source_docx_path.exists():
            raise FileNotFoundError(f"Source DOCX not found: {source_docx_path}")

        comments = self._issues_to_comments(issues)
        if not comments:
            logger.info("No issues to annotate in %s", source_docx_path)
            return output_path

        try:
            render_commented_docx(
                source_path=source_docx_path,
                output_path=output_path,
                comments=comments,
                author=author,
                initials=initials,
            )
            logger.info(
                "Annotated DOCX saved to %s with %d comments",
                output_path, len(comments),
            )
        except Exception as exc:
            logger.warning("Failed to render annotated DOCX: %s", exc)
            raise

        return output_path

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _issues_to_comments(issues: list[ReviewIssue]) -> list[DocxComment]:
        """Convert ReviewIssue objects to DocxComment objects."""
        comments: list[DocxComment] = []
        seen: set[tuple[str, str]] = set()

        for issue in issues:
            # Deduplicate by clause text + title
            key = (issue.original_excerpt[:80], issue.title)
            if key in seen:
                continue
            seen.add(key)

            suggestion = ""
            if issue.suggested_revision:
                suggestion = issue.suggested_revision.suggested_text[:300]
            elif issue.recommendation:
                suggestion = issue.recommendation[:300]

            basis = ""
            if issue.citation_sources:
                basis = "；".join(issue.citation_sources[:3])

            comments.append(
                DocxComment(
                    label=f"[{issue.severity.value}] {issue.title[:60]}",
                    basis=basis[:200] if basis else "待补充法规依据",
                    risk_level=issue.severity.value,
                    risk_analysis=issue.risk_analysis[:300],
                    suggestion=suggestion or "待补充修改建议",
                    location="",
                    quote=issue.original_excerpt[:200],
                )
            )

        return comments
