from pathlib import Path

import streamlit as st

from app_streamlit.components.legal_basis import build_legal_basis_models, render_legal_basis_summary
from app_streamlit.components.report_preview import render_markdown_file
from app_streamlit.components.risk_badge import render_risk_badge
from app_streamlit.components.schema_form import load_schema
from app_streamlit.services.client import post_json
from app_streamlit.services.knowledge import load_sources_index
from app_streamlit.theme import apply_theme, open_section, render_hero

SCHEMA_PATH = Path("app_streamlit/schemas/diagnosis_schema.json")
QUESTION_STATE_KEY = "diagnosis_question_index"

_OUTCOME_LABELS = {
    "SECURITY_ASSESSMENT": "安全评估路径",
    "SCC_OR_CERTIFICATION": "标准合同 / 个人信息保护认证路径",
    "EXEMPTION": "豁免路径（无需向监管机构申报）",
    # 兼容旧字段名
    "security_assessment": "安全评估路径",
    "scc_or_certification": "标准合同 / 个人信息保护认证路径",
    "exemption": "豁免路径（无需向监管机构申报）",
}

_OUTCOME_COLORS = {
    "SECURITY_ASSESSMENT": "🔴",
    "SCC_OR_CERTIFICATION": "🟡",
    "EXEMPTION": "🟢",
    "security_assessment": "🔴",
    "scc_or_certification": "🟡",
    "exemption": "🟢",
}


apply_theme("cn")
render_hero("2.1 合规路径诊断", "智能问答判断数据出境合规路径，AI生成专业法律说明。", kicker="CN 2.1")

schema = load_schema(str(SCHEMA_PATH))
sources = load_sources_index()
questions = schema.get("questions", [])
if not questions:
    st.error("诊断问题配置缺失")
    st.stop()

if QUESTION_STATE_KEY not in st.session_state:
    st.session_state[QUESTION_STATE_KEY] = 0

for q in questions:
    value_key = f"diagnosis__{q['name']}"
    if value_key not in st.session_state:
        st.session_state[value_key] = q.get("default")

current_idx = int(st.session_state[QUESTION_STATE_KEY])
open_section("诊断问答")
st.progress((current_idx + 1) / len(questions))
st.caption(f"第 {current_idx + 1} / {len(questions)} 题")

question = questions[current_idx]
q_key = f"diagnosis__{question['name']}"
option_labels = question.get("option_labels", {})

if question["type"] == "select":
    options = question.get("options", [])
    display_options = [option_labels.get(o, o) for o in options]
    default = st.session_state.get(q_key)
    raw_index = options.index(default) if default in options else 0
    selected_display = st.selectbox(
        question["label"],
        options=display_options,
        index=raw_index,
        help=question.get("help"),
        key=f"{q_key}_display",
    )
    # 存回原始值（不是展示文本）
    selected_raw = options[display_options.index(selected_display)]
    st.session_state[q_key] = selected_raw
elif question["type"] == "number":
    st.number_input(
        question["label"],
        min_value=question.get("min", 0),
        step=question.get("step", 1),
        key=q_key,
        help=question.get("help"),
    )
elif question["type"] == "text":
    st.text_input(question["label"], key=q_key, help=question.get("help"))
else:
    st.error(f"不支持的问题类型：{question['type']}")

col1, col2, _ = st.columns([1, 1, 2])
with col1:
    if st.button("上一步", disabled=current_idx == 0):
        st.session_state[QUESTION_STATE_KEY] = max(0, current_idx - 1)
        st.rerun()
with col2:
    if current_idx < len(questions) - 1:
        if st.button("下一步"):
            st.session_state[QUESTION_STATE_KEY] = min(len(questions) - 1, current_idx + 1)
            st.rerun()

if current_idx == len(questions) - 1:
    company_name = st.text_input("企业名称", value="示例科技有限公司", key="diagnosis__company_name")
    if st.button("生成诊断报告", type="primary"):
        payload = {
            "company_name": company_name,
            "answers": {
                "q1_is_ciio": st.session_state.get("diagnosis__q1_is_ciio", "no"),
                "q2_has_important_data": st.session_state.get("diagnosis__q2_has_important_data", "no"),
                "q3_pii_count": int(st.session_state.get("diagnosis__q3_pii_count", 0) or 0),
                "q4_spi_count": int(st.session_state.get("diagnosis__q4_spi_count", 0) or 0),
                "q5_no_personal_info": st.session_state.get("diagnosis__q5_no_personal_info", "no"),
                "q6_scenario": st.session_state.get("diagnosis__q6_scenario", "other"),
                "q7_receiver_type": st.session_state.get("diagnosis__q7_receiver_type", "third_party"),
                "q8_purpose": st.session_state.get("diagnosis__q8_purpose", ""),
            },
        }
        try:
            data = post_json("/diagnosis/report", payload)
            st.success("诊断完成")

            result = data.get("result", {})
            outcome = result.get("recommended_path") or result.get("outcome", "")
            outcome_label = _OUTCOME_LABELS.get(outcome, outcome)
            outcome_icon = _OUTCOME_COLORS.get(outcome, "⚪")

            st.markdown("### 诊断结论")
            st.markdown(f"## {outcome_icon} {outcome_label}")

            risk = result.get("risk_level")
            if risk:
                render_risk_badge(risk)

            rationale = result.get("rationale") or result.get("summary", "")
            if rationale:
                st.info(rationale)

            legal_basis = result.get("legal_basis", [])
            if legal_basis:
                basis_models = build_legal_basis_models(legal_basis, sources=sources)
                render_legal_basis_summary(
                    basis_models,
                    title="适用法规依据",
                    key_prefix="diagnosis_basis",
                )
                with st.expander("查看法规详情", expanded=False):
                    for idx, item in enumerate(basis_models, start=1):
                        st.markdown(f"**[{idx}]** {item.get('citation', '-')}")
                        st.write(f"来源机构：{item.get('source_org', '-')}")
                        if item.get("url"):
                            st.link_button(f"查看原文", item["url"])
                        st.divider()

            actions = result.get("action_items") or result.get("next_actions", [])
            if actions:
                st.markdown("### 后续行动清单")
                for action in actions:
                    st.write(f"- {action}")

            report_path = data.get("report_path", "")
            if report_path:
                st.code(report_path)
                if report_path.endswith(".md"):
                    with st.expander("预览诊断报告", expanded=False):
                        render_markdown_file(report_path)
        except Exception as exc:  # pragma: no cover
            st.error(str(exc))
