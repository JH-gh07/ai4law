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

SCHEMA_PATH = "app_streamlit/schemas/scc_schema.json"
DRAFT_PATH = Path("storage/drafts/eu_scc_draft.json")

apply_theme("eu")
render_hero("3.1 SCC审查", "上传与填写 SCC 场景信息，输出 SCC 审查报告。", kicker="EU 3.1")
sources = load_sources_index()

DRAFT_PATH.parent.mkdir(parents=True, exist_ok=True)

col_a, col_b = st.columns(2)
with col_a:
    if st.button("保存草稿"):
        draft = {k: v for k, v in st.session_state.items() if k.startswith("eu_scc__") and not k.endswith("_submit")}
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
submitted, values = render_schema_multistep_form("eu_scc", SCHEMA_PATH)
uploaded_files = render_file_uploader(module="eu_scc", label="上传 SCC 相关材料（可选）")
use_async = st.checkbox("异步生成（推荐）", value=True, key="eu_scc__use_async")

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

        st.success("SCC 审查报告生成完成")
        st.write(f"一致性问题数：{len(data['consistency_issues'])}")
        if data["consistency_issues"]:
            with st.expander("一致性问题详情"):
                for issue in data["consistency_issues"]:
                    st.write(f"- {issue}")

        render_chapter_preview(data["chapters"], sources=sources)
        render_report_download(data.get("output_files") or {"docx": data["report_path"]})
    except Exception as exc:  # pragma: no cover
        st.error(f"SCC 审查失败：{exc}")
        st.exception(exc)
