"""L1 Platform base model — Trace / Audit layer.

Every significant decision the platform makes — rule hit, Agent inference,
evidence binding, report-repair action — produces a TraceEvent.  Together
these events form an auditable chain from raw input to final conclusion.

Two-layer design:
  - Audit layer (always on)  → persisted to database, queryable, ~hundreds of KB
  - Debug layer (opt-in)     → persisted to filesystem, full prompt/response, ~MB per run
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from backend.core.time import utc_now_iso

# ── Utility (kept for backward compatibility with pipeline.py) ────────────

def dump_model_list(items: list[Any]) -> list[dict[str, Any]]:
    """Serialize a list of Pydantic models or raw objects to dicts.

    Used by WorkflowPipeline's TraceRecorder to snapshot intermediate outputs.
    """
    return [item.model_dump() if hasattr(item, "model_dump") else item for item in items]


# ── Enumerations ──────────────────────────────────────────────────────────

TraceStep = Literal[
    "raw_input",
    "document_parsing",
    "path_diagnosis",
    "fact_extraction",
    "agent:fact_extraction",
    "agent:data_classification",
    "agent:legal_grounding",
    "agent:clause_review",
    "agent:risk_reasoning",
    "agent:remediation",
    "agent:qa_alignment",
    "rule_engine",
    "issue_building",
    "evidence_grounding",
    "writing_plan",
    "report_generation",
    "qa_check",
    "repair",
    "render",
]

TraceLayer = Literal["audit", "debug"]


# ── Core models ───────────────────────────────────────────────────────────

class TraceEvent(BaseModel):
    """A single recorded step in the platform's decision-making process.

    Audit-layer events omit `prompt`, `full_response`, and `rag_details`;
    those fields are populated only when the debug layer is active.
    """

    event_id: str = Field(min_length=1, description="Unique event identifier")
    sequence: int = Field(ge=0, description="Order within this run")
    step: TraceStep = Field(description="Which pipeline stage this event belongs to")
    layer: TraceLayer = Field(default="audit")

    # ── Timestamps ──
    started_at: str = Field(default="")
    duration_ms: int = Field(default=0, ge=0)

    # ── What happened ──
    inputs_summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Key inputs to this step (not full content for audit layer)",
    )
    outputs_summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Key outputs from this step (counts, IDs, conclusions)",
    )

    # ── Model metadata (audit layer) ──
    model_used: str | None = Field(
        default=None,
        description="LLM model name and version",
    )
    prompt_version: str | None = Field(
        default=None,
        description="Git SHA or version tag of the prompt used",
    )

    # ── Debug layer only ──
    prompt: str | None = Field(
        default=None,
        description="FULL prompt sent to LLM (debug layer only)",
    )
    full_response: str | None = Field(
        default=None,
        description="FULL response received from LLM (debug layer only)",
    )
    token_count: dict[str, int] = Field(
        default_factory=dict,
        description="input/output/total token counts (debug layer only)",
    )
    rag_details: dict[str, Any] = Field(
        default_factory=dict,
        description="RAG query, hit count, selection rationale (debug layer only)",
    )

    # ── Status ──
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    fallback_used: bool = Field(
        default=False,
        description="Was the primary path (e.g. LLM) unavailable and a fallback used?",
    )


class TraceManifest(BaseModel):
    """Aggregated audit trail for a single module run.

    The manifest provides the ordered event list plus a summary that lets
    auditors and developers answer four questions:

      1. Why did the system make this judgment?
      2. Which user facts did it rely on?
      3. Which regulations / clauses / document excerpts?
      4. Which conclusions are certain, which are inferred, which need human review?
    """

    run_id: str = Field(min_length=1, description="Unique run identifier")
    module: str = Field(min_length=1)
    created_at: str = Field(default_factory=utc_now_iso)
    jurisdiction: str = Field(default="")

    # ── Version snapshot ──
    model_version: str = Field(default="")
    prompt_version: str = Field(default="")
    regulation_library_version: str = Field(default="")

    # ── Events ──
    events: list[TraceEvent] = Field(default_factory=list)

    # ── Summary counters ──
    total_duration_ms: int = 0
    total_llm_calls: int = 0
    total_tokens: int = 0
    agent_calls: int = 0
    fallback_count: int = 0
    error_count: int = 0

    def audit_summary(self) -> str:
        """Return a human-readable audit summary suitable for the report appendix."""
        lines = [
            f"本次生成链路审计摘要",
            f"  运行标识: {self.run_id}",
            f"  模块: {self.module}",
            f"  法域: {self.jurisdiction}",
            f"  模型版本: {self.model_version or 'N/A'}",
            f"  Prompt 版本: {self.prompt_version or 'N/A'}",
            f"  法规库版本: {self.regulation_library_version or 'N/A'}",
            f"  总耗时: {self.total_duration_ms}ms",
            f"  LLM 调用: {self.total_llm_calls} 次 ({self.total_tokens} tokens)",
            f"  Agent 调用: {self.agent_calls} 次",
            f"  降级次数: {self.fallback_count}",
            f"  错误次数: {self.error_count}",
        ]
        return "\n".join(lines)

    def export_for_report(self) -> dict[str, Any]:
        """Export audit-layer events only, suitable for inclusion in report artefacts."""
        return {
            "run_id": self.run_id,
            "module": self.module,
            "jurisdiction": self.jurisdiction,
            "created_at": self.created_at,
            "summary": self.audit_summary(),
            "events": [
                {
                    "step": e.step,
                    "inputs_summary": e.inputs_summary,
                    "outputs_summary": e.outputs_summary,
                    "warnings": e.warnings,
                    "fallback_used": e.fallback_used,
                }
                for e in self.events
                if e.layer == "audit"
            ],
        }
