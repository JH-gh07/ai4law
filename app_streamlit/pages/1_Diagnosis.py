import streamlit as st

from app_streamlit.services.client import post_json

st.title("模块1：合规路径诊断")

with st.form("diagnosis_form"):
    company_name = st.text_input("企业名称", value="示例科技")
    q1 = st.selectbox("Q1 是否 CIIO", ["yes", "no", "unknown"], index=1)
    q2 = st.selectbox("Q2 是否涉及重要数据", ["yes", "no", "unknown"], index=1)
    q3 = st.number_input("Q3 累计出境普通个人信息量", min_value=0, value=200000)
    q4 = st.number_input("Q4 累计出境敏感个人信息量", min_value=0, value=500)
    q5 = st.text_input("Q5 出境目的", value="集团统一客户管理")
    submit = st.form_submit_button("生成诊断")

if submit:
    payload = {
        "company_name": company_name,
        "answers": {
            "q1_is_ciio": q1,
            "q2_has_important_data": q2,
            "q3_pii_count": int(q3),
            "q4_spi_count": int(q4),
            "q5_purpose": q5,
        },
    }
    try:
        data = post_json("/diagnosis/report", payload)
        st.success("诊断完成")
        st.json(data["result"])
        st.code(data["report_path"])
    except Exception as exc:  # pragma: no cover
        st.error(str(exc))
