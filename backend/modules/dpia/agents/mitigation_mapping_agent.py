"""Agent 5: MitigationMappingAgent — map each HIGH/MEDIUM risk to concrete, verifiable measures.

Solves: DPIA cannot just list measures. Must prove each high risk has a corresponding measure,
the measure is specific, verifiable, can reduce risk, and what residual risk remains.

Reference: doc/tmp/dpia Section 6
"""

from __future__ import annotations

from backend.modules.dpia.agents import DPIAAgentBase


class MitigationMappingAgent(DPIAAgentBase):
    agent_name = "dpia_mitigation_mapping"
    max_tokens = 1200

    def run(
        self,
        risk_matrix: list[dict] | None = None,
        user_measures: list[str] | None = None,
        reference_measures: list[str] | None = None,
    ) -> dict:
        """Map risks to mitigation measures and assess residual risk."""
        risk_matrix = risk_matrix or []
        user_measures = user_measures or []
        reference_measures = reference_measures or []

        if not self.enabled:
            return _rule_based_mitigation(risk_matrix, user_measures)

        risks_text = _format_risks(risk_matrix)
        measures_text = "\n".join(f"- {m}" for m in user_measures) if user_measures else "未提供"
        ref_text = ", ".join(reference_measures) if reference_measures else "data minimisation, human review, transparency notice, bias audit"

        prompt = f"""Map risks to mitigation measures for a GDPR DPIA.

RISK MATRIX:
{risks_text}

USER-PROVIDED MEASURES:
{measures_text}

REFERENCE MEASURE TYPES: {ref_text}

TASK: For each HIGH and MEDIUM risk, provide:
1. Concrete measures that address that specific risk
2. Status: "planned" | "implemented" | "missing" (conservative: prefer "planned" unless evidence confirms "implemented")
3. Effect: how this measure reduces the risk
4. Verification: how to verify this measure is effective
5. Residual risk after measures: LOW | MEDIUM | HIGH
6. Additional actions still needed

For risks with no matching user measures, mark as "missing" and propose measures.

CRITICAL RULES:
- Never write "风险已完全消除" (risk fully eliminated)
- Never mark a measure as "implemented" without clear evidence
- Each HIGH risk must have at least 1 measure
- Distinguish between measures the user ALREADY has vs measures they SHOULD implement

Return JSON:
{{
  "agent_name": "MitigationMappingAgent",
  "mitigation_plan": [
    {{
      "risk_id": "RISK-xxx",
      "measures": [
        {{
          "measure": "<specific measure in Chinese>",
          "status": "planned" | "implemented" | "missing",
          "effect": "<how it reduces risk>",
          "verification": "<how to verify>"
        }}
      ],
      "residual_risk": "LOW" | "MEDIUM" | "HIGH",
      "additional_actions_required": ["action1", "action2"]
    }}
  ],
  "draft_text": "<overall mitigation summary>"
}}"""

        result = self._call_llm(prompt)
        if result is None:
            return _rule_based_mitigation(risk_matrix, user_measures)

        result.setdefault("agent_name", "MitigationMappingAgent")
        result.setdefault("mitigation_plan", [])
        result.setdefault("draft_text", "")
        return result


def _rule_based_mitigation(risk_matrix: list[dict], user_measures: list[str]) -> dict:
    """Fallback rule-based mitigation mapping."""
    mitigation_plan: list[dict] = []
    measures_text = " ".join(user_measures).lower()

    for risk in risk_matrix:
        risk_id = risk.get("risk_id", "")
        risk_name = risk.get("risk_name", "")
        overall = risk.get("overall_level", "MEDIUM")

        measures: list[dict] = []
        residual = overall

        # Generic mitigation by risk type
        if "discrimination" in risk_id or "歧视" in risk_name:
            has_audit = any(kw in measures_text for kw in ["审计", "audit", "公平", "fairness"])
            measures.append({
                "measure": "每季度开展公平性审计，按性别、年龄等维度检查模型输出差异",
                "status": "planned" if not has_audit else "implemented",
                "effect": "降低训练数据偏差导致的系统性歧视风险",
                "verification": "审计报告和模型版本记录",
            })
            measures.append({
                "measure": "提供人工复核渠道，确保自动化决策可被人类干预和推翻",
                "status": "planned",
                "effect": "降低自动化评分不可纠正影响的风险",
                "verification": "人工复核操作日志",
            })
            residual = "MEDIUM"

        elif "special" in risk_id or "特殊" in risk_name:
            measures.append({
                "measure": "取消或严格限制可能推断特殊类别数据的处理环节",
                "status": "planned",
                "effect": "直接消除特殊类别数据推断的根本原因",
                "verification": "数据处理活动清单和数据流图更新",
            })

        elif "transparency" in risk_id or "透明" in risk_name:
            measures.append({
                "measure": "提供清晰、可理解的处理逻辑说明，上线'解释功能'",
                "status": "planned",
                "effect": "增强数据主体对自动化决策的理解和信任",
                "verification": "解释功能上线记录及用户反馈",
            })

        elif "cross-border" in risk_id or "跨境" in risk_name:
            measures.append({
                "measure": "签署欧盟标准合同条款(SCC)或实施约束性公司规则(BCR)",
                "status": "planned",
                "effect": "为跨境传输提供GDPR第46条要求的适当保障",
                "verification": "已签署的SCC/BCR文件",
            })

        else:
            measures.append({
                "measure": "建立定期数据保护影响评估复评机制",
                "status": "planned",
                "effect": "及时识别和处理新出现的风险",
                "verification": "DPIA复评记录",
            })

        additional = []
        if overall == "HIGH":
            additional.append("上线前完成所有计划措施的落实和验证")

        mitigation_plan.append({
            "risk_id": risk_id,
            "measures": measures,
            "residual_risk": residual,
            "additional_actions_required": additional,
        })

    return {
        "agent_name": "MitigationMappingAgent",
        "mitigation_plan": mitigation_plan,
        "draft_text": f"已为{len(mitigation_plan)}项风险匹配缓解措施，建议上线前落实全部planned状态措施",
    }


def _format_risks(risk_matrix: list[dict]) -> str:
    lines = []
    for r in risk_matrix:
        lines.append(
            f"- [{r.get('overall_level', '?')}] {r.get('risk_id')}: {r.get('risk_name', '')}. "
            f"Likelihood={r.get('likelihood')}, Impact={r.get('impact')}. "
            f"Rights affected: {r.get('affected_rights', [])}"
        )
    return "\n".join(lines) if lines else "（无风险矩阵）"
