from pathlib import Path

import streamlit as st


_ALLOWED_SUFFIXES = {".pdf", ".docx", ".txt", ".md", ".csv", ".json", ".xlsx", ".png", ".jpg"}


def save_uploaded_files(uploaded_files: list, module: str) -> list[str]:
    output_dir = Path("storage/uploads") / module
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    unsupported: list[str] = []

    for file in uploaded_files:
        suffix = Path(file.name).suffix.lower()
        if suffix not in _ALLOWED_SUFFIXES:
            unsupported.append(file.name)
            continue

        target = output_dir / file.name
        target.write_bytes(file.getbuffer())
        paths.append(str(target))

    if unsupported:
        st.error(f"存在不支持格式文件，已跳过：{', '.join(unsupported)}")

    return paths


def render_file_uploader(module: str, label: str = "上传材料") -> list[str]:
    files = st.file_uploader(
        label,
        accept_multiple_files=True,
        type=[s[1:] for s in sorted(_ALLOWED_SUFFIXES)],
        help="支持 pdf/docx/txt/md/csv/json/xlsx/png/jpg",
    )
    if not files:
        return []

    saved_paths = save_uploaded_files(files, module=module)
    if saved_paths:
        rows = []
        for path in saved_paths:
            p = Path(path)
            rows.append(
                {
                    "文件名": p.name,
                    "格式": p.suffix.lower().lstrip("."),
                    "大小(KB)": round((p.stat().st_size or 0) / 1024, 2),
                    "本地路径": str(p),
                }
            )

        st.success(f"已保存 {len(saved_paths)} 个文件")
        st.dataframe(rows, use_container_width=True, hide_index=True)

    return saved_paths
