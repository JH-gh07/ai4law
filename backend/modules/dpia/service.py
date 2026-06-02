"""DPIA service — full WorkflowPipeline orchestration for GDPR DPIA draft generation."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from backend.common.tasks.manager import InMemoryTaskManager, TaskSnapshot
from backend.common.trace.context import current_trace
from backend.common.trace.recorder import TraceRecorder
from backend.common.workflow import GenerationContextPack, WorkflowPipeline
from backend.modules.dpia.chapter_generator import DPIAChapterGenerator
from backend.modules.dpia.consistency_checker import DPIAConsistencyChecker
from backend.modules.dpia.evidence_builder import build_dpia_evidence
from backend.modules.dpia.fact_builder import build_dpia_facts
from backend.modules.dpia.generation_basis import build_generation_basis_pack
from backend.modules.dpia.issue_builder import build_dpia_issues
from backend.modules.dpia.legal_grounding import build_dpia_legal_grounding
from backend.modules.dpia.need_detector import DPIANeedDetector
from backend.modules.dpia.profile_extractor import DPIAProfileExtractor
from backend.modules.dpia.repair_generator import run_dpia_repair_pass
from backend.modules.dpia.report_renderer import DPIAReportRenderer
from backend.modules.dpia.retriever import DPIARetriever
from backend.modules.dpia.writing_strategy_builder import build_writing_strategy
from backend.modules.dpia.schema import (
    DPIAAsyncAccepted,
    DPIAAsyncStatus,
    DPIARequest,
    DPIAResult,
)

if TYPE_CHECKING:
    from backend.common.llm.client import LLMClient


class DPIAService:
    """Full DPIA draft generation service using WorkflowPipeline orchestration."""

    def __init__(self, llm_client: "LLMClient | None" = None) -> None:
        from backend.core.settings import get_settings

        if llm_client is None:
            from backend.common.llm.client import LLMClient as _LLMClient

            llm_client = _LLMClient(get_settings())
        self.llm_client = llm_client
        self.extractor = DPIAProfileExtractor()
        self.need_detector = DPIANeedDetector()
        self.retriever = DPIARetriever()
        self.generator = DPIAChapterGenerator(llm_client=llm_client)
        self.checker = DPIAConsistencyChecker()
        self.renderer = DPIAReportRenderer()
        self.tasks = InMemoryTaskManager(module="dpia")

    def generate_report(self, payload: DPIARequest) -> DPIAResult:
        task_id = str(uuid.uuid4())
        trace_dir = Path("outputs/dpia") / task_id / "trace"
        trace = TraceRecorder(trace_dir)
        token = current_trace.set(trace)

        try:
            run_result = self._build_pipeline().run(
                payload=payload, task_id=task_id, trace=trace
            )
        finally:
            current_trace.reset(token)

        need_assessment = None
        if run_result.diagnosis is not None:
            if hasattr(run_result.diagnosis, "model_dump"):
                need_assessment = run_result.diagnosis.model_dump()
            elif isinstance(run_result.diagnosis, dict):
                need_assessment = run_result.diagnosis

        return DPIAResult(
            task_id=task_id,
            state="COMPLETED",
            report_path=run_result.outputs.get("markdown", ""),
            output_files=run_result.outputs,
            profile=run_result.profile,
            regulations=run_result.regulations,
            chapters=run_result.chapters,
            consistency_issues=run_result.consistency_issues,
            need_assessment=need_assessment,
            risk_matrix=[],
            mitigation_plan=[],
        )

    def _build_pipeline(self) -> WorkflowPipeline:
        return WorkflowPipeline(
            extract_profile=self.extractor.extract,
            evaluate_diagnosis=self.need_detector.evaluate,
            validate_path=self._noop_validate,
            build_facts=build_dpia_facts,
            retrieve_regulations=self.retriever.search,
            build_attachment_notes=_attachment_notes_from_profile,
            build_issues=build_dpia_issues,
            build_evidence=build_dpia_evidence,
            retrieve_per_issue=None,
            build_context_pack=self._build_context_pack,
            generate_chapters=self.generator.generate,
            check_consistency=self.checker.check_with_context,
            check_alignment=self._noop_check_alignment,
            repair_chapters=self._repair_chapters,
            render_artifacts=self._render_outputs,
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
        per_issue_rag: dict[str, dict] | None = None,
    ) -> GenerationContextPack:
        legal_grounding, case_grounding = build_dpia_legal_grounding(
            issues=issues,
            facts=facts,
            regulations=regulations,
            per_issue_rag=per_issue_rag,
        )
        writing_strategy = build_writing_strategy(issues=issues)

        need_diagnosis = None
        if diagnosis is not None:
            if hasattr(diagnosis, "model_dump"):
                need_diagnosis = diagnosis.model_dump()
            elif isinstance(diagnosis, dict):
                need_diagnosis = diagnosis

        generation_basis_pack = build_generation_basis_pack(
            task_id=task_id,
            facts=facts,
            issues=issues,
            evidence_chain=evidence_chain,
            regulations=regulations,
            attachment_notes=attachment_notes,
            need_assessment=need_diagnosis,
            legal_grounding=legal_grounding,
            writing_strategy=writing_strategy,
        )

        regulation_dicts = [hit.model_dump() for hit in regulations]

        return GenerationContextPack(
            module_key="dpia",
            request_id=task_id,
            facts=facts,
            diagnosis_result=need_diagnosis or {},
            regulations=regulation_dicts,
            issues=issues,
            evidence_chain=evidence_chain,
            path_warning=path_warning,
            risk_summary={
                "dpia_required": need_diagnosis.get("dpia_required") if need_diagnosis else None,
                "prior_consultation_possible": (
                    need_diagnosis.get("prior_consultation_possible")
                    if need_diagnosis else None
                ),
            },
            attachment_notes=attachment_notes,
            output_requirements={
                "chapter_keys": DPIA_CHAPTER_KEYS,
            },
            legal_grounding=legal_grounding,
            case_grounding=case_grounding,
            writing_strategy=writing_strategy,
            generation_basis_pack=generation_basis_pack,
        )

    def _repair_chapters(
        self,
        *,
        chapters,
        consistency_issues: list[str],
        profile,
        context_pack,
    ) -> tuple[list, list[str], bool]:
        return run_dpia_repair_pass(
            chapters=chapters,
            consistency_issues=consistency_issues,
            profile=profile,
            context_pack=context_pack,
            llm_client=self.llm_client,
            max_retries=3,
        )

    def _render_outputs(
        self,
        *,
        task_id: str,
        payload: DPIARequest,
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
        need_diagnosis = None
        if diagnosis is not None:
            if hasattr(diagnosis, "model_dump"):
                need_diagnosis = diagnosis.model_dump()
            elif isinstance(diagnosis, dict):
                need_diagnosis = diagnosis

        return self.renderer.render(
            task_id=task_id,
            profile=profile,
            chapters=chapters,
            issues=issues,
            evidence_chain=evidence_chain,
            facts=facts,
            need_assessment=need_diagnosis,
            legal_grounding=context_pack.legal_grounding if context_pack else None,
            writing_strategy=context_pack.writing_strategy if context_pack else None,
            generation_basis_pack=context_pack.generation_basis_pack if context_pack else None,
            citation_registry=context_pack.citation_registry if context_pack else None,
            trace_manifest_path=trace_manifest_path,
        )

    # ── No-ops ──

    @staticmethod
    def _noop_validate(payload: Any, recommended_path: str, rationale: str) -> str | None:
        """DPIA does not need path validation."""
        return None

    @staticmethod
    def _noop_check_alignment(report_content: str, profile) -> list[str]:
        """DPIA alignment check is handled by consistency checker."""
        return []

    # ── Async API ──

    def submit_async(self, payload: DPIARequest) -> DPIAAsyncAccepted:
        snapshot = self.tasks.submit(lambda: self.generate_report(payload))
        return self._snapshot_to_accepted(snapshot)

    def get_async_status(self, task_id: str) -> DPIAAsyncStatus:
        snapshot = self.tasks.get_or_raise(task_id)
        return self._snapshot_to_status(snapshot)

    def retry_async(self, task_id: str) -> DPIAAsyncStatus:
        snapshot = self.tasks.retry(task_id)
        return self._snapshot_to_status(snapshot)

    def cancel_async(self, task_id: str) -> DPIAAsyncStatus:
        snapshot = self.tasks.cancel(task_id)
        return self._snapshot_to_status(snapshot)

    @staticmethod
    def _snapshot_to_accepted(snapshot: TaskSnapshot) -> DPIAAsyncAccepted:
        return DPIAAsyncAccepted(
            task_id=snapshot.task_id,
            module=snapshot.module,
            state=snapshot.state,
            attempts=snapshot.attempts,
            max_attempts=snapshot.max_attempts,
        )

    @staticmethod
    def _snapshot_to_status(snapshot: TaskSnapshot) -> DPIAAsyncStatus:
        result = None
        if snapshot.result is not None:
            result = DPIAResult.model_validate(snapshot.result)
        return DPIAAsyncStatus(
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


def _attachment_notes_from_profile(profile) -> list[dict[str, str]]:
    """Extract attachment notes from DPIAProjectProfile."""
    if hasattr(profile, "attachment_metadata") and profile.attachment_metadata:
        notes: list[dict[str, str]] = []
        for meta in profile.attachment_metadata:
            entry: dict[str, str] = {
                "source_ref": meta.get("filename", ""),
                "type": meta.get("type", "other"),
            }
            if "char_count" in meta and meta.get("char_count", 0) > 0:
                entry["summary"] = f"已解析 {meta['char_count']} 字符"
            elif "summary" in meta:
                entry["summary"] = meta["summary"]
            else:
                entry["summary"] = "附件已上传但尚未解析"
            notes.append(entry)
        return notes

    # Fallback to string notes
    notes: list[dict[str, str]] = []
    for raw_note in getattr(profile, "extracted_notes", []):
        if isinstance(raw_note, str):
            source_ref, _, summary = raw_note.partition(":")
            notes.append({
                "source_ref": source_ref.strip(),
                "summary": summary.strip() if summary else raw_note,
            })
    return notes


DPIA_CHAPTER_KEYS = [
    "need_identification",
    "processing_description",
    "consultation",
    "necessity_proportionality",
    "risk_assessment",
    "mitigation",
    "signoff",
]
