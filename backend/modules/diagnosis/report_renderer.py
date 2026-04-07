from pathlib import Path

from backend.common.llm.client import LLMClient
from backend.common.render.report import render_markdown_report
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
    return "\n".join(
        [
            f"- 推荐路径：{path_cn}（`{result.recommended_path}`）",
            f"- 风险等级：{result.risk_level}",
            f"- 判定说明：{result.rationale}",
            "",
            "### 法律依据",
            legal_basis or "- （暂无）",
            "",
            "### 后续行动建议",
            actions or "- （暂无）",
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


class DiagnosisReportRenderer:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        if llm_client is None:
            from backend.core.settings import get_settings
            llm_client = LLMClient(get_settings())
        self.llm_client = llm_client

    def render(self, company_name: str, answers: DiagnosisAnswers, result: DiagnosisResult) -> Path:
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
        sections = [
            ("企业回答", _format_answers_block(answers)),
            ("诊断结果", _format_result_block(result)),
            ("AI 摘要", ai_summary),
            ("机器可读附录", _format_json_appendix(answers, result)),
        ]
        output = Path("outputs/diagnosis") / f"{company_name}_diagnosis_report.md"
        return render_markdown_report(output, "合规路径诊断报告", sections)
