import streamlit as st

from app_streamlit.services.client import post_json

st.title("模块3：SCC / PIPIA 报告")

with st.form("scc_form"):
    company_name = st.text_input("企业名称", value="示例科技")
    receiver_name = st.text_input("境外接收方", value="Example SG Pte. Ltd.")
    receiver_country = st.text_input("接收方国家", value="Singapore")
    purpose = st.text_input("出境目的", value="集团统一客户管理")
    pii_count = st.number_input("普通个人信息量", min_value=0, value=200000)
    spi_count = st.number_input("敏感个人信息量", min_value=0, value=800)
    has_scc_draft = st.checkbox("是否已有 SCC 草案", value=False)
    submit = st.form_submit_button("生成 PIPIA 报告")

if submit:
    payload = {
        "company_name": company_name,
        "receiver_name": receiver_name,
        "receiver_country": receiver_country,
        "transfer_purpose": purpose,
        "pii_count": int(pii_count),
        "spi_count": int(spi_count),
        "has_scc_draft": has_scc_draft,
        "uploaded_files": [],
    }
    try:
        data = post_json("/scc/generate", payload)
        st.success("PIPIA 报告生成完成")
        st.code(data["report_path"])
        st.write(f"一致性问题数：{len(data['consistency_issues'])}")
        st.json(data["profile"])
    except Exception as exc:  # pragma: no cover
        st.error(str(exc))
