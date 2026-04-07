from uuid import uuid4

from backend.schemas.review import ClassifiedClause, ReviewIssue, ReviewSeverity
from backend.services.review_service.rag_provider import LocalRegulationKnowledgeBase


class ClauseReviewer:
    def __init__(self, knowledge_base: LocalRegulationKnowledgeBase) -> None:
        self.knowledge_base = knowledge_base

    def review(self, clause: ClassifiedClause) -> list[ReviewIssue]:
        config = self.knowledge_base.lookup(clause.clause_type, clause.text)
        issues: list[ReviewIssue] = []
        text = clause.text

        for group in config.get("required_groups", []):
            if not any(keyword in text for keyword in group):
                missing_label = "/".join(group)
                severity = self._severity_for(clause.clause_type)
                issues.append(
                    ReviewIssue(
                        issue_id=str(uuid4()),
                        clause_id=clause.clause_id,
                        file_id=clause.file_id,
                        clause_type=clause.clause_type,
                        severity=severity,
                        title=f"缺少关键信息：{missing_label}",
                        problem_type="MISSING_REQUIREMENT",
                        risk_analysis=f"当前条款未清晰体现“{missing_label}”，可能导致该类合规义务表达不完整。",
                        original_excerpt=text[:240],
                        citation_sources=config.get("citations", []),
                        recommendation=f"建议补充与“{missing_label}”相关的明确约定，并结合实际业务补全责任边界与操作路径。",
                        position=clause.position,
                    )
                )

        if "尽最大努力" in text or "必要时" in text:
            issues.append(
                ReviewIssue(
                    issue_id=str(uuid4()),
                    clause_id=clause.clause_id,
                    file_id=clause.file_id,
                    clause_type=clause.clause_type,
                    severity=ReviewSeverity.LOW,
                    title="表述存在模糊空间",
                    problem_type="AMBIGUOUS_LANGUAGE",
                    risk_analysis="条款包含较模糊的义务表述，执行和追责口径可能不够清晰。",
                    original_excerpt=text[:240],
                    citation_sources=config.get("citations", []),
                    recommendation="建议将模糊性表述改为可验证、可执行的具体义务或时间要求。",
                    position=clause.position,
                )
            )

        return issues

    def _severity_for(self, clause_type):
        if clause_type.value in {"CONSENT_NOTICE", "CROSS_BORDER_TRANSFER"}:
            return ReviewSeverity.HIGH
        if clause_type.value in {"SECURITY_MEASURES", "RIGHTS_REQUEST"}:
            return ReviewSeverity.MEDIUM
        return ReviewSeverity.LOW
