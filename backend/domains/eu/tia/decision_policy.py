"""Deterministic TIA transfer decision policy.

This module owns the legal-operational decision only.  It does not call an LLM,
render documents, or parse files.  Parsed evidence and rule-engine results enter
through a stable interface so report wording cannot upgrade the decision.
"""

from __future__ import annotations

from backend.domains.eu.tia.schema import TIADecision, TIAStructuredInput


def _evidence_for_role(items: list[dict], role: str) -> list[dict]:
    return [
        item
        for item in items
        if item.get("role") == role and not item.get("parse_error")
    ]


def _transfer_tool_verified(transfer_tool: str, evidence: dict | None) -> bool:
    if evidence is None:
        return False
    if transfer_tool == "scc":
        return all(
            bool(evidence.get(field))
            for field in ("has_scc_mention", "is_2021_914_scc", "has_module_selection")
        )
    if transfer_tool == "bcr":
        return bool(evidence.get("has_bcr_mention"))
    if transfer_tool == "derogation":
        return bool(evidence.get("has_article_49_derogation"))
    return False


def _country_law_verified(items: list[dict]) -> bool:
    country_items = [
        item
        for item in items
        if item.get("role") == "country_law_analysis" and not item.get("parse_error")
    ]
    return bool(country_items) and all(
        any(bool(item.get(field)) for item in country_items)
        for field in (
            "has_gov_access_analysis",
            "has_remedy_assessment",
            "has_oversight_assessment",
        )
    )


def _technical_controls_verified(
    structured_input: TIAStructuredInput | None,
    evidence: dict | None,
) -> bool:
    if structured_input is None or evidence is None:
        return False
    if structured_input.has_secure_enclave and structured_input.has_key_separation:
        return bool(evidence.get("has_secure_enclave") and evidence.get("has_key_separation"))
    if structured_input.has_end_to_end_encryption and structured_input.key_managed_in_eu:
        return all(
            bool(evidence.get(field))
            for field in ("has_end_to_end_encryption", "has_key_management", "key_location_eu")
        )
    if structured_input.encryption_before_transfer and structured_input.key_managed_in_eu:
        return all(
            bool(evidence.get(field))
            for field in ("has_encryption_in_transit", "has_key_management", "key_location_eu")
        )
    return False


def evaluate_tia_decision(
    *,
    transfer_tool: str,
    structured_input: TIAStructuredInput | None,
    inherent_risk: str,
    residual_risk: str,
    measure_sufficiency: str,
    attachment_evidences: list[dict],
    consistency_issues: list[str],
) -> TIADecision:
    """Return a fail-closed transfer decision from structured facts and evidence."""
    missing_evidence: list[str] = []
    transfer_evidences = _evidence_for_role(attachment_evidences, "transfer_agreement")
    technical_evidences = _evidence_for_role(attachment_evidences, "technical_control_doc")

    if not any(
        _transfer_tool_verified(transfer_tool, evidence)
        for evidence in transfer_evidences
    ):
        missing_evidence.append("签署或适用的传输工具文件")
    if not _country_law_verified(attachment_evidences):
        missing_evidence.append("覆盖政府访问、救济和独立监督的第三国法律分析")
    if inherent_risk in ("HIGH", "VERY_HIGH") and not any(
        _technical_controls_verified(structured_input, evidence)
        for evidence in technical_evidences
    ):
        missing_evidence.append("技术控制实施证据")

    reasons: list[str] = []
    must_suspend = False
    if residual_risk in ("HIGH", "VERY_HIGH"):
        must_suspend = True
        reasons.append(f"剩余风险仍为 {residual_risk}，不得以附条件方式继续传输")
    if measure_sufficiency in ("insufficient", "unknown"):
        must_suspend = True
        reasons.append("补充措施尚未证明足以达到实质等同保护水平")
    if missing_evidence:
        must_suspend = True
        reasons.append("关键结论仅有结构化声明，缺少附件证据佐证")
    if consistency_issues:
        must_suspend = True
        reasons.append("确定性一致性检查仍有未解决问题")

    if must_suspend:
        status = "suspend"
    elif inherent_risk in ("HIGH", "VERY_HIGH") or residual_risk == "MEDIUM":
        status = "proceed_with_conditions"
        reasons.append("关键证据已核验，但高风险目的地仍需持续复审和停传触发机制")
    else:
        status = "proceed"
        reasons.append("风险、补充措施和关键证据满足当前规则门槛")

    if missing_evidence:
        evidence_status = "missing"
    elif consistency_issues:
        evidence_status = "partial"
    else:
        evidence_status = "verified"

    mandatory_conditions = [f"补齐并核验：{item}" for item in missing_evidence]
    if status == "suspend":
        mandatory_conditions.append("问题修复并经 DPO 重新审阅前不得开始或继续传输")
    elif status == "proceed_with_conditions":
        mandatory_conditions.extend([
            "持续维持已核验的补充措施",
            "第三国法律、处理范围或技术控制发生重大变化时立即复审并按需暂停传输",
        ])

    return TIADecision(
        transfer_status=status,
        inherent_risk=inherent_risk,
        residual_risk=residual_risk,
        measure_sufficiency=measure_sufficiency,
        evidence_status=evidence_status,
        reasons=reasons,
        missing_evidence=missing_evidence,
        mandatory_conditions=mandatory_conditions,
    )


def build_decision_chapter_text(
    decision: TIADecision,
    *,
    proposed_conclusion: str,
    citation_markers: list[str] | None = None,
) -> tuple[str, str]:
    """Compile the two decision-bearing chapters from the rule result."""
    status_label = {
        "proceed": "可以推进传输",
        "proceed_with_conditions": "满足前置条件后方可推进传输",
        "suspend": "暂停传输",
    }[decision.transfer_status]
    citations = " ".join(citation_markers or [])
    legal_basis = f"\n\n法律依据：{citations}" if citations else ""
    reasons = "\n".join(f"- {reason}" for reason in decision.reasons) or "- 无"
    missing = "\n".join(f"- {item}" for item in decision.missing_evidence) or "- 无"
    conditions = "\n".join(f"- {item}" for item in decision.mandatory_conditions) or "- 无"

    conclusion = (
        "## 系统规则结论\n\n"
        f"**系统规则结论：{status_label}**\n\n"
        "该结论由结构化风险、补充措施充分性和附件证据共同计算，"
        "模型生成内容和用户拟定结论均不得覆盖。\n\n"
        f"- 固有风险：{decision.inherent_risk}\n"
        f"- 剩余风险：{decision.residual_risk}\n"
        f"- 补充措施充分性：{decision.measure_sufficiency}\n"
        f"- 证据状态：{decision.evidence_status}\n\n"
        f"### 判定理由\n\n{reasons}\n\n"
        f"### 尚缺证据\n\n{missing}\n\n"
        "### 用户提交的拟定结论（不构成系统批准）\n\n"
        f"{proposed_conclusion}\n\n"
        "上述拟定结论仅作为输入记录，不构成系统批准或 DPO 正式签署。"
        f"{legal_basis}"
    )
    action_plan = (
        "## 强制行动与复审计划\n\n"
        f"{conditions}\n\n"
        "完成条件后应重新运行 TIA，并由具备授权的 DPO 或法律负责人正式复核。"
        "法规依据沿用上一章的系统规则结论，不在本章重复列示。"
    )
    return conclusion, action_plan
