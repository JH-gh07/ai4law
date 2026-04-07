import time

from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_scc_async_flow() -> None:
    accepted = client.post(
        "/api/v1/scc/generate_async",
        json={
            "company_name": "AsyncCo",
            "receiver_name": "Receiver SG",
            "receiver_country": "Singapore",
            "transfer_purpose": "support",
            "pii_count": 150000,
            "spi_count": 500,
            "has_scc_draft": False,
            "uploaded_files": [],
        },
    )
    assert accepted.status_code == 200
    task_id = accepted.json()["task_id"]

    for _ in range(300):
        status = client.get(f"/api/v1/scc/tasks/{task_id}")
        assert status.status_code == 200
        payload = status.json()
        if payload["state"] == "COMPLETED":
            assert payload["result"]["report_path"].endswith(".docx")
            return
        if payload["state"] == "FAILED":
            raise AssertionError(payload)
        time.sleep(0.1)

    raise AssertionError("scc async task timeout")
