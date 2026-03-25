import streamlit as st

st.set_page_config(page_title="AI4Law v0", page_icon="A", layout="wide")

st.title("AI4Law v0 Demo")
st.markdown(
    """
本版本已落实模块：
1. 合规路径诊断（Diagnosis）
2. 安全评估报告生成（Assessment）
3. 认证/标准合同路径（SCC/PIPIA）

请从左侧页面进入对应模块。默认后端地址为 `http://127.0.0.1:8000`。
"""
)

st.info("启动顺序：先运行 FastAPI，再运行 Streamlit。")
