from pathlib import Path

from backend.common.llm.adapter import LLMAdapter
from backend.common.render.report import render_markdown_report
from backend.modules.diagnosis.schema import DiagnosisAnswers, DiagnosisResult


class DiagnosisReportRenderer:
    def __init__(self) -> None:
        self.llm = LLMAdapter()

    def render(self, company_name: str, answers: DiagnosisAnswers, result: DiagnosisResult) -> Path:
        summary = self.llm.summarize(
            title="诊断结论摘要",
            bullet_points=[
                f"企业：{company_name}",
                f"推荐路径：{result.recommended_path}",
                f"风险等级：{result.risk_level}",
                f"出境目的：{answers.q5_purpose}",
            ],
        )
        sections = [
            ("企业回答", answers.model_dump_json(indent=2)),
            ("诊断结果", result.model_dump_json(indent=2)),
            ("AI 摘要", summary.text),
        ]
        output = Path("outputs/diagnosis") / f"{company_name}_diagnosis_report.md"
        return render_markdown_report(output, "合规路径诊断报告", sections)
