from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from backend.common.llm.client import LLMClient
from backend.common.quality.alignment import check_cn_alignment
from backend.common.llm.module_generator import generate_chapter
from backend.common.rag.retriever import retrieve_regulations
from backend.common.render.report import (
    format_date_stamp,
    render_docx_template,
    render_markdown_template,
    safe_filename,
)
from backend.common.render.summary import attach_citations, summarize_for_slot
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


TEMPLATE_PATH = Path("doc/v2/assets/templates/2.3_pipia_template_v0.docx")
TEMPLATE_MD = Path("doc/v2/assets/templates/2.3_pipia_template_v0.md")

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
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        if llm_client is None:
            from backend.core.settings import get_settings
            llm_client = LLMClient(get_settings())
        self.llm_client = llm_client
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
            jurisdiction="cn",
            path="scc" if payload.route_type == "scc_filing" else "all",
        )
        citations = [f"{item.title}{item.article}" for item in regs]
        reg_snippet = "\n".join(
            f"- {item.title}{item.article}：{(item.content or '')[:120]}"
            for item in regs
        ) or "（暂无检索到相关法条）"
        attachment_notes = self._extract_attachment_notes(payload)

        context_block = (
            f"【企业信息】\n"
            f"- 企业名称：{profile.company_name}\n"
            f"- 合规路径：{payload.route_type}\n"
            f"- 境外接收方：{payload.transfer_context.recipient_name}（{payload.transfer_context.recipient_country_region}）\n"
            f"- 出境目的：{payload.transfer_context.purpose}\n"
            f"- 法定基础：{payload.transfer_context.legal_basis}\n"
            f"- 个人信息规模：{profile.outbound_pi_count:,}人\n"
            f"- 敏感个人信息规模：{profile.outbound_spi_count:,}人\n"
            f"- 风险等级：{level}\n"
            f"\n【法规参考】\n{reg_snippet}\n"
        )

        chapters: list[PIPIAChapter] = []
        for idx, title in enumerate(PIPIA_CHAPTERS, start=1):
            if self.llm_client and self.llm_client.enabled:
                content = generate_chapter(self.llm_client, "pipia", title, context_block, citations=citations)
            else:
                content = f"（{title}：LLM未配置，此处为占位内容）"
            chapters.append(
                PIPIAChapter(
                    chapter_no=idx,
                    title=title,
                    content=content,
                    citations=citations,
                    risk_level=level,
                )
            )

        issues = self._check_consistency(payload, level)
        alignment_issues = check_cn_alignment(
            "\n".join(chapter.content for chapter in chapters),
            industry=payload.company_profile.industry,
            receiver_country=payload.transfer_context.recipient_country_region,
        )
        if alignment_issues:
            issues.extend(alignment_issues)
        risk_conflicts = _find_risk_conflicts(chapters, level)
        if risk_conflicts:
            issues.extend(risk_conflicts)
        outputs = self._render(
            payload,
            chapters,
            attachment_notes,
            overall_risk_level=level,
            alignment_warning="；".join(alignment_issues) if alignment_issues else None,
        )
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

    def _render(
        self,
        payload: PIPIARequest,
        chapters: list[PIPIAChapter],
        attachment_notes: list[str],
        overall_risk_level: str,
        alignment_warning: str | None = None,
    ) -> dict[str, str]:
        company_name = payload.company_profile.company_name
        output_dir = Path("outputs/pipia")
        date_stamp = format_date_stamp()
        safe_company = safe_filename(company_name)
        md_output = output_dir / f"{safe_company}_PIPIA_报告_草案_{date_stamp}.md"
        docx_output = output_dir / f"{safe_company}_PIPIA_报告_草案_{date_stamp}.docx"
        zip_output = output_dir / f"{safe_company}_PIPIA_输出包_草案_{date_stamp}.zip"
        mapping = _build_template_mapping(
            payload,
            chapters,
            date_stamp,
            overall_risk_level=overall_risk_level,
            alignment_warning=alignment_warning,
        )
        render_markdown_template(md_output, TEMPLATE_MD, mapping)
        render_docx_template(docx_output, TEMPLATE_PATH, mapping)
        with ZipFile(zip_output, mode="w", compression=ZIP_DEFLATED) as bundle:
            bundle.write(docx_output, arcname=docx_output.name)
            bundle.write(md_output, arcname=md_output.name)
        return {"markdown": str(md_output), "docx": str(docx_output), "zip": str(zip_output)}


def _build_template_mapping(
    payload: PIPIARequest,
    chapters: list[PIPIAChapter],
    date_stamp: str,
    overall_risk_level: str,
    alignment_warning: str | None = None,
) -> dict[str, str]:
    def pick(title: str) -> str:
        for chapter in chapters:
            if chapter.title == title:
                return chapter.content
        return ""

    scope = payload.personal_info_scope
    citations: list[str] = []
    for chapter in chapters:
        if chapter.citations:
            citations = chapter.citations
            break

    necessity = summarize_for_slot(pick("处理者与出境活动基础信息"), max_sentences=2, max_chars=260)
    risk_list = summarize_for_slot(pick("个人信息主体权益影响评估"), max_sentences=2, max_chars=260)
    controls = summarize_for_slot(pick("技术与组织措施有效性评估"), max_sentences=2, max_chars=260)
    remediation = summarize_for_slot(pick("事件响应与整改计划"), max_sentences=2, max_chars=260)
    conclusion = summarize_for_slot(pick("PIPIA 结论与备案建议"), max_sentences=2, max_chars=260)
    conclusion = _normalize_risk_label(conclusion, overall_risk_level)
    conclusion = f"综合风险等级：{overall_risk_level}。{conclusion}".strip()
    if alignment_warning:
        conclusion = f"【输入对齐告警】{alignment_warning}\n{conclusion}".strip()

    return {
        "company_name": payload.company_profile.company_name,
        "processing_activity_name": "个人信息出境处理活动（PIPIA）",
        "assessment_date": date_stamp,
        "processing_purpose": payload.transfer_context.purpose,
        "processing_method": "跨境传输并由境外接收方处理。",
        "processing_scope": f"涉及{scope.subject_volume:,}人，含敏感信息{len(scope.spi_categories)}类",
        "legal_basis": payload.transfer_context.legal_basis,
        "necessity_analysis": attach_citations(necessity, citations),
        "pi_categories": "、".join(scope.pi_categories),
        "spi_categories": "、".join(scope.spi_categories) or "无",
        "subject_volume": f"{scope.subject_volume:,}人",
        "risk_list": attach_citations(risk_list, citations),
        "risk_level": overall_risk_level,
        "current_controls": attach_citations(controls, citations),
        "additional_controls": attach_citations(remediation, citations),
        "improvement_plan": attach_citations(remediation, citations),
        "final_conclusion": attach_citations(conclusion, citations),
    }


def _find_risk_conflicts(chapters: list[PIPIAChapter], overall_risk_level: str) -> list[str]:
    opposite_tokens = ("LOW", "低风险") if overall_risk_level == "HIGH" else ("HIGH", "高风险")
    conflicts: list[str] = []
    for chapter in chapters:
        if any(token in chapter.content for token in opposite_tokens):
            conflicts.append(
                f"Chapter '{chapter.title}' contains risk label inconsistent with overall risk level {overall_risk_level}."
            )
    return conflicts


def _normalize_risk_label(text: str, overall_risk_level: str) -> str:
    if overall_risk_level == "HIGH":
        return text.replace("LOW", "HIGH").replace("低风险", "高风险")
    if overall_risk_level == "LOW":
        return text.replace("HIGH", "LOW").replace("高风险", "低风险")
    return text
