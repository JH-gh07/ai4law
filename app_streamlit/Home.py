import sys
from pathlib import Path

for _parent in Path(__file__).resolve().parents:
    if (_parent / "app_streamlit").exists():
        _root = str(_parent)
        if _root not in sys.path:
            sys.path.insert(0, _root)
        break

import streamlit as st

from app_streamlit.theme import apply_theme, render_hero

st.set_page_config(page_title="AI4Law Frontend v2", page_icon="A", layout="wide")
apply_theme("home")

render_hero("AI4Law v2 合规控制台", "面向数据跨境合规的规则驱动编排平台。", kicker="Compliance Control Room")

st.markdown(
    """
<div class="homev3-top">
  <div class="homev3-intro">
    <div class="homev3-intro-kicker">AI4LAW V2 / REGULATORY OPS</div>
    <div class="homev3-intro-title">规则先行 + RAG 依据链 + 文档交付闭环</div>
    <div class="homev3-intro-desc">
      平台以“路径判定 -> 材料收集 -> 报告生成 -> 引用回溯”为主线，覆盖中国大陆、欧盟、美国三法域跨境合规场景。
      左侧导航为三级结构：一级（首页/模块总览/报告中心/知识库中心） -> 二级（法域） -> 三级（功能模块）。
    </div>
  </div>
  <div class="homev3-status">
    <div class="homev3-status-label">运行态</div>
    <div class="homev3-status-value">联调中</div>
    <div class="homev3-status-meta">FastAPI: 127.0.0.1:8000</div>
    <div class="homev3-status-meta">模块: 11 | 输出: 11 类文档</div>
    <div class="homev3-status-meta">输出格式: md/docx/pdf/xlsx/zip</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="homev3-principles">
  <div class="homev3-principle"><span>规则先行</span><small>路径判定确定性</small></div>
  <div class="homev3-principle"><span>引用可追溯</span><small>法规来源可回查</small></div>
  <div class="homev3-principle"><span>结构化输出</span><small>JSON + 模板渲染</small></div>
  <div class="homev3-principle"><span>复核门控</span><small>风险分级与人工介入</small></div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="homev3-section-title">法域模块矩阵</div>', unsafe_allow_html=True)
st.markdown(
    """
<div class="homev3-domain-grid">
  <div class="homev3-domain-card is-cn">
    <div class="homev3-domain-head">中国大陆 -> 境外</div>
    <div class="homev3-domain-mods">2.1 / 2.2 / 2.3 / 2.4 / 2.5</div>
    <div class="homev3-domain-desc">路径诊断、安全评估、PIPIA、通用服务、文档审查</div>
    <div class="homev3-tag-row">
      <span class="homev3-tag">2.1 路径诊断</span>
      <span class="homev3-tag">2.2 安全评估</span>
      <span class="homev3-tag">2.3 PIPIA</span>
      <span class="homev3-tag">2.4 通用服务</span>
      <span class="homev3-tag">2.5 文档审查</span>
    </div>
  </div>
  <div class="homev3-domain-card is-eu">
    <div class="homev3-domain-head">欧盟 -> 境外</div>
    <div class="homev3-domain-mods">3.1 / 3.2 / 3.3 / 3.4</div>
    <div class="homev3-domain-desc">SCC/BCR 审查与 DPIA/TIA 草案生成</div>
    <div class="homev3-tag-row">
      <span class="homev3-tag">3.1 SCC</span>
      <span class="homev3-tag">3.2 BCR</span>
      <span class="homev3-tag">3.3 DPIA</span>
      <span class="homev3-tag">3.4 TIA</span>
    </div>
  </div>
  <div class="homev3-domain-card is-us">
    <div class="homev3-domain-head">美国 -> 境外</div>
    <div class="homev3-domain-mods">4.1 / 4.2</div>
    <div class="homev3-domain-desc">对华数据流动合规与 CPRA 全景治理</div>
    <div class="homev3-tag-row">
      <span class="homev3-tag">4.1 对华流动</span>
      <span class="homev3-tag">4.2 CPRA 全景</span>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="homev3-section-title">执行链路</div>
<div class="homev3-flow-grid">
  <div class="homev3-flow-item">
    <div class="homev3-flow-no">01</div>
    <div class="homev3-flow-title">模块入口</div>
    <div class="homev3-flow-desc">左侧展开「模块总览」，按法域进入子功能。</div>
  </div>
  <div class="homev3-flow-item">
    <div class="homev3-flow-no">02</div>
    <div class="homev3-flow-title">材料与字段</div>
    <div class="homev3-flow-desc">填报结构化字段并上传附件，系统执行基础校验。</div>
  </div>
  <div class="homev3-flow-item">
    <div class="homev3-flow-no">03</div>
    <div class="homev3-flow-title">报告交付</div>
    <div class="homev3-flow-desc">生成报告并在报告中心下载，知识库中心回溯依据。</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="homev3-section-title">快捷入口</div>', unsafe_allow_html=True)
if hasattr(st, "page_link"):
    st.markdown(
        """
<div class="homev3-quick is-sidebar">
  <div class="homev3-quick-title">模块总览</div>
  <div class="homev3-quick-desc">模块总览已并入左侧导航，不再单独页面跳转。</div>
</div>
""",
        unsafe_allow_html=True,
    )

    q2, q3 = st.columns(2, gap="medium")
    with q2:
        st.markdown(
            """
<div class="homev3-quick">
  <div class="homev3-quick-title">报告中心</div>
  <div class="homev3-quick-desc">集中查看各模块交付文档并统一下载。</div>
</div>
""",
            unsafe_allow_html=True,
        )
        st.page_link("pages/6_Report_Center.py", label="进入报告中心")
    with q3:
        st.markdown(
            """
<div class="homev3-quick">
  <div class="homev3-quick-title">知识库中心</div>
  <div class="homev3-quick-desc">浏览法规与案例来源，验证引用可追溯性。</div>
</div>
""",
            unsafe_allow_html=True,
        )
        st.page_link("pages/7_Knowledge_Center.py", label="进入知识库中心")
else:
    st.info("请从左侧导航进入各模块。")

st.caption("启动顺序：先运行 FastAPI，再运行 Streamlit。")
