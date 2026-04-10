import sys
from pathlib import Path

for _parent in Path(__file__).resolve().parents:
    if (_parent / "app_streamlit").exists():
        _root = str(_parent)
        if _root not in sys.path:
            sys.path.insert(0, _root)
        break

import streamlit as st

from app_streamlit.components.file_uploader import render_file_uploader
from app_streamlit.components.report_preview import render_markdown_file, render_report_download
from app_streamlit.components.risk_badge import render_risk_badge
from app_streamlit.components.schema_form import render_schema_multistep_form
from app_streamlit.services.local_generators import generate_review_report
from app_streamlit.theme import apply_theme, open_section, render_hero

SCHEMA_PATH = "app_streamlit/schemas/review_schema.json"

apply_theme("cn")
render_hero("2.5 文档专项智能审查", "上传合同或制度文本，输出条款级问题与修订建议。", kicker="CN 2.5")

open_section("审查输入")
submitted, values = render_schema_multistep_form("review", SCHEMA_PATH)
uploaded_paths = render_file_uploader(module="review", label="上传待审文件")

if submitted:
    company_name = str(values["company_name"])
    notes = str(values["review_notes"])

    result = generate_review_report(company_name=company_name, uploaded_paths=uploaded_paths, notes=notes)

    st.success("文档审查报告已生成")
    render_risk_badge(result.summary.get("risk_level", "MEDIUM"))
    st.write(f"问题数：{result.summary.get('issue_count', 0)}")

    issues = result.summary.get("issues", [])
    if issues:
        with st.expander("问题清单"):
            for issue in issues:
                st.write(f"- {issue}")

    render_report_download(result.output_files)

    md_path = result.output_files.get("markdown")
    if md_path:
        with st.expander("预览 Markdown 报告", expanded=False):
            render_markdown_file(md_path)
