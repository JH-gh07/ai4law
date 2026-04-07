import time
from pathlib import Path

import streamlit as st

from app_streamlit.components.file_uploader import render_file_uploader
from app_streamlit.components.report_preview import render_chapter_preview, render_report_download
from app_streamlit.components.schema_form import render_schema_multistep_form
from app_streamlit.services.client import get_json, post_json
from app_streamlit.services.knowledge import load_sources_index
from app_streamlit.theme import apply_theme, open_section, render_hero

SCHEMA_PATH = "app_streamlit/schemas/tia_schema.json"
_ALLOWED_ATTACHMENT_FORMATS = {"docx", "pdf"}


def _build_attachments(uploaded_paths: list[str], file_role: str) -> list[dict]:
    attachments: list[dict] = []
    for path in uploaded_paths:
        p = Path(path)
        file_format = p.suffix.lower().lstrip(".")
        if file_format not in _ALLOWED_ATTACHMENT_FORMATS:
            continue
        attachments.append(
            {
                "file_role": file_role,
                "file_name": p.name,
                "file_format": file_format,
                "storage_uri": str(p),
                "size_bytes": p.stat().st_size if p.exists() else None,
            }
        )
    return attachments


apply_theme("eu")
render_hero("3.4 TIA草案生成", "面向跨境传输场景输出 TIA 草案。", kicker="EU 3.4")
sources = load_sources_index()

open_section("信息采集")
submitted, values = render_schema_multistep_form("tia", SCHEMA_PATH)
uploaded_files = render_file_uploader(module="tia", label="上传 TIA 附件（至少1个，docx/pdf）")
use_async = st.checkbox("异步生成（推荐）", value=True, key="tia__use_async")

if submitted:
    attachments = _build_attachments(uploaded_files, file_role=str(values["attachment_role"]))
    if not attachments:
        st.error("TIA 至少需要 1 个可用附件（docx/pdf）。")
    else:
        payload = {
            "transfer_tool": str(values["transfer_tool"]),
            "data_exporter_profile": str(values["data_exporter_profile"]),
            "data_importer_profile": str(values["data_importer_profile"]),
            "third_country_assessment": str(values["third_country_assessment"]),
            "supplementary_measures": str(values["supplementary_measures"]),
            "final_conclusion": str(values["final_conclusion"]),
            "attachments": attachments,
        }

        try:
            if use_async:
                accepted = post_json("/tia/generate_async", payload)
                task_id = accepted["task_id"]
                with st.spinner(f"任务 {task_id} 执行中..."):
                    data = None
                    for _ in range(180):
                        status = get_json(f"/tia/tasks/{task_id}")
                        if status["state"] == "COMPLETED":
                            data = status["result"]
                            break
                        if status["state"] == "FAILED":
                            raise RuntimeError(status.get("error") or "task failed")
                        time.sleep(0.5)
                    if data is None:
                        raise TimeoutError("tia async timeout")
            else:
                data = post_json("/tia/generate", payload)

            st.success("TIA 草案生成完成")
            st.write(f"传输工具：`{data['transfer_tool']}`")
            st.write(f"风险等级：`{data['risk_level']}`")
            st.write(f"一致性问题数：{len(data['consistency_issues'])}")

            if data["consistency_issues"]:
                with st.expander("一致性问题详情"):
                    for issue in data["consistency_issues"]:
                        st.write(f"- {issue}")

            if data.get("attachment_notes"):
                with st.expander("附件检查备注"):
                    for note in data["attachment_notes"]:
                        st.write(f"- {note}")

            render_chapter_preview(data["chapters"], sources=sources)
            render_report_download(data.get("output_files") or {"docx": data["report_path"]})
        except Exception as exc:  # pragma: no cover
            st.error(f"TIA 生成失败：{exc}")
            st.exception(exc)
