import time

from backend.domains.us.cpra import router as cpra_router
from backend.common.tasks.manager import InMemoryTaskManager
from backend.domains.us.cpra.service import CPRAService


class _DisabledLLM:
    enabled = False


def _install_test_service(monkeypatch) -> None:
    """Keep the default async contract test independent of developer API keys."""
    monkeypatch.setattr(cpra_router, "service", CPRAService(llm_client=_DisabledLLM()))


def test_cpra_async_flow(authenticated_client, monkeypatch) -> None:
    _install_test_service(monkeypatch)
    accepted = authenticated_client.post(
        "/api/v1/cpra/generate_async",
        json={
            "company_name": "AsyncCPRA",
            "business_model": "SaaS",
            "data_lifecycle": "收集-处理-存储-删除",
            "notice_and_consent": "隐私告知缺失",
            "consumer_rights_process": "目前仅邮箱接收",
            "opt_out_and_sale_sharing": "存在共享但无opt-out",
            "vendor_management": "供应商管理未体现DPA",
            "attachments": [
                {
                    "file_role": "privacy_policy",
                    "file_name": "policy.url",
                    "file_format": "url",
                    "storage_uri": "https://example.com/privacy",
                }
            ],
        },
    )
    assert accepted.status_code == 200
    task_id = accepted.json()["task_id"]

    for _ in range(200):
        status = authenticated_client.get(f"/api/v1/cpra/tasks/{task_id}")
        assert status.status_code == 200
        payload = status.json()
        if payload["state"] == "COMPLETED":
            assert payload["result"]["output_files"]["xlsx"].endswith(".xlsx")
            return
        if payload["state"] == "FAILED":
            raise AssertionError(payload)
        time.sleep(0.05)

    raise AssertionError("cpra async task timeout")


def test_cpra_status_recovers_after_worker_memory_miss(
    authenticated_client,
    monkeypatch,
) -> None:
    _install_test_service(monkeypatch)
    accepted = authenticated_client.post(
        "/api/v1/cpra/generate_async",
        json={
            "company_name": "RecoveredCPRA",
            "business_model": "SaaS",
            "data_lifecycle": "收集-处理-存储-删除",
            "notice_and_consent": "隐私告知缺失",
            "consumer_rights_process": "目前仅邮箱接收",
            "opt_out_and_sale_sharing": "存在共享但无opt-out",
            "vendor_management": "供应商管理未体现DPA",
            "attachments": [
                {
                    "file_role": "privacy_policy",
                    "file_name": "policy.url",
                    "file_format": "url",
                    "storage_uri": "https://example.com/privacy",
                }
            ],
        },
    )
    assert accepted.status_code == 200
    task_id = accepted.json()["task_id"]

    for _ in range(200):
        status = authenticated_client.get(f"/api/v1/cpra/tasks/{task_id}")
        assert status.status_code == 200
        if status.json()["state"] == "COMPLETED":
            break
        time.sleep(0.05)
    else:
        raise AssertionError("cpra async task timeout")

    cpra_router.service.tasks = InMemoryTaskManager(module="cpra")
    recovered = authenticated_client.get(f"/api/v1/cpra/tasks/{task_id}")

    assert recovered.status_code == 200
    assert recovered.json()["state"] == "COMPLETED"
    assert recovered.json()["result"]["company_name"] == "RecoveredCPRA"
