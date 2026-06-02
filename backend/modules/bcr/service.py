"""BCRService — document-driven BCR review engine with form-driven fallback."""

from __future__ import annotations

import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from backend.common.llm.client import LLMClient
from backend.common.llm.module_generator import generate_chapter
from backend.common.rag.retriever import retrieve_regulations
from backend.common.render.report import (
    format_date_stamp, render_docx_template, render_markdown_template, safe_filename,
)
from backend.common.storage.file_parser import FileParser
from backend.common.tasks.manager import InMemoryTaskManager, TaskSnapshot
from backend.modules.bcr.bcr_checklist_checker import BCRChecklistChecker
from backend.modules.bcr.bcr_clause_reviewer import BCRClauseReviewer
from backend.modules.bcr.bcr_document_parser import BCRDocumentParser
from backend.modules.bcr.bcr_legal_retriever import BCRLegalRetriever
from backend.modules.bcr.bcr_report_renderer import BCRReportRenderer
from backend.modules.bcr.bcr_risk_aggregator import BCRRiskAggregator
from backend.modules.bcr.bcr_rulebook_loader import BCRRulebookLoader
from backend.modules.bcr.bcr_scenario_extractor import BCRScenarioExtractor
from backend.modules.bcr.bcr_type_classifier import BCRTypeClassifier
from backend.modules.bcr.schema import (
    BCRAsyncAccepted, BCRAsyncStatus, BCRChapter, BCRProblem, BCRRequest, BCRResult, BCRScore,
)

TEMPLATE_PATH = Path("doc/v2/assets/templates/3.2_bcr_review_template_v0.docx")
TEMPLATE_MD = Path("doc/v2/assets/templates/3.2_bcr_review_template_v0.md")
BCR_REQUIRED_CODES = {f"3.2-C{i}" for i in range(1, 11)}


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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_report(self, payload: BCRRequest) -> BCRResult:
        if payload.uploaded_documents:
            return self._run_document_driven_review(payload)
        return self._run_form_driven_review(payload)

    def submit_async(self, payload: BCRRequest) -> BCRAsyncAccepted:
        snapshot = self.tasks.submit(lambda: self.generate_report(payload))
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

    def _run_document_driven_review(self, payload: BCRRequest) -> BCRResult:
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

        # Stage 3: SCENARIO_EXTRACTION
        scenario = self.scenario_extractor.extract(
            combined_text, doc=main_doc, user_context=payload.scenario_context,
        )

        # Stage 4: CHECKLIST_CHECKING
        findings, missing = self.checklist_checker.check(main_doc, bcr_type)

        # Stage 5: CLAUSE_REVIEWING
        requirements = self.rulebook.get_all_requirements(bcr_type)
        for ch in main_doc.chapters:
            for req in requirements:
                if any(kw.lower() in ch.content.lower() for kw in req.get("check_keywords", [])[:3]):
                    refs = self.legal_retriever.retrieve(req["requirement_id"], bcr_type, ch.content)
                    findings.extend(self.clause_reviewer.review_clause(
                        ch.content, req, bcr_type, refs,
                    ))
                    break

        # Deduplicate findings
        seen_titles: set[str] = set()
        deduped: list = []
        for f in findings:
            if f.title not in seen_titles:
                seen_titles.add(f.title)
                deduped.append(f)

        # Stage 6: AGGREGATING + RENDERING
        agg = self.risk_aggregator.aggregate(deduped, missing, type_class)
        rating = agg["overall_rating"]
        score = agg["overall_score"]

        metadata = {
            "completed_at": datetime.datetime.now().isoformat(),
            "review_mode": "llm" if (self.llm_client and self.llm_client.enabled) else "rule_only",
            "bcr_type": bcr_type, "total_findings": len(deduped), "total_missing": len(missing),
        }

        sections = self.report_renderer.build_sections(type_class, deduped, missing, rating, score, metadata)

        # Generate chapters for backward compat
        chapters = [
            BCRChapter(
                chapter_no=i + 1, title=title, content="\n".join(lines[:20]),
                citations=[], risk_level=rating,
            )
            for i, (title, lines) in enumerate(sections[:4])
        ]

        outputs = self._render_document_driven(payload, rating, deduped, chapters, sections, metadata)

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

    def _run_form_driven_review(self, payload: BCRRequest) -> BCRResult:
        problems = self._extract_problems(payload)
        rating = self._resolve_rating(payload.review_items)
        issues = self._check_consistency(payload)
        attachment_notes = self._extract_attachment_notes(payload)

        regs = retrieve_regulations("GDPR BCR Article 47 onward transfer liability", top_k=4, jurisdiction="eu", path="all")
        citations = [f"{item.title}{item.article}" for item in regs]
        reg_snippet = "\n".join(f"- {item.title}{item.article}：{(item.content or '')[:120]}" for item in regs) or "（暂无检索到相关法条）"
        chapters = self._generate_chapters(payload, rating, problems, citations, reg_snippet)
        outputs = self._render(payload, rating, problems, chapters, attachment_notes)
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

    def _generate_chapters(self, payload, rating, problems, citations, reg_snippet) -> list[BCRChapter]:
        detail = "\n".join(
            f"{p.code} | {p.title} | 风险={p.risk_level} | {p.finding} | {p.recommendation}"
            for p in problems
        ) or "未发现高/中风险问题。"
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
                content = generate_chapter(self.llm_client, "bcr", title, ctx, citations=citations)
            else:
                content = f"（{title}：LLM未配置，此处为占位内容）"
            chapters.append(BCRChapter(chapter_no=idx, title=title, content=content, citations=citations, risk_level=rating))
        return chapters

    def _render(self, payload, rating, problems, chapters, attachment_notes) -> dict[str, str]:
        output_dir = Path("outputs/bcr")
        date_stamp = format_date_stamp()
        safe_name = safe_filename(payload.company_name)
        md_out = output_dir / f"{safe_name}_BCR-C_合规审查报告_草案_{date_stamp}.md"
        docx_out = output_dir / f"{safe_name}_BCR-C_合规审查报告_草案_{date_stamp}.docx"
        zip_out = output_dir / f"{safe_name}_BCR-C_输出包_草案_{date_stamp}.zip"
        mapping = _build_template_mapping(payload, rating, problems, chapters, date_stamp)
        output_dir.mkdir(parents=True, exist_ok=True)
        render_markdown_template(md_out, TEMPLATE_MD, mapping)
        render_docx_template(docx_out, TEMPLATE_PATH, mapping)
        with ZipFile(zip_out, mode="w", compression=ZIP_DEFLATED) as z:
            z.write(docx_out, arcname=docx_out.name)
            z.write(md_out, arcname=md_out.name)
        return {"markdown": str(md_out), "docx": str(docx_out), "zip": str(zip_out)}

    # ------------------------------------------------------------------
    # Document-driven rendering
    # ------------------------------------------------------------------

    def _render_document_driven(self, payload, rating, findings, chapters, sections, metadata) -> dict[str, str]:
        output_dir = Path("outputs/bcr")
        date_stamp = format_date_stamp()
        safe_name = safe_filename(payload.company_name)
        md_out = output_dir / f"{safe_name}_BCR审查报告_草案_{date_stamp}.md"
        docx_out = output_dir / f"{safe_name}_BCR审查报告_草案_{date_stamp}.docx"
        zip_out = output_dir / f"{safe_name}_BCR审查输出包_草案_{date_stamp}.zip"

        # Build template mapping from sections
        mapping = {
            "bcr_subject": payload.company_name,
            "review_scope": f"BCR Document-Driven Review ({metadata.get('bcr_type', 'unknown')})",
            "review_date": date_stamp,
            "overall_rating": rating,
            "key_findings": "；".join(f.title for f in findings[:5]) or "未发现高风险问题",
            "detailed_findings": "\n".join(f"{f.title} [{f.risk_level}] {f.finding}" for f in findings[:10]) or "无",
            "high_risk_items": "；".join(f.title for f in findings if f.risk_level == "HIGH") or "无",
            "medium_risk_items": "；".join(f.title for f in findings if f.risk_level == "MEDIUM") or "无",
            "low_risk_items": "；".join(f.title for f in findings if f.risk_level == "LOW") or "无",
            "remediation_roadmap": "\n".join(sections[7][1][:6]) if len(sections) > 7 else "按风险优先级制定整改路线。",
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        render_markdown_template(md_out, TEMPLATE_MD, mapping)
        render_docx_template(docx_out, TEMPLATE_PATH, mapping)
        with ZipFile(zip_out, mode="w", compression=ZIP_DEFLATED) as z:
            z.write(docx_out, arcname=docx_out.name)
            z.write(md_out, arcname=md_out.name)
        return {"markdown": str(md_out), "docx": str(docx_out), "zip": str(zip_out)}

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
    detailed = "\n".join(f"{p.code} | {p.title} | 风险={p.risk_level} | {p.finding} | {p.recommendation}" for p in problems) or "无"
    return {
        "bcr_subject": payload.company_name, "review_scope": "EDPB BCR-C 核心要素",
        "review_date": date_stamp, "overall_rating": rating,
        "key_findings": join_items(problems), "detailed_findings": detailed,
        "high_risk_items": join_items(high), "medium_risk_items": join_items(med),
        "low_risk_items": join_items(low),
        "remediation_roadmap": ch_text(4) or "按风险优先级制定整改路线。",
    }
