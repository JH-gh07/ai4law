import time

from backend.domains.eu.bcr_review import router as bcr_router
from backend.domains.eu.bcr_review.service import BCRService


class _DisabledLLM:
    enabled = False


def test_bcr_async_flow(authenticated_client, monkeypatch) -> None:
    # Automated tests must not inherit developer provider credentials.
    monkeypatch.setattr(
        bcr_router,
        "service",
        BCRService(llm_client=_DisabledLLM()),
    )
    accepted = authenticated_client.post(
        "/api/v1/bcr/generate_async",
        json={
            "company_name": "AsyncBCR",
            "review_items": [
                {
                    "code": "3.2-C1",
                    "title": "结构完整性",
                    "score": "partial",
                    "finding": "章节覆盖不完整",
                    "legal_basis": "GDPR 第47条",
                    "recommendation": "补齐约束力与权利章节",
                    "evidence": "BCR-v1 第3章",
                },
                {
                    "code": "3.2-C2",
                    "title": "集团内部约束力",
                    "score": "compliant",
                    "finding": "已覆盖",
                    "legal_basis": "GDPR 第47条",
                    "recommendation": "保持",
                    "evidence": "BCR-v1 第4章",
                },
            ],
            "attachments": [],
        },
    )
    assert accepted.status_code == 200
    task_id = accepted.json()["task_id"]

    for _ in range(200):
        status = authenticated_client.get(f"/api/v1/bcr/tasks/{task_id}")
        assert status.status_code == 200
        payload = status.json()
        if payload["state"] == "COMPLETED":
            assert payload["result"]["report_path"].endswith(".docx")
            return
        if payload["state"] == "FAILED":
            raise AssertionError(payload)
        time.sleep(0.05)

    raise AssertionError("bcr async task timeout")
