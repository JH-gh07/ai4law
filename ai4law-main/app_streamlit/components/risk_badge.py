import streamlit as st

_RISK_COLOR = {
    "HIGH": "#b42318",
    "MEDIUM": "#b54708",
    "LOW": "#067647",
}


def render_risk_badge(risk_level: str) -> None:
    level = risk_level.upper().strip()
    color = _RISK_COLOR.get(level, "#344054")
    st.markdown(
        (
            "<span style=\"display:inline-block;padding:2px 8px;border-radius:12px;"
            "font-size:12px;font-weight:600;color:white;background:{}\">{}</span>"
        ).format(color, level),
        unsafe_allow_html=True,
    )
