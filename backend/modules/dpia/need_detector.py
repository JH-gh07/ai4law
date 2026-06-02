"""DPIA need detector — determines whether a DPIA is required under GDPR Art 35.

Based on WP248 high-risk criteria and EDPB guidelines.
"""

from __future__ import annotations

from backend.modules.dpia.schema import DPIANeedAssessment, DPIARequest


# WP248 high-risk criteria mapping
_HIGH_RISK_TRIGGERS = {
    "automated_decision_making": {
        "reason": "自动化决策或画像可能对个人产生法律效力或类似重大影响 (GDPR Art 22)",
        "legal_basis": ["GDPR Article 35", "GDPR Article 22", "WP251"],
    },
    "systematic_monitoring": {
        "reason": "对公共区域的大规模系统性监控 (WP248 criterion)",
        "legal_basis": ["GDPR Article 35", "WP248"],
    },
    "special_category_data": {
        "reason": "处理特殊类别个人数据 (GDPR Art 9)",
        "legal_basis": ["GDPR Article 35", "GDPR Article 9"],
    },
    "large_scale_processing": {
        "reason": "大规模处理个人数据 (WP248 criterion)",
        "legal_basis": ["GDPR Article 35", "WP248"],
    },
    "data_matching": {
        "reason": "数据匹配或重识别组合 (WP248 criterion)",
        "legal_basis": ["GDPR Article 35", "WP248"],
    },
    "new_technology": {
        "reason": "使用新技术处理方式 (GDPR Art 35(1))",
        "legal_basis": ["GDPR Article 35"],
    },
    "vulnerable_data_subjects": {
        "reason": "处理弱势数据主体的个人数据 (WP248 criterion)",
        "legal_basis": ["GDPR Article 35", "WP248"],
    },
    "cross_border_transfer": {
        "reason": "跨境数据传输需额外保障评估 (GDPR Art 44-49)",
        "legal_basis": ["GDPR Article 44", "GDPR Article 46"],
    },
}

# Risk descriptions for profiling / automated decision keywords in project goal
_PROFILING_KEYWORDS = ["评估", "评分", "排名", "预测", "分类", "画像", "recommendation", "scoring", "ranking", "profiling", "evaluation", "predict"]


class DPIANeedDetector:
    """Determine DPIA necessity based on WP248 high-risk criteria."""

    @staticmethod
    def evaluate(payload: DPIARequest) -> DPIANeedAssessment:
        triggers: dict[str, str] = {}
        all_legal_basis: list[str] = []
        prior_consultation_possible = False

        # Check each field from the request
        if payload.automated_decision_making:
            triggers["automated_decision_making"] = _HIGH_RISK_TRIGGERS["automated_decision_making"]["reason"]
        if payload.systematic_monitoring:
            triggers["systematic_monitoring"] = _HIGH_RISK_TRIGGERS["systematic_monitoring"]["reason"]
        if payload.special_category_data:
            triggers["special_category_data"] = _HIGH_RISK_TRIGGERS["special_category_data"]["reason"]
        if payload.large_scale_processing:
            triggers["large_scale_processing"] = _HIGH_RISK_TRIGGERS["large_scale_processing"]["reason"]
        if payload.data_matching:
            triggers["data_matching"] = _HIGH_RISK_TRIGGERS["data_matching"]["reason"]
        if payload.new_technology:
            triggers["new_technology"] = _HIGH_RISK_TRIGGERS["new_technology"]["reason"]
        if payload.vulnerable_data_subjects:
            triggers["vulnerable_data_subjects"] = _HIGH_RISK_TRIGGERS["vulnerable_data_subjects"]["reason"]
        if payload.cross_border_transfer:
            triggers["cross_border_transfer"] = _HIGH_RISK_TRIGGERS["cross_border_transfer"]["reason"]

        # Check project goal for profiling/automated decision keywords
        goal_lower = payload.project_goal.lower()
        if any(kw.lower() in goal_lower for kw in _PROFILING_KEYWORDS):
            if "automated_decision_making" not in triggers:
                triggers["profiling"] = "项目目标涉及评估、评分或画像处理 (WP248 criterion)"

        # Collect legal basis from matched triggers
        for trigger_key in triggers:
            if trigger_key in _HIGH_RISK_TRIGGERS:
                for base in _HIGH_RISK_TRIGGERS[trigger_key]["legal_basis"]:
                    if base not in all_legal_basis:
                        all_legal_basis.append(base)

        dpia_required = len(triggers) > 0
        trigger_reasons = list(triggers.values())

        # Prior consultation is possible when:
        # - DPIA is required AND
        # - high-risk triggers are present AND
        # - mitigation may not fully eliminate residual risk
        if dpia_required and len(triggers) >= 2:
            prior_consultation_possible = True

        # Build reasoning
        if dpia_required:
            reasoning_parts = [f"触发 {len(triggers)} 项高风险标准："]
            for reason in trigger_reasons:
                reasoning_parts.append(f"  - {reason}")
            if prior_consultation_possible:
                reasoning_parts.append(
                    "多项高风险标准同时满足，若剩余风险无法充分降低，"
                    "建议依据 GDPR Art 36 进行监管机构事先咨询。"
                )
            reasoning = "\n".join(reasoning_parts)
        else:
            reasoning = "未触发 WP248 高风险标准。如处理活动不含特殊类别数据、系统性监控、自动化决策等，可能无需正式 DPIA，但建议记录评估过程。"

        return DPIANeedAssessment(
            dpia_required=dpia_required,
            trigger_reasons=trigger_reasons,
            legal_basis=all_legal_basis or ["GDPR Article 35"],
            prior_consultation_possible=prior_consultation_possible,
            reasoning=reasoning,
        )
