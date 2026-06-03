"""Agent 4: Legal citation validation — checks citation relevance and support level."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from backend.modules.assessment.citation_quality import (
    CitationSupportLevel,
    validate_citation_for_issue,
    validate_all_citations,
    filter_external_citations,
    get_weak_citation_warnings,
)


@dataclass
class CitationValidationReport:
    validations: list = field(default_factory=list)
    weak_citations: list[str] = field(default_factory=list)
    external_ready_citations: list = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class LegalCitationAgent:
    """Validates citation quality and recommends improvements."""

    def run(self, issues: list, legal_grounding: dict | None, regulations: list | None = None) -> CitationValidationReport:
        """Validate all citations against issue requirements."""
        validations = validate_all_citations(issues, legal_grounding)
        weak = get_weak_citation_warnings(validations)
        external = filter_external_citations(validations)

        recommendations: list[str] = []
        for v in validations:
            if v.support_level in ("background_only", "irrelevant"):
                recommendations.append(
                    f"Issue '{v.issue_id}': citation '{v.citation_title} {v.citation_article}' "
                    f"is {v.support_level}. Consider replacing with a more specific article."
                )

        return CitationValidationReport(
            validations=validations,
            weak_citations=weak,
            external_ready_citations=external,
            recommendations=recommendations,
        )

    def run_with_llm(self, issues: list, legal_grounding: dict | None, llm_client: Any, regulations: list | None = None) -> CitationValidationReport:
        """Enhanced validation with LLM suggestions for weak citations."""
        report = self.run(issues, legal_grounding, regulations)

        if not llm_client or not getattr(llm_client, "enabled", False) or not report.recommendations:
            return report

        prompt = (
            "The following citation issues were found in a Chinese data export security assessment:\n"
            + "\n".join(report.recommendations[:5]) +
            "\n\nFor each issue, suggest the most appropriate Chinese legal article to cite. "
            "Return JSON array with fields: issue_id, suggested_citation_title, suggested_citation_article, reason."
        )

        try:
            raw = llm_client.chat(system="You are a Chinese data protection law expert.", user=prompt, temperature=0.1, max_tokens=500)
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(parsed, list):
                for item in parsed:
                    report.recommendations.append(
                        f"Suggestion for {item.get('issue_id')}: "
                        f"{item.get('suggested_citation_title')} {item.get('suggested_citation_article')} — {item.get('reason')}"
                    )
        except (json.JSONDecodeError, Exception):
            pass

        return report
