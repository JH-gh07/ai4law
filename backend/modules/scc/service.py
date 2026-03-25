from pathlib import Path

from backend.common.llm.adapter import LLMAdapter
from backend.common.rag.retriever import retrieve_regulations
from backend.common.render.report import render_markdown_report
from backend.common.risk.scoring import risk_level
from backend.common.storage.file_parser import FileParser
from backend.modules.scc.schema import SCCChapter, SCCProfile, SCCRequest, SCCResult


SCC_CHAPTERS = [
    "处理活动与出境背景",
    "个人信息类型与规模",
    "境外接收方保护能力",
    "合同与组织措施",
    "个人信息权益影响分析",
    "PIPIA 结论与备案建议",
]


class SCCService:
    def __init__(self) -> None:
        self.llm = LLMAdapter()
        self.parser = FileParser()

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
        )
        citations = [f"{item.title}{item.article}" for item in regs]

        chapters: list[SCCChapter] = []
        for idx, title in enumerate(SCC_CHAPTERS, start=1):
            summary = self.llm.summarize(
                title=title,
                bullet_points=[
                    f"企业：{profile.company_name}",
                    f"接收方：{profile.receiver_name} ({profile.receiver_country})",
                    f"用途：{profile.transfer_purpose}",
                    f"风险等级：{level}",
                ],
            )
            chapters.append(
                SCCChapter(
                    chapter_no=idx,
                    title=title,
                    content=summary.text,
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

        sections: list[tuple[str, str]] = [("SCC 企业画像", profile.model_dump_json(indent=2))]
        for chapter in chapters:
            sections.append((f"第{chapter.chapter_no}章 {chapter.title}", chapter.content))

        output = Path("outputs/scc") / f"{payload.company_name}_pipia_report.md"
        render_markdown_report(output, "个人信息保护影响评估报告（PIPIA, v0）", sections)

        return SCCResult(
            report_path=str(output),
            profile=profile,
            chapters=chapters,
            consistency_issues=issues,
        )
