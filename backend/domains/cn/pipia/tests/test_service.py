from pathlib import Path
from zipfile import ZipFile

from pypdf import PdfReader

from backend.domains.cn.pipia.schema import PIPIARequest
from backend.domains.cn.pipia.service import PIPIAService


def test_pipia_generate_report(tmp_path: Path) -> None:
    attachment_path = tmp_path / "scc.txt"
    attachment_path.write_text("标准合同条款示例", encoding="utf-8")

    service = PIPIAService(llm_client=None)
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

    assert result.report_path.endswith(".docx")
    assert "_PIPIA_报告_草案_" in result.report_path
    assert result.output_files["zip"].endswith(".zip")
    assert "_PIPIA_输出包_草案_" in result.output_files["zip"]
    pdf_path = Path(result.output_files["pdf"])
    assert pdf_path.read_bytes().startswith(b"%PDF")
    assert len(PdfReader(pdf_path).pages) >= 1
    with ZipFile(result.output_files["zip"]) as bundle:
        assert pdf_path.name in bundle.namelist()
    assert len(result.chapters) == 7
    assert result.route_type == "scc_filing"
    assert result.consistency_issues == []
    assert result.facts, "PIPIA must expose structured facts"
    assert result.issues == [], "Low-risk complete SCC filing should not create blocking issues"
    assert result.evidence_chain, "PIPIA must expose evidence chain"
    assert result.filing_readiness.status == "ready"
    assert result.material_gaps == []


def test_pipia_certification_without_materials_is_blocked(tmp_path: Path) -> None:
    attachment_path = tmp_path / "policy.txt"
    attachment_path.write_text("内部制度仅概括提及跨境合规要求", encoding="utf-8")

    service = PIPIAService(llm_client=None)
    payload = PIPIARequest.model_validate(
        {
            "route_type": "certification",
            "company_profile": {
                "company_name": "认证路径测试公司",
                "company_uscc": "91310000YYYYYYYYYY",
                "is_ciio": False,
                "processing_person_count": 80000,
                "outbound_pi_count": 5000,
                "outbound_spi_count": 120,
                "industry": "跨境零售",
            },
            "transfer_context": {
                "purpose": "会员运营与客户服务",
                "recipient_name": "Global Service Hub",
                "recipient_country_region": "新加坡",
                "legal_basis": "单独同意",
            },
            "personal_info_scope": {
                "pi_categories": ["账户信息", "联系方式"],
                "spi_categories": ["交易偏好画像"],
                "subject_volume": 5000,
            },
            "rights_protection": {
                "notice_mechanism": "隐私政策",
                "consent_mechanism": "注册勾选",
                "dsar_channel": "privacy@example.com",
                "retention_policy": "按最短必要期限保存",
            },
            "emergency_plan": {
                "incident_response_sla_hours": 96,
                "escalation_path": "隐私负责人 -> 法务",
            },
            "attachments": [
                {
                    "file_role": "internal_policy",
                    "file_name": "policy.txt",
                    "file_format": "txt",
                    "storage_uri": str(attachment_path),
                }
            ],
        }
    )

    result = service.generate_report(payload)

    assert result.filing_readiness.status == "blocked"
    assert any("certification_material" in gap for gap in result.material_gaps)
    assert any(issue["severity"] == "BLOCKER" for issue in result.issues)
    assert any("72 hours" in issue for issue in result.consistency_issues)
