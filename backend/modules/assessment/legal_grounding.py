from __future__ import annotations

import re
from typing import Any

from backend.common.workflow import FactItem, IssueItem
from backend.modules.assessment.schema import RegulationHit


_CATEGORY_HINTS: dict[str, tuple[str, ...]] = {
    "path": ("安全评估", "申报", "CIIO", "关键信息基础设施", "重要数据", "个人信息"),
    "data_scope": ("个人信息", "敏感个人信息", "重要数据", "数据项", "匿名化", "去标识化"),
    "consent": ("告知", "单独同意", "个人信息", "个人权利", "第三十九条"),
    "recipient": ("境外接收方", "安全保障能力", "管理措施", "技术措施", "所在国家"),
    "contract": ("法律文件", "合同", "再转移", "保存期限", "违约责任", "第九条"),
    "security_measure": ("加密", "访问控制", "应急处置", "安全措施", "审计"),
    "documentation": ("申报材料", "自评估报告", "附件", "证明材料"),
    "expression": ("风险", "整改", "材料", "结论", "审慎"),
}


def _tokens(value: str) -> set[str]:
    text = re.sub(r"[\s,，。；;：:（）()\[\]【】\"'“”]", " ", value or "").lower()
    return {token for token in text.split() if token}


def _fact_value(fact: FactItem | None) -> str:
    if fact is None:
        return ""
    value = fact.normalized_value if fact.normalized_value is not None else fact.value
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return str(value or "")


def _issue_query(issue: IssueItem, facts_by_id: dict[str, FactItem]) -> str:
    fact_text = " ".join(_fact_value(facts_by_id.get(ref)) for ref in issue.fact_refs)
    hints = " ".join(_CATEGORY_HINTS.get(issue.category, ()))
    return " ".join(
        [
            issue.title,
            issue.description,
            issue.recommended_action,
            issue.category,
            hints,
            fact_text,
        ]
    )


def _score_regulation(issue: IssueItem, query: str, regulation: RegulationHit) -> tuple[float, str]:
    source = f"{regulation.title} {regulation.article} {regulation.snippet}"
    score = 0.0
    reasons: list[str] = []

    if regulation.source_id in issue.rule_refs:
        score += 0.6
        reasons.append("issue.rule_refs 直接引用")

    query_tokens = _tokens(query)
    source_l = source.lower()
    overlap = [token for token in query_tokens if len(token) >= 2 and token in source_l]
    if overlap:
        score += min(len(overlap) * 0.04, 0.25)
        reasons.append(f"关键词重合：{', '.join(overlap[:5])}")

    for hint in _CATEGORY_HINTS.get(issue.category, ()):
        if hint.lower() in source_l:
            score += 0.05
            reasons.append(f"类别提示命中：{hint}")
            break

    if issue.severity in {"HIGH", "BLOCKER"}:
        score += 0.05

    return min(score, 0.98), "；".join(reasons) or "候选法规与问题文本弱相关"


def build_legal_grounding(
    *,
    issues: list[IssueItem],
    facts: list[FactItem],
    regulations: list[RegulationHit],
    source_version: str = "local-regulation-index-v2",
) -> dict[str, Any]:
    facts_by_id = {fact.fact_id: fact for fact in facts}
    by_issue: dict[str, list[dict[str, Any]]] = {}

    for issue in issues:
        query = _issue_query(issue, facts_by_id)
        candidates: list[dict[str, Any]] = []
        for regulation in regulations:
            confidence, reason = _score_regulation(issue, query, regulation)
            if confidence <= 0:
                continue
            candidates.append(
                {
                    "issue_id": issue.issue_id,
                    "rule_id": regulation.source_id,
                    "title": regulation.title,
                    "article": regulation.article,
                    "confidence_score": round(confidence, 3),
                    "relevance_reason": reason,
                    "source_version": source_version,
                    "query_context": query,
                }
            )
        candidates.sort(key=lambda item: item["confidence_score"], reverse=True)
        by_issue[issue.issue_id] = candidates[:3]

    return {
        "grounding_version": "v1",
        "source_version": source_version,
        "by_issue": by_issue,
    }
