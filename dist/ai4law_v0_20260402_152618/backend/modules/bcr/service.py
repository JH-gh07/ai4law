from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from backend.common.llm.adapter import LLMAdapter
from backend.common.rag.retriever import retrieve_regulations
from backend.common.render.report import render_docx_report, render_markdown_report
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
    def __init__(self) -> None:
        self.llm = LLMAdapter()
        self.parser = FileParser()
        self.tasks = InMemoryTaskManager(module="bcr")

    def generate_report(self, payload: BCRRequest) -> BCRResult:
        problems = self._extract_problems(payload)
        rating = self._resolve_rating(payload.review_items)
        issues = self._check_consistency(payload)
        attachment_notes = self._extract_attachment_notes(payload)

        regs = retrieve_regulations("GDPR BCR Article 47 onward transfer liability", top_k=4)
        citations = [f"{item.title}{item.article}" for item in regs]
        chapters = self._generate_chapters(payload, rating, problems, citations)
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
    ) -> list[BCRChapter]:
        summary = self.llm.summarize(
            title="报告摘要",
            bullet_points=[
                f"公司：{payload.company_name}",
                f"审查项总数：{len(payload.review_items)}",
                f"问题数：{len(problems)}",
                f"综合评级：{rating}",
            ],
        ).text
        detail_lines = [
            f"{item.code} | {item.title} | 风险={item.risk_level} | 问题={item.finding} | 建议={item.recommendation}"
            for item in problems
        ]
        detail_content = "\n".join(detail_lines) if detail_lines else "未发现高/中风险问题。"
        priority_content = self.llm.summarize(
            title="风险优先级与整改路径",
            bullet_points=[
                "HIGH: 立即整改并复审",
                "MEDIUM: 版本内修订并补证据",
                "LOW: 保持监控并定期抽查",
            ],
        ).text
        return [
            BCRChapter(chapter_no=1, title="报告摘要", content=summary, citations=citations, risk_level=rating),
            BCRChapter(chapter_no=2, title="合规评级", content=f"综合评级：{rating}", citations=citations, risk_level=rating),
            BCRChapter(chapter_no=3, title="详细审查结果", content=detail_content, citations=citations, risk_level=rating),
            BCRChapter(
                chapter_no=4,
                title="风险优先级与整改建议",
                content=priority_content,
                citations=citations,
                risk_level=rating,
            ),
        ]

    def _render(
        self,
        payload: BCRRequest,
        rating: str,
        problems: list[BCRProblem],
        chapters: list[BCRChapter],
        attachment_notes: list[str],
    ) -> dict[str, str]:
        sections: list[tuple[str, str]] = [
            ("审查对象", f"company_name: {payload.company_name}"),
            ("综合评级", rating),
            ("问题清单", "\n".join(f"- {item.code}: {item.finding}" for item in problems) or "- 无"),
            ("附件解析摘要", "\n".join(f"- {item}" for item in attachment_notes) or "- 无"),
        ]
        for chapter in chapters:
            sections.append((f"第{chapter.chapter_no}章 {chapter.title}", chapter.content))

        output_dir = Path("outputs/bcr")
        md_output = output_dir / f"{payload.company_name}_bcr_review_report.md"
        docx_output = output_dir / f"{payload.company_name}_bcr_review_report.docx"
        zip_output = output_dir / f"{payload.company_name}_bcr_output_bundle.zip"
        render_markdown_report(md_output, "BCR-C 合规审查报告（v0）", sections)
        render_docx_report(docx_output, "BCR-C 合规审查报告（v0）", sections)
        with ZipFile(zip_output, mode="w", compression=ZIP_DEFLATED) as bundle:
            bundle.write(docx_output, arcname=docx_output.name)
            bundle.write(md_output, arcname=md_output.name)
        return {"markdown": str(md_output), "docx": str(docx_output), "zip": str(zip_output)}

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

