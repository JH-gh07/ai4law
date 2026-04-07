from __future__ import annotations

from html import escape
from typing import Iterable

import streamlit as st

from app_streamlit.services.knowledge import resolve_citation


def build_legal_basis_models(
    citations: Iterable[str],
    sources: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    models: list[dict[str, str]] = []
    for raw in citations:
        citation = str(raw).strip()
        if not citation:
            continue
        matched = resolve_citation(citation, sources=sources)
        if matched is None:
            models.append(
                {
                    "citation": citation,
                    "status": "未匹配",
                    "status_class": "is-missing",
                    "summary_title": "未匹配到知识库条目",
                    "summary_meta": "可在知识库中心手动检索或补充法规库映射。",
                    "source_org": "-",
                    "publish_date": "-",
                    "url": "",
                    "snapshot_path": "",
                }
            )
            continue

        note = matched.get("notes", "").strip() or "已匹配到法规来源，支持可追溯审计。"
        models.append(
            {
                "citation": citation,
                "status": "已匹配",
                "status_class": "is-matched",
                "summary_title": matched.get("title", "-"),
                "summary_meta": note,
                "source_org": matched.get("source_org", "-"),
                "publish_date": matched.get("publish_date", "-"),
                "url": matched.get("url", ""),
                "snapshot_path": matched.get("snapshot_path", ""),
            }
        )
    return models


def render_legal_basis_summary(
    models: list[dict[str, str]],
    *,
    title: str = "法律依据摘要",
    max_items: int = 6,
    key_prefix: str = "legal_basis",
) -> None:
    st.markdown(f"### {title}")
    if not models:
        st.info("当前结果未返回法律依据。")
        return

    shown = models[:max_items]
    if len(models) > max_items:
        st.caption(f"当前展示前 {max_items} 条，共 {len(models)} 条。")

    for idx, item in enumerate(shown, start=1):
        st.markdown(
            (
                '<div class="ai4law-legal-card">'
                f'<div class="ai4law-legal-topline"><span class="ai4law-legal-index">[{idx}]</span>'
                f'<span class="ai4law-legal-chip {escape(item["status_class"])}">{escape(item["status"])}</span></div>'
                f'<div class="ai4law-legal-citation">{escape(item["citation"])}</div>'
                f'<div class="ai4law-legal-title">{escape(item["summary_title"])}</div>'
                f'<div class="ai4law-legal-meta">{escape(item["summary_meta"])}</div>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        url = item.get("url", "")
        if url:
            st.link_button(f"打开来源链接（{idx}）", url)
