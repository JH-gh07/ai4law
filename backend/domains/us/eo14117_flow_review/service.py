"""Historical CN Flow API compatibility layer for the canonical EO 14117 service."""

from __future__ import annotations

import uuid
from pathlib import Path

from backend.common.llm.client import LLMClient
from backend.common.tasks.manager import InMemoryTaskManager, TaskSnapshot
from backend.common.trace.recorder import TraceRecorder
from backend.domains.us.eo14117.schema import US14117Result
from backend.domains.us.eo14117.service import US14117Service
from backend.domains.us.eo14117_flow_review.compatibility import adapt_cn_flow_request
from backend.domains.us.eo14117_flow_review.schema import (
    CNFlowAsyncAccepted,
    CNFlowAsyncStatus,
    CNFlowChapter,
    CNFlowRequest,
    CNFlowResult,
    CNFlowRiskItem,
)


class CNFlowService:
    """Preserve old routes and task records while delegating all decisions."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        if llm_client is None:
            from backend.core.settings import get_settings

            llm_client = LLMClient(get_settings())
        self.llm_client = llm_client
        self.tasks = InMemoryTaskManager(module="cn_flow")
        self.canonical_service = US14117Service(llm_client=llm_client)

    def generate_report(
        self,
        payload: CNFlowRequest,
        *,
        task_id: str | None = None,
        trace: TraceRecorder | None = None,
    ) -> CNFlowResult:
        run_task_id = task_id or str(uuid.uuid4())
        if trace is None:
            trace = TraceRecorder(
                Path("outputs/us_14117") / run_task_id / "trace",
                task_id=run_task_id,
            )
        compatibility = adapt_cn_flow_request(payload)
        trace.record(
            "cn_flow_request",
            {
                "canonical_module": compatibility.canonical_module,
                "lossy_fields": compatibility.lossy_fields,
                "clarification_questions": compatibility.clarification_questions,
            },
        )
        canonical_result = self.canonical_service.generate_report(
            compatibility.canonical_request,
            task_id=run_task_id,
            trace=trace,
        )
        return _wrap_canonical_result(payload, canonical_result, compatibility.lossy_fields)

    def submit_async(self, payload: CNFlowRequest) -> CNFlowAsyncAccepted:
        # Reject incomplete input before creating a task that can only fail.
        adapt_cn_flow_request(payload)
        task_id = str(uuid.uuid4())
        trace = TraceRecorder(Path("outputs/us_14117") / task_id / "trace", task_id=task_id)
        snapshot = self.tasks.submit_with_trace(
            lambda: self.generate_report(payload, task_id=task_id, trace=trace),
            trace_recorder=trace,
            llm_client=self.llm_client,
            input_snapshot=payload.model_dump(mode="json"),
        )
        return self._snapshot_to_accepted(snapshot)

    def get_async_status(self, task_id: str) -> CNFlowAsyncStatus:
        return self._snapshot_to_status(self.tasks.get_or_raise(task_id))

    def retry_async(self, task_id: str) -> CNFlowAsyncStatus:
        return self._snapshot_to_status(self.tasks.retry(task_id))

    def cancel_async(self, task_id: str) -> CNFlowAsyncStatus:
        return self._snapshot_to_status(self.tasks.cancel(task_id))

    @staticmethod
    def _snapshot_to_accepted(snapshot: TaskSnapshot) -> CNFlowAsyncAccepted:
        return CNFlowAsyncAccepted(
            task_id=snapshot.task_id,
            module=snapshot.module,
            state=snapshot.state,
            attempts=snapshot.attempts,
            max_attempts=snapshot.max_attempts,
        )

    @staticmethod
    def _snapshot_to_status(snapshot: TaskSnapshot) -> CNFlowAsyncStatus:
        result = CNFlowResult.model_validate(snapshot.result) if snapshot.result is not None else None
        return CNFlowAsyncStatus(
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


def _wrap_canonical_result(
    payload: CNFlowRequest,
    result: US14117Result,
    lossy_fields: list[str],
) -> CNFlowResult:
    risk_level = {"RED": "HIGH", "YELLOW": "MEDIUM", "GREEN": "LOW"}.get(
        result.overall_traffic_light,
        "MEDIUM",
    )
    risk_items = [
        CNFlowRiskItem(
            risk_id=hit.rule_id,
            risk_level=risk_level,
            title=hit.rule_name,
            basis=hit.section_ref,
            recommendation="按统一 EO 14117 规则结果处理并留存证据。",
        )
        for hit in result.rule_hits
        if hit.hit
    ]
    return CNFlowResult(
        report_path=result.output_files.get("docx", result.report_path),
        output_files=result.output_files,
        company_name=payload.company_name,
        risk_level=risk_level,
        risk_items=risk_items,
        chapters=[
            CNFlowChapter(
                chapter_no=chapter.chapter_no,
                title=chapter.title,
                content=chapter.content,
                citations=chapter.citations,
                risk_level=risk_level,
            )
            for chapter in result.chapters
        ],
        consistency_issues=result.consistency_issues
        + [f"compatibility_lossy_field: {field}" for field in lossy_fields],
        attachment_notes=result.attachment_notes,
    )
