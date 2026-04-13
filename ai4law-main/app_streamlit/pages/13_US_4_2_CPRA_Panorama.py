import sys
from pathlib import Path

for _parent in Path(__file__).resolve().parents:
    if (_parent / "app_streamlit").exists():
        _root = str(_parent)
        if _root not in sys.path:
            sys.path.insert(0, _root)
        break

import time
from pathlib import Path

import streamlit as st

from app_streamlit.components.file_uploader import render_file_uploader
from app_streamlit.components.report_preview import render_chapter_preview, render_report_download
from app_streamlit.components.schema_form import render_schema_multistep_form
from app_streamlit.services.client import get_json, post_json
from app_streamlit.services.knowledge import load_sources_index
from app_streamlit.theme import apply_theme, open_section, render_hero

SCHEMA_PATH = "app_streamlit/schemas/cpra_schema.json"


def _build_attachments(uploaded_paths: list[str], file_role: str) -> list[dict]:
    normalized: list[dict] = []
    for path in uploaded_paths:
        p = Path(path)
        file_format = p.suffix.lower().lstrip(".")
        if file_format not in {"docx", "pdf", "xlsx", "csv"}:
            continue
        normalized.append(
            {
                "file_role": file_role,
                "file_name": p.name,
                "file_format": file_format,
                "storage_uri": str(p),
                "size_bytes": p.stat().st_size if p.exists() else None,
            }
        )
    return normalized


apply_theme("us")
render_hero("4.2 加州隐私合规（CPRA）", "输出 CPRA 合规全景报告与整改建议。", kicker="US 4.2")
sources = load_sources_index()

open_section("信息采集")
submitted, values = render_schema_multistep_form("cpra", SCHEMA_PATH)
uploaded_files = render_file_uploader(module="cpra", label="上传 CPRA 附件（至少1个）")
use_async = st.checkbox("异步生成（推荐）", value=True, key="cpra__use_async")

if submitted:
    attachments = _build_attachments(uploaded_files, file_role=str(values["attachment_role"]))
    if not attachments:
        st.error("4.2 至少需要 1 个可用附件（docx/pdf/xlsx/csv）。")
    else:
        payload = {
            "company_name": str(values["company_name"]),
            "business_model": str(values["business_model"]),
            "data_lifecycle": str(values["data_lifecycle"]),
            "notice_and_consent": str(values["notice_and_consent"]),
            "consumer_rights_process": str(values["consumer_rights_process"]),
            "opt_out_and_sale_sharing": str(values["opt_out_and_sale_sharing"]),
            "vendor_management": str(values["vendor_management"]),
            "attachments": attachments,
        }

        try:
            if use_async:
                accepted = post_json("/cpra/generate_async", payload)
                task_id = accepted["task_id"]
                with st.spinner(f"任务 {task_id} 执行中..."):
                    data = None
                    for _ in range(180):
                        status = get_json(f"/cpra/tasks/{task_id}")
                        if status["state"] == "COMPLETED":
                            data = status["result"]
                            break
                        if status["state"] == "FAILED":
                            raise RuntimeError(status.get("error") or "task failed")
                        time.sleep(0.5)
                    if data is None:
                        raise TimeoutError("cpra async timeout")
            else:
                data = post_json("/cpra/generate", payload)

            st.success("CPRA 合规报告生成完成")
            st.write(f"企业：`{data['company_name']}`")
            st.write(f"风险等级：`{data['risk_level']}`")
            st.write(f"一致性问题数：{len(data.get('consistency_issues', []))}")

            if data.get("gap_items"):
                with st.expander("差距项"):
                    for item in data["gap_items"]:
                        st.write(
                            f"- [{item['risk_level']}] {item['domain']}（{item['phase']}）：{item['gap']}"
                        )

            if data.get("consistency_issues"):
                with st.expander("一致性问题详情"):
                    for issue in data["consistency_issues"]:
                        st.write(f"- {issue}")

            if data.get("attachment_notes"):
                with st.expander("附件检查备注"):
                    for note in data["attachment_notes"]:
                        st.write(f"- {note}")

            render_chapter_preview(data.get("chapters", []), sources=sources)
            render_report_download(data.get("output_files") or {"docx": data["report_path"]})
        except Exception as exc:  # pragma: no cover
            st.error(f"4.2 生成失败：{exc}")
            st.exception(exc)
