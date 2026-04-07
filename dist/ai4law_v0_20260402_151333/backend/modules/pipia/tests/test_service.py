from pathlib import Path

from backend.modules.pipia.schema import PIPIARequest
from backend.modules.pipia.service import PIPIAService


def test_pipia_generate_report(tmp_path: Path) -> None:
    attachment_path = tmp_path / "scc.txt"
    attachment_path.write_text("标准合同条款示例", encoding="utf-8")

    service = PIPIAService()
    payload = PIPIARequest.model_validate(
        {
            "route_type": "scc_filing",
            "company_profile": {
                "company_name": "测试公司",
                "company_uscc": "91310000XXXXXXXXXX",
                "is_ciio": False,
                "processing_person_count": 230000,
                "outbound_pi_count": 46000,
                "outbound_spi_count": 2500,
                "industry": "互联网SaaS",
            },
            "transfer_context": {
                "purpose": "境外客服与系统运维",
                "recipient_name": "OceanStar Technology Inc.",
                "recipient_country_region": "美国加州",
                "legal_basis": "合同履行必要",
            },
            "personal_info_scope": {
                "pi_categories": ["账户信息", "联系方式", "日志信息"],
                "spi_categories": ["身份认证信息"],
                "subject_volume": 46000,
            },
            "rights_protection": {
                "notice_mechanism": "隐私政策+弹窗",
                "consent_mechanism": "单独同意",
                "dsar_channel": "privacy@example.com",
                "retention_policy": "到期删除+最短必要",
            },
            "emergency_plan": {
                "incident_response_sla_hours": 24,
                "escalation_path": "DPO -> 法务 -> 管理层",
            },
            "attachments": [
                {
                    "file_role": "scc_contract",
                    "file_name": "scc.txt",
                    "file_format": "txt",
                    "storage_uri": str(attachment_path),
                }
            ],
        }
    )

    result = service.generate_report(payload)

    assert result.report_path.endswith("_pipia_report.docx")
    assert result.output_files["zip"].endswith("_pipia_output_bundle.zip")
    assert len(result.chapters) == 7
    assert result.route_type == "scc_filing"
    assert result.consistency_issues == []

