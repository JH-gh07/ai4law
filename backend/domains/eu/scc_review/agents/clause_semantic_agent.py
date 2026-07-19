"""Agent 3: ClauseSemanticAgent — semantic-level clause comparison vs EU 2021/914.

Goes beyond keyword matching to detect: weakened obligations, discretionary language,
narrowed notification scope, removed regulatory cooperation, limited liability shift.
"""

from __future__ import annotations

import re

from backend.domains.eu.scc_review.agents import SCCAgentBase


class ClauseSemanticAgent(SCCAgentBase):
    agent_name = "eu_scc_clause_semantic"
    max_tokens = 600

    # Obligation weakening patterns (semantic, not just keyword)
    _SEMANTIC_WEAKENING = {
        "notification": [
            (r"as\s+soon\s+as\s+(?:legally\s+)?(?:permissible|practicable|possible)", "Not 'promptly' — conditioned on local legal permissibility"),
            (r"without\s+undue\s+delay\s+(?:to\s+the\s+extent|unless|provided)", "Undue delay qualified by condition"),
            (r"subject\s+to\s+(?:applicable\s+)?(?:local\s+)?law", "Notification obligation subordinated to local law"),
            (r"where\s+(?:it\s+)?deems?\s+(?:it\s+)?(?:necessary|appropriate|relevant)", "Mandatory disclosure turned into discretion"),
        ],
        "information_provision": [
            (r"at\s+(?:its|the\s+(?:data\s+)?importer[´'’]?s)\s+(?:sole\s+)?discretion", "Information provision made discretionary"),
            (r"to\s+the\s+extent\s+(?:reasonably\s+)?(?:practicable|possible|feasible)", "Information scope limited by practicability"),
            (r"(?:may|can)\s+provide\s+(?:relevant\s+)?information", "Mandatory → permissive"),
            (r"such\s+information\s+as\s+(?:it|the\s+importer)\s+(?:considers?|deems?)\s+(?:relevant|appropriate)", "Importer decides what is relevant"),
        ],
        "review_obligation": [
            (r"if\s+it\s+(?:reasonably\s+)?considers?\s+(?:it\s+to\s+be\s+)?(?:appropriate|necessary|relevant|warranted)", "Review obligation weakened to reasonableness test"),
            (r"(?:reserves?\s+the\s+right|may\s+choose|has\s+the\s+option)\s+to\s+(?:review|challenge)", "Obligation turned into option"),
            (r"(?:shall|must|will)\s+not\s+(?:unreasonably\s+)?(?:challenge|review|contest)", "Negative framing — presumption against review"),
        ],
        "regulatory_cooperation": [
            (r"(?:make\s+available|provide)\s+(?:to\s+the\s+competent\s+supervisory\s+authority)?\s*(?:upon\s+request|on\s+demand)", "Limits proactive disclosure to reactive"),
            (r"to\s+the\s+extent\s+(?:required|mandated)\s+by\s+(?:applicable\s+)?law", "Regulatory cooperation subordinated to local law"),
            (r"(?:may|can|shall)\s+(?:not\s+)?(?:be\s+required\s+to\s+)?disclose\s+(?:confidential|proprietary|trade secret)", "Confidentiality override on regulatory disclosure"),
        ],
        "liability_shift": [
            (r"(?:the\s+)?(?:data\s+)?(?:exporter|importer)\s+shall\s+not\s+be\s+(?:liable|responsible)", "Liability exclusion"),
            (r"liability\s+(?:shall\s+be\s+)?(?:limited|capped|restricted)\s+to\s+(?:\d+|EUR|USD|[£$€])", "Liability capped"),
            (r"(?:indirect|consequential|special|punitive|exemplary)\s+damages?\s+(?:shall|are|will)\s+(?:not\s+)?(?:be\s+)?(?:excluded|recoverable)", "Exclusion of consequential damages"),
            (r"maximum\s+(?:aggregate\s+)?liability.*?(?:shall|will)\s+not\s+exceed", "Aggregate liability cap"),
        ],
    }

    def run(self, document: dict, rule_clause_comparison: dict,
            target_clauses: list[int] | None = None) -> dict:
        """Compare user clauses against EU 2021/914 standard semantically."""
        if target_clauses is None:
            target_clauses = [7, 9, 14, 15, 16, 17, 18]

        clauses = document.get("clauses", []) if isinstance(document, dict) else getattr(document, "clauses", [])
        additional_findings: list[dict] = []
        candidate_findings: list[dict] = []
        obligation_matrix: list[dict] = []

        rule_finding_locations = set()
        for f in (rule_clause_comparison.get("findings", []) if isinstance(rule_clause_comparison, dict) else getattr(rule_clause_comparison, "findings", [])):
            loc = f.get("location", "") if isinstance(f, dict) else getattr(f, "location", "")
            rule_finding_locations.add(loc)

        for clause in clauses:
            cdict = clause if isinstance(clause, dict) else {"clause_no": getattr(clause, "clause_no", 0), "content": getattr(clause, "content", ""), "title": getattr(clause, "title", "")}
            clause_no = cdict.get("clause_no", 0)
            if clause_no not in target_clauses:
                continue
            content = cdict.get("content", "")
            if not content:
                continue

            for category, patterns in self._SEMANTIC_WEAKENING.items():
                for pattern, description in patterns:
                    for m in re.finditer(pattern, content, re.IGNORECASE):
                        matched_text = m.group(0)[:150]
                        finding_id = f"EU-SCC-CLAUSE-{clause_no}-SEMANTIC-{category.upper()}"
                        location = f"Clause {clause_no}"
                        if location in rule_finding_locations:
                            continue  # Already caught by rule engine

                        confidence = 0.85 if any(kw in pattern for kw in ("discretion", "shall not", "limited")) else 0.75
                        if confidence >= 0.85:
                            additional_findings.append({"finding_id": finding_id, "location": location, "clause_ref": str(clause_no), "original_text": matched_text, "issue_type": "clause_weakened", "severity": "HIGH", "risk_analysis": f"Semantic weakening ({category}): {description}", "legal_basis": "EU 2021/914 Recital 3; SCC Clause " + str(clause_no) + "; GDPR Article 46", "recommendation": "Restore the standard EU 2021/914 text for this provision.", "confidence": confidence})
                        else:
                            candidate_findings.append({"finding_id": finding_id, "location": location, "matched_text": matched_text, "issue_type": "clause_weakened", "risk_analysis": description, "confidence": confidence})

                        obligation_matrix.append({"clause": str(clause_no), "category": category, "description": description, "matched": matched_text[:80], "confidence": confidence})

        # ── LLM enhancement for clauses with no rule findings but suspicious content ──
        if not additional_findings and len(clauses) >= 2:
            llm_text = "\n".join(str(c.get("content", "")[:500]) if isinstance(c, dict) else getattr(c, "content", "")[:500] for c in clauses if (isinstance(c, dict) and c.get("clause_no") in target_clauses) or (not isinstance(c, dict) and getattr(c, "clause_no", 0) in target_clauses))
            if len(llm_text) > 100:
                llm_result = self._call_llm(f"Review these SCC clauses for potential semantic weakening vs EU 2021/914 standard:\n{llm_text[:3000]}\n\nReturn JSON: {{\"findings\": [{{\"location\": \"Clause X\", \"description\": \"...\", \"severity\": \"HIGH|MEDIUM|LOW\", \"confidence\": 0.0-1.0}}]}}")
                if llm_result and llm_result.get("findings"):
                    for f in llm_result["findings"]:
                        additional_findings.append({"location": f["location"], "risk_analysis": f["description"], "severity": f.get("severity", "MEDIUM"), "confidence": f.get("confidence", 0.7), "source": "llm"})

        return {"additional_findings": additional_findings, "candidate_findings": candidate_findings, "obligation_matrix": obligation_matrix, "findings_added": len(additional_findings)}
