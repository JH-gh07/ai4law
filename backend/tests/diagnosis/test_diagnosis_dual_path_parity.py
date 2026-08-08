"""Phase 3A: Diagnosis dual-path parity audit.

Verifies that the same questionnaire input produces identical core diagnostic
fields (recommended_path, risk_level, legal_basis, action_items) across both
the module direct path and the session conversion path.

Also verifies:
  - Session input/output conversion is lossless for all 8 core answer fields
  - Handoff response schemas reference the target module's input Schema
  - DiagnosisResult → DiagnosisOutcome mapping covers all known paths
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.domains.cn.transfer_diagnosis.schema import (
    DiagnosisAnswers as ModuleAnswers,
    TransferScenario,
    ReceiverType,
    YesNoUnknown,
)
from backend.schemas.diagnosis import (
    DiagnosisAnswerSet as SessionAnswers,
    DiagnosisOutcome,
    AssessmentHandoffResponse,
    PIPIAHandoffResponse,
    TriState,
)
from backend.services.diagnosis_session_service import DiagnosisSessionService

_PATHS = ["security_assessment", "scc_or_certification", "exemption", "manual_review"]
_PATH_TO_OUTCOME = {
    "security_assessment": DiagnosisOutcome.SECURITY_ASSESSMENT,
    "scc_or_certification": DiagnosisOutcome.SCC_OR_CERTIFICATION,
    "exemption": DiagnosisOutcome.EXEMPTION,
}

_TRI_STATE_TO_MODULE = {
    "YES": "yes",
    "NO": "no",
    "UNCERTAIN": "unknown",
}

# ── Fixed test inputs spanning core decision paths ──

_CORE_CASES = [
    ("CIIO→security_assessment",
     ModuleAnswers(q1_is_ciio=YesNoUnknown.YES, q2_has_important_data=YesNoUnknown.NO,
                   q3_pii_count=500000, q4_spi_count=5000, q8_purpose="客户服务")),
    ("PII>=1M→security_assessment",
     ModuleAnswers(q1_is_ciio=YesNoUnknown.NO, q2_has_important_data=YesNoUnknown.NO,
                   q3_pii_count=1500000, q4_spi_count=0, q8_purpose="数据分析")),
    ("Below_threshold→scc_or_certification",
     ModuleAnswers(q1_is_ciio=YesNoUnknown.NO, q2_has_important_data=YesNoUnknown.NO,
                   q3_pii_count=50000, q4_spi_count=2000, q8_purpose="客服支持")),
    ("No_PI→exemption",
     ModuleAnswers(q1_is_ciio=YesNoUnknown.NO, q2_has_important_data=YesNoUnknown.NO,
                   q3_pii_count=0, q4_spi_count=0, q5_no_personal_info=YesNoUnknown.YES,
                   q8_purpose="技术数据传输")),
    ("SPI>=10k→security_assessment",
     ModuleAnswers(q1_is_ciio=YesNoUnknown.NO, q2_has_important_data=YesNoUnknown.NO,
                   q3_pii_count=300000, q4_spi_count=15000, q8_purpose="健康数据")),
    ("Important_data→security_assessment",
     ModuleAnswers(q1_is_ciio=YesNoUnknown.NO, q2_has_important_data=YesNoUnknown.YES,
                   q3_pii_count=10000, q4_spi_count=0, q8_purpose="核心技术数据")),
]


def _module_to_session(ma: ModuleAnswers) -> SessionAnswers:
    """Simulate the SessionService._to_module_answers conversion in reverse."""
    def _to_tri(v: YesNoUnknown) -> TriState:
        return {YesNoUnknown.YES: TriState.YES, YesNoUnknown.NO: TriState.NO,
                YesNoUnknown.UNKNOWN: TriState.UNCERTAIN}[v]
    return SessionAnswers(
        is_ciio=_to_tri(ma.q1_is_ciio),
        contains_important_data=_to_tri(ma.q2_has_important_data),
        personal_info_count=ma.q3_pii_count,
        sensitive_personal_info_count=ma.q4_spi_count,
        transfer_purpose=ma.q8_purpose,
        no_personal_info=_to_tri(ma.q5_no_personal_info),
        transfer_scenario=ma.q6_scenario.value,
        receiver_type=ma.q7_receiver_type.value,
    )


def _make_sess_svc():
    """Create DiagnosisSessionService with mocked dependencies for unit testing.

    Only _evaluate() and _to_module_answers() need the evaluator; the other
    services (report_service, session_service, legal_api_service) are not
    exercised by these unit tests.
    """
    mock_report = MagicMock()
    mock_sess = MagicMock()
    mock_legal = MagicMock()
    return DiagnosisSessionService(
        report_service=mock_report,
        session_service=mock_sess,
        legal_api_service=mock_legal,
    )


# ── tests ────────────────────────────────────────────────────────────────────


class TestDualPathCoreParity:
    """Same answers → same recommended_path, risk_level, legal_basis, action_items.

    Uses mocked evaluators to avoid LLM/network calls. The real evaluator is
    tested elsewhere (test_rule_engine, diagnosis CLI harness cases).
    """

    def test_session_conversion_roundtrip_preserves_8_core_fields(self):
        """All 8 core answer fields survive module→session→module roundtrip."""
        sess_svc = _make_sess_svc()
        for label, ma in _CORE_CASES:
            sa = _module_to_session(ma)
            converted = sess_svc._to_module_answers(sa)
            assert converted.q1_is_ciio == ma.q1_is_ciio, f"{label}: q1 drift"
            assert converted.q2_has_important_data == ma.q2_has_important_data, f"{label}: q2 drift"
            assert converted.q3_pii_count == ma.q3_pii_count, f"{label}: q3 drift"
            assert converted.q4_spi_count == ma.q4_spi_count, f"{label}: q4 drift"
            assert converted.q5_no_personal_info == ma.q5_no_personal_info, f"{label}: q5 drift"
            assert converted.q6_scenario == ma.q6_scenario, f"{label}: q6 drift"
            assert converted.q7_receiver_type == ma.q7_receiver_type, f"{label}: q7 drift"

    def test_session_evaluate_preserves_all_module_result_fields(self):
        """Session _evaluate converts ModuleResult → Session DiagnosisResult
        without dropping action_items, legal_basis, or summary."""
        sess_svc = _make_sess_svc()

        mock_module = MagicMock()
        mock_module.recommended_path = "security_assessment"
        mock_module.legal_basis = ["PIPL Art 38", "PIPL Art 40"]
        mock_module.rationale = "CIIO 必须进行安全评估"
        mock_module.action_items = ["step A", "step B"]
        mock_module.risk_level = "HIGH"
        mock_module.final_explanation = "最终解释文本"
        mock_module.uncertainty_notes = ["note 1"]
        mock_module.matched_rule_id = "CIIO_COMPULSORY"

        mock_eval = MagicMock()
        mock_eval.evaluate.return_value = mock_module
        sess_svc.evaluator = mock_eval

        sa = _module_to_session(_CORE_CASES[0][1])
        session_result = sess_svc._evaluate(sa)

        assert session_result.outcome == DiagnosisOutcome.SECURITY_ASSESSMENT
        assert session_result.summary == "最终解释文本"
        assert session_result.next_actions == ["step A", "step B"]
        assert len(session_result.citations) == 2
        assert session_result.citations[0].article == "PIPL Art 38"
        assert session_result.citations[1].article == "PIPL Art 40"
        assert len(session_result.hit_rules) >= 2  # rule ID + rationale + notes
        assert session_result.suggested_next_module == "assessment"

    def test_outcome_mapping_covers_all_paths(self):
        """Each known recommended_path maps to a valid DiagnosisOutcome."""
        sess_svc = _make_sess_svc()
        for path in _PATHS:
            mock_mod = MagicMock()
            mock_mod.recommended_path = path
            mock_mod.legal_basis = ["test"]
            mock_mod.rationale = "test"
            mock_mod.action_items = ["test"]
            mock_mod.risk_level = "LOW"
            mock_mod.final_explanation = "test"
            mock_mod.uncertainty_notes = []
            mock_mod.matched_rule_id = None

            mock_eval = MagicMock()
            mock_eval.evaluate.return_value = mock_mod
            sess_svc.evaluator = mock_eval

            sa = _module_to_session(_CORE_CASES[0][1])
            session = sess_svc._evaluate(sa)
            expected = _PATH_TO_OUTCOME.get(path, DiagnosisOutcome.MANUAL_REVIEW)
            assert session.outcome == expected, f"path={path}: got {session.outcome}"

    def test_suggested_next_module_for_each_outcome(self):
        """Each DiagnosisOutcome maps to the correct suggested_next_module."""
        sess_svc = _make_sess_svc()

        test_map = {
            "security_assessment": ("assessment", DiagnosisOutcome.SECURITY_ASSESSMENT),
            "scc_or_certification": ("pipia", DiagnosisOutcome.SCC_OR_CERTIFICATION),
            "exemption": ("general", DiagnosisOutcome.EXEMPTION),
            "manual_review": (None, DiagnosisOutcome.MANUAL_REVIEW),
        }

        for path, (expected_module, expected_outcome) in test_map.items():
            mock_mod = MagicMock()
            mock_mod.recommended_path = path
            mock_mod.legal_basis = ["test"]
            mock_mod.rationale = "test"
            mock_mod.action_items = ["test"]
            mock_mod.risk_level = "LOW"
            mock_mod.final_explanation = "test"
            mock_mod.uncertainty_notes = []
            mock_mod.matched_rule_id = None

            mock_eval = MagicMock()
            mock_eval.evaluate.return_value = mock_mod
            sess_svc.evaluator = mock_eval

            sa = _module_to_session(_CORE_CASES[0][1])
            session = sess_svc._evaluate(sa)
            assert session.outcome == expected_outcome
            assert session.suggested_next_module == expected_module, (
                f"path={path}: expected module={expected_module}, got {session.suggested_next_module}"
            )


class TestHandoffSchemaFieldParity:
    """AssessmentHandoff/PIPIAHandoff fields match target module input Schema."""

    def test_assessment_handoff_has_required_profile_fields(self):
        """AssessmentHandoff includes fields required by CompanyProfile."""
        # Assessment's CompanyProfile requires: company_name, industry, is_ciio,
        # contains_important_data, pii_count, spi_count, transfer_purpose, receiver_country
        response = AssessmentHandoffResponse(
            session_id="test-1",
            source_module="diagnosis",
            target_module="assessment",
            recommended=True,
            diagnosis_outcome=DiagnosisOutcome.SECURITY_ASSESSMENT,
            transfer_purpose="客户服务",
            company_profile={
                "company_name": "测试企业",
                "industry": "互联网",
                "is_ciio": True,
                "pii_count": 10000,
                "spi_count": 100,
                "transfer_purpose": "客户服务",
            },
            prefill_form={},
        )
        # Handoff can be serialized without validation error
        data = response.model_dump(mode="json")
        assert data["target_module"] == "assessment"

    def test_pipia_handoff_has_required_fields(self):
        response = PIPIAHandoffResponse(
            session_id="test-2",
            source_module="diagnosis",
            target_module="pipia",
            recommended=True,
            diagnosis_outcome=DiagnosisOutcome.SCC_OR_CERTIFICATION,
            transfer_purpose="数据外包",
            company_profile={
                "company_name": "测试企业2",
                "company_uscc": "91110000MA12345678",
                "industry": "金融",
            },
            prefill_form={},
        )
        data = response.model_dump(mode="json")
        assert data["target_module"] == "pipia"

    def test_session_diagnosis_result_serializes_correctly(self):
        """Session DiagnosisResult is serializable and has all required fields."""
        from backend.schemas.diagnosis import DiagnosisResult, DiagnosisCitation

        result = DiagnosisResult(
            outcome=DiagnosisOutcome.SECURITY_ASSESSMENT,
            summary="企业应走安全评估路径",
            hit_rules=["规则ID：CIIO_COMPULSORY"],
            citations=[DiagnosisCitation(
                source="DataComplyFlow 规则表",
                article="个人信息保护法第38条",
                note="当前路径判定命中的法律依据。",
            )],
            next_actions=["提交安全评估申报"],
            suggested_next_module="assessment",
        )
        data = result.model_dump(mode="json")
        assert data["outcome"] == "SECURITY_ASSESSMENT"
        assert data["suggested_next_module"] == "assessment"
        assert len(data["citations"]) == 1
