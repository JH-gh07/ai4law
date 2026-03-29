from pathlib import Path

import streamlit as st

from app_streamlit.components.report_preview import render_markdown_file
from app_streamlit.components.risk_badge import render_risk_badge
from app_streamlit.components.schema_form import load_schema
from app_streamlit.services.client import post_json
from app_streamlit.services.knowledge import load_sources_index, resolve_citation
from app_streamlit.theme import apply_theme, open_section, render_hero

SCHEMA_PATH = Path("app_streamlit/schemas/diagnosis_schema.json")
QUESTION_STATE_KEY = "diagnosis_question_index"

apply_theme()
render_hero("模块1：合规路径诊断", "前端动态问答，生成可追溯诊断结论。", kicker="Diagnosis")

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

if question["type"] == "select":
    options = question.get("options", [])
    default = st.session_state.get(q_key)
    index = options.index(default) if default in options else 0
    st.selectbox(question["label"], options=options, index=index, key=q_key, help=question.get("help"))
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
    company_name = st.text_input("企业名称", value="示例科技", key="diagnosis__company_name")
    if st.button("生成诊断报告", type="primary"):
        payload = {
            "company_name": company_name,
            "answers": {
                "q1_is_ciio": st.session_state["diagnosis__q1_is_ciio"],
                "q2_has_important_data": st.session_state["diagnosis__q2_has_important_data"],
                "q3_pii_count": int(st.session_state["diagnosis__q3_pii_count"]),
                "q4_spi_count": int(st.session_state["diagnosis__q4_spi_count"]),
                "q5_purpose": st.session_state["diagnosis__q5_purpose"],
            },
        }
        try:
            data = post_json("/diagnosis/report", payload)
            st.success("诊断完成")

            result = data["result"]
            st.markdown("### 诊断结论")
            st.write(f"推荐路径：`{result['recommended_path']}`")
            render_risk_badge(result["risk_level"])
            st.write(result["rationale"])

            st.markdown("### 法律依据")
            for idx, item in enumerate(result["legal_basis"], start=1):
                with st.expander(f"[{idx}] {item}"):
                    matched = resolve_citation(str(item), sources=sources)
                    if matched is None:
                        st.write("未匹配到知识库条目，可在知识库中心手动检索。")
                    else:
                        st.write(f"匹配条目：{matched.get('title', '-')}")
                        if matched.get("url"):
                            st.link_button("打开来源链接", matched["url"])

            st.markdown("### 后续行动")
            for action in result["action_items"]:
                st.write(f"- {action}")

            report_path = data["report_path"]
            st.code(report_path)
            if report_path.endswith(".md"):
                with st.expander("预览诊断报告", expanded=False):
                    render_markdown_file(report_path)
        except Exception as exc:  # pragma: no cover
            st.error(str(exc))
