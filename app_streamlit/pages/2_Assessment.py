import streamlit as st

from app_streamlit.services.client import post_json

st.title("模块2：安全评估报告")

with st.form("assessment_form"):
    company_name = st.text_input("企业名称", value="示例科技")
    industry = st.text_input("行业", value="电商")
    is_ciio = st.checkbox("是否 CIIO", value=False)
    important_data = st.checkbox("是否涉及重要数据", value=False)
    pii_count = st.number_input("普通个人信息量", min_value=0, value=300000)
    spi_count = st.number_input("敏感个人信息量", min_value=0, value=500)
    purpose = st.text_input("出境目的", value="跨境客服")
    country = st.text_input("接收方国家", value="Singapore")
    submit = st.form_submit_button("生成自评估报告")

if submit:
    payload = {
        "company_name": company_name,
        "industry": industry,
        "is_ciio": is_ciio,
        "contains_important_data": important_data,
        "pii_count": int(pii_count),
        "spi_count": int(spi_count),
        "transfer_purpose": purpose,
        "receiver_country": country,
        "uploaded_files": [],
    }
    try:
        data = post_json("/assessment/generate", payload)
        st.success("报告生成完成")
        st.code(data["report_path"])
        st.write(f"一致性问题数：{len(data['consistency_issues'])}")
        st.json(data["profile"])
    except Exception as exc:  # pragma: no cover
        st.error(str(exc))
