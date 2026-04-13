from dataclasses import dataclass
from pathlib import Path

from backend.common.render.report import render_docx_report, render_markdown_report
from backend.common.storage.file_parser import FileParser


@dataclass
class LocalReportResult:
    report_path: str
    output_files: dict[str, str]
    summary: dict


def generate_general_report(payload: dict) -> LocalReportResult:
    company_name = payload["company_name"]
    doc_type = payload["doc_type"]

    sections = [
        (
            "业务场景摘要",
            (
                f"企业：{company_name}\n"
                f"文书类型：{doc_type}\n"
                f"目的：{payload.get('transfer_purpose', '')}\n"
                f"接收方国家：{payload.get('receiver_country', '')}"
            ),
        ),
        (
            "主要风险",
            "- 数据最小化边界需进一步论证\n- 跨境传输必要性证明材料不充分\n- 接收方保障能力需持续评估",
        ),
        (
            "整改建议",
            "- 建立出境清单按季度复核\n- 补齐 SCC/认证证据链\n- 对高风险字段增加加密与访问控制",
        ),
    ]

    stem = f"{company_name}_{doc_type}_report"
    md_path = Path("outputs/general") / f"{stem}.md"
    docx_path = Path("outputs/general") / f"{stem}.docx"

    render_markdown_report(md_path, f"{company_name} 通用服务报告（{doc_type}）", sections)
    render_docx_report(docx_path, f"{company_name} 通用服务报告（{doc_type}）", sections)

    return LocalReportResult(
        report_path=str(docx_path),
        output_files={"markdown": str(md_path), "docx": str(docx_path)},
        summary={"risk_level": "MEDIUM", "sections": len(sections)},
    )


def generate_review_report(company_name: str, uploaded_paths: list[str], notes: str) -> LocalReportResult:
    parser = FileParser()
    content_blocks: list[str] = []

    for path in uploaded_paths:
        try:
            text = parser.parse_text(path)
        except Exception:
            text = ""
        if text.strip():
            content_blocks.append(text[:3000])

    corpus = "\n".join(content_blocks + [notes]).lower()

    checks = [
        ("跨境传输目的与必要性", ["目的", "必要", "跨境"]),
        ("接收方义务与安全措施", ["接收方", "安全", "措施"]),
        ("个人权利与救济路径", ["权利", "申诉", "救济"]),
        ("删除与保留期限", ["删除", "保存期限", "保留"]),
    ]

    issues: list[str] = []
    for check_name, keywords in checks:
        if not any(word in corpus for word in keywords):
            issues.append(f"{check_name}：可能缺失或表述不足")

    risk_level = "HIGH" if len(issues) >= 3 else "MEDIUM" if issues else "LOW"

    sections = [
        ("审查范围", f"企业：{company_name}\n文件数量：{len(uploaded_paths)}"),
        (
            "发现问题",
            "\n".join([f"- {item}" for item in issues]) if issues else "- 未发现明显缺失项",
        ),
        (
            "法规依据",
            "- 《个人信息保护法》第38条\n- 《个人信息保护法》第39条\n- 《个人信息出境标准合同办法》",
        ),
        (
            "修订建议",
            "- 增加跨境目的与必要性说明\n- 明确接收方义务与违约责任\n- 增加个人权利响应机制",
        ),
    ]

    stem = f"{company_name}_document_review_report"
    md_path = Path("outputs/review") / f"{stem}.md"
    docx_path = Path("outputs/review") / f"{stem}.docx"

    render_markdown_report(md_path, f"{company_name} 文档合规审查报告", sections)
    render_docx_report(docx_path, f"{company_name} 文档合规审查报告", sections)

    return LocalReportResult(
        report_path=str(docx_path),
        output_files={"markdown": str(md_path), "docx": str(docx_path)},
        summary={"risk_level": risk_level, "issue_count": len(issues), "issues": issues},
    )
