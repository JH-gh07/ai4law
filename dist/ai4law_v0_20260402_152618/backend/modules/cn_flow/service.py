from __future__ import annotations

from pathlib import Path

from backend.common.llm.adapter import LLMAdapter
from backend.common.rag.retriever import retrieve_regulations
from backend.common.render.artifacts import bundle_files, render_pdf_report, render_simple_xlsx
from backend.common.render.report import render_docx_report, render_markdown_report
from backend.common.storage.file_parser import FileParser
from backend.common.tasks.manager import InMemoryTaskManager, TaskSnapshot
from backend.modules.cn_flow.schema import (
    CNFlowAsyncAccepted,
    CNFlowAsyncStatus,
    CNFlowChapter,
    CNFlowRequest,
    CNFlowResult,
    CNFlowRiskItem,
)


CN_FLOW_CHAPTERS = [
    "场景定义与适用范围",
    "数据类型与实体结构分析",
    "限制条件命中分析",
    "风险分级与处置建议",
]


class CNFlowService:
    def __init__(self) -> None:
        self.llm = LLMAdapter()
        self.parser = FileParser()
        self.tasks = InMemoryTaskManager(module="cn_flow")

    def generate_report(self, payload: CNFlowRequest) -> CNFlowResult:
        risk_items = self._build_risk_items(payload)
        risk_level = self._resolve_overall_level(risk_items)
        regs = retrieve_regulations("EO 14117 US China data flow restricted transactions", top_k=4)
        citations = [f"{item.title}{item.article}" for item in regs]
        attachment_notes = self._extract_attachment_notes(payload)
        chapters = self._generate_chapters(payload, risk_level, risk_items, citations)
        issues = self._check_consistency(payload, risk_items)
        outputs = self._render(payload, chapters, risk_items, attachment_notes)
        return CNFlowResult(
            report_path=outputs["docx"],
            output_files=outputs,
            company_name=payload.company_name,
            risk_level=risk_level,
            risk_items=risk_items,
            chapters=chapters,
            consistency_issues=issues,
            attachment_notes=attachment_notes,
        )

    def submit_async(self, payload: CNFlowRequest) -> CNFlowAsyncAccepted:
        snapshot = self.tasks.submit(lambda: self.generate_report(payload))
        return self._snapshot_to_accepted(snapshot)

    def get_async_status(self, task_id: str) -> CNFlowAsyncStatus:
        snapshot = self.tasks.get_or_raise(task_id)
        return self._snapshot_to_status(snapshot)

    def retry_async(self, task_id: str) -> CNFlowAsyncStatus:
        snapshot = self.tasks.retry(task_id)
        return self._snapshot_to_status(snapshot)

    def cancel_async(self, task_id: str) -> CNFlowAsyncStatus:
        snapshot = self.tasks.cancel(task_id)
        return self._snapshot_to_status(snapshot)

    @staticmethod
    def _resolve_overall_level(items: list[CNFlowRiskItem]) -> str:
        levels = {item.risk_level for item in items}
        if "HIGH" in levels:
            return "HIGH"
        if "MEDIUM" in levels:
            return "MEDIUM"
        return "LOW"

    def _build_risk_items(self, payload: CNFlowRequest) -> list[CNFlowRiskItem]:
        items: list[CNFlowRiskItem] = []
        if payload.sensitive_data_flags:
            items.append(
                CNFlowRiskItem(
                    risk_id="CNF-R1",
                    risk_level="HIGH",
                    title="存在敏感数据跨境流动",
                    basis="EO 14117 敏感数据外流限制框架",
                    recommendation="优先评估敏感字段脱敏、最小化及本地化处理方案。",
                    affected_entities=[entity.entity_name for entity in payload.recipient_entities],
                )
            )
        restricted = [entity.entity_name for entity in payload.recipient_entities if entity.is_restricted_party]
        if restricted:
            items.append(
                CNFlowRiskItem(
                    risk_id="CNF-R2",
                    risk_level="HIGH",
                    title="接收方存在受限主体风险",
                    basis="受限交易与第三方尽调要求",
                    recommendation="暂停向受限主体传输，补齐尽调与审批记录。",
                    affected_entities=restricted,
                )
            )
        if "subprocessor" in payload.transfer_chain.lower() or "第三方" in payload.transfer_chain:
            items.append(
                CNFlowRiskItem(
                    risk_id="CNF-R3",
                    risk_level="MEDIUM",
                    title="传输链路复杂导致控制断点",
                    basis="跨实体/再传输控制要求",
                    recommendation="明确 onward transfer 约束与监控机制，补充链路审计。",
                    affected_entities=[entity.entity_name for entity in payload.recipient_entities],
                )
            )
        if not items:
            items.append(
                CNFlowRiskItem(
                    risk_id="CNF-R0",
                    risk_level="LOW",
                    title="暂未识别高风险触发条件",
                    basis="输入范围内未命中高风险规则",
                    recommendation="保持季度复审并持续监控接收方变化。",
                    affected_entities=[entity.entity_name for entity in payload.recipient_entities],
                )
            )
        return items

    def _extract_attachment_notes(self, payload: CNFlowRequest) -> list[str]:
        notes: list[str] = []
        for item in payload.attachments:
            try:
                text = self.parser.parse_text(item.storage_uri)
                notes.append(f"{item.file_name}: {text[:160].replace(chr(10), ' ')}")
            except (FileNotFoundError, ValueError) as exc:
                notes.append(f"{item.file_name}: [parse skipped] {exc}")
        return notes

    def _generate_chapters(
        self,
        payload: CNFlowRequest,
        level: str,
        risk_items: list[CNFlowRiskItem],
        citations: list[str],
    ) -> list[CNFlowChapter]:
        items_summary = "；".join(f"{item.risk_id}-{item.title}" for item in risk_items)
        chapters: list[CNFlowChapter] = []
        for idx, title in enumerate(CN_FLOW_CHAPTERS, start=1):
            summary = self.llm.summarize(
                title=title,
                bullet_points=[
                    f"企业：{payload.company_name}",
                    f"传输目的：{payload.transfer_purpose}",
                    f"数据类别：{', '.join(payload.data_categories)}",
                    f"链路：{payload.transfer_chain}",
                    f"风险概要：{items_summary}",
                    f"风险等级：{level}",
                ],
            )
            chapters.append(
                CNFlowChapter(
                    chapter_no=idx,
                    title=title,
                    content=summary.text,
                    citations=citations,
                    risk_level=level,
                )
            )
        return chapters

    @staticmethod
    def _check_consistency(payload: CNFlowRequest, risk_items: list[CNFlowRiskItem]) -> list[str]:
        issues: list[str] = []
        required_roles = {item.file_role for item in payload.attachments}
        if "data_inventory" not in required_roles:
            issues.append("Missing required attachment role: data_inventory")
        if "entity_inventory" not in required_roles:
            issues.append("Missing required attachment role: entity_inventory")
        if any(item.risk_level == "HIGH" for item in risk_items):
            issues.append("Contains HIGH risk items; recommend legal escalation before execution.")
        return issues

    def _render(
        self,
        payload: CNFlowRequest,
        chapters: list[CNFlowChapter],
        risk_items: list[CNFlowRiskItem],
        attachment_notes: list[str],
    ) -> dict[str, str]:
        sections: list[tuple[str, str]] = [
            ("输入摘要", payload.model_dump_json(indent=2)),
            ("风险清单摘要", "\n".join(f"- {item.risk_id}: {item.title}" for item in risk_items)),
            ("附件解析摘要", "\n".join(f"- {item}" for item in attachment_notes) or "- 无"),
        ]
        for chapter in chapters:
            sections.append((f"第{chapter.chapter_no}章 {chapter.title}", chapter.content))

        output_dir = Path("outputs/cn_flow")
        base = payload.company_name
        md_output = output_dir / f"{base}_cn_flow_compliance_report.md"
        docx_output = output_dir / f"{base}_cn_flow_compliance_report.docx"
        pdf_output = output_dir / f"{base}_cn_flow_compliance_report.pdf"
        xlsx_output = output_dir / f"{base}_cn_flow_risk_list.xlsx"
        zip_output = output_dir / f"{base}_cn_flow_output_bundle.zip"

        render_markdown_report(md_output, "对华数据流动合规报告（v0）", sections)
        render_docx_report(docx_output, "对华数据流动合规报告（v0）", sections)
        render_pdf_report(pdf_output, "对华数据流动合规报告（v0）", sections)
        headers = ["risk_id", "risk_level", "title", "basis", "recommendation", "affected_entities"]
        rows = [
            [
                item.risk_id,
                item.risk_level,
                item.title,
                item.basis,
                item.recommendation,
                "; ".join(item.affected_entities),
            ]
            for item in risk_items
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

    @staticmethod
    def _snapshot_to_accepted(snapshot: TaskSnapshot) -> CNFlowAsyncAccepted:
        return CNFlowAsyncAccepted(
            task_id=snapshot.task_id,
            module=snapshot.module,
            state=snapshot.state,
            attempts=snapshot.attempts,
            max_attempts=snapshot.max_attempts,
        )

    @staticmethod
    def _snapshot_to_status(snapshot: TaskSnapshot) -> CNFlowAsyncStatus:
        result = None
        if snapshot.result is not None:
            result = CNFlowResult.model_validate(snapshot.result)
        return CNFlowAsyncStatus(
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

