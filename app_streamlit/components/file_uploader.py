from pathlib import Path

import streamlit as st


_ALLOWED_SUFFIXES = {".pdf", ".docx", ".txt", ".md", ".csv", ".json"}


def save_uploaded_files(uploaded_files: list, module: str) -> list[str]:
    output_dir = Path("storage/uploads") / module
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []

    for file in uploaded_files:
        suffix = Path(file.name).suffix.lower()
        if suffix not in _ALLOWED_SUFFIXES:
            st.warning(f"跳过不支持文件：{file.name}")
            continue
        target = output_dir / file.name
        target.write_bytes(file.getbuffer())
        paths.append(str(target))

    return paths


def render_file_uploader(module: str, label: str = "上传材料") -> list[str]:
    files = st.file_uploader(
        label,
        accept_multiple_files=True,
        type=[s[1:] for s in sorted(_ALLOWED_SUFFIXES)],
        help="支持 pdf/docx/txt/md/csv/json",
    )
    if not files:
        return []

    saved_paths = save_uploaded_files(files, module=module)
    if saved_paths:
        st.caption("已保存文件")
        for path in saved_paths:
            st.code(path)
    return saved_paths
