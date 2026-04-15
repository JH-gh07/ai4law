from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from backend.common.llm.client import LLMClient
from backend.common.llm.module_generator import generate_chapter
from backend.common.rag.retriever import retrieve_regulations
from backend.common.render.report import (
    format_date_stamp,
    render_docx_template,
    render_markdown_template,
    safe_filename,
)
from backend.common.storage.file_parser import FileParser
from backend.common.tasks.manager import InMemoryTaskManager, TaskSnapshot
from backend.modules.bcr.schema import (
    BCRAsyncAccepted,
    BCRAsyncStatus,
    BCRChapter,
    BCRProblem,
    BCRRequest,
    BCRResult,
    BCRScore,
)

TEMPLATE_PATH = Path("doc/v2/assets/templates/3.2_bcr_review_template_v0.docx")
TEMPLATE_MD = Path("doc/v2/assets/templates/3.2_bcr_review_template_v0.md")


BCR_REQUIRED_CODES = {
    "3.2-C1",
    "3.2-C2",
    "3.2-C3",
    "3.2-C4",
    "3.2-C5",
    "3.2-C6",
    "3.2-C7",
    "3.2-C8",
    "3.2-C9",
    "3.2-C10",
}


class BCRService:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        if llm_client is None:
            from backend.core.settings import get_settings
            llm_client = LLMClient(get_settings())
        self.llm_client = llm_client
        self.parser = FileParser()
        self.tasks = InMemoryTaskManager(module="bcr")

    def generate_report(self, payload: BCRRequest) -> BCRResult:
        problems = self._extract_problems(payload)
        rating = self._resolve_rating(payload.review_items)
        issues = self._check_consistency(payload)
        attachment_notes = self._extract_attachment_notes(payload)

        regs = retrieve_regulations(
            "GDPR BCR Article 47 onward transfer liability",
            top_k=4,
            jurisdiction="eu",
            path="all",
        )
        citations = [f"{item.title}{item.article}" for item in regs]
        reg_snippet = "\n".join(
            f"- {item.title}{item.article}：{(item.content or '')[:120]}"
            for item in regs
        ) or "（暂无检索到相关法条）"
        chapters = self._generate_chapters(payload, rating, problems, citations, reg_snippet)
        outputs = self._render(payload, rating, problems, chapters, attachment_notes)
        return BCRResult(
            report_path=outputs["docx"],
            output_files=outputs,
            company_name=payload.company_name,
            rating=rating,
            problems=problems,
            chapters=chapters,
            consistency_issues=issues,
            attachment_notes=attachment_notes,
        )

    def submit_async(self, payload: BCRRequest) -> BCRAsyncAccepted:
        snapshot = self.tasks.submit(lambda: self.generate_report(payload))
        return self._snapshot_to_accepted(snapshot)

    def get_async_status(self, task_id: str) -> BCRAsyncStatus:
        snapshot = self.tasks.get_or_raise(task_id)
        return self._snapshot_to_status(snapshot)

    def retry_async(self, task_id: str) -> BCRAsyncStatus:
        snapshot = self.tasks.retry(task_id)
        return self._snapshot_to_status(snapshot)

    def cancel_async(self, task_id: str) -> BCRAsyncStatus:
        snapshot = self.tasks.cancel(task_id)
        return self._snapshot_to_status(snapshot)

    @staticmethod
    def _snapshot_to_accepted(snapshot: TaskSnapshot) -> BCRAsyncAccepted:
        return BCRAsyncAccepted(
            task_id=snapshot.task_id,
            module=snapshot.module,
            state=snapshot.state,
            attempts=snapshot.attempts,
            max_attempts=snapshot.max_attempts,
        )

    @staticmethod
    def _snapshot_to_status(snapshot: TaskSnapshot) -> BCRAsyncStatus:
        result = None
        if snapshot.result is not None:
            result = BCRResult.model_validate(snapshot.result)
        return BCRAsyncStatus(
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
    def _score_to_risk(score: BCRScore) -> str:
        if score == "non_compliant":
            return "HIGH"
        if score == "partial":
            return "MEDIUM"
        return "LOW"

    def _extract_problems(self, payload: BCRRequest) -> list[BCRProblem]:
        problems: list[BCRProblem] = []
        for item in payload.review_items:
            if item.score == "compliant":
                continue
            problems.append(
                BCRProblem(
                    code=item.code,
                    title=item.title,
                    risk_level=self._score_to_risk(item.score),
                    finding=item.finding,
                    legal_basis=item.legal_basis,
                    recommendation=item.recommendation,
                    evidence=item.evidence,
                )
            )
        return problems

    @staticmethod
    def _resolve_rating(items: list) -> str:
        non_compliant = sum(1 for item in items if item.score == "non_compliant")
        partial = sum(1 for item in items if item.score == "partial")
        if non_compliant >= 2:
            return "高风险"
        if non_compliant >= 1 or partial >= 1:
            return "部分缺失"
        return "基本合规"

    def _check_consistency(self, payload: BCRRequest) -> list[str]:
        issues: list[str] = []
        codes = {item.code for item in payload.review_items}
        missing = sorted(BCR_REQUIRED_CODES - codes)
        if missing:
            issues.append(f"Missing review items: {', '.join(missing)}")
        if not payload.attachments and not payload.uploaded_files:
            issues.append("No BCR document attachments provided; evidence traceability is weak.")
        if self._resolve_rating(payload.review_items) == "高风险":
            issues.append("Overall rating is 高风险; prioritize remediation before regulatory submission.")
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
        payload: BCRRequest,
        rating: str,
        problems: list[BCRProblem],
        citations: list[str],
        reg_snippet: str,
    ) -> list[BCRChapter]:
        detail_lines = [
            f"{item.code} | {item.title} | 风险={item.risk_level} | 问题={item.finding} | 建议={item.recommendation}"
            for item in problems
        ]
        detail_content = "\n".join(detail_lines) if detail_lines else "未发现高/中风险问题。"

        context_block = (
            f"【审查信息】\n"
            f"- 公司名称：{payload.company_name}\n"
            f"- 审查项总数：{len(payload.review_items)}\n"
            f"- 问题数：{len(problems)}\n"
            f"- 综合评级：{rating}\n"
            f"- 问题清单：{detail_content[:400]}\n"
            f"\n【法规参考】\n{reg_snippet}\n"
        )

        BCR_CHAPTERS = ["报告摘要", "合规评级", "详细审查结果", "风险优先级与整改建议"]
        chapters: list[BCRChapter] = []
        for idx, title in enumerate(BCR_CHAPTERS, start=1):
            if title == "合规评级":
                content = f"综合评级：{rating}"
            elif title == "详细审查结果":
                content = detail_content
            elif self.llm_client and self.llm_client.enabled:
                content = generate_chapter(self.llm_client, "bcr", title, context_block, citations=citations)
            else:
                content = f"（{title}：LLM未配置，此处为占位内容）"
            chapters.append(BCRChapter(chapter_no=idx, title=title, content=content, citations=citations, risk_level=rating))
        return chapters

    def _render(
        self,
        payload: BCRRequest,
        rating: str,
        problems: list[BCRProblem],
        chapters: list[BCRChapter],
        attachment_notes: list[str],
    ) -> dict[str, str]:
        output_dir = Path("outputs/bcr")
        date_stamp = format_date_stamp()
        safe_company = safe_filename(payload.company_name)
        md_output = output_dir / f"{safe_company}_BCR-C_合规审查报告_草案_{date_stamp}.md"
        docx_output = output_dir / f"{safe_company}_BCR-C_合规审查报告_草案_{date_stamp}.docx"
        zip_output = output_dir / f"{safe_company}_BCR-C_输出包_草案_{date_stamp}.zip"
        mapping = _build_template_mapping(payload, rating, problems, chapters, date_stamp)
        render_markdown_template(md_output, TEMPLATE_MD, mapping)
        render_docx_template(docx_output, TEMPLATE_PATH, mapping)
        with ZipFile(zip_output, mode="w", compression=ZIP_DEFLATED) as bundle:
            bundle.write(docx_output, arcname=docx_output.name)
            bundle.write(md_output, arcname=md_output.name)
        return {"markdown": str(md_output), "docx": str(docx_output), "zip": str(zip_output)}


def _build_template_mapping(
    payload: BCRRequest,
    rating: str,
    problems: list[BCRProblem],
    chapters: list[BCRChapter],
    date_stamp: str,
) -> dict[str, str]:
    def join_items(items: list[BCRProblem]) -> str:
        if not items:
            return "无"
        return "; ".join(f"{item.code}-{item.title}" for item in items)

    def chapter_text(no: int) -> str:
        for chapter in chapters:
            if chapter.chapter_no == no:
                return chapter.content
        return ""

    high = [p for p in problems if p.risk_level == "HIGH"]
    medium = [p for p in problems if p.risk_level == "MEDIUM"]
    low = [p for p in problems if p.risk_level == "LOW"]
    detailed = "\n".join(
        f"{p.code} | {p.title} | 风险={p.risk_level} | 问题={p.finding} | 建议={p.recommendation}"
        for p in problems
    ) or "无"

    return {
        "bcr_subject": payload.company_name,
        "review_scope": "EDPB BCR-C 核心要素",
        "review_date": date_stamp,
        "overall_rating": rating,
        "key_findings": join_items(problems),
        "detailed_findings": detailed,
        "high_risk_items": join_items(high),
        "medium_risk_items": join_items(medium),
        "low_risk_items": join_items(low),
        "remediation_roadmap": chapter_text(4) or "按风险优先级制定整改路线。",
    }
