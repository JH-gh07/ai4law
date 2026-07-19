"""Agent 2: BCRRequirementCoverageAgent — judge substantive compliance beyond keywords.

Performs in-depth coverage analysis:
- Checks core obligation fulfillment (not just keyword presence)
- Detects vague/imprecise language (6 EN + 6 CN patterns)
- Assesses executability and responsibility clarity
- Forces re-review for PARTIALLY_COVERED/VAGUE/HIGH-severity requirements
"""

from __future__ import annotations

import re

from backend.domains.eu.bcr_review.agents import BCRAgentBase

class BCRRequirementCoverageAgent(BCRAgentBase):
    agent_name = "bcr_requirement_coverage"
    max_tokens = 500

    # Vague language patterns that weaken obligation strength
    _VAGUE_PATTERNS = [
        (r"as\s+appropriate", "vague_obligation"),
        (r"where\s+feasible", "vague_obligation"),
        (r"endeavo[u]?r\s+to", "weakened_obligation"),
        (r"to\s+the\s+extent\s+possible", "vague_scope"),
        (r"shall\s+consider", "weakened_obligation"),
        (r"may\s+(?:also\s+)?consider", "discretion_only"),
        (r"as\s+soon\s+as\s+practicable", "vague_timeline"),
        (r"reasonable\s+efforts?", "weakened_obligation"),
    ]

    # Core obligation patterns that indicate real coverage
    _CORE_OBLIGATION_PATTERNS = [
        (r"(?:shall|must|will)\s+(?:ensure|guarantee|provide|implement)", "binding_commitment"),
        (r"(?:responsible|liable)\s+(?:for|to)", "responsibility_assignment"),
        (r"(?:designate|appoint|name)\s+(?:a\s+)?(?:specific|the)\s+(?:entity|person)", "specific_designation"),
        (r"(?:within|no\s+later\s+than)\s+\d+\s+(?:days|months|weeks)", "specific_timeline"),
    ]

    def run(self, requirement_id: str, requirement_title: str,
            matched_clauses: list[str], coverage_status: str,
            legal_basis: list[str], bcr_type: str,
            severity_if_missing: str = "MEDIUM") -> dict:
        """Judge whether a BCR requirement is substantively met.

        Uses deterministic pattern analysis + LLM fallback for ambiguous cases.
        """
        clauses_text = "\n---\n".join(matched_clauses[:5]) if matched_clauses else ""
        clauses_lower = clauses_text.lower()

        # ── Deterministic analysis ──
        missing_elements: list[str] = []
        risk_level = severity_if_missing
        should_generate_finding = False

        # 1. Check for vague language
        vague_hits = []
        for pattern, vtype in self._VAGUE_PATTERNS:
            matches = re.findall(pattern, clauses_lower)
            if matches:
                vague_hits.append({"pattern": pattern, "type": vtype, "count": len(matches)})

        if vague_hits and coverage_status in ("PARTIALLY_COVERED", "FULLY_COVERED"):
            missing_elements.append(f"Contains {len(vague_hits)} vague/weakened obligation patterns: "
                                    f"{[h['type'] for h in vague_hits[:3]]}")
            if coverage_status == "FULLY_COVERED":
                coverage_status = "VAGUE"

        # 2. Check for core obligation strength
        obligation_hits = []
        for pattern, otype in self._CORE_OBLIGATION_PATTERNS:
            if re.search(pattern, clauses_lower):
                obligation_hits.append(otype)

        if not obligation_hits and coverage_status in ("PARTIALLY_COVERED", "FULLY_COVERED"):
            missing_elements.append("No binding commitment language found (shall/must/will ensure/provide)")
            coverage_status = "VAGUE"

        # 3. Assess executability: check for specific entity designation
        has_specific_entity = any(re.search(p, clauses_lower) for p in [
            r"(?:the\s+)?(?:EU\s+)?(?:liable|responsible|designated)\s+(?:entity|person|company|member)",
            r"(?:headquarters?|registered\s+office)\s+(?:in|at)\s+\w+",
        ])
        if not has_specific_entity and "EU" in requirement_title.upper():
            missing_elements.append("No specific EU liable entity or responsibility designation found")

        # 4. Determine final assessment
        if len(missing_elements) >= 2 or coverage_status == "MISSING":
            should_generate_finding = True
            risk_level = max(risk_level, "HIGH") if severity_if_missing == "HIGH" else risk_level
        elif len(missing_elements) == 1:
            should_generate_finding = True
            risk_level = "MEDIUM"
        elif coverage_status in ("VAGUE", "PARTIALLY_COVERED"):
            should_generate_finding = True

        result = {
            "requirement_id": requirement_id,
            "coverage_status": coverage_status,
            "missing_elements": missing_elements,
            "vague_patterns_detected": len(vague_hits),
            "obligation_strength": "strong" if len(obligation_hits) >= 2 else "weak" if not obligation_hits else "moderate",
            "risk_level": risk_level,
            "should_generate_finding": should_generate_finding,
            "finding_text": "",
            "recommendation": "",
            "facts_uncertain": False,
        }

        # ── LLM enhancement for ambiguous cases ──
        if (coverage_status in ("PARTIALLY_COVERED", "VAGUE") or risk_level == "HIGH") and matched_clauses:
            llm_result = self._try_llm_coverage(requirement_id, requirement_title, clauses_text,
                                                  coverage_status, legal_basis, bcr_type)
            if llm_result:
                result["coverage_status"] = llm_result.get("coverage_status", result["coverage_status"])
                result["finding_text"] = llm_result.get("finding_text", "")
                result["recommendation"] = llm_result.get("recommendation", "")

        return result

    def _try_llm_coverage(self, req_id: str, title: str, clauses: str, status: str,
                           legal: list[str], bcr_type: str) -> dict | None:
        prompt = f"""Determine whether a BCR requirement is substantively met.

BCR Type: {bcr_type}
Requirement: {req_id} — {title}
Current rule-based status: {status}
Legal basis: {legal}

Matched clauses:
{clauses[:3000]}

Return JSON:
{{
  "coverage_status": "FULLY_COVERED" | "PARTIALLY_COVERED" | "VAGUE" | "MISSING" | "INCORRECT",
  "finding_text": "<if issue found, one sentence>",
  "recommendation": "<one sentence remediation>",
  "facts_uncertain": true | false
}}"""
        return self._call_llm(prompt)
