from pathlib import Path

import streamlit as st

from app_streamlit.components.report_preview import render_markdown_file
from app_streamlit.services.knowledge import get_report_records, load_sources_index, resolve_citation
from app_streamlit.theme import apply_theme, open_section, render_hero

apply_theme()
render_hero("报告中心", "集中查看各模块输出，支持下载与引用追溯。", kicker="Report Center")

records = get_report_records(output_root="outputs")
if not records:
    st.warning("尚未发现 outputs 目录。")
    st.stop()

module_options = sorted({r["module"] for r in records})
open_section("报告筛选")
selected_modules = st.multiselect("按模块过滤", options=module_options, default=module_options)
selected_ext = st.radio("文件类型", options=["all", ".md", ".docx", ".pdf", ".xlsx", ".zip"], horizontal=True)

filtered = [
    r
    for r in records
    if r["module"] in selected_modules and (selected_ext == "all" or r["ext"] == selected_ext)
]

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("报告总数", len(records))
with col2:
    st.metric("筛选后数量", len(filtered))
with col3:
    st.metric("模块数", len(module_options))

if not filtered:
    st.info("当前筛选条件下无文件。")
    st.stop()

labels = [f"[{item['module']}] {item['filename']}" for item in filtered]
selection = st.selectbox("选择报告", options=range(len(filtered)), format_func=lambda i: labels[i])
selected = filtered[selection]

st.code(selected["path"])

file_path = Path(selected["path"])
with open(file_path, "rb") as fp:
    suffix = file_path.suffix.lower()
    if suffix == ".docx":
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif suffix == ".md":
        mime = "text/markdown"
    elif suffix == ".pdf":
        mime = "application/pdf"
    elif suffix == ".xlsx":
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif suffix == ".zip":
        mime = "application/zip"
    else:
        mime = "application/octet-stream"
    st.download_button(
        label="下载该文件",
        data=fp.read(),
        file_name=file_path.name,
        mime=mime,
    )

if selected["ext"] == ".md":
    with st.expander("Markdown 预览", expanded=True):
        render_markdown_file(selected["path"])
else:
    st.info("当前类型暂不做在线渲染，可直接下载查看。")

st.markdown("### 引用联动查询")
sources = load_sources_index()
citation_query = st.text_input(
    "输入引用文本（例如：个人信息保护法第40条）",
    value="个人信息保护法第40条",
)
if citation_query.strip():
    matched = resolve_citation(citation_query, sources=sources)
    if matched is None:
        st.warning("未匹配到知识库条目。")
    else:
        st.success(f"已匹配：{matched.get('title', '-')}")
        if matched.get("url"):
            st.link_button("打开匹配来源链接", matched["url"])
        st.caption(f"来源机构：{matched.get('source_org', '-')}")
        st.caption(f"本地快照：{matched.get('snapshot_path', '-')}")
