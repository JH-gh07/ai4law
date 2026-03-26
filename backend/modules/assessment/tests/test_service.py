from backend.modules.assessment.schema import AssessmentRequest
from backend.modules.assessment.service import AssessmentService


def test_assessment_generate_report() -> None:
    service = AssessmentService()
    payload = AssessmentRequest(
        company_name="测试公司",
        industry="SaaS",
        is_ciio=False,
        contains_important_data=False,
        pii_count=200000,
        spi_count=300,
        transfer_purpose="跨境客服",
        receiver_country="Singapore",
        uploaded_files=[],
    )

    result = service.generate_report(payload)

    assert result.state == "COMPLETED"
    assert len(result.chapters) == 8
    assert result.report_path.endswith("_security_assessment_report.docx")
    assert result.output_files["markdown"].endswith("_security_assessment_report.md")
