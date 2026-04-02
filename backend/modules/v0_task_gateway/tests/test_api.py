import time
from io import BytesIO

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_v0_task_gateway_assessment_flow() -> None:
    created = client.post(
        "/api/v0/tasks",
        json={
            "module_code": "2.2",
            "session_id": "sess-v0-gateway",
            "input_payload": {
                "company_name": "V0GatewayCo",
                "industry": "SaaS",
                "is_ciio": False,
                "contains_important_data": False,
                "pii_count": 150000,
                "spi_count": 500,
                "transfer_purpose": "support",
                "receiver_country": "Singapore",
                "uploaded_files": [],
            },
            "attachment_ids": [],
        },
    )
    assert created.status_code == 200
    task_id = created.json()["data"]["task_id"]

    for _ in range(60):
        status = client.get(f"/api/v0/tasks/{task_id}")
        assert status.status_code == 200
        payload = status.json()["data"]
        if payload["status"] == "COMPLETED":
            break
        if payload["status"] == "FAILED":
            raise AssertionError(payload)
        time.sleep(0.05)
    else:
        raise AssertionError("v0 gateway task timeout")

    artifacts = client.get(f"/api/v0/tasks/{task_id}/artifacts")
    assert artifacts.status_code == 200
    items = artifacts.json()["data"]["artifacts"]
    assert items
    file_types = {item["file_type"] for item in items}
    assert "docx" in file_types
    assert "zip" in file_types

    zip_item = next(item for item in items if item["file_type"] == "zip")
    downloaded = client.get(f"/api/v0/artifacts/{zip_item['artifact_id']}/download")
    assert downloaded.status_code == 200
    assert downloaded.headers.get("content-disposition", "").lower().find(".zip") >= 0


def test_v0_task_gateway_pipia_flow() -> None:
    upload_resp = client.post(
        "/api/v0/files/upload",
        files={"file": ("evidence.txt", BytesIO("合同条款示例".encode("utf-8")), "text/plain")},
    )
    assert upload_resp.status_code == 200
    file_id = upload_resp.json()["data"]["file_id"]

    created = client.post(
        "/api/v0/tasks",
        json={
            "module_code": "2.3",
            "session_id": "sess-v0-pipia",
            "input_payload": {
                "route_type": "scc_filing",
                "company_profile": {
                    "company_name": "V0PIPIACo",
                    "company_uscc": "91310000XXXXXXXXXX",
                    "is_ciio": False,
                    "processing_person_count": 120000,
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
                "attachments": [],
            },
            "attachment_ids": [file_id],
        },
    )
    assert created.status_code == 200
    task_id = created.json()["data"]["task_id"]

    for _ in range(60):
        status = client.get(f"/api/v0/tasks/{task_id}")
        assert status.status_code == 200
        payload = status.json()["data"]
        if payload["status"] == "COMPLETED":
            break
        if payload["status"] == "FAILED":
            raise AssertionError(payload)
        time.sleep(0.05)
    else:
        raise AssertionError("v0 gateway pipia task timeout")

    artifacts = client.get(f"/api/v0/tasks/{task_id}/artifacts")
    assert artifacts.status_code == 200
    items = artifacts.json()["data"]["artifacts"]
    assert items
    file_types = {item["file_type"] for item in items}
    assert "docx" in file_types
    assert "zip" in file_types
