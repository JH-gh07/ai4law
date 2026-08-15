"""task073 T06-B/T07 — EVIDENCE_SUFFICIENCY 门（E1-E5）单元测试。"""
from __future__ import annotations

from backend.common.workflow import (
    EvidenceItem,
    FactItem,
    GenerationContextPack,
    IssueItem,
)
from backend.domains.cn.security_assessment.evidence_gate import run_evidence_gate


def _issue(issue_id: str, severity: str = "HIGH", **overrides) -> IssueItem:
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


def _fact(fact_id: str, *, supportable: bool = True, status: str = "documented_evidence") -> FactItem:
    return FactItem(
        fact_id=fact_id,
        source_type="schema",
        field_path=f"request.{fact_id.lower()}",
        value=1,
        evidence_status=status,
        can_support_external_positive_claim=supportable,
    )


def _evidence(evidence_id: str, *, confidence: float = 0.9, **overrides) -> EvidenceItem:
    base = {
        "evidence_id": evidence_id,
        "claim": "claim",
        "fact_refs": [],
        "rule_refs": [],
        "conclusion": "conclusion",
        "confidence": confidence,
    }
    base.update(overrides)
    return EvidenceItem(**base)


def _pack(
    issues: list[IssueItem],
    facts: list[FactItem],
    evidence_chain: list[EvidenceItem],
    legal_grounding: dict | None = None,
    regulations: list[dict] | None = None,
) -> GenerationContextPack:
    return GenerationContextPack(
        module_key="assessment",
        request_id="req-1",
        facts=facts,
        regulations=regulations or [{"source_id": "CN-LAW-1"}],
        issues=issues,
        evidence_chain=evidence_chain,
        legal_grounding=legal_grounding or {},
    )


def test_supported_core_issue_passes():
    issues = [
        _issue(
            "ISSUE-1",
            fact_refs=["FACT-1"],
            rule_refs=["CN-LAW-1"],
            evidence_refs=["EVID-1"],
        ),
    ]
    pack = _pack(
        issues=issues,
        facts=[_fact("FACT-1")],
        evidence_chain=[_evidence("EVID-1", fact_refs=["FACT-1"], rule_refs=["CN-LAW-1"])],
        legal_grounding={"by_issue": {"ISSUE-1": [{"rule_id": "CN-LAW-1"}]}},
    )
    gate = run_evidence_gate(pack)
    assert gate.gate == "EVIDENCE_SUFFICIENCY"
    assert gate.outcome == "PASS"
    assert gate.details["support_matrix"][0]["status"] == "SUPPORTED"


def test_core_issue_missing_evidence_is_partial():
    issues = [
        _issue(
            "ISSUE-1",
            fact_refs=["FACT-1"],
            rule_refs=["CN-LAW-1"],
            evidence_refs=[],
        ),
    ]
    pack = _pack(
        issues=issues,
        facts=[_fact("FACT-1")],
        evidence_chain=[],
        legal_grounding={"by_issue": {"ISSUE-1": [{"rule_id": "CN-LAW-1"}]}},
    )
    gate = run_evidence_gate(pack)
    assert gate.outcome == "CONDITIONAL"
    entry = gate.details["support_matrix"][0]
    assert entry["status"] == "PARTIAL"
    assert "no_evidence_refs" in entry["deficiencies"]


def test_core_issue_no_legal_basis_is_unsupported():
    issues = [
        _issue(
            "ISSUE-1",
            fact_refs=["FACT-1"],
            rule_refs=["CN-LAW-1"],
            evidence_refs=["EVID-1"],
        ),
    ]
    pack = _pack(
        issues=issues,
        facts=[_fact("FACT-1")],
        evidence_chain=[_evidence("EVID-1")],
        legal_grounding={"by_issue": {}},  # 无法律依据
    )
    gate = run_evidence_gate(pack)
    assert gate.outcome == "ESCALATE"
    entry = gate.details["support_matrix"][0]
    assert entry["status"] == "UNSUPPORTED"
    assert "no_legal_basis" in entry["deficiencies"]


def test_e3_unsupported_positive_fact_is_partial():
    issues = [
        _issue(
            "ISSUE-1",
            fact_refs=["FACT-1"],
            rule_refs=["CN-LAW-1"],
            evidence_refs=["EVID-1"],
            can_enter_external_report=True,
        ),
    ]
    pack = _pack(
        issues=issues,
        facts=[_fact("FACT-1", supportable=False, status="user_claim_only")],
        evidence_chain=[_evidence("EVID-1")],
        legal_grounding={"by_issue": {"ISSUE-1": [{"rule_id": "CN-LAW-1"}]}},
    )
    gate = run_evidence_gate(pack)
    entry = gate.details["support_matrix"][0]
    assert entry["status"] == "PARTIAL"
    assert "no_external_positive_fact_support" in entry["deficiencies"]


def test_e4_single_low_confidence_evidence_is_partial():
    issues = [
        _issue(
            "ISSUE-1",
            fact_refs=["FACT-1"],
            rule_refs=["CN-LAW-1"],
            evidence_refs=["EVID-1"],
        ),
    ]
    pack = _pack(
        issues=issues,
        facts=[_fact("FACT-1")],
        evidence_chain=[_evidence("EVID-1", confidence=0.4)],
        legal_grounding={"by_issue": {"ISSUE-1": [{"rule_id": "CN-LAW-1"}]}},
    )
    gate = run_evidence_gate(pack)
    entry = gate.details["support_matrix"][0]
    assert "single_low_confidence_evidence" in entry["deficiencies"]
    assert gate.outcome == "CONDITIONAL"


def test_e5_dangling_refs_condition_gate():
    # Issue 引用了不存在的 fact → dangling ref → CONDITIONAL
    issues = [
        _issue(
            "ISSUE-1",
            fact_refs=["FACT-MISSING"],
            rule_refs=["CN-LAW-1"],
            evidence_refs=["EVID-1"],
        ),
    ]
    pack = _pack(
        issues=issues,
        facts=[_fact("FACT-1")],
        evidence_chain=[_evidence("EVID-1")],
        legal_grounding={"by_issue": {"ISSUE-1": [{"rule_id": "CN-LAW-1"}]}},
    )
    gate = run_evidence_gate(pack)
    assert gate.outcome == "CONDITIONAL"
    assert any(
        lim["type"] == "DANGLING_REF" for lim in gate.details["limitations"]
    )


def test_document_trace_gap_is_limitation_only_not_block():
    issues = [
        _issue(
            "ISSUE-1",
            fact_refs=["FACT-1"],
            rule_refs=["CN-LAW-1"],
            evidence_refs=["EVID-1"],
        ),
    ]
    pack = _pack(
        issues=issues,
        facts=[_fact("FACT-1")],
        evidence_chain=[
            _evidence("EVID-1", fact_refs=["FACT-1"], rule_refs=["CN-LAW-1"], document_refs=[]),
        ],
        legal_grounding={"by_issue": {"ISSUE-1": [{"rule_id": "CN-LAW-1"}]}},
    )
    gate = run_evidence_gate(pack)
    # 证据充分（引用齐备、有法律依据），document_refs=[] 只记 limitation
    assert gate.outcome == "PASS"
    assert any(
        lim["type"] == "DOCUMENT_TRACE_GAP" for lim in gate.details["limitations"]
    )


def test_no_core_issues_passes():
    pack = _pack(
        issues=[_issue("ISSUE-LOW", severity="LOW")],
        facts=[],
        evidence_chain=[],
    )
    gate = run_evidence_gate(pack)
    assert gate.outcome == "PASS"
    assert gate.details["core_issue_count"] == 0
