from __future__ import annotations

from typing import Any

from backend.common.workflow import GenerationContextPack
from backend.domains.cn.security_assessment.schema import ChapterContent, CompanyProfile


def _regulation_rule_ids(context_pack: GenerationContextPack) -> set[str]:
    return {
        str(item.get("source_id"))
        for item in context_pack.regulations
        if item.get("source_id")
    }


def _is_known_rule_ref(rule_ref: str, regulation_ids: set[str]) -> bool:
    return rule_ref.startswith("diagnosis:") or rule_ref in regulation_ids


def check_context_pack_consistency(context_pack: GenerationContextPack) -> list[str]:
    issues: list[str] = []
    fact_ids = {fact.fact_id for fact in context_pack.facts}
    issue_ids = {issue.issue_id for issue in context_pack.issues}
    evidence_ids = {evidence.evidence_id for evidence in context_pack.evidence_chain}
    regulation_ids = _regulation_rule_ids(context_pack)

    for issue in context_pack.issues:
        missing_fact_refs = [fact_ref for fact_ref in issue.fact_refs if fact_ref not in fact_ids]
        if missing_fact_refs:
            issues.append(f"Issue {issue.issue_id} references missing facts: {', '.join(missing_fact_refs)}.")

        missing_rule_refs = [
            rule_ref for rule_ref in issue.rule_refs if not _is_known_rule_ref(rule_ref, regulation_ids)
        ]
        if missing_rule_refs:
            issues.append(f"Issue {issue.issue_id} references missing rules: {', '.join(missing_rule_refs)}.")

        missing_evidence_refs = [
            evidence_ref for evidence_ref in issue.evidence_refs if evidence_ref not in evidence_ids
        ]
        if missing_evidence_refs:
            issues.append(f"Issue {issue.issue_id} references missing evidence: {', '.join(missing_evidence_refs)}.")

    for evidence in context_pack.evidence_chain:
        missing_fact_refs = [fact_ref for fact_ref in evidence.fact_refs if fact_ref not in fact_ids]
        if missing_fact_refs:
            issues.append(f"Evidence {evidence.evidence_id} references missing facts: {', '.join(missing_fact_refs)}.")

        missing_rule_refs = [
            rule_ref for rule_ref in evidence.rule_refs if not _is_known_rule_ref(rule_ref, regulation_ids)
        ]
        if missing_rule_refs:
            issues.append(f"Evidence {evidence.evidence_id} references missing rules: {', '.join(missing_rule_refs)}.")

        missing_issue_refs = [
            used_ref for used_ref in evidence.used_by if used_ref.startswith("ISSUE-") and used_ref not in issue_ids
        ]
        if missing_issue_refs:
            issues.append(f"Evidence {evidence.evidence_id} is used by missing issues: {', '.join(missing_issue_refs)}.")

    return issues


def check_report_against_context(report_content: str, context_pack: GenerationContextPack) -> list[str]:
    issues: list[str] = []

    for issue in context_pack.issues:
        if issue.severity in {"HIGH", "BLOCKER"} and issue.issue_id not in report_content and issue.title not in report_content:
            issues.append(f"Report does not mention HIGH/BLOCKER issue {issue.issue_id}: {issue.title}.")

    if any(issue.issue_id == "ISSUE-missing-attachments" for issue in context_pack.issues):
        if "材料齐备" in report_content or "材料完整齐备" in report_content:
            issues.append("Report says materials are complete while ISSUE-missing-attachments exists.")

    important_data_fact = next(
        (fact for fact in context_pack.facts if fact.field_path == "request.contains_important_data"),
        None,
    )
    if important_data_fact and str(important_data_fact.normalized_value).lower() == "unknown":
        if "确认不涉及重要数据" in report_content or "不涉及重要数据" in report_content:
            issues.append("Report denies important data while request.contains_important_data is unknown.")

    if context_pack.path_warning:
        has_path_explanation = any(
            marker in report_content
            for marker in ["路径", "不匹配", "强制生成", "参考草案", "force_override"]
        )
        if not has_path_explanation:
            issues.append("Report does not mention path warning or forced-generation context.")

    diagnosis = context_pack.diagnosis_result or {}
    if diagnosis.get("recommended_path") and diagnosis.get("recommended_path") != "security_assessment":
        has_forced_draft_statement = "强制生成" in report_content or "参考草案" in report_content
        if not has_forced_draft_statement:
            issues.append("Report does not state forced-generation/reference-draft status for non-assessment path.")

    return issues


# ---------------------------------------------------------------------------
# Batch 3: expression integrity checks
# ---------------------------------------------------------------------------


def _collect_forbidden_expressions(context_pack: GenerationContextPack) -> list[str]:
    ws = context_pack.writing_strategy or {}
    global_forbidden: list[str] = list(ws.get("global_forbidden_expressions", []))
    issue_forbidden: list[str] = []
    for strategy in ws.get("strategies", []):
        if isinstance(strategy, dict):
            issue_forbidden.extend(strategy.get("forbidden_expressions", []))
    return sorted(set(global_forbidden + issue_forbidden))


def check_forbidden_expressions(report_content: str, context_pack: GenerationContextPack) -> list[str]:
    """Detect forbidden expressions in the external report."""
    issues: list[str] = []
    forbidden = _collect_forbidden_expressions(context_pack)
    for expr in forbidden:
        if expr in report_content:
            issues.append(f"Forbidden expression in external report: '{expr}'.")
    return issues


def check_internal_expression_leakage(report_content: str, context_pack: GenerationContextPack) -> list[str]:
    """Check that internal_expression content does not leak into the external report."""
    issues: list[str] = []
    ws = context_pack.writing_strategy or {}
    for strategy in ws.get("strategies", []):
        if not isinstance(strategy, dict):
            continue
        internal = strategy.get("internal_expression", "")
        # Check if a meaningful fragment of internal_expression appears in report
        # Skip short fragments (< 15 chars) to avoid false positives
        for sentence in internal.replace("；", "。").split("。"):
            sentence = sentence.strip()
            if len(sentence) >= 15 and sentence in report_content:
                issues.append(
                    f"Internal expression leaked into external report for {strategy.get('issue_id', '?')}: "
                    f"'{sentence[:60]}...'"
                )
    return issues


def check_user_claim_positive_statement(report_content: str, context_pack: GenerationContextPack) -> list[str]:
    """Check that user_claim_only facts are not used as sole basis for positive conclusions."""
    issues: list[str] = []
    positive_markers = ["已充分证明", "完全合规", "材料齐备", "无风险", "必然合法", "确认不涉及", "充分保障"]

    user_claim_facts = [
        fact for fact in context_pack.facts
        if fact.evidence_status == "user_claim_only"
    ]

    for fact in user_claim_facts:
        fact_value = str(fact.normalized_value or fact.value or "")
        if not fact_value or len(fact_value) < 5:
            continue
        for marker in positive_markers:
            if marker in report_content and fact_value[:20] in report_content:
                # Only flag if both the fact value and a positive marker appear near each other
                idx_value = report_content.find(fact_value[:20])
                idx_marker = report_content.find(marker)
                if abs(idx_value - idx_marker) < 500:
                    issues.append(
                        f"Positive claim '{marker}' may be based on user_claim_only fact "
                        f"{fact.fact_id} (evidence_status=user_claim_only)."
                    )
                    break

    return issues


def check_case_references_in_external_report(
    report_content: str, context_pack: GenerationContextPack
) -> list[str]:
    """Detect case references that should not appear in external reports.

    Checks both CitationItem markers and case_grounding titles for leakage.
    """
    issues: list[str] = []

    # Check CitationRegistry for case items
    registry = getattr(context_pack, "citation_registry", None)
    if registry is not None:
        for item in registry:
            if not item.can_enter_external_report:
                # Check if citation marker appears in report
                if item.citation_id in report_content:
                    issues.append(
                        f"Case reference '{item.title}' ({item.citation_id}) "
                        f"leaked into external report — cases must not appear in external reports."
                    )
                # Check if case title appears in report (fuzzy)
                if item.title and len(item.title) >= 8 and item.title in report_content:
                    issues.append(
                        f"Case reference title '{item.title}' appears in external report "
                        f"— cases must not appear in external reports."
                    )

    # Check case_grounding titles for leakage
    case_grounding = getattr(context_pack, "case_grounding", None) or {}
    for issue_id, bindings in case_grounding.get("by_issue", {}).items():
        for binding in bindings:
            case_title = str(binding.get("title", ""))
            if case_title and len(case_title) >= 8 and case_title in report_content:
                issues.append(
                    f"Case reference '{case_title}' from case_grounding {issue_id} "
                    f"appears in external report — cases must not appear in external reports."
                )

    return issues


class ConsistencyChecker:
    def check(self, profile: CompanyProfile, chapters: list[ChapterContent]) -> list[str]:
        issues: list[str] = []
        if not chapters:
            return ["No chapters generated."]

        for chapter in chapters:
            if not chapter.citations:
                issues.append(f"Chapter {chapter.chapter_no} has no citation.")

        high_risk = profile.is_ciio or profile.contains_important_data or profile.pii_count >= 1_000_000
        if high_risk and chapters[-1].risk_level != "HIGH":
            issues.append("Final chapter risk level should be HIGH under mandatory security-assessment conditions.")

        return issues

    def check_with_context(
        self,
        profile: CompanyProfile,
        chapters: list[ChapterContent],
        context_pack: GenerationContextPack,
    ) -> list[str]:
        report_content = "\n".join(chapter.content for chapter in chapters)
        return [
            *self.check(profile, chapters),
            *check_context_pack_consistency(context_pack),
            *check_report_against_context(report_content, context_pack),
            *check_forbidden_expressions(report_content, context_pack),
            *check_internal_expression_leakage(report_content, context_pack),
            *check_user_claim_positive_statement(report_content, context_pack),
            *check_case_references_in_external_report(report_content, context_pack),
        ]
