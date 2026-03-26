from pathlib import Path

from backend.common.render.report import render_docx_report, render_markdown_report
from backend.modules.assessment.schema import ChapterContent, CompanyProfile, RegulationHit


class AssessmentReportRenderer:
    def render(
        self,
        company_name: str,
        profile: CompanyProfile,
        regulations: list[RegulationHit],
        chapters: list[ChapterContent],
    ) -> dict[str, str]:
        sections: list[tuple[str, str]] = [
            ("企业画像", profile.model_dump_json(indent=2)),
            (
                "法规命中",
                "\n".join([f"- {hit.title}{hit.article}: {hit.snippet}" for hit in regulations]),
            ),
        ]
        for chapter in chapters:
            sections.append((f"第{chapter.chapter_no}章 {chapter.title}", chapter.content))
        md_output = Path("outputs/assessment") / f"{company_name}_security_assessment_report.md"
        docx_output = Path("outputs/assessment") / f"{company_name}_security_assessment_report.docx"
        render_markdown_report(md_output, "数据出境风险自评估报告（v0）", sections)
        render_docx_report(docx_output, "数据出境风险自评估报告（v0）", sections)
        return {"markdown": str(md_output), "docx": str(docx_output)}
