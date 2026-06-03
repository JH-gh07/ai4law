"""Agent 5: RepairCheckAgent — identifies missing citations, logic gaps in context pack."""

from __future__ import annotations

from backend.modules.us_14117.agents import US14117AgentBase


class RepairCheckAgent(US14117AgentBase):
    """Triggered after context pack build. Checks:
    - Issues with missing fact_refs or rule_refs
    - Evidence chain gaps
    - HIGH/BLOCKER issues not reflected in risk summary
    - Missing attachment references
    """
    agent_name = "us14117_repair_check"
    max_tokens = 500

    def run(self, issue_summaries: list[dict], evidence_count: int,
            has_attachments: bool, traffic_light: str, missing_measures: list[str]) -> dict:
        issue_block = "\n".join(
            f"- {i.get('issue_id','?')} [{i.get('severity','?')}]: {i.get('title','?')} "
            f"(facts={len(i.get('fact_refs',[]))}, rules={len(i.get('rule_refs',[]))})"
            for i in issue_summaries[:10]
        )

        prompt = f"""Check an EO 14117 context pack for completeness gaps.

Traffic light: {traffic_light}
Evidence items: {evidence_count}
Has attachments: {has_attachments}
Missing security measures: {missing_measures[:6]}

Issues:
{issue_block}

Return JSON:
{{
  "missing_citations": ["<issue_id that needs rule_refs>"],
  "evidence_gaps": ["<description of missing evidence link>"],
  "attachment_gaps": ["<missing attachment reference>"],
  "severity_mismatches": ["<issue severity vs traffic light inconsistency>"],
  "recommended_repairs": ["<concrete fix action>"]
}}"""
        return self._call_llm(prompt) or {
            "missing_citations": [], "evidence_gaps": [], "attachment_gaps": [],
            "severity_mismatches": [], "recommended_repairs": [],
        }
