from backend.domains.cn.transfer_diagnosis.service import DiagnosisService as TransferDiagnosisService
from backend.schemas.diagnosis import (
    DiagnosisAnswerSet,
    DiagnosisOutcome,
    TransferScenario,
    TriState,
)
from backend.services.diagnosis_session_service import DiagnosisSessionService
from backend.services.session_service import SessionService


class StubLegalService:
    def search_cases(self, query: str, size: int) -> list[dict]:
        return []

    def search_laws(self, query: str, size: int) -> list[dict]:
        return []


def _session_service() -> DiagnosisSessionService:
    evaluator = TransferDiagnosisService()
    evaluator._build_rule_explanation = (
        lambda result, answers: result.rationale
    )
    return DiagnosisSessionService(
        report_service=None,  # type: ignore[arg-type]
        session_service=None,  # type: ignore[arg-type]
        legal_api_service=StubLegalService(),  # type: ignore[arg-type]
        evaluator=evaluator,
    )


def test_session_compatibility_uses_latest_emergency_priority() -> None:
    result = _session_service()._evaluate(
        DiagnosisAnswerSet(
            is_ciio=TriState.NO,
            contains_important_data=TriState.NO,
            personal_info_count=1_000_000,
            sensitive_personal_info_count=0,
            transfer_scenario=TransferScenario.EMERGENCY,
        )
    )

    assert result.outcome == DiagnosisOutcome.EXEMPTION
    assert any("exemption_emergency" in item for item in result.hit_rules)


def test_session_compatibility_preserves_manual_review() -> None:
    result = _session_service()._evaluate(
        DiagnosisAnswerSet(
            is_ciio=TriState.NO,
            contains_important_data=TriState.YES,
            personal_info_count=0,
            sensitive_personal_info_count=0,
            no_personal_info=TriState.YES,
        )
    )

    assert result.outcome == DiagnosisOutcome.MANUAL_REVIEW
    assert result.suggested_next_module is None


def test_manual_review_has_no_automatic_handoff() -> None:
    context = SessionService().build_prefill_context(
        "MANUAL_REVIEW",
        {},
    )

    assert context["suggested_next_module"] is None