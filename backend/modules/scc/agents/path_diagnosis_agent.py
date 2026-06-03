"""P0 Agent 1: PathDiagnosisAgent — resolve "standard contract / certification / exemption / security assessment" routing.

Solves the core problem: the system cannot currently determine which path applies like a compliance lawyer would.
Handles 5 types of path judgments:
  1. Whether standard contract applies
  2. Whether certification path may apply
  3. Whether HR management exemption applies
  4. Whether security assessment is triggered by scale / important data / CIIO / sensitive PI
  5. Whether there is concept confusion (e.g. EuroCert vs Chinese certification)

Reference: doc/tmp/认证标准合同路径 Section 1
"""

from __future__ import annotations

from backend.modules.scc.agents import SCCAgentBase
from backend.modules.scc.rule_engine import evaluate_hard_thresholds, determine_path
from backend.modules.scc.schema import LegalBasis, PathDiagnosisInput, PathDiagnosisResult, PathType


class PathDiagnosisAgent(SCCAgentBase):
    agent_name = "cn_scc_path_diagnosis"
    max_tokens = 800

    def run(
        self,
        diagnosis_input: PathDiagnosisInput,
        rule_result: dict | None = None,
    ) -> dict:
        """Execute path diagnosis with LLM reasoning on top of rule engine results.

        The rule engine handles hard thresholds; the agent handles:
        - Misrouting detection (user thinks it's certification but it's really not)
        - Exemption evidence adequacy
        - Concept confusion (EuroCert vs Chinese certification)
        - Confidence calibration
        """
        # Build rule-based baseline
        rule = evaluate_hard_thresholds(diagnosis_input)
        baseline = determine_path(diagnosis_input, rule)

        if not self.enabled:
            return baseline.model_dump()

        # ── Build LLM prompt for nuanced judgment ──
        legal_basis_str = ", ".join(lb.value for lb in diagnosis_input.legal_basis) if diagnosis_input.legal_basis else "未提供"

        prompt = f"""Diagnose the correct cross-border data transfer path under Chinese law.

INPUT FACTS:
- Company: {diagnosis_input.company_name}
- CIIO: {diagnosis_input.is_ciio}
- Important Data: {diagnosis_input.has_important_data}
- PII Count: {diagnosis_input.pii_count:,}
- SPI Count: {diagnosis_input.spi_count:,}
- Transfer Purpose: {diagnosis_input.transfer_purpose}
- Legal Basis: {legal_basis_str}
- Receiver: {diagnosis_input.receiver_type.value} in {diagnosis_input.receiver_country}
- Industry: {diagnosis_input.industry}
- HR Management: {diagnosis_input.is_hr_management}
- Certification Body: {diagnosis_input.is_certification_body}
- Has SCC Draft: {diagnosis_input.has_scc_draft}
- Has Certification Material: {diagnosis_input.has_certification_material}
- Has Exemption Material: {diagnosis_input.has_exemption_material}

RULE ENGINE BASELINE:
- Recommended Path: {baseline.recommended_path}
- Triggers Security Assessment: {rule.triggers_security_assessment}
- HR Exemption Possible: {rule.hr_exemption_possible}
- Confidence: {baseline.confidence}
- Blocking Issues: {baseline.blocking_issues}

TASKS:
1. Verify the rule engine baseline — is the recommended path correct or does nuance change it?
2. Check for "concept confusion": user claiming "certification" path but referring to EuroCert/business certification, not Chinese PIPL certification
3. Assess whether exemption evidence is adequate (especially HR management exemption requiring bylaws, collective agreements, democratic procedures)
4. Calibrate confidence based on information completeness

Return JSON:
{{
  "recommended_path": "standard_contract" | "certification" | "exemption" | "security_assessment" | "uncertain",
  "alternative_path": "standard_contract" | "certification" | "exemption" | "security_assessment" | null,
  "confidence": 0.0-1.0,
  "rationale": "<2-3 sentences explaining the reasoning>",
  "blocking_issues": ["issue1", "issue2"],
  "next_questions": ["question1", "question2"],
  "triggered_thresholds": ["threshold1"],
  "exemption_assessment": "<1 sentence on exemption viability>",
  "concept_confusion_detected": true | false,
  "concept_confusion_detail": "<if detected, explain>",
  "overrides_rule_baseline": true | false,
  "override_reason": "<if overriding, explain why>"
}}"""

        result = self._call_llm(prompt) or {
            "recommended_path": baseline.recommended_path,
            "alternative_path": baseline.alternative_path,
            "confidence": baseline.confidence,
            "rationale": baseline.rationale,
            "blocking_issues": baseline.blocking_issues,
            "next_questions": baseline.next_questions,
            "triggered_thresholds": baseline.triggered_thresholds,
            "exemption_assessment": baseline.exemption_assessment,
            "concept_confusion_detected": False,
            "concept_confusion_detail": "",
            "overrides_rule_baseline": False,
            "override_reason": "",
        }

        # Ensure required fields
        result.setdefault("recommended_path", baseline.recommended_path)
        result.setdefault("confidence", baseline.confidence)
        result.setdefault("blocking_issues", baseline.blocking_issues)
        result.setdefault("next_questions", baseline.next_questions)
        result.setdefault("triggered_thresholds", baseline.triggered_thresholds)
        result.setdefault("exemption_assessment", baseline.exemption_assessment)
        result.setdefault("rationale", baseline.rationale)
        result.setdefault("alternative_path", baseline.alternative_path)
        result.setdefault("concept_confusion_detected", False)
        result.setdefault("concept_confusion_detail", "")
        result.setdefault("overrides_rule_baseline", False)
        result.setdefault("override_reason", "")

        return result
