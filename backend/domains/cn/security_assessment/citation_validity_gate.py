"""CN Security Assessment — Citation Validity 门（task073 T08）。

在 repair 之后、render 之前校验**最终章节**引用，输出
``CITATION_VALIDITY`` 门结果：

- C1 Existence：最终 marker / citation ID 必须能被 CitationRegistry 精确解析；
- C2 Eligibility：source_id 必须 exact 命中 SourceRegistry，且可引用 /
  可进入对外报告（fail-closed）；
- C3 Traceability：引用必须保留 issue / fact / evidence 关联。

只有核心（HIGH/BLOCKER）全部满足才 PASS；非核心 limitation → CONDITIONAL；
核心不满足 → ESCALATE（NEEDS_REVIEW）。``BLOCKED`` 保留契约，pilot 不主动触发。
本门为纯校验，不修改 registry 或章节内容。
"""
from __future__ import annotations

import re

from backend.common.citation.registry import CitationRegistry
from backend.common.citation.source_identity import SourceIdentityResolver
from backend.common.legal_control.contracts import (
    ACTION_HUMAN_REVIEW,
    ACTION_SUPPLEMENT_EVIDENCE,
    ACTION_VERIFY_SOURCE_IDENTITY,
    LegalControlGateResult,
)
from backend.common.workflow import GenerationContextPack
from backend.domains.cn.security_assessment.schema import ChapterContent

CORE_SEVERITIES = {"HIGH", "BLOCKER"}

# citation pipeline 在无法映射时写入的显式占位（postprocess.py）。
_PENDING_MARKERS = ("【待核验：引用无法映射】", "【待核验：引用格式不完整】")
_FOOTNOTE_RE = re.compile(r"\[(\d+)\]")
# 与 postprocess._resolve_numeric_footnotes 的脚注范围保持一致，
# 避免把正文中的 "[2023]" 之类普通括号数字误判为 dangling footnote。
_FOOTNOTE_RANGE = (1, 200)

# 硬治理失败（任何出现都按核心缺陷处理）。
_GOVERNANCE_DEFICIENCIES = {"unregistered_source", "ineligible_source"}


def _find_missing_markers(
    chapters: list[ChapterContent],
    registry: CitationRegistry | None,
) -> list[str]:
    """C1 — 精确解析最终 marker，返回无法解析的 marker 列表。"""
    missing: list[str] = []
    footnote_map = registry.get_footnote_map() if registry is not None else {}
    valid_numbers = set(footnote_map)
    has_citations = registry is not None and len(registry) > 0

    for chapter in chapters:
        text = getattr(chapter, "content", "") or ""
        for marker in _PENDING_MARKERS:
            if marker in text:
                missing.append(marker)
        if has_citations:
            for match in _FOOTNOTE_RE.finditer(text):
                number = int(match.group(1))
                if (
                    _FOOTNOTE_RANGE[0] <= number <= _FOOTNOTE_RANGE[1]
                    and number not in valid_numbers
                ):
                    missing.append(f"[{number}]")
    return sorted(set(missing))


def _evaluate_citation(
    citation,
    resolver: SourceIdentityResolver,
    *,
    issue_ids: set[str],
    fact_ids: set[str],
    evidence_ids: set[str],
    core_issue_ids: set[str],
) -> dict:
    identity = resolver.resolve(citation.source_id)
    traceable = (
        any(iid in issue_ids for iid in citation.related_issue_ids)
        or any(fid in fact_ids for fid in citation.related_fact_ids)
        or any(eid in evidence_ids for eid in citation.related_evidence_ids)
    )
    is_core = bool(set(citation.related_issue_ids) & core_issue_ids)

    deficiencies: list[str] = []
    status = "SUPPORTED"

    if identity.status == "UNREGISTERED":
        deficiencies.append("unregistered_source")
        status = "UNREGISTERED"
    elif identity.status == "INELIGIBLE":
        deficiencies.append("ineligible_source")
        status = "INELIGIBLE"

    if not traceable:
        deficiencies.append("untraceable")
        if status == "SUPPORTED":
            status = "UNTRAACEABLE"

    if identity.status == "REGISTERED" and not identity.can_enter_external_report:
        deficiencies.append("not_external_citable")
        if status == "SUPPORTED":
            status = "LIMITED"

    return {
        "citation_id": citation.citation_id,
        "source_id": citation.source_id,
        "registry_source_id": identity.registry_source_id,
        "identity_status": identity.status,
        "traceable": traceable,
        "is_core": is_core,
        "status": status,
        "deficiencies": deficiencies,
    }


def run_citation_validity_gate(
    *,
    chapters: list[ChapterContent],
    context_pack: GenerationContextPack,
    source_identity_resolver: SourceIdentityResolver | None = None,
) -> LegalControlGateResult:
    """C1/C2/C3 校验最终章节引用，输出 CITATION_VALIDITY 门结果。"""
    registry = context_pack.citation_registry
    issues = list(context_pack.issues)
    facts = list(context_pack.facts)
    evidence_chain = list(context_pack.evidence_chain)

    issue_ids = {issue.issue_id for issue in issues}
    fact_ids = {fact.fact_id for fact in facts}
    evidence_ids = {evidence.evidence_id for evidence in evidence_chain}
    core_issue_ids = {issue.issue_id for issue in issues if issue.severity in CORE_SEVERITIES}

    resolver = source_identity_resolver or SourceIdentityResolver()

    missing_markers = _find_missing_markers(chapters, registry)
    citation_entries = [
        _evaluate_citation(
            citation,
            resolver,
            issue_ids=issue_ids,
            fact_ids=fact_ids,
            evidence_ids=evidence_ids,
            core_issue_ids=core_issue_ids,
        )
        for citation in (registry if registry is not None else [])
    ]

    core_deficiencies: list[str] = []
    limitations: list[str] = []
    limitation_details: list[dict] = []

    if missing_markers:
        core_deficiencies.append(
            "存在无法解析的最终引用 marker：" + "、".join(missing_markers) + "。"
        )
        limitation_details.append(
            {"type": "C1_MISSING_MARKER", "markers": missing_markers}
        )

    if core_issue_ids and not citation_entries:
        core_deficiencies.append("核心 Issue 存在，但未生成任何可引用依据。")

    for entry in citation_entries:
        entry_deficiencies = entry["deficiencies"]
        for deficiency in entry_deficiencies:
            message = (
                f"引用 {entry['citation_id']}（{entry['source_id']}）：{deficiency}。"
            )
            if deficiency in _GOVERNANCE_DEFICIENCIES:
                core_deficiencies.append(message)
            elif deficiency == "untraceable":
                # 无法追溯的引用在存在核心 Issue 时按核心缺陷保守处理，
                # 因为无法证明它不支撑核心 Claim。
                if core_issue_ids:
                    core_deficiencies.append(message)
                else:
                    limitations.append(message)
                    limitation_details.append(
                        {"type": "C3_UNTRACEABLE", "citation_id": entry["citation_id"]}
                    )
            elif deficiency == "not_external_citable":
                limitations.append(message)
                limitation_details.append(
                    {"type": "C2_NOT_EXTERNAL_CITABLE", "citation_id": entry["citation_id"]}
                )

    if core_deficiencies:
        outcome = "ESCALATE"
        reasons = core_deficiencies + limitations
        required_actions = [ACTION_HUMAN_REVIEW, ACTION_VERIFY_SOURCE_IDENTITY]
    elif limitations:
        outcome = "CONDITIONAL"
        reasons = limitations
        required_actions = [ACTION_SUPPLEMENT_EVIDENCE]
    else:
        outcome = "PASS"
        reasons = ["最终引用 marker 可解析、来源资格可精确回查、引用可追溯。"]
        required_actions = []

    return LegalControlGateResult(
        gate="CITATION_VALIDITY",
        outcome=outcome,
        reasons=sorted(set(reasons)),
        refs=sorted(
            {entry["citation_id"] for entry in citation_entries if entry["deficiencies"]}
        ),
        required_actions=required_actions,
        details={
            "core_issue_count": len(core_issue_ids),
            "citation_count": len(citation_entries),
            "missing_markers": missing_markers,
            "citation_matrix": citation_entries,
            "limitations": limitation_details,
        },
    )
