import time

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_dpia_async_flow() -> None:
    accepted = client.post(
        "/api/v1/dpia/generate_async",
        json={
            "project_name": "EU用户行为分析系统",
            "processing_description": "收集用户行为日志并用于推荐优化",
            "purpose_and_necessity": "保障服务可用性并优化推荐准确率",
            "lawful_basis": "合法利益+合同履行",
            "risk_assessment": "存在画像偏差与过度处理风险",
            "mitigation_measures": "去标识化、最小化、访问控制、审计",
            "residual_risk": "中风险，可接受并持续监控",
            "attachments": [
                {
                    "file_role": "data_flow_diagram",
                    "file_name": "flow.pdf",
                    "file_format": "pdf",
                    "storage_uri": "storage://uploads/flow.pdf",
                }
            ],
        },
    )
    assert accepted.status_code == 200
    task_id = accepted.json()["task_id"]

    for _ in range(200):
        status = client.get(f"/api/v1/dpia/tasks/{task_id}")
        assert status.status_code == 200
        payload = status.json()
        if payload["state"] == "COMPLETED":
            assert payload["result"]["report_path"].endswith(".docx")
            return
        if payload["state"] == "FAILED":
            raise AssertionError(payload)
        time.sleep(0.05)

    raise AssertionError("dpia async task timeout")
