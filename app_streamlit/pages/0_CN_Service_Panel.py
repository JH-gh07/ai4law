import streamlit as st

from app_streamlit.theme import apply_theme, open_section, render_hero

apply_theme()
render_hero("中国大陆→境外 服务面板", "选择模块后进入可执行流程。", kicker="Jurisdiction CN")

cards = [
    ("1_Diagnosis", "模块1：合规路径诊断", "2分钟问答，输出建议路径与法律依据。"),
    ("2_Assessment", "模块2：安全评估路径", "生成风险自评估报告草案（docx/md）。"),
    ("3_SCC_PIPIA", "模块3：认证/标准合同路径", "生成 PIPIA 报告草案（docx/md）。"),
    ("4_General_Service", "模块4：通用服务", "生成 TIA/尽调/备忘录/整改清单。"),
    ("5_Document_Review", "模块5：文档智能审查", "审查合同或规则文本，输出问题清单与建议。"),
    ("7_Knowledge_Center", "知识库中心", "浏览法规与案例索引，验证报告引用来源链。"),
]

open_section("模块入口")
for file_key, title, desc in cards:
    with st.container(border=True):
        st.markdown(f"#### {title}")
        st.caption(desc)
        if hasattr(st, "page_link"):
            st.page_link(f"pages/{file_key}.py", label="进入模块")

st.info("说明：当前为 Streamlit 快速对齐版，重点验证流程闭环与可交付报告。")
