"""P2 Agent 8: ClarificationAgent — generate dynamic follow-up questions to fill critical gaps.

Solves: instead of generic "please supplement materials", the system should ask
minimum but high-impact questions that change path, risk, or report conclusions.

Reference: doc/tmp/认证标准合同路径 Section 8
"""

from __future__ import annotations

from backend.modules.scc.agents import SCCAgentBase
from backend.modules.scc.schema import ClarificationQuestion, ClarificationResult


class ClarificationAgent(SCCAgentBase):
    agent_name = "cn_scc_clarification"
    max_tokens = 600

    def run(
        self,
        current_facts: list[dict] | None = None,
        missing_materials: list[str] | None = None,
        blocking_issues: list[str] | None = None,
        path_confidence: float = 0.5,
        path_diagnosis: dict | None = None,
        uploaded_materials: list[str] | None = None,
    ) -> dict:
        """Generate 3-5 most impactful follow-up questions.

        Prioritization:
        1. Questions that could CHANGE the path (e.g., from SCC to exemption)
        2. Questions that could CHANGE the risk level
        3. Questions that affect whether the report can be filed

        Questions that only fill minor gaps are deprioritized.
        """
        current_facts = current_facts or []
        missing_materials = missing_materials or []
        blocking_issues = blocking_issues or []
        uploaded_materials = uploaded_materials or []

        if not self.enabled:
            return _rule_based_clarification(
                current_facts, missing_materials, blocking_issues, path_confidence, path_diagnosis
            )

        facts_str = "\n".join(
            f"- {f.get('value', str(f))}" for f in current_facts[:10]
        ) if current_facts else "（无当前事实）"

        missing_str = "\n".join(f"- {m}" for m in missing_materials[:10]) if missing_materials else "（无明确缺失材料）"

        blocking_str = "\n".join(f"- {b}" for b in blocking_issues[:10]) if blocking_issues else "（无阻断性问题）"

        materials_str = ", ".join(uploaded_materials) if uploaded_materials else "（未上传材料）"

        recommended_path = path_diagnosis.get("recommended_path", "未知") if path_diagnosis else "未知"

        prompt = f"""Generate the 3-5 most critical follow-up questions for a CN SCC compliance review.

CURRENT STATE:
- Recommended Path: {recommended_path}
- Path Confidence: {path_confidence}
- Known Facts: {facts_str}
- Missing Materials: {missing_str}
- Blocking Issues: {blocking_str}
- Uploaded Materials: {materials_str}

PRIORITY RULES (in order):
1. Questions that could CHANGE the recommended path (e.g., from SCC → exemption, or SCC → security assessment)
2. Questions that could CHANGE the risk level (HIGH → MEDIUM, MEDIUM → LOW)
3. Questions that affect whether the PIPIA report can be filed/registered
4. Questions about evidence adequacy, not general information gathering
5. Merge duplicate/similar questions — 3-5 questions maximum, not a questionnaire

Return JSON:
{{
  "questions": [
    {{
      "priority": "HIGH" | "MEDIUM" | "LOW",
      "question": "<concrete, answerable question in Chinese>",
      "why": "<why this matters for path/risk/conclusion>"
    }}
  ]
}}

IMPORTANT:
- Each question must be concrete and answerable (not "提供更多材料")
- Each "why" must link to path determination or risk assessment
- HIGH priority questions should affect path or risk level
- Never ask for evidence that the system should already have from uploaded files
- Merge similar questions to keep total at 3-5"""

        result = self._call_llm(prompt)
        if result is None:
            return _rule_based_clarification(
                current_facts, missing_materials, blocking_issues, path_confidence, path_diagnosis
            )

        result.setdefault("questions", [])
        return result


def _rule_based_clarification(
    current_facts: list[dict],
    missing_materials: list[str],
    blocking_issues: list[str],
    path_confidence: float,
    path_diagnosis: dict | None = None,
) -> dict:
    """Fallback rule-based clarification question generation."""
    questions: list[dict] = []

    recommended_path = path_diagnosis.get("recommended_path", "") if path_diagnosis else ""

    # Path-changing questions
    if path_confidence < 0.7:
        if "exemption" in recommended_path or "豁免" in str(path_diagnosis.get("exemption_assessment", "")):
            questions.append({
                "priority": "HIGH",
                "question": "是否能提供包含个人信息出境条款的员工手册或集体合同？",
                "why": "该问题直接影响是否可以主张人力资源管理豁免，可能改变推荐路径",
            })

        if "certification" in recommended_path:
            questions.append({
                "priority": "HIGH",
                "question": "认证机构是否在中国网信部门认可的专业认证机构名录内？请提供认证机构资质证明",
                "why": "该问题直接影响认证路径是否成立，可能改变推荐路径",
            })

        if path_confidence < 0.5:
            questions.append({
                "priority": "HIGH",
                "question": "请确认企业是否为关键信息基础设施运营者(CIIO)？",
                "why": "CIIO身份将直接触发安全评估路径",
            })

    # Risk-changing questions
    if any("spi" in str(f).lower() or "敏感" in str(f) for f in current_facts):
        questions.append({
            "priority": "MEDIUM",
            "question": "是否能提供敏感个人信息的字段清单及每类敏感信息的出境必要性说明？",
            "why": "敏感信息类型和必要性直接影响风险评估等级和合规论证强度",
        })

    # Evidence questions based on blocking issues
    for issue in blocking_issues[:3]:
        if "同意" in issue:
            questions.append({
                "priority": "HIGH",
                "question": "是否能提供覆盖全部目标用户的单独同意记录清单或统计报告？",
                "why": "单独同意的完整性直接影响告知同意义务是否成立",
            })
        if "合同" in issue or "条款" in issue:
            questions.append({
                "priority": "HIGH",
                "question": "是否能提供完整版标准合同文本（含全部附件）？",
                "why": "合同完整性直接影响条款级审查和备案可行性",
            })

    # Default questions if none generated
    if not questions:
        questions = [
            {
                "priority": "HIGH",
                "question": "是否能提供个人信息出境影响评估(PIPIA)所需的基本材料清单？",
                "why": "材料完整性直接影响报告质量和备案准备度",
            },
            {
                "priority": "MEDIUM",
                "question": "境外接收方是否能提供最新的安全审计报告或安全认证证明？",
                "why": "接收方安全能力评估是标准合同路径的必要组成部分",
            },
            {
                "priority": "MEDIUM",
                "question": "是否已有数据出境记录制度和个人信息主体权利响应机制？",
                "why": "制度完备性影响合规评级和持续合规能力评估",
            },
        ]

    return {"questions": questions[:5]}
