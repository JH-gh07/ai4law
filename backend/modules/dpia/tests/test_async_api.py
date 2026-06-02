"""Test DPIA async API endpoints with the new DPIARequest schema."""
import time

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

_VALID_PAYLOAD = {
    "project_name": "DPIA异步测试项目",
    "project_goal": "通过AI算法对员工健康数据进行评估和分类",
    "processing_flow_description": "收集员工体检报告和可穿戴设备健康数据，进行健康风险评分和个性化健康计划推荐",
    "special_category_data": True,
    "special_category_types": ["健康数据"],
    "data_subject_categories": ["员工"],
    "data_categories": ["体检数据", "心率"],
    "data_subject_count": "5,000人",
    "cross_border_transfer": True,
    "transfer_destination": "United States",
    "automated_decision_making": True,
    "new_technology": True,
    "vulnerable_data_subjects": True,
    "lawful_basis": ["GDPR Art 6(1)(b)"],
    "necessity_statement": "处理员工健康数据是实现法定职业健康管理所必需，详细论证必要性。",
    "proportionality_statement": "仅收集与职业健康评估直接相关的数据指标，限制处理频率。",
    "dpo_name": "李律师",
    "dpo_opinion": "初步审阅，待补充算法公平性验证报告",
    "uploaded_files": ["flow.pdf"],
}


def test_dpia_async_flow() -> None:
    accepted = client.post("/api/v1/dpia/generate_async", json=_VALID_PAYLOAD)
    assert accepted.status_code == 200
    data = accepted.json()
    assert "task_id" in data
    assert data["state"] == "PENDING"
    task_id = data["task_id"]

    for _ in range(200):
        status = client.get(f"/api/v1/dpia/tasks/{task_id}")
        assert status.status_code == 200
        payload = status.json()
        if payload["state"] == "COMPLETED":
            result = payload["result"]
            assert "output_files" in result
            return
        if payload["state"] == "FAILED":
            raise AssertionError(f"Task failed: {payload}")
        time.sleep(0.05)

    raise AssertionError("dpia async task timeout")
