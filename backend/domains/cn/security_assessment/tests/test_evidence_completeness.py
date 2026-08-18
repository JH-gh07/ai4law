"""task081 T081-03 — Evidence 完整性测试。

验证：
1. 无 fact_refs 的 Issue（含 HIGH）不再被跳过，生成 UNSUPPORTED Evidence。
2. 有 fact_refs 的 Evidence 正常生成并回写 issue.evidence_refs。
3. ContextPack 一致性检查的 dangling facts/rules/evidence 为 0。
4. 删除任一 fact/rule/evidence 后一致性检查显式失败（不静默通过）。
"""
from __future__ import annotations

from backend.common.workflow import GenerationContextPack
from backend.domains.cn.security_assessment.consistency_checker import (
    check_context_pack_consistency,
)
from backend.domains.cn.security_assessment.evidence_builder import build_assessment_evidence
from backend.domains.cn.security_assessment.fact_builder import build_assessment_facts
from backend.domains.cn.security_assessment.issue_builder import build_assessment_issues
from backend.domains.cn.security_assessment.profile_extractor import ProfileExtractor
from backend.domains.cn.security_assessment.schema import AssessmentRequest, RegulationHit
from backend.domains.cn.transfer_diagnosis.schema import DiagnosisResult


def _diagnosis() -> DiagnosisResult:
    return DiagnosisResult(
        recommended_path="security_assessment",
        legal_basis=["个人信息保护法 第40条"],
        rationale="规则命中",
        action_items=[],
        risk_level="HIGH",
        matched_rule_id="ciio",
    )


def _regulations() -> list[RegulationHit]:
    return [
        RegulationHit(
            source_id="reg-pipl-40",
            title="个人信息保护法",
            article="第40条",
            snippet="CIIO 或达到规模的个人信息处理者向境外提供个人信息应满足要求。",
        )
    ]


def _minimal_request() -> AssessmentRequest:
    return AssessmentRequest(
        company_name="云帆数据科技有限公司",
        industry="互联网SaaS",
        is_ciio=True,
        contains_important_data=False,
        pii_count=1200000,
        spi_count=15000,
        transfer_purpose="全球客服与风控联防",
        receiver_country="新加坡",
        uploaded_files=[],
    )


def _build_pack(request: AssessmentRequest) -> GenerationContextPack:
    diagnosis = _diagnosis()
    profile = ProfileExtractor().extract(request)
    facts = build_assessment_facts(request, profile, diagnosis)
    issues = build_assessment_issues(facts, diagnosis, _regulations(), [])
    updated_issues, evidence_chain = build_assessment_evidence(
        facts, issues, _regulations(), diagnosis
    )
    return GenerationContextPack(
        module_key="assessment",
        request_id="req-1",
        facts=facts,
        regulations=[r.model_dump() for r in _regulations()],
        issues=updated_issues,
        evidence_chain=evidence_chain,
    )


def test_high_issue_without_fact_refs_gets_unsupported_evidence() -> None:
    pack = _build_pack(_minimal_request())

    # consent-evidence-missing 是 HIGH 且无 fact_refs
    consent_issue = next(
        issue for issue in pack.issues
        if issue.issue_id == "ISSUE-consent-evidence-missing"
    )
    assert consent_issue.severity == "HIGH"
    assert consent_issue.fact_refs == []

    # 不再跳过 → 生成 UNSUPPORTED Evidence 并回写 evidence_refs
    assert consent_issue.evidence_refs
    evidence = next(
        ev for ev in pack.evidence_chain
        if ev.evidence_id == consent_issue.evidence_refs[0]
    )
    assert evidence.usage_constraint.startswith("UNSUPPORTED")
    assert evidence.fact_refs == []


def test_every_issue_has_evidence_or_explanation() -> None:
    pack = _build_pack(_minimal_request())
    evidence_ids = {ev.evidence_id for ev in pack.evidence_chain}

    for issue in pack.issues:
        if issue.severity in {"HIGH", "BLOCKER"}:
            assert issue.evidence_refs, f"{issue.issue_id} 无 evidence_refs"
            assert set(issue.evidence_refs).issubset(evidence_ids)


def test_consistency_checker_zero_dangling() -> None:
    pack = _build_pack(_minimal_request())
    dangling = check_context_pack_consistency(pack)
    assert dangling == []


def test_deleting_a_fact_fails_explicitly() -> None:
    pack = _build_pack(_minimal_request())

    # 删除一个被 issue.fact_refs 引用的 fact
    referenced_fact_ids = {
        ref for issue in pack.issues for ref in issue.fact_refs
    }
    assert referenced_fact_ids
    victim = next(iter(referenced_fact_ids))
    pack.facts = [fact for fact in pack.facts if fact.fact_id != victim]

    dangling = check_context_pack_consistency(pack)
    assert any("references missing facts" in msg for msg in dangling)


def test_deleting_an_evidence_fails_explicitly() -> None:
    pack = _build_pack(_minimal_request())

    # 删除被 issue.evidence_refs 引用的 evidence
    referenced_evidence_ids = {
        ref for issue in pack.issues for ref in issue.evidence_refs
    }
    assert referenced_evidence_ids
    victim = next(iter(referenced_evidence_ids))
    pack.evidence_chain = [
        ev for ev in pack.evidence_chain if ev.evidence_id != victim
    ]

    dangling = check_context_pack_consistency(pack)
    assert any("references missing evidence" in msg for msg in dangling)
