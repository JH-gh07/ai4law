"""Deterministic DPIA chapter fallback built only from validated pipeline data."""

from __future__ import annotations

from typing import Any

from backend.common.llm.postprocess import apply_citation_pipeline


def _display(value: Any) -> str:
    if value is None or value == "" or value == []:
        return "未提供"
    if isinstance(value, list):
        readable: list[str] = []
        for item in value:
            if isinstance(item, dict):
                text = next(
                    (
                        str(item.get(key) or "").strip()
                        for key in ("reason", "title", "description", "name", "type")
                        if str(item.get(key) or "").strip()
                    ),
                    "",
                )
                if text:
                    readable.append(text)
            elif str(item).strip():
                readable.append(str(item).strip())
        return "、".join(readable) or "未提供"
    if isinstance(value, bool):
        return "是" if value else "否"
    labels = {
        "approval": "可推进",
        "conditional_approval": "附条件推进",
        "objection": "不建议推进",
        "planned": "计划中",
        "implemented": "已实施",
        "missing": "待补充",
    }
    if isinstance(value, str) and value in labels:
        return labels[value]
    return str(value)


def _fact_map(section: dict[str, Any]) -> dict[str, Any]:
    return {
        str(item.get("field_path") or ""): item.get("value")
        for item in section.get("confirmed_facts", [])
        if isinstance(item, dict) and item.get("field_path")
    }


def _citation_marker(registry: Any, article: str, used: list[str]) -> str:
    if registry is None:
        return ""
    for item in registry:
        if str(item.article_no) == article:
            used.append(item.citation_id)
            return f" {{{{{item.citation_id}}}}}"
    return ""


def _risk_lines(risks: list[dict[str, Any]]) -> str:
    if not risks:
        return "- 未提供可核验的风险矩阵，需补充并复核。"
    lines: list[str] = []
    for risk in risks[:8]:
        name = risk.get("risk_name") or risk.get("risk_description") or risk.get("risk_id")
        level = risk.get("overall_level") or risk.get("risk_level") or "未评估"
        lines.append(
            f"- {risk.get('risk_id', '')}：{name}；可能性={risk.get('likelihood', '未评估')}，"
            f"影响={risk.get('impact', '未评估')}，等级={level}。"
        )
    return "\n".join(lines)


def _mitigation_lines(plan: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for entry in plan[:8]:
        for measure in entry.get("measures", [])[:3]:
            if not isinstance(measure, dict):
                continue
            lines.append(
                f"- {entry.get('risk_id', '')}：{measure.get('measure', '未提供')}；"
                f"状态={measure.get('status', '未提供')}；验证方式={measure.get('verification', '需补充')}。"
            )
    return "\n".join(lines) or "- 未提供可核验的缓解措施，不得视为风险已降低。"


def build_deterministic_chapter(
    *,
    chapter_id: str,
    title: str,
    section: dict[str, Any],
    generation_basis_pack: dict[str, Any],
    citation_registry: Any = None,
) -> dict[str, Any]:
    """Return conservative, non-placeholder prose when a chapter LLM call fails."""
    facts = _fact_map(section)
    basis = generation_basis_pack
    used: list[str] = []

    def cite(article: str) -> str:
        return _citation_marker(citation_registry, article, used)

    need = basis.get("need_assessment", {}) or {}
    processing = basis.get("processing_activity_pack", {}) or {}
    necessity = basis.get("necessity_findings", {}) or {}
    risks = basis.get("risk_matrix", []) or []
    mitigations = basis.get("mitigation_plan", []) or []
    dpo = basis.get("dpo_decision_pack", {}) or {}

    if chapter_id == "need_identification":
        content = (
            f"根据当前结构化输入，本项目的 DPIA 需求判定为"
            f"{'需要' if need.get('dpia_required') else '尚未确认需要'}。"
            f"触发因素包括：{_display(need.get('trigger_reasons'))}。{cite('35')}\n\n"
            f"当前判断依据为：{_display(need.get('reasoning'))}。"
            "该结论仅以已提供事实为基础，输入未附证据的内容仍需人工确认。\n\n"
            f"事先咨询可能性：{_display(need.get('prior_consultation_possible'))}。"
            f"如缓解后仍存在高剩余风险，应在开始处理前评估并履行监管机构事先咨询义务。{cite('36')}"
        )
    elif chapter_id == "processing_description":
        ambiguities = processing.get("ambiguities", [])
        content = (
            f"处理活动概述：{_display(processing.get('draft_text'))}\n\n"
            f"数据类别：{_display(processing.get('data_categories'))}；"
            f"数据主体：{_display(processing.get('data_subjects'))}；"
            f"保留期：{_display(processing.get('retention_periods'))}。"
            f"这些处理范围和保留期必须与声明目的相符，并满足数据最小化要求。{cite('5')}\n\n"
            f"当前待确认项：{_display(ambiguities)}。"
            "在这些信息补齐前，本章不对数据共享、安全措施或权利响应机制作出已落实结论。"
        )
    elif chapter_id == "consultation":
        source_opinion = facts.get("dpia.dpo_opinion") or dpo.get("source_opinion")
        content = (
            f"已记录的内部咨询对象：{_display(facts.get('dpia.consulted_internal_departments'))}。"
            f"外部专家：{_display(facts.get('dpia.external_experts'))}。\n\n"
            f"数据主体咨询计划：{_display(facts.get('dpia.data_subject_consultation_plan'))}。"
            "咨询记录应保留参与人、日期、关键意见、采纳结果和未采纳理由。\n\n"
            f"DPO 姓名：{_display(facts.get('dpia.dpo_name'))}。用户填写的 DPO 意见为："
            f"“{_display(source_opinion)}”。该内容属于用户输入，不等同于正式签署或批准；"
            "仍需补充可核验的 DPO 审阅记录。"
        )
    elif chapter_id == "necessity_proportionality":
        content = (
            f"用户申报的法律基础为：{_display(facts.get('dpia.lawful_basis'))}。"
            f"该基础仍需结合处理目的、权力不对等和撤回机制进行逐项论证。{cite('6')}{cite('7')}\n\n"
            f"用户提供的必要性说明：{_display(facts.get('dpia.necessity_statement'))}。"
            f"结构化评估结果：{_display(necessity.get('draft_text'))}。"
            f"侵入性更低的替代方案包括：{_display(necessity.get('less_intrusive_alternatives'))}。{cite('5')}\n\n"
            f"用户提供的相称性说明：{_display(facts.get('dpia.proportionality_statement'))}。"
            f"透明度安排：{_display(facts.get('dpia.transparency_information'))}。"
            f"告知内容仍应覆盖处理目的、法律基础、保留期、接收方、权利和自动化决策逻辑。{cite('13')}{cite('14')}"
        )
    elif chapter_id == "risk_assessment":
        content = (
            "基于已验证输入和当前风险矩阵，识别结果如下：\n"
            f"{_risk_lines(risks)}\n\n"
            "风险等级反映当前证据状态，不应把计划中的措施当成已实施措施扣减风险。"
            f"对可能产生法律或类似重大影响的自动化决策，需单独验证人工干预、表达观点和质疑决策的权利。{cite('22')}\n\n"
            f"如缓解后仍为高风险，应进入事先咨询判断，而不得以草案生成完成代替风险处置。{cite('35')}{cite('36')}"
        )
    elif chapter_id == "mitigation":
        content = (
            "当前缓解措施与风险的关联如下：\n"
            f"{_mitigation_lines(mitigations)}\n\n"
            "每项措施必须保留负责人、完成日期、验收方法和实施证据。"
            "状态为 planned 或 missing 的措施不得在报告中表述为已落实。\n\n"
            f"对自动化决策和 DPIA 持续复评的措施，应分别验证权利救济、技术与组织控制以及风险变化触发机制。{cite('22')}{cite('35')}"
        )
    else:
        source_opinion = facts.get("dpia.dpo_opinion") or dpo.get("source_opinion")
        content = (
            f"DPIA 负责人：{_display(facts.get('dpia.dpia_owner'))}；DPO："
            f"{_display(facts.get('dpia.dpo_name'))}；复审日期：{_display(facts.get('dpia.review_date'))}。\n\n"
            f"用户填写的 DPO 意见为：“{_display(source_opinion)}”。该输入不等同于正式 DPO 签署或批准。\n\n"
            f"结构化风险评估结论：{_display(dpo.get('dpo_position'))}。前置条件："
            f"{_display(dpo.get('conditions'))}。该结论由系统依据风险矩阵和措施状态生成，"
            f"不得冒充 DPO 本人意见；条件完成后仍需取得正式审阅记录。{cite('35')}\n\n"
            f"是否建议事先咨询：{_display(dpo.get('prior_consultation_recommended'))}。"
            f"理由：{_display(dpo.get('reason'))}。如剩余高风险无法降低，应在开始处理前完成事先咨询。{cite('36')}"
        )

    rendered = apply_citation_pipeline(
        content,
        registry=citation_registry,
        allowed_citations=[item.display_label for item in citation_registry]
        if citation_registry is not None
        else [],
    ).text
    return {
        "title": title,
        "content": rendered,
        "citations": list(dict.fromkeys(used)),
        "risk_level": "high" if chapter_id in {"risk_assessment", "mitigation", "signoff"} else "medium",
    }


def enforce_article36_conclusion(
    chapter: dict[str, Any],
    *,
    dpo_decision_pack: dict[str, Any],
    citation_registry: Any = None,
) -> dict[str, Any]:
    """Make a positive Article 36 decision deterministic when the DPO requires it."""
    if not dpo_decision_pack.get("prior_consultation_recommended"):
        return chapter
    content = str(chapter.get("content") or "")
    if "必须在开始处理前" in content and "事先咨询" in content:
        return chapter

    used = list(chapter.get("citations") or [])
    marker = _citation_marker(citation_registry, "36", used)
    reason = _display(dpo_decision_pack.get("reason"))
    content += (
        "\n\n事先咨询结论：根据结构化风险矩阵与缓解后剩余风险判断，"
        f"控制者必须在开始处理前履行 GDPR 第36条事先咨询程序。"
        f"理由：{reason}。在咨询和 DPO 前置条件完成前，不建议上线。{marker}"
    )
    rendered = apply_citation_pipeline(
        content,
        registry=citation_registry,
        allowed_citations=[item.display_label for item in citation_registry]
        if citation_registry is not None
        else [],
    ).text
    return {
        **chapter,
        "content": rendered,
        "citations": list(dict.fromkeys(used)),
        "risk_level": "high",
    }
