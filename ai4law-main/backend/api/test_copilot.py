from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.copilot import router
from backend.core.container import AppContainer
from backend.core.settings import Settings


def test_copilot_chat_returns_local_reply_when_llm_is_disabled() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/copilot")

    settings = Settings(tencent_api_key=None)
    container = AppContainer(settings)
    container.llm_client._enabled = False
    app.state.container = container

    client = TestClient(app)
    response = client.post(
        "/api/v1/copilot/chat",
        json={
            "prompt": "下一步应该怎么做？",
            "action": "memo",
            "task_space": {
                "id": "task-1",
                "name": "合规路径诊断 2026-04-12",
                "jurisdiction": "CN",
                "module": "diagnosis",
                "mode": "rapid",
                "workspace_style": "research"
            },
            "context": {
                "current_step": "基础识别 / blocked",
                "blocker": "请上传数据清单附件",
                "runs_count": 0,
                "issues_count": 1,
                "evidence_count": 0,
                "artifact_count": 0,
                "top_issues": ["[high] 缺少 data_inventory"],
                "latest_artifacts": []
            },
            "messages": [
                {"role": "assistant", "content": "我会根据当前任务上下文提供建议。"},
                {"role": "user", "content": "hi"}
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is False
    assert payload["fallback"] is True
    assert payload["model"] == "local-copilot-fallback"
    assert "先处理当前阻塞项" in payload["reply"]
    assert "请上传数据清单附件" in payload["reply"]


def test_copilot_chat_small_talk_stays_conversational_when_llm_is_disabled() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/copilot")

    settings = Settings(tencent_api_key=None)
    container = AppContainer(settings)
    container.llm_client._enabled = False
    app.state.container = container

    client = TestClient(app)
    response = client.post(
        "/api/v1/copilot/chat",
        json={
            "prompt": "hi",
            "task_space": {
                "id": "task-1",
                "name": "合规路径诊断 2026-04-12",
                "jurisdiction": "CN",
                "module": "diagnosis",
                "mode": "rapid",
                "workspace_style": "research"
            },
            "context": {
                "current_step": "基础识别 / blocked",
                "blocker": "请上传数据清单附件",
                "runs_count": 0,
                "issues_count": 1,
                "evidence_count": 0,
                "artifact_count": 0,
                "top_issues": ["[high] 缺少 data_inventory"],
                "latest_artifacts": []
            },
            "messages": []
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["fallback"] is True
    assert "我在" in payload["reply"]
    assert "现状说明" not in payload["reply"]
