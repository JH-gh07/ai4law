"""CN SCC Service — full pipeline orchestration with rule engine + 9 agents.

Architecture (per doc/tmp/认证标准合同路径 Section 11):
  用户输入/上传材料
    → [资料解析层]
    → [路径诊断 Agent]  (P0)
    → [专项审查 Agent 组]  (P0+P1)
    → [规则引擎]
    → [Issue/Evidence 构建]
    → [RAG 检索规划 Agent]  (P2)
    → [报告生成]
    → [报告审稿 Agent]  (P1)
    → [输出]

Agent failures never block the pipeline — they silently fall back to rule-based results.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.common.llm.client import LLMClient
from backend.common.llm.module_generator import generate_chapter
from backend.common.quality.alignment import check_cn_alignment
from backend.common.rag.retriever import retrieve_regulations
from backend.common.render.report import (
    format_date_stamp,
    render_docx_template,
    render_markdown_template,
    safe_filename,
)
from backend.common.render.docx_comments import DocxComment, render_commented_docx
from backend.common.render.summary import attach_citations, summarize_for_slot
from backend.common.risk.scoring import risk_level
from backend.common.runtime.module_run import finalize_run, prepare_run
from backend.common.storage.file_parser import FileParser
from backend.common.tasks.manager import InMemoryTaskManager, TaskSnapshot
from backend.common.trace.recorder import TraceRecorder
from backend.common.trace.thoughts import summarize_agent_output
from backend.common.workflow import (
    EvidenceItem,
    FactItem,
    GenerationContextPack,
    IssueItem,
    WorkflowPipeline,
)

from backend.modules.scc.agents import create_scc_agents, SCCAgentBase
from backend.modules.scc.rule_engine import evaluate_hard_thresholds, determine_path
from backend.modules.scc.fact_builder import build_scc_facts
from backend.modules.scc.issue_builder import build_scc_issues
from backend.modules.scc.evidence_builder import build_scc_evidence
from backend.modules.scc.schema import (
    ClarificationResult,
    ContractFinding,
    DataFieldClassification,
    DataFieldItem,
    EvidenceVerificationItem,
    ExplanationResult,
    LegalBasisReviewItem,
    PathDiagnosisInput,
    PathDiagnosisResult,
    RAGQueryPlan,
    ReportReviewResult,
    SCCAsyncAccepted,
    SCCAsyncStatus,
    SCCChapter,
    SCCProfile,
    SCCRequest,
    SCCResult,
)


TEMPLATE_PATH = Path("doc/v2/assets/templates/3.1_scc_review_template_v0.docx")
TEMPLATE_MD = Path("doc/v2/assets/templates/3.1_scc_review_template_v0.md")

SCC_CHAPTERS = [
    "审查依据说明",
    "总体合规评级",
    "条款级问题清单",
    "修订建议与行动计划",
]


# Sentinel to distinguish "no argument passed" from "explicit None"
_NO_LLM = object()


class SCCService:
    """CN SCC compliance review service with full agent pipeline."""

    def __init__(self, llm_client: LLMClient | None = _NO_LLM) -> None:
        if llm_client is _NO_LLM:
            from backend.core.settings import get_settings
            llm_client = LLMClient(get_settings())
        self.llm_client = llm_client
        self.parser = FileParser()
        self.tasks = InMemoryTaskManager(module="scc")
        self._agents: dict[str, SCCAgentBase] | None = None

    @property
    def agents(self) -> dict[str, SCCAgentBase]:
        if self._agents is None:
            self._agents = create_scc_agents(self.llm_client)
        return self._agents

    # ── Profile building ──

    def _build_profile(self, payload: SCCRequest) -> SCCProfile:
        """Extract profile from request + parse uploaded files."""
        notes: list[str] = []
        attachment_texts: dict[str, str] = {}

        for file_path in payload.uploaded_files:
            try:
                text = self.parser.parse_text(file_path)
                excerpt = text[:160].replace(chr(10), " ")
                notes.append(f"{file_path}: {excerpt}")
                attachment_texts[file_path] = text
            except (FileNotFoundError, ValueError) as exc:
                notes.append(f"{file_path}: [parse skipped] {exc}")

        return SCCProfile(
            company_name=payload.company_name,
            receiver_name=payload.receiver_name,
            receiver_country=payload.receiver_country,
            transfer_purpose=payload.transfer_purpose,
            pii_count=payload.pii_count,
            spi_count=payload.spi_count,
            has_scc_draft=payload.has_scc_draft,
            is_ciio=payload.is_ciio,
            has_important_data=payload.has_important_data,
            legal_basis=payload.legal_basis,
            receiver_type=payload.receiver_type,
            industry=payload.industry,
            is_hr_management=payload.is_hr_management,
            is_certification_body=payload.is_certification_body,
            has_certification_material=payload.has_certification_material,
            has_exemption_material=payload.has_exemption_material,
            extracted_notes=notes,
            attachment_texts=attachment_texts,
        )

    # ── Agent execution helpers ──

    def _run_path_diagnosis(self, payload: SCCRequest) -> PathDiagnosisResult:
        """Step 1: Path Diagnosis Agent (P0) — determine the correct path."""
        diagnosis_input = PathDiagnosisInput(
            company_name=payload.company_name,
            is_ciio=payload.is_ciio,
            has_important_data=payload.has_important_data,
            pii_count=payload.pii_count,
            spi_count=payload.spi_count,
            transfer_purpose=payload.transfer_purpose,
            legal_basis=payload.legal_basis,
            receiver_type=payload.receiver_type,
            receiver_country=payload.receiver_country,
            industry=payload.industry,
            is_hr_management=payload.is_hr_management,
            is_certification_body=payload.is_certification_body,
            has_scc_draft=payload.has_scc_draft,
            has_certification_material=payload.has_certification_material,
            has_exemption_material=payload.has_exemption_material,
        )

        agent_result = self.agents["path_diagnosis"].run(diagnosis_input=diagnosis_input)
        return PathDiagnosisResult(**agent_result)

    def _run_data_classification(self, payload: SCCRequest) -> list[DataFieldClassification]:
        """Step 2: Data Classification Agent (P0) — field-level review."""
        if not payload.data_fields:
            return []

        results: list[DataFieldClassification] = []
        for field in payload.data_fields:
            agent_result = self.agents["data_classification"].run(field=field)
            results.append(DataFieldClassification(**agent_result))
        return results

    def _run_contract_review(self, payload: SCCRequest, profile: SCCProfile) -> list[ContractFinding]:
        """Step 3: Contract Review Agent (P0) — review contract terms."""
        contract_text = ""
        contract_type = "standard_contract"

        if payload.has_scc_draft and profile.attachment_texts:
            for path, text in profile.attachment_texts.items():
                if any(kw in path.lower() for kw in ["scc", "contract", "合同", "协议", "dpa"]):
                    contract_text = text
                    break
            if not contract_text:
                contract_text = list(profile.attachment_texts.values())[0]

        if payload.contract_summary:
            contract_text = (contract_text or "") + "\n\n[用户提供的合同摘要]\n" + payload.contract_summary

        agent_results = self.agents["contract_review"].run(
            contract_text=contract_text,
            contract_type=contract_type,
            receiver_country=payload.receiver_country,
            path_type="standard_contract",
            uploaded_file_names=payload.uploaded_files,
        )

        findings: list[ContractFinding] = []
        for item in agent_results:
            if isinstance(item, dict):
                findings.append(ContractFinding(**item))
        return findings

    def _run_legal_basis_review(self, payload: SCCRequest) -> list[LegalBasisReviewItem]:
        """Step 4: Legal Basis Review Agent (P1) — check legal basis arguments."""
        agent_results = self.agents["legal_basis_review"].run(
            legal_basis_list=[lb.value for lb in payload.legal_basis],
            transfer_purpose=payload.transfer_purpose,
            user_argument=payload.legal_basis_argument,
            contract_summary=payload.contract_summary,
            privacy_policy_summary=payload.privacy_policy_summary,
            employee_handbook_summary=payload.employee_handbook_summary,
            collective_agreement_summary=payload.collective_agreement_summary,
            consent_record_summary=payload.consent_record_summary,
        )

        reviews: list[LegalBasisReviewItem] = []
        for item in agent_results:
            if isinstance(item, dict):
                reviews.append(LegalBasisReviewItem(**item))
        return reviews

    def _run_evidence_verification(
        self, payload: SCCRequest, path_diagnosis: PathDiagnosisResult
    ) -> list[EvidenceVerificationItem]:
        """Step 5: Evidence Verification Agent (P1) — verify claims against evidence."""
        claims = self._extract_claims(payload, path_diagnosis)
        material_summaries = {
            "contract_summary": payload.contract_summary,
            "privacy_policy_summary": payload.privacy_policy_summary,
            "employee_handbook_summary": payload.employee_handbook_summary,
            "collective_agreement_summary": payload.collective_agreement_summary,
            "consent_record_summary": payload.consent_record_summary,
        }

        agent_results = self.agents["evidence_verification"].run(
            claims=claims,
            uploaded_materials=payload.uploaded_files,
            material_summaries=material_summaries,
        )

        verifications: list[EvidenceVerificationItem] = []
        for item in agent_results:
            if isinstance(item, dict):
                verifications.append(EvidenceVerificationItem(**item))
        return verifications

    @staticmethod
    def _extract_claims(payload: SCCRequest, path_diagnosis: PathDiagnosisResult) -> list[dict]:
        """Extract user claims from the request for evidence verification."""
        claims: list[dict] = []

        if payload.pii_count > 0:
            claims.append({"claim": f"已取得{payload.pii_count:,}名个人信息主体的同意或具备合法性基础", "category": "consent"})

        if payload.spi_count > 0:
            claims.append({"claim": f"已按敏感个人信息要求取得{payload.spi_count:,}名主体的单独同意", "category": "consent"})

        if payload.has_scc_draft:
            claims.append({"claim": "标准合同草案已按标准合同办法要求编制", "category": "contract"})

        if payload.is_hr_management:
            claims.append({"claim": "满足人力资源管理所必需的豁免条件", "category": "employee"})

        if payload.is_certification_body:
            claims.append({"claim": "接收方为中国网信部门认可的专业认证机构", "category": "certification"})

        if payload.contract_summary:
            claims.append({"claim": "合同已包含数据保护必要条款", "category": "contract"})

        if payload.privacy_policy_summary:
            claims.append({"claim": "已通过隐私政策履行告知义务", "category": "policy"})

        for lb in payload.legal_basis:
            claims.append({"claim": f"合法性基础'{lb.value}'成立", "category": "legal_basis"})

        return claims

    def _run_rag_planning(
        self, path_type: str, issues: list[IssueItem], payload: SCCRequest
    ) -> list[RAGQueryPlan]:
        """Step 6: RAG Planning Agent (P2) — plan targeted legal queries."""
        agent_results = self.agents["rag_planning"].run(
            path_type=path_type,
            issues=[i.model_dump() for i in issues],
            industry=payload.industry,
            receiver_country=payload.receiver_country,
            data_types=[f.field_name for f in payload.data_fields],
            risk_points=[i.title for i in issues[:5]],
        )

        plans: list[RAGQueryPlan] = []
        for item in agent_results:
            if isinstance(item, dict):
                plans.append(RAGQueryPlan(**item))
        return plans

    def _generate_chapters(
        self,
        profile: SCCProfile,
        context_block: str,
        citations: list[str],
        level: str,
    ) -> tuple[list[SCCChapter], list[str]]:
        """Generate PIPIA chapters via LLM."""
        chapters: list[SCCChapter] = []
        for idx, title in enumerate(SCC_CHAPTERS, start=1):
            if self.llm_client and self.llm_client.enabled:
                content = generate_chapter(
                    self.llm_client, "scc", title, context_block, citations=citations
                )
            else:
                content = f"（{title}：LLM未配置，此处为占位内容）"
            chapters.append(
                SCCChapter(
                    chapter_no=idx,
                    title=title,
                    content=content,
                    citations=citations,
                    risk_level=level,
                )
            )

        all_content = "\n".join(ch.content for ch in chapters)
        issues = self._collect_generation_issues(profile)
        return chapters, issues

    @staticmethod
    def _collect_generation_issues(profile: SCCProfile) -> list[str]:
        """Collect generation-level issues."""
        issues: list[str] = []
        if not profile.has_scc_draft:
            issues.append("No SCC draft provided; legal terms should be manually reviewed before filing.")
        if profile.pii_count >= 1_000_000:
            issues.append("PII volume reaches 1,000,000 threshold; verify whether security assessment path is required.")
        if profile.spi_count >= 10_000:
            issues.append("Sensitive personal information volume exceeds 10,000; verify route with security assessment obligations.")
        return issues

    def _run_report_review(
        self,
        report_text: str,
        facts: list[FactItem],
        issues: list[IssueItem],
        evidence_chain: list[EvidenceItem],
        regulations: list,
        path_diagnosis: PathDiagnosisResult,
    ) -> ReportReviewResult:
        """Step 7: Report Review Agent (P1) — post-generation quality audit."""
        agent_result = self.agents["report_review"].run(
            report_text=report_text,
            facts=[f.model_dump() for f in facts],
            issues=[i.model_dump() for i in issues],
            evidence=[e.model_dump() for e in evidence_chain],
            regulations=[f"{r.title}{r.article}" for r in regulations],
            path_diagnosis=path_diagnosis.model_dump(),
            risk_level="MEDIUM",
            template_sections=SCC_CHAPTERS,
        )
        return ReportReviewResult(**agent_result)

    def _run_clarification(
        self,
        facts: list[FactItem],
        issues: list[IssueItem],
        path_diagnosis: PathDiagnosisResult,
        payload: SCCRequest,
    ) -> ClarificationResult:
        """Step 8: Clarification Agent (P2) — dynamic follow-up questions."""
        agent_result = self.agents["clarification"].run(
            current_facts=[f.model_dump() for f in facts],
            missing_materials=[m for i in issues for m in i.missing_materials],
            blocking_issues=path_diagnosis.blocking_issues,
            path_confidence=path_diagnosis.confidence,
            path_diagnosis=path_diagnosis.model_dump(),
            uploaded_materials=payload.uploaded_files,
        )
        return ClarificationResult(**agent_result)

    def _run_explanation(
        self,
        trace_events: list[dict],
        facts: list[FactItem],
        issues: list[IssueItem],
        evidence_chain: list[EvidenceItem],
        regulations: list,
        path_diagnosis: PathDiagnosisResult,
        final_conclusion: str,
    ) -> ExplanationResult:
        """Step 9: Explanation Agent (P2) — human-readable reasoning chain."""
        agent_result = self.agents["explanation"].run(
            trace_events=trace_events,
            facts=[f.model_dump() for f in facts],
            issues=[i.model_dump() for i in issues],
            evidence=[e.model_dump() for e in evidence_chain],
            regulations=[f"{r.title}{r.article}" for r in regulations],
            path_diagnosis=path_diagnosis.model_dump(),
            final_report_conclusion=final_conclusion,
        )
        return ExplanationResult(**agent_result)

    # ── Main pipeline ──

    def generate_report(
        self,
        payload: SCCRequest,
        *,
        task_id: str | None = None,
        trace: TraceRecorder | None = None,
    ) -> SCCResult:
        """Execute the full CN SCC compliance review pipeline.

        Pipeline order (per documented architecture):
        1. Profile extraction
        2. Path Diagnosis Agent (P0)
        3. Data Classification Agent (P0)
        4. Contract Review Agent (P0)
        5. Legal Basis Review Agent (P1)
        6. Evidence Verification Agent (P1)
        7. Fact/Issue/Evidence building
        8. RAG Planning Agent (P2) + RAG retrieval
        9. Chapter generation
        10. Report Review Agent (P1)
        11. Clarification Agent (P2)
        12. Explanation Agent (P2)
        13. Output rendering
        """
        run_task_id = task_id or uuid.uuid4().hex
        trace, token = prepare_run(module="scc", task_id=run_task_id, trace=trace)
        try:

            if trace:
                trace.record("thought", {"summary": "路径判断：基于出口方/进口方信息和传输角色确定 SCC 审查框架"})

            trace.record("scc_request", payload.model_dump())

        # ── Phase 1: Profile extraction ──
            profile = self._build_profile(payload)
            trace.record("profile_extracted", profile.model_dump())

        # ── Phase 2: Path Diagnosis Agent (P0) ──
            path_diagnosis = self._run_path_diagnosis(payload)
            trace.record("path_diagnosis", path_diagnosis.model_dump())
            if trace:
                thought = summarize_agent_output("SCC 路径诊断", path_diagnosis)
                trace.record("thought", {"summary": thought})

        # ── Phase 3: Data Classification Agent (P0) ──
            field_classifications = self._run_data_classification(payload)
            trace.record("field_classifications", {
            "count": len(field_classifications),
            "mislabeled": sum(1 for fc in field_classifications if fc.risk in ("HIGH", "BLOCKER")),
        })
            if trace:
                thought = summarize_agent_output("SCC 数据分级分类", field_classifications)
                trace.record("thought", {"summary": thought})

        # ── Phase 4: Contract Review Agent (P0) ──
            contract_findings = self._run_contract_review(payload, profile)
            trace.record("contract_findings", {
            "count": len(contract_findings),
            "high_severity": sum(1 for cf in contract_findings if cf.severity in ("HIGH", "BLOCKER")),
        })
            if trace:
                thought = summarize_agent_output("SCC 合同条款审查", contract_findings)
                trace.record("thought", {"summary": thought})

        # ── Phase 5: Legal Basis Review Agent (P1) ──
            legal_basis_reviews = self._run_legal_basis_review(payload)
            trace.record("legal_basis_reviews", {
            "count": len(legal_basis_reviews),
            "weak_or_worse": sum(1 for lbr in legal_basis_reviews if lbr.status in ("weak", "insufficient_evidence", "not_recommended")),
        })
            if trace:
                thought = summarize_agent_output("SCC 合法性审查", legal_basis_reviews)
                trace.record("thought", {"summary": thought})

        # ── Phase 6: Evidence Verification Agent (P1) ──
            evidence_verifications = self._run_evidence_verification(payload, path_diagnosis)
            trace.record("evidence_verifications", {
            "count": len(evidence_verifications),
            "user_claim_only": sum(1 for ev in evidence_verifications if ev.evidence_status == "user_claim_only"),
        })
            if trace:
                thought = summarize_agent_output("SCC 证据验证", evidence_verifications)
                trace.record("thought", {"summary": thought})

        # ── Phase 7: Facts / Issues / Evidence building ──
            facts = build_scc_facts(payload, profile)
            trace.record("facts_built", {"count": len(facts)})

        # Build issues from agent results
            issues = build_scc_issues(
            facts=facts,
            path_diagnosis=path_diagnosis,
            field_classifications=field_classifications,
            legal_basis_reviews=legal_basis_reviews,
            contract_findings=contract_findings,
            evidence_verifications=[ev.model_dump() for ev in evidence_verifications],
            regulations=[],
        )
            trace.record("issues_built", {"count": len(issues)})

        # RAG retrieval for each issue
            rag_plans = self._run_rag_planning(path_diagnosis.recommended_path, issues, payload)
            trace.record("rag_plans", {"count": len(rag_plans)})
            if trace:
                thought = summarize_agent_output("SCC 检索规划", rag_plans)
                trace.record("thought", {"summary": thought})

            all_regs = []
            all_citations: list[str] = []
            for plan in rag_plans:
                for query in plan.queries[:2]:
                    regs = retrieve_regulations(query, top_k=3, jurisdiction="cn", path="scc")
                    all_regs.extend(regs)
                    all_citations.extend(f"{r.title}{r.article}" for r in regs)
        # Deduplicate citations
            all_citations = list(dict.fromkeys(all_citations))
            trace.record("retrieval_hits", {"count": len(all_regs), "citations": all_citations})

        # Rebuild issues with regulations
            issues = build_scc_issues(
            facts=facts,
            path_diagnosis=path_diagnosis,
            field_classifications=field_classifications,
            legal_basis_reviews=legal_basis_reviews,
            contract_findings=contract_findings,
            evidence_verifications=[ev.model_dump() for ev in evidence_verifications],
            regulations=all_regs,
        )

        # Build evidence
            issues, evidence_chain = build_scc_evidence(facts, issues, all_regs, path_diagnosis)
            trace.record("evidence_built", {"count": len(evidence_chain)})

        # ── Phase 8: RAG context for chapter generation ──
            reg_snippet = "\n".join(
            f"- {r.title}{r.article}：{(r.content or '')[:120]}"
            for r in all_regs[:8]
        ) or "（暂无检索到相关法条）"

            severity_levels = {issue.severity for issue in issues}
            if "BLOCKER" in severity_levels:
                level = "高风险"
            elif "HIGH" in severity_levels:
                level = "高风险"
            elif "MEDIUM" in severity_levels:
                level = "部分合规"
            else:
                level = "基本合规"

            context_block = self._build_context_block(profile, path_diagnosis, issues, evidence_chain, reg_snippet, level)
            trace.record("context_block_built", {"length": len(context_block)})

        # ── Phase 9: Chapter generation ──
            chapters, gen_issues = self._generate_chapters(profile, context_block, all_citations, level)
            trace.record("chapters_generated", {"count": len(chapters)})

            report_text = "\n".join(ch.content for ch in chapters)

        # Alignment check
            alignment_issues = check_cn_alignment(report_text, receiver_country=profile.receiver_country)
            if alignment_issues:
                gen_issues.extend(alignment_issues)
            trace.record("alignment_check", {"issues": alignment_issues})

        # ── Phase 10: Report Review Agent (P1) ──
            report_review = self._run_report_review(report_text, facts, issues, evidence_chain, all_regs, path_diagnosis)
            trace.record("report_review", report_review.model_dump())
            if trace:
                thought = summarize_agent_output("SCC 报告审查", report_review)
                trace.record("thought", {"summary": thought})

        # ── Phase 11: Clarification Agent (P2) ──
            clarification = self._run_clarification(facts, issues, path_diagnosis, payload)
            trace.record("clarification", clarification.model_dump())
            if trace:
                thought = summarize_agent_output("SCC 澄清补全", clarification)
                trace.record("thought", {"summary": thought})

        # ── Phase 12: Explanation Agent (P2) ──
        # Collect trace events
            trace_events = [
            {"event": name, "payload": {}}
            for name in ["scc_request", "profile_extracted", "path_diagnosis",
                         "field_classifications", "contract_findings", "legal_basis_reviews",
                         "evidence_verifications", "facts_built", "issues_built",
                         "rag_plans", "retrieval_hits", "context_block_built",
                         "chapters_generated", "report_review"]
        ]
            explanation = self._run_explanation(
            trace_events, facts, issues, evidence_chain, all_regs, path_diagnosis,
            final_conclusion=chapters[1].content[:500] if len(chapters) > 1 else "",
        )
            trace.record("explanation", explanation.model_dump())
            if trace:
                thought = summarize_agent_output("SCC 说明生成", explanation)
                trace.record("thought", {"summary": thought})

        # ── Phase 13: Output rendering ──
            manifest = trace.write_manifest()
            date_stamp = format_date_stamp()
            safe_company = safe_filename(payload.company_name)
            output_dir = Path("outputs/scc") / run_task_id / "outputs"
            output_dir.mkdir(parents=True, exist_ok=True)
            md_output = output_dir / f"{safe_company}_SCC_合规审查报告_草案_{date_stamp}.md"
            docx_output = output_dir / f"{safe_company}_SCC_合规审查报告_草案_{date_stamp}.docx"

            mapping = _build_scc_template_mapping(
            profile, chapters, issues, evidence_chain, date_stamp,
            alignment_warning="；".join(alignment_issues) if alignment_issues else None,
        )
            render_markdown_template(md_output, TEMPLATE_MD, mapping)
            render_docx_template(docx_output, TEMPLATE_PATH, mapping)

            annotated_docx_output = self._render_annotated_docx(payload, issues, evidence_chain, date_stamp, output_dir=output_dir)
            output_files = {"markdown": str(md_output), "docx": str(docx_output)}
            if annotated_docx_output is not None:
                output_files["annotated_docx"] = str(annotated_docx_output)

        # Collect all consistency issues
            all_consistency_issues = gen_issues + alignment_issues
            if report_review.review_status != "pass":
                for problem in report_review.problems:
                    all_consistency_issues.append(f"[{problem.type}] {problem.text}")

            return SCCResult(
                report_path=str(docx_output),
                output_files=output_files,
                profile=profile,
                chapters=chapters,
                consistency_issues=all_consistency_issues,
                path_diagnosis=path_diagnosis,
                field_classifications=field_classifications,
                legal_basis_reviews=legal_basis_reviews,
                contract_findings=contract_findings,
                evidence_verifications=evidence_verifications,
                report_review=report_review,
                clarification=clarification,
                explanation=explanation,
                facts=[f.model_dump() for f in facts],
                issues=[i.model_dump() for i in issues],
                evidence_chain=[e.model_dump() for e in evidence_chain],
                rag_query_plans=rag_plans,
                trace_manifest_path=str(manifest),
            )
        finally:
            finalize_run(token)

    def _build_context_block(
        self,
        profile: SCCProfile,
        path_diagnosis: PathDiagnosisResult,
        issues: list[IssueItem],
        evidence_chain: list[EvidenceItem],
        reg_snippet: str,
        level: str,
    ) -> str:
        """Build rich context block for LLM chapter generation."""
        issue_lines = "\n".join(
            f"- [{i.severity}] {i.title}: {i.description[:100]}"
            for i in issues[:10]
        ) if issues else "（无已识别问题）"

        evidence_lines = "\n".join(
            f"- {e.claim}: {e.conclusion}（置信度{e.confidence}）"
            for e in evidence_chain[:8]
        ) if evidence_chain else "（无证据链）"

        return (
            f"【企业信息】\n"
            f"- 企业名称：{profile.company_name}\n"
            f"- 境外接收方：{profile.receiver_name}（{profile.receiver_country}）\n"
            f"- 出境目的：{profile.transfer_purpose}\n"
            f"- 个人信息规模：{profile.pii_count:,}人\n"
            f"- 敏感个人信息规模：{profile.spi_count:,}人\n"
            f"- CIIO：{'是' if profile.is_ciio else '否'}\n"
            f"- 重要数据：{'是' if profile.has_important_data else '否'}\n"
            f"- 是否已有标准合同草案：{'是' if profile.has_scc_draft else '否'}\n"
            f"- 风险等级：{level}\n"
            f"- 已上传文件摘要：{'; '.join(profile.extracted_notes[:3]) if profile.extracted_notes else '未提供'}\n"
            f"\n【路径诊断】\n"
            f"- 推荐路径：{path_diagnosis.recommended_path}\n"
            f"- 置信度：{path_diagnosis.confidence}\n"
            f"- 理由：{path_diagnosis.rationale}\n"
            f"- 阻断项：{'；'.join(path_diagnosis.blocking_issues[:5]) if path_diagnosis.blocking_issues else '无'}\n"
            f"\n【已识别问题清单】\n{issue_lines}\n"
            f"\n【证据链】\n{evidence_lines}\n"
            f"\n【法规参考】\n{reg_snippet}\n"
        )

    def _render_annotated_docx(
        self,
        payload: SCCRequest,
        issues: list[IssueItem],
        evidence_chain: list[EvidenceItem],
        date_stamp: str,
        *,
        output_dir: Path,
    ) -> Path | None:
        """Render annotated DOCX with review comments."""
        source_docx = self._pick_source_docx(payload.uploaded_files)
        if source_docx is None:
            return None

        safe_company = safe_filename(payload.company_name)
        output_path = output_dir / f"{safe_company}_SCC_批注修订版_{date_stamp}.docx"

        comments: list[DocxComment] = []
        for issue in issues:
            comments.append(DocxComment(
                label=issue.category,
                location=issue.title[:50],
                quote=issue.description[:100],
                risk_level=issue.severity,
                basis="；".join(issue.rule_refs[:3]) if issue.rule_refs else "内部规则引擎",
                risk_analysis=issue.description,
                suggestion=issue.recommended_action,
            ))

        return render_commented_docx(source_docx, output_path, comments)

    @staticmethod
    def _pick_source_docx(uploaded_files: list[str]) -> Path | None:
        for raw_path in uploaded_files:
            path = Path(raw_path)
            if path.suffix.lower() == ".docx" and path.exists():
                return path
        return None

    # ── Async API ──

    def submit_async(self, payload: SCCRequest) -> SCCAsyncAccepted:
        task_id = uuid.uuid4().hex
        trace = TraceRecorder(Path("outputs/scc") / task_id / "trace", task_id=task_id)
        snapshot = self.tasks.submit_with_trace(
            lambda: self.generate_report(payload, task_id=task_id, trace=trace),
            trace_recorder=trace,
        )
        return self._snapshot_to_accepted(snapshot)

    def get_async_status(self, task_id: str) -> SCCAsyncStatus:
        snapshot = self.tasks.get_or_raise(task_id)
        return self._snapshot_to_status(snapshot)

    def retry_async(self, task_id: str) -> SCCAsyncStatus:
        snapshot = self.tasks.retry(task_id)
        return self._snapshot_to_status(snapshot)

    def cancel_async(self, task_id: str) -> SCCAsyncStatus:
        snapshot = self.tasks.cancel(task_id)
        return self._snapshot_to_status(snapshot)

    @staticmethod
    def _snapshot_to_accepted(snapshot: TaskSnapshot) -> SCCAsyncAccepted:
        return SCCAsyncAccepted(
            task_id=snapshot.task_id,
            module=snapshot.module,
            state=snapshot.state,
            attempts=snapshot.attempts,
            max_attempts=snapshot.max_attempts,
        )

    @staticmethod
    def _snapshot_to_status(snapshot: TaskSnapshot) -> SCCAsyncStatus:
        result = None
        if snapshot.result is not None:
            result = SCCResult.model_validate(snapshot.result)
        return SCCAsyncStatus(
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


# ── Template mapping ──

def _build_scc_template_mapping(
    profile: SCCProfile,
    chapters: list[SCCChapter],
    issues: list[IssueItem],
    evidence_chain: list[EvidenceItem],
    date_stamp: str,
    alignment_warning: str | None = None,
) -> dict[str, str]:
    def pick(title: str) -> str:
        for chapter in chapters:
            if chapter.title == title:
                return chapter.content
        return ""

    citations: list[str] = []
    for chapter in chapters:
        if chapter.citations:
            citations = chapter.citations
            break

    rating = _resolve_rating(issues)
    executive_summary = summarize_for_slot(pick("总体合规评级"), max_sentences=2, max_chars=220)
    if not executive_summary or executive_summary == "未提供":
        executive_summary = (
            f"本次对 {profile.company_name} 的SCC草案进行合规审查，当前总体评级为{rating}，"
            "建议按高风险条款优先整改后再进入备案流程。"
        )
    revision_recommendations = summarize_for_slot(pick("修订建议与行动计划"), max_sentences=2, max_chars=260)
    if not revision_recommendations or revision_recommendations == "未提供":
        revision_recommendations = "请按问题清单逐条修订，形成版本差异说明并留存审查记录。"

    legal_references = "\n".join(f"- {item}" for item in citations) or "- 未检索到"
    issue_table = _format_issue_table(issues)

    if alignment_warning:
        executive_summary = f"【输入对齐告警】{alignment_warning}\n{executive_summary}".strip()

    contract_name = (
        Path(profile.extracted_notes[0].split(":", 1)[0]).name
        if profile.extracted_notes
        else f"{profile.company_name}_SCC草案"
    )
    contract_version = "draft-v1" if profile.has_scc_draft else "未提供"

    return {
        "contract_name": contract_name,
        "contract_version": contract_version,
        "review_date": date_stamp,
        "legal_references": legal_references,
        "overall_rating": rating,
        "executive_summary": attach_citations(executive_summary, citations),
        "issue_table": issue_table,
        "revision_recommendations": attach_citations(revision_recommendations, citations),
    }


def _resolve_rating(issues: list[IssueItem]) -> str:
    levels = {issue.severity for issue in issues}
    if "BLOCKER" in levels or "HIGH" in levels:
        return "高风险"
    if "MEDIUM" in levels:
        return "部分合规"
    return "基本合规"


def _format_issue_table(issues: list[IssueItem]) -> str:
    header = (
        "| 问题ID | 问题标题 | 严重度 | 类别 | 建议措施 | 缺失材料 |\n"
        "| --- | --- | --- | --- | --- | --- |"
    )
    rows: list[str] = [header]
    for item in issues[:20]:
        row = "| {id} | {title} | {severity} | {category} | {action} | {missing} |".format(
            id=_sanitize_cell(item.issue_id),
            title=_sanitize_cell(item.title[:60]),
            severity=_sanitize_cell(item.severity),
            category=_sanitize_cell(item.category),
            action=_sanitize_cell(item.recommended_action[:80]),
            missing=_sanitize_cell("；".join(item.missing_materials[:2]) if item.missing_materials else ""),
        )
        rows.append(row)
    return "\n".join(rows)


def _sanitize_cell(value: str) -> str:
    return (value or "").replace("|", "/").replace("\n", " ").strip()
