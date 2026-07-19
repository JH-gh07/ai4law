"""DPIA consistency checker — validates DPIA draft against facts, issues, and regulatory requirements.

9 DPIA-specific check dimensions:
1. DPIA trigger coverage
2. Processing description completeness
3. Consultation section
4. Necessity & proportionality
5. Risk matrix completeness
6. Mitigation verifiability
7. DPO opinion integration
8. Prior consultation if residual high
9. Forbidden DPIA expressions
"""

from __future__ import annotations

from typing import Any

from backend.common.workflow import GenerationContextPack
from backend.domains.eu.dpia.schema import DPIAChapterContent, DPIAProjectProfile


def _regulation_rule_ids(context_pack: GenerationContextPack) -> set[str]:
    return {
        str(item.get("source_id"))
        for item in context_pack.regulations
        if item.get("source_id")
    }


def _is_known_rule_ref(rule_ref: str, regulation_ids: set[str]) -> bool:
    return rule_ref.startswith("diagnosis:") or rule_ref.startswith("dpia_need:") or rule_ref in regulation_ids


def check_context_pack_consistency(context_pack: GenerationContextPack) -> list[str]:
    """Verify that all fact/rule/evidence references across issues and evidence chain are consistent."""
    issues: list[str] = []
    fact_ids = {fact.fact_id for fact in context_pack.facts}
    issue_ids = {issue.issue_id for issue in context_pack.issues}
    evidence_ids = {evidence.evidence_id for evidence in context_pack.evidence_chain}
    regulation_ids = _regulation_rule_ids(context_pack)

    for issue in context_pack.issues:
        missing_fact_refs = [ref for ref in issue.fact_refs if ref not in fact_ids]
        if missing_fact_refs:
            issues.append(
                f"Issue {issue.issue_id} references missing facts: {', '.join(missing_fact_refs)}."
            )
        missing_rule_refs = [
            ref for ref in issue.rule_refs
            if not _is_known_rule_ref(ref, regulation_ids)
        ]
        if missing_rule_refs:
            issues.append(
                f"Issue {issue.issue_id} references missing rules: {', '.join(missing_rule_refs)}."
            )
        missing_evidence_refs = [
            ref for ref in issue.evidence_refs if ref not in evidence_ids
        ]
        if missing_evidence_refs:
            issues.append(
                f"Issue {issue.issue_id} references missing evidence: {', '.join(missing_evidence_refs)}."
            )

    for evidence in context_pack.evidence_chain:
        missing_fact_refs = [ref for ref in evidence.fact_refs if ref not in fact_ids]
        if missing_fact_refs:
            issues.append(
                f"Evidence {evidence.evidence_id} references missing facts: {', '.join(missing_fact_refs)}."
            )
        missing_rule_refs = [
            ref for ref in evidence.rule_refs
            if not _is_known_rule_ref(ref, regulation_ids)
        ]
        if missing_rule_refs:
            issues.append(
                f"Evidence {evidence.evidence_id} references missing rules: {', '.join(missing_rule_refs)}."
            )
        missing_issue_refs = [
            ref for ref in evidence.used_by
            if ref.startswith("DPIA-ISSUE-") and ref not in issue_ids
        ]
        if missing_issue_refs:
            issues.append(
                f"Evidence {evidence.evidence_id} is used by missing issues: {', '.join(missing_issue_refs)}."
            )

    return issues


def check_dpia_trigger_coverage(report_content: str, context_pack: GenerationContextPack) -> list[str]:
    """Check 1: Whether DPIA trigger reasons are explained."""
    issues: list[str] = []
    diagnosis = context_pack.diagnosis_result or {}
    if diagnosis.get("dpia_required"):
        if "Article 35" not in report_content and "GDPR Art 35" not in report_content:
            issues.append("DPIA is required but GDPR Art 35 is not referenced in the report.")
        if "WP248" not in report_content:
            issues.append("DPIA trigger reasons should reference WP248 high-risk criteria.")
    return issues


def check_processing_description_completeness(
    report_content: str, context_pack: GenerationContextPack
) -> list[str]:
    """Check 2: Whether processing description contains data flow, types, count, retention."""
    issues: list[str] = []
    checks = {
        "data flow / lifecycle": any(
            kw in report_content.lower() for kw in ("数据流", "收集", "处理", "存储", "删除", "data flow")
        ),
        "data categories": any(
            kw in report_content for kw in ("数据类别", "data categor", "数据类型")
        ),
        "retention period": any(
            kw in report_content for kw in ("保留期", "retention", "保存期限")
        ),
    }
    for check_name, passed in checks.items():
        if not passed:
            issues.append(f"Processing description may lack: {check_name}.")
    return issues


def check_consultation_section(report_content: str, context_pack: GenerationContextPack) -> list[str]:
    """Check 3: Whether consultation process is recorded."""
    issues: list[str] = []
    if not any(kw in report_content for kw in ("咨询", "consult", "DPO")):
        issues.append("Consultation section should mention internal/external consultation or DPO involvement.")
    return issues


def check_necessity_proportionality(report_content: str, context_pack: GenerationContextPack) -> list[str]:
    """Check 4: Whether necessity and proportionality analyses address identified issues."""
    issues: list[str] = []
    if "必要性" not in report_content and "necessity" not in report_content.lower():
        issues.append("Necessity analysis is missing from the report.")
    if "相称性" not in report_content and "proportionality" not in report_content.lower():
        issues.append("Proportionality analysis is missing from the report.")
    if "Art 6" not in report_content:
        issues.append("Lawful basis (GDPR Art 6) should be discussed in the necessity section.")
    return issues


def check_risk_matrix_completeness(
    report_content: str, context_pack: GenerationContextPack
) -> list[str]:
    """Check 5: Whether risk matrix is complete and each HIGH risk has mitigation."""
    issues: list[str] = []
    high_issues = [iss for iss in context_pack.issues if iss.severity in {"HIGH", "BLOCKER"}]
    for issue in high_issues:
        if issue.issue_id not in report_content and issue.title not in report_content:
            issues.append(
                f"HIGH/BLOCKER issue {issue.issue_id} ({issue.title}) not mentioned in report."
            )
    return issues


def check_mitigation_verifiability(report_content: str, context_pack: GenerationContextPack) -> list[str]:
    """Check 6: Whether mitigation measures are specific and verifiable."""
    issues: list[str] = []
    if "缓解" not in report_content and "mitigation" not in report_content.lower():
        issues.append("Mitigation measures section appears empty or missing.")
    # Check for vague mitigation language
    vague_markers = ["加强管理", "提升意识", "持续关注", "定期检查"]
    for marker in vague_markers:
        if marker in report_content:
            issues.append(
                f"Vague mitigation phrasing detected: '{marker}'. "
                "Mitigation should specify concrete actions, responsible parties, and timelines."
            )
    return issues


def check_dpo_opinion_integrated(report_content: str, context_pack: GenerationContextPack) -> list[str]:
    """Check 7: Whether DPO opinion is integrated into the signoff section."""
    issues: list[str] = []
    if "DPO" not in report_content:
        issues.append("DPO opinion should be referenced in the signoff/record section.")
    return issues


def check_prior_consultation_if_residual_high(
    report_content: str, context_pack: GenerationContextPack
) -> list[str]:
    """Check 8: Whether Art 36 prior consultation is suggested if residual risk remains high."""
    issues: list[str] = []
    diagnosis = context_pack.diagnosis_result or {}
    if diagnosis.get("prior_consultation_possible") is True:
        if "Art 36" not in report_content and "Article 36" not in report_content:
            issues.append(
                "Prior consultation is possible (residual high risk) but GDPR Art 36 "
                "is not mentioned in the report."
            )
    return issues


def check_forbidden_dpia_expressions(report_content: str) -> list[str]:
    """Check 9: Whether banned DPIA expressions appear in the external report."""
    issues: list[str] = []
    forbidden = [
        "风险已完全消除",
        "不存在歧视风险",
        "已充分取得所有同意",
        "匿名化后无任何个人数据风险",
        "自动化决策不影响个人权利",
        "无需进一步监管沟通",
        "可直接上线",
        "完全符合GDPR要求",
    ]
    for expr in forbidden:
        if expr in report_content:
            issues.append(f"Forbidden DPIA expression detected: '{expr}'.")
    return issues


def _collect_forbidden_expressions(context_pack: GenerationContextPack) -> list[str]:
    ws = context_pack.writing_strategy or {}
    global_forbidden: list[str] = list(ws.get("global_forbidden_expressions", []))
    issue_forbidden: list[str] = []
    for strategy in ws.get("strategies", []):
        if isinstance(strategy, dict):
            issue_forbidden.extend(strategy.get("forbidden_expressions", []))
    return sorted(set(global_forbidden + issue_forbidden))


def check_internal_expression_leakage(
    report_content: str, context_pack: GenerationContextPack
) -> list[str]:
    """Check that internal_expression content does not leak into the external report."""
    issues: list[str] = []
    ws = context_pack.writing_strategy or {}
    for strategy in ws.get("strategies", []):
        if not isinstance(strategy, dict):
            continue
        internal = strategy.get("internal_expression", "")
        for sentence in internal.replace("；", "。").split("。"):
            sentence = sentence.strip()
            if len(sentence) >= 15 and sentence in report_content:
                issues.append(
                    f"Internal expression leaked into external report for "
                    f"{strategy.get('issue_id', '?')}: '{sentence[:60]}...'"
                )
    return issues


class DPIAConsistencyChecker:
    """Validate DPIA draft chapters against facts, issues, and legal grounding."""

    def check(self, profile: DPIAProjectProfile, chapters: list[DPIAChapterContent]) -> list[str]:
        issues: list[str] = []
        if not chapters:
            return ["No chapters generated."]

        for chapter in chapters:
            if not chapter.citations:
                issues.append(f"Chapter {chapter.chapter_no} ({chapter.title}) has no citations.")

        has_high_issues = (
            profile.special_category_data
            or profile.automated_decision_making
            or profile.systematic_monitoring
            or profile.vulnerable_data_subjects
        )
        if has_high_issues and chapters and chapters[-1].risk_level != "high":
            issues.append(
                "Final chapter risk level should be 'high' given high-risk processing activities."
            )

        return issues

    def check_with_context(
        self,
        profile: DPIAProjectProfile,
        chapters: list[DPIAChapterContent],
        context_pack: GenerationContextPack,
    ) -> list[str]:
        """Run all DPIA consistency checks (including cross-reference and expression checks)."""
        report_content = "\n".join(chapter.content for chapter in chapters)
        forbidden_exprs = _collect_forbidden_expressions(context_pack)

        all_issues: list[str] = []
        all_issues.extend(self.check(profile, chapters))
        all_issues.extend(check_context_pack_consistency(context_pack))
        all_issues.extend(check_dpia_trigger_coverage(report_content, context_pack))
        all_issues.extend(check_processing_description_completeness(report_content, context_pack))
        all_issues.extend(check_consultation_section(report_content, context_pack))
        all_issues.extend(check_necessity_proportionality(report_content, context_pack))
        all_issues.extend(check_risk_matrix_completeness(report_content, context_pack))
        all_issues.extend(check_mitigation_verifiability(report_content, context_pack))
        all_issues.extend(check_dpo_opinion_integrated(report_content, context_pack))
        all_issues.extend(check_prior_consultation_if_residual_high(report_content, context_pack))
        all_issues.extend(check_forbidden_dpia_expressions(report_content))

        # Check strategy-level forbidden expressions
        for expr in forbidden_exprs:
            if expr in report_content:
                all_issues.append(f"Forbidden expression from writing strategy detected: '{expr}'.")

        all_issues.extend(check_internal_expression_leakage(report_content, context_pack))

        return all_issues
