from __future__ import annotations

from backend.common.workflow import FactItem, IssueItem
from backend.modules.cn_flow.schema import CNFlowRequest, CNFlowRiskItem


CN_FLOW_CHAPTER_KEYS: dict[str, str] = {
    "场景定义与适用范围": "scope_applicability",
    "数据类型与实体结构分析": "data_entity_structure",
    "限制条件命中分析": "restriction_analysis",
    "风险分级与处置建议": "risk_actions",
}


def _issue(
    issue_id: str,
    title: str,
    description: str,
    category: str,
    severity: str,
    fact_refs: list[str],
    rule_refs: list[str],
    recommended_action: str,
    affects_outputs: list[str],
) -> IssueItem:
    return IssueItem(
        issue_id=issue_id,
        title=title,
        description=description,
        category=category,
        severity=severity,
        fact_refs=fact_refs,
        rule_refs=rule_refs,
        recommended_action=recommended_action,
        affects_outputs=affects_outputs,
    )


def build_cn_flow_issues(
    payload: CNFlowRequest,
    facts: list[FactItem],
    risk_items: list[CNFlowRiskItem],
    regulations: list[dict],
) -> list[IssueItem]:
    by_field = {fact.field_path: fact for fact in facts}
    attachment_fact = by_field.get("request.attachments")
    recipients_fact = by_field.get("request.recipient_entities")
    sensitive_fact = by_field.get("request.sensitive_data_flags")
    chain_fact = by_field.get("request.transfer_chain")
    rule_refs = [item.get("source_id", "") for item in regulations if item.get("source_id")]

    issues: list[IssueItem] = []

    if attachment_fact and len(payload.attachments) < 2:
        issues.append(
            _issue(
                issue_id="CNF-ISSUE-ATTACHMENT-MISSING",
                title="附件材料不完整",
                description="data_inventory 或 entity_inventory 缺失，影响对华数据流动审查完整性。",
                category="documentation",
                severity="HIGH",
                fact_refs=[attachment_fact.fact_id],
                rule_refs=rule_refs[:2],
                recommended_action="补齐 data_inventory 与 entity_inventory 后重跑评估。",
                affects_outputs=["scope_applicability", "risk_actions"],
            )
        )

    if recipients_fact and any(entity.is_restricted_party for entity in payload.recipient_entities):
        issues.append(
            _issue(
                issue_id="CNF-ISSUE-RESTRICTED-ENTITY",
                title="命中受限主体",
                description="接收方实体中存在受限主体，存在禁止或高度受限的数据流动风险。",
                category="recipient",
                severity="BLOCKER",
                fact_refs=[recipients_fact.fact_id],
                rule_refs=rule_refs[:3],
                recommended_action="暂停传输并完成受限主体复核、法务豁免审批和替代路径评估。",
                affects_outputs=["restriction_analysis", "risk_actions"],
            )
        )

    if sensitive_fact and payload.sensitive_data_flags:
        issues.append(
            _issue(
                issue_id="CNF-ISSUE-SENSITIVE-DATA",
                title="存在敏感数据跨境传输",
                description="敏感数据标记存在，需验证最小化、脱敏和接收方控制措施。",
                category="data_scope",
                severity="HIGH",
                fact_refs=[sensitive_fact.fact_id],
                rule_refs=rule_refs[:2],
                recommended_action="补充敏感字段清单、去标识化策略与接收方限制条款。",
                affects_outputs=["data_entity_structure", "risk_actions"],
            )
        )

    if chain_fact and ("subprocessor" in payload.transfer_chain.lower() or "第三方" in payload.transfer_chain):
        issues.append(
            _issue(
                issue_id="CNF-ISSUE-ONWARD-TRANSFER",
                title="存在 onward transfer 复杂链路",
                description="传输链路包含 subprocessor 或第三方再传输，控制链条存在断点风险。",
                category="contract",
                severity="MEDIUM",
                fact_refs=[chain_fact.fact_id],
                rule_refs=rule_refs[:2],
                recommended_action="补充 onward transfer 清单、再传输审批与审计追踪机制。",
                affects_outputs=["restriction_analysis", "risk_actions"],
            )
        )

    for item in risk_items:
        risk_fact = by_field.get("derived.risk_item_ids")
        if risk_fact:
            issues.append(
                _issue(
                    issue_id=f"CNF-ISSUE-{item.risk_id}",
                    title=item.title,
                    description=item.basis,
                    category="other",
                    severity=item.risk_level,
                    fact_refs=[risk_fact.fact_id],
                    rule_refs=rule_refs[:2],
                    recommended_action=item.recommendation,
                    affects_outputs=["risk_actions"],
                )
            )

    return issues
