import time

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_cn_flow_async_flow() -> None:
    accepted = client.post(
        "/api/v1/cn-flow/generate_async",
        json={
            "company_name": "AsyncCNFlow",
            "transfer_purpose": "全球客服与风控",
            "data_categories": ["账户信息", "设备信息"],
            "sensitive_data_flags": ["生物识别"],
            "recipient_entities": [
                {
                    "entity_name": "US ServiceCo",
                    "country_region": "United States",
                    "entity_role": "processor",
                    "is_restricted_party": False,
                }
            ],
            "transfer_chain": "CN -> US processor -> subprocessor",
            "attachments": [
                {
                    "file_role": "data_inventory",
                    "file_name": "data.csv",
                    "file_format": "csv",
                    "storage_uri": "storage://uploads/data.csv",
                },
                {
                    "file_role": "entity_inventory",
                    "file_name": "entity.csv",
                    "file_format": "csv",
                    "storage_uri": "storage://uploads/entity.csv",
                },
            ],
        },
    )
    assert accepted.status_code == 200
    task_id = accepted.json()["task_id"]

    for _ in range(60):
        status = client.get(f"/api/v1/cn-flow/tasks/{task_id}")
        assert status.status_code == 200
        payload = status.json()
        if payload["state"] == "COMPLETED":
            assert payload["result"]["output_files"]["xlsx"].endswith(".xlsx")
            return
        if payload["state"] == "FAILED":
            raise AssertionError(payload)
        time.sleep(0.05)

    raise AssertionError("cn-flow async task timeout")

