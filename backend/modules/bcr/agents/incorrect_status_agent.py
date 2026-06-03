"""Agent 7: BCRIncorrectStatusAgent — detect "wrote it but got it wrong" patterns.

Detects clauses that exist but are directionally incorrect or misassign responsibility:
- BCR-C document containing processor-specific clauses
- Data subject rights pointing to client instead of BCR entity
- Third-party beneficiary rights not including data subjects
"""

from __future__ import annotations

import re

from backend.modules.bcr.agents import BCRAgentBase


class BCRIncorrectStatusAgent(BCRAgentBase):
    agent_name = "bcr_incorrect_status"
    max_tokens = 400

    # Patterns indicating INCORRECT status for BCR-C documents
    _BCR_C_INCORRECT_PATTERNS = [
        (r"(?:data\s+)?subject(?:s|[´'’]?\s+rights?)\s+(?:shall|must|are|may)\s+(?:be\s+)?(?:exercised|enforced)\s+(?:against|with|through)\s+(?:the\s+)?(?:client|processor)",
         "数据主体权利指向客户/处理者而非BCR承担方", "HIGH"),
        (r"(?:the\s+)?(?:client|data\s+controller)\s+(?:shall|must|will|is\s+responsible)\s+(?:ensure|guarantee|provide)\s+(?:compliance|protection)",
         "将合规责任转嫁给客户控制者", "HIGH"),
        (r"third.party\s+beneficiary\s+rights?\s+(?:shall|must|do)\s+not\s+(?:apply|extend)\s+to",
         "第三方受益人权利被排除或限制", "HIGH"),
        (r"(?:on\s+behalf\s+of|according\s+to\s+instructions|as\s+a\s+processor)",
         "BCR-C文档中出现处理者条款表述", "MEDIUM"),
    ]

    # Patterns for role mismatch
    _ROLE_MISMATCH_PATTERNS = [
        (r"(?:the\s+)?(?:data\s+)?exporter\s+(?:shall|must|will)\s+(?:process|handle)\s+(?:personal\s+)?data\s+(?:on\s+behalf|according\s+to)",
         "将输出方角色从控制者改写为处理者"),
        (r"(?:the\s+)?(?:group|BCR\s+members?)\s+(?:shall|must|will)\s+only\s+process.*(?:on\s+behalf|as\s+instructed)",
         "将集团成员角色限制为处理者"),
    ]

    def run(self, clause_text: str, requirement_id: str, bcr_type: str,
            coverage_status: str = "FULLY_COVERED",
            entity_roles: list[dict] | None = None) -> dict:
        """Detect clauses that are incorrect or misassigned.

        Key question: is the clause directionally correct, or does it point
        responsibility to the wrong entity?
        """
        text_lower = clause_text.lower()
        findings: list[dict] = []
        has_incorrect = False
        risk_level = "LOW"

        # ── Only check INCORRECT patterns if coverage_status suggests content exists ──
        if coverage_status not in ("FULLY_COVERED", "PARTIALLY_COVERED", "VAGUE"):
            return {
                "coverage_status": coverage_status,
                "has_incorrect": False,
                "findings": [],
                "risk_level": "LOW",
            }

        # ── BCR-C specific incorrect patterns ──
        if bcr_type == "BCR-C":
            for pattern, description, severity in self._BCR_C_INCORRECT_PATTERNS:
                matches = re.findall(pattern, text_lower)
                if matches:
                    findings.append({
                        "pattern": pattern[:80],
                        "description": description,
                        "severity": severity,
                        "matched_text": matches[0][:120] if isinstance(matches[0], str) else str(matches[0])[:120],
                    })
                    has_incorrect = True
                    if severity == "HIGH":
                        risk_level = "HIGH"
                    elif risk_level != "HIGH":
                        risk_level = severity

        # ── Role mismatch patterns (any BCR type) ──
        for pattern, description in self._ROLE_MISMATCH_PATTERNS:
            matches = re.findall(pattern, text_lower)
            if matches:
                findings.append({
                    "pattern": pattern[:80],
                    "description": description,
                    "severity": "MEDIUM",
                    "matched_text": matches[0][:120] if isinstance(matches[0], str) else str(matches[0])[:120],
                })
                has_incorrect = True
                if risk_level == "LOW":
                    risk_level = "MEDIUM"

        # ── Determine updated coverage status ──
        updated_status = "INCORRECT" if has_incorrect else coverage_status

        # ── LLM enhancement for ambiguous cases ──
        if has_incorrect and risk_level in ("HIGH", "MEDIUM"):
            llm_result = self._try_llm_incorrect(clause_text, requirement_id, bcr_type, findings)
            if llm_result:
                if llm_result.get("additional_findings"):
                    findings.extend(llm_result["additional_findings"])

        return {
            "coverage_status": updated_status,
            "has_incorrect": has_incorrect,
            "findings": findings,
            "risk_level": risk_level,
            "finding_summary": (
                f"Found {len(findings)} incorrect/misassigned clause(s): "
                f"{[f['description'][:60] for f in findings]}"
            ) if findings else "No incorrect patterns detected.",
        }

    def _try_llm_incorrect(self, clause_text: str, req_id: str,
                            bcr_type: str, findings: list[dict]) -> dict | None:
        prompt = f"""Review these potential INCORRECT clause findings for a {bcr_type} document.

Requirement: {req_id}
Findings detected: {[f['description'] for f in findings]}

Clause text:
{clause_text[:2000]}

Return JSON:
{{
  "additional_findings": [
    {{"description": "<finding>", "severity": "HIGH" | "MEDIUM" | "LOW",
      "matched_text": "<quote>"}}
  ],
  "overall_assessment": "<1 sentence>"
}}"""
        return self._call_llm(prompt)
