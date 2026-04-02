from pathlib import Path
from typing import Iterable

import streamlit as st

from app_streamlit.components.risk_badge import render_risk_badge
from app_streamlit.services.knowledge import resolve_citation


def _mime_by_suffix(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if suffix == ".md":
        return "text/markdown"
    if suffix == ".pdf":
        return "application/pdf"
    if suffix == ".xlsx":
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if suffix == ".zip":
        return "application/zip"
    if suffix == ".json":
        return "application/json"
    if suffix == ".csv":
        return "text/csv"
    return "application/octet-stream"


def render_chapter_preview(
    chapters: Iterable[dict],
    sources: list[dict[str, str]] | None = None,
) -> None:
    st.subheader("报告预览")
    for chapter in chapters:
        title = f"第{chapter.get('chapter_no', '?')}章：{chapter.get('title', '未命名章节')}"
        with st.expander(title, expanded=False):
            risk_level = str(chapter.get("risk_level", "LOW"))
            render_risk_badge(risk_level)
            st.write(chapter.get("content", ""))
            citations = chapter.get("citations", [])
            if citations:
                st.caption("引用来源")
                for idx, citation in enumerate(citations, start=1):
                    with st.expander(f"[{idx}] {citation}", expanded=False):
                        matched = resolve_citation(str(citation), sources=sources)
                        if matched is None:
                            st.write("未匹配到知识库条目，可在知识库中心手动检索。")
                            continue
                        st.write(f"标题：{matched.get('title', '-')}")
                        st.write(f"来源机构：{matched.get('source_org', '-')}")
                        st.write(f"发布日期：{matched.get('publish_date', '-')}")
                        url = matched.get("url", "")
                        if url:
                            st.link_button("打开来源链接", url)
                        snapshot = matched.get("snapshot_path", "")
                        if snapshot:
                            st.caption(f"本地快照：{snapshot}")


def render_report_download(output_files: dict[str, str]) -> None:
    st.subheader("报告下载")
    for label, path in output_files.items():
        file_path = Path(path)
        if not file_path.exists():
            st.warning(f"{label} 文件不存在：{path}")
            continue
        mime = _mime_by_suffix(file_path)
        with open(file_path, "rb") as fp:
            st.download_button(
                label=f"下载 {label} ({file_path.name})",
                data=fp.read(),
                file_name=file_path.name,
                mime=mime,
                key=f"download_{label}_{file_path.name}",
            )


def render_markdown_file(path: str) -> None:
    file_path = Path(path)
    if not file_path.exists():
        st.error(f"文件不存在：{path}")
        return
    st.markdown(file_path.read_text(encoding="utf-8", errors="ignore"))
