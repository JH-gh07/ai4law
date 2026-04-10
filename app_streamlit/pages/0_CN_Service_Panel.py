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

apply_theme("home")
render_hero("模块总览（已并入左侧导航）", "旧版模块总览页面已停用，请在左侧“模块总览”展开法域并进入三级功能。", kicker="Navigator Update")

st.info("当前导航结构：一级（首页/模块总览/报告中心/知识库中心）-> 二级（法域）-> 三级（具体模块）。")

# LEGACY NOTE:
# 旧版模块总览页面（大卡片 + 子功能目录 + 公共能力）已按需求停用，不再在前端展示，也不再作为主导航入口生效。
# 如需回看旧实现，请使用 Git 历史版本，不在运行时加载旧版逻辑。
