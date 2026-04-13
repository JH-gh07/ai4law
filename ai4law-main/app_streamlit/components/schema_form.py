from pathlib import Path

import streamlit as st


@st.cache_data(show_spinner=False)
def load_schema(path: str) -> dict:
    import json

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _field_key(form_key: str, field_name: str) -> str:
    return f"{form_key}__{field_name}"


def _init_defaults(form_key: str, schema: dict) -> None:
    for step in schema.get("steps", []):
        for field in step.get("fields", []):
            key = _field_key(form_key, field["name"])
            if key not in st.session_state:
                st.session_state[key] = field.get("default")


def _render_field(form_key: str, field: dict) -> None:
    key = _field_key(form_key, field["name"])
    field_type = field["type"]
    label = field["label"]
    help_text = field.get("help", None)

    if field_type == "text":
        st.text_input(label, key=key, help=help_text)
        return
    if field_type == "textarea":
        st.text_area(label, key=key, help=help_text)
        return
    if field_type == "number":
        st.number_input(
            label,
            key=key,
            min_value=field.get("min", 0),
            max_value=field.get("max", None),
            step=field.get("step", 1),
            help=help_text,
        )
        return
    if field_type == "checkbox":
        st.checkbox(label, key=key, help=help_text)
        return
    if field_type == "select":
        options = field.get("options", [])
        default = st.session_state.get(key)
        if default in options:
            index = options.index(default)
        else:
            index = 0
        st.selectbox(label, options=options, index=index, key=key, help=help_text)
        return

    raise ValueError(f"Unsupported field type: {field_type}")


def _get_step_state_key(form_key: str) -> str:
    return f"{form_key}__step"


def render_schema_multistep_form(form_key: str, schema_path: str) -> tuple[bool, dict]:
    schema = load_schema(schema_path)
    steps = schema.get("steps", [])
    if not steps:
        st.error("Schema has no steps.")
        return False, {}

    _init_defaults(form_key, schema)

    step_state_key = _get_step_state_key(form_key)
    if step_state_key not in st.session_state:
        st.session_state[step_state_key] = 0

    current_step = int(st.session_state[step_state_key])
    total = len(steps)

    with st.sidebar:
        st.subheader("填写进度")
        st.progress((current_step + 1) / total)
        for idx, step in enumerate(steps):
            prefix = "->" if idx == current_step else "  "
            st.caption(f"{prefix} Step {idx + 1}: {step['title']}")

    step = steps[current_step]
    st.markdown(f"### Step {current_step + 1}/{total}: {step['title']}")

    for field in step.get("fields", []):
        _render_field(form_key, field)

    col_left, col_mid, _ = st.columns([1, 1, 2])
    submitted = False
    with col_left:
        if st.button("上一步", disabled=current_step == 0, key=f"{form_key}_prev"):
            st.session_state[step_state_key] = max(0, current_step - 1)
            st.rerun()
    with col_mid:
        if current_step < total - 1:
            if st.button("下一步", key=f"{form_key}_next"):
                st.session_state[step_state_key] = min(total - 1, current_step + 1)
                st.rerun()
        else:
            submitted = st.button("提交生成", type="primary", key=f"{form_key}_submit")

    values: dict = {}
    for step_config in steps:
        for field in step_config.get("fields", []):
            key = _field_key(form_key, field["name"])
            values[field["name"]] = st.session_state.get(key)

    return submitted, values
