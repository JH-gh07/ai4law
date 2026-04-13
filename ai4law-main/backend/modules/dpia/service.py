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
from backend.modules.dpia.schema import (
    DPIAAsyncAccepted,
    DPIAAsyncStatus,
    DPIAChapter,
    DPIARequest,
    DPIAResult,
)

TEMPLATE_PATH = Path("doc/v2/assets/templates/3.3_dpia_template_v0.docx")
TEMPLATE_MD = Path("doc/v2/assets/templates/3.3_dpia_template_v0.md")

DPIA_CHAPTERS = [
    "DPIA 项目背景与范围",
    "数据处理活动描述",
    "目的必要性与合法性评估",
    "风险识别与影响分析",
    "控制措施与缓解方案",
    "剩余风险与可接受性判断",
    "DPO 复核与后续行动",
]


class DPIAService:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        if llm_client is None:
            from backend.core.settings import get_settings
            llm_client = LLMClient(get_settings())
        self.llm_client = llm_client
        self.parser = FileParser()
        self.tasks = InMemoryTaskManager(module="dpia")

    def generate_report(self, payload: DPIARequest) -> DPIAResult:
        level = self._resolve_risk_level(payload.residual_risk, payload.risk_assessment)
        regs = retrieve_regulations(
            f"DPIA GDPR Article35 {payload.lawful_basis}",
            top_k=4,
            jurisdiction="eu",
            path="all",
        )
        citations = [f"{item.title}{item.article}" for item in regs]
        reg_snippet = "\n".join(
            f"- {item.title}{item.article}：{(item.content or '')[:120]}"
            for item in regs
        ) or "（暂无检索到相关法条）"
        attachment_notes = self._extract_attachment_notes(payload)

        context_block = (
            f"【项目信息】\n"
            f"- 项目名称：{payload.project_name}\n"
            f"- 处理活动描述：{payload.processing_description}\n"
            f"- 目的与必要性：{payload.purpose_and_necessity}\n"
            f"- 合法基础：{payload.lawful_basis}\n"
            f"- 风险评估：{payload.risk_assessment}\n"
            f"- 缓解措施：{payload.mitigation_measures}\n"
            f"- 剩余风险：{payload.residual_risk}\n"
            f"- 风险等级：{level}\n"
            f"\n【法规参考】\n{reg_snippet}\n"
        )

        chapters: list[DPIAChapter] = []
        for idx, title in enumerate(DPIA_CHAPTERS, start=1):
            if self.llm_client and self.llm_client.enabled:
                content = generate_chapter(self.llm_client, "dpia", title, context_block, citations=citations)
            else:
                content = f"（{title}：LLM未配置，此处为占位内容）"
            chapters.append(
                DPIAChapter(
                    chapter_no=idx,
                    title=title,
                    content=content,
                    citations=citations,
                    risk_level=level,
                )
            )

        issues = self._check_consistency(payload, level)
        outputs = self._render(payload, chapters, attachment_notes)
        return DPIAResult(
            report_path=outputs["docx"],
            output_files=outputs,
            project_name=payload.project_name,
            risk_level=level,
            chapters=chapters,
            consistency_issues=issues,
            attachment_notes=attachment_notes,
        )

    def submit_async(self, payload: DPIARequest) -> DPIAAsyncAccepted:
        snapshot = self.tasks.submit(lambda: self.generate_report(payload))
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

    def _extract_attachment_notes(self, payload: DPIARequest) -> list[str]:
        notes: list[str] = []
        for item in payload.attachments:
            try:
                text = self.parser.parse_text(item.storage_uri)
                notes.append(f"{item.file_name}: {text[:160].replace(chr(10), ' ')}")
            except (FileNotFoundError, ValueError) as exc:
                notes.append(f"{item.file_name}: [parse skipped] {exc}")
        return notes

    @staticmethod
    def _resolve_risk_level(residual_risk: str, risk_assessment: str) -> str:
        text = f"{residual_risk} {risk_assessment}".lower()
        if any(token in text for token in ("高", "high", "critical")):
            return "HIGH"
        if any(token in text for token in ("中", "medium", "moderate")):
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _check_consistency(payload: DPIARequest, level: str) -> list[str]:
        issues: list[str] = []
        if not payload.attachments:
            issues.append("No attachment provided; add data flow diagram or policy evidence for review traceability.")
        if "合法利益" in payload.lawful_basis and "平衡测试" not in payload.risk_assessment:
            issues.append("Lawful basis mentions legitimate interest but balancing-test evidence is not explicit.")
        if level == "HIGH" and "consult" not in payload.mitigation_measures.lower():
            issues.append("Residual risk is HIGH; consider prior consultation with supervisory authority.")
        return issues

    def _render(self, payload: DPIARequest, chapters: list[DPIAChapter], attachment_notes: list[str]) -> dict[str, str]:
        output_dir = Path("outputs/dpia")
        date_stamp = format_date_stamp()
        safe_project = safe_filename(payload.project_name)
        md_output = output_dir / f"{safe_project}_DPIA_报告_草案_{date_stamp}.md"
        docx_output = output_dir / f"{safe_project}_DPIA_报告_草案_{date_stamp}.docx"
        zip_output = output_dir / f"{safe_project}_DPIA_输出包_草案_{date_stamp}.zip"
        mapping = _build_template_mapping(payload, chapters)
        render_markdown_template(md_output, TEMPLATE_MD, mapping)
        render_docx_template(docx_output, TEMPLATE_PATH, mapping)
        with ZipFile(zip_output, mode="w", compression=ZIP_DEFLATED) as bundle:
            bundle.write(docx_output, arcname=docx_output.name)
            bundle.write(md_output, arcname=md_output.name)
        return {"markdown": str(md_output), "docx": str(docx_output), "zip": str(zip_output)}


def _build_template_mapping(payload: DPIARequest, chapters: list[DPIAChapter]) -> dict[str, str]:
    def pick(no: int) -> str:
        for chapter in chapters:
            if chapter.chapter_no == no:
                return chapter.content
        return ""

    return {
        "processing_description": pick(2) or payload.processing_description,
        "purpose_necessity": pick(3) or payload.purpose_and_necessity,
        "lawful_basis": payload.lawful_basis,
        "risk_assessment": pick(4) or payload.risk_assessment,
        "mitigation_measures": pick(5) or payload.mitigation_measures,
        "residual_risk_and_signoff": "\n".join(filter(None, [pick(6), pick(7), payload.residual_risk])),
    }
