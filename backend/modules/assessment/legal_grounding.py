from __future__ import annotations

import re
from typing import Any, Literal

from backend.common.workflow import FactItem, IssueItem
from backend.modules.assessment.schema import RegulationHit

SourceKind = Literal[
    "law_article",
    "regulation",
    "official_guide",
    "template_requirement",
    "standard_clause",
    "case_reference",
    "user_material",
]

# Usage policy per source kind
_SOURCE_USAGE_POLICY: dict[SourceKind, dict[str, Any]] = {
    "law_article": {
        "allowed_usage": ["external_report", "internal_review", "risk_explanation"],
        "can_enter_external_report": True,
    },
    "regulation": {
        "allowed_usage": ["external_report", "internal_review", "risk_explanation"],
        "can_enter_external_report": True,
    },
    "official_guide": {
        "allowed_usage": ["external_report", "internal_review", "risk_explanation"],
        "can_enter_external_report": True,
    },
    "template_requirement": {
        "allowed_usage": ["external_report", "internal_review", "risk_explanation"],
        "can_enter_external_report": True,
    },
    "standard_clause": {
        "allowed_usage": ["external_report", "internal_review", "risk_explanation"],
        "can_enter_external_report": True,
    },
    "case_reference": {
        "allowed_usage": ["internal_review", "risk_explanation"],
        "can_enter_external_report": False,
    },
    "user_material": {
        "allowed_usage": ["external_report", "internal_review"],
        "can_enter_external_report": True,
    },
}


def _infer_source_kind(title: str) -> SourceKind:
    """Infer source_kind from regulation title text."""
    t = (title or "").replace("《", "").replace("》", "")
    if any(kw in t for kw in ("指南", "指引")):
        return "official_guide"
    if any(kw in t for kw in ("标准", "规范")):
        return "standard_clause"
    if any(kw in t for kw in ("模板", "示范")):
        return "template_requirement"
    if any(kw in t for kw in ("法", "办法", "条例", "规定", "细则")):
        return "law_article"
    if any(kw in t for kw in ("案例", "判例", "裁定", "判决")):
        return "case_reference"
    return "regulation"


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


def _annotate_binding(binding: dict[str, Any], source_kind: SourceKind) -> dict[str, Any]:
    """Annotate a binding dict with source_kind, allowed_usage, and can_enter_external_report."""
    policy = _SOURCE_USAGE_POLICY.get(source_kind, _SOURCE_USAGE_POLICY["regulation"])
    binding["source_kind"] = source_kind
    binding["allowed_usage"] = policy["allowed_usage"]
    binding["can_enter_external_report"] = policy["can_enter_external_report"]
    return binding


def build_legal_grounding(
    *,
    issues: list[IssueItem],
    facts: list[FactItem],
    regulations: list[RegulationHit],
    source_version: str = "local-regulation-index-v2",
    per_issue_rag: dict[str, dict] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build legal grounding and case grounding for assessment issues.

    Returns:
        (legal_grounding, case_grounding) tuple.
        legal_grounding contains only law/regulation/guide/template/standard/user_material bindings
        (can_enter_external_report=True).
        case_grounding contains only case/penalty/judgment references
        (can_enter_external_report=False).
    """
    facts_by_id = {fact.fact_id: fact for fact in facts}
    by_issue_legal: dict[str, list[dict[str, Any]]] = {}
    by_issue_case: dict[str, list[dict[str, Any]]] = {}

    for issue in issues:
        query = _issue_query(issue, facts_by_id)
        legal_candidates: list[dict[str, Any]] = []
        case_candidates: list[dict[str, Any]] = []

        for regulation in regulations:
            confidence, reason = _score_regulation(issue, query, regulation)
            if confidence <= 0:
                continue
            source_kind = _infer_source_kind(regulation.title)
            binding = _annotate_binding(
                {
                    "issue_id": issue.issue_id,
                    "rule_id": regulation.source_id,
                    "title": regulation.title,
                    "article": regulation.article,
                    "confidence_score": round(confidence, 3),
                    "relevance_reason": reason,
                    "source_version": source_version,
                    "query_context": query,
                },
                source_kind,
            )
            legal_candidates.append(binding)

        # Merge per-issue DeliLegal results, splitting by source_kind
        if per_issue_rag and issue.issue_id in per_issue_rag:
            rag_result = per_issue_rag[issue.issue_id]
            for law in rag_result.get("laws", []):
                binding = _annotate_binding(
                    {
                        "issue_id": issue.issue_id,
                        "rule_id": f"delilegal-law-{law.get('title', 'unknown')}",
                        "title": law.get("title", "未知法规"),
                        "article": "",
                        "confidence_score": 0.85,
                        "relevance_reason": f"DeliLegal 法规检索：{law.get('summary', '')[:80]}",
                        "source_version": "delilegal-api",
                        "query_context": query,
                    },
                    "law_article",
                )
                legal_candidates.append(binding)
            for case in rag_result.get("cases", []):
                binding = _annotate_binding(
                    {
                        "issue_id": issue.issue_id,
                        "rule_id": f"delilegal-case-{case.get('title', 'unknown')}",
                        "title": case.get("title", "未命名案例"),
                        "article": "",
                        "confidence_score": 0.75,
                        "relevance_reason": f"DeliLegal 案例检索：{case.get('summary', '')[:80]}",
                        "source_version": "delilegal-api",
                        "query_context": query,
                    },
                    "case_reference",
                )
                case_candidates.append(binding)

        legal_candidates.sort(key=lambda item: item["confidence_score"], reverse=True)
        case_candidates.sort(key=lambda item: item["confidence_score"], reverse=True)
        by_issue_legal[issue.issue_id] = legal_candidates[:5]
        if case_candidates:
            by_issue_case[issue.issue_id] = case_candidates[:3]

    legal_grounding = {
        "grounding_version": "v3",
        "source_version": source_version,
        "by_issue": by_issue_legal,
    }
    case_grounding = {
        "grounding_version": "v3",
        "source_version": source_version,
        "by_issue": by_issue_case,
    }
    return legal_grounding, case_grounding
