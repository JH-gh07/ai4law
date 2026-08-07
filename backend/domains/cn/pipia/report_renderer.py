"""PIPIA report renderer — output orchestration only.

Extracted from ``PIPIAService._render`` (service.py line 579).
The renderer owns file layout, template rendering, and the schema-first
compiler gate.  It makes no business decisions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from zipfile import ZIP_DEFLATED, ZipFile

from backend.common.render.report import (
    format_date_stamp,
    render_docx_report,
    render_docx_template,
    render_markdown_report,
    render_markdown_template,
    safe_filename,
)
from backend.common.render.summary import attach_citations, summarize_for_slot
from backend.common.risk.scoring import risk_level
from backend.core.resource_paths import report_template_path
from backend.domains.cn.pipia.schema import PIPIAChapter, PIPIARequest

if TYPE_CHECKING:
    from backend.common.workflow import EvidenceItem, FactItem, IssueItem

TEMPLATE_PATH = report_template_path("cn", "2.3_pipia_template_v0.docx")
TEMPLATE_MD = report_template_path("cn", "2.3_pipia_template_v0.md")


def _write_document_ir_json(document_ir, output_dir: Path) -> str:
    path = output_dir / "document_ir.json"
    path.write_text(
        json.dumps(document_ir.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(path)


def _fallback_sections(
    payload: PIPIARequest,
    chapters: list[PIPIAChapter],
    overall_risk_level: str,
    attachment_notes: list[str],
) -> list[tuple[str, str]]:
    """Verbatim copy of PIPIAService._fallback_sections for byte-equivalence."""
    sections: list[tuple[str, str]] = [
        (
            "基础信息",
            "\n".join([
                f"- 企业名称：{payload.company_profile.company_name}",
                f"- 合规路径：{payload.route_type}",
                f"- 境外接收方：{payload.transfer_context.recipient_name}（{payload.transfer_context.recipient_country_region}）",
                f"- 出境目的：{payload.transfer_context.purpose}",
                f"- 风险等级：{overall_risk_level}",
            ]),
        )
    ]
    for chapter in chapters:
        sections.append((chapter.title, chapter.content))
    if attachment_notes:
        sections.append(("附件摘要", "\n".join(f"- {note}" for note in attachment_notes)))
    return sections
    path = output_dir / "document_ir.json"
    path.write_text(
        json.dumps(document_ir.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(path)


class PIPIAReportRenderer:
    """Render PIPIA outputs: MD, DOCX, PDF, and ZIP bundle."""

    def __init__(
        self,
        *,
        schema_first_enabled: bool = False,
        model_name: str = "legacy-pipia",
    ) -> None:
        self.schema_first_enabled = schema_first_enabled
        self.model_name = model_name

    def render(
        self,
        task_id: str,
        payload: PIPIARequest,
        chapters: list[PIPIAChapter],
        overall_risk_level: str,
        attachment_notes: list[str],
        alignment_warning: str | None = None,
        issues: "list[IssueItem] | None" = None,
        evidence_chain: "list[EvidenceItem] | None" = None,
        facts: "list[FactItem] | None" = None,
        filing_readiness: "object | None" = None,
        consistency_issues: list[str] | None = None,
    ) -> dict[str, str]:
        output_dir = Path("outputs/pipia") / task_id / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)

        document_ir = None
        if self.schema_first_enabled:
            from backend.common.citation.registry import CitationRegistry as LegacyCitationRegistry
            from backend.common.reporting import DocumentCompiler
            from backend.domains.cn.pipia.schema_first import build_pipia_document_ir

            document_ir, reporting_registry = build_pipia_document_ir(
                task_id=task_id,
                company_name=payload.company_profile.company_name,
                chapters=chapters,
                citation_registry=LegacyCitationRegistry(),
                model=self.model_name,
            )
            compile_result = DocumentCompiler().compile(document_ir, reporting_registry)
            if compile_result.status != "success":
                codes = ", ".join(item.code for item in compile_result.diagnostics)
                raise ValueError(f"Schema-first compiler blocked PIPIA output: {codes}")

        from backend.domains.cn.pipia.service import _build_template_mapping

        date_stamp = format_date_stamp()
        safe_company = safe_filename(payload.company_profile.company_name)
        md_output = output_dir / f"{safe_company}_PIPIA_报告_草案_{date_stamp}.md"
        docx_output = output_dir / f"{safe_company}_PIPIA_报告_草案_{date_stamp}.docx"
        pdf_output = output_dir / f"{safe_company}_PIPIA_报告_草案_{date_stamp}.pdf"
        zip_output = output_dir / f"{safe_company}_PIPIA_输出包_草案_{date_stamp}.zip"

        mapping = _build_template_mapping(
            payload, chapters, date_stamp, overall_risk_level, alignment_warning
        )

        if TEMPLATE_MD.exists():
            render_markdown_template(md_output, TEMPLATE_MD, mapping)
        else:
            render_markdown_report(
                md_output,
                f"{payload.company_profile.company_name} PIPIA 报告草案",
                _fallback_sections(payload, chapters, overall_risk_level, attachment_notes),
            )
        if TEMPLATE_PATH.exists():
            render_docx_template(docx_output, TEMPLATE_PATH, mapping)
        else:
            render_docx_report(
                docx_output,
                f"{payload.company_profile.company_name} PIPIA 报告草案",
                _fallback_sections(payload, chapters, overall_risk_level, attachment_notes),
            )
        from backend.common.render.pdf_renderer import get_pdf_renderer

        if TEMPLATE_MD.exists():
            get_pdf_renderer().from_template(
                pdf_output,
                f"{payload.company_profile.company_name} PIPIA 报告草案",
                TEMPLATE_MD,
                mapping,
            )
        else:
            get_pdf_renderer().from_sections(
                pdf_output,
                f"{payload.company_profile.company_name} PIPIA 报告草案",
                _fallback_sections(payload, chapters, overall_risk_level, attachment_notes),
            )

        result: dict[str, str] = {
            "markdown": str(md_output),
            "docx": str(docx_output),
            "pdf": str(pdf_output),
            "zip": str(zip_output),
        }

        if document_ir is not None:
            result["document_ir_json"] = _write_document_ir_json(document_ir, output_dir)

        with ZipFile(zip_output, mode="w", compression=ZIP_DEFLATED) as bundle:
            bundle.write(md_output, arcname=md_output.name)
            bundle.write(docx_output, arcname=docx_output.name)
            bundle.write(pdf_output, arcname=pdf_output.name)
            if document_ir is not None:
                ir_path = Path(result["document_ir_json"])
                bundle.write(ir_path, arcname=ir_path.name)

        return result
