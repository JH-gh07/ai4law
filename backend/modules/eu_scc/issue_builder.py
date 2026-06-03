"""EU SCC issue builder — identifies compliance issues from rule engine findings."""

from __future__ import annotations

from backend.common.workflow import FactItem, IssueItem
from backend.modules.eu_scc.schema import SCCRuleEngineResult


EU_SCC_CHAPTER_KEYS: dict[str, str] = {
    "文件概要": "document_overview",
    "总体合规评级": "overall_rating",
    "条款级审查发现": "clause_findings",
    "法规依据与修改建议": "legal_basis_and_recommendations",
}


def _issue(issue_id, title, description, category, severity, fact_refs, rule_refs, recommended_action, affects_outputs) -> IssueItem:
    return IssueItem(
        issue_id=issue_id, title=title, description=description,
        category=category, severity=severity, fact_refs=fact_refs,
        rule_refs=rule_refs, recommended_action=recommended_action,
        affects_outputs=affects_outputs,
    )


def build_eu_scc_issues(
    facts: list[FactItem],
    rule_result: SCCRuleEngineResult,
    regulations: list[dict],
) -> list[IssueItem]:
    rule_refs = [r.get("source_id", "") for r in regulations if r.get("source_id")][:5]
    if not rule_refs:
        rule_refs = ["EU 2021/914", "GDPR Article 46", "Schrems II C-311/18", "EDPB 01/2020"]

    issues: list[IssueItem] = []
    by_field = {f.field_path: f for f in facts if f.field_path}

    mv = rule_result.module_validation
    if not mv.is_correct:
        issues.append(_issue(
            "EU-SCC-ISSUE-MODULE-MISMATCH",
            f"模块选择错误: 应为{mv.expected_module}, 实际{mv.actual_module}",
            mv.mismatch_reason,
            "documentation", "HIGH",
            [f.fact_id for f in facts if f.field_path and "module" in f.field_path][:2],
            rule_refs + ["EU 2021/914"],
            f"将文档模块从 {mv.actual_module} 改为 {mv.expected_module} 并确认 Annex I.A 中的角色与模块一致。",
            ["overall_rating", "clause_findings"],
        ))

    cc = rule_result.clause_comparison
    if cc.deviations_found > 0:
        issues.append(_issue(
            "EU-SCC-ISSUE-CLAUSE-DEVIATIONS",
            f"标准条款被修改: {cc.deviations_found}处偏离",
            f"EU 2021/914 标准条款中发现 {cc.deviations_found} 处修改，可能削弱对数据主体的保护。",
            "contract", "HIGH",
            [f.fact_id for f in facts if f.field_path and "deviation" in f.field_path][:2],
            rule_refs + ["EU 2021/914 Recital 3"],
            "逐项复核偏离条款。涉及不可冲突条款的修改应恢复为标准文本。",
            ["clause_findings", "legal_basis_and_recommendations"],
        ))

    tia = rule_result.tia_review
    if tia.has_third_country_transfer:
        issues.append(_issue(
            "EU-SCC-ISSUE-THIRD-COUNTRY",
            f"第三国传输风险: {', '.join(tia.third_country_transfers[:3])}",
            f"数据涉及向非充分性认定第三国的传输。TIA={'存在' if tia.tia_present else '缺失'}，Schrems II 补充措施={'存在' if tia.schrems_ii_measures_present else '不足'}。",
            "cross_border", "HIGH",
            [f.fact_id for f in facts if f.field_path and "third_country" in f.field_path][:2],
            rule_refs + ["Schrems II C-311/18", "EDPB 01/2020"],
            "完成 TIA；针对第三国法律环境实施 Schrems II 补充措施。",
            ["overall_rating", "clause_findings", "legal_basis_and_recommendations"],
        ))

    # Per-finding issues
    for finding in rule_result.all_findings:
        if finding.severity == "HIGH":
            issues.append(_issue(
                f"EU-SCC-FINDING-{finding.finding_id}",
                f"[{finding.severity}] {finding.location}: {finding.risk_analysis[:100]}",
                finding.risk_analysis,
                "other", finding.severity,
                [f.fact_id for f in facts[:1]],
                rule_refs,
                finding.recommendation,
                ["clause_findings", "legal_basis_and_recommendations"],
            ))

    if rule_result.overall_rating == "LOW" and not tia.has_third_country_transfer and cc.deviations_found == 0:
        issues.append(_issue(
            "EU-SCC-ISSUE-NO-ISSUES",
            "未发现高风险问题",
            "当前 SCC 文档未发现模块错误、标准条款削弱、TIA 缺失或 Annex 重大缺陷。",
            "other", "LOW",
            [f.fact_id for f in facts[:1]],
            rule_refs,
            "保持季度复审，监控法规更新和子处理者变更。",
            ["overall_rating"],
        ))

    return issues
