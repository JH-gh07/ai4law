import streamlit as st

from app_streamlit.components.file_uploader import render_file_uploader
from app_streamlit.components.report_preview import render_markdown_file, render_report_download
from app_streamlit.components.risk_badge import render_risk_badge
from app_streamlit.components.schema_form import render_schema_multistep_form
from app_streamlit.services.local_generators import generate_general_report
from app_streamlit.theme import apply_theme, open_section, render_hero

SCHEMA_PATH = "app_streamlit/schemas/general_schema.json"

apply_theme("cn")
render_hero("2.4 通用服务", "快速生成 TIA、尽调、备忘录与整改清单。", kicker="CN 2.4")

open_section("服务配置")
submitted, values = render_schema_multistep_form("general", SCHEMA_PATH)
_ = render_file_uploader(module="general", label="可选：上传补充材料")

if submitted:
    payload = {
        "doc_type": str(values["doc_type"]),
        "company_name": str(values["company_name"]),
        "transfer_purpose": str(values["transfer_purpose"]),
        "receiver_country": str(values["receiver_country"]),
    }
    result = generate_general_report(payload)

    st.success("通用服务报告已生成")
    render_risk_badge(result.summary.get("risk_level", "MEDIUM"))
    st.write(f"报告路径：{result.report_path}")
    render_report_download(result.output_files)

    md_path = result.output_files.get("markdown")
    if md_path:
        with st.expander("预览 Markdown 报告", expanded=False):
            render_markdown_file(md_path)
