import streamlit as st


def apply_theme() -> None:
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@500;700&family=Source+Sans+3:wght@400;600;700&display=swap');

:root {
  --ai4law-bg-1: #f4f7fb;
  --ai4law-bg-2: #e9eff7;
  --ai4law-panel: #ffffff;
  --ai4law-ink: #1b2432;
  --ai4law-muted: #5b6475;
  --ai4law-accent: #0b4a8b;
  --ai4law-accent-2: #0e7490;
  --ai4law-border: #d8e0ed;
}

html, body, [class*="css"] {
  font-family: "Source Sans 3", "PingFang SC", "Microsoft YaHei", sans-serif;
  color: var(--ai4law-ink);
}

.stApp {
  background: radial-gradient(circle at 10% 0%, var(--ai4law-bg-2) 0%, var(--ai4law-bg-1) 46%, #f8fafc 100%);
}

h1, h2, h3 {
  font-family: "Noto Serif SC", serif;
  letter-spacing: 0.2px;
}

.hero {
  background: linear-gradient(135deg, #0b4a8b 0%, #0e7490 100%);
  color: white;
  border-radius: 18px;
  padding: 24px 28px;
  margin: 8px 0 18px 0;
  box-shadow: 0 10px 26px rgba(11, 74, 139, 0.25);
}

.hero-kicker {
  font-size: 12px;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  opacity: 0.85;
  margin-bottom: 6px;
}

.hero-title {
  font-size: 36px;
  line-height: 1.2;
  margin: 0;
}

.hero-subtitle {
  margin-top: 10px;
  font-size: 16px;
  opacity: 0.95;
}

.ai4law-card {
  background: var(--ai4law-panel);
  border: 1px solid var(--ai4law-border);
  border-radius: 14px;
  padding: 14px 16px;
  box-shadow: 0 4px 14px rgba(20, 35, 80, 0.05);
}

.ai4law-kpi-label {
  color: var(--ai4law-muted);
  font-size: 13px;
}

.ai4law-kpi-value {
  color: var(--ai4law-ink);
  font-size: 34px;
  font-weight: 700;
  line-height: 1.1;
}

.ai4law-kpi-sub {
  color: var(--ai4law-muted);
  font-size: 12px;
}

.ai4law-section {
  background: var(--ai4law-panel);
  border: 1px solid var(--ai4law-border);
  border-radius: 14px;
  padding: 14px 16px;
  margin: 12px 0;
}

.ai4law-module-title {
  font-family: "Noto Serif SC", serif;
  font-size: 20px;
  margin: 0 0 6px 0;
}

.ai4law-module-desc {
  color: var(--ai4law-muted);
  margin: 0;
}

.stButton > button {
  border-radius: 9px;
  border: 1px solid #0b4a8b;
  font-weight: 600;
}

.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #0b4a8b 0%, #0e7490 100%);
  color: white;
  border: none;
}

[data-testid="stSidebar"] {
  background: rgba(244, 247, 251, 0.92);
  border-right: 1px solid var(--ai4law-border);
}

[data-testid="stSidebarNav"] a {
  border-radius: 9px;
}

@media (max-width: 900px) {
  .hero-title { font-size: 28px; }
}
</style>
""",
        unsafe_allow_html=True,
    )


def render_hero(title: str, subtitle: str, kicker: str = "AI4Law") -> None:
    st.markdown(
        f"""
<div class="hero">
  <div class="hero-kicker">{kicker}</div>
  <h1 class="hero-title">{title}</h1>
  <div class="hero-subtitle">{subtitle}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_kpi_card(label: str, value: str, sub: str = "") -> None:
    st.markdown(
        f"""
<div class="ai4law-card">
  <div class="ai4law-kpi-label">{label}</div>
  <div class="ai4law-kpi-value">{value}</div>
  <div class="ai4law-kpi-sub">{sub}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def open_section(title: str, desc: str = "") -> None:
    content = f"<h3 class='ai4law-module-title'>{title}</h3>"
    if desc:
        content += f"<p class='ai4law-module-desc'>{desc}</p>"
    st.markdown(f"<div class='ai4law-section'>{content}</div>", unsafe_allow_html=True)
