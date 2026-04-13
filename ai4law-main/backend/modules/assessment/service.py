from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from backend.common.quality.alignment import check_cn_alignment
from backend.common.tasks.manager import InMemoryTaskManager, TaskSnapshot
from backend.modules.assessment.chapter_generator import AssessmentChapterGenerator
from backend.modules.assessment.consistency_checker import ConsistencyChecker
from backend.modules.assessment.profile_extractor import ProfileExtractor
from backend.modules.assessment.report_renderer import AssessmentReportRenderer
from backend.modules.assessment.retriever import AssessmentRetriever
from backend.modules.assessment.schema import (
    AssessmentAsyncAccepted,
    AssessmentAsyncStatus,
    AssessmentRequest,
    AssessmentResult,
)
from backend.modules.assessment.task_state import AssessmentTaskState
from backend.modules.diagnosis.schema import DiagnosisAnswers, ReceiverType, TransferScenario, YesNoUnknown
from backend.modules.diagnosis.service import DiagnosisService

if TYPE_CHECKING:
    from backend.common.llm.client import LLMClient
    from backend.services.legal_api_service import DeliLegalService


class AssessmentService:
    def __init__(self, llm_client: LLMClient | None = None, legal_api_service: DeliLegalService | None = None) -> None:
        from backend.core.settings import get_settings
        if llm_client is None:
            from backend.common.llm.client import LLMClient as _LLMClient
            llm_client = _LLMClient(get_settings())
        if legal_api_service is None:
            from backend.services.legal_api_service import DeliLegalService as _DeliLegalService
            legal_api_service = _DeliLegalService(get_settings())
        self.extractor = ProfileExtractor()
        self.retriever = AssessmentRetriever(legal_service=legal_api_service)
        self.generator = AssessmentChapterGenerator(llm_client=llm_client)
        self.checker = ConsistencyChecker()
        self.renderer = AssessmentReportRenderer()
        self.tasks = InMemoryTaskManager(module="assessment")

    def generate_report(self, payload: AssessmentRequest) -> AssessmentResult:
        task_id = str(uuid.uuid4())

        profile = self.extractor.extract(payload)
        diagnosis = DiagnosisService().evaluate(
            DiagnosisAnswers(
                q1_is_ciio=YesNoUnknown.YES if payload.is_ciio else YesNoUnknown.NO,
                q2_has_important_data=YesNoUnknown.YES if payload.contains_important_data else YesNoUnknown.NO,
                q3_pii_count=payload.pii_count,
                q4_spi_count=payload.spi_count,
                q6_scenario=TransferScenario.OTHER,
                q7_receiver_type=ReceiverType.THIRD_PARTY,
                q8_purpose=payload.transfer_purpose,
            )
        )
        path_warning = self._validate_path(payload, diagnosis.recommended_path, diagnosis.rationale)
        regulations = self.retriever.search(profile)
        chapters = self.generator.generate(profile, regulations)
        issues = self.checker.check(profile, chapters)
        alignment_issues = check_cn_alignment(
            "\n".join(chapter.content for chapter in chapters),
            industry=profile.industry,
            is_ciio=profile.is_ciio,
            contains_important_data=profile.contains_important_data,
            receiver_country=profile.receiver_country,
        )
        if alignment_issues:
            issues.extend(alignment_issues)
        if path_warning:
            issues.append(path_warning)
        alignment_warning = "；".join(alignment_issues) if alignment_issues else None
        outputs = self.renderer.render(
            payload.company_name,
            profile,
            regulations,
            chapters,
            path_warning=path_warning,
            alignment_warning=alignment_warning,
        )

        return AssessmentResult(
            task_id=task_id,
            state=AssessmentTaskState.COMPLETED,
            report_path=outputs["docx"],
            output_files=outputs,
            profile=profile,
            regulations=regulations,
            chapters=chapters,
            consistency_issues=issues,
        )

    def submit_async(self, payload: AssessmentRequest) -> AssessmentAsyncAccepted:
        diagnosis = DiagnosisService().evaluate(
            DiagnosisAnswers(
                q1_is_ciio=YesNoUnknown.YES if payload.is_ciio else YesNoUnknown.NO,
                q2_has_important_data=YesNoUnknown.YES if payload.contains_important_data else YesNoUnknown.NO,
                q3_pii_count=payload.pii_count,
                q4_spi_count=payload.spi_count,
                q6_scenario=TransferScenario.OTHER,
                q7_receiver_type=ReceiverType.THIRD_PARTY,
                q8_purpose=payload.transfer_purpose,
            )
        )
        self._validate_path(payload, diagnosis.recommended_path, diagnosis.rationale)
        snapshot = self.tasks.submit(lambda: self.generate_report(payload))
        return self._snapshot_to_accepted(snapshot)

    def get_async_status(self, task_id: str) -> AssessmentAsyncStatus:
        snapshot = self.tasks.get_or_raise(task_id)
        return self._snapshot_to_status(snapshot)

    def retry_async(self, task_id: str) -> AssessmentAsyncStatus:
        snapshot = self.tasks.retry(task_id)
        return self._snapshot_to_status(snapshot)

    def cancel_async(self, task_id: str) -> AssessmentAsyncStatus:
        snapshot = self.tasks.cancel(task_id)
        return self._snapshot_to_status(snapshot)

    @staticmethod
    def _snapshot_to_accepted(snapshot: TaskSnapshot) -> AssessmentAsyncAccepted:
        return AssessmentAsyncAccepted(
            task_id=snapshot.task_id,
            module=snapshot.module,
            state=snapshot.state,
            attempts=snapshot.attempts,
            max_attempts=snapshot.max_attempts,
        )

    @staticmethod
    def _snapshot_to_status(snapshot: TaskSnapshot) -> AssessmentAsyncStatus:
        result = None
        if snapshot.result is not None:
            result = AssessmentResult.model_validate(snapshot.result)
        return AssessmentAsyncStatus(
            task_id=snapshot.task_id,
            module=snapshot.module,
            state=snapshot.state,
            attempts=snapshot.attempts,
            max_attempts=snapshot.max_attempts,
            created_at=snapshot.created_at,
            updated_at=snapshot.updated_at,
            error=snapshot.error,
            result=result,
        )

    @staticmethod
    def _validate_path(payload: AssessmentRequest, recommended_path: str, rationale: str) -> str | None:
        if recommended_path == "security_assessment":
            return None
        warning = f"诊断推荐路径为 {recommended_path}：{rationale}"
        if not payload.force_override_path:
            raise ValueError(
                f"Path mismatch: {warning}。如需继续生成安全评估报告，请设置 force_override_path=true。"
            )
        return warning
