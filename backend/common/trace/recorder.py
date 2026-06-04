from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── name → event_type 映射 ──────────────────────────────────────────────
_NAME_TO_EVENT_TYPE: dict[str, str] = {
    # 新事件类型（直接映射）
    "status": "status",
    "thought": "thought",
    "tool_start": "tool_start",
    "tool_result": "tool_result",
    "intermediate": "intermediate",
    "warning": "warning",
    "final": "final",
    "final_brief": "final_brief",
    # 向后兼容 — 现有 trace.record() 调用点
    "assessment_request": "status",
    "profile_extracted": "intermediate",
    "diagnosis": "thought",
    "path_validation": "warning",
    "fact_extraction": "tool_start",
    "fact_built": "intermediate",
    "regulation_retrieval": "tool_start",
    "rag_hit": "tool_result",
    "issue_built": "intermediate",
    "evidence_built": "intermediate",
    "writing_plan": "thought",
    "report_generation": "tool_result",
    "qa_check": "tool_result",
    "consistency_check": "tool_result",
    "repair": "warning",
    "render": "tool_result",
    # CPRA 特有
    "attachment_extraction_and_fact_agents": "tool_result",
    "fact_merge": "tool_result",
    "rule_engine": "tool_result",
    "legacy_fallback": "warning",
    "spi_review": "tool_result",
    "vendor_review": "tool_result",
    "attach_gap_citations": "tool_result",
    "resolve_rating": "tool_result",
    "attachment_notes": "tool_result",
    "build_context": "tool_result",
    "generate_chapters": "tool_result",
    "consistency_review": "tool_result",
    "retrieval_hits": "tool_result",
    "facts_built": "intermediate",
    "issues_built": "intermediate",
    "chapters_generated": "tool_result",
    "context_pack_built": "intermediate",
    "consistency_issues": "warning",
    "alignment_issues": "warning",
    "rule_engine_result": "tool_result",
    "rule_engine_result_raw": "tool_result",
    "need_detection_rule": "thought",
    "need_diagnosis_enriched": "thought",
    "agent_dpia_need": "thought",
    "agent_processing_activity": "intermediate",
    "agent_necessity_proportionality": "thought",
    "agent_risk_assessment": "intermediate",
    "agent_mitigation_mapping": "tool_result",
    "agent_dpo_consultation": "thought",
    "agent_external_draft": "tool_result",
    "agent_internal_review": "warning",
    "agent_consistency_repair": "warning",
    "parsed_document_raw": "intermediate",
    "transfer_chain_raw": "intermediate",
    "agent_document_structure": "tool_result",
    "agent_transfer_chain": "thought",
    "agent_clause_semantic": "tool_result",
    "agent_tia_effectiveness": "tool_result",
    "agent_evidence_review": "warning",
    "agent_remediation": "tool_result",
    "scc_request": "status",
    "path_diagnosis": "thought",
    "field_classifications": "tool_result",
    "contract_findings": "tool_result",
    "legal_basis_reviews": "tool_result",
    "evidence_verifications": "tool_result",
    "rag_plans": "thought",
    "context_block_built": "intermediate",
    "alignment_check": "warning",
    "report_review": "warning",
    "clarification": "thought",
    "explanation": "thought",
    "cn_flow_request": "status",
    "eu_scc_request": "status",
    "us_14117_request": "status",
}


@dataclass
class TraceEvent:
    seq: int
    name: str
    path: str
    created_at: str


class TraceRecorder:
    """Write step-by-step trace payloads as JSON files under a run directory."""

    def __init__(self, trace_dir: Path, task_id: str = "") -> None:
        self.trace_dir = trace_dir
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self._seq = 0
        self._events: list[TraceEvent] = []
        self._subscribers: list[Callable] = []  # Callable[[RunEvent], None]
        self._task_id = task_id

    def record(self, name: str, payload: dict[str, Any]) -> Path:
        self._seq += 1
        safe_name = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in (name or "event")).strip("_")
        filename = f"{self._seq:03d}_{safe_name}.json"
        path = self.trace_dir / filename
        to_write = {"name": name, "seq": self._seq, "created_at": _utc_now_iso(), "payload": payload}
        path.write_text(json.dumps(to_write, ensure_ascii=False, indent=2), encoding="utf-8")
        self._events.append(TraceEvent(seq=self._seq, name=name, path=str(path), created_at=to_write["created_at"]))
        # ── 新增：发布 RunEvent 给订阅者 ──
        if self._subscribers:
            from backend.common.trace.events import RunEvent
            event_type = _NAME_TO_EVENT_TYPE.get(name, "status")
            run_event = RunEvent(
                task_id=self._task_id,
                seq=self._seq,
                event_type=event_type,
                timestamp=to_write["created_at"],
                summary=payload.get("summary", name),
                detail=payload.get("detail"),
                level=payload.get("level", "audit"),
            )
            for sub in self._subscribers:
                try:
                    sub(run_event)
                except Exception:
                    pass  # 订阅者异常不影响主流程

        return path

    def subscribe(self, callback: Callable) -> None:
        """注册事件订阅者。callback 接收 RunEvent 实例。"""
        self._subscribers.append(callback)

    def write_manifest(self) -> Path:
        path = self.trace_dir / "manifest.json"
        payload = {
            "created_at": _utc_now_iso(),
            "event_count": len(self._events),
            "events": [event.__dict__ for event in self._events],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
