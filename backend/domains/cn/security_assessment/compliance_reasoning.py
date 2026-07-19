"""Compliance reasoning matrix — fact status × reasonableness × ambiguity × legal risk × expression strategy.

Produces ComplianceReasoningItem for each key assessment area, enabling the LLM to
generate reports with proper boundary awareness rather than generic positive claims.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.common.workflow.facts import FactItem
from backend.common.workflow.issues import IssueItem


@dataclass
class ComplianceReasoningItem:
    target: str
    user_claim: str
    fact_status: str  # user_claim_only | partially_supported | fully_documented
    reasonableness: str
    ambiguity: str
    legal_risk: str
    possible_non_compliance: str
    correct_expression: str
    external_claim_allowed: bool = False
    related_issue_ids: list[str] = field(default_factory=list)


# ── Reasoning templates per assessment area ──

_REASONING_TEMPLATES: dict[str, dict[str, Any]] = {
    "ciio_status": {
        "target": "关键信息基础设施运营者认定",
        "fact_status": "user_claim_only",
        "reasonableness": "方向明确但缺少外部证据佐证",
        "ambiguity": "未提供CIIO认定文件或主管部门确认函",
        "legal_risk": "如果实际属于CIIO但未申报，将直接触发强制安全评估且面临处罚",
        "possible_non_compliance": "无法排除实际属于CIIO但未如实申报的风险",
        "correct_expression": "用户声明不属于CIIO，但建议补充主管部门确认或行业主管部门函件予以佐证。",
        "external_claim_allowed": False,
    },
    "important_data": {
        "target": "重要数据认定",
        "fact_status": "user_claim_only",
        "reasonableness": "方向明确但缺少分类分级支撑",
        "ambiguity": "未提供数据分类分级结果或行业主管部门对重要数据的认定文件",
        "legal_risk": "如果实际涉及重要数据但未申报安全评估，数据出境行为可能违法",
        "possible_non_compliance": "无法排除所传输数据包含重要数据但未被识别的风险",
        "correct_expression": "用户声明不涉及重要数据，但建议完成数据分类分级并取得主管部门确认后再行申报。",
        "external_claim_allowed": False,
    },
    "recipient_security": {
        "target": "境外接收方安全保障能力",
        "fact_status": "user_claim_only",
        "reasonableness": "方向合理，但表述过于概括",
        "ambiguity": "未说明具体认证标准、认证名称、有效期、审计范围、适用系统",
        "legal_risk": "接收方安全保障能力证明不足以支撑报告中的正面结论",
        "possible_non_compliance": "可能难以满足安全评估办法对境外接收方安全能力的要求",
        "correct_expression": "用户已说明接收方遵循相关标准，但尚需补充认证证书、审计报告或安全制度文件予以佐证。",
        "external_claim_allowed": False,
    },
    "legal_document": {
        "target": "法律文件约定情况",
        "fact_status": "partially_supported",
        "reasonableness": "已提供相关协议，但条款覆盖不完整",
        "ambiguity": "六项核心条款中部分条款未被检索到或表述不够明确",
        "legal_risk": "法律文件如未覆盖安全评估办法第九条全部要求，申报材料可能被退回",
        "possible_non_compliance": "可能存在法律文件不足以保障数据主体权益的风险",
        "correct_expression": "已提供相关法律文件，经审查发现以下条款需补充: {missing}。建议在正式申报前修订完善。",
        "external_claim_allowed": False,
    },
    "consent_record": {
        "target": "个人信息出境告知同意",
        "fact_status": "user_claim_only",
        "reasonableness": "方向明确但缺少可验证记录",
        "ambiguity": "未提供单独的告知同意记录、隐私政策版本快照或同意日志",
        "legal_risk": "无法充分证明已履行个保法第三十九条规定的告知同意义务",
        "possible_non_compliance": "可能面临合法性基础不足的监管质疑",
        "correct_expression": "用户声明已取得数据主体同意，但在现有材料条件下尚无法充分验证单独同意的获取过程、范围和记录保存情况。",
        "external_claim_allowed": False,
    },
    "onward_transfer": {
        "target": "再转移约束",
        "fact_status": "user_claim_only",
        "reasonableness": "未提供再转移审批机制和约束条款",
        "ambiguity": "未说明接收方是否可能将数据再转移至其他主体",
        "legal_risk": "如果存在未受合同约束的再转移，数据可能流向不可控的第三方",
        "possible_non_compliance": "可能违反数据出境安全评估办法第九条关于再转移约束的要求",
        "correct_expression": "当前材料未充分说明境外接收方是否存在再转移安排及其约束措施，建议补充相关合同条款和审批记录。",
        "external_claim_allowed": False,
    },
    "anonymization": {
        "target": "匿名化/去标识化有效性",
        "fact_status": "user_claim_only",
        "reasonableness": "技术手段方向合理但缺乏第三方验证",
        "ambiguity": "未提供匿名化/去标识化的技术方案、有效性评估或审计报告",
        "legal_risk": "如果匿名化不充分，相关数据仍属于个人信息，需履行全部合规义务",
        "possible_non_compliance": "可能低估了数据可重识别风险，导致合规路径选择或风险评估出现偏差",
        "correct_expression": "用户声称已采取匿名化/去标识化措施，但鉴于匿名化有效性对合规判断具有关键影响，建议提供技术方案和第三方评估以充分论证。",
        "external_claim_allowed": False,
    },
    "necessity_proportionality": {
        "target": "出境必要性与相称性",
        "fact_status": "user_claim_only",
        "reasonableness": "必要性描述存在但论证不够充分",
        "ambiguity": "未详细说明为何无法以境内处理替代，以及数据处理范围与目的的相称性",
        "legal_risk": "必要性论证不充分可能导致安全评估申报被要求补充说明",
        "possible_non_compliance": "可能无法满足个保法第六条关于目的限制和数据最小化的要求",
        "correct_expression": "用户说明了出境业务目的，但建议补充以下论证: 为何无法在境内完成处理、数据处理范围如何控制在实现目的所必需的最小限度。",
        "external_claim_allowed": False,
    },
    "security_measures": {
        "target": "安全保障措施有效性",
        "fact_status": "partially_supported",
        "reasonableness": "措施方向正确，但缺乏可验证的证据支撑",
        "ambiguity": "未提供安全措施的详细配置、实施范围、有效性测试或第三方审计结果",
        "legal_risk": "安全措施概括性描述可能不足以满足安全评估对保障能力的具体要求",
        "possible_non_compliance": "可能存在安全保障水平与数据风险等级不匹配的风险",
        "correct_expression": "用户已列出所采取的安全措施，建议补充各项措施的技术配置细节、实施范围、有效性验证记录或第三方审计报告。",
        "external_claim_allowed": False,
    },
}


def _get_attachment_evidence_map(attachment_metadata: list[dict]) -> dict[str, bool]:
    """Build an evidence presence map from attachment_metadata."""
    evidence: dict[str, bool] = {
        "has_contract": False, "has_privacy_policy": False,
        "has_certification": False, "has_audit_report": False,
        "has_consent_record": False, "has_data_inventory": False,
        "has_internal_policy": False,
    }
    for meta in attachment_metadata:
        atype = meta.get("type", "")
        filename = str(meta.get("filename") or meta.get("source_ref", "")).lower()
        summary = str(meta.get("summary", "")).lower()
        if "contract" in atype or "协议" in filename:
            evidence["has_contract"] = True
        if "privacy_policy" in atype or "隐私" in filename or "privacy" in summary:
            evidence["has_privacy_policy"] = True
        if (
            "certification" in atype
            or "认证" in filename
            or "iso" in filename
            or "soc" in filename
            or "cert" in summary
        ):
            evidence["has_certification"] = True
        if "audit" in atype or "审计" in filename or "审计" in summary:
            evidence["has_audit_report"] = True
        if "consent" in atype or "同意" in filename or "同意" in summary or "告知" in summary:
            evidence["has_consent_record"] = True
        if "data_inventory" in atype or "数据清单" in filename or "字段" in summary:
            evidence["has_data_inventory"] = True
        if "policy" in atype or "制度" in filename or "制度" in summary or "预案" in filename:
            evidence["has_internal_policy"] = True
    return evidence


def build_compliance_reasoning(
    facts: list[FactItem],
    issues: list[IssueItem],
    payload: Any = None,
    attachment_metadata: list[dict] | None = None,
) -> list[ComplianceReasoningItem]:
    """Build the compliance reasoning matrix — one item per key assessment area.

    Each item expresses: what the user claimed, what fact status it has,
    whether the claim is reasonable, what is ambiguous, what legal risks exist,
    what the correct external expression should be, and whether a positive
    external claim is allowed.
    """
    evidence = _get_attachment_evidence_map(attachment_metadata or [])

    # Map issue categories to reasoning templates
    issue_category_map = {
        "recipient": "recipient_security",
        "consent": "consent_record",
        "contract": "legal_document",
        "onward_transfer": "onward_transfer",
        "anonymization": "anonymization",
        "necessity": "necessity_proportionality",
        "data_classification": "important_data",
        "legal_document": "legal_document",
        "security_measure": "security_measures",
    }

    items: list[ComplianceReasoningItem] = []

    # Always include core reasoning items
    core_targets = ["ciio_status", "important_data", "recipient_security", "legal_document",
                    "consent_record", "onward_transfer", "necessity_proportionality", "security_measures"]
    for target in core_targets:
        template = _REASONING_TEMPLATES.get(target)
        if template is None:
            continue
        # Enhance with evidence
        fact_status = template["fact_status"]
        if target == "legal_document" and evidence.get("has_contract"):
            fact_status = "partially_supported"
        if target == "recipient_security" and evidence.get("has_certification"):
            fact_status = "partially_supported"
        if target == "consent_record" and evidence.get("has_consent_record"):
            fact_status = "partially_supported"
        if target == "security_measures" and (evidence.get("has_certification") or evidence.get("has_audit_report")):
            fact_status = "partially_supported"

        # Find related issues
        related = [
            issue.issue_id for issue in issues
            if issue_category_map.get(issue.category) == target
        ]

        items.append(ComplianceReasoningItem(
            target=template["target"],
            user_claim=f"用户声称情况（证据状态: {fact_status}）",
            fact_status=fact_status,
            reasonableness=template["reasonableness"],
            ambiguity=template["ambiguity"],
            legal_risk=template["legal_risk"],
            possible_non_compliance=template["possible_non_compliance"],
            correct_expression=template["correct_expression"],
            external_claim_allowed=template["external_claim_allowed"],
            related_issue_ids=related,
        ))

    return items


def render_compliance_reasoning_markdown(items: list[ComplianceReasoningItem]) -> str:
    """Render compliance reasoning items as a user-facing markdown document."""
    lines = [
        "# 合规推理说明",
        "",
        "本文档说明系统对各评估维度的合规判断逻辑和表达策略。",
        "",
        "| 评估维度 | 事实状态 | 合理性 | 法律风险 | 对外表达策略 |",
        "|---------|---------|--------|---------|------------|",
    ]
    for item in items:
        lines.append(
            f"| {item.target} | {item.fact_status} | {item.reasonableness[:30]}... | "
            f"{item.legal_risk[:30]}... | {'不可正面肯定' if not item.external_claim_allowed else '可正面表述'} |"
        )

    lines.append("")
    lines.append("## 逐项详细说明")
    lines.append("")
    for item in items:
        lines.append(f"### {item.target}")
        lines.append(f"- **事实状态**: {item.fact_status}")
        lines.append(f"- **合理性**: {item.reasonableness}")
        lines.append(f"- **模糊性**: {item.ambiguity}")
        lines.append(f"- **法律风险**: {item.legal_risk}")
        lines.append(f"- **可能不合规**: {item.possible_non_compliance}")
        lines.append(f"- **正确对外表述**: {item.correct_expression}")
        lines.append(f"- **是否允许正面结论**: {'是' if item.external_claim_allowed else '否'}")
        if item.related_issue_ids:
            lines.append(f"- **关联问题**: {', '.join(item.related_issue_ids)}")
        lines.append("")

    return "\n".join(lines)
