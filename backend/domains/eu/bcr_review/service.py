"""BCRService — document-driven BCR review engine with form-driven fallback."""

from __future__ import annotations

import datetime
import json
import re
import uuid
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from backend.common.llm.client import LLMClient
from backend.common.llm.module_generator import generate_chapter
from backend.common.citation.output import write_citation_map_json
from backend.common.citation.registry import CitationRegistry, registry_from_documents
from backend.common.llm.postprocess import apply_citation_pipeline
from backend.common.rag.service import retrieve_legal_documents
from backend.common.render.report import (
    format_date_stamp, render_docx_template, render_markdown_template, safe_filename,
)
from backend.common.runtime.module_run import finalize_run, prepare_run
from backend.common.storage.file_parser import FileParser
from backend.common.tasks.manager import InMemoryTaskManager, TaskSnapshot
from backend.common.trace.recorder import TraceRecorder
from backend.common.trace.thoughts import summarize_agent_output
from backend.core.resource_paths import report_template_path
from backend.domains.eu.bcr_review.bcr_checklist_checker import BCRChecklistChecker
from backend.domains.eu.bcr_review.bcr_clause_reviewer import BCRClauseReviewer
from backend.domains.eu.bcr_review.bcr_document_parser import BCRDocumentParser
from backend.domains.eu.bcr_review.bcr_legal_retriever import BCRLegalRetriever
from backend.domains.eu.bcr_review.bcr_report_renderer import BCRReportRenderer
from backend.domains.eu.bcr_review.bcr_risk_aggregator import BCRRiskAggregator
from backend.domains.eu.bcr_review.bcr_rulebook_loader import BCRRulebookLoader
from backend.domains.eu.bcr_review.bcr_scenario_extractor import BCRScenarioExtractor
from backend.domains.eu.bcr_review.bcr_type_classifier import BCRTypeClassifier
from backend.domains.eu.bcr_review.bcr_tia_checker import BCRTiaChecker
from backend.domains.eu.bcr_review.bcr_onward_transfer_checker import BCROnwardTransferChecker
from backend.domains.eu.bcr_review.bcr_liability_checker import BCRLiabilityChecker
from backend.domains.eu.bcr_review.agents import create_agents
from backend.domains.eu.bcr_review.schema import (
    BCRAsyncAccepted, BCRAsyncStatus, BCRChapter, BCRFinding, BCRProblem, BCRRequest, BCRResult, BCRScore,
)

TEMPLATE_PATH = report_template_path("eu", "3.2_bcr_review_template_v0.docx")
TEMPLATE_MD = report_template_path("eu", "3.2_bcr_review_template_v0.md")
BCR_REQUIRED_CODES = {f"3.2-C{i}" for i in range(1, 11)}


def _escape_md_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\r", " ").replace("\n", " ").strip()


def _build_markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    if not headers or not rows:
        return "无"
    normalized_rows = [row for row in rows if len(row) == len(headers)]
    if not normalized_rows:
        return "无"
    lines = [
        f"| {' | '.join(_escape_md_cell(header) for header in headers)} |",
        f"| {' | '.join('---' for _ in headers)} |",
    ]
    lines.extend(
        f"| {' | '.join(_escape_md_cell(cell or '-') for cell in row)} |"
        for row in normalized_rows
    )
    return "\n".join(lines)


def _build_problem_detail_table(problems: list[BCRProblem]) -> str:
    return _build_markdown_table(
        ["检查项", "主题", "风险", "现状", "整改建议", "法律依据"],
        [
            [p.code, p.title, p.risk_level, p.finding, p.recommendation, p.legal_basis]
            for p in problems
        ],
    )


def _build_finding_detail_table(findings: list[BCRFinding]) -> str:
    return _build_markdown_table(
        ["检查项", "主题", "风险", "现状", "整改建议", "法律依据"],
        [
            [
                f.requirement_id,
                f.title,
                f.risk_level,
                f.finding,
                f.recommendation,
                "；".join(f.legal_basis) if f.legal_basis else "-",
            ]
            for f in findings
        ],
    )


class BCRService:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        if llm_client is None:
            from backend.core.settings import get_settings
            llm_client = LLMClient(get_settings())
        self.llm_client = llm_client
        self.parser = FileParser()
        self.tasks = InMemoryTaskManager(module="bcr")
        # NEW document-driven components
        self.rulebook = BCRRulebookLoader()
        self.type_classifier = BCRTypeClassifier(rulebook_loader=self.rulebook, llm_client=llm_client)
        self.doc_parser = BCRDocumentParser()
        self.checklist_checker = BCRChecklistChecker(rulebook_loader=self.rulebook)
        self.clause_reviewer = BCRClauseReviewer(llm_client=llm_client, rulebook=self.rulebook)
        self.scenario_extractor = BCRScenarioExtractor()
        self.legal_retriever = BCRLegalRetriever()
        self.risk_aggregator = BCRRiskAggregator(rulebook=self.rulebook)
        self.report_renderer = BCRReportRenderer()
        from backend.core.settings import get_settings as _gs
        self.schema_first_enabled = _gs().schema_first_bcr_enabled
        self.tia_checker = BCRTiaChecker()
        self.onward_checker = BCROnwardTransferChecker()
        self.liability_checker = BCRLiabilityChecker()
        self.agents = create_agents(llm_client)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_report(
        self,
        payload: BCRRequest,
        *,
        task_id: str | None = None,
        trace: TraceRecorder | None = None,
    ) -> BCRResult:
        run_task_id = task_id or uuid.uuid4().hex
        _, token = prepare_run(module="bcr", task_id=run_task_id, trace=trace)
        try:
            if payload.uploaded_documents:
                return self._run_document_driven_review(payload, task_id=run_task_id, trace=trace)
            return self._run_form_driven_review(payload, task_id=run_task_id)
        finally:
            finalize_run(token)

    def submit_async(self, payload: BCRRequest) -> BCRAsyncAccepted:
        task_id = uuid.uuid4().hex
        trace = TraceRecorder(Path("outputs/bcr") / task_id / "trace", task_id=task_id)
        snapshot = self.tasks.submit_with_trace(
            lambda: self.generate_report(payload, task_id=task_id, trace=trace),
            trace_recorder=trace,
            llm_client=self.llm_client,
            input_snapshot=payload.model_dump(mode="json"),
        )
        return self._snapshot_to_accepted(snapshot)

    def get_async_status(self, task_id: str) -> BCRAsyncStatus:
        return self._snapshot_to_status(self.tasks.get_or_raise(task_id))

    def retry_async(self, task_id: str) -> BCRAsyncStatus:
        return self._snapshot_to_status(self.tasks.retry(task_id))

    def cancel_async(self, task_id: str) -> BCRAsyncStatus:
        return self._snapshot_to_status(self.tasks.cancel(task_id))

    # ------------------------------------------------------------------
    # Document-driven review (NEW — 6-stage pipeline)
    # ------------------------------------------------------------------

    def _run_document_driven_review(self, payload: BCRRequest, *, task_id: str, trace: TraceRecorder | None = None) -> BCRResult:
        if trace:
            trace.record("status", {"summary": "开始 BCR 合规审查", "detail": {"module": "bcr", "company": getattr(payload, 'company_name', '')}})
            trace.record("thought", {"summary": "路径判断：基于集团结构和数据流范围确定 BCR 适用条款"})

        # Stage 1: PARSING
        sdocs = []
        for ud in payload.uploaded_documents:
            path = Path(ud.file_path)
            if path.exists():
                sdocs.append(self.doc_parser.parse(ud.file_id, path))

        combined_text = "\n".join(d.plain_text for d in sdocs)
        main_doc = sdocs[0] if sdocs else None
        declared_type = (payload.scenario_context.declared_bcr_type if payload.scenario_context else None)

        # Stage 2: TYPE_CHECKING
        type_class = self.type_classifier.classify(combined_text, declared_type)
        bcr_type = type_class.actual_bcr_type if type_class.actual_bcr_type != "unknown" else "BCR-C"

        # Agent 1: Type reasoning — when uncertain or mismatch
        if bcr_type == "BCR-C" and type_class.actual_bcr_type == "unknown":
            c_ev = type_class.evidence
            agent_type = self.agents["type_reasoning"].run(
                text=combined_text, declared_type=declared_type or "BCR-C",
                c_score=sum(1 for e in c_ev if "BCR-C" in e),
                p_score=sum(1 for e in c_ev if "BCR-P" in e),
                c_evidence=c_ev, p_evidence=c_ev,
            )
            if agent_type.get("type_judgment") in ("BCR-C", "BCR-P"):
                bcr_type = agent_type["type_judgment"]
            type_class.risk_level = agent_type.get("risk_level", "MEDIUM")
            if trace:
                thought = summarize_agent_output("BCR 类型推理", agent_type)
                trace.record("thought", {"summary": thought})

        # Stage 3: SCENARIO_EXTRACTION
        scenario = self.scenario_extractor.extract(
            combined_text, doc=main_doc, user_context=payload.scenario_context,
        )

        # Agent 3: Actor role — identify EU liable entity beyond regex
        if main_doc:
            scenario_context = {
                "company_name": scenario.company_name or payload.company_name,
                "eu_liable_entity": scenario.eu_liable_entity or "",
                "headquarters_country": scenario.headquarters_country or "",
            }
            agent_roles = self.agents["actor_role"].run(
                text=combined_text,
                scenario_context=scenario_context,
                bcr_type=bcr_type,
            )
            if trace:
                thought = summarize_agent_output("BCR 角色识别", agent_roles)
                trace.record("thought", {"summary": thought})
            if agent_roles.get("eu_liable_entity") and not scenario.eu_liable_entity:
                scenario.eu_liable_entity = agent_roles["eu_liable_entity"]

        # Stage 4: CHECKLIST_CHECKING
        findings, missing = self.checklist_checker.check(main_doc, bcr_type)

        # Stage 4.5: SPECIALIZED CHECKERS (TIA, Onward Transfer, Liability)
        findings.extend(self.tia_checker.check(main_doc))
        findings.extend(self.onward_checker.check(main_doc))
        findings.extend(self.liability_checker.check(main_doc))

        # Agent 2: Coverage — for PARTIALLY_COVERED / VAGUE requirements
        requirements = self.rulebook.get_all_requirements(bcr_type)
        for req in requirements:
            status = req.get("_coverage_status", "")  # set by checker
            if status in ("PARTIALLY_COVERED", "VAGUE") and req.get("severity_if_missing") in ("HIGH",):
                matched = [ch.content for ch in main_doc.chapters
                          if any(kw.lower() in ch.content.lower() for kw in req.get("check_keywords", [])[:2])]
                agent_cov = self.agents["coverage"].run(
                    requirement_id=req["requirement_id"], requirement_title=req["title"],
                    matched_clauses=matched[:3], coverage_status=status,
                    legal_basis=[req.get("gdpr_basis", ""), req.get("source", "")], bcr_type=bcr_type,
                )
                if trace:
                    thought = summarize_agent_output("BCR 覆盖率评估", agent_cov)
                    trace.record("thought", {"summary": thought})
                if agent_cov.get("should_generate_finding"):
                    findings.append(BCRFinding(
                        finding_id=f"BCR-AGENT-COV-{req['requirement_id']}",
                        requirement_id=req["requirement_id"],
                        title=req["title"],
                        risk_level=agent_cov.get("risk_level", "MEDIUM"),
                        finding=agent_cov.get("finding_text", ""),
                        recommendation=agent_cov.get("recommendation", ""),
                    ))

        # Agent 4: Onward Transfer — when weak standard detected
        onward_text = "\n".join(ch.content for ch in main_doc.chapters if any(kw in ch.title.lower() for kw in ["onward", "transfer"]))
        if onward_text:
            agent_ot = self.agents["onward_transfer"].run(
                clause_text=onward_text, has_scc=False, has_adequacy=False,
                has_derogation=False, bcr_type=bcr_type,
            )
            if trace:
                thought = summarize_agent_output("BCR 后续传输风险", agent_ot)
                trace.record("thought", {"summary": thought})
            if agent_ot.get("finding_type") == "ONWARD_TRANSFER_WEAK_STANDARD":
                findings.append(BCRFinding(
                    finding_id="BCR-AGENT-OT-01",
                    requirement_id="BCR-C-1.8",
                    title=agent_ot.get("finding", "Onward Transfer protection standard may be insufficient"),
                    risk_level=agent_ot.get("risk_level", "MEDIUM"),
                    finding=agent_ot.get("finding", ""),
                    recommendation=agent_ot.get("recommendation", ""),
                ))

        # Agent 6: Evidence coverage — check main text vs annex coverage for key requirements
        for req in requirements:
            req_id = req.get("requirement_id", "")
            if req_id in ("BCR-C-1.1", "BCR-C-1.2", "BCR-C-1.3", "BCR-C-1.4", "BCR-P-1.1"):
                agent_ev = self.agents["evidence_coverage"].run(
                    requirement_id=req_id,
                    main_body_text=combined_text[:5000],
                    annex_texts={},
                    coverage_status=req.get("_coverage_status", "FULLY_COVERED"),
                )
                if trace:
                    thought = summarize_agent_output("BCR 证据覆盖", agent_ev)
                    trace.record("thought", {"summary": thought})
                if agent_ev.get("risk_level") in ("MEDIUM", "HIGH"):
                    findings.append(BCRFinding(
                        finding_id=f"BCR-AGENT-EV-{req_id}",
                        requirement_id=req_id,
                        title=f"Coverage source: {req.get('title', req_id)}",
                        risk_level=agent_ev.get("risk_level", "MEDIUM"),
                        finding=agent_ev.get("assessment", ""),
                        recommendation=("Move key obligation to main BCR body text" if agent_ev.get("is_key_requirement") else "Consider inline coverage"),
                    ))

        # Agent 7: Incorrect status — detect BCR-C documents with processor clauses
        for req in requirements:
            req_id = req.get("requirement_id", "")
            status = req.get("_coverage_status", "")
            if status in ("PARTIALLY_COVERED", "VAGUE", "FULLY_COVERED"):
                matched = [ch.content for ch in main_doc.chapters
                          if any(kw.lower() in ch.content.lower() for kw in req.get("check_keywords", [])[:2])]
                clause_text = "\n".join(matched[:3]) if matched else combined_text[:3000]
                agent_inc = self.agents["incorrect_status"].run(
                    clause_text=clause_text, requirement_id=req_id,
                    bcr_type=bcr_type, coverage_status=status,
                )
                if trace:
                    thought = summarize_agent_output("BCR 状态纠正", agent_inc)
                    trace.record("thought", {"summary": thought})
                if agent_inc.get("has_incorrect"):
                    findings.append(BCRFinding(
                        finding_id=f"BCR-AGENT-INC-{req_id}",
                        requirement_id=req_id,
                        title=f"Incorrect clause: {req.get('title', req_id)}",
                        risk_level=agent_inc.get("risk_level", "HIGH"),
                        finding=agent_inc.get("finding_summary", ""),
                        recommendation="Realign clause to correct BCR type (C vs P) responsibility assignment.",
                    ))

        # Agent 5: TIA completeness
        tia_text = "\n".join(ch.content for ch in main_doc.chapters if any(kw in ch.title.lower() for kw in ["third country", "tia", "local law"]))
        gov_text = "\n".join(ch.content for ch in main_doc.chapters if any(kw in ch.title.lower() for kw in ["government", "access"]))
        if tia_text:
            agent_tia = self.agents["tia_reasoning"].run(
                tia_section=tia_text, gov_access_section=gov_text,
                legal_refs=["Schrems II", "EDPB 01/2020"],
            )
            if trace:
                thought = summarize_agent_output("BCR TIA 评估", agent_tia)
                trace.record("thought", {"summary": thought})
            if agent_tia.get("tia_completeness") != "complete":
                findings.append(BCRFinding(
                    finding_id="BCR-AGENT-TIA-01",
                    requirement_id="BCR-C-1.9",
                    title=f"TIA completeness: {agent_tia.get('tia_completeness', 'incomplete')}",
                    risk_level=agent_tia.get("risk_level", "MEDIUM"),
                    finding=agent_tia.get("finding_summary", "TIA assessment is incomplete."),
                    recommendation=agent_tia.get("recommendation", ""),
                ))

        # Stage 5: CLAUSE_REVIEWING
        retrieved_legal_documents: list[dict] = []
        requirements = self.rulebook.get_all_requirements(bcr_type)
        for ch in main_doc.chapters:
            for req in requirements:
                if any(kw.lower() in ch.content.lower() for kw in req.get("check_keywords", [])[:3]):
                    refs = self.legal_retriever.retrieve(req["requirement_id"], bcr_type, ch.content)
                    retrieved_legal_documents.extend(refs)
                    findings.extend(self.clause_reviewer.review_clause(
                        ch.content, req, bcr_type, refs,
                    ))
                    # Agent 8: Legal grounding — validate that RAG citations support findings
                    if refs:
                        agent_lg = self.agents["legal_grounding"].run(
                            finding_id=f"BCR-CLAUSE-{req['requirement_id']}",
                            requirement_id=req["requirement_id"],
                            rag_citations=refs, clause_text=ch.content, bcr_type=bcr_type,
                        )
                        if trace:
                            thought = summarize_agent_output("BCR 法律依据", agent_lg)
                            trace.record("thought", {"summary": thought})
                        if not agent_lg.get("grounding_adequate"):
                            findings.append(BCRFinding(
                                finding_id=f"BCR-AGENT-LG-{req['requirement_id']}",
                                requirement_id=req["requirement_id"],
                                title=f"Weak legal grounding: {req['title']}",
                                risk_level="MEDIUM",
                                finding=f"Legal citations for this requirement may not be adequate "
                                        f"(discarded {agent_lg.get('discarded_count', 0)} of "
                                        f"{agent_lg.get('total_citations', 0)} citations).",
                                recommendation="Verify legal basis with primary GDPR articles.",
                            ))
                    break

        # Deduplicate findings
        seen_titles: set[str] = set()
        deduped: list = []
        for f in findings:
            if f.title not in seen_titles:
                seen_titles.add(f.title)
                deduped.append(f)

        citation_registry = registry_from_documents(
            retrieved_legal_documents, jurisdiction="EU"
        )
        _annotate_finding_footnotes(deduped, citation_registry)

        # Stage 6: AGGREGATING + RENDERING
        agg = self.risk_aggregator.aggregate(deduped, missing, type_class)
        rating = agg["overall_rating"]
        score = agg["overall_score"]

        # Agent 9: Approval risk — beyond formula
        finding_dicts = [{"title": f.title, "risk_level": f.risk_level,
                          "finding": f.finding, "requirement_id": f.requirement_id}
                         for f in deduped]
        agent_risk = self.agents["approval_risk"].run(
            findings=finding_dicts, current_rating=rating,
            type_consistency=type_class.type_consistency, bcr_type=bcr_type,
        )
        if trace:
            thought = summarize_agent_output("BCR 审批风险", agent_risk)
            trace.record("thought", {"summary": thought})
        if agent_risk.get("rating_adjustment") == "HIGH" and rating != "高风险":
            rating = "高风险"

        # Agent 10: Remediation — generate actionable fix suggestions for HIGH findings
        remediation_suggestions: list[dict] = []
        for f in deduped:
            if getattr(f, "risk_level", "LOW") in ("HIGH",):
                req_text = next((ch.content for ch in main_doc.chapters
                               if any(kw.lower() in ch.content.lower()
                                      for kw in ["liable", "binding", "liability", "rights",
                                                 "third party", "transfer", "government"])), "")
                agent_rem = self.agents["remediation"].run(
                    requirement_id=getattr(f, "requirement_id", ""),
                    clause_text=req_text[:2000] if req_text else "",
                    bcr_type=bcr_type,
                    finding_text=getattr(f, "finding", ""),
                    legal_basis=getattr(f, "legal_basis", ""),
                )
                if trace:
                    thought = summarize_agent_output("BCR 整改建议", agent_rem)
                    trace.record("thought", {"summary": thought})
                if agent_rem.get("suggested_text"):
                    remediation_suggestions.append(agent_rem)

        metadata = {
            "completed_at": datetime.datetime.now().isoformat(),
            "review_mode": "llm" if (self.llm_client and self.llm_client.enabled) else "rule_only",
            "bcr_type": bcr_type, "total_findings": len(deduped), "total_missing": len(missing),
        }

        sections = self.report_renderer.build_sections(type_class, deduped, missing, rating, score, metadata)
        detailed_findings_table = _build_finding_detail_table(deduped[:10])

        # Generate chapters for backward compat, but keep the detailed findings
        # chapter aligned with the same markdown table exported into the template.
        chapter_pairs: list[tuple[str, str]] = []
        for title, lines in sections[:2]:
            chapter_pairs.append((title, "\n".join(lines[:20])))
        chapter_pairs.append(("详细审查结果", detailed_findings_table))
        if len(sections) > 7:
            chapter_pairs.append(("风险优先级与整改建议", "\n".join(sections[7][1][:20])))
        elif len(sections) > 2:
            title, lines = sections[2]
            chapter_pairs.append((title, "\n".join(lines[:20])))

        chapters = [
            BCRChapter(
                chapter_no=i + 1,
                title=title,
                content=content,
                citations=[],
                risk_level=rating,
            )
            for i, (title, content) in enumerate(chapter_pairs)
        ]

        if trace:
            trace.record("tool_start", {"summary": "报告章节生成", "detail": {"agent": "chapter_generation"}})

        outputs = self._render_document_driven(
            task_id,
            payload,
            rating,
            deduped,
            chapters,
            sections,
            metadata,
            citation_registry,
        )

        if trace:
            trace.record("final", {
                "summary": "BCR 合规审查完成",
                "detail": {"output_files": outputs, "module": "bcr"},
            })
            trace.record("final_brief", {
                "summary": "BCR 合规审查完成",
                "detail": {
                    "conclusion": f"BCR 合规审查完成，已生成 {len(outputs)} 个输出文件",
                    "files": list(outputs.values()) if isinstance(outputs, dict) else [],
                    "risks": [],
                    "next_steps": ["复核生成的合规审查报告", "根据审查发现制定整改计划"],
                },
            })

        return BCRResult(
            report_path=outputs["docx"],
            output_files=outputs,
            company_name=payload.company_name,
            rating=rating,
            chapters=chapters,
            bcr_type_classification=type_class,
            findings=deduped,
            missing_requirements=missing,
            review_metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Form-driven review (original path — backward compat)
    # ------------------------------------------------------------------

    def _run_form_driven_review(self, payload: BCRRequest, *, task_id: str) -> BCRResult:
        problems = self._extract_problems(payload)
        rating = self._resolve_rating(payload.review_items)
        issues = self._check_consistency(payload)
        attachment_notes = self._extract_attachment_notes(payload)

        regs = retrieve_legal_documents(
            "GDPR BCR Article 47 onward transfer liability",
            module="eu_bcr",
            top_k=4,
            jurisdiction="eu",
            path="all",
        ).documents
        reg_snippet = "\n".join(f"- {item.title}{item.article}：{(item.content or '')[:120]}" for item in regs) or "（暂无检索到相关法条）"
        citation_registry = registry_from_documents(regs, jurisdiction="EU")
        chapters = self._generate_chapters(
            payload, rating, problems, citation_registry, reg_snippet
        )
        outputs = self._render(
            task_id,
            payload,
            rating,
            problems,
            chapters,
            attachment_notes,
            citation_registry,
        )
        return BCRResult(
            report_path=outputs["docx"], output_files=outputs,
            company_name=payload.company_name, rating=rating,
            problems=problems, chapters=chapters,
            consistency_issues=issues, attachment_notes=attachment_notes,
        )

    # ------------------------------------------------------------------
    # Form-driven helpers (original methods preserved)
    # ------------------------------------------------------------------

    @staticmethod
    def _score_to_risk(score: BCRScore) -> str:
        return "HIGH" if score == "non_compliant" else "MEDIUM" if score == "partial" else "LOW"

    def _extract_problems(self, payload: BCRRequest) -> list[BCRProblem]:
        problems: list[BCRProblem] = []
        for item in payload.review_items:
            if item.score == "compliant":
                continue
            problems.append(BCRProblem(
                code=item.code, title=item.title,
                risk_level=self._score_to_risk(item.score),
                finding=item.finding, legal_basis=item.legal_basis,
                recommendation=item.recommendation, evidence=item.evidence,
            ))
        return problems

    @staticmethod
    def _resolve_rating(items: list) -> str:
        nc = sum(1 for i in items if i.score == "non_compliant")
        partial = sum(1 for i in items if i.score == "partial")
        if nc >= 2: return "高风险"
        if nc >= 1 or partial >= 1: return "部分缺失"
        return "基本合规"

    def _check_consistency(self, payload: BCRRequest) -> list[str]:
        issues: list[str] = []
        codes = {item.code for item in payload.review_items}
        missing = sorted(BCR_REQUIRED_CODES - codes)
        if missing: issues.append(f"Missing review items: {', '.join(missing)}")
        if not payload.attachments and not payload.uploaded_files:
            issues.append("No BCR document attachments provided.")
        if self._resolve_rating(payload.review_items) == "高风险":
            issues.append("Overall rating is 高风险.")
        return issues

    def _extract_attachment_notes(self, payload: BCRRequest) -> list[str]:
        notes: list[str] = []
        paths = [item.storage_uri for item in payload.attachments] + list(payload.uploaded_files)
        for path in paths:
            try:
                text = self.parser.parse_text(path)
                notes.append(f"{Path(path).name}: {text[:160].replace(chr(10), ' ')}")
            except (FileNotFoundError, ValueError) as exc:
                notes.append(f"{Path(path).name}: [parse skipped] {exc}")
        return notes

    def _generate_chapters(
        self,
        payload,
        rating,
        problems,
        citation_registry: CitationRegistry,
        reg_snippet,
    ) -> list[BCRChapter]:
        detail = _build_problem_detail_table(problems)
        citations = [item.display_label for item in citation_registry]
        citation_marker_section = citation_registry.build_marker_list()
        ctx = (
            f"【审查信息】\n- 公司名称：{payload.company_name}\n"
            f"- 审查项总数：{len(payload.review_items)}\n- 问题数：{len(problems)}\n"
            f"- 综合评级：{rating}\n- 问题清单：{detail[:400]}\n\n【法规参考】\n{reg_snippet}\n"
        )
        titles = ["报告摘要", "合规评级", "详细审查结果", "风险优先级与整改建议"]
        chapters: list[BCRChapter] = []
        for idx, title in enumerate(titles, 1):
            if title == "合规评级":
                content = f"综合评级：{rating}"
            elif title == "详细审查结果":
                content = detail
            elif self.llm_client and self.llm_client.enabled:
                content = generate_chapter(
                    self.llm_client,
                    "bcr",
                    title,
                    ctx,
                    citations=citations,
                    citation_marker_section=citation_marker_section,
                    use_citation_markers=True,
                    citation_registry=citation_registry,
                )
            else:
                content = f"（{title}：LLM未配置，此处为占位内容）"
            footnote_map = citation_registry.get_footnote_map()
            cited_ids = [
                footnote_map[number].citation_id
                for number in _footnote_numbers(content)
                if number in footnote_map
            ]
            chapters.append(
                BCRChapter(
                    chapter_no=idx,
                    title=title,
                    content=content,
                    citations=cited_ids,
                    risk_level=rating,
                )
            )
        return chapters

    def _render(
        self,
        task_id: str,
        payload,
        rating,
        problems,
        chapters,
        attachment_notes,
        citation_registry: CitationRegistry,
    ) -> dict[str, str]:
        document_ir_path: Path | None = None
        if self.schema_first_enabled:
            from backend.common.reporting import DocumentCompiler
            from backend.domains.eu.bcr_review.schema_first import build_bcr_document_ir
            _doc, _rr = build_bcr_document_ir(
                task_id=task_id, company_name=payload.company_name,
                chapters=chapters, citation_registry=citation_registry, model="legacy-bcr",
            )
            _cr = DocumentCompiler().compile(_doc, _rr)
            if _cr.status != "success":
                _codes = ", ".join(i.code for i in _cr.diagnostics)
                raise ValueError(f"Schema-first compiler blocked BCR output: {_codes}")
            _ir_dir = Path("outputs/bcr") / task_id / "outputs"
            _ir_dir.mkdir(parents=True, exist_ok=True)
            import json as _json
            document_ir_path = _ir_dir / "document_ir.json"
            document_ir_path.write_text(
                _json.dumps(_doc.model_dump(mode="json"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        output_dir = Path("outputs/bcr") / task_id / "outputs"
        date_stamp = format_date_stamp()
        safe_name = safe_filename(payload.company_name)
        md_out = output_dir / f"{safe_name}_BCR-C_合规审查报告_草案_{date_stamp}.md"
        docx_out = output_dir / f"{safe_name}_BCR-C_合规审查报告_草案_{date_stamp}.docx"
        pdf_out = output_dir / f"{safe_name}_BCR-C_合规审查报告_草案_{date_stamp}.pdf"
        zip_out = output_dir / f"{safe_name}_BCR-C_输出包_草案_{date_stamp}.zip"
        mapping = _build_template_mapping(payload, rating, problems, chapters, date_stamp)
        output_dir.mkdir(parents=True, exist_ok=True)
        render_markdown_template(md_out, TEMPLATE_MD, mapping)
        render_docx_template(docx_out, TEMPLATE_PATH, mapping)
        from backend.common.render.pdf_renderer import get_pdf_renderer

        get_pdf_renderer().from_template(
            pdf_out,
            f"{payload.company_name} BCR-C 合规审查报告草案",
            TEMPLATE_MD,
            mapping,
        )
        citation_map_json = write_citation_map_json(
            output_dir=output_dir,
            module="eu_bcr",
            task_id=task_id,
            footnote_map={
                str(number): item.to_dict()
                for number, item in citation_registry.get_footnote_map().items()
            },
            all_items=citation_registry.to_list(),
        )
        with ZipFile(zip_out, mode="w", compression=ZIP_DEFLATED) as z:
            z.write(docx_out, arcname=docx_out.name)
            z.write(md_out, arcname=md_out.name)
            z.write(pdf_out, arcname=pdf_out.name)
            z.write(citation_map_json, arcname=Path(citation_map_json).name)
            if document_ir_path is not None:
                z.write(document_ir_path, arcname=document_ir_path.name)
        result = {
            "markdown": str(md_out),
            "docx": str(docx_out),
            "pdf": str(pdf_out),
            "zip": str(zip_out),
            "citation_map_json": citation_map_json,
        }
        if document_ir_path is not None:
            result["document_ir_json"] = str(document_ir_path)
        return result

    # ------------------------------------------------------------------
    # Document-driven rendering
    # ------------------------------------------------------------------

    def _render_document_driven(
        self,
        task_id: str,
        payload,
        rating,
        findings,
        chapters,
        sections,
        metadata,
        citation_registry: CitationRegistry | None = None,
    ) -> dict[str, str]:
        citation_registry = citation_registry or CitationRegistry()
        document_ir_path: Path | None = None
        if self.schema_first_enabled:
            from backend.common.reporting import DocumentCompiler
            from backend.domains.eu.bcr_review.schema_first import build_bcr_document_ir

            document_ir, reporting_registry = build_bcr_document_ir(
                task_id=task_id,
                company_name=payload.company_name,
                chapters=chapters,
                citation_registry=citation_registry,
                model="legacy-bcr-document-driven",
            )
            compile_result = DocumentCompiler().compile(document_ir, reporting_registry)
            if compile_result.status != "success":
                codes = ", ".join(item.code for item in compile_result.diagnostics)
                raise ValueError(f"Schema-first compiler blocked BCR output: {codes}")
            document_ir_path = Path("outputs/bcr") / task_id / "outputs" / "document_ir.json"
            document_ir_path.parent.mkdir(parents=True, exist_ok=True)
            document_ir_path.write_text(
                json.dumps(document_ir.model_dump(mode="json"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        output_dir = Path("outputs/bcr") / task_id / "outputs"
        date_stamp = format_date_stamp()
        safe_name = safe_filename(payload.company_name)
        md_out = output_dir / f"{safe_name}_BCR审查报告_草案_{date_stamp}.md"
        docx_out = output_dir / f"{safe_name}_BCR审查报告_草案_{date_stamp}.docx"
        pdf_out = output_dir / f"{safe_name}_BCR审查报告_草案_{date_stamp}.pdf"
        zip_out = output_dir / f"{safe_name}_BCR审查输出包_草案_{date_stamp}.zip"

        # Build template mapping from sections
        mapping = {
            "bcr_subject": payload.company_name,
            "review_scope": f"BCR Document-Driven Review ({metadata.get('bcr_type', 'unknown')})",
            "review_date": date_stamp,
            "overall_rating": rating,
            "key_findings": "；".join(f.title for f in findings[:5]) or "未发现高风险问题",
            "detailed_findings": _build_finding_detail_table(findings[:10]),
            "high_risk_items": "；".join(f.title for f in findings if f.risk_level == "HIGH") or "无",
            "medium_risk_items": "；".join(f.title for f in findings if f.risk_level == "MEDIUM") or "无",
            "low_risk_items": "；".join(f.title for f in findings if f.risk_level == "LOW") or "无",
            "remediation_roadmap": "\n".join(sections[7][1][:6]) if len(sections) > 7 else "按风险优先级制定整改路线。",
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        render_markdown_template(md_out, TEMPLATE_MD, mapping)
        render_docx_template(docx_out, TEMPLATE_PATH, mapping)
        from backend.common.render.pdf_renderer import get_pdf_renderer

        get_pdf_renderer().from_template(
            pdf_out,
            f"{payload.company_name} BCR 审查报告草案",
            TEMPLATE_MD,
            mapping,
        )
        citation_map_json = write_citation_map_json(
            output_dir=output_dir,
            module="eu_bcr",
            task_id=task_id,
            footnote_map={
                str(number): item.to_dict()
                for number, item in citation_registry.get_footnote_map().items()
            },
            all_items=citation_registry.to_list(),
        )
        with ZipFile(zip_out, mode="w", compression=ZIP_DEFLATED) as z:
            z.write(docx_out, arcname=docx_out.name)
            z.write(md_out, arcname=md_out.name)
            z.write(pdf_out, arcname=pdf_out.name)
            z.write(citation_map_json, arcname=Path(citation_map_json).name)
            if document_ir_path is not None:
                z.write(document_ir_path, arcname=document_ir_path.name)
        result = {
            "markdown": str(md_out),
            "docx": str(docx_out),
            "pdf": str(pdf_out),
            "zip": str(zip_out),
            "citation_map_json": citation_map_json,
        }
        if document_ir_path is not None:
            result["document_ir_json"] = str(document_ir_path)
        return result

    # ------------------------------------------------------------------
    # Async helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _snapshot_to_accepted(s: TaskSnapshot) -> BCRAsyncAccepted:
        return BCRAsyncAccepted(task_id=s.task_id, module=s.module, state=s.state, attempts=s.attempts, max_attempts=s.max_attempts)

    @staticmethod
    def _snapshot_to_status(s: TaskSnapshot) -> BCRAsyncStatus:
        result = BCRResult.model_validate(s.result) if s.result else None
        return BCRAsyncStatus(task_id=s.task_id, module=s.module, state=s.state, attempts=s.attempts, max_attempts=s.max_attempts, created_at=s.created_at, updated_at=s.updated_at, error=s.error, result=result)


def _build_template_mapping(payload, rating, problems, chapters, date_stamp):
    def join_items(items):
        return "；".join(f"{i.code}-{i.title}" for i in items) if items else "无"
    def ch_text(no):
        for c in chapters:
            if c.chapter_no == no: return c.content
        return ""
    high = [p for p in problems if p.risk_level == "HIGH"]
    med = [p for p in problems if p.risk_level == "MEDIUM"]
    low = [p for p in problems if p.risk_level == "LOW"]
    detailed = _build_problem_detail_table(problems)
    return {
        "bcr_subject": payload.company_name, "review_scope": "EDPB BCR-C 核心要素",
        "review_date": date_stamp, "overall_rating": rating,
        "key_findings": join_items(problems), "detailed_findings": detailed,
        "high_risk_items": join_items(high), "medium_risk_items": join_items(med),
        "low_risk_items": join_items(low),
        "remediation_roadmap": ch_text(4) or "按风险优先级制定整改路线。",
    }


def _footnote_numbers(text: str) -> list[int]:
    """Return unique footnote numbers in first-appearance order."""
    return list(dict.fromkeys(int(value) for value in re.findall(r"\[(\d+)\]", text)))


def _annotate_finding_footnotes(findings: list[BCRFinding], registry: CitationRegistry) -> None:
    """Add a verified footnote only when a finding's source maps uniquely."""
    for finding in findings:
        rendered: list[str] = []
        for legal_basis in finding.legal_basis:
            resolved = apply_citation_pipeline(
                f"【依据：{legal_basis}】",
                registry=registry,
            ).text
            rendered.append(
                f"{legal_basis} {resolved}" if re.fullmatch(r"(?:\[\d+\])+", resolved) else legal_basis
            )
        finding.legal_basis = rendered
