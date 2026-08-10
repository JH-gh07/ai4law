"""DPIA evidence builder — links DPIA issues to facts and regulations as EvidenceItems."""

from __future__ import annotations

import re
from typing import Any

from backend.common.workflow import (
    DocumentRef,
    EvidenceItem,
    FactItem,
    IssueItem,
    build_citation_bindings,
)


_EVIDENCE_WORDING: dict[str, tuple[str, str]] = {
    "DPIA-ISSUE-automated-decision": (
        "自动化决策或画像处理可能对数据主体产生法律效力或类似重大影响",
        "该项目涉及自动化决策/画像，应落实 GDPR Art 22 要求，确保人工干预、表达观点和质疑决策的权利。",
    ),
    "DPIA-ISSUE-profiling-risk": (
        "项目目标涉及评估、评分或画像处理",
        "画像处理可能对数据主体产生重大影响，需补充画像逻辑说明和异议处理机制。",
    ),
    "DPIA-ISSUE-special-category": (
        "处理特殊类别个人数据属于高风险处理",
        "特殊类别数据需满足 GDPR Art 9 豁免条件，并应补充保护措施和必要性论证。",
    ),
    "DPIA-ISSUE-large-scale": (
        "大规模处理个人数据属于 WP248 高风险标准",
        "大规模处理触发严格的数据最小化和定期审查要求，需补充统计口径和管控措施。",
    ),
    "DPIA-ISSUE-systematic-monitoring": (
        "公共区域系统性监控属于 WP248 明确列举的高风险活动",
        "应补充监控的合法性基础、数据保留期限和透明度措施。",
    ),
    "DPIA-ISSUE-data-matching": (
        "多源数据匹配可能超出原始收集目的",
        "需进行目的兼容性分析并评估重识别风险。",
    ),
    "DPIA-ISSUE-new-technology": (
        "使用新技术处理方式需评估对个人数据保护的影响",
        "应补充新技术技术说明和隐私风险评估。",
    ),
    "DPIA-ISSUE-vulnerable-subjects": (
        "弱势数据主体面临权力不对等风险",
        "应补充弱势群体保护措施和额外保障机制。",
    ),
    "DPIA-ISSUE-necessity-weak": (
        "处理必要性论证不充分",
        "当前必要性陈述过短，应补充详细论证说明为何必须处理该数据及为何无法以侵入性更低的方式实现目的。",
    ),
    "DPIA-ISSUE-proportionality-weak": (
        "相称性分析不充分",
        "当前相称性陈述过短，应论证处理范围、频率和存储期限与处理目的相称。",
    ),
    "DPIA-ISSUE-lawful-basis-unclear": (
        "处理合法性基础不明确",
        "应明确列示所依赖的 GDPR Art 6(1) 合法性基础。",
    ),
    "DPIA-ISSUE-consent-not-free": (
        "在雇佣/保险等不对等关系中的同意可能非自由给予",
        "应评估同意的自由性，考虑是否应依赖其他合法性基础替代同意。",
    ),
    "DPIA-ISSUE-transparency-gap": (
        "透明度信息不足以满足 GDPR Art 13/14 告知要求",
        "应补充数据主体告知内容，包括处理目的、法律依据、接收方、保留期限和权利。",
    ),
    "DPIA-ISSUE-discrimination-risk": (
        "自动化决策叠加特殊类别数据可能导致歧视",
        "应补充反歧视保障措施、算法公平性审计和定期偏差检测。",
    ),
    "DPIA-ISSUE-cross-border-risk": (
        "接收方国家/地区缺乏充分性认定",
        "应补充传输保障措施（SCCs/BCRs/行为准则等）并评估接收方数据保护水平。",
    ),
    "DPIA-ISSUE-mitigation-insufficient": (
        "风险缓解措施未完全覆盖已识别风险",
        "应逐项核查每个已识别风险是否有对应缓解措施，补充缺失项。",
    ),
    "DPIA-ISSUE-prior-consultation-needed": (
        "剩余高风险可能需要监管机构事先咨询",
        "应评估剩余风险可接受性。如不可接受，准备事先咨询材料。",
    ),
    "DPIA-ISSUE-dpo-opinion-missing": (
        "DPO 审查意见缺失",
        "应请 DPO 审查 DPIA 草案并出具书面意见。",
    ),
}


def _evidence_id(issue_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9]+", "-", issue_id.removeprefix("DPIA-ISSUE-")).strip("-")
    return f"DPIA-EVIDENCE-{safe}"


def _regulation_rule_refs(regulations: list[Any]) -> list[str]:
    return [getattr(r, "source_id", str(r)) for r in regulations if getattr(r, "source_id", None)]


def _confidence(severity: str, has_rule_refs: bool) -> float:
    if severity in {"HIGH", "BLOCKER"} and has_rule_refs:
        return 0.9
    if severity in {"HIGH", "BLOCKER"}:
        return 0.8
    if severity == "MEDIUM":
        return 0.75
    return 0.6


def _extract_document_refs(
    fact_refs: list[str],
    facts: list[FactItem],
) -> list[DocumentRef]:
    """Extract DocumentRef entries from facts that carry supporting material refs."""
    fact_map = {f.fact_id: f for f in facts}
    refs: list[DocumentRef] = []
    for fact_id in fact_refs:
        fact = fact_map.get(fact_id)
        if fact is None:
            continue
        material_refs = getattr(fact, "supporting_material_refs", None)
        if material_refs:
            for ref in material_refs:
                if isinstance(ref, dict):
                    refs.append(DocumentRef(**ref))
                elif isinstance(ref, DocumentRef):
                    refs.append(ref)
                elif hasattr(ref, "file_name"):
                    refs.append(
                        DocumentRef(
                            file_name=getattr(ref, "file_name", ""),
                            page=getattr(ref, "page", 1),
                            quote=getattr(ref, "quote", ""),
                        )
                    )
    return refs


def build_dpia_evidence(
    facts: list[FactItem],
    issues: list[IssueItem],
    regulations: list[Any],
    diagnosis_result: object | None = None,
) -> tuple[list[IssueItem], list[EvidenceItem]]:
    """Build evidence chain linking DPIA issues to facts and GDPR regulatory basis."""
    fact_ids = {fact.fact_id for fact in facts}
    evidence_chain: list[EvidenceItem] = []
    updated_issues: list[IssueItem] = []

    for issue in issues:
        fact_refs = [ref for ref in issue.fact_refs if ref in fact_ids]
        if not fact_refs:
            updated_issues.append(issue)
            continue

        evidence_id = _evidence_id(issue.issue_id)
        claim, conclusion = _EVIDENCE_WORDING.get(
            issue.issue_id,
            (issue.title, issue.recommended_action),
        )
        rule_refs = list(issue.rule_refs) if issue.rule_refs else _regulation_rule_refs(regulations)[:3]
        evidence = EvidenceItem(
            evidence_id=evidence_id,
            claim=claim,
            fact_refs=fact_refs,
            rule_refs=rule_refs,
            conclusion=conclusion,
            confidence=_confidence(issue.severity, bool(rule_refs)),
            used_by=[issue.issue_id, *issue.affects_outputs],
            legal_basis=build_citation_bindings(regulations),
            document_refs=_extract_document_refs(fact_refs, facts),
            rag_query_used=f"dpia:{issue.issue_id}",
            rag_hits_count=len(regulations),
        )
        evidence_chain.append(evidence)
        updated_issues.append(issue.model_copy(update={"evidence_refs": [evidence_id]}))

    return updated_issues, evidence_chain
