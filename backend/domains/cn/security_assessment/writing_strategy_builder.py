from __future__ import annotations

from typing import Any

from backend.common.workflow import IssueItem


_BASE_FORBIDDEN_EXPRESSIONS = [
    "完全合规",
    "材料齐备",
    "无风险",
    "已充分证明",
    "必然合法",
]

_ISSUE_FORBIDDEN: dict[str, list[str]] = {
    "ISSUE-recipient-security-evidence-missing": [
        "接收方具备充分安全保障能力",
        "接收方完全符合数据安全要求",
        "接收方安全能力已得到充分证明",
    ],
    "ISSUE-consent-evidence-missing": [
        "已取得全部个人的单独同意",
        "同意记录完整有效",
    ],
    "ISSUE-legal-document-gaps": [
        "法律文件已完整覆盖全部责任义务",
        "合同条款完全符合监管要求",
    ],
    "ISSUE-anonymization-uncertain": [
        "数据已匿名化且不涉及个人信息风险",
        "不存在重新识别风险",
    ],
}


def _external_expression(issue: IssueItem) -> str:
    if issue.issue_id == "ISSUE-recipient-security-evidence-missing":
        return (
            "当前材料已对境外接收方基本情况作出说明，但其数据安全管理制度、"
            "认证证明或第三方审计材料仍有待进一步补充，以增强安全保障能力论证。"
        )
    if issue.issue_id == "ISSUE-consent-evidence-missing":
        return (
            "涉及个人信息出境的，应进一步补充告知、单独同意或适用豁免情形的说明及佐证材料，"
            "以支撑个人信息权益保障相关论述。"
        )
    if issue.issue_id == "ISSUE-legal-document-gaps":
        return (
            "建议进一步核验并完善与境外接收方签署的法律文件，重点补充处理目的、保存期限、"
            "再转移约束、安全事件处置和违约责任等条款。"
        )
    if issue.issue_id == "ISSUE-anonymization-uncertain":
        return (
            "如拟主张相关数据已匿名化或去标识化，应补充技术验证、重识别风险评估或第三方审计材料；"
            "在材料补足前，建议采用审慎表述。"
        )
    if issue.category == "documentation":
        return "当前材料尚需进一步补充，以提高报告论证充分性和申报材料完整性。"
    if issue.category == "path":
        return "当前出境活动适用路径需结合诊断结论进一步复核，必要时应在正式提交前完成路径确认。"
    return f"建议围绕“{issue.title}”进一步补充事实说明、佐证材料和整改安排。"


def _internal_expression(issue: IssueItem) -> str:
    return f"{issue.title}：{issue.description} 建议：{issue.recommended_action}"


def build_writing_strategy(issues: list[IssueItem]) -> dict[str, Any]:
    strategies: list[dict[str, Any]] = []
    for issue in issues:
        forbidden = [*_BASE_FORBIDDEN_EXPRESSIONS, *_ISSUE_FORBIDDEN.get(issue.issue_id, [])]
        tone = "conservative" if issue.severity in {"HIGH", "BLOCKER"} else "balanced"
        strategies.append(
            {
                "issue_id": issue.issue_id,
                "issue_type": issue.category,
                "risk_level": issue.severity,
                "internal_expression": _internal_expression(issue),
                "external_expression": _external_expression(issue),
                "forbidden_expressions": forbidden,
                "tone": tone,
                "can_enter_external_report": True,
            }
        )

    return {
        "module": "assessment",
        "strategy_version": "v1",
        "global_external_tone": "正式、审慎、避免无依据的正面承诺",
        "global_forbidden_expressions": _BASE_FORBIDDEN_EXPRESSIONS,
        "strategies": strategies,
    }
