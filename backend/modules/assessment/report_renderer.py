from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from backend.common.render.report import (
    format_date_stamp,
    render_docx_template,
    render_markdown_template,
    safe_filename,
)
from backend.common.render.summary import attach_citations, dedup_if_same, summarize_for_slot
from backend.modules.assessment.schema import ChapterContent, CompanyProfile, RegulationHit

TEMPLATE_PATH = Path("doc/v2/assets/templates/2.2_risk_assessment_template_v0.docx")
TEMPLATE_MD = Path("doc/v2/assets/templates/2.2_risk_assessment_template_v0.md")


class AssessmentReportRenderer:
    def render(
        self,
        company_name: str,
        profile: CompanyProfile,
        regulations: list[RegulationHit],
        chapters: list[ChapterContent],
        path_warning: str | None = None,
        alignment_warning: str | None = None,
    ) -> dict[str, str]:
        output_dir = Path("outputs/assessment")
        date_stamp = format_date_stamp()
        safe_company = safe_filename(company_name)
        md_output = output_dir / f"{safe_company}_数据出境风险自评估报告_草案_{date_stamp}.md"
        docx_output = output_dir / f"{safe_company}_数据出境风险自评估报告_草案_{date_stamp}.docx"
        zip_output = output_dir / f"{safe_company}_安全评估路径输出包_草案_{date_stamp}.zip"
        mapping = _build_template_mapping(profile, regulations, chapters, date_stamp, path_warning, alignment_warning)
        render_markdown_template(md_output, TEMPLATE_MD, mapping)
        render_docx_template(docx_output, TEMPLATE_PATH, mapping)
        with ZipFile(zip_output, mode="w", compression=ZIP_DEFLATED) as bundle:
            bundle.write(docx_output, arcname=docx_output.name)
            bundle.write(md_output, arcname=md_output.name)
        return {"markdown": str(md_output), "docx": str(docx_output), "zip": str(zip_output)}


def _build_template_mapping(
    profile: CompanyProfile,
    regulations: list[RegulationHit],
    chapters: list[ChapterContent],
    date_stamp: str,
    path_warning: str | None = None,
    alignment_warning: str | None = None,
) -> dict[str, str]:
    def pick(title: str) -> str:
        for chapter in chapters:
            if chapter.title == title:
                return chapter.content
        return ""

    pii = f"{profile.pii_count:,}人"
    spi = f"{profile.spi_count:,}人"
    contains_spi = "是" if profile.spi_count > 0 else "否"

    legal_basis = summarize_for_slot(pick("出境必要性与合法性基础"), max_sentences=2, max_chars=260)
    security_measures = summarize_for_slot(pick("安全措施与传输机制"), max_sentences=2, max_chars=260)
    risk_summary = summarize_for_slot(pick("剩余风险与整改建议"), max_sentences=2, max_chars=260)
    conclusion = summarize_for_slot(pick("综合评估结论"), max_sentences=2, max_chars=260)
    if path_warning:
        conclusion = f"【路径不匹配警示】{path_warning}\n{conclusion}".strip()
    if alignment_warning:
        conclusion = f"【输入对齐告警】{alignment_warning}\n{conclusion}".strip()
    citations = [f"{item.title}{item.article}" for item in regulations[:3]]
    regulations_text = "; ".join(citations) or "未提供"

    governance_candidate = summarize_for_slot(pick("剩余风险与整改建议"), max_sentences=1, max_chars=200)
    technical_candidate = summarize_for_slot(pick("安全措施与传输机制"), max_sentences=1, max_chars=200)
    governance_measures, technical_measures = dedup_if_same(
        governance_candidate,
        technical_candidate,
        "管理措施待补充（当前仅提供技术措施摘要）。",
    )

    business_flow_summary = summarize_for_slot(pick("出境活动概述"), max_sentences=2, max_chars=260) or "基于企业业务需要进行跨境传输。"
    legal_risk = legal_basis or risk_summary
    security_risk = security_measures or "需结合技术与管理措施持续评估。"
    process_risk = risk_summary or "流程风险可控，但需完善内控。"
    governance_measures = attach_citations(governance_measures, citations)
    technical_measures = attach_citations(technical_measures, citations)
    business_flow_summary = attach_citations(business_flow_summary, citations)
    legal_risk = attach_citations(legal_risk, citations)
    security_risk = attach_citations(security_risk, citations)
    process_risk = attach_citations(process_risk, citations)
    conclusion = attach_citations(conclusion or "综合评估结论需结合监管要求进一步确认。", citations)

    return {
        "company_name": profile.company_name,
        "company_uscc": "未提供",
        "report_date": date_stamp,
        "contact_name": "未提供",
        "transfer_purpose": profile.transfer_purpose,
        "recipient_name": profile.receiver_country or "未提供",
        "recipient_country_region": profile.receiver_country or "未提供",
        "business_flow_summary": business_flow_summary,
        "data_categories": f"个人信息（普通/敏感），参考法规：{regulations_text}",
        "data_volume": f"普通个人信息{pii}，敏感个人信息{spi}",
        "contains_spi": contains_spi,
        "transfer_frequency": "未提供",
        "legal_risk": legal_risk,
        "security_risk": security_risk,
        "process_risk": process_risk,
        "governance_measures": governance_measures,
        "technical_measures": technical_measures,
        "contractual_measures": "拟通过合同与附加条款约束接收方处理范围与责任。",
        "overall_conclusion": conclusion,
        "remediation_items": attach_citations("详见风险识别与整改建议章节。", citations),
        "attachments": "- 无",
    }
