"""CN SCC Issue Builder — build IssueItem objects from agent results and rule engine findings.

Issues are the core compliance gap reporting mechanism. Each issue links to:
- Specific facts it references
- Rule/regulation refs
- Evidence refs
- Recommended actions
- Affected output chapters

Reference: docs/archive/design-provenance/认证标准合同路径.md — Facts/Issues/Evidence layered architecture
"""

from __future__ import annotations

from typing import Any

from backend.common.workflow import FactItem, IssueItem
from backend.domains.cn.scc_review.schema import (
    ContractFinding,
    DataFieldClassification,
    LegalBasisReviewItem,
    PathDiagnosisResult,
    RiskLevel,
)


def _issue(
    issue_id: str,
    title: str,
    description: str,
    category: str,
    severity: str,
    fact_refs: list[str] | None = None,
    rule_refs: list[str] | None = None,
    evidence_refs: list[str] | None = None,
    recommended_action: str = "",
    affects_outputs: list[str] | None = None,
    missing_materials: list[str] | None = None,
) -> IssueItem:
    return IssueItem(
        issue_id=issue_id,
        title=title,
        description=description,
        category=category,
        severity=severity,
        fact_refs=fact_refs or [],
        rule_refs=rule_refs or [],
        evidence_refs=evidence_refs or [],
        recommended_action=recommended_action,
        affects_outputs=affects_outputs or ["PIPIA报告", "批注版DOCX"],
        missing_materials=missing_materials or [],
    )


def _fact_refs_for_field(facts: list[FactItem], field_paths: list[str]) -> list[str]:
    """Find fact IDs matching the given field paths."""
    refs = []
    for fact in facts:
        for path in field_paths:
            if fact.field_path and path in fact.field_path:
                refs.append(fact.fact_id)
                break
    return refs


def build_scc_issues(
    facts: list[FactItem],
    path_diagnosis: PathDiagnosisResult | None,
    field_classifications: list[DataFieldClassification] | None,
    legal_basis_reviews: list[LegalBasisReviewItem] | None,
    contract_findings: list[ContractFinding] | None,
    evidence_verifications: list[dict] | None,
    regulations: list[Any],
) -> list[IssueItem]:
    """Build comprehensive issues list from all agent outputs."""

    issues: list[IssueItem] = []
    counter = [0]

    def next_id() -> str:
        counter[0] += 1
        return f"CN-SCC-ISSUE-{counter[0]:03d}"

    regulation_refs = [getattr(r, "source_id", str(r)) for r in regulations]

    # ── 1. Path-related issues ──
    if path_diagnosis:
        if path_diagnosis.recommended_path == "security_assessment":
            issues.append(_issue(
                issue_id=next_id(),
                title="触发安全评估路径",
                description=f"出境个人信息规模或数据类型触发安全评估门槛：{'；'.join(path_diagnosis.triggered_thresholds)}",
                category="path",
                severity="BLOCKER",
                rule_refs=regulation_refs[:3],
                recommended_action="建议立即启动数据出境安全评估程序，准备安全评估申报材料",
            ))

        if path_diagnosis.confidence < 0.7:
            issues.append(_issue(
                issue_id=next_id(),
                title="路径判断不确定度较高",
                description=f"推荐路径为{path_diagnosis.recommended_path}，但置信度仅{path_diagnosis.confidence}。阻断项：{'；'.join(path_diagnosis.blocking_issues)}",
                category="path",
                severity="HIGH" if path_diagnosis.confidence < 0.5 else "MEDIUM",
                rule_refs=regulation_refs[:2],
                recommended_action=f"建议补充材料后再进行路径判断：{'；'.join(path_diagnosis.next_questions[:3])}",
                missing_materials=path_diagnosis.next_questions[:3],
            ))

        if path_diagnosis.blocking_issues:
            for bi in path_diagnosis.blocking_issues[:3]:
                issues.append(_issue(
                    issue_id=next_id(),
                    title=f"路径阻断：{bi[:50]}",
                    description=bi,
                    category="path",
                    severity="MEDIUM",
                    rule_refs=regulation_refs[:1],
                    recommended_action="补充相关材料后再评估路径适用性",
                ))

    # ── 2. Data classification issues ──
    if field_classifications:
        mislabeled = [fc for fc in field_classifications if fc.risk in ("HIGH", "BLOCKER")]
        for fc in mislabeled[:5]:
            issues.append(_issue(
                issue_id=next_id(),
                title=f"字段分类风险：{fc.field_name}",
                description=f"用户标注'{fc.user_claim}'，系统判断为'{fc.agent_judgment}'。原因：{fc.reason}",
                category="data_classification",
                severity=fc.risk,
                recommended_action=f"重新评估'{fc.field_name}'的分类，补充必要证据：{'；'.join(fc.required_evidence[:3])}",
                missing_materials=fc.required_evidence[:3],
            ))

        medium_mislabeled = [fc for fc in field_classifications if fc.risk == "MEDIUM"]
        for fc in medium_mislabeled[:3]:
            issues.append(_issue(
                issue_id=next_id(),
                title=f"字段分类需关注：{fc.field_name}",
                description=f"用户标注'{fc.user_claim}'，系统判断存在分类风险。原因：{fc.reason}",
                category="data_classification",
                severity="MEDIUM",
                recommended_action=f"确认'{fc.field_name}'的分类和必要性",
            ))

    # ── 3. Legal basis issues ──
    if legal_basis_reviews:
        for review in legal_basis_reviews:
            if review.status in ("not_recommended", "weak", "insufficient_evidence"):
                severity: RiskLevel = "HIGH" if review.status == "not_recommended" else "MEDIUM"
                issues.append(_issue(
                    issue_id=next_id(),
                    title=f"合法性基础论证不充分：{review.legal_basis}",
                    description=f"合法性基础'{review.legal_basis}'的论证强度为'{review.status}'。{review.reason}",
                    category="lawful_basis",
                    severity=severity,
                    recommended_action=review.recommended_adjustment,
                    missing_materials=review.evidence_missing,
                ))

    # ── 4. Contract/document issues ──
    if contract_findings:
        for cf in contract_findings:
            issues.append(_issue(
                issue_id=next_id(),
                title=f"合同审查：{cf.issue[:60]}",
                description=f"定位：{cf.location}。{cf.risk_analysis}",
                category="legal_document",
                severity=cf.severity,
                recommended_action=cf.suggested_text,
                fact_refs=_fact_refs_for_field(facts, ["has_scc_draft"]),
            ))

    # ── 5. Evidence issues ──
    if evidence_verifications:
        weak_evidence = [
            ev for ev in evidence_verifications
            if ev.get("evidence_status") in ("user_claim_only", "partial_evidence")
        ]
        for ev in weak_evidence[:5]:
            severity: RiskLevel = "HIGH" if ev.get("evidence_status") == "user_claim_only" else "MEDIUM"
            issues.append(_issue(
                issue_id=next_id(),
                title=f"证据不足：{ev.get('claim', '')[:50]}",
                description=f"主张'{ev.get('claim', '')}'的证据状态为'{ev.get('evidence_status', '')}'。缺失：{ev.get('gap', '')}",
                category="documentation",
                severity=severity,
                recommended_action=ev.get("report_strategy", "补充证据后再生成报告"),
                missing_materials=[ev.get("gap", "")] if ev.get("gap") else [],
            ))

    # ── 6. Missing SCC draft issue ──
    has_scc = any(
        f.field_path and "has_scc_draft" in f.field_path and f.value is True
        for f in facts
    )
    if not has_scc:
        issues.append(_issue(
            issue_id=next_id(),
            title="未提供标准合同草案",
            description="缺少标准合同文本导致无法完成条款级定位审查，备案材料不具备提交条件",
            category="legal_document",
            severity="BLOCKER",
            recommended_action="先补齐SCC完整文本（含附件），再执行逐条款审查与修订",
            missing_materials=["标准合同完整文本（含全部附件）"],
        ))

    # ── 7. Default issue if none found ──
    if not issues:
        issues.append(_issue(
            issue_id=next_id(),
            title="初步审查未发现阻断性问题",
            description="基于当前输入信息，未命中高危风险项，但仍需持续复核和人工审查",
            category="other",
            severity="LOW",
            recommended_action="保持季度复核，记录版本差异与评审意见",
        ))

    return issues
