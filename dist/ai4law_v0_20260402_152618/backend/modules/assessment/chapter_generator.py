from backend.common.llm.adapter import LLMAdapter
from backend.common.risk.scoring import risk_level
from backend.modules.assessment.schema import ChapterContent, CompanyProfile, RegulationHit


ASSESSMENT_CHAPTERS = [
    "出境活动概述",
    "数据类型与规模",
    "出境必要性与合法性基础",
    "境外接收方保障能力",
    "个人信息权益影响分析",
    "安全措施与传输机制",
    "剩余风险与整改建议",
    "综合评估结论",
]


class AssessmentChapterGenerator:
    def __init__(self) -> None:
        self.llm = LLMAdapter()

    def generate(self, profile: CompanyProfile, hits: list[RegulationHit]) -> list[ChapterContent]:
        level = risk_level(
            is_ciio=profile.is_ciio,
            contains_important_data=profile.contains_important_data,
            pii_count=profile.pii_count,
            spi_count=profile.spi_count,
        )
        citation_keys = [f"{hit.title}{hit.article}" for hit in hits[:3]]
        chapters: list[ChapterContent] = []
        for idx, chapter_title in enumerate(ASSESSMENT_CHAPTERS, start=1):
            summary = self.llm.summarize(
                title=chapter_title,
                bullet_points=[
                    f"企业：{profile.company_name}",
                    f"目的：{profile.transfer_purpose}",
                    f"接收方国家：{profile.receiver_country}",
                    f"风险等级：{level}",
                ],
            )
            content = (
                f"{summary.text}\n\n"
                f"本章基于企业画像与法规检索结果生成，用于 v0 可验收版本演示。"
            )
            chapters.append(
                ChapterContent(
                    chapter_no=idx,
                    title=chapter_title,
                    content=content,
                    citations=citation_keys,
                    risk_level=level,
                )
            )
        return chapters
