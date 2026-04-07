from backend.modules.dpia.schema import DPIARequest
from backend.modules.dpia.service import DPIAService


def test_dpia_generate_report() -> None:
    service = DPIAService()
    payload = DPIARequest.model_validate(
        {
            "project_name": "EU用户行为分析系统",
            "processing_description": "收集用户行为日志并用于推荐优化",
            "purpose_and_necessity": "保障服务可用性并优化推荐准确率",
            "lawful_basis": "合法利益+合同履行",
            "risk_assessment": "存在画像偏差与过度处理风险",
            "mitigation_measures": "去标识化、最小化、访问控制、审计",
            "residual_risk": "中风险，可接受并持续监控",
            "attachments": [
                {
                    "file_role": "data_flow_diagram",
                    "file_name": "flow.pdf",
                    "file_format": "pdf",
                    "storage_uri": "storage://uploads/flow.pdf",
                }
            ],
        }
    )

    result = service.generate_report(payload)

    assert result.report_path.endswith("_dpia_report.docx")
    assert result.output_files["zip"].endswith("_dpia_output_bundle.zip")
    assert len(result.chapters) == 7
    assert result.risk_level == "MEDIUM"

