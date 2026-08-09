"""Structured fallback drafting for TIA chapters 1-4.

The fallback consumes existing domain facts and decisions.  It never invents
missing evidence and never decides whether a transfer may proceed.
"""

from __future__ import annotations

from backend.domains.eu.tia.schema import (
    TIACountryRisk,
    TIADecision,
    TIAMeasureAssessment,
    TIARequest,
    TIARouteDecision,
)

_MEASURE_LABELS = {
    "secure_enclave_with_key_separation": "安全飞地与密钥分离",
    "e2e_encryption_eu_key_management": "端到端加密与欧盟密钥管理",
    "encryption_before_transfer_eu_keys": "传输前加密与欧盟密钥管理",
    "encryption_before_transfer": "传输前加密",
    "contractual_only": "仅合同或组织措施",
}


def _marker(markers: dict[str, str], key: str) -> str:
    value = markers.get(key, "")
    return f" {value}" if value else ""


def _list_text(values: list[str]) -> str:
    return "、".join(values) if values else "未提供"


def build_deterministic_tia_chapters(
    *,
    payload: TIARequest,
    route: TIARouteDecision | None,
    country_risk: TIACountryRisk | None,
    data_sensitivity: dict,
    measures: list[TIAMeasureAssessment],
    decision: TIADecision,
    citation_markers: dict[str, str],
) -> dict[int, str]:
    structured = payload.structured_input
    destination = (
        (structured.destination_country or structured.importer_country)
        if structured
        else "未结构化确认"
    )
    exporter_role = structured.exporter_role if structured else "未结构化确认"
    importer_role = structured.importer_role if structured else "未结构化确认"
    categories = _list_text(list(structured.data_categories)) if structured else "未结构化确认"
    subjects = _list_text(structured.data_subjects) if structured else "未结构化确认"

    chapter_1 = (
        "## 传输场景与角色\n\n"
        f"- 数据出口方：{payload.data_exporter_profile}\n"
        f"- 数据进口方：{payload.data_importer_profile}\n"
        f"- 目的地：{destination}\n"
        f"- 出口方 GDPR 角色：{exporter_role}\n"
        f"- 进口方 GDPR 角色：{importer_role}\n"
        f"- 传输目的：{structured.transfer_purpose if structured else '未结构化确认'}\n"
        f"- 数据类别：{categories}\n"
        f"- 数据主体：{subjects}\n\n"
        "以上内容来自用户输入和结构化字段；缺失项保持未确认，不由模型补写。"
        f"{_marker(citation_markers, 'step 1')}"
    )

    route_text = route.route if route else "未启用结构化路径判断"
    route_reason = route.reason if route else "当前为兼容输入路径"
    chapter_2 = (
        "## 传输工具适用性\n\n"
        f"- 用户选择的传输工具：{payload.transfer_tool}\n"
        f"- 系统评估路径：{route_text}\n"
        f"- 路径理由：{route_reason}\n"
        f"- 是否需要完整 TIA：{'是' if not route or route.need_full_tia else '否'}\n\n"
        "在没有充分性决定时，SCC 或其他 Article 46 工具必须在具体传输中实际有效，"
        "且应有可核验的适用文件；仅填写工具名称不等于已经建立适当保障。"
        f"{_marker(citation_markers, '44')}{_marker(citation_markers, '46')}"
    )

    if country_risk:
        country_lines = (
            f"- 评估国家：{country_risk.country}\n"
            f"- 国家风险：{country_risk.risk_level}\n"
            f"- 政府访问风险：{'是' if country_risk.gov_access_risk else '否'}\n"
            f"- 有效救济：{'有' if country_risk.effective_remedy else '未确认'}\n"
            f"- 独立监督：{'有' if country_risk.independent_oversight else '未确认'}\n"
            f"- 风险来源：{_list_text(country_risk.risk_sources)}\n"
            f"- 规则说明：{country_risk.notes or '无'}"
        )
    else:
        country_lines = "- 未启用结构化国家风险规则；以下用户材料仍需人工核验"
    chapter_3 = (
        "## 第三国法律与实践\n\n"
        f"{country_lines}\n\n"
        f"用户提交的第三国评估：{payload.third_country_assessment}\n\n"
        "系统只记录可追踪事实和规则结果；是否达到实质等同保护水平仍取决于"
        "适用于本次传输的法律、实践和证据。"
        f"{_marker(citation_markers, 'step 3')}"
    )

    measure_lines = "\n".join(
        f"- {'充足' if item.sufficient_for_risk else '不足'}："
        f"{_MEASURE_LABELS.get(item.measure_name, item.measure_name)}；{item.assessment}"
        for item in measures
    ) or "- 尚无可计算的结构化措施"
    chapter_4 = (
        "## 补充措施可执行性\n\n"
        f"用户声称的补充措施：{payload.supplementary_measures}\n\n"
        f"结构化规则评估：\n{measure_lines}\n\n"
        f"- 数据敏感等级：{data_sensitivity.get('sensitivity', 'unknown')}\n"
        f"- 措施充分性：{decision.measure_sufficiency}\n"
        f"- 附件证据状态：{decision.evidence_status}\n\n"
        "结构化勾选只代表用户声明；只有与技术控制文件相互印证后，措施才能作为"
        "允许传输的证据。"
        f"{_marker(citation_markers, 'step 3')}"
    )

    return {1: chapter_1, 2: chapter_2, 3: chapter_3, 4: chapter_4}
