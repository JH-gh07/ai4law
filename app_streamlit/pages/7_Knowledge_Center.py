from pathlib import Path

import streamlit as st

from app_streamlit.components.legal_basis import build_legal_basis_models, render_legal_basis_summary
from app_streamlit.services.knowledge import (
    load_practice_cases,
    load_sources_index,
    read_text_preview,
    resolve_citation,
)
from app_streamlit.theme import apply_theme, render_hero

apply_theme("knowledge")
render_hero("知识库中心", "浏览法规与案例索引，验证报告引用的可追溯性。", kicker="Knowledge Base")

sources = load_sources_index()
cases = load_practice_cases()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("法规/指南条目", len(sources))
with col2:
    st.metric("实践案例条目", len(cases))
with col3:
    p0_count = sum(1 for row in sources if row.get("usage_priority") == "P0")
    st.metric("P0 法规条目", p0_count)

tab1, tab2, tab3 = st.tabs(["法规与指南", "实践案例", "引用联动演示"])

with tab1:
    if not sources:
        st.info("未找到 sources.csv")
    else:
        layer_options = sorted({row.get("layer", "") for row in sources if row.get("layer")})
        path_options = sorted({row.get("path", "") for row in sources if row.get("path")})
        priority_options = sorted({row.get("usage_priority", "") for row in sources if row.get("usage_priority")})

        selected_layers = st.multiselect("按 layer 过滤", layer_options, default=layer_options)
        selected_paths = st.multiselect("按 path 过滤", path_options, default=path_options)
        selected_priority = st.multiselect("按优先级过滤", priority_options, default=priority_options)

        filtered_sources = [
            row
            for row in sources
            if row.get("layer") in selected_layers
            and row.get("path") in selected_paths
            and row.get("usage_priority") in selected_priority
        ]

        st.write(f"命中条目：{len(filtered_sources)}")
        st.dataframe(
            filtered_sources,
            use_container_width=True,
            hide_index=True,
            column_order=[
                "source_id",
                "title",
                "layer",
                "path",
                "authority_level",
                "publish_date",
                "usage_priority",
                "url",
            ],
        )

        if filtered_sources:
            idx = st.selectbox(
                "查看条目详情",
                options=range(len(filtered_sources)),
                format_func=lambda i: f"{filtered_sources[i].get('source_id', '')} | {filtered_sources[i].get('title', '')}",
            )
            selected = filtered_sources[idx]
            st.code(selected.get("snapshot_path", ""))
            if selected.get("url"):
                st.link_button("打开来源链接", selected["url"])

            preview = read_text_preview(selected.get("snapshot_path", ""), limit=600)
            if preview:
                with st.expander("本地快照文本预览", expanded=False):
                    st.write(preview)

with tab2:
    if not cases:
        st.info("未找到 practice_cases.csv")
    else:
        module_options = sorted({m for row in cases for m in row.get("expected_module", "").split("|") if m})
        priority_options = sorted({row.get("priority", "") for row in cases if row.get("priority")})

        selected_modules = st.multiselect("按模块过滤", module_options, default=module_options)
        selected_priority = st.multiselect("按优先级过滤", priority_options, default=priority_options)

        def _match_case(case_row: dict[str, str]) -> bool:
            modules = [m for m in case_row.get("expected_module", "").split("|") if m]
            return any(m in selected_modules for m in modules) and case_row.get("priority") in selected_priority

        filtered_cases = [row for row in cases if _match_case(row)]

        st.write(f"命中案例：{len(filtered_cases)}")
        st.dataframe(
            filtered_cases,
            use_container_width=True,
            hide_index=True,
            column_order=[
                "case_id",
                "case_title",
                "case_type",
                "expected_module",
                "priority",
                "usable_for_validation",
                "url",
            ],
        )

        if filtered_cases:
            idx = st.selectbox(
                "查看案例详情",
                options=range(len(filtered_cases)),
                format_func=lambda i: f"{filtered_cases[i].get('case_id', '')} | {filtered_cases[i].get('case_title', '')}",
                key="case_detail_select",
            )
            selected = filtered_cases[idx]
            st.write(f"限制：{selected.get('limitations', '-')}")
            st.write(f"可用材料：{selected.get('available_artifacts', '-')}")
            if selected.get("url"):
                st.link_button("打开案例来源", selected["url"])
            preview = read_text_preview(selected.get("snapshot_path", ""), limit=600)
            if preview:
                with st.expander("案例快照文本预览", expanded=False):
                    st.write(preview)

with tab3:
    citation_query = st.text_input("输入引用文本", value="数据出境安全评估办法第4条")
    if citation_query.strip():
        query_models = build_legal_basis_models([citation_query], sources=sources)
        render_legal_basis_summary(
            query_models,
            title="引用匹配摘要",
            max_items=1,
            key_prefix="knowledge_center_citation_query",
        )

        matched = resolve_citation(citation_query, sources=sources)
        if matched:
            st.markdown("#### 结构化匹配详情")
            st.write(f"source_id：{matched.get('source_id', '-')}")
            st.write(f"层级：{matched.get('layer', '-')}")
            st.write(f"路径：{matched.get('path', '-')}")
            snapshot_path = matched.get("snapshot_path", "")
            st.caption(f"快照路径：{snapshot_path}")
            if snapshot_path and Path(snapshot_path).exists():
                with st.expander("快照预览", expanded=False):
                    st.write(read_text_preview(snapshot_path, limit=600))
