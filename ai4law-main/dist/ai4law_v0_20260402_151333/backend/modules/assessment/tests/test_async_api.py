import time

from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_assessment_async_flow() -> None:
    accepted = client.post(
        "/api/v1/assessment/generate_async",
        json={
            "company_name": "AsyncCo",
            "industry": "SaaS",
            "is_ciio": False,
            "contains_important_data": False,
            "pii_count": 150000,
            "spi_count": 500,
            "transfer_purpose": "support",
            "receiver_country": "Singapore",
            "uploaded_files": [],
        },
    )
    assert accepted.status_code == 200
    task_id = accepted.json()["task_id"]

    for _ in range(50):
        status = client.get(f"/api/v1/assessment/tasks/{task_id}")
        assert status.status_code == 200
        payload = status.json()
        if payload["state"] == "COMPLETED":
            assert payload["result"]["report_path"].endswith(".docx")
            return
        if payload["state"] == "FAILED":
            raise AssertionError(payload)
        time.sleep(0.05)

    raise AssertionError("assessment async task timeout")
