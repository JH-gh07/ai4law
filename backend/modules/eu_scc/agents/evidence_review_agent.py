"""Agent 5: EvidenceReviewAgent — review evidence precision per issue.

Checks whether fact_refs and rule_refs in evidence items actually support
the issue claim. Detects: missing key citations, irrelevant citations,
low-confidence evidence, and citation-to-issue mismatches.
"""

from __future__ import annotations

from backend.modules.eu_scc.agents import SCCAgentBase


class EvidenceReviewAgent(SCCAgentBase):
    agent_name = "eu_scc_evidence_review"
    max_tokens = 500

    # Standard citation templates per issue type
    _ISSUE_CITATION_TEMPLATES: dict[str, list[str]] = {
        "module_mismatch": ["EU 2021/914 Annex (Module scope)", "GDPR Article 28(4)"],
        "clause_weakened": ["EU 2021/914 Recital 3", "SCC Clause [N] standard text", "GDPR Article 46"],
        "clause_deleted": ["EU 2021/914 Recital 3", "SCC Clause [N] standard text"],
        "annex_incomplete": ["EU 2021/914 Annex requirements", "Clause 3 / Clause 13"],
        "annex_vague": ["EU 2021/914 Annex I data specificity requirement", "GDPR Article 5(1)(c)"],
        "special_category_misclassified": ["GDPR Article 9", "GDPR Recital 159"],
        "tia_missing": ["Schrems II C-311/18", "EDPB Recommendations 01/2020", "GDPR Article 46"],
        "supplementary_measures_insufficient": ["Schrems II C-311/18", "EDPB Recommendations 01/2020 §4", "GDPR Article 46"],
        "sub_processor_chain_incomplete": ["EU 2021/914 Clause 9", "GDPR Article 28"],
        "party_info_incomplete": ["EU 2021/914 Annex I.A", "GDPR Article 46(2)(c)"],
        "other": ["GDPR Article 46", "EU 2021/914"],
    }

    def run(self, facts: list, issues: list, evidence_chain: list,
            regulations: list, findings: list) -> dict:
        """Review evidence precision for each issue."""
        evidence_patches: list[dict] = []
        low_confidence_evidence: list[dict] = []
        issue_dict = self._index_issues(issues)
        evidence_dict = self._index_evidence(evidence_chain)
        finding_dict = self._index_findings(findings)

        for ev_id, ev in evidence_dict.items():
            rule_refs = ev.get("rule_refs", []) if isinstance(ev, dict) else getattr(ev, "rule_refs", [])
            fact_refs = ev.get("fact_refs", []) if isinstance(ev, dict) else getattr(ev, "fact_refs", [])
            used_by = ev.get("used_by", []) if isinstance(ev, dict) else getattr(ev, "used_by", [])

            # Find which issue this evidence serves
            issue_id = None
            for target in used_by:
                if target.startswith("EU-SCC-ISSUE-") or target.startswith("EU-SCC-FINDING-"):
                    issue_id = target
                    break

            if not issue_id:
                continue

            issue = issue_dict.get(issue_id) or finding_dict.get(issue_id)
            issue_type = "other"
            if issue:
                issue_type = issue.get("category", "other") if isinstance(issue, dict) else getattr(issue, "category", "other")

            # Get expected citations
            expected = self._ISSUE_CITATION_TEMPLATES.get(issue_type, self._ISSUE_CITATION_TEMPLATES["other"])

            # Check rule_refs
            missing_refs: list[str] = []
            irrelevant_refs: list[str] = []

            has_any_expected = any(any(exp_ref.lower() in rule_ref.lower() for rule_ref in rule_refs) for exp_ref in expected[:2])
            if not has_any_expected and rule_refs:
                missing_refs = expected[:2]
                irrelevant_ids = [r for r in rule_refs if not any(e.lower() in r.lower() for e in expected[:3])]
                if irrelevant_ids:
                    irrelevant_refs = irrelevant_ids

            # Check fact_refs
            fact_ids_set = {f.get("fact_id", getattr(f, "fact_id", "")) if isinstance(f, dict) else getattr(f, "fact_id", "") for f in facts}
            missing_fact_refs = [fr for fr in fact_refs if fr not in fact_ids_set]

            confidence = 0.60 if missing_refs or missing_fact_refs else 0.90

            if missing_refs or irrelevant_refs:
                evidence_patches.append({"evidence_id": ev_id, "missing_rule_refs": missing_refs, "irrelevant_rule_refs": irrelevant_refs, "reason": f"Expected citations: {expected[:2]}"})

            if confidence < 0.75:
                low_confidence_evidence.append({"evidence_id": ev_id, "problem": f"Confidence {confidence:.0%} — {'missing key citations' if missing_refs else 'missing fact references'}", "needs_human_review": True})

        revised_evidence = list(evidence_chain)  # Keep original evidence, patches are advisory
        return {"revised_evidence": revised_evidence, "evidence_patches": evidence_patches, "low_confidence_evidence": low_confidence_evidence, "patch_count": len(evidence_patches)}

    @staticmethod
    def _index_issues(issues: list) -> dict:
        result = {}
        for i in issues:
            iid = i.get("issue_id", getattr(i, "issue_id", "")) if isinstance(i, dict) else getattr(i, "issue_id", "")
            if iid:
                result[iid] = i if isinstance(i, dict) else {"category": getattr(i, "category", "other")}
        return result

    @staticmethod
    def _index_evidence(evidence: list) -> dict:
        result = {}
        for e in evidence:
            eid = e.get("evidence_id", getattr(e, "evidence_id", "")) if isinstance(e, dict) else getattr(e, "evidence_id", "")
            if eid:
                result[eid] = e if isinstance(e, dict) else {"rule_refs": getattr(e, "rule_refs", []), "fact_refs": getattr(e, "fact_refs", []), "used_by": getattr(e, "used_by", [])}
        return result

    @staticmethod
    def _index_findings(findings: list) -> dict:
        result = {}
        for f in findings:
            fid = f.get("finding_id", getattr(f, "finding_id", "")) if isinstance(f, dict) else getattr(f, "finding_id", "")
            if fid:
                result[fid] = f
        return result
