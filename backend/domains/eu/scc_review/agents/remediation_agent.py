"""Agent 6: RemediationAgent — generate actionable, insertable clause-level fix suggestions.

Produces specific clause text, target location, fix type, and priority for each finding.
Uses built-in templates per finding type + LLM customization for tailored wording.
"""

from __future__ import annotations

from backend.domains.eu.scc_review.agents import SCCAgentBase


class RemediationAgent(SCCAgentBase):
    agent_name = "eu_scc_remediation"
    max_tokens = 500

    _REMEDIATION_TEMPLATES = {
        "module_mismatch": {"fix_type": "REPLACE_HEADER", "insert_location": "Document Header / Module Type declaration", "suggested_text": "Change the declared module from {actual} to {expected}. Update exporter/importer role descriptions in Annex I.A to match the correct module.", "priority": "P0", "rationale": "Module selection error invalidates the entire SCC structure."},
        "clause_weakened": {"fix_type": "RESTORE_CLAUSE", "insert_location": "Clause {clause_ref}", "suggested_text": "Restore the standard EU 2021/914 text for this provision without modifications. If additional safeguards beyond the standard clause are desired, add them as a separate annex that does not conflict with the SCC.", "priority": "P0", "rationale": "Weakened SCC clauses violate the invariability principle (Recital 3)."},
        "clause_deleted": {"fix_type": "REINSERT_CLAUSE", "insert_location": "After Clause {clause_no - 1}", "suggested_text": "Reinsert the deleted standard clause per EU 2021/914.", "priority": "P0", "rationale": "Deleted SCC clauses may render the entire SCC ineffective."},
        "annex_incomplete": {"fix_type": "COMPLETE_ANNEX", "insert_location": "Annex {location}", "suggested_text": "Complete all required fields in this annex. Ensure party names, addresses, contacts, and roles are entered directly (not by reference to external agreements).", "priority": "P1", "rationale": "Incomplete Annexes prevent regulatory review and may cause rejection of the SCC."},
        "annex_vague": {"fix_type": "CLARIFY_ANNEX", "insert_location": "Annex I.B", "suggested_text": "Replace vague data category descriptions with specific categories. For example, 'order history data' should be broken down into: products purchased, dates of purchase, transaction values, payment status, delivery information.", "priority": "P1", "rationale": "Vague data categories do not meet GDPR Article 5(1)(c) specificity requirements."},
        "special_category_misclassified": {"fix_type": "CORRECT_CLASSIFICATION", "insert_location": "Annex I.B", "suggested_text": "Mark health/medical/biometric/genetic data as special categories under GDPR Article 9. In Annex I.B, explicitly state the Article 9(2) exemption relied upon and any additional safeguards.", "priority": "P0", "rationale": "Misclassification of special category data undermines the entire transfer's legal basis."},
        "tia_missing": {"fix_type": "CREATE_TIA", "insert_location": "New document: Transfer Impact Assessment", "suggested_text": "Complete a Transfer Impact Assessment per EDPB Recommendations 01/2020 covering: (1) factual assessment of transfers, (2) assessment of transfer tool, (3) third country law analysis (government access, surveillance laws), (4) supplementary measures identification and effectiveness evaluation, (5) procedural steps, (6) reassessment mechanism.", "priority": "P0", "rationale": "TIA is mandatory for transfers to non-adequate third countries under Schrems II."},
        "supplementary_measures_insufficient": {"fix_type": "ADD_MEASURES", "insert_location": "Annex II", "suggested_text": "Add: (Technical) End-to-end encryption with EU-held keys (BYOK/HYOK), zero-access architecture. (Contractual) Government access notification obligation, commitment to challenge unlawful requests, transparency reporting. (Organizational) Independent annual audit, comprehensive access logging, separation of duties for key management.", "priority": "P0", "rationale": "Insufficient supplementary measures expose the transfer to government access under third country surveillance laws."},
        "sub_processor_chain_incomplete": {"fix_type": "COMPLETE_SUBPROCESSOR_LIST", "insert_location": "Annex III", "suggested_text": "List all sub-processors with name, address, processing activities, and location. Include cloud providers (AWS/Azure/GCP) if they process or store personal data. Add Clause 9 authorization mechanism.", "priority": "P1", "rationale": "Incomplete sub-processor chains create uncontrolled onward transfer risks."},
        "party_info_incomplete": {"fix_type": "COMPLETE_PARTY_INFO", "insert_location": "Annex I.A", "suggested_text": "Enter all party information directly in Annex I.A. Do not reference external documents (MSA, DPA) as substitutes for required information.", "priority": "P1", "rationale": "Annex I.A must contain complete party information per EU 2021/914."},
    }

    def run(self, findings: list, evidence: list | None = None,
            document: dict | None = None, transfer_chain: dict | None = None,
            module_validation: dict | None = None) -> dict:
        """Generate actionable remediation suggestions for each finding."""
        patched_findings: list = []
        action_plan: list[dict] = []

        for i, f in enumerate(findings):
            fdict = f if isinstance(f, dict) else {"finding_id": getattr(f, "finding_id", ""), "location": getattr(f, "location", ""), "clause_ref": getattr(f, "clause_ref", ""), "issue_type": getattr(f, "issue_type", "other"), "severity": getattr(f, "severity", "MEDIUM"), "recommendation": getattr(f, "recommendation", ""), "risk_analysis": getattr(f, "risk_analysis", "")}
            issue_type = fdict.get("issue_type", "other")
            template = self._REMEDIATION_TEMPLATES.get(issue_type, {"fix_type": "REVIEW", "insert_location": "See finding location", "suggested_text": "Address this finding per the recommendation in the review report.", "priority": "P2", "rationale": "See detailed review."})

            clause_ref = fdict.get("clause_ref", "")
            location = fdict.get("location", "")

            # Fill template variables
            if isinstance(module_validation, dict):
                actual_mod = module_validation.get("actual_module", "unknown")
                expected_mod = module_validation.get("expected_module", "unknown")
                sg_text = template["suggested_text"].replace("{actual}", actual_mod).replace("{expected}", expected_mod)
            else:
                sg_text = template["suggested_text"]

            sg_text = sg_text.replace("{clause_ref}", str(clause_ref)).replace("{location}", location).replace("{clause_no}", str(clause_ref) if clause_ref.isdigit() else "N")

            action_plan.append({"priority": template["priority"], "finding_id": fdict.get("finding_id", f"finding-{i}"), "task": sg_text[:120], "fix_type": template["fix_type"], "insert_location": template["insert_location"].replace("{clause_ref}", str(clause_ref)).replace("{location}", location), "owner": "Legal / DPO" if template["priority"] == "P0" else "Privacy Counsel / Compliance"})

            # Patch finding
            patched = dict(fdict)
            patched["recommendation"] = sg_text[:300]
            patched["suggested_text"] = sg_text[:300]
            patched["action_priority"] = template["priority"]
            patched_findings.append(patched)

        # ── LLM enhancement for P0 items ──
        p0_findings = [pf for pf in patched_findings if pf.get("action_priority") == "P0"]
        if p0_findings and self.enabled:
            llm_result = self._try_llm_remediation([pf for pf in p0_findings[:3]])
            if llm_result:
                for item in llm_result.get("enhanced", []):
                    for pf in patched_findings:
                        if pf.get("finding_id") == item.get("finding_id"):
                            pf["suggested_text"] = item.get("suggested_text", pf["suggested_text"])

        return {"patched_findings": patched_findings, "action_plan": action_plan, "p0_count": len([a for a in action_plan if a["priority"] == "P0"])}

    def _try_llm_remediation(self, findings: list) -> dict | None:
        import json
        summary = "\n".join(f"- [{f.get('issue_type', 'unknown')}] {f.get('location', '?')}: {f.get('risk_analysis', '')[:100]}" for f in findings)
        return self._call_llm(f"Generate specific, actionable remediation text for these SCC findings:\n{summary}\n\nReturn JSON: {{ \"enhanced\": [ {{\"finding_id\": \"...\", \"suggested_text\": \"...\"}} ] }}")
