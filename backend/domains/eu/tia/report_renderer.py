"""TIA report renderer — output orchestration only.

Extracted from ``service.py`` per the migration plan §11: a module must not keep
DocumentIR conversion, business judgment, and file writing inside one service
function.  This module owns *only* file layout, template rendering, and the
schema-first compiler gate.  It makes no business decisions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from zipfile import ZIP_DEFLATED, ZipFile

from backend.common.citation.output import write_citation_map_json
from backend.common.render.report import (
    format_date_stamp,
    render_docx_template,
    render_markdown_template,
    safe_filename,
)
from backend.core.resource_paths import report_template_path
from backend.domains.eu.tia.schema import TIAChapter, TIARequest

if TYPE_CHECKING:
    from backend.common.citation.registry import CitationRegistry

TEMPLATE_PATH = report_template_path("eu", "3.4_tia_template_v0.docx")
TEMPLATE_MD = report_template_path("eu", "3.4_tia_template_v0.md")


def build_template_mapping(payload: TIARequest, chapters: list[TIAChapter]) -> dict[str, str]:
    """Map chapter content onto template slots.

    Moved verbatim from ``service._build_template_mapping`` so rendered output
    stays byte-identical.
    """
    def pick(no: int) -> str:
        for ch in chapters:
            if ch.chapter_no == no:
                return ch.content
        return ""

    final_parts = [pick(5), pick(6)]
    proposed_label = "用户提交的拟定结论（不构成系统批准）"
    final_text = "\n".join(filter(None, final_parts))
    if payload.final_conclusion in final_text:
        if proposed_label not in final_text:
            final_text = final_text.replace(
                payload.final_conclusion,
                f"{proposed_label}：\n{payload.final_conclusion}",
                1,
            )
    else:
        final_text = "\n".join(filter(None, [
            final_text,
            f"{proposed_label}：\n{payload.final_conclusion}",
        ]))

    return {
        "transfer_context": pick(1) or f"{payload.data_exporter_profile} -> {payload.data_importer_profile}",
        "transfer_tool": pick(2) or payload.transfer_tool,
        "third_country_analysis": pick(3) or payload.third_country_assessment,
        "supplementary_measures": pick(4) or payload.supplementary_measures,
        "final_assessment": final_text,
    }


def _write_document_ir_json(document_ir, output_dir: Path) -> str:
    """Persist the typed DocumentIR as an internal (non-user-facing) artifact."""
    path = output_dir / "document_ir.json"
    path.write_text(
        json.dumps(document_ir.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(path)


class TIAReportRenderer:
    """Render TIA outputs: MD/DOCX/PDF drafts, CitationMap, and the ZIP bundle."""

    def __init__(
        self,
        *,
        schema_first_enabled: bool = False,
        model_name: str = "legacy-tia",
    ) -> None:
        self.schema_first_enabled = schema_first_enabled
        self.model_name = model_name

    def render(
        self,
        task_id: str,
        payload: TIARequest,
        chapters: list[TIAChapter],
        attachment_notes: list[str],
        citation_registry: "CitationRegistry",
    ) -> dict[str, str]:
        output_dir = Path("outputs/tia") / task_id / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)

        document_ir = None
        if self.schema_first_enabled:
            from backend.common.citation.registry import CitationRegistry as LegacyCitationRegistry
            from backend.common.reporting import DocumentCompiler
            from backend.domains.eu.tia.schema_first import build_tia_document_ir

            document_ir, reporting_registry = build_tia_document_ir(
                task_id=task_id,
                exporter_profile=payload.data_exporter_profile,
                chapters=chapters,
                citation_registry=citation_registry or LegacyCitationRegistry(),
                model=self.model_name,
            )
            compile_result = DocumentCompiler().compile(document_ir, reporting_registry)
            if compile_result.status != "success":
                codes = ", ".join(item.code for item in compile_result.diagnostics)
                raise ValueError(f"Schema-first compiler blocked TIA output: {codes}")

        date_stamp = format_date_stamp()
        base_name = safe_filename(f"{payload.data_exporter_profile}_{payload.transfer_tool}_TIA")
        md_output = output_dir / f"{base_name}_报告_草案_{date_stamp}.md"
        docx_output = output_dir / f"{base_name}_报告_草案_{date_stamp}.docx"
        pdf_output = output_dir / f"{base_name}_报告_草案_{date_stamp}.pdf"
        zip_output = output_dir / f"{base_name}_输出包_草案_{date_stamp}.zip"

        mapping = build_template_mapping(payload, chapters)
        render_markdown_template(md_output, TEMPLATE_MD, mapping)
        render_docx_template(docx_output, TEMPLATE_PATH, mapping)

        from backend.common.render.pdf_renderer import get_pdf_renderer

        get_pdf_renderer().from_template(
            pdf_output,
            f"{payload.data_exporter_profile} TIA 报告草案",
            TEMPLATE_MD,
            mapping,
        )

        result: dict[str, str] = {
            "markdown": str(md_output),
            "docx": str(docx_output),
            "pdf": str(pdf_output),
            "zip": str(zip_output),
        }

        document_ir_path: str | None = None
        if document_ir is not None:
            document_ir_path = _write_document_ir_json(document_ir, output_dir)
            result["document_ir_json"] = document_ir_path

        with ZipFile(zip_output, mode="w", compression=ZIP_DEFLATED) as bundle:
            bundle.write(docx_output, arcname=docx_output.name)
            bundle.write(md_output, arcname=md_output.name)
            bundle.write(pdf_output, arcname=pdf_output.name)
            if document_ir_path is not None:
                bundle.write(document_ir_path, arcname=Path(document_ir_path).name)

        footnote_map = {
            str(num): item.to_dict()
            for num, item in citation_registry.get_footnote_map().items()
        }
        result["citation_map_json"] = write_citation_map_json(
            output_dir=output_dir,
            module="tia",
            task_id=task_id,
            footnote_map=footnote_map,
            all_items=citation_registry.to_list(),
        )
        return result
