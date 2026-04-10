import sys
from pathlib import Path

for _parent in Path(__file__).resolve().parents:
    if (_parent / "app_streamlit").exists():
        _root = str(_parent)
        if _root not in sys.path:
            sys.path.insert(0, _root)
        break

import json
import time
from pathlib import Path

import streamlit as st

from app_streamlit.components.file_uploader import render_file_uploader
from app_streamlit.components.report_preview import render_chapter_preview, render_report_download
from app_streamlit.components.schema_form import render_schema_multistep_form
from app_streamlit.services.client import get_json, post_json
from app_streamlit.services.knowledge import load_sources_index
from app_streamlit.theme import apply_theme, open_section, render_hero

SCHEMA_PATH = "app_streamlit/schemas/pipia_schema.json"
DRAFT_PATH = Path("storage/drafts/pipia_draft.json")
_ALLOWED_ATTACHMENT_FORMATS = {"doc", "docx", "pdf", "txt", "md", "json", "csv"}


def _split_csv(raw: str) -> list[str]:
    return [item.strip() for item in str(raw).replace("，", ",").split(",") if item.strip()]


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


apply_theme("cn")
render_hero("2.3 认证/标准合同路径（PIPIA）", "生成可提交前使用的 PIPIA 报告草案。", kicker="CN 2.3")
sources = load_sources_index()

DRAFT_PATH.parent.mkdir(parents=True, exist_ok=True)

col_a, col_b = st.columns(2)
with col_a:
    if st.button("保存草稿"):
        draft = {k: v for k, v in st.session_state.items() if k.startswith("pipia__") and not k.endswith("_submit")}
        DRAFT_PATH.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
        st.success(f"草稿已保存：{DRAFT_PATH}")
with col_b:
    if st.button("恢复草稿"):
        if DRAFT_PATH.exists():
            draft = json.loads(DRAFT_PATH.read_text(encoding="utf-8"))
            st.session_state.update(draft)
            st.success("草稿已恢复")
            st.rerun()
        else:
            st.info("暂无草稿")

open_section("信息采集")
submitted, values = render_schema_multistep_form("pipia", SCHEMA_PATH)
uploaded_files = render_file_uploader(module="pipia", label="上传 PIPIA 相关材料（至少1个）")
use_async = st.checkbox("异步生成（推荐）", value=True, key="pipia__use_async")

if submitted:
    attachments = _build_attachments(uploaded_files, file_role=str(values["attachment_role"]))
    if not attachments:
        st.error("PIPIA 至少需要 1 个可用附件（doc/docx/pdf/txt/md/json/csv）。")
    else:
        payload = {
            "route_type": str(values["route_type"]),
            "company_profile": {
                "company_name": str(values["company_name"]),
                "company_uscc": str(values["company_uscc"]),
                "is_ciio": bool(values["is_ciio"]),
                "processing_person_count": int(values["processing_person_count"]),
                "outbound_pi_count": int(values["outbound_pi_count"]),
                "outbound_spi_count": int(values["outbound_spi_count"]),
                "industry": str(values["industry"]),
            },
            "transfer_context": {
                "purpose": str(values["purpose"]),
                "recipient_name": str(values["recipient_name"]),
                "recipient_country_region": str(values["recipient_country_region"]),
                "legal_basis": str(values["legal_basis"]),
            },
            "personal_info_scope": {
                "pi_categories": _split_csv(str(values["pi_categories"])),
                "spi_categories": _split_csv(str(values["spi_categories"])),
                "subject_volume": int(values["subject_volume"]),
            },
            "rights_protection": {
                "notice_mechanism": str(values["notice_mechanism"]),
                "consent_mechanism": str(values["consent_mechanism"]),
                "dsar_channel": str(values["dsar_channel"]),
                "retention_policy": str(values["retention_policy"]),
            },
            "emergency_plan": {
                "incident_response_sla_hours": int(values["incident_response_sla_hours"]),
                "escalation_path": str(values["escalation_path"]),
            },
            "attachments": attachments,
        }

        try:
            if use_async:
                accepted = post_json("/pipia/generate_async", payload)
                task_id = accepted["task_id"]
                with st.spinner(f"任务 {task_id} 执行中..."):
                    data = None
                    for _ in range(240):
                        status = get_json(f"/pipia/tasks/{task_id}")
                        if status["state"] == "COMPLETED":
                            data = status["result"]
                            break
                        if status["state"] == "FAILED":
                            raise RuntimeError(status.get("error") or "task failed")
                        time.sleep(0.5)
                    if data is None:
                        raise TimeoutError("pipia async timeout")
            else:
                data = post_json("/pipia/generate", payload)

            st.success("PIPIA 报告生成完成")
            st.write(f"路径类型：`{data['route_type']}`")
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
            st.error(f"PIPIA 生成失败：{exc}")
            st.exception(exc)
