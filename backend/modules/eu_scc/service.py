"""EU SCC service — WorkflowPipeline orchestration for SCC compliance review."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from backend.common.llm.client import LLMClient
from backend.common.llm.module_generator import generate_chapter
from backend.common.rag.retriever import retrieve_regulations
from backend.common.render.report import format_date_stamp, render_docx_template, render_markdown_template, safe_filename
from backend.common.render.docx_comments import DocxComment, render_commented_docx
from backend.common.render.summary import attach_citations, summarize_for_slot
from backend.common.storage.file_parser import FileParser
from backend.common.tasks.manager import InMemoryTaskManager, TaskSnapshot
from backend.common.trace.context import current_trace
from backend.common.trace.recorder import TraceRecorder
from backend.common.workflow import GenerationContextPack, WorkflowPipeline
from backend.modules.eu_scc.evidence_builder import build_eu_scc_evidence
from backend.modules.eu_scc.fact_builder import build_eu_scc_facts
from backend.modules.eu_scc.issue_builder import EU_SCC_CHAPTER_KEYS, build_eu_scc_issues
from backend.modules.eu_scc.scc_parser import parse_scc_document
from backend.modules.eu_scc.scc_rule_engine import run_eu_scc_rule_engine, score_scc_risk
from backend.modules.eu_scc.agents import create_eu_scc_agents
from backend.modules.eu_scc.schema import (
    SCCAsyncAccepted, SCCAsyncStatus, SCCChapter, SCCReviewRequest, SCCReviewResult, SCCRuleEngineResult,
)

EU_SCC_CHAPTERS = [
    "文件概要",
    "总体合规评级",
    "条款级审查发现",
    "法规依据与修改建议",
]


class EU_SCCService:
    """EU SCC compliance review service with deterministic rule engine + WorkflowPipeline."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        if llm_client is None:
            from backend.core.settings import get_settings
            llm_client = LLMClient(get_settings())
        self.llm_client = llm_client
        self.parser = FileParser()
        self.tasks = InMemoryTaskManager(module="eu_scc")
        self.agents = create_eu_scc_agents(llm_client)

    def generate_report(self, payload: SCCReviewRequest) -> SCCReviewResult:
        task_id = str(uuid.uuid4())
        trace_dir = Path("outputs/eu_scc") / task_id / "trace"
        trace = TraceRecorder(trace_dir)
        token = current_trace.set(trace)

        # Parse SCC document
        doc = parse_scc_document(
            payload.scc_text,
            declared_module=payload.declared_module_type,
            exporter_role=payload.exporter_role,
            importer_role=payload.importer_role,
        )
        trace.record("parsed_document_raw", doc.model_dump())

        # ── Agent 1: Document Structure Completion ──
        doc_patch = self.agents["document_structure"].run(
            raw_text=payload.scc_text, parsed_document=doc.model_dump(),
            declared_module=payload.declared_module_type,
        )
        trace.record("agent_document_structure", doc_patch)
        # Apply patches to doc (field-level corrections) — only fill missing fields
        for patch in doc_patch.get("patches", []):
            field_path = patch.get("field_path", "")
            if "exporter_role" in field_path and patch.get("new_value") and not payload.exporter_role:
                payload.exporter_role = patch["new_value"]
            if "importer_role" in field_path and patch.get("new_value") and not payload.importer_role:
                payload.importer_role = patch["new_value"]

        # Build transfer chain
        from backend.modules.eu_scc.scc_parser import _build_transfer_chain
        chain = _build_transfer_chain(
            payload.exporter_role, payload.importer_role, doc, ""
        )
        trace.record("transfer_chain_raw", chain.model_dump())

        # ── Agent 2: Transfer Chain Reasoning ──
        chain_patch = self.agents["transfer_chain"].run(
            document=doc.model_dump(), initial_chain=chain.model_dump(),
            uploaded_attachment_notes=payload.uploaded_files,
        )
        trace.record("agent_transfer_chain", chain_patch)
        # Merge risk hints into rule engine input
        risk_hints = chain_patch.get("risk_hints", [])

        # Run rule engine
        rule_result = run_eu_scc_rule_engine(
            doc, chain, payload.declared_module_type,
            has_tia=payload.has_tia,
            has_supplementary_measures=payload.has_supplementary_measures,
        )
        trace.record("rule_engine_result_raw", rule_result.model_dump())

        # ── Agent 3: Clause Semantic Comparison ──
        clause_agent_out = self.agents["clause_semantic"].run(
            document=doc.model_dump(),
            rule_clause_comparison=rule_result.clause_comparison.model_dump(),
        )
        for f in clause_agent_out.get("additional_findings", []):
            rule_result.clause_comparison.findings.append(
                type(rule_result.clause_comparison.findings[0])(**f) if rule_result.clause_comparison.findings else f)
            from backend.modules.eu_scc.schema import SCCFinding
            rule_result.all_findings.append(SCCFinding(
                finding_id=f.get("finding_id", "EU-SCC-AGENT-CLAUSE"), location=f.get("location", ""),
                clause_ref=f.get("clause_ref", ""), issue_type=f.get("issue_type", "clause_weakened"),
                severity=f.get("severity", "MEDIUM"), risk_analysis=f.get("risk_analysis", ""),
                legal_basis=f.get("legal_basis", ""), recommendation=f.get("recommendation", ""),
            ))
        trace.record("agent_clause_semantic", {k: v for k, v in clause_agent_out.items() if k != "additional_findings"})

        # ── Agent 4: TIA / Supplementary Measures Effectiveness ──
        tia_agent_out = self.agents["tia_effectiveness"].run(
            document=doc.model_dump(), transfer_chain=chain.model_dump(),
            tia_review=rule_result.tia_review.model_dump(),
            has_tia=payload.has_tia,
            has_supplementary_measures=payload.has_supplementary_measures,
        )
        for f in tia_agent_out.get("additional_findings", []):
            from backend.modules.eu_scc.schema import SCCFinding
            rule_result.all_findings.append(SCCFinding(
                finding_id=f.get("finding_id", "EU-SCC-AGENT-TIA"), location=f.get("location", ""),
                issue_type=f.get("issue_type", "supplementary_measures_insufficient"),
                severity=f.get("severity", "MEDIUM"), risk_analysis=f.get("risk_analysis", ""),
                legal_basis=f.get("legal_basis", ""), recommendation=f.get("recommendation", ""),
            ))
        trace.record("agent_tia_effectiveness", {k: v for k, v in tia_agent_out.items() if k != "additional_findings"})

        # ── Re-score after agent findings ──
        rule_result.overall_rating = score_scc_risk(rule_result.all_findings)

        try:
            run_result = self._build_pipeline(rule_result).run(
                payload=payload, task_id=task_id, trace=trace
            )
        finally:
            current_trace.reset(token)

        # ── Agent 5: Evidence Review (post-pipeline) ──
        try:
            evidence_agent_out = self.agents["evidence_review"].run(
                facts=[f.model_dump() if hasattr(f, "model_dump") else f for f in run_result.context_pack.facts],
                issues=[i.model_dump() if hasattr(i, "model_dump") else i for i in run_result.context_pack.issues],
                evidence_chain=[e.model_dump() if hasattr(e, "model_dump") else e for e in run_result.context_pack.evidence_chain],
                regulations=[], findings=[f.model_dump() if hasattr(f, "model_dump") else f for f in rule_result.all_findings],
            )
            trace.record("agent_evidence_review", evidence_agent_out)
        except Exception:
            pass  # Agent 5 is advisory — never block the pipeline

        # ── Agent 6: Remediation Generation ──
        remediation_out = self.agents["remediation"].run(
            findings=[f.model_dump() for f in rule_result.all_findings],
            document=doc.model_dump(), transfer_chain=chain.model_dump(),
            module_validation=rule_result.module_validation.model_dump(),
        )
        trace.record("agent_remediation", remediation_out)
        # Apply remediation suggestions to findings
        for pf in remediation_out.get("patched_findings", []):
            for orig in rule_result.all_findings:
                if orig.finding_id == pf.get("finding_id"):
                    orig.recommendation = pf.get("recommendation", orig.recommendation)
                    orig.suggested_text = pf.get("suggested_text", orig.suggested_text)

        return SCCReviewResult(
            report_path=run_result.outputs.get("markdown", ""),
            output_files=run_result.outputs,
            company_name=payload.company_name,
            overall_rating=rule_result.overall_rating,
            findings=rule_result.all_findings,
            module_validation=rule_result.module_validation,
            chapters=run_result.chapters,
            consistency_issues=run_result.consistency_issues,
            attachment_notes=[
                f"{item.get('source_ref', '')}: {item.get('summary', '')}"
                for item in run_result.context_pack.attachment_notes
            ],
        )

    def _build_pipeline(self, rule_result: SCCRuleEngineResult) -> WorkflowPipeline:
        return WorkflowPipeline(
            extract_profile=lambda payload: payload,
            evaluate_diagnosis=lambda payload: rule_result,
            validate_path=lambda payload, path, rationale: None,
            build_facts=self._build_facts(rule_result),
            retrieve_regulations=self._retrieve_regulations,
            build_attachment_notes=self._extract_notes,
            build_issues=self._build_issues(rule_result),
            build_evidence=self._build_evidence,
            build_context_pack=self._build_context_pack(rule_result),
            generate_chapters=self._generate_chapters(rule_result),
            check_consistency=self._check_consistency,
            check_alignment=lambda content, profile: [],
            render_artifacts=self._render_outputs(rule_result),
            request_event_name="eu_scc_request",
            consistency_check_labels=["eu_scc_rules"],
        )

    def _build_facts(self, rule_result):
        def _inner(payload, profile, diagnosis):
            return build_eu_scc_facts(payload, rule_result)
        return _inner

    @staticmethod
    def _retrieve_regulations(payload: SCCReviewRequest) -> list[dict]:
        query = (
            f"GDPR Article 46 standard contractual clauses EU 2021/914 "
            f"EDPB recommendations Schrems II transfer impact assessment "
            f"{payload.declared_module_type} {payload.exporter_role} {payload.importer_role}"
        )
        docs = retrieve_regulations(query, top_k=5, jurisdiction="eu", path="scc")
        return [{"source_id": d.id, "title": d.title, "article": d.article, "snippet": d.content} for d in docs]

    def _extract_notes(self, payload: SCCReviewRequest) -> list[dict[str, str]]:
        notes: list[dict[str, str]] = []
        for fp in payload.uploaded_files:
            try:
                text = self.parser.parse_text(fp)
                notes.append({"source_ref": fp, "summary": text[:160].replace("\n", " ")})
            except (FileNotFoundError, ValueError) as e:
                notes.append({"source_ref": fp, "summary": f"[parse skipped] {e}"})
        return notes

    def _build_issues(self, rule_result):
        def _inner(facts, diagnosis, regulations, attachment_notes):
            return build_eu_scc_issues(facts, rule_result, regulations)
        return _inner

    @staticmethod
    def _build_evidence(facts, issues, regulations, diagnosis):
        return build_eu_scc_evidence(facts, issues, regulations)

    def _build_context_pack(self, rule_result):
        def _inner(*, task_id, diagnosis, facts, regulations, issues, evidence_chain, path_warning, attachment_notes, **kw):
            return GenerationContextPack(
                module_key="eu_scc", request_id=task_id, facts=facts,
                diagnosis_result=diagnosis.model_dump(), regulations=regulations,
                issues=issues, evidence_chain=evidence_chain, path_warning=path_warning,
                risk_summary={"overall_rating": rule_result.overall_rating, "finding_count": len(rule_result.all_findings)},
                attachment_notes=attachment_notes,
                output_requirements={"chapter_keys": list(EU_SCC_CHAPTER_KEYS.values())},
            )
        return _inner

    def _generate_chapters(self, rule_result):
        def _inner(payload, regulations, context_pack):
            citations = [f"{r.get('title', '')}{r.get('article', '')}" for r in regulations]
            chapters: list[SCCChapter] = []
            for idx, title in enumerate(EU_SCC_CHAPTERS, start=1):
                chapter_id = EU_SCC_CHAPTER_KEYS[title]
                ctx = _build_context_block(payload, context_pack, rule_result, chapter_id)
                if self.llm_client and self.llm_client.enabled:
                    content = generate_chapter(self.llm_client, "eu_scc", title, ctx, citations=citations)
                else:
                    content = _render_placeholder(title, chapter_id, rule_result)
                chapters.append(SCCChapter(chapter_no=idx, title=title, content=content, citations=citations, risk_level=rule_result.overall_rating))
            return chapters
        return _inner

    @staticmethod
    def _check_consistency(payload, chapters, context_pack):
        issues: list[str] = []
        if not payload.scc_text or len(payload.scc_text.strip()) < 100:
            issues.append("SCC document text is too short or missing.")
        if any(i.severity in ("HIGH", "BLOCKER") for i in context_pack.issues):
            issues.append("Contains HIGH risk items — recommend legal review before filing.")
        return issues

    def _render_outputs(self, rule_result):
        def _inner(*, task_id, payload, profile, regulations, chapters, path_warning, alignment_warning, issues, evidence_chain, attachment_notes, trace_manifest_path, facts, diagnosis, **kw):
            output_dir = Path("outputs/eu_scc") / task_id / "outputs"
            output_dir.mkdir(parents=True, exist_ok=True)
            date_stamp = format_date_stamp()
            base = safe_filename(payload.company_name)
            md_out = output_dir / f"{base}_EU_SCC审查报告_{date_stamp}.md"
            docx_out = output_dir / f"{base}_EU_SCC审查报告_{date_stamp}.docx"
            mapping = _build_template_mapping(payload, chapters, rule_result, date_stamp)

            # MD report (self-rendered)
            _render_markdown_report(md_out, payload, chapters, rule_result, date_stamp)
            # DOCX (placeholder — template not yet available)
            docx_out.touch()

            # Annotated DOCX (findings as comments)
            annotated_path = None
            source_docx = _pick_source_docx(payload.uploaded_files)
            if source_docx:
                comments = [
                    DocxComment(
                        label=f.get("issue_type", "EU SCC Review"),
                        location=f.location,
                        quote=f.original_text,
                        risk_level=f.severity,
                        basis=f.legal_basis,
                        risk_analysis=f.risk_analysis,
                        suggestion=f.recommendation,
                    )
                    for f in rule_result.all_findings
                ]
                ann_out = output_dir / f"{base}_EU_SCC批注修订版_{date_stamp}.docx"
                render_commented_docx(source_docx, ann_out, comments)
                annotated_path = str(ann_out)

            # JSON artifacts
            (output_dir / "findings.json").write_text(json.dumps([f.model_dump() for f in rule_result.all_findings], ensure_ascii=False, indent=2), encoding="utf-8")
            (output_dir / "rule_engine_result.json").write_text(rule_result.model_dump_json(indent=2), encoding="utf-8")
            (output_dir / "issues.json").write_text(json.dumps([i.model_dump() for i in issues], ensure_ascii=False, indent=2), encoding="utf-8")
            (output_dir / "evidence.json").write_text(json.dumps([e.model_dump() for e in evidence_chain], ensure_ascii=False, indent=2), encoding="utf-8")

            result = {"markdown": str(md_out), "docx": str(docx_out), "findings_json": str(output_dir / "findings.json"), "rule_engine_result_json": str(output_dir / "rule_engine_result.json")}
            if annotated_path:
                result["annotated_docx"] = annotated_path
            return result
        return _inner

    # Async
    def submit_async(self, payload): snapshot = self.tasks.submit(lambda: self.generate_report(payload)); return self._to_accepted(snapshot)
    def get_async_status(self, tid): return self._to_status(self.tasks.get_or_raise(tid))
    def retry_async(self, tid): return self._to_status(self.tasks.retry(tid))
    def cancel_async(self, tid): return self._to_status(self.tasks.cancel(tid))

    @staticmethod
    def _to_accepted(s: TaskSnapshot): return SCCAsyncAccepted(task_id=s.task_id, module=s.module, state=s.state, attempts=s.attempts, max_attempts=s.max_attempts)
    @staticmethod
    def _to_status(s: TaskSnapshot):
        r = SCCReviewResult.model_validate(s.result) if s.result else None
        return SCCAsyncStatus(task_id=s.task_id, module=s.module, state=s.state, attempts=s.attempts, max_attempts=s.max_attempts, created_at=s.created_at, updated_at=s.updated_at, error=s.error, result=r)


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

def _build_context_block(payload, context_pack, rule_result, chapter_id):
    matched = [i for i in context_pack.issues if chapter_id in i.affects_outputs]
    if not matched:
        matched = [i for i in context_pack.issues if i.severity in ("HIGH", "BLOCKER")]

    issue_block = "\n".join(f"- {i.issue_id} | {i.severity} | {i.title}" for i in matched) or "- None"
    reg_block = "\n".join(f"- {r.get('source_id','')}: {str(r.get('snippet',''))[:120]}" for r in context_pack.regulations[:5]) or "- None"

    findings_block = "\n".join(
        f"- [{f.severity}] {f.location}: {f.risk_analysis[:200]}"
        for f in rule_result.all_findings[:10]
    ) or "- None"

    mv = rule_result.module_validation
    tia = rule_result.tia_review

    return (
        f"【EU SCC Review Context】\n"
        f"- Module: declared={mv.actual_module}, expected={mv.expected_module}, correct={mv.is_correct}\n"
        f"- Clause deviations: {rule_result.clause_comparison.deviations_found}\n"
        f"- Third country transfers: {tia.third_country_transfers}\n"
        f"- TIA present: {tia.tia_present}\n"
        f"- Schrems II measures: {tia.schrems_ii_measures_present}\n"
        f"- Overall rating: {rule_result.overall_rating}\n"
        f"\n【Findings】\n{findings_block}\n"
        f"\n【Issues】\n{issue_block}\n"
        f"\n【Regulations】\n{reg_block}\n"
    )


def _render_placeholder(title, chapter_id, rule_result):
    mv = rule_result.module_validation
    tia = rule_result.tia_review
    cc = rule_result.clause_comparison

    if chapter_id == "document_overview":
        return (
            f"## 文件概要\n\n"
            f"- SCC 模块: 声明={mv.actual_module}, 预期={mv.expected_module}, 正确={'是' if mv.is_correct else '否'}\n"
            f"- 条款数: {len(rule_result.document.clauses)}\n"
            f"- Annex I.A 主体数: {len(rule_result.document.annex_i_a.parties)}\n"
            f"- Annex II 措施数: {len(rule_result.document.annex_ii.tom_items)}\n"
            f"- Annex III 子处理者数: {len(rule_result.document.annex_iii.sub_processors)}\n"
        )
    elif chapter_id == "overall_rating":
        return (
            f"## 总体合规评级: {rule_result.overall_rating}\n\n"
            f"- 模块选择: {'正确' if mv.is_correct else f'错误 ({mv.mismatch_reason})'}\n"
            f"- 标准条款偏离: {cc.deviations_found}处\n"
            f"- 第三国传输: {'是 (' + ', '.join(tia.third_country_transfers[:3]) + ')' if tia.has_third_country_transfer else '否'}\n"
            f"- TIA: {'存在' if tia.tia_present else '缺失'}\n"
            f"- Schrems II 补充措施: {'存在' if tia.schrems_ii_measures_present else '不足'}\n"
        )
    elif chapter_id == "clause_findings":
        lines = ["## 条款级审查发现\n"]
        for f in rule_result.all_findings:
            lines.append(f"### [{f.severity}] {f.location}")
            lines.append(f"- 问题类型: {f.issue_type}")
            lines.append(f"- 风险分析: {f.risk_analysis}")
            lines.append(f"- 法规依据: {f.legal_basis}")
            lines.append(f"- 修改建议: {f.recommendation}")
            if f.suggested_text:
                lines.append(f"- 建议文本: {f.suggested_text}")
            lines.append("")
        return "\n".join(lines) if len(lines) > 2 else "## 条款级审查发现\n\n未发现重大合规问题。"
    elif chapter_id == "legal_basis_and_recommendations":
        lines = ["## 法规依据与修改建议\n"]
        seen_bases = set()
        for f in rule_result.all_findings:
            if f.legal_basis not in seen_bases:
                seen_bases.add(f.legal_basis)
                lines.append(f"- {f.legal_basis}")
        lines.append("\n### 修改建议汇总\n")
        for f in rule_result.all_findings:
            if f.recommendation:
                lines.append(f"- [{f.severity}] {f.location}: {f.recommendation}")
        return "\n".join(lines)
    return f"（{title}：内容待生成）"


def _build_template_mapping(payload, chapters, rule_result, date_stamp):
    def pick(no):
        for c in chapters:
            if c.chapter_no == no: return c.content
        return ""

    citations = []
    for c in chapters:
        if c.citations: citations = c.citations; break

    mv = rule_result.module_validation
    findings_table = "\n".join(
        f"| {f.location} | {f.original_text[:60]} | {f.issue_type} | {f.severity} | {f.risk_analysis[:150]} | {f.legal_basis[:80]} | {f.recommendation[:150]} |"
        for f in rule_result.all_findings[:15]
    )
    table_header = "| Location | Original Text | Issue Type | Severity | Risk Analysis | Legal Basis | Recommendation |\n| --- | --- | --- | --- | --- | --- | --- |"

    return {
        "company_name": payload.company_name,
        "review_date": date_stamp,
        "module_type": f"{mv.actual_module} (correct: {mv.is_correct})",
        "overall_rating": rule_result.overall_rating,
        "finding_count": str(len(rule_result.all_findings)),
        "clause_deviations": str(rule_result.clause_comparison.deviations_found),
        "third_country": "Yes" if rule_result.tia_review.has_third_country_transfer else "No",
        "tia_present": "Yes" if rule_result.tia_review.tia_present else "No",
        "executive_summary": attach_citations(summarize_for_slot(pick(2), max_sentences=3, max_chars=300), citations),
        "findings_table": f"{table_header}\n{findings_table}" if findings_table else "No findings.",
        "revision_recommendations": attach_citations(summarize_for_slot(pick(4), max_sentences=3, max_chars=300), citations),
    }


def _render_markdown_report(output_path, payload, chapters, rule_result, date_stamp):
    lines = [
        f"# EU SCC Compliance Review Report — {payload.company_name}",
        f"**Date**: {date_stamp} | **Rating**: {rule_result.overall_rating}",
        "",
    ]
    for chapter in chapters:
        lines.append(f"## {chapter.title}")
        lines.append(chapter.content)
        lines.append("")
        if chapter.citations:
            lines.append(f"*References: {'; '.join(chapter.citations)}*")
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def _pick_source_docx(files: list[str]) -> Path | None:
    for raw in files:
        p = Path(raw)
        if p.suffix.lower() == ".docx" and p.exists():
            return p
    return None
