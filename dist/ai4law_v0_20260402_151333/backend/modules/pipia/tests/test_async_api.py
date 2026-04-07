import time
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_pipia_async_flow(tmp_path: Path) -> None:
    attachment_path = tmp_path / "scc.txt"
    attachment_path.write_text("标准合同条款示例", encoding="utf-8")

    accepted = client.post(
        "/api/v1/pipia/generate_async",
        json={
            "route_type": "scc_filing",
            "company_profile": {
                "company_name": "AsyncPIPIA",
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
        },
    )
    assert accepted.status_code == 200
    task_id = accepted.json()["task_id"]

    for _ in range(60):
        status = client.get(f"/api/v1/pipia/tasks/{task_id}")
        assert status.status_code == 200
        payload = status.json()
        if payload["state"] == "COMPLETED":
            assert payload["result"]["report_path"].endswith(".docx")
            assert payload["result"]["output_files"]["zip"].endswith(".zip")
            return
        if payload["state"] == "FAILED":
            raise AssertionError(payload)
        time.sleep(0.05)

    raise AssertionError("pipia async task timeout")

