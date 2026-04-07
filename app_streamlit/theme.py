import streamlit as st


_SIDEBAR_DOMAIN_KEY = "ai4law_sidebar_domain"


def _nav_item(label: str, page_path: str, domain: str) -> None:
    key = f"nav_btn_{domain}_{page_path.replace('/', '_').replace('.', '_')}"
    if hasattr(st, "switch_page"):
        if st.button(label, key=key, use_container_width=True):
            st.session_state[_SIDEBAR_DOMAIN_KEY] = domain
            st.switch_page(page_path)
    elif hasattr(st, "page_link"):
        st.page_link(page_path, label=label)
    else:
        st.caption(label)


def _render_sidebar_navigation(active_domain: str | None = None) -> None:
    if active_domain:
        st.session_state[_SIDEBAR_DOMAIN_KEY] = active_domain

    selected = st.session_state.get(_SIDEBAR_DOMAIN_KEY, "home")

    with st.sidebar:
        st.markdown(
            """
<div class="ai4law-side-brand">
  <div class="ai4law-side-kicker">AI4LAW V2</div>
  <div class="ai4law-side-title">功能导航</div>
  <div class="ai4law-side-desc">先选择法域，再进入对应子功能。</div>
</div>
""",
            unsafe_allow_html=True,
        )

        if not hasattr(st, "switch_page") and not hasattr(st, "page_link"):
            st.info("当前 Streamlit 版本不支持导航控件，请从页面入口访问。")
            return

        _nav_item("首页", "Home.py", "home")

        with st.expander("模块总览", expanded=selected in {"cn", "eu", "us"}):
            with st.expander("中国大陆 -> 境外", expanded=selected == "cn"):
                _nav_item("2.1 合规路径诊断", "pages/1_Diagnosis.py", "cn")
                _nav_item("2.2 安全评估路径", "pages/2_Assessment.py", "cn")
                _nav_item("2.3 认证/标准合同路径（PIPIA）", "pages/3_SCC_PIPIA.py", "cn")
                _nav_item("2.4 通用服务", "pages/4_General_Service.py", "cn")
                _nav_item("2.5 文档专项智能审查", "pages/5_Document_Review.py", "cn")

            with st.expander("欧盟 -> 境外", expanded=selected == "eu"):
                _nav_item("3.1 SCC审查", "pages/8_EU_3_1_SCC_Review.py", "eu")
                _nav_item("3.2 BCR审核", "pages/9_EU_3_2_BCR_Review.py", "eu")
                _nav_item("3.3 DPIA草案生成", "pages/10_EU_3_3_DPIA_Draft.py", "eu")
                _nav_item("3.4 TIA草案生成", "pages/11_EU_3_4_TIA_Draft.py", "eu")

            with st.expander("美国 -> 境外", expanded=selected == "us"):
                _nav_item("4.1 对华数据流动合规", "pages/12_US_4_1_CN_Flow_Compliance.py", "us")
                _nav_item("4.2 加州隐私合规", "pages/13_US_4_2_CPRA_Panorama.py", "us")

        _nav_item("报告中心", "pages/6_Report_Center.py", "report")
        _nav_item("知识库中心", "pages/7_Knowledge_Center.py", "knowledge")


def apply_theme(active_domain: str | None = None) -> None:
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;500;600;700&family=Noto+Serif+SC:wght@500;700&display=swap');

:root {
  --ai4law-bg-1: #f2f5fa;
  --ai4law-bg-2: #e8eef7;
  --ai4law-panel: #ffffff;
  --ai4law-panel-soft: rgba(255, 255, 255, 0.82);
  --ai4law-ink: #1d2a3b;
  --ai4law-muted: #5f6f86;
  --ai4law-border: #d2dced;
  --ai4law-cn: #0b4a8b;
  --ai4law-eu: #0f766e;
  --ai4law-us: #1f7a46;
  --ai4law-warn: #b45309;
}

html, body, [class*="css"] {
  font-family: "Source Sans 3", "PingFang SC", "Microsoft YaHei", sans-serif;
  color: var(--ai4law-ink);
}

.stApp {
  background:
    radial-gradient(1000px 550px at 105% -20%, rgba(15, 118, 110, 0.10), transparent 60%),
    radial-gradient(900px 520px at -15% -8%, rgba(11, 74, 139, 0.12), transparent 58%),
    linear-gradient(180deg, var(--ai4law-bg-1) 0%, var(--ai4law-bg-2) 52%, #f8fafd 100%);
}

[data-testid="stAppViewContainer"] [data-testid="stVerticalBlock"] {
  gap: 0.82rem;
}

[data-testid="stAppViewContainer"] .main .block-container {
  max-width: 1180px;
  padding-top: 1.1rem;
  padding-bottom: 2.4rem;
}

h1, h2, h3 {
  font-family: "Noto Serif SC", serif;
  letter-spacing: 0.2px;
}

.hero {
  background: linear-gradient(128deg, #0b4a8b 0%, #0f5b9f 52%, #0f766e 100%);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 18px;
  padding: 24px 28px;
  margin: 8px 0 16px 0;
  box-shadow: 0 14px 32px rgba(10, 50, 95, 0.26);
}

.hero-kicker {
  font-size: 12px;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  opacity: 0.9;
  margin-bottom: 6px;
}

.hero-title {
  font-size: 34px;
  line-height: 1.2;
  margin: 0;
}

.hero-subtitle {
  margin-top: 10px;
  font-size: 16px;
  opacity: 0.96;
}

.ai4law-card {
  background: var(--ai4law-panel-soft);
  backdrop-filter: blur(4px);
  border: 1px solid var(--ai4law-border);
  border-radius: 14px;
  padding: 14px 16px;
  box-shadow: 0 5px 14px rgba(26, 39, 71, 0.06);
}

.ai4law-kpi-label {
  color: var(--ai4law-muted);
  font-size: 13px;
  font-weight: 600;
}

.ai4law-kpi-value {
  color: var(--ai4law-ink);
  font-size: 32px;
  font-weight: 700;
  line-height: 1.1;
}

.ai4law-kpi-sub {
  color: var(--ai4law-muted);
  font-size: 12px;
}

.ai4law-section {
  background: var(--ai4law-panel-soft);
  border: 1px solid var(--ai4law-border);
  border-radius: 14px;
  padding: 14px 16px;
  margin: 10px 0;
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

.ai4law-side-brand {
  margin: 0.3rem 0 0.7rem 0;
  padding: 0.75rem 0.82rem;
  border-radius: 12px;
  background: linear-gradient(145deg, rgba(11, 74, 139, 0.12), rgba(15, 118, 110, 0.1));
  border: 1px solid var(--ai4law-border);
}

.ai4law-side-kicker {
  font-size: 11px;
  letter-spacing: 1.1px;
  color: #0f5a86;
  font-weight: 700;
}

.ai4law-side-title {
  margin-top: 0.12rem;
  font-weight: 700;
  font-size: 1rem;
}

.ai4law-side-desc {
  margin-top: 0.22rem;
  color: var(--ai4law-muted);
  font-size: 0.84rem;
}

[data-testid="stSidebar"] {
  background: rgba(242, 246, 252, 0.94);
  border-right: 1px solid var(--ai4law-border);
}

[data-testid="stSidebarNav"] {
  display: none;
}

[data-testid="stSidebar"] [data-testid="stExpander"] {
  background: rgba(255, 255, 255, 0.68);
}

[data-testid="stSidebar"] .stButton > button {
  justify-content: flex-start;
}

.stButton > button {
  border-radius: 10px;
  border: 1px solid #9ab2d5;
  font-weight: 600;
  transition: all 0.18s ease;
  background: #ffffff;
}

.stButton > button:hover {
  transform: translateY(-1px);
  border-color: #6d8fc1;
}

.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #0b4a8b 0%, #0f766e 100%);
  color: white;
  border-color: transparent;
  box-shadow: 0 9px 20px rgba(11, 74, 139, 0.24);
}

[data-testid="stExpander"] {
  border: 1px solid var(--ai4law-border);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.78);
}

[data-testid="stMetric"] {
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid var(--ai4law-border);
  border-radius: 12px;
  padding: 0.25rem 0.5rem;
}

[data-testid="stMetricValue"] {
  font-size: 1.65rem;
}

div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div,
textarea {
  border-radius: 10px !important;
  border: 1px solid var(--ai4law-border) !important;
  background: rgba(255, 255, 255, 0.95) !important;
}

[data-testid="stTextInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stNumberInput"] label,
[data-testid="stTextArea"] label,
[data-testid="stRadio"] label,
[data-testid="stCheckbox"] label {
  font-weight: 600;
}

[data-testid="stFileUploaderDropzone"] {
  border: 1.5px dashed #89a4ca;
  border-radius: 12px;
  background: rgba(245, 250, 255, 0.85);
}

.stCodeBlock,
code {
  border-radius: 9px;
}

.stAlert {
  border-radius: 10px;
  border-width: 1px;
}

[data-testid="stLinkButton"] a {
  border-radius: 10px;
}

.ai4law-legal-card {
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid var(--ai4law-border);
  border-left: 4px solid #90a8c9;
  border-radius: 12px;
  padding: 10px 12px;
  margin: 0.35rem 0 0.45rem 0;
}

.ai4law-legal-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.18rem;
}

.ai4law-legal-index {
  font-size: 0.8rem;
  color: var(--ai4law-muted);
  font-weight: 700;
}

.ai4law-legal-chip {
  display: inline-block;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  padding: 2px 8px;
  border: 1px solid transparent;
}

.ai4law-legal-chip.is-matched {
  color: #0b5f3a;
  background: #e8f7ef;
  border-color: #9dd7b7;
}

.ai4law-legal-chip.is-missing {
  color: #8d4f07;
  background: #fff4e5;
  border-color: #f3c88d;
}

.ai4law-legal-citation {
  font-size: 1rem;
  color: var(--ai4law-ink);
  font-weight: 650;
  line-height: 1.4;
}

.ai4law-legal-title {
  margin-top: 0.22rem;
  font-size: 0.92rem;
  color: #1f3d5f;
  font-weight: 620;
}

.ai4law-legal-meta {
  margin-top: 0.16rem;
  color: var(--ai4law-muted);
  font-size: 0.84rem;
}

.ai4law-domain-tile {
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid var(--ai4law-border);
  border-top: 4px solid var(--domain-accent);
  border-radius: 14px;
  padding: 12px 14px;
  min-height: 150px;
  box-shadow: 0 6px 14px rgba(26, 39, 71, 0.06);
}

.ai4law-domain-tile.is-active {
  box-shadow: 0 10px 24px rgba(11, 74, 139, 0.16);
  transform: translateY(-1px);
}

.ai4law-domain-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem;
}

.ai4law-domain-title {
  font-size: 0.98rem;
  color: #2f4260;
  font-weight: 700;
}

.ai4law-domain-state {
  font-size: 0.72rem;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid var(--ai4law-border);
  background: rgba(255, 255, 255, 0.88);
  color: #496181;
  font-weight: 700;
}

.ai4law-domain-count {
  margin-top: 0.45rem;
  font-size: 1.24rem;
  font-weight: 760;
  color: #17283f;
}

.ai4law-domain-summary {
  margin-top: 0.45rem;
  color: var(--ai4law-muted);
  font-size: 0.88rem;
  line-height: 1.45;
}

.ai4law-focus-card {
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid var(--ai4law-border);
  border-left: 5px solid var(--domain-accent);
  border-radius: 14px;
  padding: 14px 16px;
}

.ai4law-focus-kicker {
  font-size: 0.8rem;
  color: #5d7390;
  font-weight: 700;
  letter-spacing: 0.4px;
}

.ai4law-focus-title {
  margin-top: 0.22rem;
  font-size: 1.55rem;
  font-weight: 760;
  color: #1d2f49;
}

.ai4law-focus-summary {
  margin-top: 0.38rem;
  font-size: 0.95rem;
  color: var(--ai4law-muted);
}

.ai4law-flow-card {
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid var(--ai4law-border);
  border-radius: 14px;
  padding: 14px 16px;
}

.ai4law-flow-title {
  font-size: 1.03rem;
  font-weight: 760;
  color: #22334a;
}

.ai4law-flow-list {
  margin: 0.5rem 0 0 1.1rem;
  color: #2d3f58;
  line-height: 1.6;
  font-size: 0.96rem;
  font-weight: 620;
}

.ai4law-feature-card {
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid var(--ai4law-border);
  border-left: 4px solid var(--domain-accent);
  border-radius: 12px;
  padding: 11px 14px;
  min-height: 84px;
}

.ai4law-feature-title {
  font-size: 1.04rem;
  font-weight: 740;
  color: #1b2f4a;
}

.ai4law-feature-io {
  margin-top: 0.28rem;
  font-size: 0.86rem;
  color: #5f738d;
  line-height: 1.45;
}

.ai4law-quick-title {
  font-size: 1.02rem;
  font-weight: 730;
  color: #263a56;
  margin-bottom: 2px;
}

.ai4law-home-section-title {
  margin-top: 0.55rem;
  font-size: 1.55rem;
  font-weight: 760;
  color: #1c2e49;
}

.ai4law-home-section-desc {
  margin-top: 0.2rem;
  margin-bottom: 0.65rem;
  color: #5f738d;
  font-size: 0.96rem;
}

.ai4law-home-stat {
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid var(--ai4law-border);
  border-radius: 14px;
  padding: 14px 16px;
  box-shadow: 0 8px 18px rgba(26, 39, 71, 0.07);
}

.ai4law-home-stat.is-cn {
  border-top: 3px solid #0b4a8b;
}

.ai4law-home-stat.is-eu {
  border-top: 3px solid #0f766e;
}

.ai4law-home-stat.is-us {
  border-top: 3px solid #1f7a46;
}

.ai4law-home-stat-label {
  font-size: 0.91rem;
  color: #5a6f8a;
  font-weight: 680;
}

.ai4law-home-stat-value {
  margin-top: 0.2rem;
  font-size: 2.05rem;
  line-height: 1.1;
  font-weight: 780;
  color: #1a2c46;
}

.ai4law-home-stat-sub {
  margin-top: 0.24rem;
  font-size: 0.86rem;
  color: #677d98;
}

.ai4law-home-domain-card {
  height: 100%;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid var(--ai4law-border);
  border-radius: 14px;
  padding: 14px 16px;
  box-shadow: 0 8px 18px rgba(26, 39, 71, 0.07);
}

.ai4law-home-domain-card.is-cn {
  border-left: 4px solid #0b4a8b;
}

.ai4law-home-domain-card.is-eu {
  border-left: 4px solid #0f766e;
}

.ai4law-home-domain-card.is-us {
  border-left: 4px solid #1f7a46;
}

.ai4law-home-domain-title {
  font-size: 1.04rem;
  font-weight: 730;
  color: #1f3554;
}

.ai4law-home-domain-modules {
  margin-top: 0.38rem;
  font-size: 1.34rem;
  line-height: 1.2;
  font-weight: 780;
  color: #1a2d48;
}

.ai4law-home-domain-desc {
  margin-top: 0.42rem;
  font-size: 0.89rem;
  color: #627892;
  line-height: 1.45;
}

.ai4law-home-flow-grid {
  margin-top: 0.44rem;
  display: grid;
  gap: 10px;
}

.ai4law-home-flow-item {
  display: grid;
  grid-template-columns: 54px 1fr;
  gap: 10px;
  align-items: center;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid var(--ai4law-border);
  border-radius: 13px;
  padding: 10px 12px;
}

.ai4law-home-flow-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 32px;
  border-radius: 10px;
  background: linear-gradient(130deg, #0b4a8b, #0f766e);
  color: #fff;
  font-size: 0.92rem;
  font-weight: 780;
}

.ai4law-home-flow-text {
  color: #233850;
  font-size: 0.96rem;
}

.ai4law-home-quick-card {
  min-height: 104px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid var(--ai4law-border);
  border-radius: 13px;
  padding: 12px 14px;
}

.ai4law-home-quick-title {
  font-size: 1.08rem;
  font-weight: 740;
  color: #1d3250;
}

.ai4law-home-quick-desc {
  margin-top: 0.34rem;
  font-size: 0.88rem;
  color: #607891;
  line-height: 1.45;
}

.ai4law-home-command {
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(440px 220px at 100% -5%, rgba(15, 118, 110, 0.2), transparent 68%),
    linear-gradient(145deg, rgba(255, 255, 255, 0.9), rgba(236, 244, 255, 0.88));
  border: 1px solid #c4d4ec;
  border-radius: 16px;
  padding: 16px 18px;
  box-shadow: 0 10px 24px rgba(22, 44, 79, 0.1);
}

.ai4law-home-top-grid {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 12px;
}

.ai4law-home-command-kicker {
  font-size: 0.72rem;
  letter-spacing: 1.4px;
  font-weight: 760;
  color: #235482;
}

.ai4law-home-command-title {
  margin-top: 0.26rem;
  font-size: 1.62rem;
  line-height: 1.2;
  font-weight: 780;
  color: #1a2f4d;
}

.ai4law-home-command-desc {
  margin-top: 0.48rem;
  color: #5b7090;
  font-size: 0.92rem;
  line-height: 1.55;
}

.ai4law-home-livebox {
  height: 100%;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid #c8d7ee;
  border-radius: 16px;
  padding: 16px 18px;
  box-shadow: 0 10px 24px rgba(22, 44, 79, 0.09);
}

.ai4law-home-live-label {
  font-size: 0.82rem;
  color: #5d7593;
  font-weight: 700;
}

.ai4law-home-live-status {
  margin-top: 0.35rem;
  font-size: 2.08rem;
  font-weight: 800;
  line-height: 1.05;
  color: #1d3352;
}

.ai4law-home-live-meta {
  margin-top: 0.34rem;
  color: #617995;
  font-size: 0.88rem;
}

.ai4law-home-chipstat {
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid #ccd9ee;
  border-radius: 13px;
  padding: 12px 14px;
}

.ai4law-home-stat-grid {
  margin-top: 0.25rem;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.ai4law-home-chipstat-label {
  font-size: 0.82rem;
  font-weight: 700;
  color: #5d7593;
}

.ai4law-home-chipstat-value {
  margin-top: 0.18rem;
  font-size: 1.46rem;
  font-weight: 790;
  color: #1e3453;
}

.ai4law-home-chipstat-sub {
  margin-top: 0.22rem;
  font-size: 0.84rem;
  color: #647c97;
}

.ai4law-home-domain-panel {
  min-height: 180px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid #c6d5eb;
  border-radius: 14px;
  padding: 14px 15px;
  box-shadow: 0 10px 20px rgba(22, 44, 79, 0.09);
}

.ai4law-home-domain-grid {
  margin-top: 0.35rem;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.ai4law-home-domain-panel.is-cn {
  border-left: 5px solid #0b4a8b;
}

.ai4law-home-domain-panel.is-eu {
  border-left: 5px solid #0f766e;
}

.ai4law-home-domain-panel.is-us {
  border-left: 5px solid #1f7a46;
}

.ai4law-home-domain-panel-title {
  font-size: 1.02rem;
  font-weight: 740;
  color: #213a5a;
}

.ai4law-home-domain-panel-mods {
  margin-top: 0.34rem;
  font-size: 1.34rem;
  font-weight: 800;
  color: #1b304f;
}

.ai4law-home-domain-panel-desc {
  margin-top: 0.38rem;
  font-size: 0.88rem;
  line-height: 1.45;
  color: #5f7692;
}

.ai4law-home-domain-panel-tip {
  margin-top: 0.58rem;
  font-size: 0.79rem;
  color: #2c5d8f;
  font-weight: 680;
}

.ai4law-home-track {
  margin-top: 0.35rem;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  align-items: stretch;
  gap: 8px;
}

.ai4law-home-track-step {
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid #c6d5eb;
  border-radius: 14px;
  padding: 12px;
}

.ai4law-home-track-no {
  display: inline-block;
  font-size: 0.78rem;
  font-weight: 780;
  letter-spacing: 0.8px;
  color: #ffffff;
  background: linear-gradient(120deg, #0b4a8b, #0f766e);
  padding: 2px 8px;
  border-radius: 999px;
}

.ai4law-home-track-text {
  margin-top: 0.42rem;
  color: #28405e;
  font-size: 0.91rem;
  line-height: 1.5;
}

.ai4law-home-quick {
  min-height: 108px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid #c8d7ee;
  border-radius: 13px;
  padding: 12px 14px;
}

.ai4law-home-quick-title {
  font-size: 1.02rem;
  font-weight: 750;
  color: #1f3655;
}

.ai4law-home-quick-desc {
  margin-top: 0.32rem;
  font-size: 0.87rem;
  line-height: 1.45;
  color: #607893;
}

.homev3-top {
  display: grid;
  grid-template-columns: 1.65fr 1fr;
  gap: 12px;
}

.homev3-intro {
  background:
    radial-gradient(420px 180px at 100% 0, rgba(15, 118, 110, 0.18), transparent 70%),
    linear-gradient(145deg, rgba(255, 255, 255, 0.92), rgba(236, 244, 255, 0.88));
  border: 1px solid #c6d7ee;
  border-radius: 16px;
  padding: 16px 18px;
  box-shadow: 0 10px 24px rgba(19, 37, 71, 0.1);
}

.homev3-intro-kicker {
  font-size: 0.73rem;
  font-weight: 760;
  letter-spacing: 1.3px;
  color: #2b5a8a;
}

.homev3-intro-title {
  margin-top: 0.28rem;
  font-size: 1.72rem;
  line-height: 1.16;
  font-weight: 790;
  color: #1a2f4c;
}

.homev3-intro-desc {
  margin-top: 0.5rem;
  font-size: 0.92rem;
  line-height: 1.58;
  color: #5a6f8a;
}

.homev3-status {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid #c6d7ee;
  border-radius: 16px;
  padding: 16px 18px;
  box-shadow: 0 10px 24px rgba(19, 37, 71, 0.08);
}

.homev3-status-label {
  font-size: 0.83rem;
  font-weight: 700;
  color: #627895;
}

.homev3-status-value {
  margin-top: 0.28rem;
  font-size: 2.06rem;
  font-weight: 800;
  line-height: 1.05;
  color: #1d3452;
}

.homev3-status-meta {
  margin-top: 0.3rem;
  font-size: 0.87rem;
  color: #617995;
}

.homev3-principles {
  margin-top: 0.5rem;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.homev3-principle {
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid #cbdbef;
  border-radius: 12px;
  padding: 10px 12px;
}

.homev3-principle span {
  display: block;
  font-size: 0.91rem;
  font-weight: 740;
  color: #213a5a;
}

.homev3-principle small {
  display: block;
  margin-top: 0.18rem;
  font-size: 0.79rem;
  color: #637b97;
}

.homev3-section-title {
  margin-top: 0.75rem;
  margin-bottom: 0.3rem;
  font-size: 1.4rem;
  font-weight: 770;
  color: #1d3250;
}

.homev3-domain-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.homev3-domain-card {
  min-height: 230px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid #c6d7ee;
  border-radius: 14px;
  padding: 14px;
  box-shadow: 0 10px 20px rgba(19, 37, 71, 0.09);
}

.homev3-domain-card.is-cn {
  border-left: 5px solid #0b4a8b;
}

.homev3-domain-card.is-eu {
  border-left: 5px solid #0f766e;
}

.homev3-domain-card.is-us {
  border-left: 5px solid #1f7a46;
}

.homev3-domain-head {
  font-size: 1rem;
  font-weight: 740;
  color: #223c5b;
}

.homev3-domain-mods {
  margin-top: 0.32rem;
  font-size: 1.33rem;
  font-weight: 800;
  color: #1d3150;
}

.homev3-domain-desc {
  margin-top: 0.36rem;
  font-size: 0.88rem;
  line-height: 1.45;
  color: #5f7692;
}

.homev3-tag-row {
  margin-top: 0.52rem;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.homev3-tag {
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid #bfd1ea;
  background: #f8fbff;
  color: #36597f;
  font-size: 0.76rem;
  font-weight: 680;
}

.homev3-flow-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.homev3-flow-item {
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid #c6d7ee;
  border-radius: 13px;
  padding: 12px;
}

.homev3-flow-no {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  background: linear-gradient(120deg, #0b4a8b, #0f766e);
  color: #fff;
  font-size: 0.78rem;
  font-weight: 780;
}

.homev3-flow-title {
  margin-top: 0.4rem;
  font-size: 1.02rem;
  font-weight: 730;
  color: #233d5d;
}

.homev3-flow-desc {
  margin-top: 0.24rem;
  font-size: 0.89rem;
  line-height: 1.5;
  color: #607792;
}

.homev3-quick {
  min-height: 110px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid #c6d7ee;
  border-radius: 13px;
  padding: 12px 14px;
}

.homev3-quick.is-sidebar {
  border-left: 4px solid #7396c6;
}

.homev3-quick-title {
  font-size: 1.04rem;
  font-weight: 750;
  color: #1f3656;
}

.homev3-quick-desc {
  margin-top: 0.3rem;
  font-size: 0.88rem;
  line-height: 1.45;
  color: #617995;
}

@media (max-width: 900px) {
  .hero-title {
    font-size: 27px;
  }

  [data-testid="stAppViewContainer"] .main .block-container {
    padding-top: 0.8rem;
  }

  .ai4law-home-flow-item {
    grid-template-columns: 44px 1fr;
  }

  .ai4law-home-top-grid {
    grid-template-columns: 1fr;
  }

  .ai4law-home-stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .ai4law-home-domain-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .ai4law-home-track {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .homev3-top {
    grid-template-columns: 1fr;
  }

  .homev3-principles {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .homev3-domain-grid,
  .homev3-flow-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 780px) {
  .ai4law-home-stat-grid,
  .ai4law-home-domain-grid,
  .ai4law-home-track {
    grid-template-columns: 1fr;
  }

  .homev3-principles,
  .homev3-domain-grid,
  .homev3-flow-grid {
    grid-template-columns: 1fr;
  }
}
</style>
""",
        unsafe_allow_html=True,
    )
    _render_sidebar_navigation(active_domain=active_domain)


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
