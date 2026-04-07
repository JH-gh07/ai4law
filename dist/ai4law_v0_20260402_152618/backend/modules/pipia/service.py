from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from backend.common.llm.adapter import LLMAdapter
from backend.common.rag.retriever import retrieve_regulations
from backend.common.render.report import render_docx_report, render_markdown_report
from backend.common.risk.scoring import risk_level
from backend.common.storage.file_parser import FileParser
from backend.common.tasks.manager import InMemoryTaskManager, TaskSnapshot
from backend.modules.pipia.schema import (
    PIPIAAsyncAccepted,
    PIPIAAsyncStatus,
    PIPIAChapter,
    PIPIARequest,
    PIPIAResult,
)


PIPIA_CHAPTERS = [
    "处理者与出境活动基础信息",
    "个人信息出境处理活动说明",
    "境外接收方信息与保护能力",
    "个人信息主体权益影响评估",
    "技术与组织措施有效性评估",
    "事件响应与整改计划",
    "PIPIA 结论与备案建议",
]


class PIPIAService:
    def __init__(self) -> None:
        self.llm = LLMAdapter()
        self.parser = FileParser()
        self.tasks = InMemoryTaskManager(module="pipia")

    def generate_report(self, payload: PIPIARequest) -> PIPIAResult:
        profile = payload.company_profile
        level = risk_level(
            is_ciio=profile.is_ciio,
            contains_important_data=False,
            pii_count=profile.outbound_pi_count,
            spi_count=profile.outbound_spi_count,
        )
        regs = retrieve_regulations(
            f"PIPIA standard contract certification {payload.transfer_context.purpose} {payload.transfer_context.recipient_country_region}",
            top_k=4,
        )
        citations = [f"{item.title}{item.article}" for item in regs]
        attachment_notes = self._extract_attachment_notes(payload)

        chapters: list[PIPIAChapter] = []
        for idx, title in enumerate(PIPIA_CHAPTERS, start=1):
            summary = self.llm.summarize(
                title=title,
                bullet_points=[
                    f"路径类型：{payload.route_type}",
                    f"企业：{profile.company_name}",
                    f"境外接收方：{payload.transfer_context.recipient_name}（{payload.transfer_context.recipient_country_region}）",
                    f"出境目的：{payload.transfer_context.purpose}",
                    f"法定基础：{payload.transfer_context.legal_basis}",
                    f"PI规模：{profile.outbound_pi_count}，SPI规模：{profile.outbound_spi_count}",
                    f"风险等级：{level}",
                ],
            )
            chapters.append(
                PIPIAChapter(
                    chapter_no=idx,
                    title=title,
                    content=summary.text,
                    citations=citations,
                    risk_level=level,
                )
            )

        issues = self._check_consistency(payload, level)
        outputs = self._render(payload, chapters, attachment_notes)
        return PIPIAResult(
            report_path=outputs["docx"],
            output_files=outputs,
            route_type=payload.route_type,
            risk_level=level,
            chapters=chapters,
            consistency_issues=issues,
            attachment_notes=attachment_notes,
        )

    def submit_async(self, payload: PIPIARequest) -> PIPIAAsyncAccepted:
        snapshot = self.tasks.submit(lambda: self.generate_report(payload))
        return self._snapshot_to_accepted(snapshot)

    def get_async_status(self, task_id: str) -> PIPIAAsyncStatus:
        snapshot = self.tasks.get_or_raise(task_id)
        return self._snapshot_to_status(snapshot)

    def retry_async(self, task_id: str) -> PIPIAAsyncStatus:
        snapshot = self.tasks.retry(task_id)
        return self._snapshot_to_status(snapshot)

    def cancel_async(self, task_id: str) -> PIPIAAsyncStatus:
        snapshot = self.tasks.cancel(task_id)
        return self._snapshot_to_status(snapshot)

    def _extract_attachment_notes(self, payload: PIPIARequest) -> list[str]:
        notes: list[str] = []
        for item in payload.attachments:
            file_path = item.storage_uri
            try:
                text = self.parser.parse_text(file_path)
                notes.append(f"{item.file_name}: {text[:160].replace(chr(10), ' ')}")
            except (FileNotFoundError, ValueError) as exc:
                notes.append(f"{item.file_name}: [parse skipped] {exc}")
        return notes

    @staticmethod
    def _check_consistency(payload: PIPIARequest, level: str) -> list[str]:
        issues: list[str] = []
        if payload.route_type == "scc_filing":
            has_scc = any(item.file_role == "scc_contract" for item in payload.attachments)
            if not has_scc:
                issues.append("Route is scc_filing but no scc_contract attachment was provided.")
        if payload.route_type == "certification":
            has_material = any(item.file_role == "certification_material" for item in payload.attachments)
            if not has_material:
                issues.append("Route is certification but no certification_material attachment was provided.")
        if payload.emergency_plan.incident_response_sla_hours > 72:
            issues.append("Incident response SLA exceeds 72 hours; suggest tightening escalation and response plan.")
        if level == "HIGH":
            issues.append("Current profile falls into HIGH risk; recommend legal manual review before filing.")
        return issues

    def _render(self, payload: PIPIARequest, chapters: list[PIPIAChapter], attachment_notes: list[str]) -> dict[str, str]:
        company_name = payload.company_profile.company_name
        sections: list[tuple[str, str]] = [
            ("路径信息", f"route_type: {payload.route_type}"),
            ("企业基础信息", payload.company_profile.model_dump_json(indent=2)),
            ("出境上下文", payload.transfer_context.model_dump_json(indent=2)),
            ("附件解析摘要", "\n".join(f"- {item}" for item in attachment_notes) or "- 无"),
        ]
        for chapter in chapters:
            sections.append((f"第{chapter.chapter_no}章 {chapter.title}", chapter.content))

        output_dir = Path("outputs/pipia")
        md_output = output_dir / f"{company_name}_pipia_report.md"
        docx_output = output_dir / f"{company_name}_pipia_report.docx"
        zip_output = output_dir / f"{company_name}_pipia_output_bundle.zip"
        render_markdown_report(md_output, "个人信息保护影响评估报告（PIPIA, v0）", sections)
        render_docx_report(docx_output, "个人信息保护影响评估报告（PIPIA, v0）", sections)
        with ZipFile(zip_output, mode="w", compression=ZIP_DEFLATED) as bundle:
            bundle.write(docx_output, arcname=docx_output.name)
            bundle.write(md_output, arcname=md_output.name)
        return {"markdown": str(md_output), "docx": str(docx_output), "zip": str(zip_output)}

    @staticmethod
    def _snapshot_to_accepted(snapshot: TaskSnapshot) -> PIPIAAsyncAccepted:
        return PIPIAAsyncAccepted(
            task_id=snapshot.task_id,
            module=snapshot.module,
            state=snapshot.state,
            attempts=snapshot.attempts,
            max_attempts=snapshot.max_attempts,
        )

    @staticmethod
    def _snapshot_to_status(snapshot: TaskSnapshot) -> PIPIAAsyncStatus:
        result = None
        if snapshot.result is not None:
            result = PIPIAResult.model_validate(snapshot.result)
        return PIPIAAsyncStatus(
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

