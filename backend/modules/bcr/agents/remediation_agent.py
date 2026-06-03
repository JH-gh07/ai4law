"""Agent 10: BCRRemediationAgent — generate actionable, insertable fix suggestions.

Produces specific clause text tailored to the document language, BCR type, and
the specific requirement deficiency. Goes beyond generic template recommendations.
"""

from __future__ import annotations

from backend.modules.bcr.agents import BCRAgentBase


class BCRRemediationAgent(BCRAgentBase):
    agent_name = "bcr_remediation"
    max_tokens = 400

    _REMEDIATION_TEMPLATES: dict[str, dict] = {
        "BCR-C-1.1": {
            "fix_type": "REPLACE_CLAUSE",
            "insert_location": "Chapter: Binding Nature / Section 1",
            "suggested_text": (
                "These Binding Corporate Rules constitute a legally binding instrument "
                "that is enforceable by all BCR members against each other and by data "
                "subjects as third-party beneficiaries. Each BCR member shall enter into "
                "an intra-group agreement that expressly incorporates these Rules and "
                "creates binding obligations under the law of [EU Member State]."
            ),
            "rationale": "GDPR Article 47(1)(a) requires a legally binding instrument "
                         "that applies to and is enforced by every group member.",
        },
        "BCR-C-1.2": {
            "fix_type": "INSERT_CLAUSE",
            "insert_location": "After Chapter: Scope and Application",
            "suggested_text": (
                "Data subjects shall have the right to enforce these Rules as "
                "third-party beneficiaries against the EU liable entity and any "
                "BCR member. This right includes: (a) the right to lodge a complaint "
                "with the competent supervisory authority; (b) the right to an "
                "effective judicial remedy; and (c) the right to claim compensation "
                "for damages suffered as a result of a breach of these Rules."
            ),
            "rationale": "GDPR Article 47(1)(b) requires that BCR expressly confer "
                         "enforceable third-party beneficiary rights on data subjects.",
        },
        "BCR-C-1.3": {
            "fix_type": "INSERT_CLAUSE",
            "insert_location": "Chapter: Liability and Enforcement",
            "suggested_text": (
                "[Company Name], established in [EU Member State], shall act as the "
                "EU liable entity and shall: (a) accept responsibility for and "
                "guarantee compliance with these Rules by all BCR members; "
                "(b) assume the burden of proof that a BCR member has not violated "
                "these Rules; (c) maintain sufficient assets within the EU to meet "
                "any compensation claims by data subjects."
            ),
            "rationale": "GDPR Article 47(1)(f) and 47(2)(a) require designation of "
                         "a specific EU entity with delegated liability.",
        },
        "BCR-C-1.4": {
            "fix_type": "REPLACE_CLAUSE",
            "insert_location": "Chapter: Liability and Compensation",
            "suggested_text": (
                "The EU liable entity shall be liable for any breach of these Rules "
                "by any BCR member and shall pay compensation for both material and "
                "non-material damage resulting from such breach. The EU liable entity "
                "shall not use the defence that the damage was caused by another "
                "BCR member to avoid liability. Any BCR member that has paid "
                "compensation shall have the right to recover from other BCR members "
                "the portion of compensation corresponding to their part of "
                "responsibility for the damage."
            ),
            "rationale": "GDPR Article 47(1)(f) requires that the EU liable entity "
                         "accepts full liability for breaches by any BCR member.",
        },
        "_default": {
            "fix_type": "ADD_CHAPTER",
            "insert_location": "New chapter after existing obligations",
            "suggested_text": (
                "[Insert specific clause addressing the identified requirement "
                "in accordance with GDPR Article 47 and EDPB Recommendations]"
            ),
            "rationale": "See specific BCR requirement for detailed guidance.",
        },
    }

    def run(self, requirement_id: str, clause_text: str = "",
            bcr_type: str = "BCR-C", finding_text: str = "",
            legal_basis: str = "", document_language: str = "en") -> dict:
        """Generate actionable remediation for a BCR finding.

        Returns fix_type, insert location, suggested_text, and rationale.
        Uses built-in templates + LLM customization for tailors fixes.
        """
        template = self._REMEDIATION_TEMPLATES.get(
            requirement_id,
            self._REMEDIATION_TEMPLATES["_default"]
        )

        result = {
            "requirement_id": requirement_id,
            "fix_type": template["fix_type"],
            "insert_location": template["insert_location"],
            "suggested_text": template["suggested_text"],
            "rationale": template["rationale"],
        }

        # LLM enhancement to tailor the suggested_text to the specific finding
        if finding_text and clause_text:
            llm_result = self._try_llm_remediation(
                requirement_id, clause_text[:2000], finding_text, legal_basis, bcr_type
            )
            if llm_result:
                if llm_result.get("suggested_text"):
                    result["suggested_text"] = llm_result["suggested_text"]
                if llm_result.get("rationale"):
                    result["rationale"] = llm_result["rationale"]
                if llm_result.get("fix_type"):
                    result["fix_type"] = llm_result["fix_type"]

        return result

    def _try_llm_remediation(self, req_id: str, clause: str, finding: str,
                              legal: str, bcr_type: str) -> dict | None:
        prompt = f"""Generate a specific remediation clause for this BCR finding.

BCR Type: {bcr_type}
Requirement: {req_id}
Finding: {finding}
Legal basis: {legal}

Original clause text (for context):
{clause}

Generate a specific, insertable clause text that addresses the deficiency.
Use the same language style as the original document.

Return JSON:
{{
  "fix_type": "INSERT_CLAUSE" | "REPLACE_CLAUSE" | "DELETE_CLAUSE" | "ADD_CHAPTER" | "CLARIFY",
  "insert_location": "<specific chapter or section>",
  "suggested_text": "<the full clause text to insert>",
  "rationale": "<why this fixes the requirement>"
}}"""
        return self._call_llm(prompt)
