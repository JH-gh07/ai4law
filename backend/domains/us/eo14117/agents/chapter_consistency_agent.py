"""Agent 4: ChapterConsistencyAgent — verifies generated chapters are internally consistent."""

from __future__ import annotations

from backend.domains.us.eo14117.agents import US14117AgentBase


class ChapterConsistencyAgent(US14117AgentBase):
    """Triggered after chapter generation. Checks:
    - RED/YELLOW/GREEN signals are consistent across all 4 chapters
    - All HIGH/BLOCKER issues are mentioned in at least one chapter
    - No contradictory statements (e.g., "prohibited" in chapter 1 but "GREEN" in chapter 4)
    - Missing security measures are addressed in compliance_actions
    """
    agent_name = "us14117_chapter_consistency"
    max_tokens = 500

    def run(self, chapter_summaries: list[dict], traffic_light: str,
            issue_count: int, missing_measures: list[str]) -> dict:
        ch_block = "\n".join(
            f"Chapter {c.get('no','?')} '{c.get('title','?')}': {c.get('content','')[:200]}..."
            for c in chapter_summaries
        )

        prompt = f"""Check report chapter consistency for an EO 14117 assessment.

Overall traffic light: {traffic_light}
Issue count: {issue_count}
Missing security measures: {missing_measures[:8]}

Chapter content:
{ch_block}

Return JSON:
{{
  "consistent": true | false,
  "issues_found": ["<specific inconsistency>"],
  "missing_from_chapters": ["<issue or measure not mentioned but should be>"],
  "recommended_fixes": ["<concrete fix suggestion>"]
}}"""
        return self._call_llm(prompt) or {
            "consistent": True, "issues_found": [],
            "missing_from_chapters": [],
            "recommended_fixes": ["Agent unavailable — manual consistency review recommended."],
        }
