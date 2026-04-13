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
        force_override_path=True,
        uploaded_files=[],
    )

    result = service.generate_report(payload)

    assert result.state == "COMPLETED"
    assert len(result.chapters) == 8
    assert result.report_path.endswith(".docx")
    assert "_数据出境风险自评估报告_草案_" in result.report_path
    assert result.output_files["markdown"].endswith(".md")
    assert "_数据出境风险自评估报告_草案_" in result.output_files["markdown"]


def test_assessment_rejects_path_mismatch_without_force() -> None:
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
        force_override_path=False,
        uploaded_files=[],
    )

    try:
        service.generate_report(payload)
        raise AssertionError("expected ValueError for path mismatch")
    except ValueError as exc:
        assert "force_override_path=true" in str(exc)
