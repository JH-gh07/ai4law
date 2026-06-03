"""Agent 6: BCREvidenceCoverageAgent — distinguish main-text from annex-only coverage.

Checks whether requirements are covered in the BCR main body vs. only in annexes.
Key requirements (EU liable entity, third-party beneficiary, binding mechanism)
must be covered in the main body — annex-only support is flagged as MEDIUM risk.
"""

from __future__ import annotations

import re

from backend.modules.bcr.agents import BCRAgentBase


class BCREvidenceCoverageAgent(BCRAgentBase):
    agent_name = "bcr_evidence_coverage"
    max_tokens = 400

    # Requirements that MUST be in the main body (not just annex)
    _MAIN_BODY_REQUIREMENTS = {
        "BCR-C-1.1",  # Binding nature
        "BCR-C-1.2",  # Third-party beneficiary rights
        "BCR-C-1.3",  # EU liable entity
        "BCR-C-1.4",  # Liability and compensation
        "BCR-P-1.1",  # Binding nature (processor)
    }

    _ANNEX_REFERENCE_PATTERNS = [
        r"(?:see|refer\s+to|as\s+set\s+(?:out|forth)\s+in)\s+(?:Annex|Appendix|Schedule)",
        r"(?:Annex|Appendix|Schedule)\s+(?:[A-Z0-9]+)\s+(?:contains|sets?\s+out|describes)",
        r"(?:detailed|further|specific)\s+(?:in|under|pursuant\s+to)\s+(?:the\s+)?(?:Annex|Appendix)",
    ]

    def run(self, requirement_id: str, main_body_text: str,
            annex_texts: dict[str, str] | None = None,
            coverage_status: str = "FULLY_COVERED") -> dict:
        """Determine if requirement coverage comes from main body or annex only.

        For key requirements, annex-only coverage is flagged.
        """
        # ── 1. Check main body coverage ──
        main_body_lower = main_body_text.lower()
        has_main_body_coverage = len(main_body_lower.strip()) > 50

        # ── 2. Check annex references in main body ──
        annex_refs_in_main: list[str] = []
        for pattern in self._ANNEX_REFERENCE_PATTERNS:
            for m in re.finditer(pattern, main_body_lower):
                annex_refs_in_main.append(m.group(0)[:100])

        # ── 3. Determine coverage source ──
        coverage_source = "inline_covered"
        assessment = ""
        risk_level = "LOW"

        if annex_refs_in_main and not has_main_body_coverage:
            coverage_source = "annex_support_only"
        elif annex_refs_in_main:
            coverage_source = "cross_ref_only"
        elif not has_main_body_coverage:
            coverage_source = "missing"

        # ── 4. Flag key requirements that are annex-only ──
        is_key_requirement = requirement_id in self._MAIN_BODY_REQUIREMENTS

        if coverage_source in ("annex_support_only", "cross_ref_only"):
            if is_key_requirement:
                risk_level = "MEDIUM"
                assessment = (
                    f"Requirement {requirement_id} is a key BCR obligation but its coverage "
                    f"appears to be in annexes only (not in the main body). "
                    f"The main body should directly state the obligation, not just reference an annex."
                )
            else:
                risk_level = "LOW"
                assessment = (
                    f"Coverage is via annex reference — this may be acceptable for "
                    f"non-core requirements, but direct main-body coverage is preferred."
                )
        elif coverage_source == "missing":
            risk_level = "HIGH" if is_key_requirement else "MEDIUM"
            assessment = (
                f"Requirement {requirement_id} has no detectable coverage in main body or annexes."
            )
        else:
            assessment = f"Requirement {requirement_id} is covered inline in the main body."

        return {
            "requirement_id": requirement_id,
            "coverage_source": coverage_source,
            "is_key_requirement": is_key_requirement,
            "annex_references_detected": len(annex_refs_in_main),
            "assessment": assessment,
            "risk_level": risk_level,
        }
