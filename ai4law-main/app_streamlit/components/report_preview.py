import json
import re
from pathlib import Path
from typing import Iterable

import streamlit as st

from app_streamlit.components.legal_basis import build_legal_basis_models, render_legal_basis_summary
from app_streamlit.components.risk_badge import render_risk_badge

_YES_NO_LABEL = {"yes": "是", "no": "否", "unknown": "待确认"}
_PATH_LABEL = {
    "security_assessment": "安全评估路径",
    "scc_or_certification": "标准合同备案 / 认证路径",
}
_RATIONALE_I18N = {
    "Threshold not reached for mandatory security assessment.": "未触发强制安全评估门槛，可走标准合同备案或认证路径。",
    "CIIO must apply for security assessment": "企业被识别为关键信息基础设施运营者，应优先走安全评估路径。",
    "Important data export must apply for security assessment": "涉及重要数据出境，按监管要求应优先走安全评估路径。",
    "PII count >= 1,000,000 must apply for security assessment": "个人信息处理规模达到法定门槛，应优先走安全评估路径。",
    "Sensitive PII count >= 10,000 must apply for security assessment": "敏感个人信息处理规模达到法定门槛，应优先走安全评估路径。",
}
_ACTION_I18N = {
    "Choose SCC filing or certification route.": "在标准合同备案与个人信息保护认证之间确定实施路径。",
    "Generate PIPIA report and contract appendix.": "生成 PIPIA 报告及标准合同配套附件。",
    "Prepare provincial filing package.": "准备省级网信备案/留档材料并完成内部审批。",
    "Prepare data export inventory and processing map.": "整理数据出境清单与处理活动映射。",
    "Generate Data Export Security Assessment report.": "生成《数据出境风险自评估报告》草案并补齐附件。",
    "Submit assessment package to CAC.": "按属地网信要求提交安全评估申报材料。",
}


def _mime_by_suffix(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if suffix == ".md":
        return "text/markdown"
    if suffix == ".pdf":
        return "application/pdf"
    if suffix == ".xlsx":
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if suffix == ".zip":
        return "application/zip"
    if suffix == ".json":
        return "application/json"
    if suffix == ".csv":
        return "text/csv"
    return "application/octet-stream"


def render_chapter_preview(
    chapters: Iterable[dict],
    sources: list[dict[str, str]] | None = None,
) -> None:
    st.subheader("报告预览")
    chapter_list = list(chapters)
    st.caption(f"共 {len(chapter_list)} 章")

    for chapter_idx, chapter in enumerate(chapter_list, start=1):
        title = f"第{chapter.get('chapter_no', '?')}章：{chapter.get('title', '未命名章节')}"
        with st.expander(title, expanded=False):
            risk_level = str(chapter.get("risk_level", "LOW"))
            render_risk_badge(risk_level)
            st.write(chapter.get("content", ""))

            citations = chapter.get("citations", [])
            if citations:
                basis_models = build_legal_basis_models(citations, sources=sources)
                chapter_no = chapter.get("chapter_no", "x")
                render_legal_basis_summary(
                    basis_models,
                    title="引用来源摘要（首屏可见）",
                    key_prefix=f"chapter_{chapter_idx}_{chapter_no}_basis",
                )
                with st.expander("查看引用详情（来源机构/日期/快照）", expanded=False):
                    for idx, item in enumerate(basis_models, start=1):
                        st.markdown(f"**[{idx}] 引用条目**：{item.get('citation', '-')}")
                        st.write(f"匹配状态：{item.get('status', '-')}")
                        st.write(f"匹配标题：{item.get('summary_title', '-')}")
                        st.write(f"来源机构：{item.get('source_org', '-')}")
                        st.write(f"发布日期：{item.get('publish_date', '-')}")
                        url = item.get("url", "")
                        if url:
                            st.link_button(f"打开来源链接（章节{chapter_no}-{idx}）", url)
                        snapshot = item.get("snapshot_path", "")
                        if snapshot:
                            st.caption(f"本地快照：{snapshot}")
                        st.divider()


def render_report_download(output_files: dict[str, str]) -> None:
    st.subheader("报告下载")
    for label, path in output_files.items():
        file_path = Path(path)
        if not file_path.exists():
            st.error(f"{label} 文件不存在：{path}")
            continue

        mime = _mime_by_suffix(file_path)
        with open(file_path, "rb") as fp:
            st.download_button(
                label=f"下载 {label} ({file_path.name})",
                data=fp.read(),
                file_name=file_path.name,
                mime=mime,
                key=f"download_{label}_{file_path.name}",
            )


def render_markdown_file(path: str) -> None:
    file_path = Path(path)
    if not file_path.exists():
        st.error(f"文件不存在：{path}")
        return
    raw = file_path.read_text(encoding="utf-8", errors="ignore")
    if file_path.name.endswith("_diagnosis_report.md"):
        transformed = _convert_legacy_diagnosis_markdown(raw)
        if transformed is not None:
            st.markdown(transformed)
            return
    st.markdown(raw)


def _extract_section(markdown_text: str, header: str) -> str | None:
    pattern = rf"##\s+{re.escape(header)}\s*\n(.*?)(?=\n##\s+|\Z)"
    match = re.search(pattern, markdown_text, flags=re.DOTALL)
    if not match:
        return None
    return match.group(1).strip()


def _convert_legacy_diagnosis_markdown(raw: str) -> str | None:
    answers_block = _extract_section(raw, "企业回答")
    result_block = _extract_section(raw, "诊断结果")
    summary_block = _extract_section(raw, "AI 摘要") or ""
    if not answers_block or not result_block:
        return None

    if not answers_block.startswith("{") or not result_block.startswith("{"):
        return None

    try:
        answers = json.loads(answers_block)
        result = json.loads(result_block)
    except json.JSONDecodeError:
        return None

    rationale = str(result.get("rationale", "")).strip()
    rationale_cn = _RATIONALE_I18N.get(rationale, rationale)
    actions = [_ACTION_I18N.get(str(item).strip(), str(item).strip()) for item in result.get("action_items", [])]
    legal_basis = result.get("legal_basis", [])
    recommended_path = str(result.get("recommended_path", "")).strip()
    recommended_path_cn = _PATH_LABEL.get(recommended_path, recommended_path)

    lines = [
        "# 合规路径诊断报告",
        "",
        "## 企业回答",
        f"- 是否 CIIO：{_YES_NO_LABEL.get(str(answers.get('q1_is_ciio', '')).strip(), answers.get('q1_is_ciio', '-'))}",
        f"- 是否涉及重要数据出境：{_YES_NO_LABEL.get(str(answers.get('q2_has_important_data', '')).strip(), answers.get('q2_has_important_data', '-'))}",
        f"- 个人信息主体规模：{answers.get('q3_pii_count', '-')} 人",
        f"- 敏感个人信息主体规模：{answers.get('q4_spi_count', '-')} 人",
        f"- 出境目的：{answers.get('q5_purpose', '-')}",
        "",
        "## 诊断结果",
        f"- 推荐路径：{recommended_path_cn}（`{recommended_path}`）",
        f"- 风险等级：{result.get('risk_level', '-')}",
        f"- 判定说明：{rationale_cn}",
        "",
        "### 法律依据",
    ]
    if legal_basis:
        lines.extend([f"- {item}" for item in legal_basis])
    else:
        lines.append("- （暂无）")

    lines.extend(["", "### 后续行动建议"])
    if actions:
        lines.extend([f"- {item}" for item in actions])
    else:
        lines.append("- （暂无）")

    if summary_block:
        lines.extend(["", "## AI 摘要", summary_block])

    lines.extend(
        [
            "",
            "## 机器可读附录",
            "### 企业回答 JSON",
            "```json",
            json.dumps(answers, ensure_ascii=False, indent=2),
            "```",
            "",
            "### 诊断结果 JSON",
            "```json",
            json.dumps({**result, "rationale": rationale_cn, "action_items": actions}, ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    )
    return "\n".join(lines)
