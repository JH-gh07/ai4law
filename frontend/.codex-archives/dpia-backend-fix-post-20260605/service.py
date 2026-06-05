"""DPIA service — full WorkflowPipeline + 9-agent orchestration for GDPR DPIA draft generation.

Agent pipeline (per doc/tmp/dpia Section 13):
  DPIARequest → DPIAFactBuilder → DPIANeedDetector(rule) → DPIA Need Agent →
  Processing Activity Agent → Necessity & Proportionality Agent →
  Risk Assessment Agent → Mitigation Mapping Agent → DPO/Prior Consultation Agent →
  Legal Grounding + Citation Builder → GenerationBasisPack →
  External DPIA Draft Agent → Internal Review Agent → Consistency/Repair Agent →
  Repair → Renderer

Architecture principle:
- Rule layer: base facts, trigger signals, hard thresholds
- Agent layer: reasoning, explanation, structured judgment
- Renderer: docx/md/json/xlsx/zip output
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from backend.common.runtime.module_run import finalize_run, prepare_run
from backend.common.tasks.manager import InMemoryTaskManager, TaskSnapshot
from backend.common.trace.recorder import TraceRecorder
from backend.common.trace.thoughts import summarize_agent_output
from backend.common.workflow import GenerationContextPack, WorkflowPipeline

from backend.modules.dpia.agents import create_dpia_agents, DPIAAgentBase
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
    DPIANeedAssessment,
    DPIANeedAgentOutput,
    DPIAResult,
    DPIARequest,
    ProcessingActivityPack,
    NecessityFindings,
    RiskMatrix,
    MitigationPlan,
    DPODecisionPack,
    InternalReviewOutput,
    ConsistencyReport,
)

if TYPE_CHECKING:
    from backend.common.llm.client import LLMClient

_NO_LLM = object()


class DPIAService:
    """Full DPIA draft generation service using WorkflowPipeline + 9 agents."""

    def __init__(self, llm_client: "LLMClient | None" = _NO_LLM) -> None:
        if llm_client is _NO_LLM:
            from backend.core.settings import get_settings
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
        self._agents: dict[str, DPIAAgentBase] | None = None

    @property
    def agents(self) -> dict[str, DPIAAgentBase]:
        if self._agents is None:
            self._agents = create_dpia_agents(self.llm_client)
        return self._agents

    # ── Main pipeline ──

    def generate_report(
        self,
        payload: DPIARequest,
        *,
        task_id: str | None = None,
        trace: TraceRecorder | None = None,
    ) -> DPIAResult:
        run_task_id = task_id or str(uuid.uuid4())
        trace, token = prepare_run(module="dpia", task_id=run_task_id, trace=trace)

        if trace:
            trace.record("thought", {"summary": "路径判断：基于项目类型和触发理由确定 DPIA 评估框架"})

        try:
            # Phase 1: Profile + Facts + Need Detection (rule layer)
            profile = self.extractor.extract(payload)
            trace.record("profile_extracted", profile.model_dump())

            need_assessment_raw = self.need_detector.evaluate(payload)
            trace.record("need_detection_rule", need_assessment_raw.model_dump())

            facts = build_dpia_facts(payload, profile, need_assessment_raw)
            trace.record("facts_built", {"count": len(facts)})

            # ── Agent 1: DPIA Need Agent ──
            rule_signals = {
                "automated_decision_making": payload.automated_decision_making,
                "large_scale_processing": payload.large_scale_processing,
                "special_category_inference": payload.special_category_data,
                "systematic_monitoring": payload.systematic_monitoring,
                "new_technology": payload.new_technology,
                "vulnerable_subjects": payload.vulnerable_data_subjects,
                "data_matching": payload.data_matching,
                "rights_impact": bool(payload.dpia_trigger_reasons),
            }
            need_agent_result = self.agents["dpia_need"].run(
                project_profile={
                    "project_name": payload.project_name,
                    "project_goal": payload.project_goal,
                    "data_categories": payload.data_categories,
                    "data_subject_count": payload.data_subject_count,
                },
                rule_signals=rule_signals,
                legal_candidates=["GDPR Article 35", "WP29 WP248 rev.01"],
            )
            dpia_need_output = DPIANeedAgentOutput(**need_agent_result)
            trace.record("agent_dpia_need", dpia_need_output.model_dump())
            if trace:
                thought = summarize_agent_output("DPIA 触发判定", need_agent_result)
                trace.record("thought", {"summary": thought})

            # ── Agent 2: Processing Activity Agent ──
            proc_result = self.agents["processing_activity"].run(
                raw_inputs={
                    "data_flow": payload.processing_flow_description,
                    "data_types": payload.data_categories,
                    "data_subject_categories": payload.data_subject_categories,
                    "retention": payload.retention_period,
                    "cross_border": payload.transfer_destination if payload.cross_border_transfer else "",
                    "project_goal": payload.project_goal,
                },
                attachments=[{"type": "profile", "summary": f"Special category: {payload.special_category_data}"}],
            )
            proc_pack = ProcessingActivityPack(**proc_result)
            trace.record("agent_processing_activity", proc_pack.model_dump())
            if trace:
                thought = summarize_agent_output("DPIA 处理活动描述", proc_result)
                trace.record("thought", {"summary": thought})

            # Phase 2: RAG + Issues + Evidence (rule layer)
            regulations = self.retriever.search(profile)
            trace.record("retrieval_hits", {"count": len(regulations)})

            attachment_notes = _attachment_notes_from_profile(profile)
            issues = build_dpia_issues(facts, need_assessment_raw, regulations, attachment_notes)
            trace.record("issues_built", {"count": len(issues)})

            issues, evidence_chain = build_dpia_evidence(facts, issues, regulations, need_assessment_raw)
            trace.record("evidence_built", {"count": len(evidence_chain)})

            # ── Agent 3: Necessity & Proportionality Agent ──
            nec_result = self.agents["necessity_proportionality"].run(
                project_goal=payload.project_goal,
                processing_activity_pack=proc_pack.model_dump(),
                lawful_basis=payload.lawful_basis,
                data_categories=payload.data_categories,
            )
            nec_findings = NecessityFindings(**nec_result)
            trace.record("agent_necessity_proportionality", nec_findings.model_dump())
            if trace:
                thought = summarize_agent_output("DPIA 必要性与相称性", nec_result)
                trace.record("thought", {"summary": thought})

            # ── Agent 4: Risk Assessment Agent ──
            risk_result = self.agents["risk_assessment"].run(
                dpia_need_pack=dpia_need_output.model_dump(),
                processing_activity_pack=proc_pack.model_dump(),
                necessity_findings=nec_findings.model_dump(),
                user_identified_risks=[r.risk_description for r in (payload.identified_risks or [])],
                legal_grounding=["GDPR_ART35", "GDPR_ART22"],
            )
            risk_matrix = RiskMatrix(**risk_result)
            trace.record("agent_risk_assessment", risk_matrix.model_dump())
            if trace:
                thought = summarize_agent_output("DPIA 风险评估", risk_result)
                trace.record("thought", {"summary": thought})

            # ── Agent 5: Mitigation Mapping Agent ──
            user_measures = [m.description for m in (payload.mitigation_measures or [])]
            risk_dicts = [r.model_dump() for r in risk_matrix.risk_matrix]
            mit_result = self.agents["mitigation_mapping"].run(
                risk_matrix=risk_dicts,
                user_measures=user_measures,
            )
            mit_plan = MitigationPlan(**mit_result)
            trace.record("agent_mitigation_mapping", mit_plan.model_dump())
            if trace:
                thought = summarize_agent_output("DPIA 缓解措施映射", mit_result)
                trace.record("thought", {"summary": thought})

            # ── Agent 6: DPO / Prior Consultation Agent ──
            mit_dicts = [m.model_dump() for m in mit_plan.mitigation_plan]
            remaining_high = [
                entry.risk_id for entry in mit_plan.mitigation_plan
                if entry.residual_risk == "HIGH"
            ]
            dpo_result = self.agents["dpo_consultation"].run(
                risk_matrix=risk_dicts,
                mitigation_plan=mit_dicts,
                dpo_opinion=payload.dpo_opinion,
                remaining_high_risks=remaining_high,
            )
            dpo_pack = DPODecisionPack(**dpo_result)
            trace.record("agent_dpo_consultation", dpo_pack.model_dump())
            if trace:
                thought = summarize_agent_output("DPIA DPO咨询", dpo_result)
                trace.record("thought", {"summary": thought})

            # Phase 3: Legal Grounding + Generation Basis + Context Pack
            need_diagnosis_dict = {
                "dpia_required": dpia_need_output.dpia_required,
                "trigger_reasons": dpia_need_output.trigger_reasons,
                "legal_basis": dpia_need_output.legal_basis_refs,
                "prior_consultation_possible": dpo_pack.prior_consultation_recommended,
                "reasoning": dpia_need_output.draft_text,
            }
            trace.record("need_diagnosis_enriched", need_diagnosis_dict)

            legal_grounding, case_grounding = build_dpia_legal_grounding(
                issues=issues, facts=facts, regulations=regulations, per_issue_rag=None,
            )
            writing_strategy = build_writing_strategy(issues=issues)

            # Enrich generation basis with all agent outputs
            gen_basis = build_generation_basis_pack(
                task_id=run_task_id,
                facts=facts,
                issues=issues,
                evidence_chain=evidence_chain,
                regulations=regulations,
                attachment_notes=attachment_notes,
                need_assessment=need_diagnosis_dict,
                legal_grounding=legal_grounding,
                writing_strategy=writing_strategy,
            )
            # Inject agent outputs into generation basis
            gen_basis["dpia_need_pack"] = dpia_need_output.model_dump()
            gen_basis["processing_activity_pack"] = proc_pack.model_dump()
            gen_basis["necessity_findings"] = nec_findings.model_dump()
            gen_basis["risk_matrix"] = risk_matrix.model_dump()
            gen_basis["mitigation_plan"] = mit_plan.model_dump()
            gen_basis["dpo_decision_pack"] = dpo_pack.model_dump()

            regulation_dicts = [hit.model_dump() for hit in regulations]
            context_pack = GenerationContextPack(
                module_key="dpia",
                request_id=run_task_id,
                facts=facts,
                diagnosis_result=need_diagnosis_dict,
                regulations=regulation_dicts,
                issues=issues,
                evidence_chain=evidence_chain,
                path_warning=None,
                risk_summary={
                    "dpia_required": dpia_need_output.dpia_required,
                    "prior_consultation_possible": dpo_pack.prior_consultation_recommended,
                    "high_risk_count": sum(1 for r in risk_matrix.risk_matrix if r.overall_level == "HIGH"),
                },
                attachment_notes=attachment_notes,
                output_requirements={"chapter_keys": DPIA_CHAPTER_KEYS},
                legal_grounding=legal_grounding,
                case_grounding=case_grounding,
                writing_strategy=writing_strategy,
                generation_basis_pack=gen_basis,
            )
            trace.record("context_pack_built", {"has_agent_outputs": True})

            # ── Agent 7: External DPIA Draft Agent ──
            chapters = self.agents["external_draft"].run(
                generation_basis_pack=gen_basis,
                writing_strategy=writing_strategy,
            )
            # Convert to DPIAChapterContent format
            from backend.modules.dpia.schema import DPIAChapterContent
            dpia_chapters: list[DPIAChapterContent] = []
            for ch in chapters:
                if isinstance(ch, dict):
                    dpia_chapters.append(DPIAChapterContent(
                        chapter_no=ch.get("chapter_no", len(dpia_chapters) + 1),
                        title=ch.get("title", ""),
                        content=ch.get("content", ""),
                        citations=ch.get("citations", []),
                        risk_level=ch.get("risk_level", "medium"),
                    ))
            trace.record("agent_external_draft", {"chapters": len(dpia_chapters)})
            if trace:
                thought = summarize_agent_output("DPIA 外部草拟", chapters)
                trace.record("thought", {"summary": thought})

            # ── Agent 8: Internal Review Agent ──
            user_claim_facts = [
                str(f.value) for f in facts
                if hasattr(f, "evidence_status") and f.evidence_status == "user_claim_only"
            ]
            int_review_result = self.agents["internal_review"].run(
                risk_matrix=risk_dicts,
                mitigation_plan=mit_dicts,
                dpo_decision_pack=dpo_pack.model_dump(),
                user_claim_only_facts=user_claim_facts,
                issues=[i.model_dump() for i in issues],
            )
            int_review = InternalReviewOutput(**int_review_result)
            trace.record("agent_internal_review", int_review.model_dump())
            if trace:
                thought = summarize_agent_output("DPIA 内部审查", int_review_result)
                trace.record("thought", {"summary": thought})

            # ── Agent 9: Consistency / Repair Agent ──
            known_citations = []
            for ch in dpia_chapters:
                known_citations.extend(ch.citations)
            cons_result = self.agents["consistency_repair"].run(
                draft_chapters=[ch.model_dump() for ch in dpia_chapters],
                generation_basis_pack=gen_basis,
                risk_matrix=risk_dicts,
                mitigation_plan=mit_dicts,
                dpo_decision_pack=dpo_pack.model_dump(),
                facts=[f.model_dump() for f in facts],
                known_citations=list(set(known_citations)),
            )
            cons_report = ConsistencyReport(**cons_result)
            trace.record("agent_consistency_repair", cons_report.model_dump())
            if trace:
                thought = summarize_agent_output("DPIA 一致性修复", cons_result)
                trace.record("thought", {"summary": thought})

            # Repair pass if needed
            consistency_issues: list[str] = []
            for bi in cons_report.blocking_issues:
                if isinstance(bi, dict):
                    consistency_issues.append(f"[{bi.get('check', '')}] {bi.get('finding', '')}")
            if cons_report.needs_manual_review:
                consistency_issues.append("CONSISTENCY_BLOCKED: 存在需人工复核的一致性问题")

            # Apply text repairs to chapters
            report_text = "\n".join(ch.content for ch in dpia_chapters)
            for repair in cons_report.repairs_applied:
                if isinstance(repair, dict):
                    orig = repair.get("original", "")
                    repaired = repair.get("repaired", "")
                    if orig and repaired and orig in report_text:
                        report_text = report_text.replace(orig, repaired)
                        consistency_issues.append(f"REPAIRED: {repair.get('check', '')}")

            trace.record("repair_pass", {"issues_count": len(consistency_issues)})

            # ── Output rendering ──
            manifest = trace.write_manifest()

            # Build risk matrix for result (use dict versions from risk_dicts)
            risk_items = [
                {
                    "risk_id": r.get("risk_id", ""),
                    "risk_description": r.get("description", r.get("risk_name", "")),
                    "likelihood": r.get("likelihood", "medium"),
                    "impact": r.get("impact", "medium"),
                    "risk_level": r.get("overall_level", r.get("overall_level", "medium")),
                    "affected_data_subjects": ", ".join(r.get("affected_rights", [])),
                    "risk_source": "processing_activity",
                }
                for r in risk_dicts
            ]

            mit_items = []
            for entry in mit_dicts:
                measures = entry.get("measures", [])
                if isinstance(measures, list):
                    for m in measures:
                        mit_items.append({
                            "mitigation_id": f"MIT-{len(mit_items) + 1:03d}",
                            "description": m.get("measure", str(m)) if isinstance(m, dict) else str(m),
                            "target_risk_ids": [entry.get("risk_id", "")],
                            "status": m.get("status", "planned") if isinstance(m, dict) else "planned",
                            "responsible_party": "",
                            "residual_risk_level": entry.get("residual_risk", "MEDIUM"),
                        })

            outputs = self.renderer.render(
                task_id=run_task_id,
                profile=profile,
                chapters=dpia_chapters,
                issues=issues,
                evidence_chain=evidence_chain,
                facts=facts,
                need_assessment=need_diagnosis_dict,
                legal_grounding=legal_grounding,
                writing_strategy=writing_strategy,
                generation_basis_pack=gen_basis,
                citation_registry=context_pack.citation_registry,
                trace_manifest_path=str(manifest),
            )

        finally:
            finalize_run(token)

        # Build DPIANeedAssessment for result
        need_assessment = DPIANeedAssessment(
            dpia_required=dpia_need_output.dpia_required,
            trigger_reasons=[
                t.get("type", "") if isinstance(t, dict) else str(t)
                for t in dpia_need_output.trigger_reasons
            ],
            legal_basis=dpia_need_output.legal_basis_refs,
            prior_consultation_possible=dpo_pack.prior_consultation_recommended,
            reasoning=dpia_need_output.draft_text,
        )

        return DPIAResult(
            task_id=run_task_id,
            state="COMPLETED",
            report_path=outputs.get("markdown", ""),
            output_files=outputs,
            profile=profile,
            regulations=regulations,
            chapters=dpia_chapters,
            consistency_issues=consistency_issues,
            need_assessment=need_assessment,
            risk_matrix=risk_items,
            mitigation_plan=mit_items,
            # Agent enrichment
            processing_activity_pack=proc_pack.model_dump(),
            necessity_findings=nec_findings.model_dump(),
            dpo_decision_pack=dpo_pack.model_dump(),
            internal_ai_review=int_review.model_dump(),
            consistency_report=cons_report.model_dump(),
            generation_basis_snapshot=gen_basis,
            trace_manifest_path=str(manifest),
        )

    # ── Async API ──

    def submit_async(self, payload: DPIARequest) -> DPIAAsyncAccepted:
        task_id = str(uuid.uuid4())
        trace = TraceRecorder(Path("outputs/dpia") / task_id / "trace", task_id=task_id)
        snapshot = self.tasks.submit_with_trace(
            lambda: self.generate_report(payload, task_id=task_id, trace=trace),
            trace_recorder=trace,
        )
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
