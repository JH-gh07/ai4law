from __future__ import annotations

from backend.common.llm.client import LLMClient
from backend.common.llm.postprocess import ensure_paragraph_citations
from backend.common.risk.scoring import risk_level
from backend.modules.assessment.schema import ChapterContent, CompanyProfile, RegulationHit

_SYSTEM_PROMPT = (
    "你是一名专注于中国数据跨境合规的资深律师，深度掌握《个人信息保护法》《数据安全法》"
    "《数据出境安全评估办法》《数据出境安全评估申报指南（第三版）》等法规。"
    "请严格按照《数据出境风险自评估报告》的行文规范，用专业、严谨的中文撰写报告章节内容。"
    "每章节结构清晰、有据可查，避免空话套话，直接针对企业实际情况分析。"
)

_STRICT_CONSTRAINT = (
    "写作约束：仅使用上下文提供的事实与法规条文，不得新增行业、国家/地区、主体、规模或场景。"
    "若上下文缺失，请写“未提供”。如需推测，请明确标注【推测】。"
    "每段末尾需引用至少一条法规依据，格式为“【依据：法规标题+条款】”；若无可引用，写“【依据：未检索到】”。"
)

_CHAPTER_PROMPTS: dict[str, str] = {
    "出境活动概述": (
        "请根据以下企业信息，撰写《数据出境风险自评估报告》第一章「出境活动概述」，"
        "包含：(1)企业基本情况；(2)数据出境业务背景；(3)出境活动的必要性说明。"
    ),
    "数据类型与规模": (
        "请根据以下企业信息，撰写第二章「数据类型与规模」，"
        "包含：(1)出境个人信息的具体类型（普通/敏感）及字段清单；"
        "(2)累计出境规模（人数/条数）；(3)是否触发重要数据认定，并说明依据。"
    ),
    "出境必要性与合法性基础": (
        "请根据以下企业信息，撰写第三章「出境必要性与合法性基础」，"
        "包含：(1)业务必要性论证（为什么必须出境，而非境内处理）；"
        "(2)合法性基础（《个保法》第13条、第38条适用情形）；"
        "(3)是否已获取个人信息主体的单独同意（《个保法》第39条）。"
    ),
    "境外接收方保障能力": (
        "请根据以下企业信息，撰写第四章「境外接收方保障能力评估」，"
        "包含：(1)接收方基本情况（名称、国家/地区、法律地位）；"
        "(2)接收方所在地数据保护法律环境分析；"
        "(3)接收方已建立的个人信息保护制度和技术措施；"
        "(4)接收方处理个人信息的目的、方式、范围是否超出合同约定。"
    ),
    "个人信息权益影响分析": (
        "请根据以下企业信息，撰写第五章「个人信息权益影响分析」，"
        "包含：(1)数据主体知情同意权的保障情况；"
        "(2)数据主体查阅、更正、删除、转移等权利的行使途径；"
        "(3)数据出境对数据主体权益可能造成的影响及风险等级（高/中/低）。"
    ),
    "安全措施与传输机制": (
        "请根据以下企业信息，撰写第六章「安全措施与传输机制」，"
        "包含：(1)传输通道加密技术（TLS/HTTPS/专线等）；"
        "(2)访问控制与身份验证机制；"
        "(3)数据最小化和去标识化措施；"
        "(4)与接收方签订的数据处理协议/标准合同的主要条款；"
        "(5)安全事件应急响应预案。"
    ),
    "剩余风险与整改建议": (
        "请根据以下企业信息，撰写第七章「剩余风险识别与整改建议」，"
        "包含：(1)列举已识别的合规风险点（至少3项）；"
        "(2)每项风险的成因、可能影响及风险等级；"
        "(3)具体整改措施和时间表建议；"
        "(4)法规依据引用。"
    ),
    "综合评估结论": (
        "请根据以下企业信息，撰写第八章「综合评估结论」，"
        "包含：(1)总体合规评级（高风险/中风险/低风险）；"
        "(2)核心结论摘要（不超过150字）；"
        "(3)申报建议（是否建议提交安全评估申报，注意事项）；"
        "(4)有效期说明（通常为2年，如业务或法律环境重大变化须重新评估）。"
    ),
}


def _build_context_block(profile: CompanyProfile, hits: list[RegulationHit], level: str) -> str:
    reg_snippet = "\n".join(
        f"- {h.title} {h.article}：{h.snippet[:120]}" for h in hits[:5]
    ) or "（暂无检索到相关法条）"
    return (
        f"【企业基本信息】\n"
        f"- 企业名称：{profile.company_name}\n"
        f"- 行业：{profile.industry or '未填写'}\n"
        f"- 是否CIIO：{'是' if profile.is_ciio else '否'}\n"
        f"- 是否含重要数据：{'是' if profile.contains_important_data else '否'}\n"
        f"- 普通个人信息出境人数：{profile.pii_count:,}人\n"
        f"- 敏感个人信息出境人数：{profile.spi_count:,}人\n"
        f"- 出境目的：{profile.transfer_purpose}\n"
        f"- 境外接收方国家/地区：{profile.receiver_country}\n"
        f"- 整体风险等级：{level}\n"
        f"\n【相关法规条文】\n{reg_snippet}\n"
    )


class AssessmentChapterGenerator:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client

    def generate(self, profile: CompanyProfile, hits: list[RegulationHit]) -> list[ChapterContent]:
        level = risk_level(
            is_ciio=profile.is_ciio,
            contains_important_data=profile.contains_important_data,
            pii_count=profile.pii_count,
            spi_count=profile.spi_count,
        )
        context_block = _build_context_block(profile, hits, level)
        citation_keys = [f"{h.title}{h.article}" for h in hits[:5]]

        chapters: list[ChapterContent] = []
        for idx, (chapter_title, chapter_instruction) in enumerate(
            _CHAPTER_PROMPTS.items(), start=1
        ):
            content = self._generate_chapter(chapter_title, chapter_instruction, context_block, citation_keys)
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

    def _generate_chapter(
        self,
        title: str,
        instruction: str,
        context: str,
        citations: list[str] | None = None,
    ) -> str:
        if self.llm and self.llm.enabled:
            user_prompt = (
                f"{instruction}\n\n{context}\n\n"
                f"{_STRICT_CONSTRAINT}\n\n"
                "请直接输出章节正文，格式为结构化段落，无需重复章节标题。"
            )
            raw = self.llm.chat(
                system=_SYSTEM_PROMPT,
                user=user_prompt,
                temperature=0.2,
                max_tokens=800,
            )
            return ensure_paragraph_citations(raw, citations)
        # 降级占位
        return f"（{title}：LLM未配置，此处为占位内容）"
