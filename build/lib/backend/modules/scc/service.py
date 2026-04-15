from __future__ import annotations

from pathlib import Path

from backend.common.llm.client import LLMClient
from backend.common.llm.module_generator import generate_chapter
from backend.common.quality.alignment import check_cn_alignment
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


TEMPLATE_PATH = Path("doc/v2/assets/templates/3.1_scc_review_template_v0.docx")
TEMPLATE_MD = Path("doc/v2/assets/templates/3.1_scc_review_template_v0.md")

SCC_CHAPTERS = [
    "审查依据说明",
    "总体合规评级",
    "条款级问题清单",
    "修订建议与行动计划",
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

    def _generate_chapters(self, profile: SCCProfile) -> tuple[list[SCCChapter], list[str], list[dict[str, str]]]:
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
            f"- 已上传文件摘要：{'; '.join(profile.extracted_notes[:3]) if profile.extracted_notes else '未提供'}\n"
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
        if profile.pii_count >= 1_000_000:
            issues.append("PII volume reaches 1,000,000 threshold; verify whether security assessment path is required.")
        if profile.spi_count >= 10_000:
            issues.append("Sensitive personal information volume exceeds 10,000; verify route with security assessment obligations.")

        findings = _build_review_findings(profile, citations)
        return chapters, issues, findings

    def generate_report(self, payload: SCCRequest) -> SCCResult:
        profile = self._build_profile(payload)
        chapters, issues, findings = self._generate_chapters(profile)
        alignment_issues = check_cn_alignment(
            "\n".join(chapter.content for chapter in chapters),
            receiver_country=profile.receiver_country,
        )
        if alignment_issues:
            issues.extend(alignment_issues)
            for text in alignment_issues:
                findings.append(
                    {
                        "location": "全文一致性校验",
                        "quote": "生成内容与输入字段冲突。",
                        "issue_type": "与输入不一致",
                        "risk_level": "MEDIUM",
                        "risk_analysis": text,
                        "basis": "内部一致性校验规则",
                        "suggestion": "按输入字段重写对应段落，禁止引入未提供国家/行业事实。",
                    }
                )

        date_stamp = format_date_stamp()
        safe_company = safe_filename(payload.company_name)
        md_output = Path("outputs/scc") / f"{safe_company}_SCC_合规审查报告_草案_{date_stamp}.md"
        docx_output = Path("outputs/scc") / f"{safe_company}_SCC_合规审查报告_草案_{date_stamp}.docx"
        mapping = _build_scc_template_mapping(
            profile,
            chapters,
            findings,
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


def _build_scc_template_mapping(
    profile: SCCProfile,
    chapters: list[SCCChapter],
    findings: list[dict[str, str]],
    date_stamp: str,
    alignment_warning: str | None = None,
) -> dict[str, str]:
    def pick(title: str) -> str:
        for chapter in chapters:
            if chapter.title == title:
                return chapter.content
        return ""

    citations: list[str] = []
    for chapter in chapters:
        if chapter.citations:
            citations = chapter.citations
            break

    rating = _resolve_rating(profile, findings)
    executive_summary = summarize_for_slot(pick("总体合规评级"), max_sentences=2, max_chars=220)
    if not executive_summary or executive_summary == "未提供":
        executive_summary = (
            f"本次对 {profile.company_name} 的SCC草案进行合规审查，当前总体评级为{rating}，"
            "建议按高风险条款优先整改后再进入备案流程。"
        )
    revision_recommendations = summarize_for_slot(pick("修订建议与行动计划"), max_sentences=2, max_chars=260)
    if not revision_recommendations or revision_recommendations == "未提供":
        revision_recommendations = "请按问题清单逐条修订，形成版本差异说明并留存审查记录。"

    legal_references = "\n".join(f"- {item}" for item in citations) or "- 未检索到"
    issue_table = _format_issue_table(findings)

    if alignment_warning:
        executive_summary = f"【输入对齐告警】{alignment_warning}\n{executive_summary}".strip()

    contract_name = Path(profile.extracted_notes[0].split(":", 1)[0]).name if profile.extracted_notes else f"{profile.company_name}_SCC草案"
    contract_version = "draft-v1" if profile.has_scc_draft else "未提供"

    return {
        "contract_name": contract_name,
        "contract_version": contract_version,
        "review_date": date_stamp,
        "legal_references": legal_references,
        "overall_rating": rating,
        "executive_summary": attach_citations(executive_summary, citations),
        "issue_table": issue_table,
        "revision_recommendations": attach_citations(revision_recommendations, citations),
    }


def _build_review_findings(profile: SCCProfile, citations: list[str]) -> list[dict[str, str]]:
    basis = citations[0] if citations else "未检索到"
    findings: list[dict[str, str]] = []

    if not profile.has_scc_draft:
        findings.append(
            {
                "location": "合同主文/附件",
                "quote": "未提供可审查的SCC草案文本。",
                "issue_type": "缺失条款",
                "risk_level": "HIGH",
                "risk_analysis": "缺少合同文本会导致无法完成条款级定位审查，备案材料不具备提交条件。",
                "basis": basis,
                "suggestion": "先补齐SCC完整文本（含附件），再执行逐条款审查与修订。",
            }
        )

    if profile.spi_count > 0:
        findings.append(
            {
                "location": "附录II 技术与组织措施",
                "quote": "敏感个人信息处理条款可能不足（需明确加密、访问控制与审计机制）。",
                "issue_type": "定义模糊",
                "risk_level": "MEDIUM",
                "risk_analysis": "涉及敏感个人信息但缺少专项控制条款，存在权利侵害与监管质疑风险。",
                "basis": basis,
                "suggestion": "增加敏感个人信息最小化处理、传输加密与访问留痕条款。",
            }
        )

    if profile.pii_count >= 1_000_000 or profile.spi_count >= 10_000:
        findings.append(
            {
                "location": "路径适用性说明",
                "quote": "出境规模可能达到强制安全评估阈值。",
                "issue_type": "与法规冲突",
                "risk_level": "HIGH",
                "risk_analysis": "若实际触发评估门槛仍采用SCC备案路径，可能导致路径适用错误。",
                "basis": basis,
                "suggestion": "先完成路径复核；触发门槛时应转入安全评估流程。",
            }
        )

    if not findings:
        findings.append(
            {
                "location": "合同整体",
                "quote": "未发现阻断性问题。",
                "issue_type": "完善建议",
                "risk_level": "LOW",
                "risk_analysis": "当前输入范围内未命中高风险缺口，但仍需持续复核合同版本变更。",
                "basis": basis,
                "suggestion": "保持季度复核，并记录每次版本差异与评审意见。",
            }
        )
    return findings


def _resolve_rating(profile: SCCProfile, findings: list[dict[str, str]]) -> str:
    levels = {item["risk_level"] for item in findings}
    if not profile.has_scc_draft or "HIGH" in levels:
        return "高风险"
    if "MEDIUM" in levels:
        return "部分合规"
    return "基本合规"


def _format_issue_table(findings: list[dict[str, str]]) -> str:
    header = (
        "| 定位 | 原文引用 | 问题类型 | 风险等级 | 风险分析 | 法规/标准依据 | 修改建议 |\n"
        "| --- | --- | --- | --- | --- | --- | --- |"
    )
    rows: list[str] = [header]
    for item in findings:
        row = "| {location} | {quote} | {issue_type} | {risk_level} | {risk_analysis} | {basis} | {suggestion} |".format(
            location=_sanitize_cell(item["location"]),
            quote=_sanitize_cell(item["quote"]),
            issue_type=_sanitize_cell(item["issue_type"]),
            risk_level=_sanitize_cell(item["risk_level"]),
            risk_analysis=_sanitize_cell(item["risk_analysis"]),
            basis=_sanitize_cell(item["basis"]),
            suggestion=_sanitize_cell(item["suggestion"]),
        )
        rows.append(row)
    return "\n".join(rows)


def _sanitize_cell(value: str) -> str:
    return (value or "").replace("|", "/").replace("\n", " ").strip()
