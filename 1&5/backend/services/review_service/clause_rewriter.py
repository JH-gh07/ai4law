from collections import defaultdict

from backend.schemas.review import Clause, RevisedClause, RevisionAction, RevisionInstruction, ReviewIssue, SectionType


class ClauseRewriter:
    def rewrite(
        self,
        clauses: list[Clause],
        instructions: list[RevisionInstruction],
        issues: list[ReviewIssue],
    ) -> list[RevisedClause]:
        issues_by_clause: dict[str, list[ReviewIssue]] = defaultdict(list)
        for issue in issues:
            issues_by_clause[issue.clause_id].append(issue)

        clause_map = {clause.clause_id: clause for clause in clauses}
        revised: list[RevisedClause] = []

        for instruction in instructions:
            if instruction.action == RevisionAction.APPEND_APPENDIX:
                revised.append(
                    RevisedClause(
                        clause_id=instruction.clause_id,
                        heading=instruction.appendix_id or "附件A",
                        revised_text="附件A 个人信息出境配套清单\n1. 处理目的与范围。\n2. 境外接收方信息与联系方式。\n3. 安全措施与个人权利行使路径。\n4. 标准合同备案与影响评估配套安排。",
                        revision_reason=instruction.reason,
                        action=instruction.action,
                        section_type=SectionType.APPENDIX,
                        appendix_id=instruction.appendix_id,
                    )
                )
                continue

            original = clause_map[instruction.clause_id]
            clause_issues = issues_by_clause.get(original.clause_id, [])
            revised_text = original.text

            if instruction.action in {RevisionAction.MODIFY, RevisionAction.REWRITE}:
                revised_text = self._normalize_ambiguous_terms(revised_text)
                supplements = [issue.suggested_revision or issue.recommendation for issue in clause_issues]
                supplement_text = "\n".join(f"补充建议：{item}" for item in supplements if item)
                if supplement_text:
                    revised_text = f"{revised_text}\n{supplement_text}"

            revised.append(
                RevisedClause(
                    clause_id=original.clause_id,
                    heading=original.heading,
                    revised_text=revised_text,
                    revision_reason=instruction.reason,
                    action=instruction.action,
                    section_type=original.section_type,
                    appendix_id=original.appendix_id,
                )
            )

        return revised

    def _normalize_ambiguous_terms(self, text: str) -> str:
        replacements = {
            "必要时": "在满足明确触发条件时",
            "尽最大努力": "采取可验证的合理措施",
            "合理范围内": "在合同约定且可审计的范围内",
            "及时": "在五个工作日内",
        }
        normalized = text
        for source, target in replacements.items():
            normalized = normalized.replace(source, target)
        return normalized
