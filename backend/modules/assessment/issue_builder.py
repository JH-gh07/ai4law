from __future__ import annotations

from typing import Any

from backend.common.workflow import FactItem, IssueItem
from backend.modules.assessment.chapter_generator import ASSESSMENT_CHAPTER_KEYS
from backend.modules.assessment.schema import RegulationHit

ALL_CHAPTER_IDS = list(ASSESSMENT_CHAPTER_KEYS.values())


def _diagnosis_value(diagnosis_result: object | None, field: str) -> Any:
    if diagnosis_result is None:
        return None
    if isinstance(diagnosis_result, dict):
        return diagnosis_result.get(field)
    return getattr(diagnosis_result, field, None)


def _diagnosis_rule_ref(diagnosis_result: object | None) -> str:
    matched_rule_id = _diagnosis_value(diagnosis_result, "matched_rule_id")
    if matched_rule_id:
        return f"diagnosis:{matched_rule_id}"
    recommended_path = _diagnosis_value(diagnosis_result, "recommended_path") or "unknown"
    return f"diagnosis:{recommended_path}"


def _regulation_refs(regulations: list[RegulationHit]) -> list[str]:
    return [item.source_id for item in regulations if item.source_id]


def _by_field(facts: list[FactItem]) -> dict[str, FactItem]:
    return {fact.field_path or "": fact for fact in facts}


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


def build_assessment_issues(
    facts: list[FactItem],
    diagnosis_result: object | None,
    regulations: list[RegulationHit],
    attachment_notes: list[dict] | list[str],
) -> list[IssueItem]:
    field_facts = _by_field(facts)
    issues: list[IssueItem] = []
    regulation_refs = _regulation_refs(regulations)
    diagnosis_rule_ref = _diagnosis_rule_ref(diagnosis_result)
    legal_rule_refs = [diagnosis_rule_ref, *regulation_refs[:3]]

    recommended_path = _diagnosis_value(diagnosis_result, "recommended_path")
    recommended_path_fact = field_facts.get("diagnosis_result.recommended_path")
    if recommended_path and recommended_path != "security_assessment" and recommended_path_fact:
        issues.append(
            _issue(
                issue_id="ISSUE-path-mismatch",
                title="诊断路径与安全评估报告不匹配",
                description=f"诊断模块推荐路径为 {recommended_path}，当前仍在生成安全评估报告。",
                category="path",
                severity="HIGH",
                fact_refs=[recommended_path_fact.fact_id],
                rule_refs=[diagnosis_rule_ref],
                recommended_action="复核合规路径；如继续生成，应在报告中标注为强制生成的参考草案。",
                affects_outputs=["overview", "risk_remediation", "conclusion"],
            )
        )

    is_ciio_fact = field_facts.get("request.is_ciio")
    if is_ciio_fact and is_ciio_fact.normalized_value is True:
        issues.append(
            _issue(
                issue_id="ISSUE-ciio-security-assessment",
                title="CIIO 触发安全评估路径",
                description="输入事实显示企业属于 CIIO，应按高风险路径处理数据出境评估。",
                category="path",
                severity="HIGH",
                fact_refs=[is_ciio_fact.fact_id],
                rule_refs=legal_rule_refs,
                recommended_action="按安全评估申报要求准备自评估报告和配套材料。",
                affects_outputs=["overview", "risk_remediation", "conclusion"],
            )
        )

    important_data_fact = field_facts.get("request.contains_important_data")
    if important_data_fact and important_data_fact.normalized_value is True:
        issues.append(
            _issue(
                issue_id="ISSUE-important-data",
                title="重要数据触发高风险路径",
                description="输入事实显示本次出境涉及重要数据，应按安全评估口径处理。",
                category="data_scope",
                severity="HIGH",
                fact_refs=[important_data_fact.fact_id],
                rule_refs=legal_rule_refs,
                recommended_action="补充重要数据识别依据、目录映射和出境必要性说明。",
                affects_outputs=["data_scope", "risk_remediation", "conclusion"],
            )
        )

    pii_fact = field_facts.get("request.pii_count")
    if pii_fact and int(pii_fact.normalized_value or 0) >= 1_000_000:
        issues.append(
            _issue(
                issue_id="ISSUE-pii-threshold",
                title="个人信息规模达到安全评估阈值",
                description="普通个人信息出境人数达到 100 万人以上，触发安全评估关注点。",
                category="data_scope",
                severity="HIGH",
                fact_refs=[pii_fact.fact_id],
                rule_refs=legal_rule_refs,
                recommended_action="核验近 12 个月累计人数口径，并在报告中说明统计方法。",
                affects_outputs=["data_scope", "risk_remediation", "conclusion"],
            )
        )

    spi_fact = field_facts.get("request.spi_count")
    if spi_fact and int(spi_fact.normalized_value or 0) >= 10_000:
        issues.append(
            _issue(
                issue_id="ISSUE-spi-threshold",
                title="敏感个人信息规模达到安全评估阈值",
                description="敏感个人信息出境人数达到 1 万人以上，应按高风险口径处理。",
                category="data_scope",
                severity="HIGH",
                fact_refs=[spi_fact.fact_id],
                rule_refs=legal_rule_refs,
                recommended_action="补充敏感个人信息类型、数量统计和单独同意材料。",
                affects_outputs=["data_scope", "rights_impact", "risk_remediation", "conclusion"],
            )
        )

    uploaded_files_fact = field_facts.get("request.uploaded_files")
    if uploaded_files_fact and not uploaded_files_fact.normalized_value:
        issues.append(
            _issue(
                issue_id="ISSUE-missing-attachments",
                title="申报支撑材料缺失",
                description="当前请求未提供上传附件，报告中的材料审查和证据追溯能力不足。",
                category="documentation",
                severity="MEDIUM",
                fact_refs=[uploaded_files_fact.fact_id],
                rule_refs=[],
                recommended_action="补充数据清单、隐私政策、合同/协议、安全措施说明等材料。",
                affects_outputs=["overview", "security_measures", "risk_remediation", "conclusion"],
            )
        )
    elif not attachment_notes and uploaded_files_fact:
        issues.append(
            _issue(
                issue_id="ISSUE-attachments-not-parsed",
                title="附件解析摘要缺失",
                description="请求包含附件路径，但当前未形成可用附件解析摘要。",
                category="documentation",
                severity="LOW",
                fact_refs=[uploaded_files_fact.fact_id],
                rule_refs=[],
                recommended_action="检查附件路径和格式，确保解析摘要进入生成上下文。",
                affects_outputs=["security_measures", "risk_remediation"],
            )
        )

    receiver_fact = field_facts.get("request.receiver_country")
    if receiver_fact and not str(receiver_fact.normalized_value or "").strip():
        issues.append(
            _issue(
                issue_id="ISSUE-missing-receiver-country",
                title="境外接收方国家/地区缺失",
                description="未提供境外接收方国家/地区，无法充分评估接收方所在地风险。",
                category="recipient",
                severity="HIGH",
                fact_refs=[receiver_fact.fact_id],
                rule_refs=regulation_refs[:3],
                recommended_action="补充境外接收方名称、国家/地区、联系方式和处理角色。",
                affects_outputs=["recipient_capability", "risk_remediation", "conclusion"],
            )
        )

    purpose_fact = field_facts.get("request.transfer_purpose")
    if purpose_fact and not str(purpose_fact.normalized_value or "").strip():
        issues.append(
            _issue(
                issue_id="ISSUE-missing-transfer-purpose",
                title="出境目的不明确",
                description="未提供清晰的出境目的，无法支撑必要性和合法性分析。",
                category="data_scope",
                severity="HIGH",
                fact_refs=[purpose_fact.fact_id],
                rule_refs=regulation_refs[:3],
                recommended_action="补充出境目的、处理方式、使用场景和必要性论证。",
                affects_outputs=["necessity_legal_basis", "risk_remediation", "conclusion"],
            )
        )

    return issues
