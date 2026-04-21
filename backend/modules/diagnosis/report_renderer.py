from datetime import datetime
import re
from html import escape
from pathlib import Path
from uuid import uuid4

from backend.common.render.artifacts import render_pdf_report
from backend.common.llm.client import LLMClient
from backend.common.render.report import safe_filename
from backend.modules.diagnosis.schema import DiagnosisAnswers, DiagnosisResult


_YES_NO_LABEL = {
    "yes": "是",
    "no": "否",
    "unknown": "待确认",
}

_PATH_LABEL = {
    "security_assessment": "安全评估路径",
    "scc_or_certification": "标准合同备案 / 认证路径",
    "exemption": "豁免情形",
}

_SCENARIO_LABEL = {
    "contract_performance": "履行合同/向消费者提供服务",
    "hr_management": "跨国公司内部人力资源管理",
    "emergency": "紧急情况保护自然人生命健康财产",
    "legal_duty": "履行法定职责或法定义务",
    "other": "其他商业目的",
}

_RECEIVER_LABEL = {
    "intra_group": "集团内部关联公司",
    "third_party": "独立第三方",
}

_CONCLUSION_LABEL = {
    "security_assessment": "安全评估",
    "scc_or_certification": "标准合同备案 / 个人信息保护认证",
    "exemption": "暂不触发出境申报义务",
}

_RISK_LABEL = {
    "HIGH": "HIGH",
    "MEDIUM": "MEDIUM",
    "LOW": "LOW",
}

_SCENARIO_SHORT = {
    "contract_performance": "用户服务",
    "hr_management": "集团内部管理",
    "emergency": "紧急情形",
    "legal_duty": "法定义务",
    "other": "其他",
}


def _format_answers_block(answers: DiagnosisAnswers) -> str:
    return "\n".join(
        [
            "- 是否 CIIO：{}".format(_YES_NO_LABEL.get(answers.q1_is_ciio.value, answers.q1_is_ciio.value)),
            "- 是否涉及重要数据出境：{}".format(
                _YES_NO_LABEL.get(answers.q2_has_important_data.value, answers.q2_has_important_data.value)
            ),
            f"- 个人信息主体规模：{answers.q3_pii_count:,} 人",
            f"- 敏感个人信息主体规模：{answers.q4_spi_count:,} 人",
            "- 不含个人信息且不涉及重要数据：{}".format(
                _YES_NO_LABEL.get(answers.q5_no_personal_info.value, answers.q5_no_personal_info.value)
            ),
            "- 出境场景：{}".format(
                _SCENARIO_LABEL.get(answers.q6_scenario.value, answers.q6_scenario.value)
            ),
            "- 境外接收方类型：{}".format(
                _RECEIVER_LABEL.get(answers.q7_receiver_type.value, answers.q7_receiver_type.value)
            ),
            f"- 出境目的：{answers.q8_purpose}",
        ]
    )


def _format_result_block(result: DiagnosisResult) -> str:
    path_cn = _PATH_LABEL.get(result.recommended_path, result.recommended_path)
    legal_basis = "\n".join(f"- {item}" for item in result.legal_basis)
    actions = "\n".join(f"- {item}" for item in result.action_items)
    uncertainty = "\n".join(f"- {item}" for item in result.uncertainty_notes)
    return "\n".join(
        [
            f"- 推荐路径：{path_cn}（`{result.recommended_path}`）",
            f"- 风险等级：{result.risk_level}",
            f"- 结论来源：{result.conclusion_source}",
            f"- 置信度：{result.confidence}",
            f"- 命中规则ID：{result.matched_rule_id or '无（AI推测）'}",
            f"- 判定说明：{result.rationale}",
            f"- 最终解释：{result.final_explanation or result.rationale}",
            "",
            "### 法律依据",
            legal_basis or "- （暂无）",
            "",
            "### 后续行动建议",
            actions or "- （暂无）",
            "",
            "### 不确定性提示",
            uncertainty or "- 无",
        ]
    )


def _format_json_appendix(answers: DiagnosisAnswers, result: DiagnosisResult) -> str:
    return "\n".join(
        [
            "### 企业回答 JSON",
            "```json",
            answers.model_dump_json(indent=2),
            "```",
            "",
            "### 诊断结果 JSON",
            "```json",
            result.model_dump_json(indent=2),
            "```",
        ]
    )


def _yn(value: str) -> str:
    mapping = {"yes": "是", "no": "否", "unknown": "不确定"}
    return mapping.get(value, value or "不确定")


def _pi_range(count: int) -> str:
    if count >= 1_000_000:
        return "≥100万"
    if count >= 100_000:
        return "10万-100万"
    if count > 0:
        return "<10万"
    return "不确定"


def _spi_range(count: int) -> str:
    if count >= 10_000:
        return "≥1万"
    if count > 0:
        return "<1万"
    return "不确定"


def _build_template_markdown(company_name: str, answers: DiagnosisAnswers, result: DiagnosisResult) -> str:
    diag_id = f"DX-{datetime.now().strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    jurisdiction = "中国大陆"
    scenario_label = _SCENARIO_LABEL.get(answers.q6_scenario.value, answers.q6_scenario.value)
    conclusion = _CONCLUSION_LABEL.get(result.recommended_path, "需进一步人工判断")
    if result.conclusion_source == "ai_inference" and result.confidence == "LOW":
        conclusion = "需进一步人工判断"
    compliance_necessity = "否" if result.recommended_path == "exemption" else "是"

    has_sensitive = "是" if answers.q4_spi_count > 0 or len(answers.m3_sensitive_info_types) > 0 else "否"
    cross_border = answers.m4_cross_border_transfer or ("yes" if answers.q8_purpose else "unknown")
    facts_block = [
        f"* **是否处理个人信息：** `{_yn(answers.m3_processes_personal_info or ('no' if answers.q5_no_personal_info.value == 'yes' else 'yes'))}`",
        f"* **是否涉及敏感个人信息：** `{has_sensitive}`",
        f"* **是否涉及重要数据：** `{_yn(answers.m3_processes_important_data or answers.q2_has_important_data.value)}`",
        f"* **是否存在跨境传输：** `{_yn(cross_border)}`",
        f"* **是否为 CIIO：** `{_yn(answers.q1_is_ciio.value)}`",
        f"* **普通个人信息出境规模：** `{_pi_range(answers.q3_pii_count)}`",
        f"* **敏感个人信息出境规模：** `{_spi_range(answers.q4_spi_count)}`",
        f"* **出境目的：** `{_SCENARIO_SHORT.get(answers.q6_scenario.value, '其他')}`",
    ]

    legal_basis_lines = [f"* `{item}`" for item in result.legal_basis[:3]] or ["* `[待补充]`"]
    rule_chain = [
        f"1. `{result.matched_rule_id or 'ai_inference'}`：`{result.rationale}`",
        f"2. `risk_level`：`根据CIIO/重要数据/规模阈值计算得到{_RISK_LABEL.get(result.risk_level, result.risk_level)}`",
        f"3. `conclusion_source`：`{result.conclusion_source}`",
    ]

    not_recommended = {
        "security_assessment": [
            ("标准合同备案/认证路径", "当前已触发更高优先级门槛，需先按安全评估路径处理。"),
            ("豁免路径", "存在强制触发因素，不符合豁免条件。"),
        ],
        "scc_or_certification": [
            ("安全评估路径", "当前未触发CIIO/重要数据/规模阈值等强制条件。"),
            ("豁免路径", "存在个人信息处理活动，且不满足明确豁免情形。"),
        ],
        "exemption": [
            ("安全评估路径", "未触发强制安全评估门槛。"),
            ("标准合同备案/认证路径", "当前已命中可适用豁免情形，优先按豁免留痕。"),
        ],
    }.get(result.recommended_path, [("安全评估路径", "待人工复核"), ("标准合同备案/认证路径", "待人工复核")])

    risk_points = [
        f"* `{item}`" for item in (
            result.uncertainty_notes[:3]
            if result.uncertainty_notes
            else ["存在字段不确定或口径待确认，建议复核后再提交。", "需核对重要数据识别口径。", "需核对出境规模统计口径。"]
        )
    ]
    manual_review = [
        "* `CIIO身份是否明确`",
        "* `重要数据识别是否经业务与法务双重确认`",
        "* `近12个月规模统计口径是否一致`",
    ]

    gaps_rows = [
        "| 项目 | 当前状态 | 对结论影响 | 建议动作 |",
        "| --- | --- | --- | --- |",
    ]
    gap_candidates = []
    if answers.q1_is_ciio.value == "unknown":
        gap_candidates.append(("CIIO身份", "不确定", "高", "由网安负责人/法务确认CIIO属性并留痕"))
    if answers.q2_has_important_data.value == "unknown":
        gap_candidates.append(("重要数据识别", "不确定", "高", "按行业主管目录补充识别说明"))
    if answers.q3_pii_count == 0:
        gap_candidates.append(("个人信息规模", "缺失/不确定", "中", "补充近12个月出境规模统计口径与数据"))
    if answers.m4_cross_border_transfer in ("", "unknown"):
        gap_candidates.append(("跨境传输事实", "不确定", "高", "确认是否存在境外存储/访问链路"))
    if not gap_candidates:
        gap_candidates.append(("关键字段完整性", "基本完整", "低", "继续补充证明材料并进入下一模块"))
    for item in gap_candidates[:3]:
        gaps_rows.append(f"| `{item[0]}` | `{item[1]}` | `{item[2]}` | `{item[3]}` |")

    next_modules = {
        "security_assessment": [
            ("安全评估路径模块", "生成《数据出境风险自评估报告》草案"),
            ("PIPIA 模块", "补充个人信息影响评估材料"),
            ("文档审查模块", "审查现有隐私政策/合同文本"),
        ],
        "scc_or_certification": [
            ("认证/标准合同路径模块", "生成《个人信息保护影响评估报告》草案"),
            ("文档审查模块", "审查标准合同、DPA与隐私政策"),
            ("任务空间材料中心", "沉淀备案/认证所需附件"),
        ],
        "exemption": [
            ("豁免留痕模块", "形成豁免适用论证与内部记录"),
            ("文档审查模块", "核查告知同意与权利保障条款"),
            ("风险复核模块", "定期复核是否仍满足豁免条件"),
        ],
    }.get(result.recommended_path, [
        ("人工复核模块", "由法务确认最终路径"),
        ("文档审查模块", "补齐文本证据"),
        ("材料中心", "完善关键信息字段"),
    ])

    ai_summary = result.final_explanation or result.rationale
    size_hint = answers.m1_company_size or "未填写"
    deadline_hint = answers.m2_deadline or "未填写"
    step1 = "完成关键字段补齐与口径统一（CIIO/重要数据/规模）"
    step2 = "形成数据清单、流转图与接收方清单"
    step3 = "按判定路径生成核心文档草案（自评估/PIPIA/合同）"
    step4 = "开展条款审查与风险整改闭环"
    step5 = "完成申报/备案/留痕与周期复核机制"
    if "紧急" in deadline_hint or "整改" in deadline_hint:
        step1 = "T+3天内完成关键字段补齐与管理层确认"
        step2 = "T+7天完成数据清单与出境链路证据包"
        step3 = "T+14天完成路径文档草案并并行法务复核"
    if "微型" in size_hint or "小型" in size_hint:
        step4 = "以最小必要整改集优先闭环（高风险条款优先）"
    elif "大型" in size_hint or "特大型" in size_hint or "超大型" in size_hint:
        step4 = "按业务线分批整改并建立统一治理台账"

    return "\n".join(
        [
            "# 合规路径诊断结果报告（模板）",
            "",
            "## 一、基本信息",
            "",
            f"**诊断编号：** `{diag_id}`",
            f"**诊断时间：** `{ts}`",
            f"**适用法域：** `{jurisdiction}`",
            f"**企业名称：** `{company_name}`",
            f"**业务场景：** `{answers.m1_industry or '未填写'} / {scenario_label}`",
            "**诊断方式：** `结构化问卷 + 规则判断 + AI 汇总说明`",
            "",
            "---",
            "",
            "## 二、诊断结论摘要",
            "",
            "### 1. 推荐合规路径",
            "",
            f"**结论：** `{conclusion}`",
            "",
            "### 1.1 合规必要性",
            "",
            f"**必要性：** `{compliance_necessity}`",
            "",
            "### 2. 结论置信度",
            "",
            f"**置信度：** `{result.confidence}`",
            "",
            "### 3. 总体风险等级",
            "",
            f"**风险等级：** `{_RISK_LABEL.get(result.risk_level, result.risk_level)}`",
            "",
            "### 4. 一句话总结",
            "",
            "**AI总结：**",
            f"`{ai_summary}`",
            "",
            "---",
            "",
            "## 三、关键判断依据",
            "",
            "### 1. 事实依据",
            "",
            "根据本次问卷，系统识别出的关键事实如下：",
            "",
            *facts_block,
            "",
            "### 2. 法律依据",
            "",
            "本次路径判断主要参考以下规则与法律依据：",
            "",
            *legal_basis_lines,
            "",
            "### 3. 规则触发链",
            "",
            "本次诊断命中的核心规则如下：",
            "",
            *rule_chain,
            "",
            "---",
            "",
            "## 四、路径判定说明",
            "",
            "### 情形说明",
            "",
            f"`系统综合判断认为，贵司当前业务场景更符合【{conclusion}】的适用条件，原因在于：`",
            "",
            f"* `{result.rationale}`",
            "* `关键判断基于CIIO/重要数据/规模阈值与场景豁免条件。`",
            "* `当前结论可用于下一模块材料准备与审查排期。`",
            "",
            "### 非适用路径排除说明",
            "",
            "`以下路径当前未被优先推荐，主要原因如下：`",
            "",
            f"* **未推荐路径A：** `{not_recommended[0][0]}：{not_recommended[0][1]}`",
            f"* **未推荐路径B：** `{not_recommended[1][0]}：{not_recommended[1][1]}`",
            "",
            "---",
            "",
            "## 五、核心风险提示",
            "",
            "### 1. 当前已识别风险",
            "",
            *risk_points,
            "",
            "### 2. 风险解释",
            "",
            "* **高风险事项：** `重要数据识别不清、规模接近门槛、CIIO身份不明。`",
            "* **中风险事项：** `接收方信息不完整、出境目的与授权机制描述不足。`",
            "* **低风险事项：** `已有制度和材料基础，但证据链仍需补强。`",
            "",
            "### 3. 需重点人工复核事项",
            "",
            *manual_review,
            "",
            "---",
            "",
            "## 六、缺口与待补充信息",
            "",
            "以下信息缺失或存在不确定性，可能影响路径判断准确性：",
            "",
            *gaps_rows,
            "",
            "---",
            "",
            "## 七、建议后续行动",
            "",
            "### 1. 推荐下一步",
            "",
            "根据本次诊断结果，建议优先进入以下模块：",
            "",
            "1. **`{}`**\n   目的：`{}`".format(next_modules[0][0], next_modules[0][1]),
            "",
            "2. **`{}`**\n   目的：`{}`".format(next_modules[1][0], next_modules[1][1]),
            "",
            "3. **`{}`**\n   目的：`{}`".format(next_modules[2][0], next_modules[2][1]),
            "",
            "### 2. 建议准备的材料",
            "",
            "* `[企业主体信息]`",
            "* `[数据清单 / 数据分类结果]`",
            "* `[接收方信息]`",
            "* `[现有隐私政策 / 标准合同 / DPA]`",
            "* `[安全措施与制度材料]`",
            "",
            "### 3. 优先级行动清单",
            "",
            "| 优先级 | 行动事项 | 目标 |",
            "| --- | --- | --- |",
            "| P1 | `[立即确认关键字段]` | `[确保路径判断准确]` |",
            "| P1 | `[补充必要材料]` | `[进入报告生成]` |",
            "| P2 | `[启动合同/政策审查]` | `[提前识别整改点]` |",
            "| P3 | `[完善制度与记录]` | `[提升申报与审查通过率]` |",
            "",
            "### 4. 定制化5步实施路径",
            "",
            f"1. `{step1}`",
            f"2. `{step2}`",
            f"3. `{step3}`",
            f"4. `{step4}`",
            f"5. `{step5}`",
            "",
            "---",
            "",
            "## 八、系统生成说明",
            "",
            "### 1. 结论性质",
            "",
            "`本报告为系统基于当前问卷答案自动生成的合规路径诊断结果，属于辅助判断结果，不构成正式法律意见。`",
            "",
            "### 2. 使用边界",
            "",
            "`当涉及重要数据识别、CIIO身份认定、规模统计口径不清、跨法域冲突等复杂情形时，本报告仅作为初筛和流程指引使用，最终结论应结合专业律师或法务人员复核。`",
            "",
            "### 3. 生成方式",
            "",
            "`本结果由结构化问卷、规则引擎和 AI 总结模块联合生成。规则引擎负责路径判断，AI 负责解释、归纳与结果汇总。`",
            "",
        ]
    )


class DiagnosisReportRenderer:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        if llm_client is None:
            from backend.core.settings import get_settings
            llm_client = LLMClient(get_settings())
        self.llm_client = llm_client

    def render(self, company_name: str, answers: DiagnosisAnswers, result: DiagnosisResult) -> dict[str, Path]:
        path_cn = _PATH_LABEL.get(result.recommended_path, result.recommended_path)
        if self.llm_client and self.llm_client.enabled:
            ai_summary = self.llm_client.chat(
                system="你是一名精通中国数据出境合规的资深律师，用专业中文简洁总结诊断结论。",
                user=(
                    f"企业：{company_name}\n"
                    f"推荐路径：{path_cn}（{result.recommended_path}）\n"
                    f"风险等级：{result.risk_level}\n"
                    f"判定说明：{result.rationale}\n\n"
                    "请用2-3句话概括本次合规路径诊断的核心结论和关键注意事项。"
                ),
                temperature=0.2,
                max_tokens=300,
            )
        else:
            ai_summary = "（AI摘要：LLM未配置，此处为占位内容）"
        template_markdown = _build_template_markdown(company_name, answers, result)
        sections = [
            ("企业回答", _format_answers_block(answers)),
            ("诊断结果", _format_result_block(result)),
            ("AI 摘要", ai_summary),
            ("模板化报告", template_markdown),
            ("机器可读附录", _format_json_appendix(answers, result)),
        ]

        safe_company = safe_filename(company_name)
        output_dir = Path("outputs/diagnosis")
        output_dir.mkdir(parents=True, exist_ok=True)

        html_output = output_dir / f"{safe_company}_diagnosis_report.html"
        pdf_output = output_dir / f"{safe_company}_diagnosis_report.pdf"

        html_output.write_text(self._build_html_doc("合规路径诊断报告", sections), encoding="utf-8")
        render_pdf_report(pdf_output, "合规路径诊断报告", sections)
        return {"html": html_output, "pdf": pdf_output}

    @staticmethod
    def _build_html_doc(title: str, sections: list[tuple[str, str]]) -> str:
        def _inline(text: str) -> str:
            safe = escape(text)
            safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)
            safe = re.sub(r"`([^`]+)`", r"<code>\1</code>", safe)
            return safe

        def _markdown_to_html(content: str) -> str:
            lines = (content or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
            html_parts: list[str] = []
            in_ul = False
            in_ol = False
            in_table = False
            table_header_rendered = False

            def close_lists() -> None:
                nonlocal in_ul, in_ol
                if in_ul:
                    html_parts.append("</ul>")
                    in_ul = False
                if in_ol:
                    html_parts.append("</ol>")
                    in_ol = False

            def close_table() -> None:
                nonlocal in_table, table_header_rendered
                if in_table:
                    html_parts.append("</tbody></table>")
                    in_table = False
                    table_header_rendered = False

            def is_table_row(text: str) -> bool:
                return "|" in text and text.count("|") >= 2

            for idx, raw in enumerate(lines):
                line = raw.strip()
                if not line:
                    close_lists()
                    close_table()
                    continue

                if line == "---":
                    close_lists()
                    close_table()
                    html_parts.append("<hr />")
                    continue

                if line.startswith("### "):
                    close_lists()
                    close_table()
                    html_parts.append(f"<h3>{_inline(line[4:])}</h3>")
                    continue
                if line.startswith("## "):
                    close_lists()
                    close_table()
                    html_parts.append(f"<h2>{_inline(line[3:])}</h2>")
                    continue
                if line.startswith("# "):
                    close_lists()
                    close_table()
                    html_parts.append(f"<h1>{_inline(line[2:])}</h1>")
                    continue

                ul_match = re.match(r"^-\s+(.+)$", line)
                if ul_match:
                    close_table()
                    if in_ol:
                        html_parts.append("</ol>")
                        in_ol = False
                    if not in_ul:
                        html_parts.append("<ul>")
                        in_ul = True
                    html_parts.append(f"<li>{_inline(ul_match.group(1))}</li>")
                    continue

                ol_match = re.match(r"^\d+\.\s+(.+)$", line)
                if ol_match:
                    close_table()
                    if in_ul:
                        html_parts.append("</ul>")
                        in_ul = False
                    if not in_ol:
                        html_parts.append("<ol>")
                        in_ol = True
                    html_parts.append(f"<li>{_inline(ol_match.group(1))}</li>")
                    continue

                if is_table_row(line):
                    close_lists()
                    cells = [cell.strip() for cell in line.strip("|").split("|")]
                    if not in_table:
                        html_parts.append("<table><thead>")
                        html_parts.append("<tr>" + "".join(f"<th>{_inline(cell)}</th>" for cell in cells) + "</tr>")
                        html_parts.append("</thead><tbody>")
                        in_table = True
                        table_header_rendered = True
                        continue
                    # markdown 表头分隔行，如 | --- | --- |
                    if table_header_rendered and all(re.fullmatch(r":?-{3,}:?", cell or "") for cell in cells):
                        continue
                    html_parts.append("<tr>" + "".join(f"<td>{_inline(cell)}</td>" for cell in cells) + "</tr>")
                    continue

                close_lists()
                close_table()
                html_parts.append(f"<p>{_inline(line)}</p>")

            close_lists()
            close_table()
            return "\n".join(html_parts)

        blocks: list[str] = []
        for header, content in sections:
            blocks.append(
                "<section>"
                f"<h2>{escape(header)}</h2>"
                f"<div class=\"doc-content\">{_markdown_to_html(content or '')}</div>"
                "</section>"
            )
        body = "\n".join(blocks)
        return (
            "<!doctype html>"
            "<html lang=\"zh-CN\">"
            "<head>"
            "<meta charset=\"utf-8\" />"
            f"<title>{escape(title)}</title>"
            "<style>"
            "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:960px;margin:28px auto;padding:0 16px;line-height:1.6;}"
            "h1{font-size:28px;margin:0 0 18px 0;}"
            "h2{font-size:20px;margin:22px 0 10px 0;}"
            ".doc-content{background:#f8fbff;border:1px solid #e5e7eb;border-radius:8px;padding:12px;}"
            ".doc-content h1,.doc-content h2,.doc-content h3{margin:14px 0 8px;line-height:1.35;}"
            ".doc-content h1{font-size:22px;}"
            ".doc-content h2{font-size:18px;}"
            ".doc-content h3{font-size:16px;}"
            ".doc-content p{margin:8px 0;}"
            ".doc-content ul,.doc-content ol{margin:8px 0 10px;padding-left:20px;}"
            ".doc-content li{margin:4px 0;}"
            ".doc-content hr{border:0;border-top:1px solid #d0d7de;margin:12px 0;}"
            ".doc-content code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;background:#ecf3ff;border-radius:4px;padding:1px 4px;}"
            ".doc-content table{width:100%;border-collapse:collapse;margin:10px 0;}"
            ".doc-content th,.doc-content td{border:1px solid #d0d7de;padding:6px 8px;text-align:left;vertical-align:top;}"
            ".doc-content th{background:#eef5ff;}"
            "</style>"
            "</head>"
            "<body>"
            f"<h1>{escape(title)}</h1>"
            f"{body}"
            "</body>"
            "</html>"
        )
