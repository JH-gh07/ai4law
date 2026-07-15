from __future__ import annotations

import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from backend.common.quality.alignment import check_cn_alignment
from backend.common.runtime.module_run import finalize_run, prepare_run
from backend.common.tasks.manager import InMemoryTaskManager, TaskSnapshot
from backend.common.trace.recorder import TraceRecorder
from backend.common.trace.thoughts import summarize_agent_output
from backend.common.citation.audit import log_citations_created
from backend.common.citation.registry import CitationRegistry
from backend.common.knowledge.v2 import RetrievalRequest
from backend.common.workflow import GenerationContextPack, WorkflowPipeline
from backend.modules.assessment.chapter_generator import AssessmentChapterGenerator
from backend.modules.assessment.citation_builder import build_citations
from backend.modules.assessment.consistency_checker import ConsistencyChecker
from backend.modules.assessment.evidence_builder import build_assessment_evidence
from backend.modules.assessment.fact_builder import build_assessment_facts
from backend.modules.assessment.generation_basis import build_generation_basis_pack
from backend.modules.assessment.issue_builder import build_assessment_issues
from backend.modules.assessment.legal_grounding import build_legal_grounding
from backend.modules.assessment.profile_extractor import ProfileExtractor
from backend.modules.assessment.repair_generator import run_repair_pass
from backend.modules.assessment.report_renderer import AssessmentReportRenderer
from backend.modules.assessment.retriever import AssessmentRetriever
from backend.modules.assessment.writing_strategy_builder import build_writing_strategy
from backend.modules.assessment.compliance_reasoning import build_compliance_reasoning
from backend.modules.diagnosis.schema import (
    DiagnosisAnswers,
    ReceiverType,
    TransferScenario,
    YesNoUnknown,
)
from backend.modules.diagnosis.service import DiagnosisService
from backend.modules.assessment.schema import (
    AssessmentAsyncAccepted,
    AssessmentAsyncStatus,
    AssessmentRequest,
    AssessmentResult,
)
from backend.modules.assessment.task_state import AssessmentTaskState

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
        self.legal_service = legal_api_service
        self.diagnosis_service = DiagnosisService()
        self.extractor = ProfileExtractor()
        self.retriever = AssessmentRetriever(legal_service=legal_api_service)
        self.generator = AssessmentChapterGenerator(llm_client=llm_client)
        self.checker = ConsistencyChecker()
        self.renderer = AssessmentReportRenderer(llm_client=llm_client)
        self.tasks = InMemoryTaskManager(module="assessment")

    def generate_report(
        self,
        payload: AssessmentRequest,
        *,
        task_id: str | None = None,
        trace: TraceRecorder | None = None,
    ) -> AssessmentResult:
        run_task_id = task_id or str(uuid.uuid4())
        active_trace, token = prepare_run(module="assessment", task_id=run_task_id, trace=trace)

        try:
            if trace:
                trace.record("status", {"summary": "开始安全自评估", "detail": {"module": "assessment", "company": getattr(payload, 'company_name', '')}})
            run_result = self._build_pipeline().run(payload=payload, task_id=run_task_id, trace=active_trace)
        finally:
            finalize_run(token)

        report_path = self._select_report_path(run_result.outputs)
        if trace:
            trace.record("final", {"summary": "安全自评估完成", "detail": {"report_path": report_path}})
        return AssessmentResult(
            task_id=run_task_id,
            state=AssessmentTaskState.COMPLETED,
            report_path=report_path,
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
            retrieve_per_issue=self._retrieve_per_issue,
            build_context_pack=self._build_context_pack,
            generate_chapters=self.generator.generate,
            check_consistency=self.checker.check_with_context,
            check_alignment=self._check_alignment,
            repair_chapters=self._repair_chapters,
            render_artifacts=self._render_outputs,
        )

    def _evaluate_diagnosis(self, payload: AssessmentRequest):
        return self.diagnosis_service.evaluate(self._to_diagnosis_answers(payload))

    @staticmethod
    def _to_yes_no_unknown(value: bool | None) -> YesNoUnknown:
        if value is True:
            return YesNoUnknown.YES
        if value is False:
            return YesNoUnknown.NO
        return YesNoUnknown.UNKNOWN

    @staticmethod
    def _infer_transfer_scenario(payload: AssessmentRequest) -> TransferScenario:
        text = " ".join(
            [
                payload.transfer_purpose or "",
                payload.industry or "",
                payload.receiver_country or "",
            ]
        ).lower()
        if any(token in text for token in ["人力", "hr", "员工", "雇员", "payroll"]):
            return TransferScenario.HR_MANAGEMENT
        if any(token in text for token in ["紧急", "emergency", "生命", "健康", "救助"]):
            return TransferScenario.EMERGENCY
        if any(token in text for token in ["法定", "监管", "司法", "执法", "compliance filing"]):
            return TransferScenario.LEGAL_DUTY
        if any(token in text for token in ["合同", "服务", "客户", "客服", "履约", "support", "crm"]):
            return TransferScenario.CONTRACT_PERFORMANCE
        return TransferScenario.OTHER

    @staticmethod
    def _infer_receiver_type(payload: AssessmentRequest) -> ReceiverType:
        recipient_info = payload.recipient_info
        if recipient_info is not None:
            relation = " ".join(
                [
                    recipient_info.relationship or "",
                    recipient_info.role or "",
                    recipient_info.name or "",
                ]
            ).lower()
            if any(token in relation for token in ["子公司", "母公司", "集团", "关联", "affiliate", "subsidiary", "group"]):
                return ReceiverType.INTRA_GROUP
        for processor in payload.downstream_processors:
            relation = " ".join([processor.name or "", processor.role or ""]).lower()
            if any(token in relation for token in ["子公司", "母公司", "集团", "关联", "affiliate", "subsidiary", "group"]):
                return ReceiverType.INTRA_GROUP
        return ReceiverType.THIRD_PARTY

    @staticmethod
    def _build_data_type_lists(payload: AssessmentRequest) -> tuple[list[str], list[str], list[str]]:
        personal_types: list[str] = []
        sensitive_types: list[str] = []
        important_types: list[str] = []
        for item in payload.data_inventory_items:
            label = item.name or item.description or "未命名数据项"
            dtype = (item.personal_info_type or "").strip().lower()
            if dtype in {"personal_information", "general"}:
                personal_types.append(label)
            elif dtype == "sensitive_personal_information":
                personal_types.append(label)
                sensitive_types.append(label)
            elif dtype == "important_data":
                important_types.append(label)
            if item.is_important_data_candidate and label not in important_types:
                important_types.append(label)
        return personal_types, sensitive_types, important_types

    def _to_diagnosis_answers(self, payload: AssessmentRequest) -> DiagnosisAnswers:
        personal_types, sensitive_types, important_types = self._build_data_type_lists(payload)
        receiver_type = self._infer_receiver_type(payload)
        scenario = self._infer_transfer_scenario(payload)
        no_personal_info = (
            payload.pii_count <= 0
            and payload.spi_count <= 0
            and not payload.contains_important_data
            and not personal_types
            and not sensitive_types
            and not important_types
        )
        return DiagnosisAnswers(
            q1_is_ciio=self._to_yes_no_unknown(payload.is_ciio),
            q2_has_important_data=(
                YesNoUnknown.YES
                if payload.contains_important_data or bool(important_types)
                else YesNoUnknown.NO
            ),
            q3_pii_count=payload.pii_count,
            q4_spi_count=payload.spi_count,
            q5_no_personal_info=YesNoUnknown.YES if no_personal_info else YesNoUnknown.NO,
            q6_scenario=scenario,
            q7_receiver_type=receiver_type,
            q8_purpose=payload.transfer_purpose,
            m1_enterprise_name=payload.company_name,
            m1_industry=payload.industry,
            m3_processes_personal_info="yes" if payload.pii_count > 0 or payload.spi_count > 0 or bool(personal_types) else "no",
            m3_personal_info_types=personal_types,
            m3_sensitive_info_types=sensitive_types,
            m3_processes_important_data="yes" if payload.contains_important_data or bool(important_types) else "no",
            m3_important_data_types=important_types,
            m4_cross_border_transfer="yes" if payload.receiver_country.strip() else "unknown",
            m4_cross_border_regions=payload.receiver_country,
            m4_entrusted_processing="yes" if payload.downstream_processors else "no",
            m5_security_measures=list(payload.security_capability.technical_measures if payload.security_capability else []),
            m5_compliance_docs=[
                *list(payload.recipient_info.security_certifications if payload.recipient_info else []),
                *list(payload.security_capability.certifications if payload.security_capability else []),
            ],
        )

    def _retrieve_per_issue(self, *, issues, profile, regulations) -> dict[str, dict]:
        """为每个 HIGH/BLOCKER issue 调用 DeliLegal search_laws + search_cases。"""
        enriched: dict[str, dict] = {}
        if not self.legal_service or not self.legal_service.enabled:
            return enriched
        for issue in issues:
            if issue.severity not in {"HIGH", "BLOCKER"}:
                continue
            query = f"{issue.title} {issue.description}"
            laws = self.legal_service.search_laws(query, size=3)
            cases = self.legal_service.search_cases(query, size=2)
            if laws or cases:
                enriched[issue.issue_id] = {"laws": laws, "cases": cases}
        return enriched

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
        retrieval_bundle = getattr(self.retriever, "last_bundle", None)
        legal_grounding_context = [
            chunk.model_dump()
            for chunk in getattr(retrieval_bundle, "legal_grounding", []) or []
        ]
        workflow_rule_context = [
            chunk.model_dump()
            for chunk in getattr(retrieval_bundle, "workflow_rules", []) or []
        ]
        template_result = self.retriever.retrieve_context(
            RetrievalRequest(
                module="cn_assessment",
                task_stage="report_generation",
                query="安全评估 模板 章节 结构",
                facts={fact.fact_id: fact.normalized_value if fact.normalized_value is not None else fact.value for fact in facts},
                environment="production",
                top_k=8,
                jurisdiction="cn",
                path="assessment",
            )
        )
        template_context = [
            chunk.model_dump()
            for chunk in template_result.bundle.templates
        ]
        legal_grounding, case_grounding = build_legal_grounding(
            issues=issues,
            facts=facts,
            regulations=regulations,
            per_issue_rag=per_issue_rag,
            legal_grounding_context=legal_grounding_context,
        )
        writing_strategy = build_writing_strategy(issues=issues)
        compliance_reasoning_items = build_compliance_reasoning(
            facts=facts,
            issues=issues,
            payload=None,
            attachment_metadata=attachment_notes,
        )
        compliance_reasoning = [item.__dict__ for item in compliance_reasoning_items]
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
            workflow_rules=workflow_rule_context,
            template_context=template_context,
            compliance_reasoning=compliance_reasoning,
        )

        # Build citation registry from pipeline data
        regulation_dicts = [hit.model_dump() for hit in regulations]
        citation_items = build_citations(
            legal_grounding=legal_grounding,
            regulations=regulation_dicts,
            issues=issues,
            facts=facts,
            evidence_chain=evidence_chain,
            case_grounding=case_grounding,
        )
        citation_registry = CitationRegistry()
        for item in citation_items:
            citation_registry.register(item)

        log_citations_created(
            [item.citation_id for item in citation_items],
            task_id=task_id,
            report_id=task_id,
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
            case_grounding=case_grounding,
            writing_strategy=writing_strategy,
            generation_basis_pack=generation_basis_pack,
            citation_registry=citation_registry,
            legal_grounding_context=legal_grounding_context,
            workflow_rule_context=workflow_rule_context,
            template_context=template_context,
            evaluation_context=compliance_reasoning,
            compliance_reasoning=compliance_reasoning,
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

    def _repair_chapters(
        self,
        *,
        chapters,
        consistency_issues: list[str],
        profile,
        context_pack,
    ) -> tuple[list, list[str], bool]:
        """Run the repair pass: fix repairable issues, re-check, block if unfixable."""
        return run_repair_pass(
            chapters=chapters,
            consistency_issues=consistency_issues,
            profile=profile,
            context_pack=context_pack,
            llm_client=self.generator.llm_client if hasattr(self.generator, 'llm_client') else None,
            max_retries=3,
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
            case_grounding=context_pack.case_grounding if context_pack else None,
            compliance_reasoning=context_pack.compliance_reasoning if context_pack else None,
            citation_registry=context_pack.citation_registry if context_pack else None,
        )

    @staticmethod
    def _select_report_path(outputs: dict[str, str]) -> str:
        for key in ("docx", "official_markdown", "internal_markdown", "markdown"):
            value = outputs.get(key)
            if isinstance(value, str) and value.strip():
                return value
        raise ValueError("Assessment renderer produced no usable report artifact.")

    def submit_async(self, payload: AssessmentRequest) -> AssessmentAsyncAccepted:
        task_id = str(uuid.uuid4())
        trace = TraceRecorder(Path("outputs/assessment") / task_id / "trace", task_id=task_id)
        snapshot = self.tasks.submit_with_trace(
            lambda: self.generate_report(payload, task_id=task_id, trace=trace),
            trace_recorder=trace,
        )
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
        mode = payload.path_check_mode
        if mode == "generate_only":
            return warning
        if mode == "warn_only":
            return warning
        if mode == "block_on_mismatch" and not payload.force_override_path:
            raise ValueError(
                f"Path mismatch: {warning}。如需继续生成安全评估报告，请设置 force_override_path=true。"
            )
        return warning


def _attachment_notes_from_profile(profile) -> list[dict[str, str]]:
    if profile.attachment_metadata:
        notes: list[dict[str, str]] = []
        for meta in profile.attachment_metadata:
            entry: dict[str, str] = {
                "source_ref": meta.get("filename", ""),
                "type": meta.get("type", "other"),
            }
            # Contract clauses (existing)
            if "contract_clauses" in meta:
                clauses = meta["contract_clauses"]
                entry["six_core_clauses_coverage"] = str(clauses.get("six_core_clauses_coverage", {}))
                entry["missing_core_clauses"] = ", ".join(clauses.get("missing_core_clauses", []))
                entry["all_covered"] = str(clauses.get("all_covered", False))
            # Certification
            if "certification" in meta:
                cert = meta["certification"]
                entry["cert_types"] = ", ".join(cert.get("cert_types_found", []))
                entry["cert_validity"] = cert.get("validity_status", "unknown")
            # Consent record
            if "consent_record" in meta:
                consent = meta["consent_record"]
                entry["consent_all_covered"] = str(consent.get("all_covered", False))
                entry["consent_missing"] = ", ".join(consent.get("missing_elements", []))
            # Audit report
            if "audit_report" in meta:
                audit = meta["audit_report"]
                entry["audit_types"] = ", ".join(audit.get("audit_types", []))
                entry["audit_scope"] = ", ".join(audit.get("scope_areas", []))
            # Data inventory
            if "data_inventory" in meta:
                inventory = meta["data_inventory"]
                present_cats = [cat for cat, found in inventory.get("data_categories", {}).items() if found]
                entry["inventory_categories"] = ", ".join(present_cats)
            # Policy document
            if "policy_doc" in meta:
                policy = meta["policy_doc"]
                entry["policy_types"] = ", ".join(policy.get("policy_types_found", []))
                entry["policy_requirements_met"] = str(policy.get("all_requirements_met", False))

            if "missing_summary" in meta:
                entry["summary"] = meta["missing_summary"]
            elif meta.get("char_count", 0) > 0:
                entry["summary"] = f"已解析 {meta['char_count']} 字符"
            notes.append(entry)
        return notes

    # Fallback to legacy string parsing
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
