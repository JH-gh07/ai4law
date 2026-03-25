from pathlib import Path

from backend.common.render.report import render_markdown_report
from backend.modules.assessment.schema import ChapterContent, CompanyProfile, RegulationHit


class AssessmentReportRenderer:
    def render(
        self,
        company_name: str,
        profile: CompanyProfile,
        regulations: list[RegulationHit],
        chapters: list[ChapterContent],
    ) -> Path:
        sections: list[tuple[str, str]] = [
            ("企业画像", profile.model_dump_json(indent=2)),
            (
                "法规命中",
                "\n".join([f"- {hit.title}{hit.article}: {hit.snippet}" for hit in regulations]),
            ),
        ]
        for chapter in chapters:
            sections.append((f"第{chapter.chapter_no}章 {chapter.title}", chapter.content))
        output = Path("outputs/assessment") / f"{company_name}_security_assessment_report.md"
        return render_markdown_report(output, "数据出境风险自评估报告（v0）", sections)
