from uuid import uuid4

from backend.schemas.review import (
    ClassifiedClause,
    ContractType,
    CustomRuleInput,
    ReviewIssue,
    ReviewSeverity,
    ReviewStance,
)
from backend.services.review_service.rag_provider import LocalRegulationKnowledgeBase


class ClauseReviewer:
    ambiguous_terms = ("必要时", "尽最大努力", "合理范围内", "及时")

    def __init__(self, knowledge_base: LocalRegulationKnowledgeBase) -> None:
        self.knowledge_base = knowledge_base

    def review(
        self,
        clause: ClassifiedClause,
        contract_type: ContractType,
        review_stance: ReviewStance,
        custom_rules: CustomRuleInput,
    ) -> list[ReviewIssue]:
        config = self.knowledge_base.lookup(
            clause.clause_type,
            clause.text,
            contract_type=contract_type,
            review_stance=review_stance,
        )
        issues: list[ReviewIssue] = []
        text = clause.text

        for group in config.get("required_groups", []):
            if not any(keyword in text for keyword in group):
                label = "/".join(group)
                severity = self._severity_for(clause.clause_type)
                issues.append(
                    ReviewIssue(
                        issue_id=str(uuid4()),
                        clause_id=clause.clause_id,
                        file_id=clause.file_id,
                        clause_type=clause.clause_type,
                        severity=severity,
                        title=f"缺少关键要素：{label}",
                        problem_type="MISSING_REQUIREMENT",
                        risk_analysis=f"当前条款未清晰体现“{label}”，可能导致义务边界和监管要求表达不完整。",
                        original_excerpt=text[:300],
                        citation_sources=config.get("citations", []),
                        recommendation=f"建议补充与“{label}”相关的明确约定，并结合实际业务写明责任主体、处理范围和执行路径。",
                        stance_relevance=config.get("stance_focus", ""),
                        suggested_revision=f"建议新增对“{label}”的明确描述。",
                        position=clause.position,
                    )
                )

        if any(term in text for term in self.ambiguous_terms):
            issues.append(
                ReviewIssue(
                    issue_id=str(uuid4()),
                    clause_id=clause.clause_id,
                    file_id=clause.file_id,
                    clause_type=clause.clause_type,
                    severity=ReviewSeverity.LOW,
                    title="条款存在模糊表述",
                    problem_type="AMBIGUOUS_LANGUAGE",
                    risk_analysis="条款含有较模糊的义务措辞，执行标准和追责口径可能不清晰。",
                    original_excerpt=text[:300],
                    citation_sources=config.get("citations", []),
                    recommendation="建议改写为可验证、可执行、带有对象和时限的具体义务表达。",
                    stance_relevance=config.get("stance_focus", ""),
                    suggested_revision="将模糊词语替换为明确的操作要求和时间要求。",
                    position=clause.position,
                )
            )

        issues.extend(self._review_stance_specific(clause, review_stance, config.get("citations", [])))
        issues.extend(self._review_contract_specific(clause, contract_type, config.get("citations", [])))

        if custom_rules.text and clause.position.paragraph == 1:
            issues.append(
                ReviewIssue(
                    issue_id=str(uuid4()),
                    clause_id=clause.clause_id,
                    file_id=clause.file_id,
                    clause_type=clause.clause_type,
                    severity=ReviewSeverity.MEDIUM,
                    title="已纳入自定义审查关注点",
                    problem_type="CUSTOM_RULE_FOCUS",
                    risk_analysis=f"本次审查额外纳入自定义规则：{custom_rules.text}",
                    original_excerpt=text[:200],
                    citation_sources=config.get("citations", []),
                    recommendation=f"请结合自定义规则进一步核对：{custom_rules.text}",
                    stance_relevance="来自用户自定义规则输入。",
                    suggested_revision=f"建议在合同中补强与以下关注点有关的条款：{custom_rules.text}",
                    position=clause.position,
                )
            )

        return issues

    def _review_stance_specific(
        self,
        clause: ClassifiedClause,
        review_stance: ReviewStance,
        citations: list[str],
    ) -> list[ReviewIssue]:
        text = clause.text
        issues: list[ReviewIssue] = []
        if review_stance == ReviewStance.PARTY_B and ("乙方承担全部责任" in text or "乙方应赔偿全部损失" in text):
            issues.append(
                ReviewIssue(
                    issue_id=str(uuid4()),
                    clause_id=clause.clause_id,
                    file_id=clause.file_id,
                    clause_type=clause.clause_type,
                    severity=ReviewSeverity.HIGH,
                    title="乙方责任明显过重",
                    problem_type="STANCE_IMBALANCE",
                    risk_analysis="当前条款显著偏向甲方，可能导致乙方承担失衡或无限化责任。",
                    original_excerpt=text[:300],
                    citation_sources=citations,
                    recommendation="建议将责任限定为与违约行为、过错程度和可预见损失相匹配，并加入责任上限或例外条款。",
                    stance_relevance="乙方视角重点关注责任失衡。",
                    suggested_revision="将“乙方承担全部责任”修改为与违约行为和可预见损失相匹配的责任条款。",
                    position=clause.position,
                )
            )
        if review_stance == ReviewStance.PARTY_A and "甲方不得审计" in text:
            issues.append(
                ReviewIssue(
                    issue_id=str(uuid4()),
                    clause_id=clause.clause_id,
                    file_id=clause.file_id,
                    clause_type=clause.clause_type,
                    severity=ReviewSeverity.MEDIUM,
                    title="甲方控制权不足",
                    problem_type="STANCE_IMBALANCE",
                    risk_analysis="条款限制了甲方的监督或审计权，不利于甲方持续履行合规管理义务。",
                    original_excerpt=text[:300],
                    citation_sources=citations,
                    recommendation="建议补充甲方的监督、审计、整改通知和暂停处理权利。",
                    stance_relevance="甲方视角重点关注控制权和追偿权。",
                    suggested_revision="增加甲方有权开展合规审计和要求整改的条款。",
                    position=clause.position,
                )
            )
        return issues

    def _review_contract_specific(
        self,
        clause: ClassifiedClause,
        contract_type: ContractType,
        citations: list[str],
    ) -> list[ReviewIssue]:
        text = clause.text
        issues: list[ReviewIssue] = []
        if contract_type == ContractType.PERSONAL_INFO_SCC and clause.clause_type.name == "CROSS_BORDER_TRANSFER":
            if "标准合同" not in text and "备案" not in text:
                issues.append(
                    ReviewIssue(
                        issue_id=str(uuid4()),
                        clause_id=clause.clause_id,
                        file_id=clause.file_id,
                        clause_type=clause.clause_type,
                        severity=ReviewSeverity.HIGH,
                        title="未体现标准合同备案配套义务",
                        problem_type="FILING_GAP",
                        risk_analysis="针对个人信息出境标准合同场景，条款中未体现备案、影响评估或配套履约安排。",
                        original_excerpt=text[:300],
                        citation_sources=citations,
                        recommendation="建议补充标准合同备案、个人信息保护影响评估和监管配合义务。",
                        stance_relevance="与标准合同场景直接相关。",
                        suggested_revision="增加标准合同备案、影响评估和监管配合的专门条款。",
                        position=clause.position,
                    )
                )
        return issues

    def _severity_for(self, clause_type) -> ReviewSeverity:
        if clause_type.value in {"CONSENT_NOTICE", "CROSS_BORDER_TRANSFER", "PIA_FILING"}:
            return ReviewSeverity.HIGH
        if clause_type.value in {"SECURITY_MEASURES", "RIGHTS_REQUEST", "THIRD_PARTY_SHARING", "LIABILITY"}:
            return ReviewSeverity.MEDIUM
        return ReviewSeverity.LOW
