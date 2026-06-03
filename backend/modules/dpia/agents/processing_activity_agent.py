"""Agent 2: ProcessingActivityAgent — extract structured processing activity description from raw inputs.

Solves: DPIA's "describe processing" (GDPR Art 35(7)(a)) cannot be just a summary.
Must systematically describe data flows, sources, recipients, retention, and cross-border transfers.
Field concatenation alone misses data sources, system flows, third parties, model training locations,
retention periods, cross-border nodes, and data subject categories.

Reference: doc/tmp/dpia Section 3
"""

from __future__ import annotations

from backend.modules.dpia.agents import DPIAAgentBase


class ProcessingActivityAgent(DPIAAgentBase):
    agent_name = "dpia_processing_activity"
    max_tokens = 1000

    def run(
        self,
        raw_inputs: dict | None = None,
        attachments: list[dict] | None = None,
    ) -> dict:
        """Parse raw user inputs + attachment summaries into structured processing activity pack.

        Steps:
        A: read form fields + attachment summaries / data flow diagram summaries
        B: extract data flow nodes
        C: distinguish data sources, processing steps, recipients, storage locations
        D: flag ambiguities
        E: output processing_activity_pack
        """
        raw_inputs = raw_inputs or {}
        attachments = attachments or []

        if not self.enabled:
            return _rule_based_processing_activity(raw_inputs, attachments)

        raw_text = _format_raw_inputs(raw_inputs)
        att_text = _format_attachments(attachments)

        prompt = f"""Extract structured processing activities from raw DPIA inputs.

RAW INPUTS:
{raw_text}

ATTACHMENTS:
{att_text}

TASK: Parse these inputs into a structured processing activity description.

1. Identify each processing step: data collection → processing → storage → sharing → deletion
2. For each step, identify: actor, data sources, data categories, processing action, risk notes
3. Identify data subjects, recipients, retention periods
4. Detect cross-border transfers and their destinations
5. Flag any ambiguities or missing information

Output JSON:
{{
  "processing_steps": [
    {{
      "step": "<step name in Chinese>",
      "actor": "<who performs this step>",
      "data_sources": ["source1", "source2"],
      "data_categories": ["category1", "category2"],
      "processing": "<what happens in this step>",
      "risk_notes": ["<any risk observation>"]
    }}
  ],
  "data_sources": ["<all data sources>"],
  "data_categories": ["<all data categories>"],
  "data_subjects": ["<types of data subjects>"],
  "recipients": ["<all recipients>"],
  "retention_periods": ["<retention rules>"],
  "cross_border_transfer": {{
    "exists": true | false,
    "destination": "<country/region>",
    "description": "<what is transferred where>"
  }},
  "ambiguities": ["<unclear items that need clarification>"],
  "draft_text": "<2-3 sentence summary>"
}}

IMPORTANT: Distinguish between what IS stated and what IS NOT stated. Flag the latter as ambiguities."""

        result = self._call_llm(prompt)
        if result is None:
            return _rule_based_processing_activity(raw_inputs, attachments)

        result.setdefault("processing_steps", [])
        result.setdefault("data_sources", [])
        result.setdefault("data_categories", [])
        result.setdefault("data_subjects", [])
        result.setdefault("recipients", [])
        result.setdefault("retention_periods", [])
        result.setdefault("cross_border_transfer", {"exists": False, "destination": "", "description": ""})
        result.setdefault("ambiguities", [])
        result.setdefault("draft_text", "")
        return result


def _rule_based_processing_activity(
    raw_inputs: dict,
    attachments: list[dict],
) -> dict:
    """Fallback rule-based processing activity extraction."""
    data_flow = raw_inputs.get("data_flow", raw_inputs.get("processing_flow_description", ""))
    data_types = raw_inputs.get("data_types", raw_inputs.get("data_categories", []))
    retention = raw_inputs.get("retention", raw_inputs.get("retention_period", ""))
    cross_border = raw_inputs.get("cross_border", raw_inputs.get("transfer_destination", ""))

    processing_steps: list[dict] = []
    ambiguities: list[str] = []

    # Parse data flow into steps
    if data_flow and "→" in str(data_flow):
        nodes = [n.strip() for n in str(data_flow).split("→")]
        for i, node in enumerate(nodes):
            steps_map = {
                0: "数据收集",
                len(nodes) - 2: "数据处理与分析",
                len(nodes) - 1: "数据使用/决策",
            }
            step_name = steps_map.get(i, f"处理环节{i+1}")
            processing_steps.append({
                "step": step_name,
                "actor": node if node else "未指明",
                "data_sources": [nodes[0]] if i > 0 else ["数据主体"],
                "data_categories": list(data_types) if isinstance(data_types, list) else [str(data_types)],
                "processing": f"数据从{nodes[i-1] if i > 0 else '数据主体'}流转至{node}",
                "risk_notes": [],
            })
    else:
        processing_steps = [{
            "step": "数据处理",
            "actor": "未指明",
            "data_sources": ["数据主体"],
            "data_categories": list(data_types) if isinstance(data_types, list) else [],
            "processing": str(data_flow or raw_inputs.get("project_goal", "")),
            "risk_notes": [],
        }]

    if not data_flow or "→" not in str(data_flow):
        ambiguities.append("数据流转路径不够清晰，缺少系统级数据流描述")

    cross_border_info = {"exists": False, "destination": "", "description": ""}
    if cross_border:
        cross_border_info = {
            "exists": True,
            "destination": str(cross_border),
            "description": str(cross_border),
        }

    if not retention:
        ambiguities.append("数据保留期限未明确")

    return {
        "processing_steps": processing_steps,
        "data_sources": ["数据主体"] + (["第三方平台"] if len(processing_steps) > 2 else []),
        "data_categories": list(data_types) if isinstance(data_types, list) else [],
        "data_subjects": raw_inputs.get("data_subject_categories", []),
        "recipients": [s.get("actor", "") for s in processing_steps[1:]] if len(processing_steps) > 1 else [],
        "retention_periods": [retention] if retention else [],
        "cross_border_transfer": cross_border_info,
        "ambiguities": ambiguities,
        "draft_text": f"共识别{len(processing_steps)}个处理环节。{'存在跨境传输。' if cross_border_info['exists'] else ''}{'发现' + str(len(ambiguities)) + '项模糊信息需补充。' if ambiguities else ''}",
    }


def _format_raw_inputs(raw: dict) -> str:
    lines = []
    for k, v in raw.items():
        if isinstance(v, list):
            lines.append(f"- {k}: {', '.join(str(x) for x in v[:5])}")
        else:
            lines.append(f"- {k}: {str(v)[:200]}")
    return "\n".join(lines) or "未提供"

def _format_attachments(attachments: list[dict]) -> str:
    if not attachments:
        return "未提供附件"
    lines = []
    for a in attachments[:5]:
        att_type = a.get("type", "other")
        summary = a.get("summary", str(a))
        lines.append(f"- [{att_type}] {summary[:200]}")
    return "\n".join(lines)
