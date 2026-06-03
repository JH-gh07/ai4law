"""Agent 5: BCRTiaReasoningAgent — assess TIA completeness per EDPB 01/2020 six-step method.

Evaluates whether the TIA forms a complete, executable assessment mechanism:
- Checks EDPB 01/2020 six-step coverage
- Evaluates review frequency, responsible party, documentation requirements
- Assesses supplementary measures and suspension mechanism
"""

from __future__ import annotations

import re

from backend.modules.bcr.agents import BCRAgentBase


class BCRTiaReasoningAgent(BCRAgentBase):
    agent_name = "bcr_tia_reasoning"
    max_tokens = 500

    # EDPB 01/2020 six-step method checklist
    _SIX_STEP_CHECKS: dict[str, dict] = {
        "step1_factual_assessment": {
            "label": "Step 1: Factual assessment & transfer mapping",
            "patterns": [
                r"(?:transfer\s+)?(?:mapping|inventory|assessment)\s+of\s+(?:the\s+)?(?:data\s+)?transfers?",
                r"(?:identif(?:y|ied|ies)\s+)?(?:all\s+)?(?:data\s+)?(?:flows?|transfers?)",
                r"(?:categor(?:y|ies|ized)\s+)?(?:of\s+)?(?:data\s+)?(?:recipients?|destinations?)",
            ],
        },
        "step2_transfer_tool": {
            "label": "Step 2: Assessment of transfer tool",
            "patterns": [
                r"(?:transfer\s+tool|SCC|adequacy|BCR|article\s+46|article\s+47)",
                r"(?:legal\s+basis\s+for\s+(?:the\s+)?transfer)",
                r"(?:appropriate\s+safeguards?\s+(?:under|pursuant\s+to)\s+(?:GDPR|Article))",
            ],
        },
        "step3_third_country_law": {
            "label": "Step 3: Third country law assessment",
            "patterns": [
                r"(?:third\s+country|local|destination\s+country)\s+(?:law|legislation|legal\s+framework)",
                r"(?:government\s+access|surveillance|national\s+security|law\s+enforcement)",
                r"(?:assess(?:ment|ed)\s+(?:of\s+)?(?:the\s+)?(?:laws?\s+and\s+practices?|legal\s+environment))",
                r"(?:Schrems\s+II|C-311/18|FISA|CLOUD\s+Act|intelligence)",
            ],
        },
        "step4_supplementary_measures": {
            "label": "Step 4: Supplementary measures identification",
            "patterns": [
                r"(?:supplement(?:ary|al)\s+measures?)",
                r"(?:additional\s+(?:technical|organi[sz]ational|contractual)\s+measures?)",
                r"(?:end.to.end\s+encryption|zero.access|hold\s+your\s+own\s+key)",
                r"(?:mitigation|compensat(?:e|ing)\s+(?:measures?|controls?))",
            ],
        },
        "step5_procedural_steps": {
            "label": "Step 5: Procedural steps & documentation",
            "patterns": [
                r"(?:document(?:ed|ation)\s+(?:of|for)\s+(?:the\s+)?(?:assessment|TIA))",
                r"(?:record(?:ed|s?\s+of)\s+(?:the\s+)?(?:assessment|evaluation))",
                r"(?:approv(?:al|ed)\s+(?:by|from)\s+(?:DPO|management|board))",
            ],
        },
        "step6_reassessment": {
            "label": "Step 6: Reassessment mechanism",
            "patterns": [
                r"(?:re.?assess(?:ment)?|periodic\s+review|regular\s+(?:review|assessment))",
                r"(?:at\s+least\s+(?:annually|yearly|every\s+\d+\s+(?:year|month)))",
                r"(?:upon\s+(?:material\s+)?(?:change|amendment))",
            ],
        },
    }

    def run(self, tia_text: str, has_tia_document: bool = False) -> dict:
        """Assess TIA completeness against EDPB 01/2020 six-step method."""
        if not tia_text and not has_tia_document:
            return {
                "tia_completeness": "missing",
                "missing_elements": ["No TIA text or document provided"],
                "edpb_method_used": False,
                "suggested_revision_points": [
                    "Complete a full Transfer Impact Assessment per EDPB Recommendations 01/2020",
                    "Document all six steps of the EDPB methodology",
                ],
                "step_coverage": {k: False for k in self._SIX_STEP_CHECKS},
            }

        text_lower = tia_text.lower()
        step_coverage: dict[str, bool] = {}
        missing_elements: list[str] = []
        covered_steps = 0

        for step_key, step_config in self._SIX_STEP_CHECKS.items():
            patterns = step_config.get("patterns", [])
            matched = any(re.search(p, text_lower) for p in patterns)
            step_coverage[step_key] = matched
            if matched:
                covered_steps += 1
            else:
                missing_elements.append(step_config["label"])

        # ── Determine completeness ──
        if covered_steps >= 5:
            completeness = "complete"
        elif covered_steps >= 3:
            completeness = "partial"
        else:
            completeness = "incomplete"

        edpb_method_used = "EDPB" in tia_text or "six.step" in text_lower or "6.step" in text_lower

        # ── Additional checks ──
        extra_checks: list[str] = []
        has_supplementary = step_coverage.get("step4_supplementary_measures", False)
        has_reassessment = step_coverage.get("step6_reassessment", False)
        has_third_country = step_coverage.get("step3_third_country_law", False)

        if not has_supplementary:
            extra_checks.append("Add supplementary measures section covering technical, "
                                 "contractual, and organizational measures")
        if not has_reassessment:
            extra_checks.append("Add periodic reassessment mechanism "
                                "(at least annually or upon material change)")
        if not has_third_country:
            extra_checks.append("Add third country law and practice assessment, "
                                "including government access analysis")

        risk_level = "HIGH" if completeness == "incomplete" else ("MEDIUM" if completeness == "partial" else "LOW")

        # ── LLM enhancement for partial/incomplete ──
        llm_suggestions: list[str] = []
        if completeness in ("partial", "incomplete"):
            llm_result = self._try_llm_tia(tia_text, completeness, missing_elements)
            if llm_result:
                llm_suggestions = llm_result.get("suggested_revision_points", [])

        return {
            "tia_completeness": completeness,
            "steps_covered": covered_steps,
            "total_steps": len(self._SIX_STEP_CHECKS),
            "missing_elements": missing_elements,
            "edpb_method_used": edpb_method_used,
            "suggested_revision_points": extra_checks + llm_suggestions,
            "risk_level": risk_level,
            "step_coverage": step_coverage,
        }

    def _try_llm_tia(self, tia_text: str, completeness: str,
                     missing: list[str]) -> dict | None:
        prompt = f"""Assess this TIA text for EDPB 01/2020 completeness.

Current assessment: {completeness}
Missing steps: {missing}

TIA text (first 2500 chars):
{tia_text[:2500]}

Return JSON:
{{
  "suggested_revision_points": ["point1", "point2", "point3"],
  "should_generate_finding": true | false
}}"""
        return self._call_llm(prompt)
