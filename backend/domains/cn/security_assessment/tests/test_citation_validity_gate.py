"""task073 T08 — CITATION_VALIDITY 门（C1/C2/C3）单元测试。"""
from __future__ import annotations

from backend.common.citation.models import CitationItem
from backend.common.citation.registry import CitationRegistry
from backend.common.citation.source_identity import SourceIdentityResolver
from backend.common.knowledge.v2 import SourceRegistryEntry
from backend.common.workflow import EvidenceItem, FactItem, GenerationContextPack, IssueItem
from backend.domains.cn.security_assessment.citation_validity_gate import (
    run_citation_validity_gate,
)
from backend.domains.cn.security_assessment.schema import ChapterContent


def _entry(source_id, *, can_be_cited=True, can_enter_external_report=True, review_status="published"):
    return SourceRegistryEntry(
        source_id=source_id,
        title=f"《{source_id}》",
        layer="L1_regulatory_evidence",
        source_kind="law_article",
        review_status=review_status,
        can_be_cited=can_be_cited,
        can_enter_external_report=can_enter_external_report,
    )


def _resolver(*entries):
    return SourceIdentityResolver(entries=list(entries))


def _issue(issue_id, severity="HIGH", **overrides):
    base = {
        "issue_id": issue_id,
        "title": f"issue {issue_id}",
        "description": "desc",
        "category": "consent",
        "severity": severity,
        "fact_refs": [],
        "rule_refs": [],
        "evidence_refs": [],
        "recommended_action": "action",
        "affects_outputs": ["overview"],
    }
    base.update(overrides)
    return IssueItem(**base)


def _fact(fact_id):
    return FactItem(fact_id=fact_id, source_type="schema", field_path=f"req.{fact_id}", value=1)


def _evidence(evidence_id):
    return EvidenceItem(
        evidence_id=evidence_id,
        claim="claim",
        conclusion="conclusion",
        fact_refs=["FACT-1"],
    )


def _citation(citation_id, source_id, **overrides):
    base = {
        "citation_id": citation_id,
        "source_id": source_id,
        "related_issue_ids": [],
        "related_fact_ids": [],
        "related_evidence_ids": [],
    }
    base.update(overrides)
    return CitationItem(**base)


def _registry(*items):
    reg = CitationRegistry()
    for item in items:
        reg.register(item)
    return reg


def _pack(issues, facts, evidence_chain, registry):
    return GenerationContextPack(
        module_key="assessment",
        request_id="req-1",
        facts=facts,
        regulations=[{"source_id": "CN-LAW-1"}],
        issues=issues,
        evidence_chain=evidence_chain,
        citation_registry=registry,
    )


def _chapter(content, chapter_no=1):
    return ChapterContent(chapter_no=chapter_no, title="结论", content=content, risk_level="HIGH")


CORE_ISSUE = _issue(
    "ISSUE-1",
    fact_refs=["FACT-1"],
    rule_refs=["CN-LAW-1"],
    evidence_refs=["EVID-1"],
)


def _supported_registry():
    reg = _registry(
        _citation(
            "CIT-CN-LAW1-ART1-P01",
            "CN-LAW-1",
            related_issue_ids=["ISSUE-1"],
            related_fact_ids=["FACT-1"],
            related_evidence_ids=["EVID-1"],
        )
    )
    reg.assign_footnote_number("CIT-CN-LAW1-ART1-P01")
    return reg


# ── PASS：核心引用完整、已注册、可追溯 ──────────────────────────────────

def test_supported_core_citation_passes():
    reg = _supported_registry()
    pack = _pack([CORE_ISSUE], [_fact("FACT-1")], [_evidence("EVID-1")], reg)
    resolver = _resolver(_entry("CN-LAW-1"))
    gate = run_citation_validity_gate(
        chapters=[_chapter("结论 [1] 引用。")],
        context_pack=pack,
        source_identity_resolver=resolver,
    )
    assert gate.outcome == "PASS"
    assert gate.details["citation_matrix"][0]["status"] == "SUPPORTED"
    assert gate.details["missing_markers"] == []


# ── C1：最终 marker 无法解析 → ESCALATE ─────────────────────────────────

def test_c1_missing_marker_escalates():
    reg = _supported_registry()
    pack = _pack([CORE_ISSUE], [_fact("FACT-1")], [_evidence("EVID-1")], reg)
    resolver = _resolver(_entry("CN-LAW-1"))
    gate = run_citation_validity_gate(
        chapters=[_chapter("结论【待核验：引用无法映射】。")],
        context_pack=pack,
        source_identity_resolver=resolver,
    )
    assert gate.outcome == "ESCALATE"
    assert "【待核验：引用无法映射】" in gate.details["missing_markers"]


def test_c1_dangling_footnote_escalates():
    reg = _supported_registry()  # 只分配了 [1]
    pack = _pack([CORE_ISSUE], [_fact("FACT-1")], [_evidence("EVID-1")], reg)
    resolver = _resolver(_entry("CN-LAW-1"))
    gate = run_citation_validity_gate(
        chapters=[_chapter("结论 [1] 与 [2] 引用。")],  # [2] 无 registry 映射
        context_pack=pack,
        source_identity_resolver=resolver,
    )
    assert gate.outcome == "ESCALATE"
    assert "[2]" in gate.details["missing_markers"]


# ── C2：unregistered / ineligible 来源 → ESCALATE ───────────────────────

def test_c2_unregistered_source_escalates():
    reg = _registry(
        _citation("CIT-CN-SYNTH-ART1-P01", "DeliLegal-synthetic-1", related_issue_ids=["ISSUE-1"])
    )
    pack = _pack([CORE_ISSUE], [_fact("FACT-1")], [_evidence("EVID-1")], reg)
    gate = run_citation_validity_gate(
        chapters=[_chapter("结论引用。")],
        context_pack=pack,
        source_identity_resolver=_resolver(_entry("CN-LAW-1")),
    )
    assert gate.outcome == "ESCALATE"
    entry = gate.details["citation_matrix"][0]
    assert entry["identity_status"] == "UNREGISTERED"
    assert entry["status"] == "UNREGISTERED"


def test_c2_ineligible_source_escalates():
    reg = _registry(
        _citation("CIT-CN-LAW9-ART1-P01", "CN-LAW-9", related_issue_ids=["ISSUE-1"])
    )
    pack = _pack([CORE_ISSUE], [_fact("FACT-1")], [_evidence("EVID-1")], reg)
    gate = run_citation_validity_gate(
        chapters=[_chapter("结论引用。")],
        context_pack=pack,
        source_identity_resolver=_resolver(_entry("CN-LAW-9", can_be_cited=False)),
    )
    assert gate.outcome == "ESCALATE"
    entry = gate.details["citation_matrix"][0]
    assert entry["identity_status"] == "INELIGIBLE"


# ── C3：可追溯性 ────────────────────────────────────────────────────────

def test_c3_untraceable_core_escalates():
    # 引用无任何 issue/fact/evidence 关联 → untraceable；存在核心 Issue → ESCALATE。
    reg = _registry(_citation("CIT-CN-LAW1-ART1-P01", "CN-LAW-1"))
    pack = _pack([CORE_ISSUE], [_fact("FACT-1")], [_evidence("EVID-1")], reg)
    gate = run_citation_validity_gate(
        chapters=[_chapter("结论引用。")],
        context_pack=pack,
        source_identity_resolver=_resolver(_entry("CN-LAW-1")),
    )
    assert gate.outcome == "ESCALATE"
    entry = gate.details["citation_matrix"][0]
    assert entry["traceable"] is False
    assert entry["status"] == "UNTRAACEABLE"


def test_c3_untraceable_non_core_conditional():
    # 无核心 Issue 时，untraceable 引用只是 limitation → CONDITIONAL。
    reg = _registry(_citation("CIT-CN-LAW1-ART1-P01", "CN-LAW-1"))
    pack = _pack([_issue("ISSUE-LOW", severity="LOW")], [_fact("FACT-1")], [_evidence("EVID-1")], reg)
    gate = run_citation_validity_gate(
        chapters=[_chapter("结论引用。")],
        context_pack=pack,
        source_identity_resolver=_resolver(_entry("CN-LAW-1")),
    )
    assert gate.outcome == "CONDITIONAL"


# ── 注册但不得进入对外报告 → CONDITIONAL ───────────────────────────────

def test_not_external_citable_is_conditional():
    reg = _registry(
        _citation(
            "CIT-CN-LAW1-ART1-P01",
            "CN-LAW-1",
            related_issue_ids=["ISSUE-1"],
            related_fact_ids=["FACT-1"],
        )
    )
    pack = _pack([CORE_ISSUE], [_fact("FACT-1")], [_evidence("EVID-1")], reg)
    gate = run_citation_validity_gate(
        chapters=[_chapter("结论引用。")],
        context_pack=pack,
        source_identity_resolver=_resolver(
            _entry("CN-LAW-1", can_enter_external_report=False)
        ),
    )
    assert gate.outcome == "CONDITIONAL"
    entry = gate.details["citation_matrix"][0]
    assert entry["status"] == "LIMITED"
    assert "not_external_citable" in entry["deficiencies"]


# ── 无核心 issue → PASS；有核心 issue 但无引用 → ESCALATE ───────────────

def test_no_core_issues_passes():
    pack = _pack([_issue("ISSUE-LOW", severity="LOW")], [], [], _registry())
    gate = run_citation_validity_gate(
        chapters=[_chapter("结论。")],
        context_pack=pack,
        source_identity_resolver=_resolver(_entry("CN-LAW-1")),
    )
    assert gate.outcome == "PASS"
    assert gate.details["core_issue_count"] == 0


def test_core_issues_no_citations_escalates():
    pack = _pack([CORE_ISSUE], [_fact("FACT-1")], [_evidence("EVID-1")], _registry())
    gate = run_citation_validity_gate(
        chapters=[_chapter("结论。")],
        context_pack=pack,
        source_identity_resolver=_resolver(_entry("CN-LAW-1")),
    )
    assert gate.outcome == "ESCALATE"
