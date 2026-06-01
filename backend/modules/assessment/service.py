from __future__ import annotations

import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from backend.common.quality.alignment import check_cn_alignment
from backend.common.tasks.manager import InMemoryTaskManager, TaskSnapshot
from backend.common.trace.context import current_trace
from backend.common.trace.recorder import TraceRecorder
from backend.common.workflow import GenerationContextPack, WorkflowPipeline
from backend.modules.assessment.chapter_generator import AssessmentChapterGenerator
from backend.modules.assessment.consistency_checker import ConsistencyChecker
from backend.modules.assessment.evidence_builder import build_assessment_evidence
from backend.modules.assessment.fact_builder import build_assessment_facts
from backend.modules.assessment.generation_basis import build_generation_basis_pack
from backend.modules.assessment.issue_builder import build_assessment_issues
from backend.modules.assessment.legal_grounding import build_legal_grounding
from backend.modules.assessment.profile_extractor import ProfileExtractor
from backend.modules.assessment.report_renderer import AssessmentReportRenderer
from backend.modules.assessment.retriever import AssessmentRetriever
from backend.modules.assessment.writing_strategy_builder import build_writing_strategy
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
        trace_dir = Path("outputs/assessment") / task_id / "trace"
        trace = TraceRecorder(trace_dir)
        token = current_trace.set(trace)

        try:
            run_result = self._build_pipeline().run(payload=payload, task_id=task_id, trace=trace)
        finally:
            current_trace.reset(token)

        return AssessmentResult(
            task_id=task_id,
            state=AssessmentTaskState.COMPLETED,
            report_path=run_result.outputs["docx"],
            output_files=run_result.outputs,
            profile=run_result.profile,
            regulations=run_result.regulations,
            chapters=run_result.chapters,
            consistency_issues=run_result.consistency_issues,
        )

    def _build_pipeline(self) -> WorkflowPipeline:
        return WorkflowPipeline(
            extract_profile=self.extractor.extract,
            evaluate_diagnosis=self._evaluate_diagnosis,
            validate_path=self._validate_path,
            build_facts=build_assessment_facts,
            retrieve_regulations=self.retriever.search,
            build_attachment_notes=_attachment_notes_from_profile,
            build_issues=build_assessment_issues,
            build_evidence=build_assessment_evidence,
            build_context_pack=self._build_context_pack,
            generate_chapters=self.generator.generate,
            check_consistency=self.checker.check_with_context,
            check_alignment=self._check_alignment,
            render_artifacts=self._render_outputs,
        )

    @staticmethod
    def _evaluate_diagnosis(payload: AssessmentRequest):
        return DiagnosisService().evaluate(
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

    def _build_context_pack(
        self,
        *,
        task_id: str,
        diagnosis,
        facts,
        regulations,
        issues,
        evidence_chain,
        path_warning: str | None,
        attachment_notes: list[dict[str, str]],
    ) -> GenerationContextPack:
        legal_grounding = build_legal_grounding(
            issues=issues,
            facts=facts,
            regulations=regulations,
        )
        writing_strategy = build_writing_strategy(issues=issues)
        generation_basis_pack = build_generation_basis_pack(
            task_id=task_id,
            facts=facts,
            issues=issues,
            evidence_chain=evidence_chain,
            regulations=regulations,
            attachment_notes=attachment_notes,
            path_warning=path_warning,
            legal_grounding=legal_grounding,
            writing_strategy=writing_strategy,
        )

        return GenerationContextPack(
            module_key="assessment",
            request_id=task_id,
            facts=facts,
            diagnosis_result=diagnosis.model_dump(),
            regulations=[hit.model_dump() for hit in regulations],
            issues=issues,
            evidence_chain=evidence_chain,
            path_warning=path_warning,
            risk_summary={
                "risk_level": diagnosis.risk_level,
                "recommended_path": diagnosis.recommended_path,
                "rationale": diagnosis.rationale,
            },
            attachment_notes=attachment_notes,
            output_requirements={"chapter_keys": list(self.generator.chapter_keys().values())},
            legal_grounding=legal_grounding,
            writing_strategy=writing_strategy,
            generation_basis_pack=generation_basis_pack,
        )

    @staticmethod
    def _check_alignment(report_content: str, profile) -> list[str]:
        return check_cn_alignment(
            report_content,
            industry=profile.industry,
            is_ciio=profile.is_ciio,
            contains_important_data=profile.contains_important_data,
            receiver_country=profile.receiver_country,
        )

    def _render_outputs(
        self,
        *,
        task_id: str,
        payload: AssessmentRequest,
        profile,
        regulations,
        chapters,
        path_warning: str | None,
        alignment_warning: str | None,
        issues,
        evidence_chain,
        attachment_notes: list[dict[str, str]],
        trace_manifest_path: str,
        facts,
        diagnosis,
        context_pack: GenerationContextPack | None = None,
    ) -> dict[str, str]:
        return self.renderer.render(
            task_id,
            payload.company_name,
            profile,
            regulations,
            chapters,
            path_warning=path_warning,
            alignment_warning=alignment_warning,
            issues=issues,
            evidence_chain=evidence_chain,
            attachment_notes=attachment_notes,
            trace_manifest_path=trace_manifest_path,
            facts=facts,
            diagnosis_result=diagnosis.model_dump() if hasattr(diagnosis, "model_dump") else diagnosis,
            force_override=payload.force_override_path,
            writing_strategy=context_pack.writing_strategy if context_pack else None,
            generation_basis_pack=context_pack.generation_basis_pack if context_pack else None,
            legal_grounding=context_pack.legal_grounding if context_pack else None,
        )

    def submit_async(self, payload: AssessmentRequest) -> AssessmentAsyncAccepted:
        diagnosis = self._evaluate_diagnosis(payload)
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


def _attachment_notes_from_profile(profile) -> list[dict[str, str]]:
    notes: list[dict[str, str]] = []
    for raw_note in profile.extracted_notes:
        source_ref, _, summary = raw_note.partition(":")
        notes.append(
            {
                "source_ref": source_ref.strip(),
                "summary": summary.strip() if summary else raw_note,
            }
        )
    return notes
