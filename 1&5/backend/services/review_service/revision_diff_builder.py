from backend.schemas.review import Clause, RevisedClause, RevisionAction, RevisionDiffItem, ReviewIssue


class RevisionDiffBuilder:
    def build(self, clauses: list[Clause], revised_clauses: list[RevisedClause], issues: list[ReviewIssue]) -> list[RevisionDiffItem]:
        severity_map = {issue.clause_id: issue.severity for issue in issues}
        original_map = {clause.clause_id: clause for clause in clauses}
        diffs: list[RevisionDiffItem] = []

        for revised in revised_clauses:
            original = original_map.get(revised.clause_id)
            if original and original.text == revised.revised_text and revised.action == RevisionAction.RETAIN:
                continue
            diffs.append(
                RevisionDiffItem(
                    clause_id=revised.clause_id,
                    heading=revised.heading,
                    original_text=original.text if original else "",
                    revised_text=revised.revised_text,
                    reason=revised.revision_reason,
                    severity=severity_map.get(revised.clause_id),
                    action=revised.action,
                )
            )

        return diffs
