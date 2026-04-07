import time
from pathlib import Path

import streamlit as st

from app_streamlit.components.file_uploader import render_file_uploader
from app_streamlit.components.report_preview import render_chapter_preview, render_report_download
from app_streamlit.components.schema_form import render_schema_multistep_form
from app_streamlit.services.client import get_json, post_json
from app_streamlit.services.knowledge import load_sources_index
from app_streamlit.theme import apply_theme, open_section, render_hero

SCHEMA_PATH = "app_streamlit/schemas/bcr_schema.json"


def _build_attachments(uploaded_paths: list[str]) -> list[dict]:
    attachments: list[dict] = []
    for path in uploaded_paths:
        p = Path(path)
        file_format = p.suffix.lower().lstrip(".")
        if file_format not in {"pdf", "docx"}:
            continue
        attachments.append(
            {
                "file_name": p.name,
                "file_format": file_format,
                "storage_uri": str(p),
            }
        )
    return attachments


apply_theme("eu")
render_hero("3.2 BCR审核", "基于审查项与证据输出 BCR 审查报告。", kicker="EU 3.2")
sources = load_sources_index()

open_section("信息采集")
submitted, values = render_schema_multistep_form("bcr", SCHEMA_PATH)
uploaded_files = render_file_uploader(module="bcr", label="上传 BCR 材料（可选，pdf/docx）")
use_async = st.checkbox("异步生成（推荐）", value=True, key="bcr__use_async")

if submitted:
    payload = {
        "company_name": str(values["company_name"]),
        "review_items": [
            {
                "code": str(values["code"]),
                "title": str(values["title"]),
                "score": str(values["score"]),
                "finding": str(values["finding"]),
                "legal_basis": str(values["legal_basis"]),
                "recommendation": str(values["recommendation"]),
                "evidence": str(values["evidence"]),
            }
        ],
        "attachments": _build_attachments(uploaded_files),
        "uploaded_files": uploaded_files,
    }

    try:
        if use_async:
            accepted = post_json("/bcr/generate_async", payload)
            task_id = accepted["task_id"]
            with st.spinner(f"任务 {task_id} 执行中..."):
                data = None
                for _ in range(180):
                    status = get_json(f"/bcr/tasks/{task_id}")
                    if status["state"] == "COMPLETED":
                        data = status["result"]
                        break
                    if status["state"] == "FAILED":
                        raise RuntimeError(status.get("error") or "task failed")
                    time.sleep(0.5)
                if data is None:
                    raise TimeoutError("bcr async timeout")
        else:
            data = post_json("/bcr/generate", payload)

        st.success("BCR 审查报告生成完成")
        st.write(f"总体评级：`{data['rating']}`")
        st.write(f"问题项数量：{len(data.get('problems', []))}")
        st.write(f"一致性问题数：{len(data.get('consistency_issues', []))}")

        if data.get("problems"):
            with st.expander("问题清单"):
                for item in data["problems"]:
                    st.write(f"- [{item['risk_level']}] {item['code']} {item['title']}：{item['finding']}")

        if data.get("consistency_issues"):
            with st.expander("一致性问题详情"):
                for issue in data["consistency_issues"]:
                    st.write(f"- {issue}")

        render_chapter_preview(data.get("chapters", []), sources=sources)
        render_report_download(data.get("output_files") or {"docx": data["report_path"]})
    except Exception as exc:  # pragma: no cover
        st.error(f"BCR 审核失败：{exc}")
        st.exception(exc)
