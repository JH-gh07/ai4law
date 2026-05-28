from backend.common.workflow import GenerationContextPack
from backend.modules.assessment.schema import ChapterContent, CompanyProfile


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
        ]
