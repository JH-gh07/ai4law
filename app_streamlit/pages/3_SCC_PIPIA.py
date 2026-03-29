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

SCHEMA_PATH = "app_streamlit/schemas/scc_schema.json"
DRAFT_PATH = Path("storage/drafts/scc_draft.json")

apply_theme()
render_hero("模块3：认证/标准合同路径", "生成 PIPIA 报告并检查备案相关风险。", kicker="SCC / PIPIA")
sources = load_sources_index()

DRAFT_PATH.parent.mkdir(parents=True, exist_ok=True)

col_a, col_b = st.columns(2)
with col_a:
    if st.button("保存草稿"):
        draft = {
            k: v
            for k, v in st.session_state.items()
            if k.startswith("scc__") and not k.endswith("_submit")
        }
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
submitted, values = render_schema_multistep_form("scc", SCHEMA_PATH)
uploaded_files = render_file_uploader(module="scc", label="上传SCC/PIPIA相关材料")
use_async = st.checkbox("异步生成（推荐）", value=True, key="scc__use_async")

if submitted:
    payload = {
        "company_name": str(values["company_name"]),
        "receiver_name": str(values["receiver_name"]),
        "receiver_country": str(values["receiver_country"]),
        "transfer_purpose": str(values["transfer_purpose"]),
        "pii_count": int(values["pii_count"]),
        "spi_count": int(values["spi_count"]),
        "has_scc_draft": bool(values["has_scc_draft"]),
        "uploaded_files": uploaded_files,
    }

    try:
        if use_async:
            accepted = post_json("/scc/generate_async", payload)
            task_id = accepted["task_id"]
            with st.spinner(f"任务 {task_id} 执行中..."):
                data = None
                for _ in range(180):
                    status = get_json(f"/scc/tasks/{task_id}")
                    if status["state"] == "COMPLETED":
                        data = status["result"]
                        break
                    if status["state"] == "FAILED":
                        raise RuntimeError(status.get("error") or "task failed")
                    time.sleep(0.5)
                if data is None:
                    raise TimeoutError("scc async timeout")
        else:
            data = post_json("/scc/generate", payload)

        st.success("PIPIA 报告生成完成")
        st.write(f"一致性问题数：{len(data['consistency_issues'])}")
        if data["consistency_issues"]:
            with st.expander("一致性问题详情"):
                for issue in data["consistency_issues"]:
                    st.write(f"- {issue}")

        render_chapter_preview(data["chapters"], sources=sources)
        render_report_download(data.get("output_files") or {"docx": data["report_path"]})
    except Exception as exc:  # pragma: no cover
        st.error(str(exc))
