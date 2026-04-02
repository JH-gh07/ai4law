from collections import defaultdict

from backend.schemas.review import (
    Clause,
    ContractType,
    RevisionAction,
    RevisionInstruction,
    ReviewIssue,
    ReviewSeverity,
    SectionType,
)


class ClauseRevisionPlanner:
    def plan(
        self,
        clauses: list[Clause],
        issues: list[ReviewIssue],
        contract_type: ContractType,
    ) -> list[RevisionInstruction]:
        issues_by_clause: dict[str, list[ReviewIssue]] = defaultdict(list)
        for issue in issues:
            issues_by_clause[issue.clause_id].append(issue)

        instructions: list[RevisionInstruction] = []
        has_appendix = any(clause.section_type == SectionType.APPENDIX for clause in clauses)

        for clause in clauses:
            clause_issues = issues_by_clause.get(clause.clause_id, [])
            if not clause_issues:
                instructions.append(
                    RevisionInstruction(
                        clause_id=clause.clause_id,
                        action=RevisionAction.RETAIN,
                        reason="当前条款未触发明显问题，保留原结构。",
                        target_section_type=clause.section_type,
                        appendix_id=clause.appendix_id,
                    )
                )
                continue

            high_count = sum(1 for issue in clause_issues if issue.severity == ReviewSeverity.HIGH)
            action = RevisionAction.REWRITE if high_count else RevisionAction.MODIFY
            instructions.append(
                RevisionInstruction(
                    clause_id=clause.clause_id,
                    action=action,
                    reason="根据条款级问题清单，需要补强合规表述并保留原合同主体结构。",
                    issue_ids=[issue.issue_id for issue in clause_issues],
                    target_section_type=clause.section_type,
                    appendix_id=clause.appendix_id,
                )
            )

        if contract_type == ContractType.PERSONAL_INFO_SCC and not has_appendix:
            instructions.append(
                RevisionInstruction(
                    clause_id="APPENDIX_TEMPLATE",
                    action=RevisionAction.APPEND_APPENDIX,
                    reason="标准合同场景通常需要补充附录或个人信息清单。",
                    target_section_type=SectionType.APPENDIX,
                    appendix_id="附件A",
                )
            )

        return instructions
