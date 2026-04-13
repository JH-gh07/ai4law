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

SCHEMA_PATH = "app_streamlit/schemas/cn_flow_schema.json"


def _split_csv(raw: str) -> list[str]:
    return [item.strip() for item in str(raw).replace("，", ",").split(",") if item.strip()]


def _build_attachments(uploaded_paths: list[str]) -> list[dict]:
    normalized: list[dict] = []
    roles = ["data_inventory", "entity_inventory"]

    for idx, path in enumerate(uploaded_paths):
        p = Path(path)
        file_format = p.suffix.lower().lstrip(".")
        if file_format not in {"xlsx", "csv", "docx", "pdf"}:
            continue
        file_role = roles[idx] if idx < len(roles) else "supporting_material"
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
render_hero("4.1 对华数据流动合规", "输入数据与实体清单，输出对华数据流动合规报告。", kicker="US 4.1")
sources = load_sources_index()

open_section("信息采集")
submitted, values = render_schema_multistep_form("cn_flow", SCHEMA_PATH)
uploaded_files = render_file_uploader(module="cn_flow", label="上传清单附件（至少2个，建议 data/entity 清单）")
use_async = st.checkbox("异步生成（推荐）", value=True, key="cn_flow__use_async")

if submitted:
    attachments = _build_attachments(uploaded_files)
    if len(attachments) < 2:
        st.error("4.1 至少需要 2 个可用附件（建议数据清单 + 实体清单）。")
    else:
        payload = {
            "company_name": str(values["company_name"]),
            "transfer_purpose": str(values["transfer_purpose"]),
            "data_categories": _split_csv(str(values["data_categories"])),
            "sensitive_data_flags": _split_csv(str(values["sensitive_data_flags"])),
            "recipient_entities": [
                {
                    "entity_name": str(values["recipient_entity_name"]),
                    "country_region": str(values["recipient_country_region"]),
                    "entity_role": str(values["recipient_role"]),
                    "is_restricted_party": bool(values["is_restricted_party"]),
                }
            ],
            "transfer_chain": str(values["transfer_chain"]),
            "attachments": attachments,
        }

        try:
            if use_async:
                accepted = post_json("/cn-flow/generate_async", payload)
                task_id = accepted["task_id"]
                with st.spinner(f"任务 {task_id} 执行中..."):
                    data = None
                    for _ in range(180):
                        status = get_json(f"/cn-flow/tasks/{task_id}")
                        if status["state"] == "COMPLETED":
                            data = status["result"]
                            break
                        if status["state"] == "FAILED":
                            raise RuntimeError(status.get("error") or "task failed")
                        time.sleep(0.5)
                    if data is None:
                        raise TimeoutError("cn-flow async timeout")
            else:
                data = post_json("/cn-flow/generate", payload)

            st.success("4.1 合规报告生成完成")
            st.write(f"企业：`{data['company_name']}`")
            st.write(f"风险等级：`{data['risk_level']}`")
            st.write(f"一致性问题数：{len(data.get('consistency_issues', []))}")

            if data.get("risk_items"):
                with st.expander("风险项"):
                    for item in data["risk_items"]:
                        st.write(f"- [{item['risk_level']}] {item['risk_id']} {item['title']}：{item['basis']}")

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
            st.error(f"4.1 生成失败：{exc}")
            st.exception(exc)
