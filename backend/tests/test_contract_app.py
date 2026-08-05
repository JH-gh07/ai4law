import json
from pathlib import Path
import subprocess
import sys


DPIA_PAYLOAD = {
    "project_name": "Contract App DPIA",
    "project_goal": "验证契约路由而不执行完整报告生成",
    "processing_flow_description": "收集员工健康数据并进行风险评估",
    "special_category_data": True,
    "special_category_types": ["健康数据"],
    "data_subject_categories": ["员工"],
    "data_categories": ["体检数据"],
    "data_subject_count": "1000",
    "cross_border_transfer": False,
    "automated_decision_making": True,
    "new_technology": True,
    "vulnerable_data_subjects": False,
    "lawful_basis": ["GDPR Art 6(1)(b)"],
    "necessity_statement": "处理范围限于职业健康管理所需数据。",
    "proportionality_statement": "通过最小化和访问控制限制处理范围。",
    "dpo_name": "Contract DPO",
    "dpo_opinion": "同意进入影响评估。",
    "uploaded_files": [],
}


def test_contract_app_starts_with_recording_execution(tmp_path: Path) -> None:
    probe = f"""
import json
from fastapi.testclient import TestClient
from backend.tests.contract_app import app

with TestClient(app) as client:
    health = client.get('/health')
    registered = client.post('/api/v1/auth/register', json={{
        'username': 'contract-user',
        'email': 'contract-user@example.com',
        'password': 'contract-password',
    }})
    token = registered.json()['access_token']
    accepted = client.post(
        '/api/v1/dpia/generate_async',
        headers={{'Authorization': f'Bearer {{token}}'}},
        json={DPIA_PAYLOAD!r},
    )
    state = client.get('/__contract__/state')
    print(json.dumps({{
        'health_status': health.status_code,
        'health': health.json(),
        'accepted_status': accepted.status_code,
        'accepted': accepted.json(),
        'state_status': state.status_code,
        'state': state.json(),
    }}))
"""
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=Path(__file__).resolve().parents[2],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
        env={
            "PATH": "",
            "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
            "AI4LAW_CONTRACT_TMP_ROOT": str(tmp_path),
        },
    )
    payload = json.loads(result.stdout.strip().splitlines()[-1])

    assert payload["health_status"] == 200
    assert payload["health"] == {"status": "ok"}
    assert payload["accepted_status"] == 200
    assert payload["accepted"]["state"] == "CREATED"
    assert payload["accepted"]["task_id"]
    assert payload["state_status"] == 200
    assert payload["state"] == {
        "manager_count": 9,
        "submission_count": 1,
        "external_network_blocked": True,
    }
