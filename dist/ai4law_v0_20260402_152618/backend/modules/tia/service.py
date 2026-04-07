from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from backend.common.llm.adapter import LLMAdapter
from backend.common.rag.retriever import retrieve_regulations
from backend.common.render.report import render_docx_report, render_markdown_report
from backend.common.storage.file_parser import FileParser
from backend.common.tasks.manager import InMemoryTaskManager, TaskSnapshot
from backend.modules.tia.schema import (
    TIAAsyncAccepted,
    TIAAsyncStatus,
    TIAChapter,
    TIARequest,
    TIAResult,
)


TIA_CHAPTERS = [
    "跨境传输场景与角色识别",
    "传输工具适用性判断",
    "第三国法律与实践评估",
    "补充措施可执行性评估",
    "剩余风险与合规结论",
    "持续复审与行动计划",
]


class TIAService:
    def __init__(self) -> None:
        self.llm = LLMAdapter()
        self.parser = FileParser()
        self.tasks = InMemoryTaskManager(module="tia")

    def generate_report(self, payload: TIARequest) -> TIAResult:
        level = self._resolve_risk_level(payload.third_country_assessment, payload.final_conclusion)
        regs = retrieve_regulations(
            f"TIA EDPB transfer tool {payload.transfer_tool} third country law assessment",
            top_k=4,
        )
        citations = [f"{item.title}{item.article}" for item in regs]
        attachment_notes = self._extract_attachment_notes(payload)

        chapters: list[TIAChapter] = []
        for idx, title in enumerate(TIA_CHAPTERS, start=1):
            summary = self.llm.summarize(
                title=title,
                bullet_points=[
                    f"传输工具：{payload.transfer_tool}",
                    f"出口方：{payload.data_exporter_profile}",
                    f"进口方：{payload.data_importer_profile}",
                    f"第三国评估：{payload.third_country_assessment}",
                    f"补充措施：{payload.supplementary_measures}",
                    f"结论：{payload.final_conclusion}",
                    f"风险等级：{level}",
                ],
            )
            chapters.append(
                TIAChapter(
                    chapter_no=idx,
                    title=title,
                    content=summary.text,
                    citations=citations,
                    risk_level=level,
                )
            )

        issues = self._check_consistency(payload, level)
        outputs = self._render(payload, chapters, attachment_notes)
        return TIAResult(
            report_path=outputs["docx"],
            output_files=outputs,
            transfer_tool=payload.transfer_tool,
            risk_level=level,
            chapters=chapters,
            consistency_issues=issues,
            attachment_notes=attachment_notes,
        )

    def submit_async(self, payload: TIARequest) -> TIAAsyncAccepted:
        snapshot = self.tasks.submit(lambda: self.generate_report(payload))
        return self._snapshot_to_accepted(snapshot)

    def get_async_status(self, task_id: str) -> TIAAsyncStatus:
        snapshot = self.tasks.get_or_raise(task_id)
        return self._snapshot_to_status(snapshot)

    def retry_async(self, task_id: str) -> TIAAsyncStatus:
        snapshot = self.tasks.retry(task_id)
        return self._snapshot_to_status(snapshot)

    def cancel_async(self, task_id: str) -> TIAAsyncStatus:
        snapshot = self.tasks.cancel(task_id)
        return self._snapshot_to_status(snapshot)

    def _extract_attachment_notes(self, payload: TIARequest) -> list[str]:
        notes: list[str] = []
        for item in payload.attachments:
            try:
                text = self.parser.parse_text(item.storage_uri)
                notes.append(f"{item.file_name}: {text[:160].replace(chr(10), ' ')}")
            except (FileNotFoundError, ValueError) as exc:
                notes.append(f"{item.file_name}: [parse skipped] {exc}")
        return notes

    @staticmethod
    def _resolve_risk_level(third_country_assessment: str, final_conclusion: str) -> str:
        text = f"{third_country_assessment} {final_conclusion}".lower()
        if any(token in text for token in ("高", "high", "不可", "cannot", "not effective")):
            return "HIGH"
        if any(token in text for token in ("中", "medium", "条件", "conditional")):
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _check_consistency(payload: TIARequest, level: str) -> list[str]:
        issues: list[str] = []
        has_law_analysis = any(item.file_role == "country_law_analysis" for item in payload.attachments)
        if not has_law_analysis:
            issues.append("No country_law_analysis attachment provided; legal-practice evidence is weak.")
        if payload.transfer_tool == "scc" and "scc" not in payload.final_conclusion.lower():
            issues.append("Transfer tool is SCC, but final conclusion does not explicitly evaluate SCC effectiveness.")
        if level == "HIGH" and "暂停" not in payload.final_conclusion and "suspend" not in payload.final_conclusion.lower():
            issues.append("Risk is HIGH; consider adding transfer suspension decision and fallback controls.")
        return issues

    def _render(self, payload: TIARequest, chapters: list[TIAChapter], attachment_notes: list[str]) -> dict[str, str]:
        sections: list[tuple[str, str]] = [
            ("传输基础信息", f"transfer_tool: {payload.transfer_tool}"),
            ("输入摘要", payload.model_dump_json(indent=2)),
            ("附件解析摘要", "\n".join(f"- {item}" for item in attachment_notes) or "- 无"),
        ]
        for chapter in chapters:
            sections.append((f"第{chapter.chapter_no}章 {chapter.title}", chapter.content))

        output_dir = Path("outputs/tia")
        md_output = output_dir / f"{payload.transfer_tool}_tia_report.md"
        docx_output = output_dir / f"{payload.transfer_tool}_tia_report.docx"
        zip_output = output_dir / f"{payload.transfer_tool}_tia_output_bundle.zip"
        render_markdown_report(md_output, "TIA Draft Report (v0)", sections)
        render_docx_report(docx_output, "TIA Draft Report (v0)", sections)
        with ZipFile(zip_output, mode="w", compression=ZIP_DEFLATED) as bundle:
            bundle.write(docx_output, arcname=docx_output.name)
            bundle.write(md_output, arcname=md_output.name)
        return {"markdown": str(md_output), "docx": str(docx_output), "zip": str(zip_output)}

    @staticmethod
    def _snapshot_to_accepted(snapshot: TaskSnapshot) -> TIAAsyncAccepted:
        return TIAAsyncAccepted(
            task_id=snapshot.task_id,
            module=snapshot.module,
            state=snapshot.state,
            attempts=snapshot.attempts,
            max_attempts=snapshot.max_attempts,
        )

    @staticmethod
    def _snapshot_to_status(snapshot: TaskSnapshot) -> TIAAsyncStatus:
        result = None
        if snapshot.result is not None:
            result = TIAResult.model_validate(snapshot.result)
        return TIAAsyncStatus(
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

