from __future__ import annotations

from pathlib import Path

from backend.common.llm.client import LLMClient
from backend.common.llm.module_generator import generate_chapter
from backend.common.rag.retriever import retrieve_regulations
from backend.common.render.artifacts import bundle_files, render_pdf_report, render_simple_xlsx
from backend.common.render.report import (
    format_date_stamp,
    render_docx_template,
    render_markdown_template,
    safe_filename,
)
from backend.common.storage.file_parser import FileParser
from backend.common.tasks.manager import InMemoryTaskManager, TaskSnapshot
from backend.modules.cpra.schema import (
    CPRAAsyncAccepted,
    CPRAAsyncStatus,
    CPRAChapter,
    CPRAGapItem,
    CPRARequest,
    CPRAResult,
)

TEMPLATE_PATH = Path("doc/v2/assets/templates/4.2_cpra_panorama_template_v0.docx")
TEMPLATE_MD = Path("doc/v2/assets/templates/4.2_cpra_panorama_template_v0.md")


CPRA_CHAPTERS = [
    "执行摘要",
    "企业适用性与范围",
    "数据处理活动合规分析",
    "消费者权利保障评估",
    "敏感信息与第三方管理",
    "行动清单与优先级",
]


class CPRAService:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        if llm_client is None:
            from backend.core.settings import get_settings
            llm_client = LLMClient(get_settings())
        self.llm_client = llm_client
        self.parser = FileParser()
        self.tasks = InMemoryTaskManager(module="cpra")

    def generate_report(self, payload: CPRARequest) -> CPRAResult:
        gap_items = self._build_gap_items(payload)
        risk_level = self._resolve_overall_level(gap_items)
        regs = retrieve_regulations(
            "CPRA CCPA consumer rights sale sharing SPI",
            top_k=4,
            jurisdiction="us",
            path="all",
        )
        citations = [f"{item.title}{item.article}" for item in regs]
        reg_snippet = "\n".join(
            f"- {item.title}{item.article}：{(item.content or '')[:120]}"
            for item in regs
        ) or "（暂无检索到相关法条）"
        attachment_notes = self._extract_attachment_notes(payload)
        chapters = self._generate_chapters(payload, risk_level, gap_items, citations, reg_snippet)
        issues = self._check_consistency(payload, gap_items)
        outputs = self._render(payload, chapters, gap_items, attachment_notes)
        return CPRAResult(
            report_path=outputs["docx"],
            output_files=outputs,
            company_name=payload.company_name,
            risk_level=risk_level,
            gap_items=gap_items,
            chapters=chapters,
            consistency_issues=issues,
            attachment_notes=attachment_notes,
        )

    def submit_async(self, payload: CPRARequest) -> CPRAAsyncAccepted:
        snapshot = self.tasks.submit(lambda: self.generate_report(payload))
        return self._snapshot_to_accepted(snapshot)

    def get_async_status(self, task_id: str) -> CPRAAsyncStatus:
        snapshot = self.tasks.get_or_raise(task_id)
        return self._snapshot_to_status(snapshot)

    def retry_async(self, task_id: str) -> CPRAAsyncStatus:
        snapshot = self.tasks.retry(task_id)
        return self._snapshot_to_status(snapshot)

    def cancel_async(self, task_id: str) -> CPRAAsyncStatus:
        snapshot = self.tasks.cancel(task_id)
        return self._snapshot_to_status(snapshot)

    @staticmethod
    def _snapshot_to_accepted(snapshot: TaskSnapshot) -> CPRAAsyncAccepted:
        return CPRAAsyncAccepted(
            task_id=snapshot.task_id,
            module=snapshot.module,
            state=snapshot.state,
            attempts=snapshot.attempts,
            max_attempts=snapshot.max_attempts,
        )

    @staticmethod
    def _snapshot_to_status(snapshot: TaskSnapshot) -> CPRAAsyncStatus:
        result = None
        if snapshot.result is not None:
            result = CPRAResult.model_validate(snapshot.result)
        return CPRAAsyncStatus(
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
    def _resolve_overall_level(items: list[CPRAGapItem]) -> str:
        levels = {item.risk_level for item in items}
        if "HIGH" in levels:
            return "HIGH"
        if "MEDIUM" in levels:
            return "MEDIUM"
        return "LOW"

    def _build_gap_items(self, payload: CPRARequest) -> list[CPRAGapItem]:
        items: list[CPRAGapItem] = []
        notice_text = payload.notice_and_consent.lower()
        rights_text = payload.consumer_rights_process.lower()
        sale_text = payload.opt_out_and_sale_sharing.lower()
        vendor_text = payload.vendor_management.lower()

        if any(token in notice_text for token in ("缺失", "无", "none")):
            items.append(
                CPRAGapItem(
                    domain="notice_and_consent",
                    risk_level="HIGH",
                    gap="隐私告知或同意机制不完整",
                    legal_basis="CPRA Notice at Collection 要求",
                    recommendation="补齐分场景告知文本与同意留痕机制。",
                    phase="short_term",
                )
            )
        if "45" not in rights_text and "sla" not in rights_text:
            items.append(
                CPRAGapItem(
                    domain="consumer_rights_process",
                    risk_level="MEDIUM",
                    gap="消费者权利响应时限与SLA未明确",
                    legal_basis="CPRA 消费者权利响应时限要求",
                    recommendation="建立统一DSR流程并设置45天响应时限监控。",
                    phase="short_term",
                )
            )
        if any(token in sale_text for token in ("yes", "是", "出售", "共享")) and "opt-out" not in sale_text:
            items.append(
                CPRAGapItem(
                    domain="opt_out_and_sale_sharing",
                    risk_level="HIGH",
                    gap="存在出售/共享但未明确 opt-out 机制",
                    legal_basis="CPRA Sale/Sharing opt-out 要求",
                    recommendation="上线 Do Not Sell/Share 链接并记录执行日志。",
                    phase="short_term",
                )
            )
        if payload.vendor_management and "dpa" not in vendor_text:
            items.append(
                CPRAGapItem(
                    domain="vendor_management",
                    risk_level="MEDIUM",
                    gap="供应商管理未体现 DPA/服务商条款",
                    legal_basis="CPRA 服务商与第三方管理要求",
                    recommendation="补齐供应商分类与DPA签署台账。",
                    phase="mid_term",
                )
            )
        if not items:
            items.append(
                CPRAGapItem(
                    domain="overall",
                    risk_level="LOW",
                    gap="未识别明显高风险差距",
                    legal_basis="输入范围内未命中高风险规则",
                    recommendation="保持半年复审并更新证据材料。",
                    phase="long_term",
                )
            )
        return items

    def _extract_attachment_notes(self, payload: CPRARequest) -> list[str]:
        notes: list[str] = []
        for item in payload.attachments:
            if item.file_format == "url":
                notes.append(f"{item.file_name}: [url] {item.storage_uri}")
                continue
            try:
                text = self.parser.parse_text(item.storage_uri)
                notes.append(f"{item.file_name}: {text[:160].replace(chr(10), ' ')}")
            except (FileNotFoundError, ValueError) as exc:
                notes.append(f"{item.file_name}: [parse skipped] {exc}")
        return notes

    def _generate_chapters(
        self,
        payload: CPRARequest,
        level: str,
        gap_items: list[CPRAGapItem],
        citations: list[str],
        reg_snippet: str,
    ) -> list[CPRAChapter]:
        gap_summary = "；".join(f"{item.domain}:{item.gap}" for item in gap_items)
        context_block = (
            f"【企业信息】\n"
            f"- 企业名称：{payload.company_name}\n"
            f"- 业务模型：{payload.business_model}\n"
            f"- 数据生命周期：{payload.data_lifecycle}\n"
            f"- 合规差距摘要：{gap_summary}\n"
            f"- 风险等级：{level}\n"
            f"\n【法规参考】\n{reg_snippet}\n"
        )
        chapters: list[CPRAChapter] = []
        for idx, title in enumerate(CPRA_CHAPTERS, start=1):
            if self.llm_client and self.llm_client.enabled:
                content = generate_chapter(self.llm_client, "cpra", title, context_block, citations=citations)
            else:
                content = f"（{title}：LLM未配置，此处为占位内容）"
            chapters.append(
                CPRAChapter(
                    chapter_no=idx,
                    title=title,
                    content=content,
                    citations=citations,
                    risk_level=level,
                )
            )
        return chapters

    @staticmethod
    def _check_consistency(payload: CPRARequest, gap_items: list[CPRAGapItem]) -> list[str]:
        issues: list[str] = []
        has_policy = any(item.file_role == "privacy_policy" for item in payload.attachments)
        if not has_policy:
            issues.append("Missing privacy_policy attachment or URL reference.")
        if any(item.risk_level == "HIGH" for item in gap_items):
            issues.append("Contains HIGH risk gaps; remediation should be scheduled in short_term phase.")
        return issues

    def _render(
        self,
        payload: CPRARequest,
        chapters: list[CPRAChapter],
        gap_items: list[CPRAGapItem],
        attachment_notes: list[str],
    ) -> dict[str, str]:
        sections: list[tuple[str, str]] = [
            ("输入摘要", payload.model_dump_json(indent=2)),
            ("差距清单摘要", "\n".join(f"- {item.domain}: {item.gap}" for item in gap_items)),
            ("附件解析摘要", "\n".join(f"- {item}" for item in attachment_notes) or "- 无"),
        ]
        for chapter in chapters:
            sections.append((f"第{chapter.chapter_no}章 {chapter.title}", chapter.content))

        output_dir = Path("outputs/cpra")
        date_stamp = format_date_stamp()
        base = safe_filename(payload.company_name)
        md_output = output_dir / f"{base}_CPRA_合规全景报告_草案_{date_stamp}.md"
        docx_output = output_dir / f"{base}_CPRA_合规全景报告_草案_{date_stamp}.docx"
        pdf_output = output_dir / f"{base}_CPRA_合规全景报告_草案_{date_stamp}.pdf"
        xlsx_output = output_dir / f"{base}_CPRA_整改路线图_草案_{date_stamp}.xlsx"
        zip_output = output_dir / f"{base}_CPRA_输出包_草案_{date_stamp}.zip"

        mapping = _build_template_mapping(payload, chapters, gap_items, date_stamp)
        render_markdown_template(md_output, TEMPLATE_MD, mapping)
        render_docx_template(docx_output, TEMPLATE_PATH, mapping)
        render_pdf_report(pdf_output, "加州CPRA合规全景报告（草案）", sections)
        headers = ["domain", "risk_level", "gap", "legal_basis", "recommendation", "phase"]
        rows = [
            [item.domain, item.risk_level, item.gap, item.legal_basis, item.recommendation, item.phase]
            for item in gap_items
        ]
        render_simple_xlsx(xlsx_output, headers=headers, rows=rows)
        bundle_files(zip_output, [docx_output, md_output, pdf_output, xlsx_output])
        return {
            "markdown": str(md_output),
            "docx": str(docx_output),
            "pdf": str(pdf_output),
            "xlsx": str(xlsx_output),
            "zip": str(zip_output),
        }


def _build_template_mapping(
    payload: CPRARequest,
    chapters: list[CPRAChapter],
    gap_items: list[CPRAGapItem],
    date_stamp: str,
) -> dict[str, str]:
    def pick(no: int) -> str:
        for chapter in chapters:
            if chapter.chapter_no == no:
                return chapter.content
        return ""

    gap_summary = "; ".join(f"{item.domain}: {item.gap}" for item in gap_items) or "暂无"
    return {
        "current_state": pick(2) or "企业业务与数据处理现状概述。",
        "cpra_mapping": pick(3) or "依据CPRA条款进行映射分析。",
        "gaps_and_risks": pick(4) or gap_summary,
        "remediation_roadmap": pick(6) or "按优先级制定整改路线图。",
        "final_conclusion": pick(1) or f"评估日期：{date_stamp}。",
    }
