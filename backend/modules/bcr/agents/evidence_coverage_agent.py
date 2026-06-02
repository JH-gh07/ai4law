"""Agent 6: BCREvidenceCoverageAgent — distinguish body text vs annex support."""

from __future__ import annotations

from backend.modules.bcr.agents import BCRAgentBase


class BCREvidenceCoverageAgent(BCRAgentBase):
    agent_name = "bcr_evidence_coverage"
    max_tokens = 500

    def run(self, requirements: list[dict], file_roles: list[dict],
            body_text_len: int, annex_text_len: int) -> dict:
        req_list = "\n".join(
            f"- {r.get('requirement_id','?')}: {r.get('title','?')} (status={r.get('coverage_status','?')})"
            for r in requirements[:15]
        )
        files = "\n".join(f"- {f.get('filename','?')}: {f.get('role','?')}" for f in file_roles)

        prompt = f"""For each BCR requirement, determine whether coverage comes from body text or annexes.
Requirements that MUST be in body text (GDPR Art 47 mandatory elements) cannot rely solely on annexes.

Requirements:
{req_list}

Files:
{files}
Body text length: {body_text_len} chars, Annex text length: {annex_text_len} chars

Return JSON:
{{
  "coverage_map": [
    {{
      "requirement_id": "BCR-C-1.2",
      "coverage_source": "body" | "annex_only" | "both" | "missing",
      "assessment": "<one sentence>",
      "risk_if_annex_only": "HIGH" | "MEDIUM" | "LOW"
    }}
  ],
  "overall_risk": "LOW" | "MEDIUM" | "HIGH"
}}"""
        result = self._call_llm(prompt) or {
            "coverage_map": requirements, "overall_risk": "MEDIUM",
        }
        result.setdefault("coverage_map", [])
        return result
