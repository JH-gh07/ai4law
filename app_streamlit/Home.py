import streamlit as st

from app_streamlit.theme import apply_theme, open_section, render_hero, render_kpi_card

st.set_page_config(page_title="AI4Law Frontend v0.2", page_icon="A", layout="wide")
apply_theme()

render_hero(
    "中国大陆→境外 合规服务",
    "基于大模型与法规知识库，完成路径诊断、报告生成与文档审查。",
    kicker="AI4Law v0.3",
)

col1, col2, col3 = st.columns(3)
with col1:
    render_kpi_card("已上线模块", "7", "2.2 / 2.3 / 3.2 / 3.3 / 3.4 / 4.1 / 4.2")
with col2:
    render_kpi_card("已支持报告输出", "7类", "assessment / pipia / bcr / dpia / tia / cn-flow / cpra")
with col3:
    render_kpi_card("后端地址", "127.0.0.1:8000", "/api/v0 + /api/v1")

open_section("法域科普", "面向跨境数据流动的监管框架概览。")
st.markdown(
    """
- 中国框架：安全评估、标准合同、个人信息保护认证。
- 欧盟框架：GDPR 下的跨境传输机制。
- 美国框架：州法与行业规则并存，需结合场景治理。
"""
)

open_section("中国大陆→境外 服务面板", "先做路径判断，再进入对应报告或审查流程。")
st.markdown(
    """
1. 合规路径诊断（动态问答）
2. 安全评估路径（表单 + 上传 + 报告）
3. 认证/标准合同路径（表单 + 上传 + 报告）
4. 通用服务（TIA/尽调/备忘录/整改清单）
5. 文档智能审查（上传 + 条款审查报告）
"""
)

open_section("快速入口")

if hasattr(st, "page_link"):
    st.page_link("pages/0_CN_Service_Panel.py", label="进入中国场景服务面板")
    st.page_link("pages/6_Report_Center.py", label="进入报告中心")
    st.page_link("pages/7_Knowledge_Center.py", label="进入知识库中心")
else:
    st.info("请从左侧侧边栏选择页面。")

st.info("启动顺序：先运行 FastAPI，再运行 Streamlit。")
