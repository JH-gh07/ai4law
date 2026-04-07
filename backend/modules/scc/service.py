from __future__ import annotations

from pathlib import Path

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
from backend.modules.scc.schema import (
    SCCAsyncAccepted,
    SCCAsyncStatus,
    SCCChapter,
    SCCProfile,
    SCCRequest,
    SCCResult,
)


TEMPLATE_PATH = Path("doc/v2/assets/templates/2.3_pipia_template_v0.docx")
TEMPLATE_MD = Path("doc/v2/assets/templates/2.3_pipia_template_v0.md")

SCC_CHAPTERS = [
    "处理活动与出境背景",
    "个人信息类型与规模",
    "境外接收方保护能力",
    "合同与组织措施",
    "个人信息权益影响分析",
    "PIPIA 结论与备案建议",
]


class SCCService:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        if llm_client is None:
            from backend.core.settings import get_settings
            llm_client = LLMClient(get_settings())
        self.llm_client = llm_client
        self.parser = FileParser()
        self.tasks = InMemoryTaskManager(module="scc")

    def _build_profile(self, payload: SCCRequest) -> SCCProfile:
        notes: list[str] = []
        for file_path in payload.uploaded_files:
            try:
                text = self.parser.parse_text(file_path)
                notes.append(f"{file_path}: {text[:160].replace(chr(10), ' ')}")
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
            extracted_notes=notes,
        )

    def _generate_chapters(self, profile: SCCProfile) -> tuple[list[SCCChapter], list[str]]:
        level = risk_level(
            is_ciio=False,
            contains_important_data=False,
            pii_count=profile.pii_count,
            spi_count=profile.spi_count,
        )
        regs = retrieve_regulations(
            f"standard contract PIPIA {profile.transfer_purpose} {profile.receiver_country}",
            top_k=4,
            jurisdiction="cn",
            path="scc",
        )
        citations = [f"{item.title}{item.article}" for item in regs]
        reg_snippet = "\n".join(
            f"- {item.title}{item.article}：{(item.content or '')[:120]}"
            for item in regs
        ) or "（暂无检索到相关法条）"

        context_block = (
            f"【企业信息】\n"
            f"- 企业名称：{profile.company_name}\n"
            f"- 境外接收方：{profile.receiver_name}（{profile.receiver_country}）\n"
            f"- 出境目的：{profile.transfer_purpose}\n"
            f"- 个人信息规模：{profile.pii_count:,}人\n"
            f"- 敏感个人信息规模：{profile.spi_count:,}人\n"
            f"- 是否已有标准合同草案：{'是' if profile.has_scc_draft else '否'}\n"
            f"- 风险等级：{level}\n"
            f"\n【法规参考】\n{reg_snippet}\n"
        )

        chapters: list[SCCChapter] = []
        for idx, title in enumerate(SCC_CHAPTERS, start=1):
            if self.llm_client and self.llm_client.enabled:
                content = generate_chapter(self.llm_client, "scc", title, context_block, citations=citations)
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

        issues: list[str] = []
        if not profile.has_scc_draft:
            issues.append("No SCC draft provided; legal terms should be manually reviewed before filing.")
        if profile.spi_count >= 10_000:
            issues.append("Sensitive personal information volume exceeds 10,000; verify route with security assessment obligations.")

        return chapters, issues

    def generate_report(self, payload: SCCRequest) -> SCCResult:
        profile = self._build_profile(payload)
        chapters, issues = self._generate_chapters(profile)
        alignment_issues = check_cn_alignment(
            "\n".join(chapter.content for chapter in chapters),
            receiver_country=profile.receiver_country,
        )
        if alignment_issues:
            issues.extend(alignment_issues)

        date_stamp = format_date_stamp()
        safe_company = safe_filename(payload.company_name)
        md_output = Path("outputs/scc") / f"{safe_company}_PIPIA_报告_草案_{date_stamp}.md"
        docx_output = Path("outputs/scc") / f"{safe_company}_PIPIA_报告_草案_{date_stamp}.docx"
        mapping = _build_pipia_template_mapping(
            profile,
            chapters,
            date_stamp,
            alignment_warning="；".join(alignment_issues) if alignment_issues else None,
        )
        render_markdown_template(md_output, TEMPLATE_MD, mapping)
        render_docx_template(docx_output, TEMPLATE_PATH, mapping)

        return SCCResult(
            report_path=str(docx_output),
            output_files={"markdown": str(md_output), "docx": str(docx_output)},
            profile=profile,
            chapters=chapters,
            consistency_issues=issues,
        )


def _build_pipia_template_mapping(
    profile: SCCProfile,
    chapters: list[SCCChapter],
    date_stamp: str,
    alignment_warning: str | None = None,
) -> dict[str, str]:
    def pick(title: str) -> str:
        for chapter in chapters:
            if chapter.title == title:
                return chapter.content
        return ""

    risk = "MEDIUM" if profile.spi_count >= 1 else "LOW"
    citations: list[str] = []
    for chapter in chapters:
        if chapter.citations:
            citations = chapter.citations
            break

    necessity = summarize_for_slot(pick("处理活动与出境背景"), max_sentences=2, max_chars=260)
    risk_list = summarize_for_slot(pick("个人信息权益影响分析"), max_sentences=2, max_chars=260)
    controls = summarize_for_slot(pick("合同与组织措施"), max_sentences=2, max_chars=260)
    improvement = summarize_for_slot(pick("PIPIA 结论与备案建议"), max_sentences=2, max_chars=260)
    conclusion = summarize_for_slot(pick("PIPIA 结论与备案建议"), max_sentences=2, max_chars=260) or "综合评估结论待进一步核验。"
    if alignment_warning:
        conclusion = f"【输入对齐告警】{alignment_warning}\n{conclusion}".strip()

    return {
        "company_name": profile.company_name,
        "processing_activity_name": "个人信息出境处理活动（SCC/PIPIA）",
        "assessment_date": date_stamp,
        "processing_purpose": profile.transfer_purpose,
        "processing_method": "跨境传输并由境外接收方提供服务支持。",
        "processing_scope": f"普通个人信息{profile.pii_count:,}人，敏感个人信息{profile.spi_count:,}人",
        "legal_basis": "合同履行必要",
        "necessity_analysis": attach_citations(necessity, citations),
        "pi_categories": "账号信息、联系方式、服务记录等（示例）",
        "spi_categories": "身份认证相关信息（示例）",
        "subject_volume": f"{profile.pii_count:,}人",
        "risk_list": attach_citations(risk_list, citations),
        "risk_level": risk,
        "current_controls": attach_citations(controls, citations),
        "additional_controls": "加强境外接收方审计与访问控制。",
        "improvement_plan": attach_citations(improvement, citations),
        "final_conclusion": attach_citations(conclusion, citations),
    }

    def submit_async(self, payload: SCCRequest) -> SCCAsyncAccepted:
        snapshot = self.tasks.submit(lambda: self.generate_report(payload))
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
